# Guía de Demo — EnergyGrid en AWS (Ciclo 24 minutos)

> Servidor: `98.91.49.34` | Todos los comandos son ejecutables desde fuera vía `curl`
> o desde adentro vía AWS Session Manager.

---

## Parámetros del simulador

| Parámetro | Valor |
|---|---|
| Intervalo de envío | **1 segundo** |
| Ciclo día virtual | **24 minutos** |
| 1 hora virtual = | **60 segundos reales** |
| Hora pico automática | **11h–13h virtual (minuto 11–13 real)** |
| Mediodía (peak máximo) | **Minuto 12 real** |
| Spike automático | Cada 60 s en subestación aleatoria, dura 30 s |

### Mapa del ciclo de 24 minutos

```
Minuto real  │  Hora virtual  │  Comportamiento
─────────────┼────────────────┼──────────────────────────────────
     0        │      0 h       │  Medianoche — consumo bajo (30-65%)
     2        │      2 h       │  Madrugada  — consumo bajo
     3        │      3 h       │  Inicio mañana
     6        │      6 h       │  Mañana     — consumo medio (70-85%)
     9        │      9 h       │  Fin mañana
    11        │     11 h       │  Pre-pico
    12        │     12 h       │  *** HORA PICO *** (88-98% todas las subestaciones)
    13        │     13 h       │  Fin hora pico
    18        │     18 h       │  Tarde — consumo bajo
    24        │     24 h       │  Fin ciclo → vuelve a minuto 0
─────────────┴────────────────┴──────────────────────────────────
Además: cada 60 seg → spike automático en 1 subestación aleatoria (dura 30 seg)
```

---

## URLs del sistema

| Recurso | URL |
|---|---|
| Frontend | http://98.91.49.34:3000 |
| Backend API + WebSocket | http://98.91.49.34:8000 |
| API Docs (Swagger) | http://98.91.49.34:8000/docs |
| Estado del simulador (externo) | http://98.91.49.34:8000/api/demo/simulator/health |
| Tiempo virtual (externo) | http://98.91.49.34:8000/api/demo/simulator/tiempo-virtual |
| Munin (monitoreo sistema) | http://98.91.49.34:8081 |
| Portainer (Docker UI) | http://98.91.49.34:9000 |

---

## Cómo ejecutar comandos en el servidor

### Opción A — AWS Session Manager (sin SSH, desde el navegador)

1. Abrir: https://us-east-1.console.aws.amazon.com/systems-manager/session-manager/sessions
2. Clic en **"Start session"** → seleccionar `energygrid-prod-ec2` → **"Start session"**
3. En la terminal:
   ```bash
   sudo su - ec2-user
   cd /opt/energygrid
   ```

### Opción B — Desde tu terminal local (SSH)

```bash
ssh -i ~/.ssh/energygrid-key.pem ec2-user@98.91.49.34
cd /opt/energygrid
```

---

## PASO 0 — Reinicio desde cero (fresh start)

> Ejecutar **desde Session Manager** o SSH. Borra todos los datos anteriores.

```bash
cd /opt/energygrid

# 1. Detener y borrar todo (incluyendo base de datos)
docker compose down -v

# 2. Limpiar logs antiguos
rm -f logs/spikes/* logs/alertas/*

# 3. Descargar imágenes más recientes (si hay deploy nuevo)
docker compose pull

# 4. Levantar toda la pila
docker compose up -d

# 5. Esperar 30 segundos a que todo arranque
sleep 30

# 6. Verificar estado de contenedores
docker compose ps
```

Salida esperada (todos `running` o `healthy`):
```
NAME                    STATUS
ENERGYGRID-DB           healthy
ENERGYGRID-REDIS        running
energygrid-backend-1    running
ENERGYGRID-NGINX        running
ENERGYGRID-FRONTEND     running
ENERGYGRID-SIMULATOR    running
ENERGYGRID-MUNIN-MASTER running
```

```bash
# 7. Activar monitoreo
curl -X POST http://98.91.49.34:8000/api/monitoring/start
```

---

## PREPARACIÓN ANTES DE LA DEMO

```bash
# Ver en qué minuto del ciclo está el simulador
curl http://98.91.49.34:8000/api/demo/simulator/tiempo-virtual

# Respuesta de ejemplo:
# {
#   "minuto_real_en_ciclo": 3.7,
#   "hora_virtual": 3.7,
#   "es_hora_pico": false,
#   "descripcion": "Periodo normal (baja demanda)",
#   "proximo_pico_en_seg": 438
# }

# Estado completo del simulador
curl http://98.91.49.34:8000/api/demo/simulator/health

# Reset del simulador (limpia sobrecargas y estados previos)
curl -X POST http://98.91.49.34:8000/api/demo/simulator/reset
```

