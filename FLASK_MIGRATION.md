# Guía de Migración de FastAPI a Flask - EnergyGrid

## Cambios Realizados

### 1. Framework Base
- **De:** FastAPI (framework async moderno)
- **A:** Flask (framework WSGI tradicional)

### 2. Dependencias Actualizadas

**requirements.txt** ahora incluye:
```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-JWT-Extended==4.5.3
Flask-CORS==4.0.0
Flask-SocketIO==5.3.5
psycopg2-binary==2.9.9
SQLAlchemy==2.0.23
```

### 3. Estructura de Archivos

```
backend/
├── app/
│   ├── main.py                    # Inicialización Flask (antes: FastAPI)
│   ├── models/
│   │   ├── models.py             # SQLAlchemy models (antes: Pydantic)
│   │   └── __init__.py
│   ├── routes/                    # Blueprints Flask (antes: APIRouter FastAPI)
│   │   ├── auth.py
│   │   ├── metrics.py
│   │   ├── districts.py
│   │   ├── demo.py
│   │   ├── monitoring.py
│   │   ├── admin.py
│   │   └── __init__.py
│   ├── services/
│   │   └── seeder.py             # Seed de datos iniciales
│   └── static/                   # Assets estáticos
├── run.py                         # Punto de entrada (reemplaza uvicorn)
├── wsgi.py                        # Entrada para Gunicorn
└── requirements.txt              # Dependencias actualizadas
```

### 4. Cambios en la Aplicación Principal (main.py)

#### Antes (FastAPI):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, ...)
```

#### Ahora (Flask):
```python
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)
    # Registrar blueprints...
```

### 5. Cambios en Rutas (Routes/Endpoints)

#### Antes (FastAPI):
```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/auth")

@router.post("/login")
async def login(data: LoginRequest, request: Request):
    pool = request.app.state.db
    # ...
```

#### Ahora (Flask):
```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    # ...
    return jsonify({...}), 200
```

**Cambios clave:**
- `APIRouter` → `Blueprint`
- `async def` → `def` (Flask es sincrónico)
- `@router.post()` → `@blueprint.route(..., methods=['POST'])`
- `raise HTTPException()` → `return jsonify({...}), status_code`
- `Depends(require_auth)` → `@jwt_required()` decorator

### 6. Cambios en Modelos (Models)

#### Antes (Pydantic):
```python
from pydantic import BaseModel

class Usuario(BaseModel):
    id: int
    username: str
    password_hash: str
```

#### Ahora (SQLAlchemy):
```python
from app.main import db

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    def to_dict(self):
        return {'id': self.id, 'username': self.username}
```

**Tablas soportadas:**
- `usuarios` - Gestión de usuarios
- `distritos` - Información de distritos
- `subestaciones` - Información de subestaciones
- `consumo_temporal` - Métricas de consumo
- `alertas` - Registro de alertas

### 7. Autenticación JWT

#### Configuración:
```python
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', '...')
jwt.init_app(app)
```

#### Uso:
```python
# Para proteger un endpoint
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    # ...
```

### 8. Base de Datos

**Cambio:** De AsyncPG (async) a psycopg2 (sync) + SQLAlchemy ORM

```python
# Configuración en main.py
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
```

### 9. Endpoints Migrados

Todos los 16+ endpoints han sido migrados:

| Recurso | Endpoints |
|---------|-----------|
| **Auth** | POST /api/auth/login, register, logout, change-password |
| **Métricas** | POST /api/metrics |
| **Distritos** | GET/POST/PUT/DELETE /api/districts |
| **Monitoreo** | GET /api/monitoring/health, dashboard, alerts |
| **Admin** | GET/POST/PUT /api/admin/users, districts, substations |
| **Demo** | GET /api/demo/metrics/sample, health |

### 10. Instrucciones de Ejecución

#### Instalación:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

pip install -r requirements.txt
```

#### Ejecución Local:
```bash
# Modo desarrollo
python run.py

# Modo producción con Gunicorn
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

#### Docker:
```bash
docker compose up --build
```

### 11. Variables de Entorno

Asegúrate de que `.env` contenga:
```
DATABASE_URL=postgresql://energygrid_user:S3cur3P@ss2026@localhost:5432/energygrid_db
JWT_SECRET=tu-secret-key-aqui
JWT_ALGORITHM=HS256
FLASK_ENV=development
```

### 12. Seed Data

Los datos iniciales se crean automáticamente al iniciar:
- Usuario admin: `admin / Admin123!`
- 4 distritos con sus subestaciones
- 5 subestaciones predefinidas

### 13. Compatibilidad con Frontend

El frontend React sigue siendo **100% compatible**:
- Mismo origen CORS
- Mismo formato JSON
- Mismos JWT tokens
- Mismos endpoints

No requiere cambios en el frontend.

### 14. Características Implementadas

✅ Autenticación JWT
✅ CRUD de usuarios, distritos, subestaciones
✅ Almacenamiento de métricas
✅ Gestión de alertas
✅ Control de acceso (admin/user)
✅ CORS global
✅ Logging estructurado
✅ Validación de datos

⏳ Por hacer (opcional):
- WebSocket en tiempo real (Flask-SocketIO listo pero no implementado completamente)
- Servicios de alertas en segundo plano (Celery)
- Monitoreo avanzado (Munin/Pingdom)

### 15. Testing

Para probar los endpoints:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'

# Obtener distritos
curl -X GET http://localhost:8000/api/districts

# Crear métrica
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "substation_id":"SSS001",
    "distrito_id":"San Salvador",
    "consumo_kw":2500,
    "capacidad_kw":5000
  }'
```

### 16. Notas Importantes

1. **Performance:** Flask es sincrónico. Para aplicaciones con alto tráfico, considera:
   - Usar Gunicorn con múltiples workers
   - Implementar caching con Redis
   - Usar Celery para tareas async

2. **WebSocket:** Implementado con Flask-SocketIO pero requiere configuración de eventos

3. **Modelos:** Todos migrados a SQLAlchemy ORM para compatibilidad

4. **Versionado:** Mantén las mismas versiones de dependencias para estabilidad

---

**Migración completada exitosamente el 2026-05-30**
