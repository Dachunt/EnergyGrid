from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["metrics"])


@router.post("/metrics")
async def receive_metric():
    pass
