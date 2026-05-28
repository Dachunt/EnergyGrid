import asyncio
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes import metrics, districts
from app.routes.monitoring import router as monitoring_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.websocket_manager import router as ws_router
from app.auth import get_password_hash
from app.db import init_db, close_db
from app.logging_config import setup_logging
from app.services.metric_queue import queue_worker
from app.services.monitoring_orchestrator import MonitoringOrchestrator

setup_logging()
logger = logging.getLogger("energygrid")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[STARTUP] Initializing database...")
    await init_db(app)
    print("[STARTUP] Database initialized")
    
    print("[STARTUP] Starting queue worker...")
    asyncio.create_task(queue_worker(app))
    print("[STARTUP] Queue worker started")
    
    print("[STARTUP] Ensuring default admin user exists...")
    await _ensure_admin(app)
    print("[STARTUP] Admin user verified")

    print("[STARTUP] Application started successfully!")
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] Closing database...")
    await close_db(app)
    print("[SHUTDOWN] Application shutdown complete")

app = FastAPI(title="EnergyGrid Backend", lifespan=lifespan)

# Montar archivos estáticos
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(districts.router)
app.include_router(monitoring_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ws_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration,
        },
    )
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    """Serve the monitoring dashboard"""
    from fastapi.responses import FileResponse
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "Dashboard not found"}

@app.get("/dashboard")
async def dashboard():
    """Serve the monitoring dashboard at /dashboard"""
    from fastapi.responses import FileResponse
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "Dashboard not found"}


async def _ensure_admin(app):
    """Ensure default admin user and seed data exist"""
    pool = getattr(app.state, "db", None)
    if not pool:
        print("[SEED] No database available, skipping seed data")
        return
    try:
        async with pool.acquire() as conn:
            existing = await conn.fetchval("SELECT id FROM usuarios WHERE username = 'admin'")
            if not existing:
                hash_val = get_password_hash("Admin123!")
                await conn.execute(
                    "INSERT INTO usuarios (username, email, password_hash, nombre_completo, rol) "
                    "VALUES ('admin', 'admin@energygrid.com', $1, 'Administrador del Sistema', 'admin')",
                    hash_val
                )
                print("[SEED] Default admin user created (admin / Admin123!)")
            else:
                print("[SEED] Default admin user already exists")

            districts_exist = await conn.fetchval("SELECT COUNT(*) FROM distritos")
            if districts_exist == 0:
                await conn.execute("""
                    INSERT INTO distritos (id, nombre, latitud, longitud, descripcion) VALUES
                      ('San Salvador',      'San Salvador',      13.6929, -89.2182, 'Distrito capital y centro financiero'),
                      ('Antiguo Cuscatlan', 'Antiguo Cuscatl\u00e1n', 13.7114, -89.2964, 'Distrito comercial y empresarial'),
                      ('Santa Tecla',       'Santa Tecla',       13.6816, -89.2833, 'Distrito residencial y comercial'),
                      ('Soyapango',         'Soyapango',         13.6667, -89.1833, 'Distrito industrial y populoso')
                    ON CONFLICT (id) DO NOTHING
                """)
                print("[SEED] Default districts created")
            else:
                print("[SEED] Districts already exist")

            subs_exist = await conn.fetchval("SELECT COUNT(*) FROM subestaciones")
            if subs_exist == 0:
                await conn.execute("""
                    INSERT INTO subestaciones (id, nombre, distrito, capacidad_kw, latitud, longitud) VALUES
                      ('SSS001', 'Subestacion Centro',    'San Salvador',      5000.00, 13.6929, -89.2182),
                      ('SSS002', 'Subestacion Norte',     'San Salvador',      4500.00, 13.7000, -89.2000),
                      ('SAN001', 'Subestacion Antiguo',   'Antiguo Cuscatlan', 3000.00, 13.7114, -89.2964),
                      ('STC001', 'Subestacion Santa Tecla', 'Santa Tecla',     3500.00, 13.6816, -89.2833),
                      ('SAL001', 'Subestacion Soyapango', 'Soyapango',         4000.00, 13.6667, -89.1833)
                    ON CONFLICT (id) DO NOTHING
                """)
                print("[SEED] Default substations created")
            else:
                print("[SEED] Substations already exist")
    except Exception as e:
        print(f"[SEED] Error ensuring seed data: {e}")
