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
from app.websocket_manager import router as ws_router
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(districts.router)
app.include_router(monitoring_router)
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