---

## Demo 1 — Flujo normal de datos (1 segundo)

**Qué muestra**: El simulador envía datos de consumo cada 1 segundo. El frontend se actualiza en tiempo real vía WebSocket.

1. Abrir **http://98.91.49.34:3000**
2. Ver el mapa con los 4 distritos — las tarjetas se actualizan **cada segundo**
3. Colores según consumo:
   - Verde (< 75%) — normal
   - Amarillo (75–90%) — moderado
   - Naranja (90–95%) — advertencia
   - Rojo (≥ 95%) — sobrecarga crítica

**Evidencia** (desde Session Manager):
```bash
docker compose logs energygrid-backend | grep METRICA_RECIBIDA | tail -10
```

---

## Demo 2 — Ciclo automático de 24 minutos

**Qué muestra**: El consumo varía automáticamente sin intervención. La hora pico ocurre sola al minuto 12.

```bash
# Ver el tiempo virtual actual
curl http://98.91.49.34:8000/api/demo/simulator/tiempo-virtual
```

**Cronograma** para seguir en la demo:
- Minutos 0–11: consumo bajo/medio, colores verdes y amarillos
- **Minuto 11**: consumo empieza a subir
- **Minuto 12**: HORA PICO — todas las tarjetas suben a naranja/rojo (88-98%)
- Minuto 13+: consumo vuelve a bajar solo

**Evidencia en logs** (desde Session Manager):
```bash
docker compose logs -f energygrid-simulator | grep HORA-PICO
```

---

## Demo 3 — Spike automático cada 60 segundos

**Qué muestra**: Cada minuto, una subestación aleatoria sube a rojo sin intervención manual.

1. Abrir **http://98.91.49.34:3000** y observar el mapa
2. Cada ~60 segundos, una subestación al azar sube a rojo (96-100%)
3. El spike dura 30 segundos y se resuelve solo

```bash
# Ver cuál subestación tiene spike activo ahora
curl http://98.91.49.34:8000/api/demo/simulator/health
# Campo "auto_spike_sub" y "auto_spike_segundos_restantes"
```

**Evidencia**:
```bash
docker compose logs -f energygrid-simulator | grep AUTO-SPIKE
```

---

## Demo 4 — HORA PICO + Balanceo de Carga (el momento clave)

**Qué muestra**: A la hora pico (minuto 12), el consumo sube automáticamente al 88-98%. Escalamos a 2 backends para distribuir la carga. El frontend no se desconecta gracias a Redis.

### Seguimiento del ciclo

```bash
# Monitorear el tiempo virtual (correr esto antes del pico)
watch -n 5 'curl -s http://98.91.49.34:8000/api/demo/simulator/tiempo-virtual | python3 -m json.tool'
```

### Cuando el minuto llegue a ~10-11 (pre-pico):

**Paso 1** — Verificar que la hora pico está llegando:
```bash
curl http://98.91.49.34:8000/api/demo/simulator/tiempo-virtual
# "es_hora_pico": false, "proximo_pico_en_seg": 60 (aprox)
```

**Paso 2** — Escalar a 2 backends (ejecutar desde Session Manager):
```bash
cd /opt/energygrid
docker compose up --scale energygrid-backend=2 -d
```

**Paso 3** — Verificar que hay 2 instancias corriendo:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep backend
```

Salida esperada:
```
energygrid-backend-1    Up 2 minutes
energygrid-backend-2    Up 2 minutes
```

**Paso 4** — En el minuto 12, observar en el frontend:
- Todos los distritos suben a naranja/rojo (88-98%)
- El frontend **NO se desconecta** — Redis sincroniza WebSockets entre ambas instancias
- Los logs muestran tráfico distribuido entre `backend-1` y `backend-2`

**Evidencia** (desde Session Manager):
```bash
# Ver logs de ambas instancias en tiempo real
docker compose logs -f energygrid-backend
```

**Paso 5** — Después del minuto 13 (fin del pico), volver a 1 backend:
```bash
docker compose up -d
# Esto escala automáticamente a 1 instancia por defecto
```

```bash
# Verificar que volvimos a 1 backend
docker ps --format "table {{.Names}}\t{{.Status}}" | grep backend
```

---

## Demo 5 — Sobrecarga manual en un distrito

**Qué muestra**: Forzar sobrecarga en cualquier momento sin esperar el ciclo automático.

**Activar sobrecarga**:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/simulator/trigger-overload?district=San%20Salvador"
```

