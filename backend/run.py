#!/usr/bin/env python
"""
Script para ejecutar la aplicación Flask
"""
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app, socketio

if __name__ == '__main__':
    # Crear la aplicación
    app = create_app()
    
    # Determinar puerto y modo debug
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"\n{'='*60}")
    print(f"{'EnergyGrid Backend - Flask':^60}")
    print(f"{'='*60}")
    print(f"Starting server on http://0.0.0.0:{port}")
    print(f"Debug mode: {debug}")
    print(f"{'='*60}\n")
    
    # Ejecutar con socketio
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, use_reloader=debug)
