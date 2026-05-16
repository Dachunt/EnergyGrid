import logging
import sys
import json
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import metrics, districts
from app.websocket_manager import router as ws_router


# ── Logging JSON estructurado (EN-35) ─────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    """
    Formatea cada log como una línea JSON con los campos:
    timestamp, level, service, event (y extras opcionales).
    """
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level":     record.levelname,
            "service":   "backend",
            "event":     record.getMessage(),
        }
        # Campos extra pasados con extra={...}
        for key in ("event", "district_id", "substation_id", "porcentaje", "action"):
            if hasattr(record, key):
                log[key] = getattr(record, key)
        return json.dumps(log, ensure_ascii=False)


def setup_logging():
    formatter = JSONFormatter()

    # Handler 1: stdout (para docker compose logs)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    # Handler 2: archivo en volumen energygrid-logs
    file_handler = logging.FileHandler("/app/logs/backend.log")
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[stdout_handler, file_handler],
    )


setup_logging()
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
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


@app.on_event("startup")
async def startup():
    from app.db import init_pool
    from app.services.retention_job import start_retention_scheduler
    await init_pool()
    start_retention_scheduler()
    logger.info("Backend iniciado correctamente")


@app.on_event("shutdown")
async def shutdown():
    from app.db import close_pool
    from app.services.retention_job import stop_retention_scheduler
    stop_retention_scheduler()
    await close_pool()
    logger.info("Backend apagado correctamente")


@app.get("/health")
async def health():
    return {"status": "ok"}
