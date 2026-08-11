import argparse

from llm_eval_lab.db import SessionLocal
from llm_eval_lab.runner.experiment_runner import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an experiment against its dataset")
    parser.add_argument("experiment_id", type=int, help="ID of the experiment to run")
    args = parser.parse_args()

    with SessionLocal() as session:
        run = run_experiment(session, experiment_id=args.experiment_id)
        session.commit()
        succeeded = sum(1 for r in run.responses if r.error is None)
        failed = len(run.responses) - succeeded
        print(
            f"Run {run.id} for experiment {args.experiment_id} finished: "
            f"status={run.status.value}, {succeeded} succeeded, {failed} failed"
        )


if __name__ == "__main__":
    main()
