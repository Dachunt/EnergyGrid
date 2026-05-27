import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.services.structured_logger import log_event
from app.websocket_manager import manager

router = APIRouter(prefix="/api", tags=["districts"])

SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://localhost:8001")


@router.get("/districts")
async def get_districts(request: Request):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (district_id)
                district_id,
                substation_id,
                consumo_kw::float8 AS consumo_kw,
                capacidad_kw::float8 AS capacidad_kw,
                porcentaje_uso::float8 AS porcentaje_uso,
                timestamp
            FROM consumo_temporal
            ORDER BY district_id, timestamp DESC
            """
        )
    return [dict(row) for row in rows]


@router.get("/districts/{district_id}/history")
async def get_district_history(district_id: str, request: Request, limit: int = 100):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                district_id,
                substation_id,
                consumo_kw::float8 AS consumo_kw,
                capacidad_kw::float8 AS capacidad_kw,
                porcentaje_uso::float8 AS porcentaje_uso,
                timestamp
            FROM consumo_temporal
            WHERE district_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            district_id,
            limit,
        )
    return [dict(row) for row in rows]


@router.get("/alerts")
async def get_alerts(request: Request, resolved: bool = False):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                district_id,
                tipo_alerta,
                descripcion,
                timestamp,
                resuelta
            FROM alertas
            WHERE resuelta = $1
            ORDER BY timestamp DESC
            """,
            resolved,
        )
    return [dict(row) for row in rows]


@router.post("/districts/{district_id}/redistribute")
async def redistribute_load(district_id: str, to: str, request: Request, factor: float = 0.55):
    """
    Aplica redistribución de carga desde district_id hacia 'to'.
    Llama al simulador para que reduzca el consumo del distrito origen.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{SIMULATOR_URL}/simulator/set-redistribution",
                params={"district": district_id, "factor": factor},
            )
            resp.raise_for_status()
    except Exception as exc:
        log_event(logging.ERROR, event="REDISTRIBUCION_ERROR", error=str(exc), district_id=district_id)
        raise HTTPException(status_code=502, detail=f"No se pudo contactar al simulador: {exc}")

    await manager.broadcast({
        "event": "REDISTRIBUCION_APLICADA",
        "from_district": district_id,
        "to_district": to,
        "factor": factor,
        "message": f"Carga redistribuida de {district_id} hacia {to}. Consumo reducido al {int(factor*100)}%.",
    })
    log_event(
        logging.INFO,
        event="REDISTRIBUCION_APLICADA",
        from_district=district_id,
        to_district=to,
        factor=factor,
    )
    return {"status": "ok", "from": district_id, "to": to, "factor": factor}


@router.delete("/districts/{district_id}/redistribute")
async def clear_redistribution(district_id: str):
    """Elimina la redistribución activa de un distrito."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{SIMULATOR_URL}/simulator/clear-redistribution",
                params={"district": district_id},
            )
            resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    await manager.broadcast({
        "event": "REDISTRIBUCION_ELIMINADA",
        "district_id": district_id,
    })
    return {"status": "ok", "district": district_id}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, request: Request):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE alertas
            SET resuelta = TRUE
            WHERE id = $1
            RETURNING id, district_id, tipo_alerta, descripcion, timestamp, resuelta
            """,
            alert_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="alerta no encontrada")
    return dict(row)
