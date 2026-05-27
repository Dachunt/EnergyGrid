# 🎯 DIAGRAMA VISUAL RÁPIDO - Cómo Está Integrado

## FLUJO GENERAL

```
USUARIO INICIA APP
      │
      ▼
┌─────────────────────────────────────────┐
│   main.py (@app.on_event("startup"))    │  ← main.py:71-83
│                                         │
│  1. await init_db(app)                  │
│     ▼                                   │
│  2. monitoring_orchestrator =           │
│     MonitoringOrchestrator()            │
│     │                                   │
│     ├─ self.munin = MuninMonitor()      │
│     ├─ self.pingdom = PingdomGuard()    │
│     └─ self.slow_query_log = ...        │
│     ▼                                   │
│  3. await orchestrator                  │
│     .initialize_monitoring()            │
│     ▼                                   │
│  4. await orchestrator                  │
│     .start_continuous_monitoring()      │
│     │                                   │
│     ├─ Inicia _munin_loop (cada 30s)   │
│     └─ Inicia _pingdom_loop (cada 60s) │
│                                         │
└─────────────────────────────────────────┘
      │
      ▼
   ✅ APP LISTA PARA MONITOREAR
```

---

## DÓNDE ESTÁ CADA COMPONENTE

```
📁 PROYECTO
│
├─ 🔵 MUNIN
│  └─ backend/app/services/munin_monitor.py (1100 líneas)
│     ├─ Función: Mide sistema en tiempo real
│     ├─ Cada 30s: collect_metrics()
│     ├─ Qué mide: CPU, Mem, Disco, Red, Procesos
│     └─ Acceso: /api/monitoring/munin/*
│
├─ 🟠 PINGDOM
│  └─ backend/app/services/pingdom_guard.py (550 líneas)
│     ├─ Función: Verifica disponibilidad
│     ├─ Cada 60s: run_checks()
│     ├─ Qué verifica: Endpoints HTTP
│     └─ Acceso: /api/monitoring/pingdom/*
│
├─ 🟢 SLOW QUERY LOG
│  └─ backend/app/services/slow_query_log.py (650 líneas)
│     ├─ Función: Registra queries lentas
│     ├─ Tiempo real: log_query()
│     ├─ Qué registra: Queries, tiempos, cuellos
│     └─ Acceso: /api/monitoring/queries/*
│
├─ 🎯 ORQUESTADOR
│  └─ backend/app/services/monitoring_orchestrator.py (400)
│     ├─ Función: Coordina los 3
│     ├─ Genera: Alertas unificadas
│     └─ Proporciona: Dashboard consolidado
│
├─ 🛣️ RUTAS API
│  └─ backend/app/routes/monitoring.py (350 líneas)
│     └─ 20+ endpoints para acceder datos
│
└─ 🔌 INTEGRACIÓN AUTOMÁTICA
   └─ backend/app/services/db_query_monitor.py (250)
      ├─ execute_query_monitored()
      ├─ DatabaseQueryMonitor (context manager)
      └─ @monitored_query (decorador)
```

---

## CUÁNDO SE EJECUTA CADA COSA

```
TIEMPO      COMPONENTE              QCHÉ HACE
═════════════════════════════════════════════════════════════════

T=0s        STARTUP                 Inicializa todo

T=0s+       Munin Loop              Recopila métricas
T=30s       (async task)
T=60s       
T=90s       ...

T=0s+       Pingdom Loop            Verifica endpoints
T=60s       (async task)
T=120s      
T=180s      ...

T=0s+       Request API             Usuario hace solicitud
T=X        (variable)              │
           ├─ Middleware           Registra en logs
           ├─ Query BD             ejecutar_query()
           │                       Slow Query Log registra
           └─ Response             Retorna al usuario

SIEMPRE     Alertas                 Se generan automáticamente
            cuando:                 basadas en umbrales
            • CPU > 80%
            • Mem > 85%
            • Query > 1000ms
            • Endpoint caído
```

---

## ARCHIVO main.py - Las Líneas Clave

```python
# LÍNEA 10 - IMPORTAR
from app.services.monitoring_orchestrator import MonitoringOrchestrator

# LÍNEA 26 - VARIABLE GLOBAL
monitoring_orchestrator = None

# LÍNEA 31 - REGISTRAR ROUTER
app.include_router(monitoring.router)

# LÍNEAS 34-48 - MIDDLEWARE 1 (Logging)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Registra tiempo de requests

# LÍNEAS 51-68 - MIDDLEWARE 2 (Monitoreo)
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    # Prepara orquestador si no existe
    if monitoring_orchestrator is None:
        monitoring_orchestrator = MonitoringOrchestrator()

# LÍNEAS 71-83 - STARTUP (LO MÁS IMPORTANTE)
@app.on_event("startup")
async def startup():
    global monitoring_orchestrator
    
    await init_db(app)
    
    # CREAR ORQUESTADOR
    monitoring_orchestrator = MonitoringOrchestrator()
    
    # INICIALIZAR
    await monitoring_orchestrator.initialize_monitoring()
    
    # INICIAR LOOPS DE BACKGROUND
    await monitoring_orchestrator.start_continuous_monitoring()
    
    logger.info("EnergyGrid startup complete - Monitoring system initialized")

# LÍNEAS 86-95 - SHUTDOWN
@app.on_event("shutdown")
async def shutdown():
    global monitoring_orchestrator
    
    if monitoring_orchestrator:
        await monitoring_orchestrator.stop_continuous_monitoring()
    
    await close_db(app)
    logger.info("EnergyGrid shutdown complete")
```

