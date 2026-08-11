from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EvaluationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    response_id: int
    metric_name: str
    score: float
    details: dict[str, Any] | None
    created_at: datetime
