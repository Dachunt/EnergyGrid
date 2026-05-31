"""
Seeder de datos iniciales - Flask
"""
import logging
from app.main import db
from app.models import Usuario, Distrito, Subestacion
from app.auth import get_password_hash

logger = logging.getLogger("energygrid")


def seed_database():
    """Crear datos iniciales en la base de datos"""
    try:
        # Crear usuario admin si no existe
        admin_exists = Usuario.query.filter_by(username='admin').first()
        if not admin_exists:
            admin = Usuario(
                username='admin',
                email='admin@energygrid.com',
                password_hash=get_password_hash('Admin123!'),
                nombre_completo='Administrador del Sistema',
                rol='admin',
                activo=True
            )
            db.session.add(admin)
            logger.info("Usuario admin creado (admin / Admin123!)")
        else:
            logger.info("Usuario admin ya existe")
        
        # Crear distritos si no existen
        districts_exist = Distrito.query.count()
        if districts_exist == 0:
            districts = [
                Distrito(
                    id='San Salvador',
                    nombre='San Salvador',
                    latitud=13.6929,
                    longitud=-89.2182,
                    descripcion='Distrito capital y centro financiero'
                ),
                Distrito(
                    id='Antiguo Cuscatlan',
                    nombre='Antiguo Cuscatlán',
                    latitud=13.7114,
                    longitud=-89.2964,
                    descripcion='Distrito comercial y empresarial'
                ),
                Distrito(
                    id='Santa Tecla',
                    nombre='Santa Tecla',
                    latitud=13.6816,
                    longitud=-89.2833,
                    descripcion='Distrito residencial y comercial'
                ),
                Distrito(
                    id='Soyapango',
                    nombre='Soyapango',
                    latitud=13.6667,
                    longitud=-89.1833,
                    descripcion='Distrito industrial y populoso'
                )
            ]
            for dist in districts:
                db.session.add(dist)
            db.session.commit()
            logger.info("Distritos creados")
        else:
            logger.info("Distritos ya existen")
        
        # Crear subestaciones si no existen
        subs_exist = Subestacion.query.count()
        if subs_exist == 0:
            substations = [
                Subestacion(
                    id='SSS001',
                    nombre='Subestación Centro',
                    distrito='San Salvador',
                    capacidad_kw=5000.00,
                    latitud=13.6929,
                    longitud=-89.2182,
                    estado='activa'
                ),
                Subestacion(
                    id='SSS002',
                    nombre='Subestación Norte',
                    distrito='San Salvador',
                    capacidad_kw=4500.00,
                    latitud=13.7000,
                    longitud=-89.2000,
                    estado='activa'
                ),
                Subestacion(
                    id='SAN001',
                    nombre='Subestación Antiguo',
                    distrito='Antiguo Cuscatlan',
                    capacidad_kw=3000.00,
                    latitud=13.7114,
                    longitud=-89.2964,
                    estado='activa'
                ),
                Subestacion(
                    id='STC001',
                    nombre='Subestación Santa Tecla',
                    distrito='Santa Tecla',
                    capacidad_kw=3500.00,
                    latitud=13.6816,
                    longitud=-89.2833,
                    estado='activa'
                ),
                Subestacion(
                    id='SAL001',
                    nombre='Subestación Soyapango',
                    distrito='Soyapango',
                    capacidad_kw=4000.00,
                    latitud=13.6667,
                    longitud=-89.1833,
                    estado='activa'
                )
            ]
            for sub in substations:
                db.session.add(sub)
            db.session.commit()
            logger.info("Subestaciones creadas")
        else:
            logger.info("Subestaciones ya existen")
        
        logger.info("Seed data completado")
    
    except Exception as e:
        logger.error(f"Error en seed: {e}")
        db.session.rollback()
