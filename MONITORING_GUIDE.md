# Sistema de Monitoreo Integrado - EnergyGrid

## 📋 Descripción General

Se ha integrado un sistema completo de monitoreo que combina tres herramientas fundamentales para hacer el sistema más robusto:

### 🔵 **Munin** - Monitor de Métricas del Sistema
- **Ubicación**: `backend/app/services/munin_monitor.py`
- **Función**: Recopila métricas en tiempo real del servidor
- **Métricas**:
  - CPU: Uso general, por núcleo, carga del sistema
  - Memoria: Total, disponible, en uso, porcentaje
  - Disco: Capacidad total, usada, libre, porcentaje
  - Red: Bytes enviados/recibidos, paquetes, errores
  - Procesos: Procesos totales, top 5 por memoria
  - Carga del sistema: 1m, 5m, 15m

### 🟠 **Pingdom** - Guardia de Disponibilidad
- **Ubicación**: `backend/app/services/pingdom_guard.py`
- **Función**: Verifica minuto a minuto la disponibilidad de endpoints
- **Características**:
  - Health checks periódicos (configurables)
  - Medición de tiempo de respuesta
  - Historial de uptime
  - Detección de incidentes
  - Reportes de disponibilidad por período

### 🟢 **Slow Query Log** - Registro de Tráfico de BD
- **Ubicación**: `backend/app/services/slow_query_log.py`
- **Función**: Registra y analiza queries lentas
- **Características**:
  - Registro de todas las queries con tiempo de ejecución
  - Identificación automática de queries lentas
  - Agrupación de queries por patrón
  - Análisis de cuellos de botella
  - Desglose de queries por tipo (SELECT, INSERT, UPDATE, DELETE)

## 🔗 Integración Central

### MonitoringOrchestrator
- **Ubicación**: `backend/app/services/monitoring_orchestrator.py`
- **Función**: Orquesta los tres monitores en un sistema unificado
- **Responsabilidades**:
  - Coordina recopilación de métricas
  - Unifica alertas de todos los sistemas
  - Genera dashboards y reportes
  - Calcula health score general del sistema

## 🛣️ Rutas API de Monitoreo

### Salud General
```
GET  /api/monitoring/health        → Estado general del sistema
GET  /api/monitoring/dashboard     → Dashboard completo
GET  /api/monitoring/report        → Reporte detallado
```

### Alertas
```
GET  /api/monitoring/alerts        → Todas las alertas
GET  /api/monitoring/alerts?severity=critical → Alertas por severidad
```

### Munin (Métricas del Sistema)
```
GET  /api/monitoring/munin/metrics     → Últimas métricas
GET  /api/monitoring/munin/health      → Score de salud
GET  /api/monitoring/munin/history     → Historial (últimas N)
```

### Pingdom (Disponibilidad)
```
GET  /api/monitoring/pingdom/status               → Estado actual
GET  /api/monitoring/pingdom/endpoints/{name}     → Endpoint específico
GET  /api/monitoring/pingdom/uptime?hours=24      → Uptime report
GET  /api/monitoring/pingdom/incidents            → Incidentes
```

### Slow Query Log (Base de Datos)
```
GET  /api/monitoring/queries/statistics       → Estadísticas generales
GET  /api/monitoring/queries/slow             → Queries más lentas
GET  /api/monitoring/queries/bottlenecks      → Cuellos de botella
GET  /api/monitoring/queries/breakdown        → Por tipo de query
GET  /api/monitoring/queries/recent           → Queries recientes
```

### Control
```
POST /api/monitoring/start              → Inicia monitoreo
POST /api/monitoring/stop               → Detiene monitoreo
GET  /api/monitoring/status             → Estado del sistema
```

## 🚀 Cómo Usar

### 1. Inicialización Automática
El sistema se inicializa automáticamente al arrancar la aplicación (ver `main.py`):

```python
@app.on_event("startup")
async def startup():
    # Se crea MonitoringOrchestrator
    # Se inicializan los tres monitores
    # Se inicia monitoreo continuo
```

### 2. Registrar Queries de Base de Datos

Usa el helper `db_query_monitor.py`:

```python
from app.services.db_query_monitor import execute_query_monitored

# Opción 1: Función helper
result = await execute_query_monitored(
    "SELECT * FROM consumption WHERE id = $1",
    district_id,
    pool=app.state.db,
    query_type="SELECT"
)

# Opción 2: Context manager
async with DatabaseQueryMonitor("SELECT ...", pool=app.state.db):
    result = await pool.fetch("SELECT ...")

# Opción 3: Decorador
@monitored_query(query_type="SELECT")
async def get_consumption_data():
    return await pool.fetch("SELECT ...")
```

