from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from llm_eval_lab.api.deps import get_db
from llm_eval_lab.comparison.compare import compare_experiment_runs
from llm_eval_lab.evaluation.deterministic import ExactMatchEvaluator, NormalizedSimilarityEvaluator
from llm_eval_lab.evaluation.runner import evaluate_run
from llm_eval_lab.models import ExperimentRun
from llm_eval_lab.schemas import ComparisonReportRead, EvaluationResultRead, ExperimentRunDetail

router = APIRouter(tags=["results"])

_DETERMINISTIC_EVALUATORS = [ExactMatchEvaluator(), NormalizedSimilarityEvaluator()]


@router.get("/runs/{run_id}", response_model=ExperimentRunDetail)
def get_run_endpoint(run_id: int, session: Session = Depends(get_db)):
    run = session.get(ExperimentRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No experiment run with id={run_id}")
    return run


@router.post("/runs/{run_id}/evaluate", response_model=list[EvaluationResultRead])
def evaluate_run_endpoint(run_id: int, session: Session = Depends(get_db)):
    """Scores every response in the run with both deterministic evaluators
    (exact_match, normalized_similarity) — mirrors the M5 evaluate_run CLI."""
    try:
        return evaluate_run(session, run_id, _DETERMINISTIC_EVALUATORS)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/compare", response_model=ComparisonReportRead)
def compare_runs_endpoint(
    run_ids: list[int] = Query(..., description="Experiment run IDs to compare"),
    session: Session = Depends(get_db),
):
    try:
        return compare_experiment_runs(session, run_ids)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
