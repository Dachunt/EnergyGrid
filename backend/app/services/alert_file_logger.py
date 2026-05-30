import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("energygrid")

ALERTAS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "logs",
    "alertas",
)


def _asegurar_directorio():
    os.makedirs(ALERTAS_DIR, exist_ok=True)


def _ruta_archivo_hoy() -> str:
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(ALERTAS_DIR, f"alertas_{fecha}.log")


def _formatear_redistribucion(redistribucion: list) -> str:
    if not redistribucion:
        return "ninguna (sin candidatos disponibles o no aplica)"
    partes = [
        f"{r['district_id']} ({r['porcentaje_uso']:.1f}% uso)"
        for r in redistribucion
    ]
    return ", ".join(partes)


def registrar_alerta_en_archivo(
    data: dict,
    nivel: str,
    tipo: str,
    redistribucion: list = None,
):
    if redistribucion is None:
        redistribucion = []

    try:
        _asegurar_directorio()
        ruta = _ruta_archivo_hoy()

        ts = data.get("timestamp")
        if ts is None:
            ts = datetime.now(timezone.utc).isoformat()

        district_id   = data.get("district_id", "N/A")
        substation_id = data.get("substation_id", "N/A")
        consumo_kw    = data.get("consumo_kw", 0.0)
        capacidad_kw  = data.get("capacidad_kw", 0.0)
        porcentaje    = data.get("porcentaje_uso")
        if porcentaje is None and capacidad_kw > 0:
            porcentaje = (consumo_kw / capacidad_kw) * 100
        porcentaje = round(porcentaje or 0.0, 2)

        redistribucion_txt = _formatear_redistribucion(redistribucion)

        separador = "=" * 70
        entrada = (
            f"\n{separador}\n"
            f"  ALERTA DE MONITOREO\n"
            f"{separador}\n"
            f"  Timestamp       : {ts}\n"
            f"  Tipo            : {tipo}\n"
            f"  Nivel           : {nivel}\n"
            f"  Distrito        : {district_id}\n"
            f"  Subestación     : {substation_id}\n"
            f"  Consumo actual  : {consumo_kw:.2f} kW\n"
            f"  Capacidad total : {capacidad_kw:.2f} kW\n"
            f"  Porcentaje uso  : {porcentaje:.2f}%\n"
            f"  Redistribución  : {redistribucion_txt}\n"
            f"{separador}\n"
        )

        with open(ruta, "a", encoding="utf-8") as f:
            f.write(entrada)

        logger.info(f"[ALERT_FILE_LOGGER] Alerta {tipo}/{nivel} registrada en {ruta}")

    except Exception as exc:
        logger.error(f"[ALERT_FILE_LOGGER] Error al escribir archivo de alerta: {exc}")
