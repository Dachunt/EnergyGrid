# Guía de Ejecución — EnergyGrid

## Accesos del sistema desplegado

| Recurso | URL |
|---|---|
| Frontend (interfaz web) | http://98.91.49.34:3000 |
| Backend API REST | http://98.91.49.34:8000 |
| Documentación API (Swagger) | http://98.91.49.34:8000/docs |
| Monitoreo Munin | http://98.91.49.34:8081 |

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `Admin123!`

---

## Opción A — Ejecución local con Docker Compose

### Prerrequisitos
- Docker Desktop instalado y corriendo
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Dachunt/EnergyGrid.git
cd EnergyGrid

# 2. Copiar y editar variables de entorno
cp .env.example .env
# Editar .env con tus valores (usuario, contraseña DB, JWT secret)

# 3. Crear directorios de logs
mkdir -p logs/spikes logs/alertas

# 4. Levantar todo el ecosistema
docker compose up --build -d

# 5. Ver logs en tiempo real
docker compose logs -f

# 6. Verificar que todos los servicios están corriendo
docker compose ps
```

### Accesos locales

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Munin | http://localhost:8081 |

### Apagar el sistema

```bash
# Apagar sin borrar datos
docker compose down

# Apagar y borrar todos los datos (base de datos, logs, métricas)
docker compose down -v
```

---

## Opción B — Ejecución en AWS (servidor ya desplegado)

El servidor EC2 ya está corriendo en `98.91.49.34`. Los contenedores se reinician automáticamente si el servidor se reinicia (configurado con `restart: unless-stopped`).

### Conectarse al servidor por SSH

```bash
ssh -i ~/.ssh/energygrid-key.pem ec2-user@98.91.49.34
```

### Comandos útiles en el servidor

```bash
# Ver estado de todos los contenedores
cd /opt/energygrid
docker compose ps

# Ver logs de un servicio específico
docker compose logs -f energygrid-backend
docker compose logs -f energygrid-db
docker compose logs -f energygrid-simulator

# Reiniciar un servicio sin bajar los demás
docker compose restart energygrid-backend

# Reiniciar toda la pila
docker compose down && docker compose up -d

# Ver uso de recursos (CPU/RAM por contenedor)
docker stats --no-stream
```

### Actualizar el código desde GitHub

```bash
cd /opt/energygrid
git pull origin master
docker compose up --build -d
```

### Actualizar variables de entorno

```bash
# Editar el .env
nano /opt/energygrid/.env

# Reiniciar para aplicar cambios
docker compose down -v
docker compose up -d
```

---

## Variables de entorno (.env)

| Variable | Descripción | Valor actual |
|---|---|---|
| `POSTGRES_USER` | Usuario de PostgreSQL | `energygrid_user` |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `S3cur3P@ss2026` |
| `POSTGRES_DB` | Nombre de la base de datos | `energygrid_db` |
| `POSTGRES_HOST` | Host de la DB (nombre del contenedor) | `energygrid-db` |
| `POSTGRES_PORT` | Puerto interno de PostgreSQL | `5432` |
| `POSTGRES_HOST_PORT` | Puerto expuesto al host | `15432` |
| `BACKEND_PORT` | Puerto del backend/nginx | `8000` |
| `FRONTEND_PORT` | Puerto del frontend | `3000` |
| `SIMULATOR_INTERVAL_MS` | Intervalo del simulador en ms | `1000` |
| `JWT_SECRET` | Clave secreta para tokens JWT | *(ver .env)* |
| `JWT_ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración del token | `1440` |
| `PINGDOM_API_TOKEN` | Token API de Pingdom | *(ver .env)* |
| `PINGDOM_EMAIL` | Email de cuenta Pingdom | *(ver .env)* |
| `MUNIN_MASTER_URL` | URL interna de Munin | `http://munin-master:8080` |
| `REDIS_URL` | URL de Redis | `redis://energygrid-redis:6379` |

---

## Servicios y contenedores

| Contenedor | Imagen | Puerto | Función |
|---|---|---|---|
| `ENERGYGRID-DB` | postgres:15-alpine | 15432 | Base de datos PostgreSQL |
| `ENERGYGRID-REDIS` | redis:7-alpine | interno | Cache y pub/sub WebSocket |
| `energygrid-backend` | build ./backend | interno | API FastAPI + Munin node |
| `ENERGYGRID-NGINX` | build ./docker/nginx | 8000 | Proxy reverso hacia el backend |
| `ENERGYGRID-FRONTEND` | build ./frontend | 3000 | React SPA (Vite + Nginx) |
| `ENERGYGRID-SIMULATOR` | build ./simulator | interno | Generador de métricas de energía |
| `ENERGYGRID-MUNIN-MASTER` | build ./docker/munin-master | 8081 | Dashboard de monitoreo del servidor |

### Orden de inicio (dependencias)

```
PostgreSQL ──┐
             ├──► Backend ──┬──► Nginx (puerto 8000)
Redis ───────┘              ├──► Simulator
                            ├──► Frontend (puerto 3000)
                            └──► Munin Master (puerto 8081)
```

---

## Verificar que el sistema funciona

### 1. Health check del backend
```bash
curl http://98.91.49.34:8000/health
# Respuesta esperada: {"status":"ok"}
```

### 2. Probar login por API
```bash
curl -X POST http://98.91.49.34:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!"}'
```

### 3. Ver distritos
```bash
# Primero obtener token del login, luego:
curl http://98.91.49.34:8000/api/districts \
  -H "Authorization: Bearer <TOKEN>"
```

### 4. Ver métricas en tiempo real
Abrir el frontend en el navegador → las tarjetas de distritos se actualizan cada segundo vía WebSocket.

---

## Solución de problemas frecuentes

### El frontend muestra pantalla en blanco o no carga datos
El frontend fue compilado con la URL del backend embebida. Si cambia la IP del servidor hay que reconstruir:

```bash
cd /opt/energygrid
docker compose build \
  --build-arg VITE_API_BASE=http://<NUEVA_IP>:8000 \
  energygrid-frontend
docker compose up -d --no-deps energygrid-frontend
```

### El backend no conecta a la base de datos
```bash
# Ver logs de PostgreSQL
docker compose logs energygrid-db | tail -20

# Verificar healthcheck
docker inspect ENERGYGRID-DB | grep -A5 Health
```

### Memoria insuficiente en EC2 (t2.micro tiene 1 GB)
```bash
# Ver uso de memoria
free -h
docker stats --no-stream

# Ver si hay swap activo (debe haber 1 GB configurado)
swapon --show
```

### Reiniciar el servidor completo
```bash
# En EC2
sudo reboot
# Los contenedores se reinician solos al volver (restart: unless-stopped)
```
