from datetime import datetime

from pydantic import BaseModel, ConfigDict

from llm_eval_lab.models import RunStatus
from llm_eval_lab.schemas.evaluation_result import EvaluationResultRead
from llm_eval_lab.schemas.response import ResponseRead


class ExperimentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    status: RunStatus
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ResponseWithEvaluations(ResponseRead):
    evaluation_results: list[EvaluationResultRead]


class ExperimentRunDetail(ExperimentRunRead):
    responses: list[ResponseWithEvaluations]
