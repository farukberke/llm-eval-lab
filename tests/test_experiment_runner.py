from typing import Any

import pytest

from llm_eval_lab.llm.base import LLMResponse
from llm_eval_lab.models import RunStatus
from llm_eval_lab.runner.experiment_runner import run_experiment
from tests.factories import (
    make_dataset,
    make_experiment,
    make_model_config,
    make_prompt,
    make_test_case,
)


class FakeLLMClient:
    """Returns a canned response per prompt, or raises for prompts listed in fail_on."""

    def __init__(self, fail_on: set[str] | None = None):
        self.fail_on = fail_on or set()
        self.calls: list[str] = []

    def generate(
        self, model: str, prompt: str, parameters: dict[str, Any] | None = None
    ) -> LLMResponse:
        self.calls.append(prompt)
        if prompt in self.fail_on:
            raise RuntimeError("simulated LLM failure")
        return LLMResponse(
            text=f"echo: {prompt}",
            latency_ms=1.0,
            prompt_tokens=1,
            completion_tokens=1,
            raw={"prompt": prompt},
        )


def _make_experiment_with_test_cases(session, questions: list[str]):
    dataset = make_dataset(session)
    for question in questions:
        make_test_case(session, dataset_id=dataset.id, question=question)
    model_config = make_model_config(session)
    prompt = make_prompt(session)
    return make_experiment(
        session,
        dataset_id=dataset.id,
        model_config_id=model_config.id,
        prompt_id=prompt.id,
    )


def test_run_experiment_creates_one_response_per_test_case(db_session):
    experiment = _make_experiment_with_test_cases(
        db_session, ["What is 2 + 2?", "What is the capital of France?"]
    )
    client = FakeLLMClient()

    run = run_experiment(db_session, experiment_id=experiment.id, llm_client=client)

    assert run.status == RunStatus.COMPLETED
    assert run.started_at is not None
    assert run.completed_at is not None
    assert len(run.responses) == 2
    assert all(r.error is None for r in run.responses)
    assert all(r.response_text.startswith("echo: Answer concisely:") for r in run.responses)


def test_run_experiment_records_per_item_failure_without_aborting(db_session):
    experiment = _make_experiment_with_test_cases(
        db_session, ["question A", "question B", "question C"]
    )
    failing_prompt = "Answer concisely: question B"
    client = FakeLLMClient(fail_on={failing_prompt})

    run = run_experiment(db_session, experiment_id=experiment.id, llm_client=client)

    assert run.status == RunStatus.COMPLETED
    assert len(run.responses) == 3
    failed = [r for r in run.responses if r.error is not None]
    succeeded = [r for r in run.responses if r.error is None]
    assert len(failed) == 1
    assert len(succeeded) == 2
    assert "simulated LLM failure" in failed[0].error
    assert failed[0].response_text is None


def test_run_experiment_raises_for_unknown_experiment(db_session):
    with pytest.raises(ValueError):
        run_experiment(db_session, experiment_id=999999, llm_client=FakeLLMClient())


@pytest.mark.integration
def test_run_experiment_against_real_ollama(db_session):
    experiment = _make_experiment_with_test_cases(
        db_session, ["What is the capital of Japan? One word answer."]
    )

    run = run_experiment(db_session, experiment_id=experiment.id)

    assert run.status == RunStatus.COMPLETED
    assert len(run.responses) == 1
    assert run.responses[0].error is None
    assert run.responses[0].response_text
