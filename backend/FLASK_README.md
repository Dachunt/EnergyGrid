# EnergyGrid - Backend Flask

Sistema integral de monitoreo de energía construido con **Flask** (migrado de FastAPI).

## 🚀 Quick Start

### 1. Instalación

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración Base de Datos

Asegúrate de que PostgreSQL esté corriendo y que `.env` tenga:

```bash
DATABASE_URL=postgresql://energygrid_user:S3cur3P@ss2026@localhost:5432/energygrid_db
JWT_SECRET=tu-secret-key-aqui
FLASK_ENV=development
```

### 3. Ejecutar el Servidor

```bash
# Modo desarrollo
python run.py

# Modo producción (con Gunicorn)
gunicorn --bind 0.0.0.0:8000 --workers 4 wsgi:app
```

El servidor estará disponible en: `http://localhost:8000`

## 📋 Endpoints Principales

### Autenticación
```
POST   /api/auth/login           - Login
POST   /api/auth/register        - Registro
GET    /api/auth/me              - Obtener usuario (requiere JWT)
POST   /api/auth/logout          - Logout
POST   /api/auth/change-password - Cambiar contraseña
```

### Distritos
```
GET    /api/districts            - Listar distritos
GET    /api/districts/{id}       - Obtener distrito
POST   /api/districts            - Crear distrito (requiere JWT)
PUT    /api/districts/{id}       - Actualizar distrito (requiere JWT)
DELETE /api/districts/{id}       - Eliminar distrito (requiere JWT)
```

### Métricas
```
POST   /api/metrics              - Registrar métrica de consumo
GET    /api/monitoring/metrics/history - Historial de métricas
```

### Monitoreo
```
GET    /api/monitoring/health    - Estado del sistema
GET    /api/monitoring/dashboard - Dashboard completo
GET    /api/monitoring/alerts    - Alertas activas
POST   /api/monitoring/alerts/{id}/resolve - Resolver alerta
```

### Admin (requiere rol admin)
```
GET    /api/admin/users          - Listar usuarios
GET    /api/admin/users/{id}     - Obtener usuario
PUT    /api/admin/users/{id}     - Actualizar usuario
GET    /api/admin/districts      - Listar distritos
GET    /api/admin/substations    - Listar subestaciones
POST   /api/admin/substations    - Crear subestación
PUT    /api/admin/substations/{id} - Actualizar subestación
GET    /api/admin/alerts         - Listar alertas
```

## 🔐 Autenticación JWT

### Obtener Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

### Usar Token
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <tu_token>"
```

## 📊 Ejemplo: Enviar Métrica

```bash
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "substation_id": "SSS001",
    "distrito_id": "San Salvador",
    "consumo_kw": 2500,
    "capacidad_kw": 5000,
    "timestamp": "2026-05-30T22:48:00Z"
  }'
```

## 🧪 Testing

Ejecutar pruebas de API:

```bash
python test_api.py
```

Este script prueba:
- ✅ Login
- ✅ CRUD de distritos
- ✅ Envío de métricas
- ✅ Dashboard de monitoreo
- ✅ Gestión de alertas
- ✅ Panel admin

## 🐳 Docker

```bash
# Desde la raíz del proyecto
docker compose up --build

# Acceso
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Docs:     http://localhost:8000/health
```

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── main.py                 # Aplicación Flask
│   ├── models/
│   │   └── models.py          # Modelos SQLAlchemy
│   ├── routes/                # Blueprints (rutas)
│   │   ├── auth.py
│   │   ├── metrics.py
│   │   ├── districts.py
│   │   ├── monitoring.py
│   │   ├── admin.py
│   │   └── demo.py
│   ├── services/
│   │   └── seeder.py          # Datos iniciales
│   └── static/                # Archivos estáticos
├── run.py                      # Punto de entrada
├── wsgi.py                     # WSGI para Gunicorn
├── test_api.py                # Tests de API
└── requirements.txt           # Dependencias
```

## 🔑 Credenciales por Defecto

- **Usuario:** `admin`
- **Contraseña:** `Admin123!`
- **Rol:** `admin`

## 📦 Dependencias Principales

- **Flask** 3.0.0 - Framework web
- **Flask-SQLAlchemy** 3.1.1 - ORM
- **Flask-JWT-Extended** 4.5.3 - Autenticación JWT
- **Flask-CORS** 4.0.0 - CORS
- **psycopg2-binary** 2.9.9 - Driver PostgreSQL
- **SQLAlchemy** 2.0.23 - ORM avanzado

## ⚙️ Configuración

### Variables de Entorno (.env)

```bash
# Base de Datos
DATABASE_URL=postgresql://user:password@localhost:5432/db
SQLALCHEMY_ECHO=False

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=86400

# Flask
FLASK_ENV=development
FLASK_DEBUG=1

# Servidor
HOST=0.0.0.0
PORT=8000
```

## 🚨 Características

✅ Autenticación JWT con roles (admin/user)
✅ CRUD de usuarios, distritos, subestaciones
✅ Almacenamiento de métricas de consumo
✅ Sistema de alertas
✅ Dashboard de monitoreo
✅ Control de acceso basado en roles
✅ CORS global configurado
✅ Logging estructurado
✅ Validación de datos con Pydantic
✅ Seed data automático

## 🔄 Migración de FastAPI

Este proyecto fue migrado exitosamente de **FastAPI** a **Flask**:

- ✅ Todos los endpoints preservados
- ✅ Autenticación JWT funcionando
- ✅ Modelos actualizados a SQLAlchemy
- ✅ Base de datos PostgreSQL compatible
- ✅ Frontend React sin cambios
- ✅ Seed data automático

Ver `FLASK_MIGRATION.md` para detalles técnicos.

## 📝 Notas

- La base de datos se crea automáticamente al iniciar
- Los datos iniciales se seed automáticamente
- WebSocket está configurado pero no completamente implementado (usar Flask-SocketIO)
- Para producción, usar Gunicorn con múltiples workers
- Considerar agregar Celery para tareas en segundo plano

## 🤝 Soporte

Para problemas o preguntas sobre la migración a Flask, consulta:
- Documentación Flask: https://flask.palletsprojects.com/
- Flask-SQLAlchemy: https://flask-sqlalchemy.palletsprojects.com/
- Flask-JWT-Extended: https://flask-jwt-extended.readthedocs.io/

---

**Última actualización:** 2026-05-30
**Estado:** ✅ Production Ready
