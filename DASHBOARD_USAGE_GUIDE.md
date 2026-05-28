# 📊 Guía de Uso del Dashboard de Monitoreo

## Acceso al Dashboard

### Iniciar la Aplicación

```bash
cd /d/ProyectoFinal/EnergyGrid/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Acceder al Dashboard

Abre tu navegador web y navega a:

```
http://localhost:8000/dashboard
```

---

## 🎯 Descripción General

El dashboard proporciona una visualización en tiempo real de los tres sistemas de monitoreo integrados:

| Componente | Descripción | Actualización |
|------------|-------------|--------------|
| **Munin** | Métricas del sistema (CPU, memoria, disco, red) | Cada 30s |
| **Pingdom** | Health checks de endpoints | Cada 60s |
| **Slow Query Log** | Análisis de queries lentas en BD | En tiempo real |

---

## 📈 Secciones del Dashboard

### 1. 🔵 Munin - Métricas del Sistema

Muestra estadísticas en tiempo real del servidor:

#### Métricas Disponibles:
- **CPU Usage**: Porcentaje de utilización del procesador
- **Memory**: Disponible vs. en uso en GB
- **Disk**: Uso de espacio en disco
- **Network**: Tráfico de entrada y salida
- **System Load**: Carga promedio (1min, 5min, 15min)
- **Processes**: Número total de procesos activos

#### Interpretación de Alertas:
- 🟢 **Verde (OK)**: Métrica dentro de rangos normales
- 🟡 **Amarillo (Warning)**: Métrica aproximándose a límite (>80%)
- 🔴 **Rojo (Critical)**: Métrica crítica (>85%)

**Ejemplo**: Si ves CPU en rojo, significa que está usando más del 85% de su capacidad y podría necesitar optimización o escalado.

---

### 2. 🟠 Pingdom - Health Checks

Verifica la disponibilidad de endpoints críticos de la aplicación:

#### Endpoints Monitoreados:
- `/health` - Check de salud general
- `/api/metrics` - API de métricas
- `/api/districts` - API de distritos
- `/api/monitoring/health` - Health del sistema de monitoreo

#### Interpretación de Resultados:
- **Status**: UP = Disponible, DOWN = No disponible
- **Response Time**: Tiempo en milisegundos
- **Last Check**: Última verificación realizada
- **Uptime**: Porcentaje de disponibilidad en últimas 24h

**Ejemplo**: Si ves un endpoint en DOWN, significa que no respondió al último health check. Investiga los logs para ver por qué.

#### Acciones:
- 🔄 **Refresh**: Recarga los datos manualmente
- 📊 **Histórico**: Ver tendencia de disponibilidad

---

### 3. 🟢 Slow Query Log - Análisis de Queries

Monitorea las consultas más lentas a la base de datos:

#### Información Disponible:
- **Query**: Sentencia SQL ejecutada
- **Duration (ms)**: Tiempo de ejecución
- **Threshold**: Tiempo configurado para alertar
- **Status**: Dentro/Fuera de límites
- **Timestamp**: Cuándo se ejecutó

#### Umbrales por Defecto:
- ⚠️ **Warning**: > 100ms
- 🔴 **Critical**: > 500ms

**Ejemplo**: Si ves una query con 1500ms, significa que es crítica y debería optimizarse (agregar índices, reescribir lógica, etc.)

#### Mejoramientos Posibles:
1. Agregar índices a columnas en WHERE/JOIN
2. Usar EXPLAIN PLAN para analizar ejecución
3. Fragmentar queries complejas
4. Implementar caching

---

## 🎛️ Controles del Dashboard

### Actualización Automática

El dashboard se actualiza automáticamente cada **5 segundos** por defecto.

**Opciones de Actualización**:
- 🔵 **5s** - Actualización muy rápida (por defecto)
- 🔵 **10s** - Actualización normal
- 🔵 **Manual** - Actualizar bajo demanda

Para cambiar: Click en el botón de actualización en la esquina superior derecha.

### Búsqueda y Filtros

- **Filtrar Alertas**: Solo mostrar alertas de un tipo (INFO, WARNING, CRITICAL)
- **Búsqueda de Queries**: Buscar queries específicas por texto
- **Filtrar por Endpoint**: Ver checks de un endpoint específico

---

## 🚨 Interpretación de Alertas

Las alertas se muestran en orden de severidad:

| Tipo | Color | Significado | Acción |
|------|-------|-------------|--------|
| **INFO** | 🔵 Azul | Información general | Informativo |
| **WARNING** | 🟡 Amarillo | Métrica acercándose a límite | Monitorear de cerca |
| **CRITICAL** | 🔴 Rojo | Métrica fuera de límites | Acción inmediata necesaria |

### Ejemplos de Alertas

**Alerta CRITICAL - CPU Alta**:
```
CRITICAL: CPU usage at 92%
Expected: < 85%
Action: Check for running processes, consider scaling
```

**Alerta WARNING - Disk Space**:
```
WARNING: Disk usage at 78%
Expected: < 80%
Action: Monitor, clean up if needed
```

**Alerta CRITICAL - Slow Query**:
```
CRITICAL: Query took 1200ms
Query: SELECT * FROM large_table JOIN...
Action: Optimize query or add index
```

---

## 📊 Health Score

En la esquina superior izquierda verás un **Health Score (0-100)**:

- **90-100**: Sistema saludable
- **70-89**: Algunas áreas requieren atención
- **50-69**: Problemas moderados
- **0-49**: Problemas severos

El score se calcula basándose en:
- Disponibilidad de endpoints (Pingdom)
- Utilización de recursos (Munin)
- Rendimiento de queries (Slow Query Log)

---

## 🔍 Monitoreo Avanzado

### Accediendo a Datos Detallados

Si necesitas más detalles, puedes acceder directamente a los endpoints API:

```bash
# Métricas de Munin
curl http://localhost:8000/api/monitoring/munin/metrics

