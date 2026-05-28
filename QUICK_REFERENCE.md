# Quick Reference: Sistema de Monitoreo EnergyGrid

## Iniciar

```bash
cd backend
python -m uvicorn app.main:app --reload
```

## Endpoints Principales

```bash
# Dashboard
curl http://localhost:8000/api/monitoring/dashboard | jq

# Health
curl http://localhost:8000/api/monitoring/health | jq

# Alertas críticas
curl "http://localhost:8000/api/monitoring/alerts?severity=critical" | jq

# Queries lentas
curl http://localhost:8000/api/monitoring/queries/slow | jq

# Cuellos de botella
curl http://localhost:8000/api/monitoring/queries/bottlenecks | jq

# Uptime último día
curl "http://localhost:8000/api/monitoring/pingdom/uptime?hours=24" | jq

# Estado de endpoints
curl http://localhost:8000/api/monitoring/pingdom/status | jq
```

## Las 3 Herramientas

### Munin (50+ métricas)
- CPU, memoria, disco, red, procesos
- Health score 0-100
- Endpoint: `/api/monitoring/munin/metrics`

### Pingdom (Disponibilidad)
- Verifica endpoints cada minuto
- Tiempos de respuesta
- Endpoint: `/api/monitoring/pingdom/status`

### Slow Query Log (Performance BD)
- Queries lentas > 500ms
- Cuellos de botella
- Endpoint: `/api/monitoring/queries/slow`

## Validar Instalación

```bash
python validate_monitoring.py
```

## Documentación

- Rápido (5 min): `MONITORING_QUICK_START.md`
- Completo (30 min): `INTEGRATION_GUIDE_COMPLETE.md`
- Ejecutivo: `MONITORING_INTEGRATION_COMPLETE.md`

## Logs

```bash
# Ver en tiempo real
tail -f backend/logs/energygrid.log
```

## Dependencias

```bash
# Instalar
pip install -r backend/requirements.txt

# Verificar
python -c "import fastapi, asyncpg, psutil; print('[OK]')"
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Puerto 8000 en uso | `--port 8001` |
| Módulo no encontrado | `pip install -r requirements.txt` |
| Base de datos no conecta | Verifica conexión PostgreSQL |
| Logs no se crean | Directorio se crea automáticamente |

## Versiones Instaladas

- fastapi: 0.136.3
- uvicorn: 0.48.0
- asyncpg: 0.31.0
- psutil: 7.2.2
- httpx: 0.28.1

## Commits Realizados

1. `feat: Integracion completa del sistema de monitoreo` - Agregó las 3 herramientas
2. `fix: Resolver error de psycopg2-binary en Windows` - Cambió a asyncpg
3. `fix: Resolver conflictos de dependencias` - Versiones flexibles

---

**Status**: ✅ LISTO PARA USAR
