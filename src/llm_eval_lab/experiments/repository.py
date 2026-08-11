from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from llm_eval_lab.models import Experiment, ModelConfig, Prompt


def create_model_config(
    session: Session,
    name: str,
    provider: str,
    model_name: str,
    parameters: dict[str, Any] | None = None,
) -> ModelConfig:
    model_config = ModelConfig(
        name=name, provider=provider, model_name=model_name, parameters=parameters
    )
    session.add(model_config)
    session.flush()
    return model_config


def list_model_configs(session: Session) -> list[ModelConfig]:
    return list(session.scalars(select(ModelConfig).order_by(ModelConfig.id)))


def create_prompt(session: Session, name: str, template: str) -> Prompt:
    prompt = Prompt(name=name, template=template)
    session.add(prompt)
    session.flush()
    return prompt


def list_prompts(session: Session) -> list[Prompt]:
    return list(session.scalars(select(Prompt).order_by(Prompt.id)))


def create_experiment(
    session: Session,
    name: str,
    dataset_id: int,
    model_config_id: int,
    prompt_id: int,
    description: str | None = None,
) -> Experiment:
    experiment = Experiment(
        name=name,
        description=description,
        dataset_id=dataset_id,
        model_config_id=model_config_id,
        prompt_id=prompt_id,
    )
    session.add(experiment)
    session.flush()
    return experiment


def get_experiment(session: Session, experiment_id: int) -> Experiment | None:
    return session.get(Experiment, experiment_id)


def list_experiments(session: Session) -> list[Experiment]:
    return list(session.scalars(select(Experiment).order_by(Experiment.id)))
