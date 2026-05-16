import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import metrics, districts
from app.websocket_manager import router as ws_router
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="EnergyGrid Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(districts.router)
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


@app.on_event("startup")
async def startup():
    from app.db import init_pool
    from app.services.retention_job import start_retention_scheduler
    await init_pool()
    start_retention_scheduler()
    logger.info("EnergyGrid backend iniciado", extra={"event": "startup"})


@app.on_event("shutdown")
async def shutdown():
    from app.db import close_pool
    from app.services.retention_job import stop_retention_scheduler
    stop_retention_scheduler()
    await close_pool()
    logger.info("EnergyGrid backend apagado", extra={"event": "shutdown"})


@app.get("/health")
async def health():
    return {"status": "ok"}
