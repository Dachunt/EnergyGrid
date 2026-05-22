from datetime import datetime
from pydantic import BaseModel, Field


class MetricPayload(BaseModel):
    substation_id: str = Field(min_length=1, max_length=50)
    district_id: str = Field(min_length=1, max_length=50)
    consumo_kw: float
    capacidad_kw: float
    timestamp: datetime | None = None
