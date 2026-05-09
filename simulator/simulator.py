import os
import time
import random
import math
import logging
from datetime import datetime, timedelta

import requests

BACKEND_URL = os.environ["BACKEND_URL"]
INTERVAL_MS = int(os.environ.get("INTERVAL_MS", 1000))

SUBESTACIONES = [
    {"id": "SSS001", "distrito": "San Salvador",      "capacidad": 5000},
    {"id": "SSS002", "distrito": "San Salvador",      "capacidad": 4500},
    {"id": "SAN001", "distrito": "Antiguo Cuscatlán", "capacidad": 3000},
    {"id": "STC001", "distrito": "Santa Tecla",       "capacidad": 3500},
    {"id": "SAL001", "distrito": "Soyapango",         "capacidad": 4000},
]

logging.basicConfig(level=logging.INFO)


def get_hora_virtual():
    segundos = time.time() % (24 * 60)
    return segundos / 60


def calcular_consumo(capacidad, hora):
    if 18 <= hora <= 21:
        factor = random.uniform(0.88, 0.98)
    elif 6 <= hora <= 9:
        factor = random.uniform(0.70, 0.85)
    else:
        factor = random.uniform(0.30, 0.65)
    return round(capacidad * factor, 2)


def inyectar_sobrecarga(subestacion):
    return round(subestacion["capacidad"] * random.uniform(0.96, 1.05), 2)


if __name__ == "__main__":
    logging.info(f"Simulador iniciado. Enviando a {BACKEND_URL} cada {INTERVAL_MS}ms")

    while True:
        hora = get_hora_virtual()
        for sub in SUBESTACIONES:
            consumo = calcular_consumo(sub["capacidad"], hora)
            payload = {
                "substation_id": sub["id"],
                "district_id":   sub["distrito"],
                "consumo_kw":    consumo,
                "capacidad_kw":  sub["capacidad"],
                "timestamp":     datetime.utcnow().isoformat(),
            }
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/api/metrics", json=payload, timeout=5
                )
                if resp.status_code != 200:
                    logging.warning(f"Status {resp.status_code} para {sub['id']}")
            except Exception as e:
                logging.error(f"Error enviando datos de {sub['id']}: {e}")

        time.sleep(INTERVAL_MS / 1000)
