# Guía de Implementación y Demo — EnergyGrid

## Requisitos

- Docker Desktop (con Docker Compose v2)
- Git Bash (Windows) o terminal Linux/Mac
- Navegador web
- curl (para pruebas manuales)

## 1. Clonar e inicializar

```bash
git clone <repo-url> energygrid
cd energygrid
```

## 2. Crear archivo .env

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

Contenido mínimo de `.env`:

```env
POSTGRES_USER=energygrid_user
POSTGRES_PASSWORD=S3cur3P@ss2026
POSTGRES_DB=energygrid_db
POSTGRES_HOST=energygrid-db
POSTGRES_PORT=5432
POSTGRES_HOST_PORT=15432
BACKEND_PORT=8000
FRONTEND_PORT=3000
SIMULATOR_INTERVAL_MS=1000
JWT_SECRET=change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MUNIN_MASTER_URL=http://munin-master:8080
```

> **Nota Windows/Git Bash**: prefija todos los comandos docker con `MSYS2_ARG_CONV_EXCL="*"` para evitar que Git Bash convierta rutas. Ej: `MSYS2_ARG_CONV_EXCL="*" docker compose up -d`

## 3. Levantar el sistema

```bash
MSYS2_ARG_CONV_EXCL="*" docker compose up --build -d
```

Esto levanta 7 servicios:
- `energygrid-db` — PostgreSQL 15 con pg_stat_statements
- `energygrid-redis` — Redis 7 para pub/sub multi-instancia
- `energygrid-backend` — API FastAPI (1 instancia)
- `energygrid-nginx` — Reverse proxy con WebSocket support
- `energygrid-frontend` — React + Leaflet
- `energygrid-simulator` — Generador de telemetría
- `munin-master` — Monitoreo Munin con gráficos históricos

### Verificar que todo funciona

```bash
# Estado de los contenedores
docker ps

# API responde
curl http://localhost:8000/health

# Frontend
abrir http://localhost:3000

# Munin gráficos
abrir http://localhost:8081
```

## 4. Activar monitoreo

El dashboard de monitoreo (Munin + Pingdom + pg_stat_statements) requiere activación manual:

```bash
curl -X POST http://localhost:8000/api/monitoring/start
```

Verificar estado:

```bash
curl http://localhost:8000/api/monitoring/status
```

Debe mostrar `"monitoring_active": true`.

## 5. Servicios y puertos

| Servicio | Puerto Host | Puerto Interno | Acceso |
|---|---|---|---|
| Frontend | 3000 | 80 | http://localhost:3000 |
| API (vía nginx) | 8000 | 8000 | http://localhost:8000 |
| PostgreSQL | 15432 | 5432 | Solo interno |
| Simulador | — | 8001 | Solo interno |
| Munin Master | 8081 | 8080 | http://localhost:8081 |
| Redis | — | 6379 | Solo interno |
| Munin Node | — | 4949 | Solo interno |

---

# GUÍA DE DEMO — Qué mostrar paso a paso

## Demo 1: Flujo normal de datos

**Qué**: El simulador envía datos de consumo cada 1s. El frontend los muestra en tiempo real.

**Pasos**:
1. Abrir http://localhost:3000
2. Ver el mapa con los distritos de El Salvador
3. Cada distrito tiene un color según consumo:
   - **Verde** (< 75%) — normal
   - **Amarillo** (75-90%) — moderado
   - **Naranja** (90-95%) — advertencia
   - **Rojo** (>= 95%) — sobrecarga crítica
4. Hacer clic en un distrito para ver detalle (consumo kW, porcentaje, subestaciones)
5. Las tarjetas se actualizan solas vía WebSocket

**Evidencia**: `docker compose logs energygrid-backend | grep METRICA_RECIBIDA`

---

## Demo 2: Alerta 1 — Sobrecarga > 95%

**Qué**: Forzar sobrecarga en un distrito, el backend detecta, alerta y redistribuye.

**Pasos**:
1. Tener el frontend abierto en http://localhost:3000
2. Ejecutar:
   ```bash
   curl -X POST "http://localhost:8001/simulator/trigger-overload?district=San%20Salvador"
   ```
3. Observar en el frontend:
   - San Salvador se pone **ROJO**
   - Aparece alerta en el panel lateral "SOBRECARGA_CRITICA"
   - Suena notificación (beep)
   - Aparece sugerencia de redistribución con distritos disponibles
4. Opcional: aplicar redistribución manual desde la tarjeta del distrito
5. Detener sobrecarga:
   ```bash
   curl -X POST "http://localhost:8001/simulator/stop-overload?district=San%20Salvador"
   ```
6. La alerta se auto-resuelve cuando baja de 95%

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep SOBRECARGA
```
Muestra logs JSON con `event: "SOBRECARGA"`, `porcentaje: 96.52`, `action: "redistribucion_sugerida"`.

---

## Demo 3: Alerta 2 — Escalar a 2 Backends

**Qué**: Activar hora pico, escalar el backend a 2 instancias, ver que el frontend no se desconecta.

**Pasos**:
1. Tener el frontend abierto en http://localhost:3000
2. Activar hora pico (burst de datos 3x):
   ```bash
   curl -X POST "http://localhost:8001/simulator/trigger-peak-hour"
   ```
3. Escalar el backend:
   ```bash
   MSYS2_ARG_CONV_EXCL="*" docker compose up --scale energygrid-backend=2 -d
   ```
4. Verificar:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```
   Deben aparecer `energygrid-energygrid-backend-1` y `energygrid-energygrid-backend-2`
5. El frontend **no se desconecta** — Redis pub/sub mantiene los WebSocket sincronizados
6. nginx distribuye el tráfico entre los 2 backends (ip_hash)
7. Detener hora pico:
   ```bash
   curl -X POST "http://localhost:8001/simulator/stop-peak-hour"
   ```
