from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["districts"])


@router.get("/districts")
async def get_districts():
    pass


@router.get("/districts/{district_id}/history")
async def get_district_history(district_id: str, limit: int = 100):
    pass


@router.get("/alerts")
async def get_alerts(resolved: bool = False):
    pass


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    pass
