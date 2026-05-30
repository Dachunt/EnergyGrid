import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("energygrid")

SPIKES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "logs",
    "spikes",
)


def _asegurar_directorio():
    os.makedirs(SPIKES_DIR, exist_ok=True)


def _ruta_archivo_hoy() -> str:
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(SPIKES_DIR, f"spikes_{fecha}.log")


def _formatear_redistribucion(redistribucion: list) -> str:
    if not redistribucion:
        return "ninguna (sin candidatos disponibles)"
    partes = [
        f"{r['district_id']} ({r['porcentaje_uso']:.1f}% uso)"
        for r in redistribucion
    ]
    return ", ".join(partes)


def registrar_pico_en_archivo(spike: dict, redistribucion: list = None):
    if redistribucion is None:
        redistribucion = []

    try:
        _asegurar_directorio()
        ruta = _ruta_archivo_hoy()

        ts = spike.get("timestamp", datetime.now(timezone.utc).isoformat())
        nivel = spike.get("nivel", "DESCONOCIDO")
        district_id = spike.get("district_id", "N/A")
        substation_id = spike.get("substation_id", "N/A")
        consumo_actual = spike.get("consumo_actual_kw", 0.0)
        promedio_ref = spike.get("promedio_referencia_kw", 0.0)
        incremento = spike.get("incremento_porcentual", 0.0)
        num_muestras = spike.get("num_muestras", 0)
        ventana = spike.get("ventana_minutos", 10)
        redistribucion_txt = _formatear_redistribucion(redistribucion)

        separador = "=" * 70
        entrada = (
            f"\n{separador}\n"
            f"  PICO DE ENERGÍA DETECTADO\n"
            f"{separador}\n"
            f"  Timestamp       : {ts}\n"
            f"  Nivel           : {nivel}\n"
            f"  Distrito        : {district_id}\n"
            f"  Subestación     : {substation_id}\n"
            f"  Consumo actual  : {consumo_actual:.2f} kW\n"
            f"  Promedio ref.   : {promedio_ref:.2f} kW (últimos {ventana} min, {num_muestras} muestras)\n"
            f"  Incremento      : +{incremento:.2f}%\n"
            f"  Redistribución  : {redistribucion_txt}\n"
            f"{separador}\n"
        )

        with open(ruta, "a", encoding="utf-8") as f:
            f.write(entrada)

        logger.info(f"[SPIKE_FILE_LOGGER] Pico {nivel} registrado en {ruta}")

    except Exception as exc:
        logger.error(f"[SPIKE_FILE_LOGGER] Error al escribir archivo de pico: {exc}")
