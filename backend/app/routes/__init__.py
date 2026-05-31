"""
Blueprints (Rutas) de la aplicación Flask
"""
from app.routes.auth import auth_bp
from app.routes.metrics import metrics_bp
from app.routes.districts import districts_bp
from app.routes.demo import demo_bp
from app.routes.monitoring import monitoring_bp
from app.routes.admin import admin_bp

__all__ = ['auth_bp', 'metrics_bp', 'districts_bp', 'demo_bp', 'monitoring_bp', 'admin_bp']
