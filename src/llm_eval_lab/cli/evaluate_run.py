import argparse

from llm_eval_lab.db import SessionLocal
from llm_eval_lab.evaluation.deterministic import (
    ExactMatchEvaluator,
    NormalizedSimilarityEvaluator,
)
from llm_eval_lab.evaluation.runner import evaluate_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an experiment run's responses")
    parser.add_argument("experiment_run_id", type=int, help="ID of the experiment run to evaluate")
    args = parser.parse_args()

    evaluators = [ExactMatchEvaluator(), NormalizedSimilarityEvaluator()]

    with SessionLocal() as session:
        results = evaluate_run(
            session, experiment_run_id=args.experiment_run_id, evaluators=evaluators
        )
        session.commit()

        print(f"Evaluated run {args.experiment_run_id}: {len(results)} evaluation results recorded")
        for evaluator in evaluators:
            scores = [r.score for r in results if r.metric_name == evaluator.metric_name]
            if not scores:
                continue
            avg = sum(scores) / len(scores)
            print(f"  {evaluator.metric_name}: avg={avg:.3f} (n={len(scores)})")


if __name__ == "__main__":
    main()
