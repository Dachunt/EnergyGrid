from datetime import datetime
from pydantic import BaseModel


class MetricPayload(BaseModel):
    substation_id: str
    district_id: str
    consumo_kw: float
    capacidad_kw: float
    timestamp: datetime | None = None
