"""
Ejemplo de integración del sistema de monitoreo en rutas de API
Este archivo muestra cómo registrar queries y usar el monitoreo
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.main import app
from app.services.db_query_monitor import (
    execute_query_monitored,
    DatabaseQueryMonitor,
    monitored_query,
)

router = APIRouter(prefix="/api/example", tags=["example"])


# Obtener instancia de monitoring
def get_monitoring():
    """Obtiene instancia global del monitoreo"""
    from app.routes.monitoring import get_monitoring_instance
    return get_monitoring_instance()


# ============== EJEMPLO 1: Usar execute_query_monitored ==============


async def get_consumption_monitored(district_id: int, monitoring=Depends(get_monitoring)):
    """Ejemplo usando execute_query_monitored"""
    try:
        pool = app.state.db
        
        query = """
            SELECT id, district_id, consumption, timestamp 
            FROM consumption 
            WHERE district_id = $1 
            ORDER BY timestamp DESC 
            LIMIT 100
        """
        
        # La query se registra automáticamente con su tiempo de ejecución
        result = await execute_query_monitored(
            query,
            district_id,
            pool=pool,
            query_type="SELECT"
        )
        
        return {
            "count": len(result),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== EJEMPLO 2: Usar DatabaseQueryMonitor context manager ==============


async def get_districts_monitored(monitoring=Depends(get_monitoring)):
    """Ejemplo usando context manager"""
    try:
        pool = app.state.db
        
        query = "SELECT * FROM districts ORDER BY name"
        
        async with DatabaseQueryMonitor(query, pool=pool, query_type="SELECT"):
            result = await pool.fetch(query)
        
        return {
            "count": len(result),
            "districts": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== EJEMPLO 3: Usar decorador @monitored_query ==============


@monitored_query(query_type="SELECT")
async def get_alerts_monitored(monitoring=Depends(get_monitoring)):
    """Ejemplo usando decorador"""
    try:
        pool = app.state.db
        query = "SELECT * FROM alerts WHERE resolved = false LIMIT 50"
        result = await pool.fetch(query)
        return {"alerts": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== EJEMPLO 4: Query lenta deliberada (para testing) ==============


async def simulate_slow_query(duration_ms: float = Query(2000, ge=100, le=10000)):
    """Simula una query lenta para testing"""
    import time
    
    pool = app.state.db
    monitoring = get_monitoring()
    
    try:
        # Query que se ejecutará lentamente
        query = """
            SELECT pg_sleep($1), * FROM consumption LIMIT 1
        """
        
        seconds = duration_ms / 1000.0
        
        start = time.time()
        await pool.fetchval(f"SELECT pg_sleep({seconds})")
        elapsed_ms = (time.time() - start) * 1000
        
        # Registrar manualmente
        monitoring.log_database_query(
            query=f"Slow query simulation ({duration_ms}ms)",
            execution_time_ms=elapsed_ms,
            status="success"
        )
        
        return {
            "status": "ok",
            "simulated_duration_ms": duration_ms,
            "actual_duration_ms": round(elapsed_ms, 2),
            "recorded": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Registrar rutas de ejemplo ==============


router.get("/consumption/{district_id}")(get_consumption_monitored)
router.get("/districts")(get_districts_monitored)
router.get("/alerts")(get_alerts_monitored)
router.post("/simulate-slow-query")(simulate_slow_query)


# ============== Helper para integración automática en otras rutas ==============


def add_query_monitoring_to_existing_routes():
    """
    Integra monitoreo automático a rutas existentes
    Coloca esto en main.py para auto-registrar todas las queries
    """
    import time
    
    # Este código envolvería las funciones de ruta
    # para capturar automáticamente queries lentas
    pass


# ============== TESTING ==============


if __name__ == "__main__":
    """
    Para testear desde línea de comandos:
    
    1. Obtener métricas:
       curl http://localhost:8000/api/monitoring/munin/metrics
    
    2. Obtener queries lentas:
       curl http://localhost:8000/api/monitoring/queries/slow
    
    3. Simular query lenta:
       curl -X POST http://localhost:8000/api/example/simulate-slow-query?duration_ms=3000
    
    4. Ver cuellos de botella:
       curl http://localhost:8000/api/monitoring/queries/bottlenecks
    
    5. Obtener dashboard completo:
       curl http://localhost:8000/api/monitoring/dashboard
    """
    pass