**Observar en frontend** — San Salvador se pone ROJO con alerta `SOBRECARGA_CRITICA`.

**Detener sobrecarga**:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/simulator/stop-overload?district=San%20Salvador"
```

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep SOBRECARGA
```

Distritos disponibles: `San Salvador`, `Antiguo Cuscatlan`, `Santa Tecla`, `Soyapango`

---

## Demo 6 — Caída de subestación

**Qué muestra**: Una subestación deja de enviar datos y el backend redistribuye la carga.

**Detener SSS001**:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/simulator/stop-substation?substation_id=SSS001"
```

**Esperar 15 segundos** → observar en frontend:
- Alerta `SUBESTACION_DESCONECTADA`
- Redistribución automática de carga

**Reactivar**:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/simulator/start-substation?substation_id=SSS001"
```

---

## Demo 7 — Timestamps inválidos

```bash
curl -X POST "http://98.91.49.34:8000/api/demo/simulator/invalid-timestamp?offset_days=2"
```

**Resultado esperado**: HTTP 422. El backend rechaza datos con timestamp de hace 2 días.

```bash
docker compose logs energygrid-backend | grep TIMESTAMP_INVALIDO
```

---

## Demo 8 — SQL Injection bloqueado

```bash
curl -X POST "http://98.91.49.34:8000/api/demo/simulator/malicious-input"
```

El payload `'; DROP TABLE consumo_temporal; --` es detectado y neutralizado por queries parametrizadas.

```bash
docker compose logs energygrid-backend | grep sospecha_sql
```

---

## Demo 9 — Dashboard de monitoreo

Abrir **http://98.91.49.34:8081** para ver gráficos históricos de CPU, RAM, disco y red.

```bash
# Estado general del sistema
curl http://98.91.49.34:8000/api/monitoring/health

# Dashboard completo
curl http://98.91.49.34:8000/api/monitoring/dashboard

# Alertas activas
curl http://98.91.49.34:8000/api/monitoring/alerts

# Queries lentas de PostgreSQL
curl http://98.91.49.34:8000/api/monitoring/queries/slow
```

---

## Demo 10 — Persistencia: caída de base de datos

```bash
# Detener la BD mientras el simulador sigue enviando datos (desde Session Manager)
cd /opt/energygrid
docker compose stop energygrid-db

# Ver que el backend encola datos en memoria
docker compose logs energygrid-backend | grep queue

# Reactivar la BD
docker compose start energygrid-db

# Los datos encolados se reinsertan automáticamente
curl http://98.91.49.34:8000/api/districts
```

---

## Comandos rápidos de referencia

Todos funcionan desde tu terminal local (no necesitan SSH):

```bash
# Estado del simulador
curl http://98.91.49.34:8000/api/demo/simulator/health

# Tiempo virtual actual
curl http://98.91.49.34:8000/api/demo/simulator/tiempo-virtual

# Reset completo del simulador
curl -X POST http://98.91.49.34:8000/api/demo/simulator/reset

# Activar monitoreo
curl -X POST http://98.91.49.34:8000/api/monitoring/start

# Health del backend
curl http://98.91.49.34:8000/health

# Distritos y consumo actual
curl http://98.91.49.34:8000/api/districts
```

Desde Session Manager (`/opt/energygrid`):

```bash
# Estado de contenedores
docker compose ps

# Logs en tiempo real
docker compose logs -f energygrid-simulator   # ciclo, picos, spikes
docker compose logs -f energygrid-backend     # alertas, métricas

# Escalar a 2 backends (para demo de balanceo)
docker compose up --scale energygrid-backend=2 -d

# Volver a 1 backend
docker compose up -d

# Uso de recursos
docker stats --no-stream
```

---

## Subestaciones disponibles

| ID | Nombre | Distrito | Capacidad |
|---|---|---|---|
| SSS001 | Subestación Centro | San Salvador | 5 000 kW |
| SSS002 | Subestación Norte | San Salvador | 4 500 kW |
| SAN001 | Subestación Antiguo | Antiguo Cuscatlán | 3 000 kW |
| STC001 | Subestación Santa Tecla | Santa Tecla | 3 500 kW |
| SAL001 | Subestación Soyapango | Soyapango | 4 000 kW |
