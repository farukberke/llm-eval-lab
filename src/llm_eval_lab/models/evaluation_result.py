from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_eval_lab.db import Base

if TYPE_CHECKING:
    from llm_eval_lab.models.response import Response


class EvaluationResult(Base):
    """One row per (response, metric) — EAV-style rather than fixed columns,
    since more metrics (several via LLM-judge in V2) will be added over time
    without requiring a migration each time."""

    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey("responses.id"))
    metric_name: Mapped[str]
    score: Mapped[float]
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    response: Mapped["Response"] = relationship(back_populates="evaluation_results")
