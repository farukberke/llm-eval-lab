from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from llm_eval_lab.models import ExperimentRun

_RESPONSE_COLUMNS = ["run_id", "succeeded", "latency_ms", "prompt_tokens", "completion_tokens"]
_SCORE_COLUMNS = ["run_id", "metric_name", "score"]


@dataclass(frozen=True)
class RunComparison:
    """Aggregated stats for one experiment run — one row per run in a ComparisonReport."""

    run_id: int
    experiment_name: str
    model_name: str
    total_responses: int
    succeeded: int
    success_rate: float
    avg_latency_ms: float | None
    avg_prompt_tokens: float | None
    avg_completion_tokens: float | None
    avg_scores: dict[str, float]


@dataclass(frozen=True)
class ComparisonReport:
    runs: list[RunComparison]


def compare_experiment_runs(session: Session, run_ids: list[int]) -> ComparisonReport:
    """Aggregate success rate, latency, tokens, and per-metric scores across a set
    of experiment runs for side-by-side comparison (e.g. one model config vs
    another on the same dataset+prompt). Read-only — no new tables; pandas
    groupby does the aggregation."""
    runs = [session.get(ExperimentRun, run_id) for run_id in run_ids]
    for run_id, run in zip(run_ids, runs):
        if run is None:
            raise ValueError(f"No experiment run with id={run_id}")

    response_rows = []
    score_rows = []
    for run in runs:
        for response in run.responses:
            response_rows.append(
                {
                    "run_id": run.id,
                    "succeeded": response.response_text is not None,
                    "latency_ms": response.latency_ms,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                }
            )
            for result in response.evaluation_results:
                score_rows.append(
                    {"run_id": run.id, "metric_name": result.metric_name, "score": result.score}
                )

    responses_df = pd.DataFrame(response_rows, columns=_RESPONSE_COLUMNS)
    scores_df = pd.DataFrame(score_rows, columns=_SCORE_COLUMNS)

    run_comparisons = [_summarize_run(run, responses_df, scores_df) for run in runs]
    return ComparisonReport(runs=run_comparisons)


def _summarize_run(
    run: ExperimentRun, responses_df: pd.DataFrame, scores_df: pd.DataFrame
) -> RunComparison:
    run_responses = responses_df[responses_df["run_id"] == run.id]
    run_scores = scores_df[scores_df["run_id"] == run.id]

    total = len(run_responses)
    succeeded = int(run_responses["succeeded"].sum())
    avg_scores = run_scores.groupby("metric_name")["score"].mean().to_dict()

    return RunComparison(
        run_id=run.id,
        experiment_name=run.experiment.name,
        model_name=run.experiment.model_config.model_name,
        total_responses=total,
        succeeded=succeeded,
        success_rate=succeeded / total if total else 0.0,
        avg_latency_ms=_mean_or_none(run_responses["latency_ms"]),
        avg_prompt_tokens=_mean_or_none(run_responses["prompt_tokens"]),
        avg_completion_tokens=_mean_or_none(run_responses["completion_tokens"]),
        avg_scores=avg_scores,
    )


def _mean_or_none(series: pd.Series) -> float | None:
    mean = series.mean()
    return None if pd.isna(mean) else float(mean)
