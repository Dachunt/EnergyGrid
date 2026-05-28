# 🎯 Guía Completa de Integración: Sistema de Monitoreo EnergyGrid

## 📋 Contenidos
1. [Descripción general](#descripción-general)
2. [Instalación](#instalación)
3. [Configuración](#configuración)
4. [Uso de las herramientas](#uso-de-las-herramientas)
5. [Endpoints API](#endpoints-api)
6. [Ejemplos de uso](#ejemplos-de-uso)
7. [Troubleshooting](#troubleshooting)

---

## Descripción General

Tu sistema EnergyGrid ahora está equipado con **tres herramientas complementarias** de monitoreo:

### 🔵 Munin — Sensor Universal
- **Función**: Mide en tiempo real procesos activos, uso de memoria, tráfico de red, velocidad del disco y carga del servidor
- **Archivo**: `backend/app/services/munin_monitor.py`
- **Características**:
  - Captura 50+ métricas del sistema
  - Calcula health score automático (0-100)
  - Genera alertas basadas en umbrales configurables
  - Historial de métricas almacenado

### 🟠 Pingdom — Guardia de Turno
- **Función**: Verifica minuto a minuto que la plataforma responde y puede utilizarse
- **Archivo**: `backend/app/services/pingdom_guard.py`
- **Características**:
  - Health checks periódicos configurables
  - Medición automática de tiempos de respuesta
  - Historial completo de uptime
  - Detección de incidentes automática
  - Alertas cuando endpoints caen

### 🟢 Slow Query Log — Registro de Tráfico
- **Función**: Consolida las respuestas lentas de la base de datos para identificar cuellos de botella
- **Archivo**: `backend/app/services/slow_query_log.py`
- **Características**:
  - Registra todas las queries con tiempo de ejecución
  - Agrupa queries por patrón
  - Identifica cuellos de botella automáticamente
  - Desglose por tipo de query
  - Umbrales configurables

---

## Instalación

### Paso 1: Instalar Dependencias

```bash
cd backend
pip install -r requirements.txt
```

El archivo `requirements.txt` ya incluye:
- `psutil==5.9.6` - Para Munin (métricas del sistema)
- `httpx==0.26.0` - Para Pingdom (health checks HTTP)

### Paso 2: Verificar la Estructura

```
backend/app/
├── services/
│   ├── munin_monitor.py              ✅ Monitor de métricas
│   ├── pingdom_guard.py              ✅ Health checks
│   ├── slow_query_log.py             ✅ Registro de queries
│   ├── monitoring_orchestrator.py    ✅ Orquestador central
│   └── monitoring_config.py          ✅ Configuración
├── routes/
│   ├── monitoring.py                 ✅ Endpoints API (30+)
│   └── monitoring_examples.py        ✅ Ejemplos de uso
└── main.py                           ✅ Inicialización automática
```

### Paso 3: Iniciar la Aplicación

```bash
python -m uvicorn app.main:app --reload
```

Verás los logs:
```
✓ Initializing monitoring system...
✓ Monitoring system initialized and running
✓ Starting continuous monitoring
```

---

## Configuración

### Configuración de Munin

```python
from app.services.munin_monitor import MuninMonitor

munin = MuninMonitor()

# Obtener métricas completas
metrics = munin.get_system_metrics()

# Obtener health score (0-100)
score = munin.get_health_score()

# Obtener alertas
alerts = munin.get_alerts()
```

**Umbrales por defecto**:
- CPU > 80% = ⚠️ Warning
- Memoria > 85% = 🔴 Critical
- Disco > 90% = 🔴 Critical
- Carga del sistema > # CPUs = ⚠️ Warning

### Configuración de Pingdom

```python
from app.services.pingdom_guard import PingdomGuard

pingdom = PingdomGuard(check_interval=60)  # Verificar cada 60 segundos

# Agregar endpoints a monitorear
pingdom.add_endpoint(
    "main_api",
    "http://localhost:8000/health",
    timeout=5,
    expected_status=200
)

pingdom.add_endpoint(
    "metrics_endpoint",
    "http://localhost:8000/api/metrics",
    timeout=10,
    expected_status=200
)

# Obtener estado
status = pingdom.get_status()

# Obtener uptime
uptime = pingdom.get_uptime_report(hours=24)
```

### Configuración de Slow Query Log

```python
from app.services.slow_query_log import SlowQueryLog

slow_query_log = SlowQueryLog(
    slow_query_threshold_ms=500  # Queries > 500ms se consideran lentas
)

# Registrar una query
await slow_query_log.log_query(
    query="SELECT * FROM devices WHERE district_id = $1",
    execution_time_ms=1200,
    query_type="SELECT",
    parameters={"district_id": 1}
)

# Obtener estadísticas
stats = slow_query_log.get_statistics()

# Obtener cuellos de botella
bottlenecks = slow_query_log.get_bottlenecks()
```

---

## Uso de las Herramientas

### Orquestador Central

El `MonitoringOrchestrator` coordina las tres herramientas:

```python
from app.services.monitoring_orchestrator import MonitoringOrchestrator

# Se crea automáticamente en main.py
monitor = app.state.monitoring

# Dashboard completo
dashboard = monitor.get_monitoring_dashboard()

# Health score global
health = monitor.get_system_health()

# Alertas unificadas
alerts = monitor.get_unified_alerts()

# Reporte detallado
report = monitor.get_detailed_report()
```

### Integración Automática de Queries

El sistema proporciona tres formas de monitorear queries:

#### Opción 1: Función Helper

```python
from app.services.db_query_monitor import execute_query_monitored

result = await execute_query_monitored(
    "SELECT * FROM devices WHERE id = $1",
    device_id,
    pool=app.state.db,
    query_type="SELECT"
)
```

#### Opción 2: Context Manager

```python
from app.services.db_query_monitor import DatabaseQueryMonitor

async with DatabaseQueryMonitor(
    "SELECT * FROM devices",
    pool=app.state.db
):
    result = await pool.fetch("SELECT * FROM devices")
```

#### Opción 3: Decorador

```python
from app.services.db_query_monitor import monitored_query

@monitored_query(query_type="SELECT")
async def get_all_devices():
    return await pool.fetch("SELECT * FROM devices")
```

---

## Endpoints API

### Dashboard y Salud General

```
GET /api/monitoring/health
```
Estado general del sistema con health scores

```
GET /api/monitoring/dashboard
```
Dashboard completo con todas las métricas

```
GET /api/monitoring/report
```
Reporte detallado del sistema

### Munin — Métricas del Sistema

```
GET /api/monitoring/munin/metrics
```
Últimas métricas del sistema (CPU, memoria, disco, red)

```
GET /api/monitoring/munin/health
```
Health score + alertas de Munin

```
GET /api/monitoring/munin/history
```
Historial de métricas (últimas 100)

### Pingdom — Disponibilidad

```
GET /api/monitoring/pingdom/status
```
Estado de todos los endpoints monitoreados

```
GET /api/monitoring/pingdom/endpoints/{name}
```
Detalles de un endpoint específico

```
GET /api/monitoring/pingdom/uptime?hours=24
```
Reporte de disponibilidad en las últimas N horas

```
GET /api/monitoring/pingdom/incidents
```
Incidentes detectados

### Slow Query Log — Performance de BD

```
GET /api/monitoring/queries/statistics
```
Estadísticas generales de queries

```
GET /api/monitoring/queries/slow?limit=10
```
Top 10 queries más lentas

```
GET /api/monitoring/queries/bottlenecks
```
Cuellos de botella identificados

```
GET /api/monitoring/queries/breakdown
```
Desglose de queries por tipo

```
GET /api/monitoring/queries/recent?limit=20
```
Últimas 20 queries registradas

### Alertas Unificadas

```
GET /api/monitoring/alerts
```
Todas las alertas de todos los monitores

```
GET /api/monitoring/alerts?severity=critical
```
Solo alertas críticas

---

## Ejemplos de Uso

### Ejemplo 1: Obtener Dashboard Completo

```bash
curl http://localhost:8000/api/monitoring/dashboard
```

**Respuesta**:
```json
{
  "timestamp": "2026-05-26T10:30:45.123456",
  "system_health": {
    "overall_health": 87.5,
    "components": {
      "system_health": 85.0,
      "availability": "up",
      "database_performance": 92.0
    },
    "status": "good"
  },
  "system_metrics": {
    "cpu_percent": 42.5,
    "memory_percent": 68.3,
    "disk_percent": 55.2,
    "system_load": {
      "load_1m": 2.5,
      "load_5m": 2.2,
      "load_15m": 2.0
    }
  },
  "availability": {
    "overall_status": "up",
    "healthy_endpoints": 5,
    "endpoints": [...]
  },
  "database": {
    "statistics": {
      "total_queries": 1250,
      "slow_queries": 45,
      "slow_query_percentage": 3.6,
      "average_time_ms": 235.5
    },
    "bottlenecks": [...]
  },
  "alerts": [
    {
      "type": "cpu_high",
      "severity": "warning",
      "value": 82,
      "message": "CPU utilización alta: 82%"
    }
  ]
}
```

### Ejemplo 2: Monitorear una Query Lenta

```python
import asyncio
from app.services.db_query_monitor import execute_query_monitored
from app.services.slow_query_log import SlowQueryLog

async def complex_report():
    slow_queries = SlowQueryLog(slow_query_threshold_ms=500)
    
    # Esta query será registrada automáticamente si tarda > 500ms
    result = await execute_query_monitored(
        """
        SELECT d.id, d.name, COUNT(m.id) as metric_count
        FROM devices d
        LEFT JOIN metrics m ON d.id = m.device_id
        GROUP BY d.id
        """,
        pool=app.state.db,
        query_type="SELECT"
    )
    
    # Obtener queries lentas
    slow = slow_queries.get_slow_queries()
    print(f"Found {len(slow)} slow queries")
```

### Ejemplo 3: Alertas Críticas

```bash
# Obtener solo alertas críticas
curl "http://localhost:8000/api/monitoring/alerts?severity=critical"
```

**Respuesta**:
```json
{
  "total": 2,
  "alerts": [
    {
      "type": "endpoint_down",
      "severity": "critical",
      "source": "pingdom",
      "message": "Endpoint 'main_api' is down",
      "timestamp": "2026-05-26T10:35:00"
    },
    {
      "type": "memory_critical",
      "severity": "critical",
      "source": "munin",
      "value": 94,
      "message": "Memory utilization critical: 94%"
    }
  ]
}
```

### Ejemplo 4: Reporte de Uptime

```bash
# Último día
curl "http://localhost:8000/api/monitoring/pingdom/uptime?hours=24"
```

**Respuesta**:
```json
{
  "period_hours": 24,
  "total_checks": 1440,
  "successful_checks": 1438,
  "failed_checks": 2,
  "uptime_percent": 99.86,
  "average_response_time_ms": 145.2,
  "endpoints": {
    "main_api": {
      "uptime_percent": 100.0,
      "response_time_avg_ms": 142.5
    },
    "metrics_endpoint": {
      "uptime_percent": 99.65,
      "response_time_avg_ms": 198.5
    }
  }
}
```

### Ejemplo 5: Identificar Cuellos de Botella

```bash
curl "http://localhost:8000/api/monitoring/queries/bottlenecks"
```

**Respuesta**:
```json
{
  "bottlenecks": [
    {
      "pattern": "SELECT * FROM metrics WHERE device_id = $1",
      "frequency": 245,
      "avg_time_ms": 1850,
      "max_time_ms": 3420,
      "total_time_ms": 452750,
      "impact_score": 8.5,
      "recommendation": "Add index on metrics(device_id)"
    },
    {
      "pattern": "SELECT * FROM districts",
      "frequency": 120,
      "avg_time_ms": 950,
      "max_time_ms": 2150,
      "total_time_ms": 114000,
      "impact_score": 6.2,
      "recommendation": "Consider caching district data"
    }
  ]
}
```

---

## Troubleshooting

### Problema: "psutil module not found"

**Solución**:
```bash
pip install psutil==5.9.6
```

### Problema: Monitoreo no inicia

**Verifica en los logs**:
```bash
# Busca estos mensajes:
# "Initializing monitoring system..."
# "Monitoring system initialized and running"
```

Si no aparecen, verifica que `main.py` tenga la integración correcta.

### Problema: Queries no se registran

**Solución**: Usa uno de los métodos de monitoreo:

```python
# Asegúrate de usar execute_query_monitored o context manager
from app.services.db_query_monitor import execute_query_monitored

result = await execute_query_monitored(
    "SELECT * FROM devices",
    pool=app.state.db,
    query_type="SELECT"
)
```

### Problema: Endpoints devuelven 404

**Verifica**:
1. El router de monitoreo está importado en `main.py`
2. La app ha iniciado correctamente
3. URL correcta: `/api/monitoring/...`

```bash
curl http://localhost:8000/api/monitoring/health
```

### Problema: Alertas no se generan

**Causas posibles**:
1. Umbrales muy altos
2. Sistema tiene métricas bajas
3. Monitoreo no iniciado

**Verifica el health score**:
```bash
curl http://localhost:8000/api/monitoring/health
```

---

## 📊 Métricas Monitoreadas

### Munin (Sistema)
- CPU: Porcentaje total, por núcleo, carga 1m/5m/15m
- Memoria: Total, disponible, usado, porcentaje
- Disco: Capacidad, uso, libre, porcentaje
- Red: Bytes entrada/salida, paquetes, errores
- Procesos: Total, top 5 por memoria
- Uptime del sistema

### Pingdom (Disponibilidad)
- Estado HTTP de cada endpoint
- Tiempo de respuesta
- Cambios de estado
- Incidentes
- Historial de checks

### Slow Query Log (Performance BD)
- Tiempo de ejecución de queries
- Frecuencia de queries
- Patrón de queries
- Queries críticas
- Cuellos de botella
- Impacto en performance

---

## 🔔 Umbrales de Alertas

| Métrica | Warning | Critical |
|---------|---------|----------|
| CPU | 80% | 95% |
| Memoria | 80% | 85% |
| Disco | 80% | 90% |
| Carga Sistema | > #CPUs | - |
| Query | 1000ms | 2000ms |
| Tasa Queries Lentas | 10% | 20% |
| Endpoint Down | - | Inmediato |
| Response Time | 5000ms | 10000ms |

---

## 🚀 Próximos Pasos

1. **Persistencia**: Guardar métricas en InfluxDB
2. **Visualización**: Dashboard con Grafana
3. **Alertas**: Webhooks a Slack/email
4. **Predicción**: ML para prognósticos
5. **Auto-scaling**: Basado en métricas
6. **Exportación**: Reportes en PDF/CSV

---

## ✅ Checklist de Validación

- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Archivos de servicio existen en `backend/app/services/`
- [ ] Rutas importadas en `main.py`
- [ ] Monitoreo inicia al arrancar
- [ ] Endpoints `/api/monitoring/` responden
- [ ] Alertas se generan correctamente
- [ ] Queries se registran
- [ ] Dashboard devuelve datos

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisa los logs: `tail -f backend.log`
2. Verifica endpoints con curl
3. Revisa `MONITORING_GUIDE.md` para más detalles
4. Revisa `monitoring_examples.py` para ejemplos

---

**Última actualización**: 2026-05-26  
**Versión**: 2.0.0 (Actualizada)  
**Estado**: ✅ Completamente integrado
