import os
import re
from fastapi import APIRouter

router = APIRouter(prefix="/api/logs", tags=["logs"])

SPIKES_DIR = "/app/logs/spikes"


def parsear_archivo_spikes(ruta: str) -> list:
    spikes = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()

        bloques = contenido.split("=" * 70)
        for bloque in bloques:
            if "PICO DE ENERGÍA DETECTADO" not in bloque:
                continue
            spike = {}
            for linea in bloque.strip().splitlines():
                linea = linea.strip()
                if linea.startswith("Timestamp"):
                    spike["timestamp"] = linea.split(":", 1)[1].strip()
                elif linea.startswith("Nivel"):
                    spike["nivel"] = linea.split(":", 1)[1].strip()
                elif linea.startswith("Distrito"):
                    spike["district_id"] = linea.split(":", 1)[1].strip()
                elif linea.startswith("Subestación"):
                    spike["substation_id"] = linea.split(":", 1)[1].strip()
                elif linea.startswith("Consumo actual"):
                    val = re.findall(r"[\d.]+", linea)
                    spike["consumo_actual_kw"] = float(val[0]) if val else 0
                elif linea.startswith("Promedio ref"):
                    val = re.findall(r"[\d.]+", linea)
                    spike["promedio_referencia_kw"] = float(val[0]) if val else 0
                elif linea.startswith("Incremento"):
                    val = re.findall(r"[\d.]+", linea)
                    spike["incremento_porcentual"] = float(val[0]) if val else 0
                elif linea.startswith("Redistribución"):
                    spike["redistribucion"] = linea.split(":", 1)[1].strip()
            if spike.get("nivel"):
                spikes.append(spike)
    except Exception:
        pass
    return spikes


@router.get("/spikes")
async def get_spike_logs():
    todos = []
    try:
        if os.path.exists(SPIKES_DIR):
            for archivo in sorted(os.listdir(SPIKES_DIR), reverse=True)[:7]:
                if archivo.endswith(".log"):
                    ruta = os.path.join(SPIKES_DIR, archivo)
                    todos.extend(parsear_archivo_spikes(ruta))
    except Exception as e:
        return {"spikes": [], "error": str(e)}
    todos.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"spikes": todos[:100]}
