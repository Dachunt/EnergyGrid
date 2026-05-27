"""
Database Query Monitor Helper
Integra Slow Query Log con operaciones de base de datos
"""

import time
from functools import wraps
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger("energygrid")

# Variable global para acceder al orquestador
_monitoring_orchestrator: Optional[Any] = None


def set_monitoring_orchestrator(orchestrator: Any):
    """Establece la instancia global del orquestador de monitoreo"""
    global _monitoring_orchestrator
    _monitoring_orchestrator = orchestrator


def get_monitoring_orchestrator() -> Optional[Any]:
    """Obtiene la instancia del orquestador"""
    return _monitoring_orchestrator


async def execute_query_monitored(
    query: str,
    *args,
    pool: Any = None,
    query_type: str = "SELECT",
    **kwargs
) -> Any:
    """
    Ejecuta una query con monitoreo automático de tiempo

    Args:
        query: Query SQL
        pool: Connection pool de asyncpg
        query_type: Tipo de query (SELECT, INSERT, UPDATE, DELETE)
        *args: Argumentos para la query
        **kwargs: Otros parámetros

    Returns:
        Resultado de la query
    """
    if pool is None:
        raise ValueError("Pool is required")

    start_time = time.time()
    result = None
    status = "success"
    error = None
    rows_affected = 0

    try:
        # Ejecutar query
        if query.strip().upper().startswith("SELECT"):
            result = await pool.fetch(query, *args)
            rows_affected = len(result)
        elif query.strip().upper().startswith("INSERT"):
            result = await pool.execute(query, *args)
            rows_affected = int(result.split()[-1]) if result else 0
        elif query.strip().upper().startswith("UPDATE"):
            result = await pool.execute(query, *args)
            rows_affected = int(result.split()[-1]) if result else 0
        elif query.strip().upper().startswith("DELETE"):
            result = await pool.execute(query, *args)
            rows_affected = int(result.split()[-1]) if result else 0
        else:
            result = await pool.execute(query, *args)

    except Exception as e:
        status = "error"
        error = str(e)
        raise
    finally:
        # Registrar en monitoreo
        execution_time_ms = (time.time() - start_time) * 1000

        monitor = get_monitoring_orchestrator()
        if monitor:
            try:
                monitor.log_database_query(
                    query=query,
                    execution_time_ms=execution_time_ms,
                    status=status,
                    rows_affected=rows_affected,
                    error=error,
                )
            except Exception as e:
                logger.error(f"Error logging query to monitoring: {e}")

    return result


class DatabaseQueryMonitor:
    """Context manager para monitorear queries"""

    def __init__(
        self,
        query: str,
        pool: Any = None,
        query_type: str = "SELECT",
    ):
        self.query = query
        self.pool = pool
        self.query_type = query_type
        self.start_time = None
        self.execution_time_ms = 0

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.execution_time_ms = (time.time() - self.start_time) * 1000

        monitor = get_monitoring_orchestrator()
        if monitor and self.pool:
            try:
                status = "error" if exc_type else "success"
                error = str(exc_val) if exc_val else None

                monitor.log_database_query(
                    query=self.query,
                    execution_time_ms=self.execution_time_ms,
                    status=status,
                    error=error,
                )
            except Exception as e:
                logger.error(f"Error logging query: {e}")


def monitored_query(query_type: str = "SELECT"):
    """Decorador para monitorear métodos que ejecutan queries"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = None
            status = "success"
            error = None

            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                status = "error"
                error = str(e)
                raise
            finally:
                execution_time_ms = (time.time() - start_time) * 1000

                # Intentar obtener query del resultado si está disponible
                query = getattr(result, "_query", f"{func.__name__} - {query_type}")

                monitor = get_monitoring_orchestrator()
                if monitor:
                    try:
                        monitor.log_database_query(
                            query=query,
                            execution_time_ms=execution_time_ms,
                            status=status,
                            error=error,
                        )
                    except Exception as e:
                        logger.error(f"Error logging monitored query: {e}")

            return result

        return wrapper

    return decorator