---

## FLUJO DE UNA REQUEST CON MONITOREO

```
Usuario hace request:
GET /api/consumption/1
│
▼
┌─────────────────────────────────────────────┐
│ middleware("http") - log_requests()         │
│ (main.py:34-48)                             │
│ ├─ start = time.time()                      │
│ ├─ response = await call_next(request)      │
│ ├─ duration = (time.time() - start) * 1000  │
│ └─ logger.info("Request completed",         │
│    extra={..., "duration_ms": duration})    │
└─────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│ Ruta de negocio (get_consumption)           │
│ ├─ await pool.fetch(...)                    │
│ │  ▼                                        │
│ │  AQUÍ OCURRE LA MAGIA                    │
│ │  Si usas execute_query_monitored:         │
│ │  ├─ Ejecuta query                         │
│ │  └─ slow_query_log.log_query()            │
│ │     ├─ Registra tiempo                    │
│ │     ├─ Calcula severity                   │
│ │     └─ Genera alertas si aplica           │
│ └─ return resultado                         │
└─────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│ Response al usuario                         │
│ {"consumption": [...], "status": 200}       │
└─────────────────────────────────────────────┘
```

---

## VER LOS DATOS - TRES FORMAS

### 1️⃣ TERMINAL (Logs en tiempo real)
```bash
$ python -m uvicorn app.main:app --reload
# Verás logs tipo:
# Request completed - duration_ms=125
# Munin metrics collected
# Slow query detected - execution_time_ms=1250
```

### 2️⃣ API (HTTP Requests)
```bash
# Dashboard completo
curl http://localhost:8000/api/monitoring/dashboard | jq

# Health score
curl http://localhost:8000/api/monitoring/health | jq

# Queries lentas
curl http://localhost:8000/api/monitoring/queries/slow | jq

# Alertas críticas
curl http://localhost:8000/api/monitoring/alerts?severity=critical | jq
```

### 3️⃣ CÓDIGO (Acceso programático)
```python
from app.routes.monitoring import get_monitoring_instance

monitor = get_monitoring_instance()
health = monitor.get_system_health()
print(health['overall_health'])  # 87.5
```

---

## RESUMEN DE INTEGRACIÓN

```
┌──────────────────────────────────────────────────────────┐
│  PUNTO DE ENTRADA: main.py                              │
├──────────────────────────────────────────────────────────┤
│ 1. Línea 10 - Importar MonitoringOrchestrator           │
│ 2. Línea 26 - Variable global                           │
│ 3. Línea 31 - Registrar rutas API                       │
│ 4. Líneas 71-83 - Inicializar en STARTUP               │
│ 5. Líneas 86-95 - Limpiar en SHUTDOWN                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  TRES MONITORES AUTOMÁTICOS                             │
├──────────────────────────────────────────────────────────┤
│ • Munin: Cada 30s → collect_metrics()                   │
│ • Pingdom: Cada 60s → run_checks()                      │
│ • Slow Query Log: En tiempo real → log_query()          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  ALERTAS AUTOMÁTICAS                                    │
├──────────────────────────────────────────────────────────┤
│ • CPU, Memoria, Disco → Munin                           │
│ • Endpoints caídos → Pingdom                            │
│ • Queries críticas → Slow Query Log                     │
│ • Todas unificadas en: /api/monitoring/alerts           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  20+ ENDPOINTS API                                      │
├──────────────────────────────────────────────────────────┤
│ • /api/monitoring/health                                │
│ • /api/monitoring/dashboard                             │
│ • /api/monitoring/munin/*                               │
│ • /api/monitoring/pingdom/*                             │
│ • /api/monitoring/queries/*                             │
│ • Y 15 más...                                           │
└──────────────────────────────────────────────────────────┘
```

---

## ARCHIVOS CLAVE PARA LEER

1. **main.py** (99 líneas totales)
   - Lee líneas: 10, 26, 31, 71-83, 86-95
   - Esto es TODO lo que se modificó en main.py

2. **monitoring_orchestrator.py** (400 líneas)
   - El coordinador central de los 3 sistemas

3. **monitoring.py** (350 líneas)
   - Los 20+ endpoints API

4. **COMO_ESTA_INTEGRADO.md** 
   - Este documento con diagramas detallados
