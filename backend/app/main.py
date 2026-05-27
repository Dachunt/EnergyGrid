import asyncio
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import metrics, districts
from app.websocket_manager import router as ws_router
from app.db import init_db, close_db
from app.logging_config import setup_logging
from app.services.metric_queue import queue_worker

setup_logging()
logger = logging.getLogger("energygrid")

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
    await init_db(app)
    asyncio.create_task(queue_worker(app))

@app.on_event("shutdown")
async def shutdown():
    await close_db(app)

@app.get("/health")
async def health():
    return {"status": "ok"}
