import os
import time
import random
import math
import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
INTERVAL_MS = int(os.environ.get("INTERVAL_MS", 1000))

SUBESTACIONES = [
    {"id": "SSS001", "distrito": "San Salvador",      "capacidad": 5000},
    {"id": "SSS002", "distrito": "San Salvador",      "capacidad": 4500},
    {"id": "SAN001", "distrito": "Antiguo Cuscatlán", "capacidad": 3000},
    {"id": "STC001", "distrito": "Santa Tecla",       "capacidad": 3500},
    {"id": "SAL001", "distrito": "Soyapango",         "capacidad": 4000},
]

# Estado global del simulador
simulator_state = {
    "running": True,
    "peak_hour_active": False,
    "overload_districts": set(),
    "stopped_substations": set(),
    "burst_multiplier": 1,  # 1 = normal, 2+ = burst mode
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simulator")


def get_hora_virtual():
    """Ciclo de 24 horas virtuales cada 24 minutos reales"""
    segundos = time.time() % (24 * 60)
    return segundos / 60


def calcular_consumo(capacidad, hora):
    """Calcula consumo con variación horaria"""
    if 18 <= hora <= 21:
        factor = random.uniform(0.88, 0.98)
    elif 6 <= hora <= 9:
        factor = random.uniform(0.70, 0.85)
    else:
        factor = random.uniform(0.30, 0.65)
    return round(capacidad * factor, 2)


def inyectar_sobrecarga(subestacion):
    """Inyecta sobrecarga en una subestación (96-105% capacidad)"""
    return round(subestacion["capacidad"] * random.uniform(0.96, 1.05), 2)


def enviar_metrica(sub, consumo):
    """Envía métrica al backend"""
    payload = {
        "substation_id": sub["id"],
        "district_id":   sub["distrito"],
        "consumo_kw":    consumo,
        "capacidad_kw":  sub["capacidad"],
        "timestamp":     datetime.utcnow().isoformat(),
    }
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/metrics", 
            json=payload, 
            timeout=5
        )
        if resp.status_code != 200:
            logger.warning(f"Status {resp.status_code} para {sub['id']}")
        return True
    except Exception as e:
        logger.error(f"Error enviando datos de {sub['id']}: {e}")
        return False


def loop_simulador():
    """Loop principal del simulador que envía datos"""
    logger.info(f"Simulador iniciado. Enviando a {BACKEND_URL} cada {INTERVAL_MS}ms")
    
    while simulator_state["running"]:
        hora = get_hora_virtual()
        
        # Si está en peak hour, aumentar frecuencia (burst)
        interval = INTERVAL_MS / simulator_state["burst_multiplier"]
        
        for sub in SUBESTACIONES:
            # Saltar subestaciones detenidas
            if sub["id"] in simulator_state["stopped_substations"]:
                continue
            
            # Calcular consumo
            if sub["distrito"] in simulator_state["overload_districts"]:
                consumo = inyectar_sobrecarga(sub)
                logger.info(f"[OVERLOAD] {sub['id']} ({sub['distrito']}): {consumo} kW")
            else:
                consumo = calcular_consumo(sub["capacidad"], hora)
            
            # Enviar métrica
            enviar_metrica(sub, consumo)
        
        time.sleep(interval / 1000)


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="EnergyGrid Simulator Control")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "simulator_running": simulator_state["running"],
        "peak_hour_active": simulator_state["peak_hour_active"],
        "overload_districts": list(simulator_state["overload_districts"]),
        "stopped_substations": list(simulator_state["stopped_substations"]),
    }


@app.post("/simulator/trigger-overload")
async def trigger_overload(district: str = Query(..., description="Nombre del distrito")):
    """
    Fuerza sobrecarga (>95% capacidad) en un distrito específico
    
    Ejemplo: POST /simulator/trigger-overload?district=San Salvador
    """
    distritos_validos = {sub["distrito"] for sub in SUBESTACIONES}
    
    if district not in distritos_validos:
        return JSONResponse(
            status_code=400,
            content={"error": f"Distrito no válido. Válidos: {list(distritos_validos)}"}
        )
    
    simulator_state["overload_districts"].add(district)
    logger.info(f"[TRIGGER] Sobrecarga activada para: {district}")
    
    return {
        "event": "OVERLOAD_TRIGGERED",
        "district": district,
        "message": f"Sobrecarga inyectada en {district}. Consumo forzado a 96-105%"
    }


@app.post("/simulator/stop-overload")
async def stop_overload(district: str = Query(..., description="Nombre del distrito")):
    """Detiene la sobrecarga en un distrito"""
    simulator_state["overload_districts"].discard(district)
    logger.info(f"[STOP] Sobrecarga detenida para: {district}")
    
    return {
        "event": "OVERLOAD_STOPPED",
        "district": district,
        "message": f"Sobrecarga detenida en {district}"
    }


