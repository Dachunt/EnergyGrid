import asyncio
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes import metrics, districts, demo
from app.routes.monitoring import router as monitoring_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.websocket_manager import router as ws_router, manager as ws_manager
from app.auth import get_password_hash
from app.db import init_db, close_db
from app.logging_config import setup_logging
from app.services.metric_queue import queue_worker
from app.routes.monitoring import set_pool_getter as set_monitoring_pool_getter
from app.routes.monitoring import get_monitoring_instance

setup_logging()
logger = logging.getLogger("energygrid")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[STARTUP] Initializing database...")
    await init_db(app)
    print("[STARTUP] Database initialized")

    print("[STARTUP] Configuring monitoring pool getter...")
    set_monitoring_pool_getter(lambda: getattr(app.state, "db", None))
    print("[STARTUP] Monitoring pool getter configured")

    print("[STARTUP] Connecting to Redis for WebSocket broadcast...")
    await ws_manager.connect_redis()
    print("[STARTUP] Redis connection established")
    
    print("[STARTUP] Starting queue worker...")
    asyncio.create_task(queue_worker(app))
    print("[STARTUP] Queue worker started")

    print("[STARTUP] Starting data retention cleanup...")
    asyncio.create_task(_data_retention_cleanup(app))
    print("[STARTUP] Data retention cleanup started")

    print("[STARTUP] Starting substation watchdog...")
    asyncio.create_task(_substation_watchdog(app))
    print("[STARTUP] Substation watchdog started")
    
    print("[STARTUP] Ensuring default admin user exists...")
    await _ensure_admin(app)
    print("[STARTUP] Admin user verified")

    print("[STARTUP] Initializing monitoring system...")
    monitor = get_monitoring_instance()
    await monitor.initialize_monitoring()
    asyncio.create_task(monitor.start_continuous_monitoring())
    print("[STARTUP] Monitoring system started!")

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
app.include_router(demo.router)
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


async def _data_retention_cleanup(app):
    """Borra registros de consumo_temporal mayores a 7 días, cada hora"""
    while True:
        try:
            pool = getattr(app.state, "db", None)
            if pool:
                async with pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM consumo_temporal WHERE timestamp < NOW() - INTERVAL '7 days'"
                    )
                    deleted = result.split()[-1] if result else "0"
                    if int(deleted) > 0:
                        logger.info("Data retention cleanup completed", extra={"deleted_records": int(deleted)})
        except Exception as e:
            logger.error(f"Data retention cleanup error: {e}")
        await asyncio.sleep(3600)  # cada hora


async def _substation_watchdog(app):
    while True:
        try:
            pool = getattr(app.state, "db", None)
            if pool:
                from app.services.alert_engine import detectar_subestaciones_caidas
                await detectar_subestaciones_caidas(pool)
        except Exception as e:
            logger.error(f"Substation watchdog error: {e}")
        await asyncio.sleep(10)


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
