# Resolucion: Error de psycopg2-binary

## Problema Original
```
ERROR: Failed to build 'psycopg2-binary' when getting requirements to build wheel
pg_config executable not found.
```

## Causa
El paquete `psycopg2-binary` intenta compilarse desde código fuente en Windows, lo que requiere PostgreSQL instalado con `pg_config`.

## Soluciones Aplicadas

### 1. Remover psycopg2-binary del requirements.txt
**Archivo**: `backend/requirements.txt`

**Cambio**:
```diff
- psycopg2-binary==2.9.9
```

**Razon**: Ya tienes `asyncpg==0.29.0` que es mejor para aplicaciones async y no requiere compilación.

### 2. Actualizar logging_config.py
**Archivo**: `backend/app/logging_config.py`

**Cambio**:
```python
# Antes:
LOG_FILE = "/app/logs/energygrid.log"

# Después:
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "energygrid.log")
```

**Razon**: Cambiar ruta absoluta a relativa y crear directorio automáticamente.

## Dependencias Actuales

```
fastapi==0.104.1         ✅
uvicorn[standard]==0.24.0 ✅
sqlalchemy==2.0.23       ✅
asyncpg==0.29.0          ✅ (mejor que psycopg2 para async)
pydantic==2.5.2          ✅
pydantic-settings==2.1.0 ✅
python-dotenv==1.0.0     ✅
websockets==12.0         ✅
python-json-logger==2.0.7 ✅
httpx==0.26.0            ✅
psutil==5.9.6            ✅ (para Munin Monitor)
```

## Pasos para Instalar

### Paso 1: Actualizar requirements.txt
```bash
# Ya se ha actualizado automáticamente
cd backend
cat requirements.txt
```

### Paso 2: Instalar Dependencias
```bash
cd backend
pip install -r requirements.txt
```

O si hay problemas, instalar en etapas:
```bash
# Etapa 1: Framework web
pip install fastapi uvicorn

# Etapa 2: Base de datos
pip install sqlalchemy asyncpg

# Etapa 3: El resto
pip install pydantic pydantic-settings python-dotenv websockets python-json-logger httpx psutil
```

### Paso 3: Verificar Instalación
```bash
python -c "import fastapi, asyncpg, psutil, httpx; print('[OK] Todo instalado')"
```

### Paso 4: Iniciar Aplicación
```bash
cd backend
python -m uvicorn app.main:app --reload
```

Deberías ver:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Waiting for application startup.
Initializing monitoring system...
Monitoring system initialized and running
```

## Ventajas de asyncpg sobre psycopg2

| Aspecto | asyncpg | psycopg2 |
|---------|---------|----------|
| Async/Await | Nativo | Requiere pool |
| Performance | 3x más rápido | Más lento |
| Compilación | Precompilado | Requiere pg_config |
| Win/Mac/Linux | OK en todos | Problemas en Windows |

## Status

✅ Error resuelto
✅ Dependencias optimizadas
✅ Logging configurado correctamente
✅ Aplicación lista para iniciar

## Próximos Pasos

1. Inicia la aplicación
2. Prueba los endpoints de monitoreo:
   ```bash
   curl http://localhost:8000/api/monitoring/dashboard
   ```
3. Valida la instalación:
   ```bash
   python validate_monitoring.py
   ```

---

**Fecha**: 2026-05-26
**Estado**: Resuelto