8. Volver a 1 backend:
   ```bash
   MSYS2_ARG_CONV_EXCL="*" docker compose up -d
   ```

**Evidencia**: Frontend funcionando sin interrupción durante todo el escalado.

---

## Demo 4: Caída de subestación

**Qué**: Simular que una subestación deja de enviar datos, el backend lo detecta y redistribuye carga.

**Pasos**:
1. Identificar subestaciones en el frontend (SSS001 = Subestación Centro, San Salvador)
2. Detener una subestación:
   ```bash
   curl -X POST "http://localhost:8001/simulator/stop-substation?substation_id=SSS001"
   ```
3. Esperar 15 segundos
4. Observar:
   - Aparece alerta `SUBESTACION_DESCONECTADA`
   - Backend redistribuye carga automáticamente a SSS002 u otros distritos
   - El banner de redistribución muestra las sugerencias
5. Reactivar la subestación:
   ```bash
   curl -X POST "http://localhost:8001/simulator/start-substation?substation_id=SSS001"
   ```
6. La alerta se resuelve automáticamente al recibir datos de nuevo

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep SUBESTACION_DESCONECTADA
```

---

## Demo 5: Timestamps inválidos

**Qué**: El backend rechaza datos con timestamps fuera de rango.

**Pasos**:
```bash
curl -X POST "http://localhost:8001/simulator/invalid-timestamp?offset_days=2"
```

**Resultado esperado**: Backend responde HTTP 422 y loguea:
```bash
docker compose logs energygrid-backend | grep TIMESTAMP_INVALIDO
```

---

## Demo 6: SQL Injection

**Qué**: El backend bloquea intentos de SQL injection y los registra.

**Pasos**:
```bash
curl -X POST "http://localhost:8001/simulator/malicious-input"
```

**Resultado esperado**: El payload con `'; DROP TABLE consumo_temporal; --` es detectado por el regex `[;'\" ]|--`, se marca como anomalía, la query parametrizada lo trata como string literal inofensivo, y se registra en logs:
```bash
docker compose logs energygrid-backend | grep sospecha_sql
```

---

## Demo 7: Dashboard de monitoreo (Munin + Pingdom + pg_stat)

**Qué**: Mostrar las 3 herramientas de monitoreo integradas.

**Pasos**:
1. Activar monitoreo (si no está activo):
   ```bash
   curl -X POST http://localhost:8000/api/monitoring/start
   ```
2. Dashboard web:
   - Abrir http://localhost:8000/dashboard
   - Muestra health score, métricas del sistema, estado de endpoints, alertas
3. Munin gráficos históricos:
   - Abrir http://localhost:8081
   - Ver gráficos de CPU, memoria, disco, carga, red, procesos
4. API endpoints de monitoreo:
   ```bash
   # Estado general
   curl http://localhost:8000/api/monitoring/health
   
   # Dashboard completo
   curl http://localhost:8000/api/monitoring/dashboard
   
   # Alertas unificadas
   curl http://localhost:8000/api/monitoring/alerts
   
   # Métricas Munin
   curl http://localhost:8000/api/monitoring/munin/metrics
   
   # Estado Pingdom
   curl http://localhost:8000/api/monitoring/pingdom/status
   
   # Queries lentas
   curl http://localhost:8000/api/monitoring/queries/slow
   
   # pg_stat_statements
   curl http://localhost:8000/api/monitoring/queries/pg_stats
   ```

---

## Demo 8: Persistencia y tolerancia a fallos

### Caída de BD con simulador activo
```bash
# Detener BD
docker compose stop energygrid-db

# Ver logs: backend encola datos en memoria
docker compose logs energygrid-backend | grep "queue"

# Reactivar BD
docker compose start energygrid-db

# Verificar: los datos encolados se reinsertan
```

### Persistencia de datos
```bash
# Detener todo
docker compose down

# Levantar de nuevo
MSYS2_ARG_CONV_EXCL="*" docker compose up -d

# Verificar: datos históricos siguen presentes
curl http://localhost:8000/api/districts
```

---

## Resumen de URLs útiles

| URL | Qué muestra |
|---|---|
| http://localhost:3000 | Frontend principal (mapa + alertas) |
| http://localhost:8000/dashboard | Dashboard de monitoreo |
| http://localhost:8000/docs | Swagger UI de la API |
| http://localhost:8000/health | Health check |
| http://localhost:8081 | Munin gráficos históricos |
| http://localhost:8001/docs | Swagger del simulador |

## Comandos rápidos

```bash
# Levantar todo
MSYS2_ARG_CONV_EXCL="*" docker compose up --build -d

# Escalar a 2 backends
MSYS2_ARG_CONV_EXCL="*" docker compose up --scale energygrid-backend=2 -d

# Volver a 1 backend
MSYS2_ARG_CONV_EXCL="*" docker compose up -d

# Ver logs
docker compose logs -f energygrid-backend

# Detener todo
docker compose down

# Detener todo + borrar volúmenes (pierde datos)
docker compose down -v
```

## Solución de problemas comunes

| Problema | Solución |
|---|---|
| `invalid file request Dockerfile` | Prefijar con `MSYS2_ARG_CONV_EXCL="*"` |
| Backend no conecta a BD | Esperar healthcheck de DB (~10s) |
| Frontend en blanco | Verificar `docker compose logs energygrid-frontend` |
| WebSocket desconecta | Verificar Redis: `docker compose logs energygrid-redis` |
| Munin no muestra gráficos | Ejecutar `curl -X POST http://localhost:8000/api/monitoring/start` |
| `container_name` conflict al escalar | Ya resuelto — backend no tiene `container_name` fijo |