@app.post("/simulator/trigger-peak-hour")
async def trigger_peak_hour():
    """
    Activa 'hora pico' - aumenta frecuencia de datos (burst mode)
    
    Ejemplo: POST /simulator/trigger-peak-hour
    """
    simulator_state["peak_hour_active"] = True
    simulator_state["burst_multiplier"] = 3  # Envía 3x más rápido
    
    logger.info("[TRIGGER] Hora pico activada. Burst mode: 3x")
    
    return {
        "event": "PEAK_HOUR_TRIGGERED",
        "message": "Hora pico activada. Frecuencia de datos aumentada a 3x",
        "burst_multiplier": simulator_state["burst_multiplier"]
    }


@app.post("/simulator/stop-peak-hour")
async def stop_peak_hour():
    """Detiene el modo de hora pico"""
    simulator_state["peak_hour_active"] = False
    simulator_state["burst_multiplier"] = 1
    
    logger.info("[STOP] Hora pico detenida")
    
    return {
        "event": "PEAK_HOUR_STOPPED",
        "message": "Hora pico detenida. Frecuencia normal",
        "burst_multiplier": simulator_state["burst_multiplier"]
    }


@app.post("/simulator/stop-substation")
async def stop_substation(substation_id: str = Query(..., description="ID de subestación")):
    """
    Detiene una subestación (simula fallo/caída)
    Deja de enviar datos de esa subestación
    
    Ejemplo: POST /simulator/stop-substation?substation_id=SSS001
    """
    subestaciones_validas = {sub["id"] for sub in SUBESTACIONES}
    
    if substation_id not in subestaciones_validas:
        return JSONResponse(
            status_code=400,
            content={"error": f"Subestación no válida. Válidas: {list(subestaciones_validas)}"}
        )
    
    simulator_state["stopped_substations"].add(substation_id)
    logger.info(f"[TRIGGER] Subestación detenida: {substation_id}")
    
    return {
        "event": "SUBSTATION_STOPPED",
        "substation_id": substation_id,
        "message": f"Subestación {substation_id} detenida. Dejará de enviar datos"
    }


@app.post("/simulator/start-substation")
async def start_substation(substation_id: str = Query(..., description="ID de subestación")):
    """Reinicia una subestación detenida"""
    simulator_state["stopped_substations"].discard(substation_id)
    logger.info(f"[START] Subestación reiniciada: {substation_id}")
    
    return {
        "event": "SUBSTATION_STARTED",
        "substation_id": substation_id,
        "message": f"Subestación {substation_id} reiniciada"
    }


@app.post("/simulator/malicious-input")
async def malicious_input(district: str = Query("San Salvador")):
    """
    Envía input malicioso con SQL injection payload
    Prueba que el backend protege contra SQL injection
    
    Ejemplo: POST /simulator/malicious-input
    """
    malicious_district = "'; DROP TABLE consumo_temporal; --"
    
    logger.warning(f"[SECURITY TEST] Enviando SQL injection payload")
    
    payload = {
        "substation_id": "TEST001",
        "district_id": malicious_district,
        "consumo_kw": 1000,
        "capacidad_kw": 5000,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/metrics",
            json=payload,
            timeout=5
        )
        
        return {
            "event": "MALICIOUS_INPUT_SENT",
            "payload_sent": payload,
            "backend_response_code": resp.status_code,
            "backend_response": resp.text[:200],
            "message": "SQL injection payload enviado. Backend debe rechazarlo."
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "No se pudo enviar el payload",
                "details": str(e)
            }
        )


@app.post("/simulator/invalid-timestamp")
async def invalid_timestamp(offset_days: int = Query(1)):
    """
    Envía timestamp inválido (futuro o pasado)
    Prueba validación de timestamps en el backend
    
    Ejemplo: POST /simulator/invalid-timestamp?offset_days=1
    """
    offset = timedelta(days=offset_days)
    invalid_ts = datetime.utcnow() - offset
    
    logger.warning(f"[TEST] Enviando timestamp inválido: {invalid_ts.isoformat()}")
    
    payload = {
        "substation_id": "TEST002",
        "district_id": "San Salvador",
        "consumo_kw": 1000,
        "capacidad_kw": 5000,
        "timestamp": invalid_ts.isoformat(),
    }
    
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/metrics",
            json=payload,
            timeout=5
        )
        
        return {
            "event": "INVALID_TIMESTAMP_SENT",
            "payload_sent": payload,
            "backend_response_code": resp.status_code,
            "backend_response": resp.text[:200],
            "message": f"Timestamp inválido ({offset_days} días) enviado. Backend debe rechazarlo con 422."
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "No se pudo enviar el payload",
                "details": str(e)
            }
        )


@app.post("/simulator/reset")
async def reset_simulator():
    """Resetea el simulador al estado normal"""
    simulator_state["overload_districts"].clear()
    simulator_state["stopped_substations"].clear()
    simulator_state["peak_hour_active"] = False
    simulator_state["burst_multiplier"] = 1
    
    logger.info("[RESET] Simulador resetado a estado normal")
    
    return {
        "event": "SIMULATOR_RESET",
        "message": "Simulador resetado a estado normal"
    }


# ============================================================================
# INICIO DEL SIMULADOR
# ============================================================================

if __name__ == "__main__":
    # Iniciar loop del simulador en un thread separado
    simulator_thread = threading.Thread(target=loop_simulador, daemon=True)
    simulator_thread.start()
    
    # Iniciar servidor FastAPI
    logger.info("Iniciando servidor FastAPI en puerto 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
