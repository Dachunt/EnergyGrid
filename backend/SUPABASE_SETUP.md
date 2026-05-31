# Guía de Conexión Supabase - EnergyGrid Backend

## ✓ Configuración Completada

### 1. Archivos Creados
- `.env` - Archivo con credenciales (local solamente, no commitear)
- `.env.example` - Plantilla sin credenciales (para versionado)

### 2. Variables de Entorno Configuradas

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=S3cur3P@ss2026
POSTGRES_HOST=db.vwizsavkjotspcnoqhva.supabase.co
POSTGRES_PORT=5432
POSTGRES_DB=postgres
SUPABASE_URL=https://vwizsavkjotspcnoqhva.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Cómo Conectarte

#### Opción A: Usar la conexión existente en `db.py`
Tu archivo `app/db.py` ya está configurado para leer estas variables:

```python
# Automáticamente cargará:
user = os.getenv("POSTGRES_USER")           # postgres
password = os.getenv("POSTGRES_PASSWORD")   # S3cur3P@ss2026
host = os.getenv("POSTGRES_HOST")           # db.vwizsavkjotspcnoqhva.supabase.co
port = int(os.getenv("POSTGRES_PORT"))      # 5432
db = os.getenv("POSTGRES_DB")               # postgres
```

#### Opción B: Usar Supabase Client (para operaciones de cliente)
Si quieres usar el cliente oficial de Supabase en Python:

```bash
pip install supabase python-gotrue
```

Luego en tu código:
```python
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(url, key)
```

### 4. Iniciar la Aplicación

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Instalar dependencias (ya incluye asyncpg)
pip install -r requirements.txt

# Ejecutar FastAPI
uvicorn app.main:app --reload
```

### 5. Verificar Conexión

Una vez que la app esté corriendo:

```bash
# En otra terminal
curl http://localhost:8000/health
# Debería retornar: {"status":"ok"}
```

### 6. Base de Datos

**Nombre:** `postgres` (base de datos por defecto de Supabase)
**Usuario:** `postgres`
**Host:** `db.vwizsavkjotspcnoqhva.supabase.co:5432`

### 7. Seguridad

⚠️ **IMPORTANTE:**
- Nunca commitear `.env` a git (usa `.env.example`)
- Cambiar `JWT_SECRET` en producción
- Cambiar credenciales de admin en producción
- Mantener contraseña segura

### 8. Próximos Pasos

1. ✓ `.env` configurado
2. Crear/migrar tablas en Supabase (si no existen)
3. Ejecutar `_ensure_admin()` para crear datos iniciales
4. Iniciar aplicación FastAPI
5. Acceder al dashboard en http://localhost:8000

### 9. Herramientas Útiles

- **Supabase Dashboard:** https://app.supabase.com/
- **SQL Editor en Supabase:** Para ejecutar queries directamente
- **Table Editor:** Para gestionar datos visualmente

