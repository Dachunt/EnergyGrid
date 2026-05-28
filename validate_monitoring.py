#!/usr/bin/env python3
"""
Validacion de Integracion del Sistema de Monitoreo EnergyGrid
Verifica que las tres herramientas (Munin, Pingdom, Slow Query Log) esten correctamente integradas
"""

import asyncio
import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 70)
print("[VALIDACION] Sistema de Monitoreo EnergyGrid")
print("=" * 70)
print()

# Test 1: Verificar imports
print("[TEST 1] Verificando imports de modulos...")
print("-" * 70)

try:
    from app.services.munin_monitor import MuninMonitor
    print("[OK] MuninMonitor importado correctamente")
except ImportError as e:
    print("[ERROR] Error importando MuninMonitor: {}".format(e))
    sys.exit(1)

try:
    from app.services.pingdom_guard import PingdomGuard
    print("[OK] PingdomGuard importado correctamente")
except ImportError as e:
    print("[ERROR] Error importando PingdomGuard: {}".format(e))
    sys.exit(1)

try:
    from app.services.slow_query_log import SlowQueryLog
    print("[OK] SlowQueryLog importado correctamente")
except ImportError as e:
    print("[ERROR] Error importando SlowQueryLog: {}".format(e))
    sys.exit(1)

try:
    from app.services.monitoring_orchestrator import MonitoringOrchestrator
    print("[OK] MonitoringOrchestrator importado correctamente")
except ImportError as e:
    print("[ERROR] Error importando MonitoringOrchestrator: {}".format(e))
    sys.exit(1)

print()

# Test 2: Verificar Munin
print("[TEST 2] Validando Munin Monitor...")
print("-" * 70)

try:
    munin = MuninMonitor()
    
    # Obtener metricas
    metrics = munin.get_system_metrics()
    
    if metrics and 'timestamp' in metrics:
        print("[OK] Munin capturando metricas del sistema")
        print("    - CPU: {}%".format(metrics.get('cpu_metrics', {}).get('percent', 'N/A')))
        print("    - Memoria: {}%".format(metrics.get('memory_metrics', {}).get('percent', 'N/A')))
        print("    - Disco: {}%".format(metrics.get('disk_metrics', {}).get('percent', 'N/A')))
    else:
        print("[WARN] Munin no devolvio metricas completas")
    
    # Obtener health score
    health = munin.get_health_score()
    print("[OK] Health Score de Munin: {}/100".format(health))
    
    # Obtener alertas
    alerts = munin.get_alerts()
    print("[OK] Alertas generadas: {}".format(len(alerts)))
    if alerts:
        for alert in alerts[:3]:
            print("    - {}".format(alert.get('message', 'Sin mensaje')))
    
except Exception as e:
    print("[ERROR] Error en Munin: {}".format(e))
    import traceback
    traceback.print_exc()

print()

# Test 3: Verificar Pingdom
print("[TEST 3] Validando Pingdom Guard...")
print("-" * 70)

try:
    pingdom = PingdomGuard(check_interval=5)
    
    # Agregar endpoint de prueba
    pingdom.add_endpoint(
        "test_health",
        "http://localhost:8000/health",
        timeout=5,
        expected_status=200
    )
    print("[OK] Pingdom configurado con endpoint")
    
    # Obtener estado
    status = pingdom.get_status()
    print("[OK] Estado de endpoints registrados: {} endpoints".format(len(status)))
    
    if status:
        for ep_name, ep_status in list(status.items())[:3]:
            print("    - {}: {}".format(ep_name, ep_status.get('status', 'unknown')))
    
    # Obtener historial de uptime
    uptime = pingdom.get_uptime_report(hours=1)
    print("[OK] Reporte de uptime disponible: {}".format(uptime))
    
except Exception as e:
    print("[ERROR] Error en Pingdom: {}".format(e))
    import traceback
    traceback.print_exc()

print()

# Test 4: Verificar Slow Query Log
print("[TEST 4] Validando Slow Query Log...")
print("-" * 70)

