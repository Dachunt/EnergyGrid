import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

from app.models.consumption import MetricPayload
from app.services.alert_engine import analizar_metrica
from app.services.structured_logger import log_event
from app.services.metric_queue import enqueue

router = APIRouter(prefix="/api", tags=["metrics"])

_SUSPICIOUS_PATTERN = re.compile(r"[;'\"]|--")


@router.post("/metrics")
async def receive_metric(payload: MetricPayload, request: Request):
    if payload.consumo_kw <= 0 or payload.capacidad_kw <= 0:
        raise HTTPException(status_code=422, detail="valores invalidos")

    now = datetime.now(timezone.utc)
    ts = payload.timestamp or now
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    if ts < now - timedelta(hours=24) or ts > now + timedelta(hours=24):
        log_event(
            logging.WARNING,
            event="TIMESTAMP_INVALIDO",
            district_id=payload.district_id,
            timestamp=str(ts),
        )
        raise HTTPException(status_code=422, detail="timestamp fuera de rango")

    anomalia = False
    notas = None
    if _SUSPICIOUS_PATTERN.search(payload.district_id) or _SUSPICIOUS_PATTERN.search(
        payload.substation_id
    ):
        anomalia = True
        notas = "sospecha_sql"

    pool = request.app.state.db
    if pool is None:
        enqueue({
            "district_id": payload.district_id,
            "substation_id": payload.substation_id,
            "consumo_kw": payload.consumo_kw,
            "capacidad_kw": payload.capacidad_kw,
            "timestamp": ts,
            "anomalia": anomalia,
            "notas": notas,
        })
        porcentaje = (payload.consumo_kw / payload.capacidad_kw) * 100
        data = {
            "district_id": payload.district_id,
            "substation_id": payload.substation_id,
            "consumo_kw": payload.consumo_kw,
            "capacidad_kw": payload.capacidad_kw,
            "timestamp": ts.isoformat(),
            "porcentaje_uso": porcentaje,
        }
        await analizar_metrica(data, pool)
        return {"status": "queued", "porcentaje_uso": porcentaje}

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO consumo_temporal (
                    district_id,
                    substation_id,
                    consumo_kw,
                    capacidad_kw,
                    timestamp,
                    anomalia,
                    notas
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, porcentaje_uso::float8 AS porcentaje_uso
                """,
                payload.district_id,
                payload.substation_id,
                payload.consumo_kw,
                payload.capacidad_kw,
                ts,
                anomalia,
                notas,
            )
    except Exception as exc:
        log_event(logging.ERROR, event="DB_ERROR", error=str(exc), district_id=payload.district_id)
        enqueue({
            "district_id": payload.district_id,
            "substation_id": payload.substation_id,
            "consumo_kw": payload.consumo_kw,
            "capacidad_kw": payload.capacidad_kw,
            "timestamp": ts,
            "anomalia": anomalia,
            "notas": notas,
        })
        porcentaje = (payload.consumo_kw / payload.capacidad_kw) * 100
        data = {
            "district_id": payload.district_id,
            "substation_id": payload.substation_id,
            "consumo_kw": payload.consumo_kw,
            "capacidad_kw": payload.capacidad_kw,
            "timestamp": ts.isoformat(),
            "porcentaje_uso": porcentaje,
        }
        await analizar_metrica(data, pool)
        return {"status": "queued", "porcentaje_uso": porcentaje}

    porcentaje = row["porcentaje_uso"]
    data = {
        "district_id": payload.district_id,
        "substation_id": payload.substation_id,
        "consumo_kw": payload.consumo_kw,
        "capacidad_kw": payload.capacidad_kw,
        "timestamp": ts.isoformat(),
        "porcentaje_uso": porcentaje,
    }
    await analizar_metrica(data, pool)

    log_event(
        logging.INFO,
        event="METRICA_RECIBIDA",
        district_id=payload.district_id,
        substation_id=payload.substation_id,
        consumo_kw=payload.consumo_kw,
        capacidad_kw=payload.capacidad_kw,
        porcentaje=round(porcentaje, 2),
        anomalia=anomalia,
    )

    return {"status": "ok", "id": int(row["id"]), "porcentaje_uso": porcentaje}
