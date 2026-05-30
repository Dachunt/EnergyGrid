"""
notification_service.py
-----------------------
Convierte un pico detectado en:
  1. Un broadcast WebSocket hacia todos los clientes conectados.
  2. Un log en archivo de picos (spikes/spikes_YYYY-MM-DD.log).
  3. Un log JSON estructurado con todos los campos requeridos.
  4. Una alerta persistida en la tabla `alertas` de la BD.
"""

import logging
from datetime import datetime, timezone

from app.websocket_manager import manager
from app.services.structured_logger import log_event
from app.services.spike_file_logger import registrar_pico_en_archivo
from app.services.load_balancer import redistribuir_carga

logger = logging.getLogger("energygrid")

_NIVEL_DESCRIPCION = {
    "MODERADO": (
        "Pico moderado detectado en {district_id}. "
        "Consumo subió {incremento_porcentual:.1f}% respecto al promedio reciente."
    ),
    "ALTO": (
        "Pico alto en {district_id}. "
        "Consumo aumentó {incremento_porcentual:.1f}%. Monitorear de cerca."
    ),
    "CRITICO": (
        "⚠️ PICO CRÍTICO en {district_id}. "
        "Consumo disparado un {incremento_porcentual:.1f}% por encima del promedio. "
        "Riesgo de sobrecarga."
    ),
}


def _build_descripcion(spike: dict) -> str:
    template = _NIVEL_DESCRIPCION.get(spike["nivel"], "Pico detectado en {district_id}.")
    return template.format(**spike)


async def notificar_pico(spike: dict, pool) -> int | None:
    nivel = spike["nivel"]
    district_id = spike["district_id"]
    descripcion = _build_descripcion(spike)
    ts = spike.get("timestamp", datetime.now(timezone.utc).isoformat())

    # ── 1. Broadcast WebSocket ───────────────────────────────────────────────
    payload = {
        "event": "PICO_ENERGIA",
        "nivel": nivel,
        "district_id": district_id,
        "substation_id": spike.get("substation_id"),
        "consumo_kw": spike["consumo_actual_kw"],
        "promedio_kw": spike["promedio_referencia_kw"],
        "incremento_pct": spike["incremento_porcentual"],
        "descripcion": descripcion,
        "timestamp": ts,
    }
    await manager.broadcast(payload)

    # ── 2. Log en archivo de picos (spikes/spikes_YYYY-MM-DD.log) ───────────
    redistribucion = []
    if pool is not None:
        try:
            redistribucion = await redistribuir_carga(pool, district_id)
        except Exception:
            redistribucion = []
    registrar_pico_en_archivo(spike, redistribucion)

    # ── 3. Log estructurado ──────────────────────────────────────────────────
    log_level = logging.ERROR if nivel == "CRITICO" else logging.WARNING
    log_event(
        log_level,
        event="PICO_ENERGIA_NOTIFICADO",
        service="notification_service",
        district_id=district_id,
        substation_id=spike.get("substation_id"),
        nivel=nivel,
        consumo_kw=spike["consumo_actual_kw"],
        incremento_pct=spike["incremento_porcentual"],
        descripcion=descripcion,
    )

    # ── 4. Persistir en BD ───────────────────────────────────────────────────
    if pool is None:
        logger.warning(
            f"[NOTIFICATION] BD no disponible; alerta de pico {nivel} en {district_id} no persistida."
        )
        return None

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO alertas (district_id, tipo_alerta, descripcion)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                district_id,
                f"PICO_{nivel}",
                descripcion,
            )
        alert_id = int(row["id"])
        log_event(
            logging.INFO,
            event="ALERTA_PICO_PERSISTIDA",
            alert_id=alert_id,
            district_id=district_id,
            nivel=nivel,
        )
        return alert_id

    except Exception as exc:
        log_event(
            logging.ERROR,
            event="ALERTA_PICO_DB_ERROR",
            district_id=district_id,
            nivel=nivel,
            error=str(exc),
        )
        return None
