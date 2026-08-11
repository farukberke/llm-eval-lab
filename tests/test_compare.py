from typing import Any

import pytest

from llm_eval_lab.comparison.compare import compare_experiment_runs
from llm_eval_lab.evaluation.deterministic import ExactMatchEvaluator
from llm_eval_lab.evaluation.runner import evaluate_run
from llm_eval_lab.llm.base import LLMResponse
from llm_eval_lab.runner.experiment_runner import run_experiment
from tests.factories import (
    make_dataset,
    make_experiment,
    make_model_config,
    make_prompt,
    make_test_case,
)


class ScriptedLLMClient:
    """Returns a fixed response text and latency per prompt (keyed by substring),
    or raises for prompts in fail_on — lets a test control exactly what each
    Response ends up containing so comparison averages are predictable."""

    def __init__(
        self,
        answers: dict[str, str],
        latency_ms: float = 1.0,
        fail_on: set[str] | None = None,
    ):
        self.answers = answers
        self.latency_ms = latency_ms
        self.fail_on = fail_on or set()

    def generate(
        self, model: str, prompt: str, parameters: dict[str, Any] | None = None
    ) -> LLMResponse:
        if prompt in self.fail_on:
            raise RuntimeError("simulated LLM failure")
        return LLMResponse(
            text=self.answers[prompt],
            latency_ms=self.latency_ms,
            prompt_tokens=10,
            completion_tokens=5,
            raw={"prompt": prompt},
        )


def _make_evaluated_run(
    session,
    answers: dict[str, str],
    model_config_name: str = "test-model",
    latency_ms: float = 1.0,
    fail_on: set[str] | None = None,
):
    dataset = make_dataset(session)
    for prompt_text in answers:
        # prompt template is "Answer concisely: {question}", so recover the question
        question = prompt_text.removeprefix("Answer concisely: ")
        make_test_case(session, dataset_id=dataset.id, question=question, expected_answer=question)
    model_config = make_model_config(session, name=model_config_name, model_name=model_config_name)
    prompt = make_prompt(session)
    experiment = make_experiment(
        session,
        dataset_id=dataset.id,
        model_config_id=model_config.id,
        prompt_id=prompt.id,
        name=f"Experiment ({model_config_name})",
    )
    client = ScriptedLLMClient(answers, latency_ms=latency_ms, fail_on=fail_on)
    run = run_experiment(session, experiment_id=experiment.id, llm_client=client)
    evaluate_run(session, experiment_run_id=run.id, evaluators=[ExactMatchEvaluator()])
    return run


def test_compare_experiment_runs_reports_known_averages(db_session):
    run_strong = _make_evaluated_run(
        db_session,
        answers={
            "Answer concisely: Paris": "Paris",
            "Answer concisely: London": "London",
        },
        model_config_name="strong-model",
        latency_ms=100.0,
    )
    run_weak = _make_evaluated_run(
        db_session,
        answers={
            "Answer concisely: Paris": "Paris",
            "Answer concisely: London": "definitely not london",
        },
        model_config_name="weak-model",
        latency_ms=200.0,
    )

    report = compare_experiment_runs(db_session, run_ids=[run_strong.id, run_weak.id])

    assert [r.run_id for r in report.runs] == [run_strong.id, run_weak.id]

    strong = report.runs[0]
    assert strong.model_name == "strong-model"
    assert strong.success_rate == 1.0
    assert strong.avg_latency_ms == 100.0
    assert strong.avg_scores["exact_match"] == 1.0

    weak = report.runs[1]
    assert weak.model_name == "weak-model"
    assert weak.success_rate == 1.0
    assert weak.avg_latency_ms == 200.0
    assert weak.avg_scores["exact_match"] == 0.5


def test_compare_excludes_failed_responses_from_latency_and_success_rate(db_session):
    failing_prompt = "Answer concisely: London"
    run = _make_evaluated_run(
        db_session,
        answers={
            "Answer concisely: Paris": "Paris",
            failing_prompt: "unused",
        },
        model_config_name="flaky-model",
        latency_ms=50.0,
        fail_on={failing_prompt},
    )

    report = compare_experiment_runs(db_session, run_ids=[run.id])

    result = report.runs[0]
    assert result.total_responses == 2
    assert result.succeeded == 1
    assert result.success_rate == 0.5
    assert result.avg_latency_ms == 50.0  # only the succeeded response has a latency
    assert result.avg_scores["exact_match"] == 1.0  # failed response skipped by evaluate_run


def test_compare_raises_for_unknown_run(db_session):
    with pytest.raises(ValueError):
        compare_experiment_runs(db_session, run_ids=[999999])
