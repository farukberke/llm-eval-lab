from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptCreate(BaseModel):
    name: str
    template: str


class PromptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    template: str
    created_at: datetime
