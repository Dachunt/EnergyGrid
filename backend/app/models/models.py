"""
SQLAlchemy Models para EnergyGrid
"""
from datetime import datetime
from app.main import db


class Usuario(db.Model):
    """Modelo de usuario del sistema"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='user', nullable=False)  # admin o user
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nombre_completo': self.nombre_completo,
            'rol': self.rol,
            'activo': self.activo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Distrito(db.Model):
    """Modelo de distrito"""
    __tablename__ = 'distritos'
    
    id = db.Column(db.String(50), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    latitud = db.Column(db.Float, nullable=False)
    longitud = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    subestaciones = db.relationship('Subestacion', backref='distrito', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'latitud': self.latitud,
            'longitud': self.longitud,
            'descripcion': self.descripcion,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Subestacion(db.Model):
    """Modelo de subestación"""
    __tablename__ = 'subestaciones'
    
    id = db.Column(db.String(50), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    distrito = db.Column(db.String(50), db.ForeignKey('distritos.id'), nullable=False, index=True)
    capacidad_kw = db.Column(db.Float, nullable=False)
    latitud = db.Column(db.Float, nullable=False)
    longitud = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), default='activa', nullable=False)  # activa, inactiva
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    consumos = db.relationship('ConsumoTemporal', backref='subestacion', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'distrito': self.distrito,
            'capacidad_kw': self.capacidad_kw,
            'latitud': self.latitud,
            'longitud': self.longitud,
            'estado': self.estado,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ConsumoTemporal(db.Model):
    """Modelo de consumo temporal (métricas)"""
    __tablename__ = 'consumo_temporal'
    
    id = db.Column(db.Integer, primary_key=True)
    subestacion_id = db.Column(db.String(50), db.ForeignKey('subestaciones.id'), nullable=False, index=True)
    distrito_id = db.Column(db.String(50), db.ForeignKey('distritos.id'), nullable=False, index=True)
    consumo_kw = db.Column(db.Float, nullable=False)
    capacidad_kw = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relación con distrito (para las queries que lo necesitan)
    _distrito = db.relationship('Distrito', backref='consumos', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subestacion_id': self.subestacion_id,
            'distrito_id': self.distrito_id,
            'consumo_kw': self.consumo_kw,
            'capacidad_kw': self.capacidad_kw,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class Alerta(db.Model):
    """Modelo de alerta del sistema"""
    __tablename__ = 'alertas'
    
    id = db.Column(db.Integer, primary_key=True)
    subestacion_id = db.Column(db.String(50), db.ForeignKey('subestaciones.id'), nullable=False, index=True)
    tipo = db.Column(db.String(50), nullable=False)  # sobrecarga, pico, caida, etc
    mensaje = db.Column(db.Text, nullable=False)
    severidad = db.Column(db.String(20), default='info', nullable=False)  # info, warning, critical
    resuelta = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subestacion_id': self.subestacion_id,
            'tipo': self.tipo,
            'mensaje': self.mensaje,
            'severidad': self.severidad,
            'resuelta': self.resuelta,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }
