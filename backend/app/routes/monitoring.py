"""
Rutas de Monitoreo - Flask
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.main import db
from app.models import ConsumoTemporal, Alerta, Subestacion
from sqlalchemy import desc, func

logger = logging.getLogger("energygrid")
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')


@monitoring_bp.route('/health', methods=['GET'])
def get_health():
    """Obtener estado de salud del sistema"""
    try:
        # Obtener últimas métricas
        latest = ConsumoTemporal.query.order_by(desc(ConsumoTemporal.timestamp)).first()
        
        # Contar alertas activas
        active_alerts = Alerta.query.filter_by(resuelta=False).count()
        
        # Calcular promedio de consumo
        last_hour = datetime.utcnow() - timedelta(hours=1)
        avg_consumption = db.session.query(func.avg(ConsumoTemporal.consumo_kw)).filter(
            ConsumoTemporal.timestamp >= last_hour
        ).scalar() or 0
        
        return jsonify({
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "active_alerts": active_alerts,
            "average_consumption_kw": round(avg_consumption, 2),
            "last_metric": latest.timestamp.isoformat() if latest else None
        }), 200
    
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@monitoring_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Obtener datos del dashboard"""
    try:
        # Obtener últimas métricas de cada subestación
        subqueries = db.session.query(
            ConsumoTemporal.subestacion_id,
            func.max(ConsumoTemporal.timestamp).label('latest_timestamp')
        ).group_by(ConsumoTemporal.subestacion_id).subquery()
        
        latest_metrics = db.session.query(ConsumoTemporal).join(
            subqueries,
            (ConsumoTemporal.subestacion_id == subqueries.c.subestacion_id) &
            (ConsumoTemporal.timestamp == subqueries.c.latest_timestamp)
        ).all()
        
        # Procesar datos
        metrics_data = []
        for metric in latest_metrics:
            sub = Subestacion.query.get(metric.subestacion_id)
            metrics_data.append({
                "subestacion_id": metric.subestacion_id,
                "subestacion_nombre": sub.nombre if sub else "Unknown",
                "consumo_kw": metric.consumo_kw,
                "capacidad_kw": metric.capacidad_kw,
                "porcentaje_uso": round((metric.consumo_kw / metric.capacidad_kw * 100), 2),
                "timestamp": metric.timestamp.isoformat()
            })
        
        # Alertas activas
        active_alerts = Alerta.query.filter_by(resuelta=False).all()
        alerts_data = [a.to_dict() for a in active_alerts]
        
        return jsonify({
            "metrics": metrics_data,
            "alerts": alerts_data,
            "total_substations": len(metrics_data),
            "active_alerts_count": len(alerts_data)
        }), 200
    
    except Exception as e:
        logger.error(f"Error en dashboard: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Obtener todas las alertas"""
    try:
        include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
        
        if include_resolved:
            alerts = Alerta.query.order_by(desc(Alerta.created_at)).all()
        else:
            alerts = Alerta.query.filter_by(resuelta=False).order_by(desc(Alerta.created_at)).all()
        
        return jsonify([a.to_dict() for a in alerts]), 200
    
    except Exception as e:
        logger.error(f"Error al obtener alertas: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_alert(alert_id):
    """Resolver una alerta"""
    try:
        alert = Alerta.query.get(alert_id)
        if not alert:
            return jsonify({"error": "Alerta no encontrada"}), 404
        
        alert.resuelta = True
        alert.resolved_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Alerta resuelta: {alert_id}")
        return jsonify(alert.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al resolver alerta: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_bp.route('/metrics/history', methods=['GET'])
def get_metrics_history():
    """Obtener historial de métricas"""
    try:
        hours = request.args.get('hours', 24, type=int)
        substation_id = request.args.get('substation_id')
        
        # Calcular fecha de inicio
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Construir query
        query = ConsumoTemporal.query.filter(ConsumoTemporal.timestamp >= start_time)
        
        if substation_id:
            query = query.filter_by(subestacion_id=substation_id)
        
        metrics = query.order_by(ConsumoTemporal.timestamp).all()
        
        return jsonify([m.to_dict() for m in metrics]), 200
    
    except Exception as e:
        logger.error(f"Error al obtener historial: {e}")
        return jsonify({"error": str(e)}), 500
