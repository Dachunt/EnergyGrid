import logging
import math
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException, Depends

from app.middleware import require_auth

logger = logging.getLogger("energygrid")
router = APIRouter(prefix="/api/admin", tags=["admin"])

PROXIMITY_KM = 5


async def check_substation_proximity(pool, lat: float, lng: float, exclude_id: str = None):
    if lat is None or lng is None:
        return
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, latitud::float8 AS latitud, longitud::float8 AS longitud FROM subestaciones "
            "WHERE latitud IS NOT NULL AND longitud IS NOT NULL AND id != COALESCE($1, '')",
            exclude_id or ""
        )
    for row in rows:
        dlat = math.radians(row["latitud"] - lat)
        dlng = math.radians(row["longitud"] - lng)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(row["latitud"])) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist = 6371 * c
        if dist < PROXIMITY_KM:
            raise HTTPException(
                status_code=400,
                detail=f"La subestación '{row['id']}' está a solo {dist:.1f} km de distancia "
                       f"(mínimo {PROXIMITY_KM} km permitido)"
            )


# ── Pydantic models ──────────────────────────────────────────────────────────

class DistrictCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = ""
    latitud: Optional[float] = None
    longitud: Optional[float] = None

class DistrictUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: Optional[bool] = None

class SubstationCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., max_length=100)
    distrito: str = Field(..., max_length=50)
    capacidad_kw: float = Field(..., gt=0)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activa: bool = True

class SubstationUpdate(BaseModel):
    nombre: Optional[str] = None
    distrito: Optional[str] = None
    capacidad_kw: Optional[float] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activa: Optional[bool] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DISTRITOS CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/districts")
async def list_districts(request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, nombre, descripcion, latitud::float8 AS latitud, longitud::float8 AS longitud, "
            "activo, created_at, updated_at FROM distritos ORDER BY nombre"
        )
    return [dict(row) for row in rows]


@router.get("/districts/{district_id}")
async def get_district(district_id: str, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, nombre, descripcion, latitud::float8 AS latitud, longitud::float8 AS longitud, "
            "activo, created_at, updated_at FROM distritos WHERE id = $1",
            district_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Distrito no encontrado")
    return dict(row)


@router.post("/districts")
async def create_district(data: DistrictCreate, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM distritos WHERE id = $1", data.id)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un distrito con ese ID")

        row = await conn.fetchrow(
            "INSERT INTO distritos (id, nombre, descripcion, latitud, longitud) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING *",
            data.id, data.nombre, data.descripcion, data.latitud, data.longitud
        )
    logger.info("Distrito creado", extra={"district_id": data.id, "user": user["username"]})
    return dict(row)


@router.put("/districts/{district_id}")
async def update_district(district_id: str, data: DistrictUpdate, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM distritos WHERE id = $1", district_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Distrito no encontrado")

        updates = {}
        for field in ["nombre", "descripcion", "latitud", "longitud", "activo"]:
            val = getattr(data, field, None)
            if val is not None:
                updates[field] = val

        if not updates:
            return dict(existing)

        set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates.keys()))
        set_clause += ", updated_at = NOW()"
        values = list(updates.values())
        values.append(district_id)

        row = await conn.fetchrow(
            f"UPDATE distritos SET {set_clause} WHERE id = ${len(values)} RETURNING *",
            *values
        )
    logger.info("Distrito actualizado", extra={"district_id": district_id, "user": user["username"]})
    return dict(row)


@router.delete("/districts/{district_id}")
async def delete_district(district_id: str, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id, activo FROM distritos WHERE id = $1", district_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Distrito no encontrado")

        if not existing["activo"]:
            raise HTTPException(status_code=400, detail="El distrito ya está inactivo")

        await conn.execute(
            "UPDATE distritos SET activo = FALSE, updated_at = NOW() WHERE id = $1",
            district_id
        )
    logger.info("Distrito desactivado", extra={"district_id": district_id, "user": user["username"]})
    return {"message": "Distrito desactivado correctamente"}


