from datetime import datetime

from pydantic import BaseModel, ConfigDict

from llm_eval_lab.schemas.test_case import TestCaseRead


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None


class DatasetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class DatasetWithTestCases(DatasetRead):
    test_cases: list[TestCaseRead]
