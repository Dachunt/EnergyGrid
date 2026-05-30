import os
import time
import random
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
INTERVAL_MS = int(os.environ.get("INTERVAL_MS", 1000))  # default 1 s

# Ciclo virtual: 24 minutos reales = 24 horas virtuales
# 60 segundos reales = 1 hora virtual
# Minuto 12 real = hora 12 virtual (HORA PICO)
CICLO_VIRTUAL_SEG = 24 * 60   # 1440 segundos
SEGUNDOS_POR_HORA_VIRTUAL = CICLO_VIRTUAL_SEG / 24  # 60 s

# Spike automático: cada 60 segundos en una subestación aleatoria, dura 30 s
AUTO_SPIKE_INTERVAL_SEG = 60
AUTO_SPIKE_DURACION_SEG  = 30

FALLBACK_SUBESTACIONES = [
    {"id": "SSS001", "distrito": "San Salvador",      "capacidad": 5000},
    {"id": "SSS002", "distrito": "San Salvador",      "capacidad": 4500},
    {"id": "SAN001", "distrito": "Antiguo Cuscatlan", "capacidad": 3000},
    {"id": "STC001", "distrito": "Santa Tecla",       "capacidad": 3500},
    {"id": "SAL001", "distrito": "Soyapango",         "capacidad": 4000},
]

subestaciones = list(FALLBACK_SUBESTACIONES)
subestaciones_lock = threading.Lock()