# ═══════════════════════════════════════════════════════════════════════════════
# SUBESTACIONES CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/substations")
async def list_substations(request: Request, user: dict = Depends(require_auth), distrito: str = None):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        if distrito:
            rows = await conn.fetch(
                "SELECT s.*, d.nombre AS distrito_nombre FROM subestaciones s "
                "LEFT JOIN distritos d ON s.distrito = d.id "
                "WHERE s.distrito = $1 ORDER BY s.id",
                distrito
            )
        else:
            rows = await conn.fetch(
                "SELECT s.*, d.nombre AS distrito_nombre FROM subestaciones s "
                "LEFT JOIN distritos d ON s.distrito = d.id ORDER BY s.id"
            )
    return [dict(row) for row in rows]


@router.get("/substations/{substation_id}")
async def get_substation(substation_id: str, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT s.*, d.nombre AS distrito_nombre FROM subestaciones s "
            "LEFT JOIN distritos d ON s.distrito = d.id WHERE s.id = $1",
            substation_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Subestación no encontrada")
    return dict(row)


@router.post("/substations")
async def create_substation(data: SubstationCreate, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db

    if data.latitud is not None and data.longitud is not None:
        await check_substation_proximity(pool, data.latitud, data.longitud)

    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM subestaciones WHERE id = $1", data.id)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe una subestación con ese ID")

        district_exists = await conn.fetchval("SELECT id FROM distritos WHERE id = $1 AND activo = TRUE", data.distrito)
        if not district_exists:
            raise HTTPException(status_code=400, detail="El distrito especificado no existe o está inactivo")

        row = await conn.fetchrow(
            "INSERT INTO subestaciones (id, nombre, distrito, capacidad_kw, latitud, longitud, activa) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *",
            data.id, data.nombre, data.distrito, data.capacidad_kw,
            data.latitud, data.longitud, data.activa
        )
    logger.info("Subestación creada", extra={"substation_id": data.id, "user": user["username"]})
    return dict(row)


@router.put("/substations/{substation_id}")
async def update_substation(substation_id: str, data: SubstationUpdate, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM subestaciones WHERE id = $1", substation_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Subestación no encontrada")

        if data.distrito is not None:
            district_exists = await conn.fetchval(
                "SELECT id FROM distritos WHERE id = $1 AND activo = TRUE", data.distrito
            )
            if not district_exists:
                raise HTTPException(status_code=400, detail="El distrito especificado no existe o está inactivo")

        updates = {}
        for field in ["nombre", "distrito", "capacidad_kw", "latitud", "longitud", "activa"]:
            val = getattr(data, field, None)
            if val is not None:
                updates[field] = val

        if not updates:
            return dict(existing)

        check_lat = updates.get("latitud", existing["latitud"])
        check_lng = updates.get("longitud", existing["longitud"])
        if check_lat is not None and check_lng is not None:
            await check_substation_proximity(pool, float(check_lat), float(check_lng), substation_id)

        set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates.keys()))
        values = list(updates.values())
        values.append(substation_id)

        row = await conn.fetchrow(
            f"UPDATE subestaciones SET {set_clause} WHERE id = ${len(values)} RETURNING *",
            *values
        )
    logger.info("Subestación actualizada", extra={"substation_id": substation_id, "user": user["username"]})
    return dict(row)


@router.delete("/substations/{substation_id}")
async def delete_substation(substation_id: str, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM subestaciones WHERE id = $1", substation_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Subestación no encontrada")

        await conn.execute("DELETE FROM consumo_temporal WHERE substation_id = $1", substation_id)
        await conn.execute("DELETE FROM subestaciones WHERE id = $1", substation_id)
    logger.info("Subestación eliminada", extra={"substation_id": substation_id, "user": user["username"]})
    return {"message": "Subestación eliminada correctamente"}


# ═══════════════════════════════════════════════════════════════════════════════
# USUARIOS (solo lectura para administradores)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/users")
async def list_users(request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, username, email, nombre_completo, rol, activo, created_at "
            "FROM usuarios ORDER BY id"
        )
    return [dict(row) for row in rows]
