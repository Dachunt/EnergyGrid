"""
Monitoring Routes - Endpoints API para el sistema de monitoreo
"""

from fastapi import APIRouter, Query
from app.services.monitoring_orchestrator import MonitoringOrchestrator

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Instancia global del orquestador
monitoring = None


def get_monitoring_instance() -> MonitoringOrchestrator:
    """Obtiene instancia global del monitoreo"""
    global monitoring
    if monitoring is None:
        monitoring = MonitoringOrchestrator()
    return monitoring


# ============== ENDPOINTS DE SALUD GENERAL ==============


@router.get("/health")
async def get_system_health():
    """Obtiene el estado general del sistema"""
    monitor = get_monitoring_instance()
    return monitor.get_system_health()


@router.get("/dashboard")
async def get_monitoring_dashboard():
    """Obtiene el dashboard completo de monitoreo"""
    monitor = get_monitoring_instance()
    return monitor.get_monitoring_dashboard()


@router.get("/report")
async def get_detailed_report():
    """Obtiene reporte detallado de monitoreo"""
    monitor = get_monitoring_instance()
    return monitor.get_detailed_report()


# ============== ENDPOINTS DE ALERTAS ==============


@router.get("/alerts")
async def get_alerts(severity: str = Query(None)):
    """Obtiene alertas unificadas de todos los monitores"""
    monitor = get_monitoring_instance()
    alerts = monitor.get_unified_alerts()

    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]

    return {
        "total": len(alerts),
        "alerts": alerts,
    }


# ============== ENDPOINTS DE MUNIN ==============


@router.get("/munin/metrics")
async def get_munin_metrics():
    """Obtiene las últimas métricas del sistema (Munin)"""
    monitor = get_monitoring_instance()
    return monitor.munin.metrics_history[-1] if monitor.munin.metrics_history else {}


@router.get("/munin/health")
async def get_munin_health():
    """Obtiene el score de salud del sistema"""
    monitor = get_monitoring_instance()
    return {
        "health_score": monitor.munin.get_health_score(),
        "alerts": monitor.munin.get_alerts(),
    }


@router.get("/munin/history")
async def get_munin_history(limit: int = Query(50, ge=1, le=500)):
    """Obtiene historial de métricas"""
    monitor = get_monitoring_instance()
    return {
        "metrics": monitor.munin.metrics_history[-limit:],
    }


# ============== ENDPOINTS DE PINGDOM ==============


@router.get("/pingdom/status")
async def get_pingdom_status():
    """Obtiene estado de todos los endpoints (Pingdom)"""
    monitor = get_monitoring_instance()
    return monitor.pingdom.get_all_status()


@router.get("/pingdom/endpoints/{endpoint_name}")
async def get_endpoint_status(endpoint_name: str):
    """Obtiene estado detallado de un endpoint específico"""
    monitor = get_monitoring_instance()
    return monitor.pingdom.get_endpoint_status(endpoint_name)


@router.get("/pingdom/uptime")
async def get_uptime_report(hours: int = Query(24, ge=1, le=720)):
    """Obtiene reporte de disponibilidad (uptime)"""
    monitor = get_monitoring_instance()
    return monitor.pingdom.get_uptime_report(hours=hours)


@router.get("/pingdom/incidents")
async def get_incidents():
    """Obtiene lista de incidentes detectados"""
    monitor = get_monitoring_instance()
    return {
        "incidents": monitor.pingdom.get_incidents(),
    }


# ============== ENDPOINTS DE SLOW QUERY LOG ==============


@router.get("/queries/statistics")
async def get_query_statistics():
    """Obtiene estadísticas de queries de base de datos"""
    monitor = get_monitoring_instance()
    return monitor.slow_query_log.get_query_statistics()


@router.get("/queries/slow")
async def get_slow_queries(limit: int = Query(50, ge=1, le=500)):
    """Obtiene las queries más lentas detectadas"""
    monitor = get_monitoring_instance()
    return {
        "slow_queries": monitor.slow_query_log.get_slow_queries(limit=limit),
    }


@router.get("/queries/bottlenecks")
async def get_bottlenecks(limit: int = Query(10, ge=1, le=100)):
    """Identifica cuellos de botella en queries"""
    monitor = get_monitoring_instance()
    return {
        "bottlenecks": monitor.slow_query_log.get_bottlenecks(limit=limit),
    }


@router.get("/queries/breakdown")
async def get_query_breakdown():
    """Obtiene desglose de queries por tipo"""
    monitor = get_monitoring_instance()
    return monitor.slow_query_log.get_query_type_breakdown()


@router.get("/queries/recent")
async def get_recent_queries(
    minutes: int = Query(5, ge=1, le=60),
    limit: int = Query(50, ge=1, le=500),
):
    """Obtiene queries recientes dentro de X minutos"""
    monitor = get_monitoring_instance()
    return {
        "recent_queries": monitor.slow_query_log.get_recent_queries(
            minutes=minutes, limit=limit
        ),
    }


# ============== ENDPOINTS DE CONTROL ==============


@router.post("/start")
async def start_monitoring():
    """Inicia monitoreo continuo"""
    monitor = get_monitoring_instance()
    await monitor.initialize_monitoring()
    await monitor.start_continuous_monitoring()
    return {"status": "monitoring started"}


@router.post("/stop")
async def stop_monitoring():
    """Detiene monitoreo continuo"""
    monitor = get_monitoring_instance()
    await monitor.stop_continuous_monitoring()
    return {"status": "monitoring stopped"}


@router.get("/status")
async def get_monitoring_status():
    """Obtiene estado del sistema de monitoreo"""
    monitor = get_monitoring_instance()
    return {
        "monitoring_active": monitor.monitoring_active,
        "munin_metrics_count": len(monitor.munin.metrics_history),
        "pingdom_checks_count": len(monitor.pingdom.uptime_history),
        "database_queries_logged": monitor.slow_query_log.stats["total_queries"],
    }
