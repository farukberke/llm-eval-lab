from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from llm_eval_lab.db import Base


class Prompt(Base):
    """Immutable by convention: edits go in as a new row, existing rows are never updated."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    template: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
