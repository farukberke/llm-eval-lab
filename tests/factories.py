from typing import Any

from sqlalchemy.orm import Session

from llm_eval_lab.datasets.repository import add_test_case, create_dataset
from llm_eval_lab.models import Dataset, Experiment, ModelConfig, Prompt, TestCase


def make_dataset(
    session: Session, name: str = "Test Dataset", description: str | None = None
) -> Dataset:
    return create_dataset(session, name=name, description=description)


def make_test_case(
    session: Session,
    dataset_id: int,
    question: str = "What is 2 + 2?",
    expected_answer: str = "4",
    reference_source: str | None = None,
) -> TestCase:
    return add_test_case(
        session,
        dataset_id=dataset_id,
        question=question,
        expected_answer=expected_answer,
        reference_source=reference_source,
    )


def make_model_config(
    session: Session,
    name: str = "Test Model Config",
    provider: str = "ollama",
    model_name: str = "qwen2.5:7b",
    parameters: dict[str, Any] | None = None,
) -> ModelConfig:
    model_config = ModelConfig(
        name=name, provider=provider, model_name=model_name, parameters=parameters
    )
    session.add(model_config)
    session.flush()
    return model_config


def make_prompt(
    session: Session,
    name: str = "Test Prompt",
    template: str = "Answer concisely: {question}",
) -> Prompt:
    prompt = Prompt(name=name, template=template)
    session.add(prompt)
    session.flush()
    return prompt


def make_experiment(
    session: Session,
    dataset_id: int,
    model_config_id: int,
    prompt_id: int,
    name: str = "Test Experiment",
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