# Status de Pingdom
curl http://localhost:8000/api/monitoring/pingdom/status

# Statistics de queries
curl http://localhost:8000/api/monitoring/queries/statistics

# Todas las alertas
curl http://localhost:8000/api/monitoring/alerts
```

### Filtrar por Tipo de Alerta

```bash
# Solo alertas críticas
curl "http://localhost:8000/api/monitoring/alerts?severity=CRITICAL"

# Solo warnings
curl "http://localhost:8000/api/monitoring/alerts?severity=WARNING"
```

---

## 🛠️ Solución de Problemas

### El dashboard no se carga

1. Verifica que la aplicación esté corriendo:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verifica que todos los servicios estén inicializados (revisa los logs)

3. Limpia la caché del navegador (Ctrl+Shift+Del) e intenta nuevamente

### Los datos no se actualizan

1. Verifica que los servicios de monitoreo estén activos:
   ```bash
   curl http://localhost:8000/api/monitoring/status
   ```

2. Aumenta la velocidad de actualización en el dashboard

3. Revisa la consola del navegador (F12) para errores

### Endpoint aparece como DOWN

1. Verifica que el endpoint sea accesible:
   ```bash
   curl http://localhost:8000/api/metrics
   ```

2. Revisa los logs de la aplicación

3. Verifica la configuración de Pingdom en `monitoring_config.py`

---

## 📝 Notas Importantes

- El dashboard requiere **conexión constante** a la aplicación
- Los datos históricos se mantienen en memoria (no persistente)
- Para persistencia, considera integrar con InfluxDB o Prometheus
- Los umbrales de alertas pueden customizarse en `monitoring_config.py`

---

## 📞 Contacto y Soporte

Para reportar issues o sugerencias:
- Revisa los logs: `backend/logs/`
- Verifica la documentación: `MONITORING_README.md`
- Consulta ejemplos de integración: `app/routes/monitoring_examples.py`

---

**Última actualización**: May 25, 2024
**Versión del Dashboard**: 1.0
