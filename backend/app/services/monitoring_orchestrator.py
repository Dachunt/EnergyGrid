"""
Monitoring System Orchestrator
Integra Munin, Pingdom y Slow Query Log en un sistema unificado
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List
import logging

from app.services.munin_monitor import MuninMonitor
from app.services.pingdom_guard import PingdomGuard
from app.services.slow_query_log import SlowQueryLog
from app.services.pg_stat_collector import PgStatCollector

logger = logging.getLogger("energygrid")


class MonitoringOrchestrator:
    """Orquestador central de monitoreo del sistema"""

    def __init__(self, pool_getter=None):
        self.munin = MuninMonitor()
        self.pingdom = PingdomGuard(check_interval=60)
        self.slow_query_log = SlowQueryLog(slow_query_threshold_ms=500)
        self.pg_stat = PgStatCollector(pool_getter=pool_getter or (lambda: None), interval_seconds=60)
        self.monitoring_active = False
        self.background_tasks = []

    async def initialize_monitoring(self):
        """Inicializa todos los monitores y endpoints"""
        logger.info("Initializing monitoring system...")

        # Configurar endpoints para Pingdom
        self.pingdom.add_endpoint(
            "main_api",
            "http://localhost:8000/health",
            timeout=5,
            expected_status=200,
        )
        
        # Agregar más endpoints para monitoreo completo
        self.pingdom.add_endpoint(
            "dashboard",
            "http://localhost:8000/",
            timeout=5,
            expected_status=200,
        )
        
        self.pingdom.add_endpoint(
            "monitoring_dashboard_api",
            "http://localhost:8000/api/monitoring/dashboard",
            timeout=5,
            expected_status=200,
        )
        
        self.pingdom.add_endpoint(
            "munin_metrics_api",
            "http://localhost:8000/api/monitoring/munin/metrics",
            timeout=5,
            expected_status=200,
        )
        
        self.pingdom.add_endpoint(
            "pingdom_status_api",
            "http://localhost:8000/api/monitoring/pingdom/status",
            timeout=5,
            expected_status=200,
        )
        
        self.pingdom.add_endpoint(
            "slow_queries_api",
            "http://localhost:8000/api/monitoring/queries/slow",
            timeout=5,
            expected_status=200,
        )

    async def start_continuous_monitoring(self):
        """Inicia monitoreo continuo en background"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        logger.info("Starting continuous monitoring")

        # Crear tareas de background
        munin_task = asyncio.create_task(self._munin_loop())
        pingdom_task = asyncio.create_task(self._pingdom_loop())
        pg_stat_task = asyncio.create_task(self._pg_stat_loop())

        self.background_tasks = [munin_task, pingdom_task, pg_stat_task]

    async def stop_continuous_monitoring(self):
        """Detiene monitoreo continuo"""
        self.monitoring_active = False
        self.pg_stat.stop()

        for task in self.background_tasks:
            task.cancel()

        logger.info("Continuous monitoring stopped")

    async def _munin_loop(self):
        """Loop de recopilación de métricas Munin"""
        while self.monitoring_active:
            try:
                self.munin.collect_metrics()
                await asyncio.sleep(30)  # Recopilar cada 30 segundos
            except Exception as e:
                logger.error(f"Error in Munin loop: {e}")
                await asyncio.sleep(10)

    async def _pingdom_loop(self):
        """Loop de verificación Pingdom"""
        sync_interval = 0
        while self.monitoring_active:
            try:
                await self.pingdom.run_checks()

                # Sync with real Pingdom API every 5 min (300s)
                sync_interval += 60
                if sync_interval >= 300:
                    await self.pingdom.sync_with_pingdom()
                    await self.pingdom.fetch_pingdom_results()
                    sync_interval = 0

                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in Pingdom loop: {e}")
                await asyncio.sleep(10)

    async def _pg_stat_loop(self):
        """Loop de recolección de pg_stat_statements"""
        while self.monitoring_active:
            try:
                data = await self.pg_stat.collect()
                if data:
                    self.slow_query_log.ingest_from_pg_stats(data)
                await asyncio.sleep(60)  # Recolectar cada 60 segundos
            except Exception as e:
                logger.error(f"Error in pg_stat loop: {e}")
                await asyncio.sleep(10)

    def log_database_query(
        self,
        query: str,
        execution_time_ms: float,
        status: str = "success",
        rows_affected: int = 0,
        error: str = None,
    ):
        """Registra una query de base de datos"""
        # Detectar tipo de query
        query_type = "SELECT"
        if query.strip().upper().startswith("INSERT"):
            query_type = "INSERT"
        elif query.strip().upper().startswith("UPDATE"):
            query_type = "UPDATE"
        elif query.strip().upper().startswith("DELETE"):
            query_type = "DELETE"

        return self.slow_query_log.log_query(
            query=query,
            execution_time_ms=execution_time_ms,
            status=status,
            rows_affected=rows_affected,
            error=error,
            query_type=query_type,
        )

    def get_system_health(self) -> Dict[str, Any]:
        """Obtiene el estado general del sistema"""
        munin_health = self.munin.get_health_score()
        pingdom_status = self.pingdom.get_all_status()
        query_stats = self.slow_query_log.get_query_statistics()

        # Calcular health score combinado
        components_health = [
            munin_health,
            (100 if pingdom_status["overall_status"] == "up" else 0),
            (100 - (query_stats.get("slow_query_percentage", 0) * 2)),
        ]

        combined_health = sum(components_health) / len(components_health)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_health": round(combined_health, 2),
            "components": {
                "system_health": round(munin_health, 2),
                "availability": pingdom_status["overall_status"],
                "database_performance": round(
                    100 - (query_stats.get("slow_query_percentage", 0) * 2), 2
                ),
            },
            "status": self._determine_status(combined_health),
        }

    def _determine_status(self, health_score: float) -> str:
        """Determina el estado general basado en el health score"""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 70:
            return "good"
        elif health_score >= 50:
            return "warning"
        else:
            return "critical"

    def get_unified_alerts(self) -> List[Dict[str, Any]]:
        """Obtiene alertas unificadas de todos los monitores"""
        all_alerts = []

        # Alertas de Munin
        all_alerts.extend(self.munin.get_alerts())

        # Alertas de Pingdom
        endpoints = self.pingdom.get_all_status()
        for name, status in endpoints.get("endpoints", {}).items():
            if status["status"] == "down":
                all_alerts.append({
                    "type": "endpoint_down",
                    "severity": "critical",
                    "message": f"Endpoint {name} is down",
                    "endpoint": name,
                })

        # Alertas de Slow Query Log
        all_alerts.extend(self.slow_query_log.get_alerts())

        return sorted(all_alerts, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x.get("severity", "info")))

    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Obtiene datos completos del dashboard de monitoreo"""
        munin_latest = (
            self.munin.metrics_history[-1]
            if self.munin.metrics_history
            else None
        )
        pingdom_status = self.pingdom.get_all_status()
        query_stats = self.slow_query_log.get_query_statistics()
        bottlenecks = self.slow_query_log.get_bottlenecks(limit=5)
        alerts = self.get_unified_alerts()
        system_health = self.get_system_health()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_health": system_health,
            "system_metrics": {
                "cpu_percent": munin_latest["cpu"]["percent"] if munin_latest else 0,
                "memory_percent": munin_latest["memory"]["percent"] if munin_latest else 0,
                "disk_percent": munin_latest["disk"]["percent"] if munin_latest else 0,
                "system_load": munin_latest["system_load"] if munin_latest else {},
            },
            "availability": pingdom_status,
            "database": {
                "statistics": query_stats,
                "bottlenecks": bottlenecks,
            },
            "alerts": alerts,
            "alert_count": len(alerts),
            "critical_alerts": len([a for a in alerts if a.get("severity") == "critical"]),
        }

    def get_detailed_report(self) -> Dict[str, Any]:
        """Genera un reporte detallado de monitoreo"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_overview": self.get_system_health(),
            "munin": {
                "latest_metrics": self.munin.metrics_history[-1] if self.munin.metrics_history else None,
                "health_score": self.munin.get_health_score(),
                "alerts": self.munin.get_alerts(),
            },
            "pingdom": {
                "overall_status": self.pingdom.get_all_status(),
                "uptime_24h": self.pingdom.get_uptime_report(hours=24),
                "incidents": self.pingdom.get_incidents(),
            },
            "slow_query_log": {
                "statistics": self.slow_query_log.get_query_statistics(),
                "bottlenecks": self.slow_query_log.get_bottlenecks(limit=10),
                "query_breakdown": self.slow_query_log.get_query_type_breakdown(),
                "recent_slow_queries": self.slow_query_log.get_slow_queries(limit=10),
            },
            "unified_alerts": self.get_unified_alerts(),
        }
