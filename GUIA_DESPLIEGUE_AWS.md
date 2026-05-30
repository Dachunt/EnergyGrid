# Guía Técnica de Despliegue — EnergyGrid en AWS (Free Tier)

## Índice

1. [Arquitectura del ecosistema](#1-arquitectura-del-ecosistema)
2. [Recursos AWS utilizados (capa gratuita)](#2-recursos-aws-utilizados-capa-gratuita)
3. [Prerrequisitos](#3-prerrequisitos)
4. [Paso 0 — Configurar credenciales AWS](#paso-0--configurar-credenciales-aws)
5. [Paso 1 — Crear par de claves EC2](#paso-1--crear-par-de-claves-ec2)
6. [Paso 2 — Configurar variables de Terraform](#paso-2--configurar-variables-de-terraform)
7. [Paso 3 — Desplegar infraestructura con Terraform](#paso-3--desplegar-infraestructura-con-terraform)
8. [Paso 4 — Construir y publicar imágenes Docker en ECR](#paso-4--construir-y-publicar-imágenes-docker-en-ecr)
9. [Paso 5 — Iniciar servicios en EC2](#paso-5--iniciar-servicios-en-ec2)
10. [Paso 6 — Verificar el despliegue](#paso-6--verificar-el-despliegue)
11. [Despliegue local con Docker Compose](#despliegue-local-con-docker-compose)
12. [Estructura de la IaC](#estructura-de-la-iac)
13. [Monitoreo y logs](#monitoreo-y-logs)
14. [Estimación de costos (Free Tier)](#estimación-de-costos-free-tier)
15. [Teardown — Destruir la infraestructura](#teardown--destruir-la-infraestructura)

---

## 1. Arquitectura del ecosistema

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              AWS VPC  (10.0.0.0/16)                 │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │         Public Subnet  10.0.1.0/24           │   │
│  │                                              │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │     EC2 t2.micro  (Amazon Linux 2023)  │  │   │
│  │  │     Elastic IP (IP pública estática)   │  │   │
│  │  │                                        │  │   │
│  │  │  Docker Compose — energygrid-net       │  │   │
│  │  │  ┌──────────┐  ┌──────────────────┐   │  │   │
│  │  │  │ :3000    │  │   :8000          │   │  │   │
│  │  │  │ Frontend │  │   Nginx Proxy    │   │  │   │
│  │  │  │ (React)  │  │   → Backend API  │   │  │   │
│  │  │  └──────────┘  └──────────────────┘   │  │   │
│  │  │  ┌──────────┐  ┌──────────────────┐   │  │   │
│  │  │  │ Backend  │  │   PostgreSQL 15   │   │  │   │
│  │  │  │ FastAPI  │  │   (interno)      │   │  │   │
│  │  │  └──────────┘  └──────────────────┘   │  │   │
│  │  │  ┌──────────┐  ┌──────────────────┐   │  │   │
│  │  │  │ Redis 7  │  │   Simulator      │   │  │   │
│  │  │  │(interno) │  │   (interno)      │   │  │   │
│  │  │  └──────────┘  └──────────────────┘   │  │   │
│  │  │  ┌──────────────────────────────────┐  │  │   │
│  │  │  │ Munin Master  :8081              │  │  │   │
│  │  │  └──────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘

AWS ECR  ─── Almacena las 5 imágenes Docker del proyecto
```

### Servicios y puertos expuestos

| Servicio            | Puerto público | Descripción                         |
|---------------------|---------------|-------------------------------------|
| Frontend (React)    | **3000**      | Interfaz web de monitoreo           |
| Backend API (nginx) | **8000**      | REST API + WebSocket                |
| Munin dashboard     | **8081**      | Gráficas de métricas del sistema    |
| SSH                 | **22**        | Administración remota               |

### Comunicación interna (Docker network `energygrid-net`)

| Servicio   | Puerto interno | Consumidores              |
|------------|---------------|---------------------------|
| PostgreSQL | 5432          | Backend                   |
| Redis      | 6379          | Backend (WebSocket pub/sub)|
| Backend    | 8000, 4949    | Nginx, Simulator, Munin   |
| Simulator  | 8001          | Backend (pull metrics)    |

---

## 2. Recursos AWS utilizados (capa gratuita)

| Recurso              | Tier gratuito                                      | Uso en este proyecto          |
|----------------------|----------------------------------------------------|-------------------------------|
| **EC2 t2.micro**     | 750 h/mes (12 meses)                               | Ejecuta todos los contenedores|
| **EBS gp2 20 GB**    | 30 GB/mes (12 meses)                               | Volumen raíz del EC2          |
| **Elastic IP**       | Gratis mientras esté asociado a instancia running  | IP pública estática           |
| **ECR**              | 500 MB/mes                                         | 5 repositorios de imágenes    |
| **VPC / Subnets**    | Siempre gratis                                     | Red privada virtual           |
| **Security Groups**  | Siempre gratis                                     | Firewall por servicio         |
| **Data transfer**    | 1 GB/mes saliente gratis                           | Tráfico de la aplicación      |

**Costo estimado: $0 USD/mes** durante los primeros 12 meses con una cuenta nueva.

---

## 3. Prerrequisitos

### Software local

| Herramienta       | Versión mínima | Instalación                                          |
|-------------------|---------------|------------------------------------------------------|
| AWS CLI           | 2.x           | `winget install Amazon.AWSCLI`                       |
| Terraform         | 1.5.x         | `winget install Hashicorp.Terraform`                 |
| Docker Desktop    | 24.x          | https://docs.docker.com/desktop/install/windows/     |
| Git               | 2.x           | Ya instalado en el proyecto                          |

### Cuenta AWS

- Cuenta AWS activa (puede ser nueva para aprovechar Free Tier)
- Usuario IAM con permisos: `AdministratorAccess` (o permisos mínimos: EC2, ECR, VPC, IAM)
- Access Key ID + Secret Access Key del usuario IAM

---

## Paso 0 — Configurar credenciales AWS

```bash
aws configure
```

```
AWS Access Key ID:     [tu_access_key_id]
AWS Secret Access Key: [tu_secret_access_key]
Default region name:   us-east-1
Default output format: json
```

Verificar:

```bash
aws sts get-caller-identity
```

Salida esperada:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/tu-usuario"
}
```

---

## Paso 1 — Crear par de claves EC2

El par de claves permite acceso SSH al servidor. Créalo una sola vez en la región que vas a usar.

```bash
# Crear el par de claves y guardar la clave privada
aws ec2 create-key-pair \
  --key-name energygrid-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/energygrid-key.pem

# Establecer permisos correctos (Linux/macOS)
chmod 400 ~/.ssh/energygrid-key.pem

# En Windows (PowerShell)
icacls "$env:USERPROFILE\.ssh\energygrid-key.pem" /inheritance:r /grant:r "$env:USERNAME:R"
```

---

## Paso 2 — Configurar variables de Terraform

```bash
# Desde la raíz del proyecto
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

Editar `infra/terraform/terraform.tfvars`:

```hcl
aws_region     = "us-east-1"
project        = "energygrid"
environment    = "prod"

# Obtener tu Account ID:
# aws sts get-caller-identity --query Account --output text
aws_account_id = "123456789012"

key_name       = "energygrid-key"

# Contraseñas seguras (cambiar estos valores)
db_password    = "MiPassword_S3gura_2025!"
jwt_secret     = "secreto-jwt-super-largo-minimo-32-caracteres-aqui"

# Pingdom (opcional — dejar vacío si no se usa)
pingdom_api_token = ""
pingdom_email     = ""

# Tu IP para SSH seguro (recomendado):
# Obtener tu IP: Invoke-RestMethod -Uri "https://ifconfig.me"
allowed_ssh_cidr = "0.0.0.0/0"
```

---

## Paso 3 — Desplegar infraestructura con Terraform

```bash
# Desde la raíz del proyecto
bash infra/scripts/02_deploy.sh
```

O paso a paso:

```bash
cd infra/terraform

# Inicializar providers de Terraform
terraform init

# Ver qué recursos se crearán (sin aplicar)
terraform plan -var-file="terraform.tfvars"

# Crear la infraestructura
terraform apply -var-file="terraform.tfvars"
```

Al finalizar, Terraform mostrará los outputs:

```
Outputs:

backend_url       = "http://54.23.X.X:8000"
ec2_public_ip     = "54.23.X.X"
ecr_registry_url  = "123456789012.dkr.ecr.us-east-1.amazonaws.com"
frontend_url      = "http://54.23.X.X:3000"
munin_url         = "http://54.23.X.X:8081"
ssh_command       = "ssh -i ~/.ssh/energygrid-key.pem ec2-user@54.23.X.X"
```

**Guardar los outputs** — los necesitarás en los pasos siguientes.

---

## Paso 4 — Construir y publicar imágenes Docker en ECR

Este paso construye las 5 imágenes del proyecto en tu máquina local y las sube a ECR.

```bash
# Desde la raíz del proyecto
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

bash infra/scripts/01_build_and_push.sh
```

El script:
1. Inicia sesión en ECR
2. Construye cada imagen con `--platform linux/amd64` (compatibilidad con EC2 x86_64)
3. Hace `docker push` de cada imagen

Imágenes publicadas:
- `energygrid-backend:latest`
- `energygrid-frontend:latest`
- `energygrid-simulator:latest`
- `energygrid-nginx:latest`
- `energygrid-munin-master:latest`

> **Nota:** La primera vez puede tardar 10-20 minutos dependiendo de la velocidad de internet.

---

## Paso 5 — Iniciar servicios en EC2

### 5.1 Conectar al servidor

```bash
# Usar el ssh_command del output de Terraform
ssh -i ~/.ssh/energygrid-key.pem ec2-user@<EC2_PUBLIC_IP>
```

### 5.2 Verificar que el bootstrap terminó

El script de bootstrap se ejecuta automáticamente al iniciar la instancia. Verificar su log:

```bash
cat /var/log/user-data.log | tail -20
# Debe terminar con: "Bootstrap complete."
```

### 5.3 Iniciar la aplicación

```bash
bash /opt/energygrid/start.sh
```

El script:
1. Lee las variables del `.env` (generado por Terraform)
2. Hace login en ECR
3. Hace `docker compose pull` para descargar imágenes
4. Levanta todos los servicios con `docker compose up -d`
5. Espera y verifica el health check del backend

### 5.4 Verificar estado de los contenedores

```bash
cd /opt/energygrid
docker compose ps
```

Salida esperada (todos `healthy` o `running`):

```
NAME                     STATUS              PORTS
ENERGYGRID-DB            healthy             0.0.0.0:15432->5432/tcp
ENERGYGRID-REDIS         running             6379/tcp
energygrid-backend       running             8000/tcp, 4949/tcp
ENERGYGRID-NGINX         running             0.0.0.0:8000->8000/tcp
ENERGYGRID-FRONTEND      running             0.0.0.0:3000->80/tcp
ENERGYGRID-SIMULATOR     running             8001/tcp
ENERGYGRID-MUNIN-MASTER  running             0.0.0.0:8081->8080/tcp
```

---

## Paso 6 — Verificar el despliegue

Reemplazar `<IP>` con el Elastic IP del output de Terraform.

### Frontend (interfaz web)
```
http://<IP>:3000
```
- Credenciales por defecto: `admin` / `Admin123!`

### Backend API — Health Check
```bash
curl http://<IP>:8000/health
# Respuesta esperada: {"status": "healthy", ...}
```

### Backend API — Documentación interactiva
```
http://<IP>:8000/docs
```

### Munin — Dashboard de monitoreo
```
http://<IP>:8081
```
Muestra gráficas de CPU, memoria, disco, red, procesos del servidor EC2.

### Probar WebSocket (tiempo real)
Abrir el frontend → ver que las métricas de los distritos se actualicen automáticamente cada segundo.

---

## Despliegue local con Docker Compose

Para desarrollo local o demostración sin AWS:

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Editar .env con tus valores (mínimo: contraseñas)
notepad .env     # Windows
# nano .env      # Linux/macOS

# 3. Crear directorios de logs
mkdir -p logs/spikes logs/alertas

# 4. Levantar toda la pila
docker compose up -d --build

# 5. Ver logs en tiempo real
docker compose logs -f

# 6. Verificar servicios
docker compose ps
```

Accesos locales:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Munin: http://localhost:8081
- API Docs: http://localhost:8000/docs

Apagar y limpiar:
```bash
docker compose down -v  # -v elimina los volúmenes (borra datos)
docker compose down     # sin -v conserva los datos
```

---

## Estructura de la IaC

```
infra/
├── terraform/
│   ├── main.tf                    # Orquestador: une todos los módulos
│   ├── variables.tf               # Declaración de variables
│   ├── outputs.tf                 # IPs, URLs y comandos útiles
│   ├── terraform.tfvars.example   # Plantilla de configuración
│   └── modules/
│       ├── networking/            # VPC, subnets, Internet Gateway,
│       │   ├── main.tf            # Route Tables, Security Groups
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── ecr/                   # Repositorios de imágenes Docker
│       │   ├── main.tf            # + políticas de limpieza (≤5 tags)
│       │   ├── variables.tf
│       │   └── outputs.tf
│       └── ec2/                   # Instancia t2.micro + Elastic IP
│           ├── main.tf            # + IAM role para ECR pull
│           ├── variables.tf
│           ├── outputs.tf
│           └── user_data.sh       # Script de bootstrap del servidor
└── scripts/
    ├── 01_build_and_push.sh       # Build imágenes → ECR
    ├── 02_deploy.sh               # Terraform init/plan/apply
    ├── 03_start_services.sh       # ECR login → pull → compose up
    └── 04_teardown.sh             # terraform destroy
```

### Flujo de dependencias Terraform

```
main.tf
  ├── module.networking  →  VPC, Subnet, Security Group
  ├── module.ecr         →  5 repositorios ECR
  └── module.ec2         →  EC2 + EIP + IAM Role
       depends_on: networking.vpc_id, networking.subnet_id, ecr.registry_url
```

---

## Monitoreo y logs

### Ver logs de un servicio específico

```bash
# En EC2
cd /opt/energygrid

docker compose logs -f energygrid-backend    # API logs
docker compose logs -f energygrid-simulator  # Simulador
docker compose logs -f energygrid-db         # PostgreSQL
```

### Logs de la aplicación (en disco)

```bash
# Logs estructurados (JSON)
cat /opt/energygrid/logs/energygrid.log | tail -50

# Picos detectados
ls /opt/energygrid/logs/spikes/

# Alertas
ls /opt/energygrid/logs/alertas/
```

### Comandos útiles en EC2

```bash
# Estado del servicio systemd
systemctl status energygrid

# Reiniciar toda la pila
systemctl restart energygrid

# Uso de memoria (revisar si t2.micro está saturado)
free -h
docker stats --no-stream

# Espacio en disco
df -h
```

---

## Estimación de costos (Free Tier)

| Servicio      | Free Tier                    | Uso mensual estimado  | Costo       |
|---------------|-----------------------------|-----------------------|-------------|
| EC2 t2.micro  | 750 h/mes × 12 meses        | 720 h (24×30)         | **$0.00**   |
| EBS 20 GB gp2 | 30 GB/mes × 12 meses        | 20 GB                 | **$0.00**   |
| Elastic IP    | Gratis si instancia running  | 1 EIP                 | **$0.00**   |
| ECR           | 500 MB/mes                  | ~400 MB (5 imágenes)  | **$0.00**   |
| Data transfer | 1 GB/mes saliente            | < 1 GB (demo)         | **$0.00**   |
| **Total**     |                              |                       | **$0.00/mes**|

> **Importante:** El Free Tier aplica para cuentas nuevas durante 12 meses. Al vencer, el costo aproximado es **~$8-10 USD/mes** (EC2 t2.micro + EBS).

---

## Teardown — Destruir la infraestructura

Para eliminar **todos** los recursos AWS y evitar cargos futuros:

```bash
# Desde la raíz del proyecto
bash infra/scripts/04_teardown.sh
```

O manualmente:

```bash
cd infra/terraform
terraform destroy -var-file="terraform.tfvars"
```

> Este comando elimina: EC2, Elastic IP, VPC, Subnets, Security Groups y repositorios ECR (con todas las imágenes). **La acción es irreversible.**

---

## Solución de problemas comunes

### Los contenedores no inician (OOM)

La EC2 t2.micro tiene 1 GB de RAM. Si el sistema queda sin memoria:

```bash
# Verificar uso de memoria
docker stats --no-stream

# Reiniciar servicios pesados
docker compose restart energygrid-backend
```

El `user_data.sh` ya crea 1 GB de swap para mitigar esto.

### El backend no se conecta a la base de datos

```bash
# Verificar que PostgreSQL esté healthy
docker compose ps energygrid-db

# Ver logs de DB
docker compose logs energygrid-db | tail -20

# Probar conexión manual
docker compose exec energygrid-db psql -U energygrid -d energygrid -c "\dt"
```

### Error al hacer push a ECR

```bash
# Re-autenticar en ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin \
    $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
```

### Terraform error: "key pair not found"

El key pair debe existir en la misma región antes de correr Terraform:

```bash
aws ec2 describe-key-pairs --region us-east-1
```

### WebSocket no conecta

Verificar que el Security Group permite tráfico en el puerto 8000 y que el frontend apunta al IP correcto del EC2. En producción, el WebSocket URL se configura en las variables de entorno del build de React.
