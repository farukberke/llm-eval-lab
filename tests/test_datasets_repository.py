import json
from pathlib import Path

import pytest
from sqlalchemy import select

from llm_eval_lab.datasets.repository import load_dataset_from_file
from llm_eval_lab.models import Dataset, TestCase
from tests.factories import make_dataset, make_test_case

SAMPLE_DATASET_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "sample_datasets" / "qa_smoke_test.json"
)


def test_create_dataset_and_add_test_case_round_trip(db_session):
    dataset = make_dataset(db_session, name="Round Trip", description="desc")
    test_case = make_test_case(
        db_session, dataset_id=dataset.id, question="Q?", expected_answer="A"
    )

    db_session.expire_all()
    fetched = db_session.get(Dataset, dataset.id)

    assert fetched.name == "Round Trip"
    assert fetched.description == "desc"
    assert len(fetched.test_cases) == 1
    assert fetched.test_cases[0].id == test_case.id
    assert fetched.test_cases[0].question == "Q?"
    assert fetched.test_cases[0].expected_answer == "A"


def test_load_dataset_from_file_round_trip(db_session):
    dataset = load_dataset_from_file(
        db_session, path=SAMPLE_DATASET_PATH, dataset_name="QA Smoke Test"
    )
    db_session.commit()

    test_cases = (
        db_session.execute(
            select(TestCase).where(TestCase.dataset_id == dataset.id)
        )
        .scalars()
        .all()
    )

    expected_records = json.loads(SAMPLE_DATASET_PATH.read_text(encoding="utf-8"))
    assert len(test_cases) == len(expected_records)
    assert {tc.question for tc in test_cases} == {r["question"] for r in expected_records}


def test_load_dataset_from_file_rejects_malformed_record(db_session, tmp_path):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(
        json.dumps(
            [
                {"question": "Fine?", "expected_answer": "Yes"},
                {"question": "Missing answer?"},
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected_answer"):
        load_dataset_from_file(db_session, path=bad_path, dataset_name="Bad Dataset")

    persisted = db_session.execute(
        select(Dataset).where(Dataset.name == "Bad Dataset")
    ).scalar_one_or_none()
    assert persisted is None
