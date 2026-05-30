import os
import httpx
import logging
from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger("energygrid")

router = APIRouter(prefix="/api/demo", tags=["demo"])

SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://localhost:8001")


@router.post("/simulator/{path:path}")
async def proxy_simulator(path: str, request: Request):
    """Proxy genérico para endpoints del simulador"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            params = dict(request.query_params)
            resp = await client.post(f"{SIMULATOR_URL}/simulator/{path}", params=params)
            try:
                body = resp.json()
            except Exception:
                body = {"text": resp.text}
            return {
                "status_code": resp.status_code,
                "simulator_status": "ok" if resp.is_success else "error",
                "response": body,
            }
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Simulador no accesible")
