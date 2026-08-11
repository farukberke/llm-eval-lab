from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    question: str
    expected_answer: str
    reference_source: str | None
    created_at: datetime
