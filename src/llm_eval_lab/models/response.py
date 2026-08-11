from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_eval_lab.db import Base

if TYPE_CHECKING:
    from llm_eval_lab.models.evaluation_result import EvaluationResult
    from llm_eval_lab.models.experiment_run import ExperimentRun
    from llm_eval_lab.models.test_case import TestCase


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (
        UniqueConstraint("experiment_run_id", "test_case_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_run_id: Mapped[int] = mapped_column(ForeignKey("experiment_runs.id"))
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"))
    response_text: Mapped[str | None]
    latency_ms: Mapped[float | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    experiment_run: Mapped["ExperimentRun"] = relationship(back_populates="responses")
    test_case: Mapped["TestCase"] = relationship()
    evaluation_results: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )
