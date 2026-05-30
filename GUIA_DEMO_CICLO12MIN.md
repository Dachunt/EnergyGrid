# Guía de Demo — EnergyGrid (Ciclo 24 minutos)

## Comportamiento del simulador

| Parámetro | Valor |
|---|---|
| Intervalo de envío | **1 segundo** |
| Ciclo día virtual | **24 minutos** |
| 1 hora virtual equivale a | **60 segundos reales** |
| Hora pico automática | **11h–13h virtual (minuto 11–13 real)** |
| Spike automático | **Cada 60 seg en subestación aleatoria, dura 30 seg** |

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

## Cómo ejecutar los comandos

### Desde SSH
```bash
ssh -i ~/.ssh/energygrid-key.pem ec2-user@98.91.49.34
cd /opt/energygrid
```

### Desde AWS Session Manager (navegador)
1. Ir a: https://us-east-1.console.aws.amazon.com/systems-manager/session-manager/sessions
2. **Start session** → seleccionar `energygrid-prod-ec2` → **Start session**
3. En la terminal:
   ```bash
   sudo su - ec2-user && cd /opt/energygrid
   ```

---

## URLs del sistema

| Recurso | URL |
|---|---|
| Frontend | http://98.91.49.34:3000 |
| API REST + WebSocket | http://98.91.49.34:8000 |
| API Docs (Swagger) | http://98.91.49.34:8000/docs |
| Munin (monitoreo) | http://98.91.49.34:8081 |
| Portainer (Docker UI) | http://98.91.49.34:9000 |

---

## Preparación antes de la demo

```bash
# 1. Verificar que todos los contenedores están corriendo
docker compose ps

# 2. Verificar el simulador con los nuevos parámetros
curl http://localhost:8001/health

# 3. Ver en qué minuto del ciclo está ahora
curl http://localhost:8001/simulator/tiempo-virtual

# 4. Activar monitoreo
curl -X POST http://localhost:8000/api/monitoring/start

# 5. Reset del simulador (limpia cualquier estado previo)
curl -X POST http://localhost:8001/simulator/reset
```

---

## Demo 1: Observar el ciclo automático de 12 minutos

**Qué muestra**: El sistema varía el consumo automáticamente sin intervención. La hora pico ocurre sola al minuto 6.

**Pasos**:
1. Abrir **http://98.91.49.34:3000**
2. Consultar el tiempo virtual actual:
   ```bash
   curl http://localhost:8001/simulator/tiempo-virtual
   ```
   Respuesta de ejemplo:
   ```json
   {
     "minuto_real_en_ciclo": 2.3,
     "hora_virtual": 4.6,
     "es_hora_pico": false,
     "descripcion": "Periodo normal (baja demanda)",
     "proximo_pico_en_seg": 438
   }
   ```
3. Esperar al **minuto 12** del ciclo — las tarjetas de todos los distritos subirán automáticamente a colores naranja/rojo
4. Observar que al minuto ~13 el consumo vuelve a bajar solo

**Evidencia en logs**:
```bash
docker compose logs -f energygrid-simulator | grep HORA-PICO
```

---

## Demo 2: Spike automático cada 60 segundos

**Qué muestra**: El simulador inyecta un pico automático en una subestación aleatoria cada minuto, sin intervención manual.

**Pasos**:
1. Abrir **http://98.91.49.34:3000** y observar el mapa
2. Cada ~60 segundos, una subestación al azar subirá a rojo (sobrecarga 96-100%)
3. El spike dura 30 segundos y luego se resuelve solo
4. Verificar en tiempo real cuál subestación tiene el spike activo:
   ```bash
   curl http://localhost:8001/health
   ```
   El campo `auto_spike_sub` muestra cuál está en pico y `auto_spike_segundos_restantes` cuánto dura.

**Evidencia en logs**:
```bash
docker compose logs -f energygrid-simulator | grep AUTO-SPIKE
```

---

## Demo 3: Sobrecarga manual en un distrito

**Qué muestra**: Forzar sobrecarga en un distrito completo. Todas sus subestaciones superan el 95%.

**Activar sobrecarga**:
```bash
curl -X POST "http://localhost:8001/simulator/trigger-overload?district=San%20Salvador"
```

**Observar en frontend**:
- San Salvador se pone **ROJO**
- Panel lateral muestra alerta `SOBRECARGA_CRITICA`
- Sugerencia de redistribución

**Detener sobrecarga**:
```bash
curl -X POST "http://localhost:8001/simulator/stop-overload?district=San%20Salvador"
```

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep SOBRECARGA
```

---

## Demo 4: Escalar a 2 backends durante hora pico (minuto 12)

**Qué muestra**: Alta carga en minuto 12 → escalar horizontalmente → el frontend no se desconecta (Redis mantiene WebSockets).

**Paso 1** — Verificar que el pico está llegando (ejecutar alrededor del minuto 10-11):
```bash
curl http://localhost:8001/simulator/tiempo-virtual
# "proximo_pico_en_seg" debe ser < 120
```

**Paso 2** — Escalar a 2 backends:
```bash
docker compose up --scale energygrid-backend=2 -d
```

**Paso 3** — Verificar 2 instancias:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep backend
```

**Paso 4** — En el minuto 12, todos los distritos suben a naranja/rojo. El frontend **no se desconecta**.

**Paso 5** — Volver a 1 instancia después del pico (minuto 13+):
```bash
docker compose up -d
```

---

## Demo 5: Caída de subestación

**Qué muestra**: Una subestación deja de enviar datos y el backend redistribuye carga.

**Detener subestación SSS001**:
```bash
curl -X POST "http://localhost:8001/simulator/stop-substation?substation_id=SSS001"
```

**Esperar 15 segundos** → observar en frontend:
- Alerta `SUBESTACION_DESCONECTADA`
- Redistribución automática

**Reactivar**:
```bash
curl -X POST "http://localhost:8001/simulator/start-substation?substation_id=SSS001"
```

**Evidencia**:
```bash
docker compose logs energygrid-backend | grep SUBESTACION_DESCONECTADA
```

---

## Demo 6: Timestamps inválidos

```bash
curl -X POST "http://localhost:8001/simulator/invalid-timestamp?offset_days=2"
```

**Resultado**: HTTP 422. El backend rechaza datos con timestamp de hace 2 días.

```bash
docker compose logs energygrid-backend | grep TIMESTAMP_INVALIDO
```

---

## Demo 7: SQL Injection bloqueado

```bash
curl -X POST "http://localhost:8001/simulator/malicious-input"
```

**Resultado**: El payload `'; DROP TABLE consumo_temporal; --` es detectado, registrado y neutralizado por queries parametrizadas.

```bash
docker compose logs energygrid-backend | grep sospecha_sql
```

---

## Demo 8: Dashboard de monitoreo

```bash
# Estado general del sistema
curl http://localhost:8000/api/monitoring/health

# Dashboard completo (JSON)
curl http://localhost:8000/api/monitoring/dashboard

# Alertas activas
curl http://localhost:8000/api/monitoring/alerts

# Métricas del sistema (Munin)
curl http://localhost:8000/api/monitoring/munin/metrics

# Queries lentas de PostgreSQL
curl http://localhost:8000/api/monitoring/queries/slow
```

También abrir **http://98.91.49.34:8081** para ver los gráficos históricos de Munin (CPU, RAM, disco, red).

---

## Demo 8: Persistencia — caída de base de datos

```bash
# Detener la BD mientras el simulador sigue enviando datos
docker compose stop energygrid-db

# Ver que el backend encola datos en memoria
docker compose logs energygrid-backend | grep queue

# Reactivar la BD
docker compose start energygrid-db

# Los datos encolados durante la caída se reinsertan automáticamente
curl http://localhost:8000/api/districts
```

---

## Comandos rápidos de referencia

```bash
# Ver estado de todos los contenedores
docker compose ps

# Ver tiempo virtual actual del simulador (desde EC2)
curl http://localhost:8001/simulator/tiempo-virtual

# Ver tiempo virtual (desde fuera, sin SSH)
curl http://98.91.49.34:8000/api/demo/simulator/tiempo-virtual

# Ver health del simulador (incluye auto-spike activo)
curl http://localhost:8001/health
# Desde fuera:
curl http://98.91.49.34:8000/api/demo/simulator/health

# Reset completo del simulador
curl -X POST http://localhost:8001/simulator/reset
# Desde fuera:
curl -X POST http://98.91.49.34:8000/api/demo/simulator/reset

# Logs en tiempo real
docker compose logs -f energygrid-simulator   # ciclo, picos, spikes
docker compose logs -f energygrid-backend     # alertas, métricas recibidas

# Escalar backend (para demo de balanceo en minuto 12)
docker compose up --scale energygrid-backend=2 -d

# Volver a 1 backend
docker compose up -d

# Estadísticas de recursos
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

## Distritos disponibles para sobrecarga manual

- `San Salvador`
- `Antiguo Cuscatlan`
- `Santa Tecla`
- `Soyapango`
