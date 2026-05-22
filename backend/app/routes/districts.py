from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api", tags=["districts"])


@router.get("/districts")
async def get_districts(request: Request):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (district_id)
                district_id,
                substation_id,
                consumo_kw::float8 AS consumo_kw,
                capacidad_kw::float8 AS capacidad_kw,
                porcentaje_uso::float8 AS porcentaje_uso,
                timestamp
            FROM consumo_temporal
            ORDER BY district_id, timestamp DESC
            """
        )
    return [dict(row) for row in rows]


@router.get("/districts/{district_id}/history")
async def get_district_history(district_id: str, request: Request, limit: int = 100):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                district_id,
                substation_id,
                consumo_kw::float8 AS consumo_kw,
                capacidad_kw::float8 AS capacidad_kw,
                porcentaje_uso::float8 AS porcentaje_uso,
                timestamp
            FROM consumo_temporal
            WHERE district_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            district_id,
            limit,
        )
    return [dict(row) for row in rows]


@router.get("/alerts")
async def get_alerts(request: Request, resolved: bool = False):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                district_id,
                tipo_alerta,
                descripcion,
                timestamp,
                resuelta
            FROM alertas
            WHERE resuelta = $1
            ORDER BY timestamp DESC
            """,
            resolved,
        )
    return [dict(row) for row in rows]


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, request: Request):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE alertas
            SET resuelta = TRUE
            WHERE id = $1
            RETURNING id, district_id, tipo_alerta, descripcion, timestamp, resuelta
            """,
            alert_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="alerta no encontrada")
    return dict(row)
