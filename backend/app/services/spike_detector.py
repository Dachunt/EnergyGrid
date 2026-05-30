"""
spike_detector.py
-----------------
Detecta picos bruscos de energía en un distrito comparando la métrica
actual contra el promedio reciente almacenado en la base de datos.

Definición de pico:
  • El consumo_kw sube ≥ SPIKE_PERCENT_THRESHOLD % respecto al promedio
    de las últimas SPIKE_WINDOW_MINUTES minutos del mismo distrito.
  • Solo se dispara si el promedio de referencia tiene al menos
    SPIKE_MIN_SAMPLES puntos (evita falsos positivos al arrancar).

Niveles de pico:
  • MODERADO  → subida ≥ 15 % y < 30 %
  • ALTO      → subida ≥ 30 % y < 50 %
  • CRITICO   → subida ≥ 50 %
"""

import logging
from datetime import datetime, timedelta, timezone

from app.services.structured_logger import log_event

SPIKE_WINDOW_MINUTES = 10          # ventana de referencia
SPIKE_MIN_SAMPLES = 3              # mínimo de muestras para activar detección
SPIKE_THRESHOLDS = {
    "MODERADO": 15.0,
    "ALTO": 30.0,
    "CRITICO": 50.0,
}

logger = logging.getLogger("energygrid")


def _spike_level(pct_increase: float) -> str | None:
    """Retorna el nivel del pico o None si no supera ningún umbral."""
    if pct_increase >= SPIKE_THRESHOLDS["CRITICO"]:
        return "CRITICO"
    if pct_increase >= SPIKE_THRESHOLDS["ALTO"]:
        return "ALTO"
    if pct_increase >= SPIKE_THRESHOLDS["MODERADO"]:
        return "MODERADO"
    return None


async def detectar_pico(data: dict, pool) -> dict | None:
    """
    Analiza si la métrica actual representa un pico respecto al historial.

    Returns:
        dict con info del pico si se detectó, None en caso contrario.
    """
    if pool is None:
        return None

    district_id = data["district_id"]
    consumo_actual = data["consumo_kw"]
    ts = data.get("timestamp")
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts is None:
        ts = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    ventana_inicio = ts - timedelta(minutes=SPIKE_WINDOW_MINUTES)

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    AVG(consumo_kw)::float8  AS promedio_kw,
                    COUNT(*)                 AS num_muestras
                FROM consumo_temporal
                WHERE district_id = $1
                  AND timestamp >= $2
                  AND timestamp < $3
                """,
                district_id,
                ventana_inicio,
                ts,
            )
    except Exception as exc:
        log_event(
            logging.ERROR,
            event="SPIKE_DETECTOR_DB_ERROR",
            district_id=district_id,
            error=str(exc),
        )
        return None

    if not row or row["num_muestras"] < SPIKE_MIN_SAMPLES:
        return None

    promedio_kw = row["promedio_kw"]
    if promedio_kw <= 0:
        return None

    pct_increase = ((consumo_actual - promedio_kw) / promedio_kw) * 100
    nivel = _spike_level(pct_increase)

    if nivel is None:
        return None

    spike_info = {
        "district_id": district_id,
        "substation_id": data.get("substation_id"),
        "consumo_actual_kw": round(consumo_actual, 2),
        "promedio_referencia_kw": round(promedio_kw, 2),
        "incremento_porcentual": round(pct_increase, 2),
        "nivel": nivel,
        "ventana_minutos": SPIKE_WINDOW_MINUTES,
        "num_muestras": int(row["num_muestras"]),
        "timestamp": ts.isoformat(),
    }

    log_event(
        logging.WARNING if nivel != "CRITICO" else logging.ERROR,
        event="PICO_ENERGIA",
        service="spike_detector",
        **spike_info,
    )

    return spike_info
