"""
Rutas de Autenticación - Flask
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.main import db
from app.models import Usuario
from app.auth import verify_password, get_password_hash

logger = logging.getLogger("energygrid")
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Endpoint de login"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Username y password son requeridos"}), 400
    
    user = Usuario.query.filter_by(username=data['username']).first()
    
    if not user:
        logger.warning(f"Login failed: usuario no encontrado - {data['username']}")
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401
    
    if not user.activo:
        logger.warning(f"Login failed: usuario inactivo - {data['username']}")
        return jsonify({"error": "Usuario inactivo"}), 401
    
    if not verify_password(data['password'], user.password_hash):
        logger.warning(f"Login failed: contraseña incorrecta - {data['username']}")
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401
    
    access_token = create_access_token(identity=str(user.id))
    
    logger.info(f"Login exitoso: {user.username}")
    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """Endpoint de registro"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Username y password son requeridos"}), 400
    
    if len(data['username']) < 3 or len(data['username']) > 50:
        return jsonify({"error": "Username debe tener entre 3 y 50 caracteres"}), 400
    
    if len(data['password']) < 6:
        return jsonify({"error": "Password debe tener al menos 6 caracteres"}), 400
    
    # Verificar si usuario ya existe
    existing = Usuario.query.filter_by(username=data['username']).first()
    if existing:
        return jsonify({"error": "El usuario ya existe"}), 400
    
    email = data.get('email', f"{data['username']}@energygrid.com")
    nombre_completo = data.get('nombre_completo', data['username'])
    
    try:
        new_user = Usuario(
            username=data['username'],
            email=email,
            password_hash=get_password_hash(data['password']),
            nombre_completo=nombre_completo,
            rol='user',
            activo=True
        )
        db.session.add(new_user)
        db.session.commit()
        
        access_token = create_access_token(identity=str(new_user.id))
        
        logger.info(f"Registro exitoso: {new_user.username}")
        return jsonify({
            "access_token": access_token,
            "token_type": "bearer",
            "user": new_user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en registro: {e}")
        return jsonify({"error": "Error al crear el usuario"}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """Obtener información del usuario autenticado"""
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    return jsonify(user.to_dict()), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout del usuario"""
    return jsonify({"message": "Sesión cerrada correctamente"}), 200


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Cambiar contraseña del usuario"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({"error": "current_password y new_password son requeridos"}), 400
    
    if len(data['new_password']) < 6:
        return jsonify({"error": "Nueva contraseña debe tener al menos 6 caracteres"}), 400
    
    user = Usuario.query.get(int(user_id))
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    if not verify_password(data['current_password'], user.password_hash):
        return jsonify({"error": "Contraseña actual incorrecta"}), 400
    
    try:
        user.password_hash = get_password_hash(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Contraseña cambiada: {user.username}")
        return jsonify({"message": "Contraseña cambiada correctamente"}), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al cambiar contraseña: {e}")
        return jsonify({"error": "Error al cambiar la contraseña"}), 500
