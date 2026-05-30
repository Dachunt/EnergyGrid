# Explicación de la Integración — EnergyGrid en AWS

Este documento explica paso a paso qué se hizo, por qué, y cómo cada pieza encaja con las demás.

---

## 1. Punto de partida

El proyecto ya existía localmente con un `docker-compose.yml` funcional que levantaba 7 servicios:
PostgreSQL, Redis, Backend (FastAPI), Nginx, Frontend (React/Vite), Simulator y Munin.

El objetivo era llevarlo a AWS usando recursos gratuitos (Free Tier) y crear la infraestructura como código (IaC) con Terraform.

---

## 2. Arquitectura elegida y por qué

### Decisión: todo en una sola EC2 t2.micro

Se evaluaron tres opciones:

| Opción | Recursos | Costo |
|---|---|---|
| EC2 + RDS + S3 | EC2, RDS PostgreSQL, S3/CloudFront | ~$0 primer año, luego ~$15/mes |
| ECS Fargate | Fargate tasks, ALB, RDS | ~$30-50/mes (NO es free tier) |
| **EC2 t2.micro todo-en-uno** | Solo EC2 + ECR | **$0 (12 meses free tier)** |

Se eligió la tercera porque:
- La t2.micro (1 vCPU, 1 GB RAM) es suficiente para una demo con 7 contenedores ligeros
- Es la que entra en el Free Tier de AWS sin restricciones
- Mantiene la misma lógica del `docker-compose.yml` original sin reescribir nada

### Diagrama final

```
Internet
    │
    ▼
EC2 t2.micro (98.91.49.34) — Amazon Linux 2023
    │
    ├── :3000  → ENERGYGRID-FRONTEND  (React compilado + Nginx)
    ├── :8000  → ENERGYGRID-NGINX     (proxy → backend FastAPI)
    └── :8081  → ENERGYGRID-MUNIN     (monitoreo del servidor)

          Internos (sin exponer al exterior):
          ├── energygrid-backend  (FastAPI + uvicorn)
          ├── ENERGYGRID-DB       (PostgreSQL 15)
          ├── ENERGYGRID-REDIS    (Redis 7)
          └── ENERGYGRID-SIMULATOR

AWS ECR — almacena las 5 imágenes Docker del proyecto
```

---

## 3. Infraestructura como Código (Terraform)

Se crearon los archivos Terraform en `infra/terraform/` divididos en 3 módulos:

### Módulo `networking/`
Crea la red base de AWS:
- **VPC** (`10.0.0.0/16`): red virtual privada aislada
- **Subnet pública** (`10.0.1.0/24`): donde vive la EC2
- **Internet Gateway**: permite que la EC2 salga a internet
- **Route Table**: conecta la subnet al gateway
- **Security Group**: el "firewall" de la EC2, que permite entrada solo en los puertos 22 (SSH), 3000, 8000 y 8081

### Módulo `ecr/`
Crea 5 repositorios en AWS Elastic Container Registry (ECR):
- `energygrid-backend`
- `energygrid-frontend`
- `energygrid-simulator`
- `energygrid-nginx`
- `energygrid-munin-master`

Cada repositorio tiene una política de limpieza que mantiene solo las últimas 5 imágenes, para no superar el límite gratuito de 500 MB de ECR.

### Módulo `ec2/`
Crea el servidor y sus permisos:
- **IAM Role + Instance Profile**: permite que la EC2 descargue imágenes de ECR sin necesitar credenciales explícitas
- **EC2 t2.micro**: instancia con Amazon Linux 2023 y disco de 30 GB (mínimo requerido por la AMI)
- **Elastic IP**: IP pública estática (`98.91.49.34`) que no cambia si el servidor se reinicia
- **user_data.sh**: script que se ejecuta automáticamente la primera vez que arranca la EC2

### El script `user_data.sh` (bootstrap)
Es el "instalador automático" del servidor. Hace:
1. Actualiza el sistema operativo
2. Crea un archivo de **swap de 1 GB** (crítico para t2.micro: sin swap, los contenedores causan OOM)
3. Instala **Docker** y lo habilita como servicio
4. Instala **Docker Compose v2**
5. Instala **AWS CLI**
6. Crea el directorio `/opt/energygrid/`
7. Escribe el `.env` y el `docker-compose.yml` con los valores inyectados por Terraform
8. Registra un servicio **systemd** llamado `energygrid` para que los contenedores se reinicien solos si el servidor se apaga y vuelve

---

## 4. Por qué se abandonó el enfoque ECR para usar git clone

El plan original era:
1. Construir imágenes localmente → subir a ECR → EC2 descarga de ECR

Pero Docker Desktop no estaba corriendo en la máquina local, lo que impidió el build local.

**Solución adoptada:**
1. Clonar el repositorio **directamente en la EC2** con `git clone`
2. Ejecutar `docker compose up --build` en el servidor

Esto construye las imágenes en el propio servidor usando los Dockerfiles del repo. Tarda más (~5 minutos en t2.micro) pero no depende de Docker en la máquina local.

---

