import logging
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Optional

from app.auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.middleware import require_auth

logger = logging.getLogger("energygrid")
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)
    nombre_completo: Optional[str] = ""

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(data: LoginRequest, request: Request):
    pool = request.app.state.db
    if not pool:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, email, password_hash, nombre_completo, rol, activo "
            "FROM usuarios WHERE username = $1",
            data.username
        )
        if not user:
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        if not user["activo"]:
            raise HTTPException(status_code=401, detail="Usuario inactivo")
        if not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

        access_token = create_access_token({"sub": str(user["id"]), "username": user["username"]})

        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        await conn.execute(
            "INSERT INTO sesiones (usuario_id, token_hash, expires_at) VALUES ($1, $2, $3)",
            user["id"], access_token[-50:], expires_at
        )

    logger.info("Login exitoso", extra={"username": data.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "nombre_completo": user["nombre_completo"],
            "rol": user["rol"],
        },
    }


@router.post("/register")
async def register(data: RegisterRequest, request: Request):
    pool = request.app.state.db
    if not pool:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    email_val = data.email if data.email else f"{data.username}@energygrid.com"
    nombre_val = data.nombre_completo if data.nombre_completo else data.username

    hashed = get_password_hash(data.password)

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM usuarios WHERE username = $1 OR email = $2",
            data.username, email_val
        )
        if existing:
            raise HTTPException(status_code=400, detail="El usuario o email ya existe")

        user = await conn.fetchrow(
            "INSERT INTO usuarios (username, email, password_hash, nombre_completo) "
            "VALUES ($1, $2, $3, $4) RETURNING id, username, email, nombre_completo, rol",
            data.username, email_val, hashed, nombre_val
        )

        access_token = create_access_token({"sub": str(user["id"]), "username": user["username"]})

        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        await conn.execute(
            "INSERT INTO sesiones (usuario_id, token_hash, expires_at) VALUES ($1, $2, $3)",
            user["id"], access_token[-50:], expires_at
        )

    logger.info("Registro exitoso", extra={"username": data.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": dict(user),
    }


@router.get("/me")
async def get_me(user: dict = Depends(require_auth)):
    return user


@router.post("/logout")
async def logout(request: Request, user: dict = Depends(require_auth)):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    pool = request.app.state.db
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM sesiones WHERE token_hash = $1 AND usuario_id = $2",
                token[-50:], user["id"]
            )
    return {"message": "Sesión cerrada correctamente"}


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, request: Request, user: dict = Depends(require_auth)):
    pool = request.app.state.db
    if not pool:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    async with pool.acquire() as conn:
        current = await conn.fetchval(
            "SELECT password_hash FROM usuarios WHERE id = $1", user["id"]
        )
        if not verify_password(data.current_password, current):
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

        new_hash = get_password_hash(data.new_password)
        await conn.execute(
            "UPDATE usuarios SET password_hash = $1, updated_at = NOW() WHERE id = $2",
            new_hash, user["id"]
        )

        await conn.execute(
            "DELETE FROM sesiones WHERE usuario_id = $1", user["id"]
        )

    return {"message": "Contraseña cambiada correctamente"}
