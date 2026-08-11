from collections.abc import Iterator

from sqlalchemy.orm import Session

from llm_eval_lab.db import SessionLocal


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
