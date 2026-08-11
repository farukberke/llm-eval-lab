import json
from pathlib import Path

from sqlalchemy.orm import Session

from llm_eval_lab.models import Dataset, TestCase

REQUIRED_TEST_CASE_FIELDS = ("question", "expected_answer")


def create_dataset(
    session: Session, name: str, description: str | None = None
) -> Dataset:
    dataset = Dataset(name=name, description=description)
    session.add(dataset)
    session.flush()
    return dataset


def add_test_case(
    session: Session,
    dataset_id: int,
    question: str,
    expected_answer: str,
    reference_source: str | None = None,
) -> TestCase:
    test_case = TestCase(
        dataset_id=dataset_id,
        question=question,
        expected_answer=expected_answer,
        reference_source=reference_source,
    )
    session.add(test_case)
    session.flush()
    return test_case


def load_dataset_from_file(
    session: Session,
    path: str | Path,
    dataset_name: str,
    dataset_description: str | None = None,
) -> Dataset:
    """Load a flat JSON list of {question, expected_answer, reference_source?}
    records into a new Dataset. Validates required fields before writing anything."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))

    if not isinstance(records, list):
        raise ValueError(f"{path}: expected a JSON list of test case records")

    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"{path}: record {i} is not a JSON object")
        missing = [f for f in REQUIRED_TEST_CASE_FIELDS if not record.get(f)]
        if missing:
            raise ValueError(
                f"{path}: record {i} missing required field(s): {', '.join(missing)}"
            )

    dataset = create_dataset(session, name=dataset_name, description=dataset_description)
    for record in records:
        add_test_case(
            session,
            dataset_id=dataset.id,
            question=record["question"],
            expected_answer=record["expected_answer"],
            reference_source=record.get("reference_source"),
        )
    return dataset
