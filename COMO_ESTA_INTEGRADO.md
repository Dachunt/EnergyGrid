# 📊 VISUALIZACIÓN DE LA INTEGRACIÓN DEL SISTEMA DE MONITOREO

## 1️⃣ PUNTO DE ENTRADA - main.py (Líneas 10, 26, 31, 71-83)

```
┌─────────────────────────────────────────────────────────────┐
│                    APLICACIÓN FASTAPI                       │
│                     (main.py)                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Línea 10:  Importar MonitoringOrchestrator                │
│  ├─ from app.services.monitoring_orchestrator import...   │
│                                                             │
│  Línea 26:  Variable global                                │
│  ├─ monitoring_orchestrator = None                         │
│                                                             │
│  Línea 31:  Registrar rutas de monitoreo                   │
│  ├─ app.include_router(monitoring.router)                  │
│                                                             │
│  Líneas 71-83: STARTUP (Inicialización automática)         │
│  ├─ 1. Conectar base de datos                             │
│  ├─ 2. Crear MonitoringOrchestrator()                     │
│  ├─ 3. await orchestrator.initialize_monitoring()         │
│  └─ 4. await orchestrator.start_continuous_monitoring()   │
│                                                             │
│  Líneas 86-95: SHUTDOWN (Limpieza)                         │
│  ├─ 1. Detener loops de monitoreo                         │
│  └─ 2. Cerrar conexiones                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ FLUJO DE INICIALIZACIÓN AL ARRANCAR

```
STARTUP (Automático cuando ejecutas: uvicorn app.main:app --reload)
│
├─ 📍 main.py:71-83 (@app.on_event("startup"))
│  │
│  ├─ await init_db(app)
│  │  └─ Conecta a PostgreSQL
│  │
│  ├─ monitoring_orchestrator = MonitoringOrchestrator()
│  │  │
│  │  ├─ Crea instancia de Munin
│  │  ├─ Crea instancia de Pingdom  
│  │  ├─ Crea instancia de Slow Query Log
│  │  └─ Inicializa variables de estado
│  │
│  ├─ await orchestrator.initialize_monitoring()
│  │  │
│  │  └─ Configura endpoints de Pingdom
│  │     └─ Agrega endpoint: http://localhost:8000/health
│  │
│  └─ await orchestrator.start_continuous_monitoring()
│     │
│     ├─ Inicia Munin Loop
│     │  └─ Cada 30 segundos → collect_metrics()
│     │
│     └─ Inicia Pingdom Loop
│        └─ Cada 60 segundos → run_checks()
│
└─ ✅ Sistema funcionando
```

---

## 3️⃣ ARQUITECTURA DE LOS TRES MONITORES

```
                    MonitoringOrchestrator
                    (monitoring_orchestrator.py)
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
    🔵 MUNIN          🟠 PINGDOM          🟢 SLOW QUERY LOG
    (munin_monitor.py) (pingdom_guard.py) (slow_query_log.py)
        │                   │                   │
        │                   │                   │
    Recopila:          Verifica:            Registra:
    • CPU %            • Endpoints          • Queries SQL
    • Memoria %        • Tiempo respuesta   • Tiempo ejecución
    • Disco %          • Disponibilidad     • Cuellos botella
    • Red              • Uptime %           • Patrones
    • Procesos         • Incidentes         • Severity
    • Carga                                 • Tipo (SELECT/INSERT)
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    Alertas Unificadas
                    Dashboard Consolidado
                    Health Score Global
```

---

## 4️⃣ DÓNDE Y CÓMO FUNCIONA CADA COMPONENTE

### 🔵 MUNIN - backend/app/services/munin_monitor.py

**Ubicación**: `backend/app/services/munin_monitor.py` (1100+ líneas)

**Función**: Monitorea el sistema en tiempo real

**Cómo funciona**:
```python
# Se instancia en MonitoringOrchestrator
self.munin = MuninMonitor()

# Loop automático cada 30 segundos
async def _munin_loop(self):
    while self.monitoring_active:
        self.munin.collect_metrics()  # ← Recopila métricas
        await asyncio.sleep(30)

# Métodos principales:
munin.collect_metrics()      → Recopila CPU, Mem, Disco, Red, etc.
munin.get_health_score()     → Calcula score 0-100
munin.get_alerts()           → Genera alertas automáticas
munin.metrics_history[-1]    → Últimas métricas
```

**Qué monitorea**:
```
• CPU: Porcentaje general, por núcleo, carga 1m/5m/15m
• Memoria: Total, disponible, usado, porcentaje
• Disco: Capacidad, uso, libre, porcentaje
• Red: Bytes entrada/salida, paquetes, errores
• Procesos: Total, top 5 por consumo memoria
• Sistema: Carga general, health score
```

---

### 🟠 PINGDOM - backend/app/services/pingdom_guard.py

**Ubicación**: `backend/app/services/pingdom_guard.py` (550+ líneas)

**Función**: Verifica disponibilidad cada minuto

**Cómo funciona**:
```python
# Se instancia en MonitoringOrchestrator
self.pingdom = PingdomGuard(check_interval=60)

