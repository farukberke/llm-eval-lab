from sqlalchemy.orm import Session

from llm_eval_lab.evaluation.base import Evaluator
from llm_eval_lab.models import EvaluationResult, ExperimentRun


def evaluate_run(
    session: Session, experiment_run_id: int, evaluators: list[Evaluator]
) -> list[EvaluationResult]:
    """Score every response in the run against its test case's expected_answer,
    once per evaluator. Responses with no response_text (failed LLM calls) are
    skipped — there's nothing to score."""
    run = session.get(ExperimentRun, experiment_run_id)
    if run is None:
        raise ValueError(f"No experiment run with id={experiment_run_id}")

    results = []
    for response in run.responses:
        if response.response_text is None:
            continue
        expected_answer = response.test_case.expected_answer
        for evaluator in evaluators:
            score = evaluator.evaluate(response.response_text, expected_answer)
            result = EvaluationResult(
                response_id=response.id,
                metric_name=evaluator.metric_name,
                score=score.value,
                details=score.details,
            )
            session.add(result)
            results.append(result)

    session.flush()
    return results
