import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("energygrid")


class PgStatCollector:
    def __init__(self, pool_getter, interval_seconds: int = 60):
        self.pool_getter = pool_getter
        self.interval = interval_seconds
        self._snapshots: List[Dict[str, Any]] = []
        self._last_raw: Optional[List[Dict[str, Any]]] = None
        self._running = False

    async def collect(self) -> List[Dict[str, Any]]:
        pool = self.pool_getter()
        if not pool:
            logger.warning("pg_stat_collector: no database pool available")
            return []

        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        queryid,
                        LEFT(query, 500) AS query,
                        calls,
                        total_exec_time,
                        min_exec_time,
                        max_exec_time,
                        mean_exec_time,
                        rows,
                        shared_blks_hit,
                        shared_blks_read,
                        ROUND(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 2) AS cache_hit_ratio
                    FROM pg_stat_statements
                    WHERE calls > 0
                    ORDER BY total_exec_time DESC
                    LIMIT 100
                """)
                data = [dict(r) for r in rows]

            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "queries": data,
                "total_queries": sum(r["calls"] for r in data) if data else 0,
                "total_time_ms": round(sum(r["total_exec_time"] for r in data), 2) if data else 0,
            }
            self._snapshots.append(snapshot)
            if len(self._snapshots) > 1440:
                self._snapshots.pop(0)
            self._last_raw = data

            slow_count = sum(1 for r in data if r["mean_exec_time"] > 500) if data else 0
            logger.info(
                "pg_stat_statements collected",
                extra={"total": len(data), "slow_queries": slow_count},
            )
            return data

        except Exception as e:
            logger.error(f"pg_stat_collector error: {e}")
            return []

    def get_last_snapshot(self) -> Optional[Dict[str, Any]]:
        return self._snapshots[-1] if self._snapshots else None

    def get_slow_queries(self, threshold_ms: float = 500, limit: int = 50) -> List[Dict[str, Any]]:
        if not self._last_raw:
            return []
        slow = [r for r in self._last_raw if r["mean_exec_time"] > threshold_ms]
        return sorted(slow, key=lambda r: r["mean_exec_time"], reverse=True)[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        snapshot = self.get_last_snapshot()
        if not snapshot:
            return {"total_queries": 0, "slow_queries": 0, "average_time_ms": 0}
        data = snapshot["queries"]
        slow_count = sum(1 for r in data if r["mean_exec_time"] > 500)
        avg_time = round(sum(r["mean_exec_time"] for r in data) / len(data), 2) if data else 0
        return {
            "total_queries": snapshot["total_queries"],
            "slow_queries": slow_count,
            "average_time_ms": avg_time,
            "max_time_ms": max((r["max_exec_time"] for r in data), default=0) if data else 0,
            "source": "pg_stat_statements",
            "cached_queries": len(data),
        }

    async def start_background_loop(self):
        self._running = True
        while self._running:
            await self.collect()
            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False
