from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from llm_eval_lab.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
