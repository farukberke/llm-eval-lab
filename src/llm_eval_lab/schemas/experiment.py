from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    dataset_id: int
    model_config_id: int
    prompt_id: int
    description: str | None = None


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    name: str
    description: str | None
    dataset_id: int
    model_config_id: int
    prompt_id: int
    created_at: datetime
