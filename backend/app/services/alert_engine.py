import logging
from datetime import datetime, timezone, timedelta

from app.websocket_manager import manager
from app.services.load_balancer import redistribuir_carga
from app.services.structured_logger import log_event
from app.services.spike_detector import detectar_pico
from app.services.notification_service import notificar_pico
from app.services.alert_file_logger import registrar_alerta_en_archivo


_subestaciones_caidas: set[str] = set()


async def detectar_subestaciones_caidas(pool):
    if not pool:
        return
    global _subestaciones_caidas
    now = datetime.now(timezone.utc)
    threshold = timedelta(seconds=15)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT substation_id, district_id, MAX(timestamp) as last_ts
            FROM consumo_temporal
            GROUP BY substation_id, district_id
        """)

    currently_down: set[str] = set()
    for row in rows:
        sid = row["substation_id"]
        last_ts = row["last_ts"]
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)

        if now - last_ts > threshold:
            currently_down.add(sid)
            if sid not in _subestaciones_caidas:
                await _handle_substation_down(pool, sid, row["district_id"])
        else:
            if sid in _subestaciones_caidas:
                await _handle_substation_recovered(pool, sid, row["district_id"])

    _subestaciones_caidas = currently_down


async def _handle_substation_down(pool, sid: str, district_id: str):
    alert_id = await crear_alerta(
        pool,
        district_id=district_id,
        tipo="SUBESTACION_DESCONECTADA",
        descripcion=(
            f"Subestacion {sid} desconectada. "
            "No se reciben datos. Redistribuyendo carga."
        ),
    )
    if alert_id is None:
        return

    await manager.broadcast({
        "event": "SUBESTACION_DESCONECTADA",
        "substation_id": sid,
        "district_id": district_id,
        "nivel": "CRITICO",
    })
    log_event(
        logging.WARNING,
        event="SUBESTACION_DESCONECTADA",
        substation_id=sid,
        district_id=district_id,
    )

    sugerencias = await redistribuir_carga(pool, district_id)
    if sugerencias:
        await manager.broadcast({
            "event": "REDISTRIBUCION",
            "district_id": district_id,
            "sugerencias": sugerencias,
        })


async def _handle_substation_recovered(pool, sid: str, district_id: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE alertas SET resuelta = TRUE
               WHERE district_id = $1
                 AND tipo_alerta = 'SUBESTACION_DESCONECTADA'
                 AND resuelta = FALSE""",
            district_id,
        )
    await manager.broadcast({
        "event": "SUBESTACION_RECONECTADA",
        "substation_id": sid,
        "district_id": district_id,
    })
    log_event(
        logging.INFO,
        event="SUBESTACION_RECONECTADA",
        substation_id=sid,
        district_id=district_id,
    )


async def analizar_metrica(data: dict, pool):
    porcentaje = data.get("porcentaje_uso")
    if porcentaje is None:
        porcentaje = (data["consumo_kw"] / data["capacidad_kw"]) * 100

    await manager.broadcast({
        "event": "ACTUALIZACION",
        "district_id": data["district_id"],
        "substation_id": data["substation_id"],
        "porcentaje": round(porcentaje, 2),
        "consumo_kw": data["consumo_kw"],
        "capacidad_kw": data["capacidad_kw"],
        "timestamp": data.get("timestamp"),
    })

    if porcentaje < 95:
        resolvio = await resolver_alertas_distrito(pool, data["district_id"])
        if resolvio:
            await manager.broadcast({
                "event": "ALERTA_RESUELTA",
                "district_id": data["district_id"],
            })

    if porcentaje >= 95:
        alert_id = await crear_alerta(
            pool,
            district_id=data["district_id"],
            tipo="SOBRECARGA_CRITICA",
            descripcion=(
                f"Distrito al {porcentaje:.1f}% de capacidad. "
                "Riesgo de apagon. Redistribuir carga."
            ),
        )
        if alert_id is None:
            return
        await manager.broadcast({
            "event": "SOBRECARGA",
            "alert_id": alert_id,
            "district_id": data["district_id"],
            "porcentaje": round(porcentaje, 2),
            "consumo_kw": data["consumo_kw"],
            "capacidad_kw": data["capacidad_kw"],
            "nivel": "CRITICO",
            "descripcion": (
                f"Distrito al {porcentaje:.1f}% de capacidad. "
                "Riesgo de apagon."
            ),
        })
        log_event(
            logging.WARNING,
            event="SOBRECARGA",
            district_id=data["district_id"],
            substation_id=data["substation_id"],
            porcentaje=round(porcentaje, 2),
            action="redistribucion_sugerida",
        )
        sugerencias = await redistribuir_carga(pool, data["district_id"])
        registrar_alerta_en_archivo(
            data,
            nivel="CRITICO",
            tipo="SOBRECARGA_CRITICA",
            redistribucion=sugerencias,
        )
        await sugerir_redistribucion(pool, data["district_id"])

    elif porcentaje >= 90:
        await manager.broadcast({
            "event": "ADVERTENCIA",
            "district_id": data["district_id"],
            "porcentaje": round(porcentaje, 2),
            "consumo_kw": data["consumo_kw"],
            "capacidad_kw": data["capacidad_kw"],
            "nivel": "ALTO",
        })
        log_event(
            logging.INFO,
            event="ADVERTENCIA",
            district_id=data["district_id"],
            substation_id=data["substation_id"],
            porcentaje=round(porcentaje, 2),
        )
        registrar_alerta_en_archivo(
            data,
            nivel="ALTO",
            tipo="ADVERTENCIA",
            redistribucion=[],
        )

    spike = await detectar_pico(data, pool)
    if spike:
        await notificar_pico(spike, pool)


async def crear_alerta(pool, district_id: str, tipo: str, descripcion: str):
    async with pool.acquire() as conn:
        existe = await conn.fetchval(
            """
            SELECT id FROM alertas
            WHERE district_id = $1 AND resuelta = FALSE
            LIMIT 1
            """,
            district_id,
        )
        if existe:
            return None
        row = await conn.fetchrow(
            """
            INSERT INTO alertas (district_id, tipo_alerta, descripcion)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            district_id,
            tipo,
            descripcion,
        )
    return int(row["id"])


async def resolver_alertas_distrito(pool, district_id: str) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE alertas
            SET resuelta = TRUE
            WHERE district_id = $1 AND resuelta = FALSE
            """,
            district_id,
        )
    return result != "UPDATE 0"


async def sugerir_redistribucion(pool, district_id: str):
    sugerencias = await redistribuir_carga(pool, district_id)
    if not sugerencias:
        return
    await manager.broadcast({
        "event": "REDISTRIBUCION",
        "district_id": district_id,
        "sugerencias": sugerencias,
    })
