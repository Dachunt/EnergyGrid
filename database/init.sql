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
    activa          BOOLEAN DEFAULT TRUE
);

INSERT INTO subestaciones (id, nombre, distrito, capacidad_kw)
VALUES
  ('SSS001', 'Subestación Centro',    'San Salvador',      5000.00),
  ('SSS002', 'Subestación Norte',     'San Salvador',      4500.00),
  ('SAN001', 'Subestación Antiguo',   'Antiguo Cuscatlán', 3000.00),
  ('STC001', 'Subestación Santa Tecla', 'Santa Tecla',     3500.00),
  ('SAL001', 'Subestación Soyapango', 'Soyapango',         4000.00)
ON CONFLICT (id) DO NOTHING;
