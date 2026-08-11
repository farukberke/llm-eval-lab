from sqlalchemy import text

from llm_eval_lab.db import engine


def test_select_1():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
