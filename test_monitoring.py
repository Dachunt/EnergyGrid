#!/usr/bin/env python3
"""
Script de validación del sistema de monitoreo
Verifica que todos los componentes funcionen correctamente
"""

import asyncio
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.munin_monitor import MuninMonitor
from app.services.pingdom_guard import PingdomGuard
from app.services.slow_query_log import SlowQueryLog
from app.services.monitoring_orchestrator import MonitoringOrchestrator
from app.services.monitoring_config import MonitoringPresets


def test_munin():
    """Valida Munin Monitor"""
    print("\n" + "="*50)
    print("🔵 TESTING MUNIN MONITOR")
    print("="*50)
    
    munin = MuninMonitor()
    
    # Recopilar métricas
    metrics = munin.collect_metrics()
    
    print(f"✓ Métricas recopiladas")
    print(f"  - CPU: {metrics['cpu']['percent']:.1f}%")
    print(f"  - Memoria: {metrics['memory']['percent']:.1f}%")
    print(f"  - Disco: {metrics['disk']['percent']:.1f}%")
    print(f"  - Procesos: {metrics['processes']['total_processes']}")
    print(f"  - Carga sistema: {metrics['system_load']['load_1m']:.2f}")
    
    # Health score
    health = munin.get_health_score()
    print(f"✓ Health score: {health:.1f}/100")
    
    # Alertas
    alerts = munin.get_alerts()
    print(f"✓ Alertas: {len(alerts)} detectadas")
    for alert in alerts:
        print(f"  - [{alert['severity']}] {alert['message']}")
    
    return True


def test_pingdom():
    """Valida Pingdom Guard"""
    print("\n" + "="*50)
    print("🟠 TESTING PINGDOM GUARD")
    print("="*50)
    
    pingdom = PingdomGuard(check_interval=5)
    
    # Agregar endpoint
    pingdom.add_endpoint(
        "test_endpoint",
        "https://httpbin.org/status/200",
        timeout=5,
        expected_status=200
    )
    print("✓ Endpoint agregado: test_endpoint")
    
    # Verificar (nota: requiere conexión)
    try:
        import httpx
        print("✓ Librería httpx disponible")
        print("  (Checks requieren conexión a internet - skipeado para tests locales)")
    except ImportError:
        print("⚠ httpx no disponible - instalar: pip install httpx")
    
    # Probar métodos
    status = pingdom.get_all_status()
    print(f"✓ Estado general: {status['overall_status']}")
    
    uptime = pingdom.get_uptime_report(hours=1)
    print(f"✓ Reporte uptime: {uptime['uptime_percentage']}%")
    
    return True


def test_slow_query_log():
    """Valida Slow Query Log"""
    print("\n" + "="*50)
    print("🟢 TESTING SLOW QUERY LOG")
    print("="*50)
    
    sql_log = SlowQueryLog(slow_query_threshold_ms=100)
    
    # Registrar queries de prueba
    sql_log.log_query(
        query="SELECT * FROM consumption WHERE id = $1",
        execution_time_ms=50,
        status="success",
        rows_affected=10,
        query_type="SELECT"
    )
    print("✓ Query rápida registrada (50ms)")
    
    sql_log.log_query(
        query="SELECT * FROM consumption WHERE district_id IN (SELECT id FROM districts)",
        execution_time_ms=1500,
        status="success",
        rows_affected=100,
        query_type="SELECT"
    )
    print("✓ Query lenta registrada (1500ms)")
    
    sql_log.log_query(
        query="INSERT INTO logs VALUES (...)",
        execution_time_ms=200,
        status="success",
        rows_affected=1,
        query_type="INSERT"
    )
    print("✓ Query INSERT registrada (200ms)")
    
    # Estadísticas
    stats = sql_log.get_query_statistics()
    print(f"✓ Estadísticas:")
    print(f"  - Total queries: {stats['total_queries']}")
    print(f"  - Queries lentas: {stats['slow_queries']}")
    print(f"  - % lento: {stats['slow_query_percentage']}%")
    print(f"  - Tiempo promedio: {stats['average_time_ms']:.1f}ms")
    
    # Slowest queries
    slow = sql_log.get_slow_queries(limit=5)
    print(f"✓ Queries lentas: {len(slow)}")
    for q in slow:
        print(f"  - {q['execution_time_ms']:.1f}ms: {q['query'][:50]}...")
    
    # Desglose por tipo
    breakdown = sql_log.get_query_type_breakdown()
    print(f"✓ Desglose por tipo:")
    for q_type, data in breakdown.items():
        print(f"  - {q_type}: {data['count']} queries ({data['average_time_ms']:.1f}ms avg)")
    
    # Cuellos de botella
    bottlenecks = sql_log.get_bottlenecks(limit=5)
    print(f"✓ Cuellos de botella: {len(bottlenecks)}")
    
    # Alertas
    alerts = sql_log.get_alerts()
    print(f"✓ Alertas: {len(alerts)}")
    for alert in alerts:
        print(f"  - [{alert['severity']}] {alert['message']}")
    
    return True


