"""
Rutas de Métricas - Flask
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from app.main import db
from app.models import ConsumoTemporal, Subestacion, Distrito
from app.services.alert_engine import analizar_metrica

logger = logging.getLogger("energygrid")
metrics_bp = Blueprint('metrics', __name__, url_prefix='/api')

_SUSPICIOUS_PATTERN = re.compile(r"[;'\"]|--")


@metrics_bp.route('/metrics', methods=['POST'])
def receive_metric():
    """Recibir métrica de consumo de energía"""
    data = request.get_json()
    
    # Validar campos requeridos
    if not data or not data.get('substation_id') or not data.get('distrito_id'):
        return jsonify({"error": "substation_id y distrito_id son requeridos"}), 400
    
    consumo_kw = data.get('consumo_kw')
    capacidad_kw = data.get('capacidad_kw')
    
    # Validar valores
    if not consumo_kw or not capacidad_kw or consumo_kw <= 0 or capacidad_kw <= 0:
        return jsonify({"error": "valores inválidos para consumo_kw y capacidad_kw"}), 422
    
    # Validar timestamp
    now = datetime.now(timezone.utc)
    ts = data.get('timestamp')
    
    if ts:
        try:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                ts = datetime.fromtimestamp(ts, tz=timezone.utc)
        except:
            return jsonify({"error": "timestamp inválido"}), 422
    else:
        ts = now
    
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    
    # Validar que el timestamp esté dentro de rango
    if ts < now - timedelta(hours=24) or ts > now + timedelta(hours=24):
        logger.warning(f"Timestamp fuera de rango: {ts}")
        return jsonify({"error": "timestamp fuera de rango"}), 422
    
    # Detectar anomalías (SQL injection)
    anomalia = False
    notas = None
    if _SUSPICIOUS_PATTERN.search(data.get('distrito_id', '')) or _SUSPICIOUS_PATTERN.search(data.get('substation_id', '')):
        anomalia = True
        notas = "sospecha_sql"
    
    try:
        # Calcular porcentaje de uso
        porcentaje = (consumo_kw / capacidad_kw) * 100
        
        # Guardar en base de datos
        consumo = ConsumoTemporal(
            subestacion_id=data['substation_id'],
            distrito_id=data['distrito_id'],
            consumo_kw=consumo_kw,
            capacidad_kw=capacidad_kw,
            timestamp=ts
        )
        db.session.add(consumo)
        db.session.commit()
        
        # Ejecutar análisis de métrica
        metrica_data = {
            "distrito_id": data['distrito_id'],
            "subestacion_id": data['substation_id'],
            "consumo_kw": consumo_kw,
            "capacidad_kw": capacidad_kw,
            "timestamp": ts.isoformat(),
            "porcentaje_uso": porcentaje,
        }
        
        # Llamar al motor de alertas (sin await en Flask)
        try:
            analizar_metrica(metrica_data)
        except Exception as e:
            logger.error(f"Error en análisis de métrica: {e}")
        
        logger.info(f"Métrica recibida: {data['substation_id']} - {porcentaje:.2f}%")
        
        return jsonify({
            "status": "ok",
            "id": consumo.id,
            "porcentaje_uso": round(porcentaje, 2)
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al guardar métrica: {e}")
        return jsonify({"error": "Error al guardar la métrica"}), 500
