"""
Rutas de Demo - Flask
"""
import logging
import os
import requests
from flask import Blueprint, jsonify, request

logger = logging.getLogger("energygrid")

demo_bp = Blueprint('demo', __name__, url_prefix='/api/demo')

SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://localhost:8001")


@demo_bp.route('/simulator/health', methods=['GET'])
def proxy_simulator_health():
    """Estado del simulador (health check)"""
    try:
        resp = requests.get(f"{SIMULATOR_URL}/health", timeout=10)
        return resp.json(), resp.status_code
    except Exception as e:
        logger.error(f"Error conectando a simulador: {e}")
        return jsonify({"error": "Simulador no accesible"}), 502


@demo_bp.route('/simulator/tiempo-virtual', methods=['GET'])
def proxy_simulator_tiempo_virtual():
    """Tiempo virtual actual del simulador"""
    try:
        resp = requests.get(f"{SIMULATOR_URL}/simulator/tiempo-virtual", timeout=10)
        return resp.json(), resp.status_code
    except Exception as e:
        logger.error(f"Error conectando a simulador: {e}")
        return jsonify({"error": "Simulador no accesible"}), 502


@demo_bp.route('/metrics/sample', methods=['GET'])
def demo_metrics():
    """Endpoint de demo con métricas de ejemplo"""
    return jsonify({
        "substation_id": "SSS001",
        "distrito_id": "San Salvador",
        "consumo_kw": 2500,
        "capacidad_kw": 5000,
        "porcentaje_uso": 50.0,
        "timestamp": "2026-05-30T22:48:00Z"
    }), 200
