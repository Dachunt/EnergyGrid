"""
EnergyGrid Backend - Flask Application
Sistema integral de monitoreo de energía
"""
import os
import logging
from pathlib import Path
from flask import Flask, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicializar extensiones
db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("energygrid")


def create_app(config_name="development"):
    """Factory pattern para crear la aplicación Flask"""
    app = Flask(__name__)
    
    # Configuración
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://energygrid_user:S3cur3P@ss2026@localhost:5432/energygrid_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True
    
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'energygrid-jwt-secret-2026-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 horas
    
    # Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)
    CORS(app)
    
    # Registrar blueprints (rutas)
    from app.routes import auth_bp, metrics_bp, districts_bp, demo_bp, monitoring_bp, admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(districts_bp)
    app.register_blueprint(demo_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(admin_bp)
    
    # Rutas de salud
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok"}), 200
    
    @app.route('/', methods=['GET'])
    def root():
        """Serve the monitoring dashboard"""
        dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
        if dashboard_path.exists():
            return send_file(str(dashboard_path))
        return jsonify({"message": "Dashboard not found"}), 404
    
    @app.route('/dashboard', methods=['GET'])
    def dashboard():
        """Serve the monitoring dashboard at /dashboard"""
        dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
        if dashboard_path.exists():
            return send_file(str(dashboard_path))
        return jsonify({"message": "Dashboard not found"}), 404
    
    # Manejo de errores global
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    # Contexto de aplicación
    with app.app_context():
        # Crear tablas si no existen
        db.create_all()
        
        # Seed data
        from app.services.seeder import seed_database
        seed_database()
        
        logger.info("Application initialized successfully!")
    
    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)
