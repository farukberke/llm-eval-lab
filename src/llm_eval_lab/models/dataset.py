from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_eval_lab.db import Base

if TYPE_CHECKING:
    from llm_eval_lab.models.test_case import TestCase


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
