from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from llm_eval_lab.api.deps import get_db
from llm_eval_lab.experiments.repository import (
    create_experiment,
    create_model_config,
    create_prompt,
    get_experiment,
    list_experiments,
    list_model_configs,
    list_prompts,
)
from llm_eval_lab.runner.experiment_runner import run_experiment
from llm_eval_lab.schemas import (
    ExperimentCreate,
    ExperimentRead,
    ExperimentRunRead,
    ModelConfigCreate,
    ModelConfigRead,
    PromptCreate,
    PromptRead,
)

router = APIRouter(tags=["experiments"])


@router.post("/model-configs", response_model=ModelConfigRead, status_code=status.HTTP_201_CREATED)
def create_model_config_endpoint(payload: ModelConfigCreate, session: Session = Depends(get_db)):
    return create_model_config(
        session,
        name=payload.name,
        provider=payload.provider,
        model_name=payload.model_name,
        parameters=payload.parameters,
    )


@router.get("/model-configs", response_model=list[ModelConfigRead])
def list_model_configs_endpoint(session: Session = Depends(get_db)):
    return list_model_configs(session)


@router.post("/prompts", response_model=PromptRead, status_code=status.HTTP_201_CREATED)
def create_prompt_endpoint(payload: PromptCreate, session: Session = Depends(get_db)):
    return create_prompt(session, name=payload.name, template=payload.template)


@router.get("/prompts", response_model=list[PromptRead])
def list_prompts_endpoint(session: Session = Depends(get_db)):
    return list_prompts(session)


@router.post("/experiments", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
def create_experiment_endpoint(payload: ExperimentCreate, session: Session = Depends(get_db)):
    return create_experiment(
        session,
        name=payload.name,
        dataset_id=payload.dataset_id,
        model_config_id=payload.model_config_id,
        prompt_id=payload.prompt_id,
        description=payload.description,
    )


@router.get("/experiments", response_model=list[ExperimentRead])
def list_experiments_endpoint(session: Session = Depends(get_db)):
    return list_experiments(session)


@router.get("/experiments/{experiment_id}", response_model=ExperimentRead)
def get_experiment_endpoint(experiment_id: int, session: Session = Depends(get_db)):
    experiment = get_experiment(session, experiment_id)
    if experiment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No experiment with id={experiment_id}")
    return experiment


@router.post(
    "/experiments/{experiment_id}/runs",
    response_model=ExperimentRunRead,
    status_code=status.HTTP_201_CREATED,
)
def run_experiment_endpoint(experiment_id: int, session: Session = Depends(get_db)):
    """Runs synchronously — an explicit, stated V1 limitation (no background
    jobs added to solve it, per the plan)."""
    try:
        return run_experiment(session, experiment_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