### 3. Acceder al Dashboard

```bash
# Dashboard completo
curl http://localhost:8000/api/monitoring/dashboard

# Salud del sistema
curl http://localhost:8000/api/monitoring/health

# Alertas críticas
curl http://localhost:8000/api/monitoring/alerts?severity=critical

# Queries lentas
curl http://localhost:8000/api/monitoring/queries/slow?limit=10
```

## 📊 Ejemplos de Respuestas

### Health Score
```json
{
  "timestamp": "2026-05-25T10:30:45.123456",
  "overall_health": 87.5,
  "components": {
    "system_health": 85.0,
    "availability": "up",
    "database_performance": 92.0
  },
  "status": "good"
}
```

### Bottlenecks (Cuellos de Botella)
```json
{
  "bottlenecks": [
    {
      "pattern": "SELECT * FROM consumption WHERE",
      "count": 1250,
      "slow_count": 45,
      "average_time_ms": 235.5,
      "slow_percentage": 3.6,
      "impact_score": 10.6
    }
  ]
}
```

### Unified Alerts
```json
{
  "total": 3,
  "alerts": [
    {
      "type": "critical_query",
      "severity": "critical",
      "message": "Query crítica: 2500ms",
      "query_type": "SELECT"
    },
    {
      "type": "memory_high",
      "severity": "critical",
      "value": 87.5,
      "message": "Memoria: 87.5%"
    },
    {
      "type": "cpu_high",
      "severity": "warning",
      "value": 82.0,
      "message": "CPU: 82%"
    }
  ]
}
```

## 🎯 Umbrales de Alerta

### Munin
- CPU > 80% → Warning
- Memoria > 85% → Critical
- Disco > 90% → Critical
- Carga > CPU count → Warning

### Pingdom
- Timeout > configurado → Down
- Status code ≠ esperado → Down

### Slow Query Log
- Query > 500ms (configurable) → Slow
- Query > 1000ms → Warning
- Query > 2000ms → Critical
- Tasa de queries lentas > 10% → Alert

## 🔄 Ciclo de Vida

### Startup
1. Inicializar `MonitoringOrchestrator`
2. Crear instancias de Munin, Pingdom, SlowQueryLog
3. Configurar endpoints de Pingdom
4. Iniciar loops de background:
   - Munin: Cada 30 segundos
   - Pingdom: Cada 60 segundos

### Runtime
- Queries de BD se registran automáticamente
- Métricas se recopilan continuamente
- Alertas se generan en tiempo real
- APIs disponibles para consultas

### Shutdown
1. Detener loops de background
2. Guardar estado final (opcional)
3. Limpiar recursos

## 🔒 Consideraciones de Seguridad

1. **Queries**: Se truncan a 500 caracteres en logs
2. **Historial**: Se limita el tamaño máximo de historial
3. **Credenciales**: No se registran credenciales en queries
4. **Endpoints**: Se pueden filtrar por seguridad

## 📈 Métricas Clave

El sistema calcula:
- **Health Score**: 0-100 basado en CPU, memoria, disco y carga
- **Uptime Percentage**: % de tiempo que endpoints están disponibles
- **Slow Query Percentage**: % de queries que exceden el umbral
- **Impact Score**: Multiplicador de frecuencia × tiempo

## 🛠️ Customización

### Cambiar umbral de queries lentas
```python
monitor = MonitoringOrchestrator()
monitor.slow_query_log = SlowQueryLog(slow_query_threshold_ms=1000)
```

### Agregar más endpoints
```python
monitor.pingdom.add_endpoint(
    "analytics_api",
    "http://analytics:8001/health",
    timeout=10,
    expected_status=200
)
```

### Limpiar logs antiguos
```python
monitor.slow_query_log.clear_old_logs(hours=48)
```

## 📝 Próximos Pasos

1. Integrar webhooks para alertas (Slack, email)
2. Persistencia de métricas históricas (InfluxDB)
3. Visualización en tiempo real (Grafana)
4. Predicción de problemas (ML)
5. Auto-scaling basado en métricas

---

**Módulos creados**: 5 servicios + 1 ruta API
**Endpoints disponibles**: 20+ rutas de monitoreo
**Métricas capturadas**: 50+ métricas diferentes
**Alertas automáticas**: 10+ tipos de alertas
