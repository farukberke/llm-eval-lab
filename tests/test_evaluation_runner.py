from typing import Any

import pytest

from llm_eval_lab.evaluation.deterministic import (
    ExactMatchEvaluator,
    NormalizedSimilarityEvaluator,
)
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
    """Returns a fixed response text per prompt (keyed by substring), or raises
    for prompts in fail_on — lets a test control exactly what each Response
    ends up containing so evaluation scores are predictable."""

    def __init__(self, answers: dict[str, str], fail_on: set[str] | None = None):
        self.answers = answers
        self.fail_on = fail_on or set()

    def generate(
        self, model: str, prompt: str, parameters: dict[str, Any] | None = None
    ) -> LLMResponse:
        if prompt in self.fail_on:
            raise RuntimeError("simulated LLM failure")
        return LLMResponse(
            text=self.answers[prompt],
            latency_ms=1.0,
            prompt_tokens=1,
            completion_tokens=1,
            raw={"prompt": prompt},
        )


def _make_run(session, answers: dict[str, str], fail_on: set[str] | None = None):
    dataset = make_dataset(session)
    for prompt_text in answers:
        # prompt template is "Answer concisely: {question}", so recover the question
        question = prompt_text.removeprefix("Answer concisely: ")
        make_test_case(session, dataset_id=dataset.id, question=question, expected_answer=question)
    model_config = make_model_config(session)
    prompt = make_prompt(session)
    experiment = make_experiment(
        session,
        dataset_id=dataset.id,
        model_config_id=model_config.id,
        prompt_id=prompt.id,
    )
    client = ScriptedLLMClient(answers, fail_on=fail_on)
    return run_experiment(session, experiment_id=experiment.id, llm_client=client)


def test_evaluate_run_scores_every_response_with_every_evaluator(db_session):
    run = _make_run(
        db_session,
        answers={
            "Answer concisely: Paris": "Paris",  # exact match after the question is echoed back
            "Answer concisely: London": "definitely not london",  # partial similarity only
        },
    )

    results = evaluate_run(
        db_session,
        experiment_run_id=run.id,
        evaluators=[ExactMatchEvaluator(), NormalizedSimilarityEvaluator()],
    )

    assert len(results) == 4  # 2 responses x 2 evaluators
    by_metric = {(r.response.test_case.question, r.metric_name): r.score for r in results}
    assert by_metric[("Paris", "exact_match")] == 1.0
    assert by_metric[("Paris", "normalized_similarity")] == 1.0
    assert by_metric[("London", "exact_match")] == 0.0
    assert 0.0 < by_metric[("London", "normalized_similarity")] < 1.0


def test_evaluate_run_skips_failed_responses(db_session):
    failing_prompt = "Answer concisely: London"
    run = _make_run(
        db_session,
        answers={
            "Answer concisely: Paris": "Paris",
            failing_prompt: "unused",
        },
        fail_on={failing_prompt},
    )

    results = evaluate_run(
        db_session, experiment_run_id=run.id, evaluators=[ExactMatchEvaluator()]
    )

    assert len(results) == 1
    assert results[0].response.test_case.question == "Paris"


def test_evaluate_run_raises_for_unknown_run(db_session):
    with pytest.raises(ValueError):
        evaluate_run(
            db_session, experiment_run_id=999999, evaluators=[ExactMatchEvaluator()]
        )
