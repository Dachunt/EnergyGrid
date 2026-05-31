"""
Rutas de Distritos - Flask
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.main import db
from app.models import Distrito, Subestacion, ConsumoTemporal
from sqlalchemy import func, desc

logger = logging.getLogger("energygrid")
districts_bp = Blueprint('districts', __name__, url_prefix='/api')


@districts_bp.route('/districts', methods=['GET'])
def get_districts():
    """Obtener todos los distritos con información de subestaciones"""
    try:
        # Obtener todos los distritos
        districts = Distrito.query.all()
        result = []
        
        for district in districts:
            # Obtener última métrica de cada subestación en el distrito
            substation_data = []
            for sub in district.subestaciones:
                # Obtener último consumo
                last_consumption = ConsumoTemporal.query.filter_by(
                    subestacion_id=sub.id
                ).order_by(desc(ConsumoTemporal.timestamp)).first()
                
                sub_info = {
                    "substation_id": sub.id,
                    "nombre": sub.nombre,
                    "latitud": sub.latitud,
                    "longitud": sub.longitud,
                    "capacidad_kw": sub.capacidad_kw,
                    "estado": sub.estado,
                    "consumo_kw": last_consumption.consumo_kw if last_consumption else 0,
                    "porcentaje_uso": (last_consumption.consumo_kw / sub.capacidad_kw * 100) if last_consumption and sub.capacidad_kw > 0 else 0
                }
                substation_data.append(sub_info)
            
            # Calcular totales del distrito
            total_consumo = sum(s["consumo_kw"] for s in substation_data)
            total_capacidad = sum(s["capacidad_kw"] for s in substation_data)
            porcentaje_total = (total_consumo / total_capacidad * 100) if total_capacidad > 0 else 0
            
            district_info = {
                "district_id": district.id,
                "nombre": district.nombre,
                "descripcion": district.descripcion,
                "latitud": district.latitud,
                "longitud": district.longitud,
                "consumo_kw": round(total_consumo, 2),
                "capacidad_kw": round(total_capacidad, 2),
                "porcentaje_uso": round(porcentaje_total, 2),
                "subestaciones": substation_data
            }
            result.append(district_info)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error al obtener distritos: {e}")
        return jsonify({"error": "Error al obtener distritos"}), 500


@districts_bp.route('/districts/<district_id>', methods=['GET'])
def get_district(district_id):
    """Obtener un distrito específico"""
    try:
        district = Distrito.query.get(district_id)
        if not district:
            return jsonify({"error": "Distrito no encontrado"}), 404
        
        # Obtener información detallada de subestaciones
        substation_data = []
        for sub in district.subestaciones:
            last_consumption = ConsumoTemporal.query.filter_by(
                subestacion_id=sub.id
            ).order_by(desc(ConsumoTemporal.timestamp)).first()
            
            sub_info = sub.to_dict()
            if last_consumption:
                sub_info["consumo_kw"] = last_consumption.consumo_kw
                sub_info["porcentaje_uso"] = (last_consumption.consumo_kw / sub.capacidad_kw * 100)
            else:
                sub_info["consumo_kw"] = 0
                sub_info["porcentaje_uso"] = 0
            
            substation_data.append(sub_info)
        
        district_info = district.to_dict()
        district_info["subestaciones"] = substation_data
        
        return jsonify(district_info), 200
    
    except Exception as e:
        logger.error(f"Error al obtener distrito: {e}")
        return jsonify({"error": "Error al obtener el distrito"}), 500


@districts_bp.route('/districts', methods=['POST'])
@jwt_required()
def create_district():
    """Crear un nuevo distrito"""
    data = request.get_json()
    
    if not data or not data.get('id') or not data.get('nombre'):
        return jsonify({"error": "id y nombre son requeridos"}), 400
    
    # Verificar que el distrito no exista
    existing = Distrito.query.get(data['id'])
    if existing:
        return jsonify({"error": "El distrito ya existe"}), 400
    
    try:
        new_district = Distrito(
            id=data['id'],
            nombre=data['nombre'],
            latitud=data.get('latitud', 0),
            longitud=data.get('longitud', 0),
            descripcion=data.get('descripcion', '')
        )
        db.session.add(new_district)
        db.session.commit()
        
        logger.info(f"Nuevo distrito creado: {new_district.id}")
        return jsonify(new_district.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear distrito: {e}")
        return jsonify({"error": "Error al crear el distrito"}), 500


@districts_bp.route('/districts/<district_id>', methods=['PUT'])
@jwt_required()
def update_district(district_id):
    """Actualizar un distrito"""
    district = Distrito.query.get(district_id)
    if not district:
        return jsonify({"error": "Distrito no encontrado"}), 404
    
    data = request.get_json()
    
    try:
        if 'nombre' in data:
            district.nombre = data['nombre']
        if 'descripcion' in data:
            district.descripcion = data['descripcion']
        if 'latitud' in data:
            district.latitud = data['latitud']
        if 'longitud' in data:
            district.longitud = data['longitud']
        
        db.session.commit()
        logger.info(f"Distrito actualizado: {district_id}")
        return jsonify(district.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar distrito: {e}")
        return jsonify({"error": "Error al actualizar el distrito"}), 500


@districts_bp.route('/districts/<district_id>', methods=['DELETE'])
@jwt_required()
def delete_district(district_id):
    """Eliminar un distrito"""
    district = Distrito.query.get(district_id)
    if not district:
        return jsonify({"error": "Distrito no encontrado"}), 404
    
    try:
        db.session.delete(district)
        db.session.commit()
        logger.info(f"Distrito eliminado: {district_id}")
        return jsonify({"message": "Distrito eliminado correctamente"}), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al eliminar distrito: {e}")
        return jsonify({"error": "Error al eliminar el distrito"}), 500
