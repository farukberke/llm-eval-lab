from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ModelConfigCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    provider: str
    model_name: str
    parameters: dict[str, Any] | None = None


class ModelConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    name: str
    provider: str
    model_name: str
    parameters: dict[str, Any] | None
    created_at: datetime
