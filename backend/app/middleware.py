from fastapi import Request, HTTPException, Depends
from app.auth import decode_token


async def require_auth(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado - Token requerido")

    token = auth_header.split(" ")[1]
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inv�lido o expirado")

    pool = getattr(request.app.state, "db", None)
    if not pool:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """SELECT id, username, email, nombre_completo, rol, activo
               FROM usuarios WHERE id = $1 AND activo = TRUE""",
            int(payload["sub"])
        )
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    return dict(user)
