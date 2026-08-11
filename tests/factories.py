from sqlalchemy.orm import Session

from llm_eval_lab.datasets.repository import add_test_case, create_dataset
from llm_eval_lab.models import Dataset, TestCase


def make_dataset(
    session: Session, name: str = "Test Dataset", description: str | None = None
) -> Dataset:
    return create_dataset(session, name=name, description=description)


def make_test_case(
    session: Session,
    dataset_id: int,
    question: str = "What is 2 + 2?",
    expected_answer: str = "4",
    reference_source: str | None = None,
) -> TestCase:
    return add_test_case(
        session,
        dataset_id=dataset_id,
        question=question,
        expected_answer=expected_answer,
        reference_source=reference_source,
    )
