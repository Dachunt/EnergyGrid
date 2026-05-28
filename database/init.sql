CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ==================== NUEVAS TABLAS ====================

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(100),
    rol VARCHAR(20) DEFAULT 'admin',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sesiones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    refresh_token VARCHAR(255),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS distritos (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    latitud NUMERIC(10,6),
    longitud NUMERIC(10,6),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO distritos (id, nombre, latitud, longitud, descripcion) VALUES
  ('San Salvador',       'San Salvador',       13.6929, -89.2182, 'Distrito capital y centro financiero'),
  ('Antiguo Cuscatlan',  'Antiguo Cuscatlán',  13.7114, -89.2964, 'Distrito comercial y empresarial'),
  ('Santa Tecla',        'Santa Tecla',        13.6816, -89.2833, 'Distrito residencial y comercial'),
  ('Soyapango',          'Soyapango',          13.6667, -89.1833, 'Distrito industrial y populoso')
ON CONFLICT (id) DO NOTHING;

-- ==================== TABLAS EXISTENTES ====================

CREATE TABLE IF NOT EXISTS consumo_temporal (
    id              SERIAL PRIMARY KEY,
    district_id     VARCHAR(50) NOT NULL,
    substation_id   VARCHAR(50) NOT NULL,
    consumo_kw      NUMERIC(10, 2) NOT NULL,
    capacidad_kw    NUMERIC(10, 2) NOT NULL,
    porcentaje_uso  NUMERIC(5, 2) GENERATED ALWAYS AS
                    (consumo_kw / capacidad_kw * 100) STORED,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anomalia        BOOLEAN DEFAULT FALSE,
    notas           TEXT
);

CREATE INDEX IF NOT EXISTS idx_district_time
    ON consumo_temporal (district_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS alertas (
    id              SERIAL PRIMARY KEY,
    district_id     VARCHAR(50) NOT NULL,
    tipo_alerta     VARCHAR(100) NOT NULL,
    descripcion     TEXT,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resuelta        BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS subestaciones (
    id              VARCHAR(50) PRIMARY KEY,
    nombre          VARCHAR(100),
    distrito        VARCHAR(50),
    capacidad_kw    NUMERIC(10, 2),
    activa          BOOLEAN DEFAULT TRUE,
    latitud         NUMERIC(10, 6),
    longitud        NUMERIC(10, 6)
);

-- ==================== FOREIGN KEYS ====================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_subestaciones_distrito') THEN
        ALTER TABLE subestaciones ADD CONSTRAINT fk_subestaciones_distrito
            FOREIGN KEY (distrito) REFERENCES distritos(id);
    END IF;
END $$;

-- ==================== SEED DATA ====================

INSERT INTO subestaciones (id, nombre, distrito, capacidad_kw, latitud, longitud)
VALUES
  ('SSS001', 'Subestación Centro',    'San Salvador',      5000.00, 13.6929, -89.2182),
  ('SSS002', 'Subestación Norte',     'San Salvador',      4500.00, 13.7000, -89.2000),
  ('SAN001', 'Subestación Antiguo',   'Antiguo Cuscatlan', 3000.00, 13.7114, -89.2964),
  ('STC001', 'Subestación Santa Tecla', 'Santa Tecla',     3500.00, 13.6816, -89.2833),
  ('SAL001', 'Subestación Soyapango', 'Soyapango',         4000.00, 13.6667, -89.1833)
ON CONFLICT (id) DO NOTHING;

INSERT INTO usuarios (username, email, password_hash, nombre_completo, rol)
VALUES (
  'admin',
  'admin@energygrid.com',
  crypt('Admin123!', gen_salt('bf')),
  'Administrador del Sistema',
  'admin'
) ON CONFLICT (username) DO NOTHING;
