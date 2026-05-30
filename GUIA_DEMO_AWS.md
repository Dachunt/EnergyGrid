# Guía de Demo — EnergyGrid en AWS

> Versión adaptada para el servidor desplegado en `98.91.49.34`.
> Todos los `localhost` han sido reemplazados por la IP pública de la EC2.

---

## Cómo ejecutar comandos en el servidor (sin SSH)

Tienes dos opciones desde el navegador:

### Opción A — AWS Systems Manager Session Manager (recomendado)

Es una terminal completa dentro de la consola de AWS. No necesitas clave SSH.

1. Abre: **https://us-east-1.console.aws.amazon.com/systems-manager/session-manager/sessions**
2. Clic en **"Start session"**
3. Selecciona la instancia **`energygrid-prod-ec2`**
4. Clic en **"Start session"**
5. Se abre una terminal. Cambia al usuario correcto:
   ```bash
   sudo su - ec2-user
   cd /opt/energygrid
   ```
6. Ya puedes ejecutar cualquier comando `docker compose`, `curl`, etc.

### Opción B — Portainer (solo comandos Docker)

Para comandos de gestión de contenedores:

1. Abre: **http://98.91.49.34:9000**
2. Login con tu usuario de Portainer
3. Ve a **Stacks → energygrid**
4. Desde ahí puedes editar el compose, escalar servicios y ver logs

---

## URLs del sistema desplegado

| Recurso | URL |
|---|---|
| Frontend (interfaz web) | http://98.91.49.34:3000 |
| Backend API | http://98.91.49.34:8000 |
| API Docs (Swagger) | http://98.91.49.34:8000/docs |
| Dashboard monitoreo | http://98.91.49.34:8000/dashboard |
| Munin gráficos | http://98.91.49.34:8081 |
| Swagger Simulador | http://98.91.49.34:8000/docs |
| Portainer (Docker UI) | http://98.91.49.34:9000 |

---

## Antes de empezar — activar monitoreo

Ejecuta esto una vez al iniciar la demo (desde Session Manager o curl):

```bash
curl -X POST http://98.91.49.34:8000/api/monitoring/start
curl http://98.91.49.34:8000/api/monitoring/status
```

Debe mostrar `"monitoring_active": true`.

---

## Demo 1: Flujo normal de datos

**Qué muestra**: El simulador envía datos de consumo cada 1s. El frontend los muestra en tiempo real vía WebSocket.

**Pasos**:
1. Abrir **http://98.91.49.34:3000**
2. Ver el mapa con los 4 distritos de El Salvador
3. Cada distrito tiene color según consumo:
   - Verde (< 75%) — normal
   - Amarillo (75–90%) — moderado
   - Naranja (90–95%) — advertencia
   - Rojo (≥ 95%) — sobrecarga crítica
4. Las tarjetas se actualizan solas cada segundo

**Evidencia** (desde Session Manager):
```bash
docker compose logs energygrid-backend | grep METRICA_RECIBIDA
```

---

## Demo 2: Alerta — Sobrecarga > 95%

**Qué muestra**: Forzar sobrecarga en un distrito, el backend detecta y redistribuye.

**Paso 1** — Abrir el frontend:
```
http://98.91.49.34:3000
```

**Paso 2** — Forzar sobrecarga desde Session Manager o tu terminal:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/trigger-overload?district=San%20Salvador"
```

**Paso 3** — Observar en el frontend:
- San Salvador se pone **ROJO**
- Aparece alerta `SOBRECARGA_CRITICA` en el panel lateral
- Sugerencia de redistribución

**Paso 4** — Detener sobrecarga:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/stop-overload?district=San%20Salvador"
```

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep SOBRECARGA
```

---

## Demo 3: Escalar a 2 Backends (hora pico)

**Qué muestra**: Alta carga → escalar backend → el frontend no se desconecta gracias a Redis pub/sub.

**Paso 1** — Activar hora pico:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/trigger-peak-hour"
```

**Paso 2** — Escalar a 2 instancias de backend (desde Session Manager):
```bash
cd /opt/energygrid
docker compose up --scale energygrid-backend=2 -d
```

**Paso 3** — Verificar que hay 2 backends corriendo:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep backend
```

Deben aparecer `energygrid-backend-1` y `energygrid-backend-2`.

**Paso 4** — El frontend **sigue funcionando sin desconectarse** — Redis sincroniza los WebSocket entre ambas instancias.

**Paso 5** — Detener hora pico y volver a 1 backend:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/stop-peak-hour"
docker compose up -d
```

---

## Demo 4: Caída de subestación

**Qué muestra**: Una subestación deja de enviar datos y el backend redistribuye carga.

**Paso 1** — Detener subestación SSS001:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/stop-substation?substation_id=SSS001"
```

**Paso 2** — Esperar 15 segundos y observar en el frontend:
- Alerta `SUBESTACION_DESCONECTADA`
- Redistribución automática de carga

**Paso 3** — Reactivar:
```bash
curl -X POST "http://98.91.49.34:8000/api/demo/start-substation?substation_id=SSS001"
```

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep SUBESTACION_DESCONECTADA
```

---

## Demo 5: Timestamps inválidos

```bash
curl -X POST "http://98.91.49.34:8000/api/demo/invalid-timestamp?offset_days=2"
```

**Resultado esperado**: HTTP 422. Verificar en logs:
```bash
docker compose logs energygrid-backend | grep TIMESTAMP_INVALIDO
```

---

## Demo 6: SQL Injection bloqueado

```bash
curl -X POST "http://98.91.49.34:8000/api/demo/malicious-input"
```

**Resultado**: El payload `'; DROP TABLE consumo_temporal; --` es detectado, registrado y neutralizado.

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep sospecha_sql
```

---

## Demo 7: Dashboard de monitoreo

1. Abrir **http://98.91.49.34:8000/dashboard** — health score, métricas, estado de endpoints
2. Abrir **http://98.91.49.34:8081** — gráficos históricos de Munin (CPU, RAM, disco, red)
3. API de monitoreo:

```bash
# Estado general
curl http://98.91.49.34:8000/api/monitoring/health

# Dashboard completo
curl http://98.91.49.34:8000/api/monitoring/dashboard

# Alertas unificadas
curl http://98.91.49.34:8000/api/monitoring/alerts

# Métricas Munin
curl http://98.91.49.34:8000/api/monitoring/munin/metrics

# Estado Pingdom
curl http://98.91.49.34:8000/api/monitoring/pingdom/status

# Queries lentas
curl http://98.91.49.34:8000/api/monitoring/queries/slow

# pg_stat_statements
curl http://98.91.49.34:8000/api/monitoring/queries/pg_stats
```

---

## Demo 8: Persistencia y tolerancia a fallos

### Caída de BD con simulador activo
```bash
cd /opt/energygrid

# Detener BD
docker compose stop energygrid-db

# Ver que el backend encola datos en memoria
docker compose logs energygrid-backend | grep queue

# Reactivar BD
docker compose start energygrid-db

# Los datos encolados se reinsertan automáticamente
```

### Verificar persistencia de datos
```bash
# Reiniciar la pila completa
docker compose down
docker compose up -d

# Los datos históricos siguen presentes
curl http://98.91.49.34:8000/api/districts
```

---

## Comandos rápidos (desde Session Manager en /opt/energygrid)

```bash
# Ver estado de todos los contenedores
docker compose ps

# Ver logs en tiempo real de un servicio
docker compose logs -f energygrid-backend
docker compose logs -f energygrid-simulator
docker compose logs -f energygrid-db

# Escalar a 2 backends
docker compose up --scale energygrid-backend=2 -d

# Volver a 1 backend
docker compose up -d

# Reiniciar un servicio
docker compose restart energygrid-backend

# Ver uso de CPU y RAM por contenedor
docker stats --no-stream

# Detener todo (sin borrar datos)
docker compose down

# Detener todo y borrar datos
docker compose down -v
```

---

## Dónde ver los logs guardados en disco

```bash
# Logs estructurados del backend (JSON)
tail -f /opt/energygrid/logs/energygrid.log

# Picos detectados
ls /opt/energygrid/logs/spikes/
cat /opt/energygrid/logs/spikes/<archivo>

# Alertas registradas
ls /opt/energygrid/logs/alertas/
```
