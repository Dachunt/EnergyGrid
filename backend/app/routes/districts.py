import json
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
            WITH latest_per_substation AS (
                SELECT DISTINCT ON (ct.substation_id)
                    ct.district_id,
                    ct.substation_id,
                    ct.consumo_kw,
                    ct.capacidad_kw,
                    ct.porcentaje_uso
                FROM consumo_temporal ct
                INNER JOIN subestaciones s ON s.id = ct.substation_id AND s.activa = TRUE
                ORDER BY ct.substation_id, ct.timestamp DESC
            )
            SELECT
                d.id AS district_id,
                d.nombre,
                d.latitud::float8 AS latitud,
                d.longitud::float8 AS longitud,
                d.activo,
                COALESCE(sub.consumo_total, 0)::float8 AS consumo_kw,
                COALESCE(sub.capacidad_total, 0)::float8 AS capacidad_kw,
                CASE WHEN sub.capacidad_total > 0
                    THEN (sub.consumo_total / sub.capacidad_total * 100)::float8
                    ELSE 0
                END AS porcentaje_uso,
                COALESCE(sub.subestaciones, '[]'::jsonb) AS subestaciones
            FROM distritos d
            LEFT JOIN (
                SELECT
                    lps.district_id,
                    SUM(lps.consumo_kw::float8) AS consumo_total,
                    SUM(lps.capacidad_kw::float8) AS capacidad_total,
                    jsonb_agg(
                        jsonb_build_object(
                            'substation_id', lps.substation_id,
                            'consumo_kw', lps.consumo_kw::float8,
                            'capacidad_kw', lps.capacidad_kw::float8,
                            'porcentaje_uso', lps.porcentaje_uso::float8,
                            'latitud', s.latitud::float8,
                            'longitud', s.longitud::float8
                        )
                        ORDER BY lps.substation_id
                    ) AS subestaciones
                FROM latest_per_substation lps
                LEFT JOIN subestaciones s ON s.id = lps.substation_id
                GROUP BY lps.district_id
            ) sub ON sub.district_id = d.id
            WHERE d.activo = TRUE
            ORDER BY d.id
            """
        )
    result = []
    for row in rows:
        d = dict(row)
        if isinstance(d.get("subestaciones"), str):
            d["subestaciones"] = json.loads(d["subestaciones"])
        result.append(d)
    return result


@router.get("/simulator/districts")
async def get_simulator_districts(request: Request):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                d.id AS district_id,
                d.nombre,
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'id', s.id,
                            'capacidad_kw', s.capacidad_kw
                        )
                    ) FILTER (WHERE s.id IS NOT NULL),
                    '[]'::jsonb
                ) AS substations
            FROM distritos d
            LEFT JOIN subestaciones s ON s.distrito = d.id AND s.activa = TRUE
            WHERE d.activo = TRUE
            GROUP BY d.id, d.nombre
            ORDER BY d.id
            """
        )
    result = []
    for row in rows:
        subs = row["substations"]
        if isinstance(subs, str):
            subs = json.loads(subs)
        result.append({
            "district_id": row["district_id"],
            "nombre": row["nombre"],
            "substations": subs,
        })
    return result


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
