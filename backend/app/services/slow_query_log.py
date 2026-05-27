"""
Slow Query Log - Registro de tráfico
Consolida respuestas lentas de la base de datos para identificar cuellos de botella
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from enum import Enum

logger = logging.getLogger("energygrid")


class QuerySeverity(str, Enum):
    """Severidad de queries lentas"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SlowQueryLog:
    """Monitor y registro de queries lentas"""

    def __init__(self, slow_query_threshold_ms: float = 500):
        """
        Initialize Slow Query Log

        Args:
            slow_query_threshold_ms: Umbral de tiempo para considerar una query lenta (ms)
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.query_log = []
        self.max_history = 10000
        self.query_patterns = {}  # Agrupa queries similares
        self.stats = {
            "total_queries": 0,
            "slow_queries": 0,
            "average_time_ms": 0,
            "max_time_ms": 0,
        }

    def log_query(
        self,
        query: str,
        execution_time_ms: float,
        status: str = "success",
        rows_affected: int = 0,
        error: Optional[str] = None,
        query_type: str = "SELECT",
    ) -> Dict[str, Any]:
        """
        Registra la ejecución de una query

        Args:
            query: La query SQL
            execution_time_ms: Tiempo de ejecución en milisegundos
            status: Estado de ejecución (success, error)
            rows_affected: Filas afectadas
            error: Mensaje de error si aplica
            query_type: Tipo de query (SELECT, INSERT, UPDATE, DELETE)

        Returns:
            Registro de la query
        """
        timestamp = datetime.utcnow()
        is_slow = execution_time_ms > self.slow_query_threshold_ms

        severity = QuerySeverity.INFO
        if execution_time_ms > 2000:
            severity = QuerySeverity.CRITICAL
        elif execution_time_ms > 1000:
            severity = QuerySeverity.WARNING

        query_record = {
            "timestamp": timestamp.isoformat(),
            "query": query[:500],  # Limitar longitud
            "query_type": query_type,
            "execution_time_ms": round(execution_time_ms, 2),
            "is_slow": is_slow,
            "severity": severity,
            "status": status,
            "rows_affected": rows_affected,
            "error": error,
        }

        # Agregar al historial
        self.query_log.append(query_record)
        if len(self.query_log) > self.max_history:
            self.query_log.pop(0)

        # Actualizar estadísticas
        self._update_stats(execution_time_ms, is_slow)

        # Agrupar por patrón
        self._update_pattern_stats(query, execution_time_ms, is_slow)

        if is_slow:
            logger.warning(
                f"Slow query detected",
                extra={
                    "query_type": query_type,
                    "execution_time_ms": execution_time_ms,
                    "severity": severity,
                },
            )

        return query_record

    def _update_stats(self, execution_time_ms: float, is_slow: bool):
        """Actualiza estadísticas generales"""
        self.stats["total_queries"] += 1
        if is_slow:
            self.stats["slow_queries"] += 1

        # Calcular promedio
        total_time = sum(q["execution_time_ms"] for q in self.query_log)
        self.stats["average_time_ms"] = round(total_time / len(self.query_log), 2)

        # Máximo tiempo
        self.stats["max_time_ms"] = max(
            (q["execution_time_ms"] for q in self.query_log), default=0
        )

    def _update_pattern_stats(self, query: str, execution_time_ms: float, is_slow: bool):
        """Agrupa queries similares por patrón"""
        # Crear un patrón simplificado (primeras palabras de la query)
        pattern = " ".join(query.split()[:5])

        if pattern not in self.query_patterns:
            self.query_patterns[pattern] = {
                "pattern": pattern,
                "count": 0,
                "slow_count": 0,
                "total_time_ms": 0,
                "average_time_ms": 0,
                "max_time_ms": 0,
                "min_time_ms": float("inf"),
            }

        stats = self.query_patterns[pattern]
        stats["count"] += 1
        if is_slow:
            stats["slow_count"] += 1

        stats["total_time_ms"] += execution_time_ms
        stats["average_time_ms"] = round(stats["total_time_ms"] / stats["count"], 2)
        stats["max_time_ms"] = max(stats["max_time_ms"], execution_time_ms)
        stats["min_time_ms"] = min(stats["min_time_ms"], execution_time_ms)

    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene las queries más lentas"""
        slow = [q for q in self.query_log if q["is_slow"]]
        return sorted(slow, key=lambda x: x["execution_time_ms"], reverse=True)[:limit]

    def get_query_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales de queries"""
        if not self.query_log:
            return {
                "total_queries": 0,
                "slow_queries": 0,
                "slow_query_percentage": 0,
                "average_time_ms": 0,
                "max_time_ms": 0,
                "threshold_ms": self.slow_query_threshold_ms,
            }

        slow_percentage = round(
            (self.stats["slow_queries"] / self.stats["total_queries"]) * 100, 2
        )

        return {
            "total_queries": self.stats["total_queries"],
            "slow_queries": self.stats["slow_queries"],
            "slow_query_percentage": slow_percentage,
            "average_time_ms": self.stats["average_time_ms"],
            "max_time_ms": self.stats["max_time_ms"],
            "threshold_ms": self.slow_query_threshold_ms,
        }

    def get_bottlenecks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Identifica los cuellos de botella (queries más problemáticas)"""
        bottlenecks = sorted(
            self.query_patterns.values(),
            key=lambda x: (x["slow_count"], x["average_time_ms"]),
            reverse=True,
        )[:limit]

        return [
            {
                **bn,
                "slow_percentage": round((bn["slow_count"] / bn["count"]) * 100, 2),
                "impact_score": round(
                    (bn["slow_count"] * bn["average_time_ms"] / 1000), 2
                ),  # Multiplicar por frecuencia
            }
            for bn in bottlenecks
        ]

    def get_query_type_breakdown(self) -> Dict[str, Any]:
        """Obtiene desglose de queries por tipo"""
        breakdown = {}

        for query in self.query_log:
            q_type = query["query_type"]
            if q_type not in breakdown:
                breakdown[q_type] = {
                    "count": 0,
                    "slow_count": 0,
                    "average_time_ms": 0,
                    "total_time_ms": 0,
                }

            breakdown[q_type]["count"] += 1
            if query["is_slow"]:
                breakdown[q_type]["slow_count"] += 1
            breakdown[q_type]["total_time_ms"] += query["execution_time_ms"]

        # Calcular promedios
        for q_type in breakdown:
            breakdown[q_type]["average_time_ms"] = round(
                breakdown[q_type]["total_time_ms"] / breakdown[q_type]["count"], 2
            )

        return breakdown

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Genera alertas basadas en patrones de queries lentas"""
        alerts = []

        # Alert: Queries críticas
        critical_queries = [q for q in self.query_log if q["severity"] == QuerySeverity.CRITICAL]
        if critical_queries:
            latest_critical = critical_queries[-1]
            alerts.append({
                "type": "critical_query",
                "severity": "critical",
                "message": f"Query crítica detectada: {latest_critical['execution_time_ms']}ms",
                "query_type": latest_critical["query_type"],
                "execution_time_ms": latest_critical["execution_time_ms"],
            })

        # Alert: Aumento en queries lentas
        recent_queries = self.query_log[-100:] if len(self.query_log) > 100 else self.query_log
        if recent_queries:
            slow_count = sum(1 for q in recent_queries if q["is_slow"])
            slow_percentage = (slow_count / len(recent_queries)) * 100

            if slow_percentage > 10:
                alerts.append({
                    "type": "high_slow_query_rate",
                    "severity": "warning",
                    "message": f"Tasa alta de queries lentas: {slow_percentage:.1f}%",
                    "slow_percentage": round(slow_percentage, 2),
                })

        # Alert: Cuello de botella identificado
        bottlenecks = self.get_bottlenecks(limit=1)
        if bottlenecks:
            top_bottleneck = bottlenecks[0]
            if top_bottleneck["impact_score"] > 5:  # Arbitrary threshold
                alerts.append({
                    "type": "bottleneck_detected",
                    "severity": "warning",
                    "message": f"Cuello de botella en patrón: {top_bottleneck['pattern'][:50]}",
                    "pattern": top_bottleneck["pattern"],
                    "impact_score": top_bottleneck["impact_score"],
                })

        return alerts

    def get_recent_queries(self, minutes: int = 5, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene queries recientes dentro de X minutos"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        recent = [
            q for q in self.query_log
            if datetime.fromisoformat(q["timestamp"]) > cutoff_time
        ]

        return recent[:limit]

    def clear_old_logs(self, hours: int = 24):
        """Limpia logs antiguos"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        self.query_log = [
            q for q in self.query_log
            if datetime.fromisoformat(q["timestamp"]) > cutoff_time
        ]

        logger.info(f"Cleared query logs older than {hours} hours")
