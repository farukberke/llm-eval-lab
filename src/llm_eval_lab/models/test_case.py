from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_eval_lab.db import Base

if TYPE_CHECKING:
    from llm_eval_lab.models.dataset import Dataset


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    question: Mapped[str]
    expected_answer: Mapped[str]
    reference_source: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="test_cases")
