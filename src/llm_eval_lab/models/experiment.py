from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_eval_lab.db import Base

if TYPE_CHECKING:
    from llm_eval_lab.models.dataset import Dataset
    from llm_eval_lab.models.experiment_run import ExperimentRun
    from llm_eval_lab.models.model_config import ModelConfig
    from llm_eval_lab.models.prompt import Prompt


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None]
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    model_config_id: Mapped[int] = mapped_column(ForeignKey("model_configs.id"))
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    dataset: Mapped["Dataset"] = relationship()
    model_config: Mapped["ModelConfig"] = relationship()
    prompt: Mapped["Prompt"] = relationship()
    runs: Mapped[list["ExperimentRun"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
