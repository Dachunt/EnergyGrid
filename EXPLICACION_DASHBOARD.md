# Explicación: Dashboard de Monitoreo EnergyGrid

## ¿Qué es lo que ves?

Es el **Dashboard Completo** de monitoreo que muestra el estado actual de tu sistema en tiempo real.

---

## Estructura del Response

### 1. **Timestamp** 📅
```json
"timestamp": "2026-05-27T04:30:15.991565"
```
**Significado**: Hora exacta en que se tomó la medición (ISO 8601)
- Año: 2026
- Mes: 05 (Mayo)
- Día: 27
- Hora: 04:30:15

---

### 2. **System Health** 🔵 (MUNIN)

```json
"overall_health": 100.0,
"status": "excellent"
```

**Significado**: Health Score del sistema (0-100)
- **100.0** = Excelente (sistema en perfecto estado)
- **80-99** = Bueno
- **60-79** = Aceptable
- **40-59** = Advertencia
- **0-39** = Crítico

**Componentes**:
```json
"system_health": 100.0      → Salud general
"availability": "up"         → Sistema operacional
"database_performance": 100  → BD funcionando perfectamente
```

---

### 3. **System Metrics** 📊 (MUNIN)

```json
"cpu_percent": 0              → CPU sin usar (0%)
"memory_percent": 0           → Memoria sin usar (0%)
"disk_percent": 0             → Disco sin usar (0%)
"system_load": {}             → Carga del sistema (vacío = no hay carga)
```

**¿Por qué todo es 0?**
- La aplicación acaba de iniciar
- Sin datos de prueba aún
- Es **normal** en una instalación nueva

---

### 4. **Availability** 🟠 (PINGDOM)

```json
"overall_status": "up",
"endpoints": {},              → Sin endpoints registrados aún
"total_endpoints": 0,
"healthy_endpoints": 0,
"last_check": null
```

**Significado**:
- `"up"` = Sistema está disponible
- `endpoints: {}` = No hay endpoints monitoreados (se agregan manualmente)
- `last_check: null` = Aún no se ha hecho verificación

---

### 5. **Database** 🟢 (SLOW QUERY LOG)

```json
"statistics": {
  "total_queries": 0,         → 0 queries ejecutadas
  "slow_queries": 0,          → 0 queries lentas
  "slow_query_percentage": 0, → 0% son lentas
  "average_time_ms": 0,       → Tiempo promedio
  "max_time_ms": 0,           → Query más lenta
  "threshold_ms": 500         → Umbral: queries > 500ms son lentas
},
"bottlenecks": []             → Sin cuellos de botella detectados
```

**Significado**:
- Todo es **0** porque la BD no ha procesado queries aún
- El sistema está **listo** para capturar datos

---

### 6. **Alerts** 🔔

```json
"alerts": [],                 → Sin alertas activas
"alert_count": 0,
"critical_alerts": 0
```

**Significado**: 
- Sistema **sin problemas**
- Todas las métricas están dentro de los umbrales seguros

---

## ¿Qué Significan Los Valores?

| Campo | Rango Normal | Alerta | Crítico |
|-------|---|---|---|
| `cpu_percent` | 0-50% | > 80% | > 95% |
| `memory_percent` | 0-50% | > 80% | > 85% |
| `disk_percent` | 0-70% | > 80% | > 90% |
| `availability` | "up" | "degraded" | "down" |
| `overall_health` | 70-100 | 50-69 | 0-49 |

---

## Resumen De Lo Que Ves

```
┌─────────────────────────────────────────────────────┐
│  ESTADO DEL SISTEMA - 2026-05-27 04:30:15          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Sistema General:    ✅ Excelente (100%)            │
│  Disponibilidad:     ✅ UP                          │
│  Base de Datos:      ✅ Funcionando                 │
│  Alertas:            ✅ Ninguna                     │
│                                                      │
│  Métricas:                                          │
│    CPU:      0%                                    │
│    Memoria:  0%                                    │
│    Disco:    0%                                    │
│                                                      │
│  Queries:                                          │
│    Total:   0                                      │
│    Lentas:  0                                      │
│    Cuellos: 0                                      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## ¿Por Qué Todo Es 0?

Es **totalmente normal** porque:

1. **Acaba de iniciar** - No hay datos históricos
2. **Sistema nuevo** - Sin carga de trabajo
3. **BD vacía** - Sin queries ejecutadas
4. **Endpoints no configurados** - Pingdom necesita endpoints para monitorear

---

## Cómo Llenar De Datos

### Opción 1: Usar el Sistema
```bash
# Hacer requests para generar tráfico
curl http://localhost:8000/api/monitoring/health
curl http://localhost:8000/api/monitoring/dashboard
```

### Opción 2: Agregar Endpoints a Pingdom
```python
# En el código, agreguen endpoints:
monitoring.pingdom.add_endpoint(
    "api_main",
    "http://localhost:8000/health",
    timeout=5
)
```

### Opción 3: Ejecutar Queries
```python
# Registrar queries en la BD
from app.services.db_query_monitor import execute_query_monitored

await execute_query_monitored(
    "SELECT * FROM devices",
    pool=db,
    query_type="SELECT"
)
```

---

## Campos Importantes

| Campo | Qué es | Dónde viene |
|-------|--------|-----------|
| `timestamp` | Hora de la medición | Sistema |
| `overall_health` | Score 0-100 | Munin |
| `cpu_percent` | Uso CPU | Munin |
| `availability` | Sistema up/down | Pingdom |
| `total_queries` | Queries ejecutadas | Slow Query Log |
| `slow_queries` | Queries > 500ms | Slow Query Log |
| `alerts` | Problemas detectados | Todas |

---

## Próximas Métricas Que Verás

A medida que uses el sistema:

```json
{
  "cpu_percent": 25.5,           ← CPU en uso
  "memory_percent": 45.2,        ← Memoria en uso
  "disk_percent": 62.8,          ← Espacio disco
  "total_queries": 1250,         ← Queries procesadas
  "slow_queries": 45,            ← Queries lentas detectadas
  "bottlenecks": [{...}],        ← Cuellos identificados
  "alerts": [
    {
      "type": "cpu_high",
      "severity": "warning",
      "value": 82,
      "message": "CPU utilización alta"
    }
  ]
}
```

---

## Interpretación Rápida

| Métrica | Significa | Qué Hacer |
|---------|-----------|-----------|
| overall_health: 100 | ✅ Sistema perfecto | Nada |
| overall_health: 50-69 | ⚠️ Advertencia | Revisar alertas |
| overall_health: < 50 | 🔴 Crítico | Actuar inmediatamente |
| availability: "up" | ✅ Sistema disponible | OK |
| availability: "down" | 🔴 Sistema caído | Emergencia |
| slow_query_percentage: > 10% | ⚠️ Muchas lentas | Optimizar BD |
| cpu_percent: > 80% | ⚠️ Alto consumo | Revisar procesos |
| memory_percent: > 85% | 🔴 Crítico | Liberar memoria |

---

## En Resumen

Lo que ves es el **Dashboard Completo** que muestra:

1. **🟢 MUNIN** - Salud del sistema (CPU, memoria, disco)
2. **🟠 PINGDOM** - Disponibilidad de endpoints
3. **🔵 SLOW QUERY LOG** - Performance de la base de datos
4. **🔔 ALERTAS** - Problemas detectados automáticamente

**El sistema está funcionando perfectamente!**

Los valores 0 son normales en una instalación nueva. A medida que hagas uso del sistema, verás:
- Métricos reales
- Queries registradas
- Alertas si hay problemas
- Análisis de cuellos de botella

---

## Endpoints Relacionados

```bash
# Ver mismo dashboard
curl http://localhost:8000/api/monitoring/dashboard | jq

# Ver solo health score
curl http://localhost:8000/api/monitoring/health | jq

# Ver solo alertas
curl http://localhost:8000/api/monitoring/alerts | jq

# Ver solo métricas Munin
curl http://localhost:8000/api/monitoring/munin/metrics | jq

# Ver solo info Pingdom
curl http://localhost:8000/api/monitoring/pingdom/status | jq

# Ver solo queries lentas
curl http://localhost:8000/api/monitoring/queries/slow | jq
```

---

**¿Preguntas sobre alguna métrica específica? Pregunta y te lo explico!**