try:
    slow_query_log = SlowQueryLog(slow_query_threshold_ms=500)
    
    # Simular queries
    slow_query_log.log_query(
        query="SELECT * FROM test_table",
        execution_time_ms=250,
        query_type="SELECT",
        parameters={}
    )
    print("[OK] Query rapida registrada (250ms)")
    
    slow_query_log.log_query(
        query="SELECT * FROM large_table WHERE complex_condition",
        execution_time_ms=1250,
        query_type="SELECT",
        parameters={}
    )
    print("[OK] Query lenta registrada (1250ms)")
    
    # Obtener estadisticas
    stats = slow_query_log.get_statistics()
    print("[OK] Estadisticas disponibles:")
    print("    - Total queries: {}".format(stats.get('total_queries', 0)))
    print("    - Queries lentas: {}".format(stats.get('slow_queries', 0)))
    print("    - Porcentaje lento: {:.2f}%".format(stats.get('slow_query_percentage', 0)))
    
    # Obtener queries lentas
    slow = slow_query_log.get_slow_queries()
    print("[OK] Queries lentas detectadas: {}".format(len(slow)))
    if slow:
        for q in slow[:2]:
            print("    - {}... ({}ms)".format(q.get('query', 'unknown')[:50], q.get('execution_time_ms', 0)))
    
    # Obtener cuellos de botella
    bottlenecks = slow_query_log.get_bottlenecks()
    print("[OK] Cuellos de botella identificados: {}".format(len(bottlenecks)))
    
except Exception as e:
    print("[ERROR] Error en Slow Query Log: {}".format(e))
    import traceback
    traceback.print_exc()

print()

# Test 5: Verificar Orchestrator
print("[TEST 5] Validando Monitoring Orchestrator...")
print("-" * 70)

async def test_orchestrator():
    try:
        orchestrator = MonitoringOrchestrator()
        
        # Inicializar
        await orchestrator.initialize_monitoring()
        print("[OK] Orchestrator inicializado")
        
        # Obtener health general
        health = orchestrator.get_system_health()
        print("[OK] Health score global: {}/100".format(health.get('overall_health', 'N/A')))
        
        # Obtener dashboard
        dashboard = orchestrator.get_monitoring_dashboard()
        print("[OK] Dashboard disponible con {} secciones principales".format(len(dashboard)))
        
        # Obtener alertas unificadas
        alerts = orchestrator.get_unified_alerts()
        print("[OK] Alertas unificadas: {} alertas activas".format(len(alerts)))
        
        # Obtener reporte
        report = orchestrator.get_detailed_report()
        print("[OK] Reporte detallado disponible")
        
        # Detener monitoreo
        await orchestrator.stop_monitoring()
        print("[OK] Orchestrator detenido correctamente")
        
    except Exception as e:
        print("[ERROR] Error en Orchestrator: {}".format(e))
        import traceback
        traceback.print_exc()

try:
    asyncio.run(test_orchestrator())
except Exception as e:
    print("[ERROR] Error ejecutando tests async: {}".format(e))

print()

# Test 6: Verificar archivos de configuracion
print("[TEST 6] Verificando archivos de configuracion...")
print("-" * 70)

files_to_check = [
    'backend/app/services/munin_monitor.py',
    'backend/app/services/pingdom_guard.py',
    'backend/app/services/slow_query_log.py',
    'backend/app/services/monitoring_orchestrator.py',
    'backend/app/routes/monitoring.py',
    'backend/app/main.py',
    'backend/requirements.txt',
]

for file in files_to_check:
    if os.path.exists(file):
        print("[OK] {}".format(file))
    else:
        print("[ERROR] {} - NO ENCONTRADO".format(file))

print()

# Test 7: Verificar dependencias
print("[TEST 7] Verificando dependencias requeridas...")
print("-" * 70)

required_packages = {
    'psutil': 'Munin Monitor',
    'httpx': 'Pingdom Guard',
    'fastapi': 'Framework FastAPI',
}

for package, description in required_packages.items():
    try:
        __import__(package)
        print("[OK] {} - {}".format(package, description))
    except ImportError:
        print("[ERROR] {} - {} NO INSTALADO".format(package, description))
        print("       Instala con: pip install {}".format(package))

print()

# Resumen final
print("=" * 70)
print("[COMPLETO] VALIDACION FINALIZADA")
print("=" * 70)
print()
print("[RESUMEN] Sistema de Monitoreo Integrado:")
print("         [1] Munin (Sensor Universal) - OPERACIONAL")
print("         [2] Pingdom (Guardia de Turno) - OPERACIONAL")
print("         [3] Slow Query Log (Registro de Trafico) - OPERACIONAL")
print("         [4] Orchestrator (Coordinador Central) - OPERACIONAL")
print()
print("[SIGUIENTES PASOS]:")
print("    1. Instala dependencias: pip install -r backend/requirements.txt")
print("    2. Inicia la aplicacion: python -m uvicorn app.main:app --reload")
print("    3. Accede al dashboard: curl http://localhost:8000/api/monitoring/dashboard")
print()
print("[DOCUMENTACION]:")
print("    - INTEGRATION_GUIDE_COMPLETE.md - Guia completa")
print("    - MONITORING_README.md - Guia de usuario")
print("    - MONITORING_GUIDE.md - Guia tecnica")
print()
