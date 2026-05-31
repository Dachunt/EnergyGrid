"""
Rutas de Admin - Flask
"""
import logging
import math
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.main import db
from app.models import Usuario, Distrito, Subestacion, Alerta

logger = logging.getLogger("energygrid")
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

PROXIMITY_KM = 5


def check_admin_role(user_id):
    """Verificar que el usuario es admin"""
    user = Usuario.query.get(int(user_id))
    if not user or user.rol != 'admin':
        return False
    return True


def check_substation_proximity(lat, lng, exclude_id=None):
    """Verificar que la nueva subestación no está muy cerca de otras"""
    if lat is None or lng is None:
        return True
    
    subs = Subestacion.query.all()
    for sub in subs:
        if exclude_id and sub.id == exclude_id:
            continue
        
        if sub.latitud is None or sub.longitud is None:
            continue
        
        # Haversine formula
        dlat = math.radians(sub.latitud - lat)
        dlng = math.radians(sub.longitud - lng)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(sub.latitud)) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist = 6371 * c
        
        if dist < PROXIMITY_KM:
            return False
    
    return True


@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """Listar todos los usuarios (solo admin)"""
    user_id = get_jwt_identity()
    if not check_admin_role(user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    try:
        users = Usuario.query.all()
        return jsonify([u.to_dict() for u in users]), 200
    except Exception as e:
        logger.error(f"Error al listar usuarios: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Obtener un usuario específico"""
    current_user_id = get_jwt_identity()
    if not check_admin_role(current_user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    try:
        user = Usuario.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify(user.to_dict()), 200
    except Exception as e:
        logger.error(f"Error al obtener usuario: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Actualizar un usuario"""
    current_user_id = get_jwt_identity()
    if not check_admin_role(current_user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    user = Usuario.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    data = request.get_json()
    
    try:
        if 'nombre_completo' in data:
            user.nombre_completo = data['nombre_completo']
        if 'email' in data:
            user.email = data['email']
        if 'rol' in data:
            user.rol = data['rol']
        if 'activo' in data:
            user.activo = data['activo']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Usuario actualizado: {user_id}")
        return jsonify(user.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar usuario: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/districts', methods=['GET'])
@jwt_required()
def list_districts():
    """Listar todos los distritos (admin)"""
    user_id = get_jwt_identity()
    if not check_admin_role(user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    try:
        districts = Distrito.query.all()
        return jsonify([d.to_dict() for d in districts]), 200
    except Exception as e:
        logger.error(f"Error al listar distritos: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/substations', methods=['GET'])
@jwt_required()
def list_substations():
    """Listar todas las subestaciones (admin)"""
    user_id = get_jwt_identity()
    if not check_admin_role(user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    try:
        subs = Subestacion.query.all()
        return jsonify([s.to_dict() for s in subs]), 200
    except Exception as e:
        logger.error(f"Error al listar subestaciones: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/substations', methods=['POST'])
@jwt_required()
def create_substation():
    """Crear nueva subestación (admin)"""
    user_id = get_jwt_identity()
    if not check_admin_role(user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    data = request.get_json()
    
    if not data or not data.get('id') or not data.get('nombre'):
        return jsonify({"error": "id y nombre son requeridos"}), 400
    
    # Verificar proximidad
    if not check_substation_proximity(data.get('latitud'), data.get('longitud')):
        return jsonify({"error": f"Subestación muy cerca de otra (mínimo {PROXIMITY_KM} km)"}), 400
    
    try:
        new_sub = Subestacion(
            id=data['id'],
            nombre=data['nombre'],
            distrito=data.get('distrito'),
            capacidad_kw=data.get('capacidad_kw', 0),
            latitud=data.get('latitud', 0),
            longitud=data.get('longitud', 0),
            estado=data.get('estado', 'activa')
        )
        db.session.add(new_sub)
        db.session.commit()
        
        logger.info(f"Subestación creada: {new_sub.id}")
        return jsonify(new_sub.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear subestación: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/substations/<sub_id>', methods=['PUT'])
@jwt_required()
def update_substation(sub_id):
    """Actualizar una subestación"""
    user_id = get_jwt_identity()
    if not check_admin_role(user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    sub = Subestacion.query.get(sub_id)
    if not sub:
        return jsonify({"error": "Subestación no encontrada"}), 404
    
    data = request.get_json()
    
    # Verificar proximidad si cambia ubicación
    if 'latitud' in data or 'longitud' in data:
        lat = data.get('latitud', sub.latitud)
        lng = data.get('longitud', sub.longitud)
        if not check_substation_proximity(lat, lng, exclude_id=sub_id):
            return jsonify({"error": f"Subestación muy cerca de otra (mínimo {PROXIMITY_KM} km)"}), 400
    
    try:
        if 'nombre' in data:
            sub.nombre = data['nombre']
        if 'distrito' in data:
            sub.distrito = data['distrito']
        if 'capacidad_kw' in data:
            sub.capacidad_kw = data['capacidad_kw']
        if 'latitud' in data:
            sub.latitud = data['latitud']
        if 'longitud' in data:
            sub.longitud = data['longitud']
        if 'estado' in data:
            sub.estado = data['estado']
        
        db.session.commit()
        logger.info(f"Subestación actualizada: {sub_id}")
        return jsonify(sub.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar subestación: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/alerts', methods=['GET'])
@jwt_required()
def list_alerts():
    """Listar todas las alertas"""
    user_id = get_jwt_identity()
    if not check_admin_role(user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    
    try:
        alerts = Alerta.query.order_by(Alerta.created_at.desc()).all()
        return jsonify([a.to_dict() for a in alerts]), 200
    except Exception as e:
        logger.error(f"Error al listar alertas: {e}")
        return jsonify({"error": str(e)}), 500
