import argparse

from llm_eval_lab.comparison.compare import compare_experiment_runs
from llm_eval_lab.db import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare experiment runs side by side")
    parser.add_argument(
        "run_ids", type=int, nargs="+", help="IDs of the experiment runs to compare"
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        report = compare_experiment_runs(session, run_ids=args.run_ids)

    for run in report.runs:
        print(f"Run {run.run_id} - {run.experiment_name} ({run.model_name})")
        print(f"  success_rate={run.success_rate:.1%} ({run.succeeded}/{run.total_responses})")
        if run.avg_latency_ms is not None:
            print(f"  avg_latency_ms={run.avg_latency_ms:.1f}")
        if run.avg_prompt_tokens is not None:
            print(
                f"  avg_prompt_tokens={run.avg_prompt_tokens:.1f}  "
                f"avg_completion_tokens={run.avg_completion_tokens:.1f}"
            )
        for metric_name, score in run.avg_scores.items():
            print(f"  {metric_name}: avg={score:.3f}")
        print()


if __name__ == "__main__":
    main()