# Agregar endpoints a monitorear
orchestrator.pingdom.add_endpoint(
    "main_api",
    "http://localhost:8000/health",
    timeout=5,
    expected_status=200
)

# Loop automático cada 60 segundos
async def _pingdom_loop(self):
    while self.monitoring_active:
        await self.pingdom.run_checks()  # ← Verifica endpoints
        await asyncio.sleep(60)

# Métodos principales:
pingdom.run_checks()           → Verifica todos los endpoints
pingdom.get_all_status()       → Estado actual
pingdom.get_uptime_report()    → % disponibilidad en período
pingdom.get_incidents()        → Cambios de estado detectados
```

**Qué verifica**:
```
• Estado del endpoint (UP/DOWN)
• Tiempo de respuesta (ms)
• Status code HTTP
• Historial de uptime
• Incidentes (cambios de estado)
```

---

### 🟢 SLOW QUERY LOG - backend/app/services/slow_query_log.py

**Ubicación**: `backend/app/services/slow_query_log.py` (650+ líneas)

**Función**: Registra y analiza queries lentas

**Cómo funciona**:
```python
# Se instancia en MonitoringOrchestrator
self.slow_query_log = SlowQueryLog(slow_query_threshold_ms=500)

# Se registra cuando se ejecuta una query
slow_query_log.log_query(
    query="SELECT * FROM consumption WHERE ...",
    execution_time_ms=1250,
    status="success",
    rows_affected=100,
    query_type="SELECT"
)

# Métodos principales:
slow_query_log.log_query()           → Registra una query
slow_query_log.get_slow_queries()    → Queries más lentas
slow_query_log.get_bottlenecks()     → Cuellos de botella
slow_query_log.get_query_statistics()→ Estadísticas generales
slow_query_log.get_alerts()          → Alertas de queries críticas
```

**Qué registra**:
```
• Tiempo de ejecución
• Tipo de query (SELECT, INSERT, UPDATE, DELETE)
• Filas afectadas
• Patrones similares
• Impact score
• Severity (Info, Warning, Critical)
```

---

## 5️⃣ ORQUESTADOR - Coordinación Central

**Ubicación**: `backend/app/services/monitoring_orchestrator.py`

**Función**: Unifica los tres monitores

```python
class MonitoringOrchestrator:
    def __init__(self):
        self.munin = MuninMonitor()              # ← Instancia Munin
        self.pingdom = PingdomGuard()             # ← Instancia Pingdom
        self.slow_query_log = SlowQueryLog()      # ← Instancia Slow Query Log

    # Métodos principales:
    get_system_health()          → Health score global 0-100
    get_unified_alerts()         → Alertas de los 3 sistemas
    get_monitoring_dashboard()   → Dashboard consolidado
    get_detailed_report()        → Reporte completo
    log_database_query()         → Registra queries
```

---

## 6️⃣ RUTAS API - Cómo acceder a los datos

**Ubicación**: `backend/app/routes/monitoring.py` (350+ líneas)

```
┌─────────────────────────────────────────────────────────┐
│            ENDPOINTS API DISPONIBLES                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  GET /api/monitoring/health                            │
│  └─ Retorna: {health_score, components, status}       │
│                                                         │
│  GET /api/monitoring/dashboard                         │
│  └─ Retorna: Dashboard completo unificado             │
│                                                         │
│  GET /api/monitoring/munin/metrics                    │
│  └─ Retorna: Últimas métricas de sistema              │
│                                                         │
│  GET /api/monitoring/pingdom/status                   │
│  └─ Retorna: Estado de todos los endpoints            │
│                                                         │
│  GET /api/monitoring/queries/slow                     │
│  └─ Retorna: Queries más lentas detectadas            │
│                                                         │
│  GET /api/monitoring/alerts?severity=critical         │
│  └─ Retorna: Alertas filtradas por severidad          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 7️⃣ HELPERS DE INTEGRACIÓN - Cómo registrar queries

**Ubicación**: `backend/app/services/db_query_monitor.py`

**3 formas de registrar queries automáticamente**:

### Opción 1: Función Helper
```python
from app.services.db_query_monitor import execute_query_monitored

result = await execute_query_monitored(
    "SELECT * FROM consumption WHERE id = $1",
    district_id,
    pool=app.state.db,
    query_type="SELECT"
)
# ✅ La query se registra automáticamente
```

### Opción 2: Context Manager
```python
from app.services.db_query_monitor import DatabaseQueryMonitor

async with DatabaseQueryMonitor("SELECT ...", pool=app.state.db):
    result = await pool.fetch("SELECT ...")
# ✅ La query se registra automáticamente
```

