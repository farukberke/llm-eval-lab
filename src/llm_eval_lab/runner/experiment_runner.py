from datetime import datetime, timezone

from sqlalchemy.orm import Session

from llm_eval_lab.config import settings
from llm_eval_lab.llm.base import LLMClient
from llm_eval_lab.llm.factory import get_llm_client
from llm_eval_lab.models import Experiment, ExperimentRun, Response, RunStatus


def run_experiment(
    session: Session, experiment_id: int, llm_client: LLMClient | None = None
) -> ExperimentRun:
    """Run every test case in the experiment's dataset through its model/prompt
    config, recording one Response per test case. A single test case's LLM call
    failing is recorded on Response.error and does not abort the run."""
    experiment = session.get(Experiment, experiment_id)
    if experiment is None:
        raise ValueError(f"No experiment with id={experiment_id}")

    client = llm_client or get_llm_client(
        experiment.model_config.provider, host=settings.ollama_host
    )

    run = ExperimentRun(
        experiment_id=experiment.id,
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.flush()

    try:
        for test_case in experiment.dataset.test_cases:
            prompt_text = experiment.prompt.template.format(question=test_case.question)
            try:
                result = client.generate(
                    model=experiment.model_config.model_name,
                    prompt=prompt_text,
                    parameters=experiment.model_config.parameters,
                )
            except Exception as exc:
                session.add(
                    Response(
                        experiment_run_id=run.id,
                        test_case_id=test_case.id,
                        error=str(exc),
                    )
                )
                continue

            session.add(
                Response(
                    experiment_run_id=run.id,
                    test_case_id=test_case.id,
                    response_text=result.text,
                    latency_ms=result.latency_ms,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    raw_response=result.raw,
                )
            )
    except Exception:
        run.status = RunStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        session.flush()
        raise

    run.status = RunStatus.COMPLETED
    run.completed_at = datetime.now(timezone.utc)
    session.flush()
    return run
