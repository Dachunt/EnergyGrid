import logging

from app.websocket_manager import manager
from app.services.load_balancer import redistribuir_carga
from app.services.structured_logger import log_event


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


async def crear_alerta(pool, district_id: str, tipo: str, descripcion: str) -> int:
    async with pool.acquire() as conn:
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


async def sugerir_redistribucion(pool, district_id: str):
    sugerencias = await redistribuir_carga(pool, district_id)
    if not sugerencias:
        return
    await manager.broadcast({
        "event": "REDISTRIBUCION",
        "district_id": district_id,
        "sugerencias": sugerencias,
    })