async def test_orchestrator():
    """Valida Monitoring Orchestrator"""
    print("\n" + "="*50)
    print("🎯 TESTING MONITORING ORCHESTRATOR")
    print("="*50)
    
    orchestrator = MonitoringOrchestrator()
    
    # Inicializar
    await orchestrator.initialize_monitoring()
    print("✓ Orchestrator inicializado")
    
    # Recopilar una métrica de cada monitor
    munin_metric = orchestrator.munin.collect_metrics()
    print(f"✓ Munin: {len(munin_metric)} campos")
    
    # Log de query de prueba
    orchestrator.log_database_query(
        query="SELECT * FROM test",
        execution_time_ms=250,
        status="success",
        rows_affected=10
    )
    print("✓ Query registrada")
    
    # Health check unificado
    health = orchestrator.get_system_health()
    print(f"✓ Health score: {health['overall_health']:.1f}/100")
    print(f"  - Status: {health['status']}")
    print(f"  - System: {health['components']['system_health']:.1f}")
    print(f"  - Availability: {health['components']['availability']}")
    print(f"  - Database: {health['components']['database_performance']:.1f}")
    
    # Alertas unificadas
    alerts = orchestrator.get_unified_alerts()
    print(f"✓ Alertas unificadas: {len(alerts)}")
    
    # Dashboard
    dashboard = orchestrator.get_monitoring_dashboard()
    print(f"✓ Dashboard generado")
    print(f"  - CPU: {dashboard['system_metrics']['cpu_percent']:.1f}%")
    print(f"  - Memory: {dashboard['system_metrics']['memory_percent']:.1f}%")
    print(f"  - Alerts: {dashboard['alert_count']}")
    
    return True


def test_config():
    """Valida Configuración"""
    print("\n" + "="*50)
    print("⚙️  TESTING CONFIGURATION")
    print("="*50)
    
    # Test presets
    dev_config = MonitoringPresets.development()
    print(f"✓ Development preset: {dev_config.munin.max_history_records} records")
    
    prod_config = MonitoringPresets.production()
    print(f"✓ Production preset: {prod_config.munin.max_history_records} records")
    
    minimal_config = MonitoringPresets.minimal()
    print(f"✓ Minimal preset: {minimal_config.munin.max_history_records} records")
    
    aggressive_config = MonitoringPresets.aggressive()
    print(f"✓ Aggressive preset: {aggressive_config.munin.max_history_records} records")
    
    return True


async def main():
    """Ejecuta todos los tests"""
    print("\n" + "🚀 "*20)
    print("VALIDACIÓN DEL SISTEMA DE MONITOREO - EnergyGrid")
    print("🚀 "*20)
    
    tests = [
        ("Munin", test_munin, False),
        ("Pingdom", test_pingdom, False),
        ("Slow Query Log", test_slow_query_log, False),
        ("Orchestrator", test_orchestrator, True),
        ("Configuration", test_config, False),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func, is_async in tests:
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"\n✅ {name}: PASSED")
            else:
                failed += 1
                print(f"\n❌ {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name}: ERROR - {e}")
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE TESTS")
    print("="*50)
    print(f"✅ Pasados: {passed}")
    print(f"❌ Fallidos: {failed}")
    print(f"📈 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ¡Todos los tests pasaron!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) fallaron")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