### Opción 3: Decorador
```python
from app.services.db_query_monitor import monitored_query

@monitored_query(query_type="SELECT")
async def get_consumption_data():
    return await pool.fetch("SELECT * FROM consumption")
# ✅ La query se registra automáticamente
```

---

## 8️⃣ FLUJO COMPLETO DE EJECUCIÓN

```
Usuario hace una solicitud
│
└─ HTTP Request → http://localhost:8000/api/consumption/1
   │
   ├─ middleware("http") - main.py:34-48
   │  └─ Mide tiempo de request
   │
   ├─ monitoring_middleware - main.py:51-68
   │  └─ Prepara orquestador si no existe
   │
   ├─ Ruta de negocio (ej: get_consumption)
   │  │
   │  └─ Query a base de datos
   │     │
   │     └─ execute_query_monitored()  ← INTEGRACIÓN
   │        │
   │        ├─ Ejecuta: await pool.fetch(...)
   │        │
   │        └─ Registra en Slow Query Log
   │           ├─ Tiempo de ejecución
   │           ├─ Tipo de query
   │           ├─ Severidad (Slow/Warning/Critical)
   │           └─ Alertas si aplica
   │
   └─ HTTP Response (200 OK)
      │
      └─ Logger registra el request (duración_ms)

En Background (Asyncio Tasks):
│
├─ Munin Loop (cada 30s)
│  └─ collect_metrics() → CPU, Mem, Disco, etc.
│
└─ Pingdom Loop (cada 60s)
   └─ run_checks() → Verifica /health endpoint
```

---

## 9️⃣ DÓNDE VER LOS DATOS

### Terminal (Logs)
```bash
# Logs en tiempo real
✓ Request completed - method=GET path=/api/consumption/1 duration_ms=125
✓ Munin metrics collected
✓ Slow query detected - execution_time_ms=1250
✓ Pingdom check: main_api status=up response_time_ms=45
```

### API HTTP
```bash
# Ver dashboard
curl http://localhost:8000/api/monitoring/dashboard | jq

# Ver health score
curl http://localhost:8000/api/monitoring/health | jq '.overall_health'

# Ver queries lentas
curl http://localhost:8000/api/monitoring/queries/slow | jq

# Ver alertas críticas
curl http://localhost:8000/api/monitoring/alerts?severity=critical | jq
```

### Código
```python
# Acceder programáticamente
from app.routes.monitoring import get_monitoring_instance

monitor = get_monitoring_instance()
health = monitor.get_system_health()
print(f"Health Score: {health['overall_health']}")
```

---

## 🔟 ARCHIVOS CLAVE Y SUS RESPONSABILIDADES

```
main.py (99 líneas)
├─ Línea 10: Importar MonitoringOrchestrator
├─ Línea 26: Variable global
├─ Línea 31: Registrar router de monitoreo
├─ Línea 71-83: STARTUP → Inicializar
└─ Línea 86-95: SHUTDOWN → Limpiar

services/
├─ munin_monitor.py (1100 líneas)
│  └─ Clase MuninMonitor → Métricas del sistema
│
├─ pingdom_guard.py (550 líneas)
│  └─ Clase PingdomGuard → Disponibilidad
│
├─ slow_query_log.py (650 líneas)
│  └─ Clase SlowQueryLog → Queries lentas
│
├─ monitoring_orchestrator.py (400 líneas)
│  └─ Clase MonitoringOrchestrator → Coordinación
│
├─ monitoring_config.py (500 líneas)
│  └─ Configuración centralizada y presets
│
└─ db_query_monitor.py (250 líneas)
   └─ Helpers para integración automática

routes/
├─ monitoring.py (350 líneas)
│  └─ 20+ endpoints API
│
└─ monitoring_examples.py (200 líneas)
   └─ Ejemplos de uso
```

---

## 1️⃣1️⃣ RESUMEN DE INTEGRACIÓN

```
┌──────────────────────────────────────────────────────────┐
│  CUANDO ARRANCA LA APP (main.py:71-83)                  │
├──────────────────────────────────────────────────────────┤
│ 1. Crea MonitoringOrchestrator                          │
│ 2. Instancia Munin, Pingdom, SlowQueryLog               │
│ 3. Inicia loops de background                           │
│ 4. Registra rutas API                                   │
│ 5. Listo para monitorear                                │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  CUANDO LLEGA UNA REQUEST                               │
├──────────────────────────────────────────────────────────┤
│ 1. Middleware registra en logs                          │
│ 2. Si hay query → Slow Query Log registra               │
│ 3. Responde al usuario                                  │
│ 4. Datos disponibles en /api/monitoring/*               │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  EN BACKGROUND (Asyncio)                                │
├──────────────────────────────────────────────────────────┤
│ • Cada 30s: Munin recopila métricas                    │
│ • Cada 60s: Pingdom verifica disponibilidad            │
│ • Siempre: Alertas se generan automáticamente          │
└──────────────────────────────────────────────────────────┘
```

---

Este es el sistema de monitoreo completamente integrado en EnergyGrid.
