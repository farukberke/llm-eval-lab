import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_eval_lab.db import Base

if TYPE_CHECKING:
    from llm_eval_lab.models.experiment import Experiment
    from llm_eval_lab.models.response import Response


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.PENDING
    )
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    experiment: Mapped["Experiment"] = relationship(back_populates="runs")
    responses: Mapped[list["Response"]] = relationship(
        back_populates="experiment_run", cascade="all, delete-orphan"
    )