## 5. El problema del frontend y cómo se resolvió

### El problema
Al abrir el frontend en el navegador, las llamadas a la API fallaban aunque el backend estuviera funcionando.

**Causa raíz:** Vite (el bundler de React) embebe las variables de entorno `VITE_*` en el JavaScript en el momento de la compilación (`npm run build`). No son variables de runtime como en Node.js.

El código fuente hace:
```js
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
```

Como el Dockerfile original no pasaba `VITE_API_BASE` durante el build, el bundle quedó con `http://localhost:8000` hardcodeado. Cuando el usuario abre el navegador, su máquina no tiene nada en `localhost:8000`, así que todas las peticiones fallaban.

### La solución
Se modificó el `Dockerfile` del frontend para aceptar un argumento de build:

```dockerfile
# Antes:
RUN npm run build

# Después:
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build
```

Y se reconstruyó pasando la IP pública de la EC2:
```bash
docker compose build \
  --build-arg VITE_API_BASE=http://98.91.49.34:8000 \
  energygrid-frontend
```

Así el bundle quedó con `http://98.91.49.34:8000` embebido, y el frontend pudo comunicarse con el backend correctamente.

---

## 6. Flujo completo de datos en producción

```
Usuario (navegador)
    │
    │  HTTP :3000
    ▼
ENERGYGRID-FRONTEND (Nginx sirviendo el bundle React)
    │
    │  fetch() / WebSocket a http://98.91.49.34:8000
    ▼
ENERGYGRID-NGINX (proxy reverso)
    │
    │  proxy_pass a http://energygrid-backend:8000
    ▼
energygrid-backend (FastAPI / uvicorn)
    │
    ├──► ENERGYGRID-DB (PostgreSQL) — lectura/escritura de datos
    └──► ENERGYGRID-REDIS (Redis)   — pub/sub para WebSocket tiempo real

ENERGYGRID-SIMULATOR ──► POST /api/metrics ──► Backend
(genera datos de consumo eléctrico cada 1 segundo)
```

---

## 7. Archivos creados durante la integración

```
infra/
├── terraform/
│   ├── main.tf                     # Une los 3 módulos
│   ├── variables.tf                # Parámetros configurables
│   ├── outputs.tf                  # IPs y URLs al terminar
│   ├── terraform.tfvars            # Valores reales (no subir a git)
│   ├── terraform.tfvars.example    # Plantilla pública
│   └── modules/
│       ├── networking/             # VPC, subnet, SG, IGW, route table
│       ├── ecr/                    # 5 repositorios + lifecycle policy
│       └── ec2/                    # t2.micro + EIP + IAM + user_data.sh
└── scripts/
    ├── 01_build_and_push.sh        # Build local → ECR (si Docker disponible)
    ├── 02_deploy.sh                # terraform init + plan + apply
    ├── 03_start_services.sh        # En EC2: ECR login + pull + compose up
    └── 04_teardown.sh              # terraform destroy

GUIA_DESPLIEGUE_AWS.md             # Guía técnica completa
GUIA_EJECUCION.md                  # Este documento de ejecución
EXPLICACION_INTEGRACION.md         # Explicación de la integración
```

---

## 8. Recursos AWS creados (verificables en la consola)

| Servicio | Recurso | Identificador |
|---|---|---|
| EC2 | Instancia t2.micro | `i-084104f36c9bcf27f` |
| EC2 | Elastic IP | `98.91.49.34` |
| ECR | Repositorio backend | `107901884265.dkr.ecr.us-east-1.amazonaws.com/energygrid-backend` |
| ECR | Repositorio frontend | `107901884265.dkr.ecr.us-east-1.amazonaws.com/energygrid-frontend` |
| ECR | Repositorio simulator | `107901884265.dkr.ecr.us-east-1.amazonaws.com/energygrid-simulator` |
| ECR | Repositorio nginx | `107901884265.dkr.ecr.us-east-1.amazonaws.com/energygrid-nginx` |
| ECR | Repositorio munin-master | `107901884265.dkr.ecr.us-east-1.amazonaws.com/energygrid-munin-master` |
| VPC | Red virtual | `vpc-0692a9463d37f3a2a` |
| IAM | Role para EC2 | `energygrid-prod-ec2-role` |

---

## 9. Decisiones técnicas clave

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| EC2 t2.micro todo-en-uno | ECS Fargate | Fargate no es free tier |
| Build en EC2 via git clone | Build local + ECR push | Docker Desktop no estaba disponible |
| Swap de 1 GB en EC2 | Sin swap | t2.micro tiene solo 1 GB RAM; sin swap los contenedores causan OOM |
| VITE_API_BASE como build arg | Proxy en nginx | Es la forma correcta para Vite; el proxy habría requerido cambiar nginx.conf |
| Volumen `down -v` al cambiar credenciales DB | Solo reiniciar | PostgreSQL inicializa el usuario/DB solo si el volumen está vacío |
| `restart: unless-stopped` en compose | Sin restart policy | Garantiza que los contenedores vuelvan si el servidor se reinicia |