simulator_state = {
    "running":               True,
    "peak_hour_active":      False,
    "overload_districts":    set(),
    "stopped_substations":   set(),
    "burst_multiplier":      1,
    "redistribution_factors": {},
    "redistribution_pairs":  {},
    "auto_spike_sub":        None,   # subestación con spike automático activo
    "auto_spike_until":      0,      # timestamp hasta el que dura el spike
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("simulator")


# ── Hora virtual ───────────────────────────────────────────────────────────────

def get_hora_virtual() -> float:
    """
    Ciclo de 24 horas virtuales cada 12 minutos reales.
    30 segundos reales = 1 hora virtual.
    Minuto 6 real → hora 12 virtual (mediodía / HORA PICO).
    """
    segundos_en_ciclo = time.time() % CICLO_VIRTUAL_SEG
    return (segundos_en_ciclo / CICLO_VIRTUAL_SEG) * 24


def minuto_en_ciclo() -> float:
    """Minuto actual dentro del ciclo de 12 minutos (0-12)."""
    return (time.time() % CICLO_VIRTUAL_SEG) / 60


def es_hora_pico_virtual(hora: float) -> bool:
    """Hora pico virtual: 11h-13h (centrado en el minuto 6 del ciclo real)."""
    return 11 <= hora <= 13


# ── Consumo ────────────────────────────────────────────────────────────────────

def calcular_consumo(capacidad: float, hora: float, distrito: str = None) -> float:
    """
    Calcula consumo según la hora virtual:
    - Hora pico (11-13 h virtual / minuto ~6 real): 88-98 %  ← PICO AUTOMÁTICO
    - Mañana    (6-9  h virtual / minuto ~3 real):  70-85 %
    - Nocturno  (resto):                             30-65 %
    Respeta redistribución si está activa para el distrito.
    """
    if distrito and distrito in simulator_state["redistribution_factors"]:
        factor = simulator_state["redistribution_factors"][distrito]
        factor += random.uniform(-0.03, 0.03)
        return round(capacidad * max(0.20, min(factor, 0.90)), 2)

    if es_hora_pico_virtual(hora):
        factor = random.uniform(0.88, 0.98)
    elif 6 <= hora <= 9:
        factor = random.uniform(0.70, 0.85)
    else:
        factor = random.uniform(0.30, 0.65)

    return round(capacidad * factor, 2)


def inyectar_sobrecarga(sub: dict) -> float:
    """Spike de sobrecarga: 96-100 % de capacidad."""
    return round(sub["capacidad"] * random.uniform(0.96, 1.00), 2)


# ── Envío de métricas ──────────────────────────────────────────────────────────

def enviar_metrica(sub: dict, consumo: float) -> bool:
    payload = {
        "substation_id": sub["id"],
        "district_id":   sub["distrito"],
        "consumo_kw":    consumo,
        "capacidad_kw":  sub["capacidad"],
        "timestamp":     datetime.utcnow().isoformat(),
    }
    try:
        resp = requests.post(f"{BACKEND_URL}/api/metrics", json=payload, timeout=5)
        if resp.status_code != 200:
            logger.warning(f"Status {resp.status_code} para {sub['id']}")
        return True
    except Exception as e:
        logger.error(f"Error enviando {sub['id']}: {e}")
        return False


# ── Loop principal ─────────────────────────────────────────────────────────────

def loop_simulador():
    logger.info(f"Simulador iniciado → {BACKEND_URL} cada {INTERVAL_MS} ms")
    logger.info(f"Ciclo virtual: {CICLO_VIRTUAL_SEG}s reales = 24h virtuales | Pico en minuto 12")

    while simulator_state["running"]:
        hora   = get_hora_virtual()
        minuto = minuto_en_ciclo()
        ahora  = time.time()

        # Spike automático: limpiar si expiró
        if (simulator_state["auto_spike_sub"]
                and ahora > simulator_state["auto_spike_until"]):
            sub_expirado = simulator_state["auto_spike_sub"]
            simulator_state["auto_spike_sub"] = None
            logger.info(f"[AUTO-SPIKE] Spike automático finalizado en {sub_expirado}")

        interval = (INTERVAL_MS / 1000) / simulator_state["burst_multiplier"]

        with subestaciones_lock:
            current = list(subestaciones)

        for sub in current:
            if sub["id"] in simulator_state["stopped_substations"]:
                continue

            en_spike_auto = (sub["id"] == simulator_state["auto_spike_sub"]
                             and ahora <= simulator_state["auto_spike_until"])

            if sub["distrito"] in simulator_state["redistribution_factors"]:
                consumo = calcular_consumo(sub["capacidad"], hora, sub["distrito"])
            elif sub["distrito"] in simulator_state["overload_districts"] or en_spike_auto:
                consumo = inyectar_sobrecarga(sub)
                if en_spike_auto:
                    logger.info(f"[AUTO-SPIKE] {sub['id']} ({sub['distrito']}): {consumo} kW"
                                f" | min {minuto:.1f}/12 | hora virtual {hora:.1f}")
                else:
                    logger.info(f"[OVERLOAD] {sub['id']} ({sub['distrito']}): {consumo} kW")
            else:
                consumo = calcular_consumo(sub["capacidad"], hora, sub["distrito"])
                if es_hora_pico_virtual(hora):
                    logger.info(f"[HORA-PICO] {sub['id']}: {consumo} kW"
                                f" | min {minuto:.1f}/12 | hora virtual {hora:.1f}")

            enviar_metrica(sub, consumo)

        time.sleep(interval)


# ── Spike automático cada 60 segundos ─────────────────────────────────────────

def loop_auto_spike():
    """Cada AUTO_SPIKE_INTERVAL_SEG segundos inyecta un spike en una subestación aleatoria."""
    time.sleep(AUTO_SPIKE_INTERVAL_SEG)   # esperar el primer ciclo antes de empezar
    while simulator_state["running"]:
        with subestaciones_lock:
            activas = [s for s in subestaciones
                       if s["id"] not in simulator_state["stopped_substations"]]
        if activas:
            sub_elegida = random.choice(activas)
            simulator_state["auto_spike_sub"]   = sub_elegida["id"]
            simulator_state["auto_spike_until"] = time.time() + AUTO_SPIKE_DURACION_SEG
            logger.info(f"[AUTO-SPIKE] Spike iniciado en {sub_elegida['id']}"
                        f" ({sub_elegida['distrito']}) durante {AUTO_SPIKE_DURACION_SEG}s")
        time.sleep(AUTO_SPIKE_INTERVAL_SEG)


# ── Actualización de subestaciones desde backend ───────────────────────────────

def fetch_subestaciones():
    global subestaciones
    try:
        resp = requests.get(f"{BACKEND_URL}/api/simulator/districts", timeout=5)
        if resp.status_code != 200:
            return
        data = resp.json()
        nuevas = []
        for d in data:
            for s in d.get("substations", []):
                nuevas.append({
                    "id":       s["id"],
                    "distrito": d["district_id"],
                    "capacidad": s["capacidad_kw"],
                })
        if nuevas:
            with subestaciones_lock:
                subestaciones = nuevas
            logger.info(f"Subestaciones actualizadas: {len(nuevas)}")
    except Exception as e:
        logger.warning(f"No se pudo obtener subestaciones: {e}")


def refresh_subestaciones_loop():
    while simulator_state["running"]:
        fetch_subestaciones()
        time.sleep(15)


# ── FastAPI ────────────────────────────────────────────────────────────────────

app = FastAPI(title="EnergyGrid Simulator Control")


@app.get("/health")
async def health():
    hora   = get_hora_virtual()
    minuto = minuto_en_ciclo()
    return {
        "status":              "healthy",
        "simulator_running":   simulator_state["running"],
        "peak_hour_active":    es_hora_pico_virtual(hora),
        "hora_virtual":        round(hora, 2),
        "minuto_en_ciclo":     round(minuto, 2),
        "ciclo_total_min":     24,
        "interval_ms":         INTERVAL_MS,
        "overload_districts":  list(simulator_state["overload_districts"]),
        "stopped_substations": list(simulator_state["stopped_substations"]),
        "auto_spike_sub":      simulator_state["auto_spike_sub"],
        "auto_spike_segundos_restantes": max(
            0, round(simulator_state["auto_spike_until"] - time.time())
        ) if simulator_state["auto_spike_sub"] else 0,
    }


@app.get("/simulator/tiempo-virtual")
async def tiempo_virtual():
    hora   = get_hora_virtual()
    minuto = minuto_en_ciclo()
    return {
        "minuto_real_en_ciclo":  round(minuto, 2),
        "hora_virtual":          round(hora, 2),
        "es_hora_pico":          es_hora_pico_virtual(hora),
        "descripcion": (
            "HORA PICO (alta demanda)" if es_hora_pico_virtual(hora)
            else "Mañana (demanda media)" if 6 <= hora <= 9
            else "Periodo normal (baja demanda)"
        ),
        "proximo_pico_en_seg": round(
            ((11 - hora) % 24) * SEGUNDOS_POR_HORA_VIRTUAL
        ) if not es_hora_pico_virtual(hora) else 0,
    }


@app.post("/simulator/trigger-overload")
async def trigger_overload(district: str = Query(...)):
    with subestaciones_lock:
        distritos_validos = {s["distrito"] for s in subestaciones}
    if district not in distritos_validos:
        return JSONResponse(status_code=400,
            content={"error": f"Distrito no válido. Válidos: {list(distritos_validos)}"})
    simulator_state["overload_districts"].add(district)
    logger.info(f"[TRIGGER] Sobrecarga activada: {district}")
    return {"event": "OVERLOAD_TRIGGERED", "district": district,
            "message": f"Sobrecarga inyectada en {district} (96-100%)"}


@app.post("/simulator/stop-overload")
async def stop_overload(district: str = Query(...)):
    simulator_state["overload_districts"].discard(district)
    logger.info(f"[STOP] Sobrecarga detenida: {district}")
    return {"event": "OVERLOAD_STOPPED", "district": district}


@app.post("/simulator/trigger-peak-hour")
async def trigger_peak_hour():
    simulator_state["peak_hour_active"] = True
    simulator_state["burst_multiplier"] = 3
    logger.info("[TRIGGER] Hora pico manual activada. Burst 3x")
    return {"event": "PEAK_HOUR_TRIGGERED",
            "message": "Hora pico manual activada (3x frecuencia)",
            "burst_multiplier": 3}


@app.post("/simulator/stop-peak-hour")
async def stop_peak_hour():
    simulator_state["peak_hour_active"] = False
    simulator_state["burst_multiplier"] = 1
    logger.info("[STOP] Hora pico manual detenida")
    return {"event": "PEAK_HOUR_STOPPED", "burst_multiplier": 1}


@app.post("/simulator/stop-substation")
async def stop_substation(substation_id: str = Query(...)):
    with subestaciones_lock:
        validas = {s["id"] for s in subestaciones}
    if substation_id not in validas:
        return JSONResponse(status_code=400,
            content={"error": f"Subestación no válida. Válidas: {list(validas)}"})
    simulator_state["stopped_substations"].add(substation_id)
    logger.info(f"[TRIGGER] Subestación detenida: {substation_id}")
    return {"event": "SUBSTATION_STOPPED", "substation_id": substation_id}


@app.post("/simulator/start-substation")
async def start_substation(substation_id: str = Query(...)):
    simulator_state["stopped_substations"].discard(substation_id)
    logger.info(f"[START] Subestación reiniciada: {substation_id}")
    return {"event": "SUBSTATION_STARTED", "substation_id": substation_id}


@app.post("/simulator/malicious-input")
async def malicious_input():
    payload = {
        "substation_id": "TEST001",
        "district_id":   "'; DROP TABLE consumo_temporal; --",
        "consumo_kw":    1000,
        "capacidad_kw":  5000,
        "timestamp":     datetime.utcnow().isoformat(),
    }
    logger.warning("[SECURITY TEST] Enviando SQL injection payload")
    try:
        resp = requests.post(f"{BACKEND_URL}/api/metrics", json=payload, timeout=5)
        return {"event": "MALICIOUS_INPUT_SENT", "payload_sent": payload,
                "backend_response_code": resp.status_code,
                "backend_response": resp.text[:200]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/simulator/invalid-timestamp")
async def invalid_timestamp(offset_days: int = Query(2)):
    invalid_ts = datetime.utcnow() - timedelta(days=offset_days)
    payload = {
        "substation_id": "TEST002",
        "district_id":   "San Salvador",
        "consumo_kw":    1000,
        "capacidad_kw":  5000,
        "timestamp":     invalid_ts.isoformat(),
    }
    logger.warning(f"[TEST] Timestamp inválido: {invalid_ts.isoformat()}")
    try:
        resp = requests.post(f"{BACKEND_URL}/api/metrics", json=payload, timeout=5)
        return {"event": "INVALID_TIMESTAMP_SENT", "payload_sent": payload,
                "backend_response_code": resp.status_code,
                "backend_response": resp.text[:200]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/simulator/set-redistribution")
async def set_redistribution(
    district: str = Query(...),
    to: str = Query(None),
    factor: float = Query(0.55),
    increase_factor: float = Query(0.85),
):
    with subestaciones_lock:
        distritos_validos = {s["distrito"] for s in subestaciones}
    if district not in distritos_validos:
        return JSONResponse(status_code=400,
            content={"error": f"Distrito no válido. Válidos: {list(distritos_validos)}"})
    simulator_state["overload_districts"].discard(district)
    factor = max(0.20, min(factor, 0.90))
    simulator_state["redistribution_factors"][district] = factor
    if to and to in distritos_validos and to != district:
        simulator_state["redistribution_factors"][to] = max(0.50, min(increase_factor, 0.95))
        simulator_state["redistribution_pairs"][district] = to
    return {"event": "REDISTRIBUTION_SET", "district": district,
            "factor": factor, "to": to}


@app.post("/simulator/clear-redistribution")
async def clear_redistribution(district: str = Query(...)):
    target = simulator_state["redistribution_pairs"].pop(district, None)
    if target:
        simulator_state["redistribution_factors"].pop(target, None)
    simulator_state["redistribution_factors"].pop(district, None)
    return {"event": "REDISTRIBUTION_CLEARED", "district": district,
            "cleared_target": target}


@app.post("/simulator/reset")
async def reset_simulator():
    simulator_state["overload_districts"].clear()
    simulator_state["stopped_substations"].clear()
    simulator_state["peak_hour_active"]   = False
    simulator_state["burst_multiplier"]   = 1
    simulator_state["redistribution_factors"].clear()
    simulator_state["redistribution_pairs"].clear()
    simulator_state["auto_spike_sub"]     = None
    simulator_state["auto_spike_until"]   = 0
    logger.info("[RESET] Simulador resetado")
    return {"event": "SIMULATOR_RESET", "message": "Simulador resetado a estado normal"}


# ── Arranque ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    for attempt in range(10):
        fetch_subestaciones()
        with subestaciones_lock:
            count = len(subestaciones)
        if count > 3:
            break
        time.sleep(3)

    threading.Thread(target=refresh_subestaciones_loop, daemon=True).start()
    threading.Thread(target=loop_simulador,             daemon=True).start()
    threading.Thread(target=loop_auto_spike,            daemon=True).start()

    logger.info(f"Servidor iniciado en :8001 | Intervalo={INTERVAL_MS}ms"
                f" | Ciclo virtual=24min | Pico=min12 | Auto-spike cada {AUTO_SPIKE_INTERVAL_SEG}s")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
