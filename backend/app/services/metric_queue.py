import asyncio
import logging
from collections import deque

from app.services.structured_logger import log_event

logger = logging.getLogger("energygrid")

_queue: deque = deque(maxlen=10000)


def enqueue(record: dict):
    _queue.append(record)
    log_event(
        logging.WARNING,
        event="METRICA_ENCOLADA",
        district_id=record.get("district_id"),
        substation_id=record.get("substation_id"),
        queue_size=len(_queue),
    )


async def _flush_once(pool) -> bool:
    if not _queue or pool is None:
        return True
    record = _queue[0]
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO consumo_temporal (
                district_id, substation_id, consumo_kw,
                capacidad_kw, timestamp, anomalia, notas
            ) VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
            record["district_id"],
            record["substation_id"],
            record["consumo_kw"],
            record["capacidad_kw"],
            record["timestamp"],
            record.get("anomalia", False),
            record.get("notas"),
        )
    _queue.popleft()
    return True


async def queue_worker(app):
    delay = 2
    while True:
        await asyncio.sleep(delay)
        pool = getattr(app.state, "db", None)
        if not _queue or pool is None:
            delay = 2
            continue
        try:
            flushed = 0
            while _queue:
                await _flush_once(pool)
                flushed += 1
            if flushed:
                log_event(logging.INFO, event="QUEUE_FLUSHED", inserted=flushed)
            delay = 2
        except Exception as exc:
            logger.error(f"[QUEUE] Error reinsertando: {exc}")
            delay = min(delay * 2, 60)
