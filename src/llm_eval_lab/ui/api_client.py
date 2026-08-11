import httpx

from llm_eval_lab.schemas import (
    ComparisonReportRead,
    DatasetRead,
    EvaluationResultRead,
    ExperimentRead,
    ExperimentRunRead,
    ModelConfigRead,
    PromptRead,
)

DEFAULT_TIMEOUT_SECONDS = 120.0


class ApiClient:
    """Thin httpx wrapper over the existing FastAPI endpoints.

    Contains no scoring/aggregation logic of its own — every method is a
    direct call to an endpoint already backed by M2-M7's repository/runner/
    evaluation/comparison functions. The one exception is
    `get_or_create_experiment`, which does a client-side lookup by
    (dataset_id, model_config_id, prompt_id) before creating a new
    Experiment row, so repeated demo runs reuse the same config per the
    platform's own Experiment/ExperimentRun split rather than piling up
    duplicate Experiments.
    """

    def __init__(self, base_url: str, http_client: httpx.Client | None = None):
        self._http_client = http_client or httpx.Client(
            base_url=base_url, timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def list_datasets(self) -> list[DatasetRead]:
        response = self._http_client.get("/datasets")
        response.raise_for_status()
        return [DatasetRead.model_validate(item) for item in response.json()]

    def list_model_configs(self) -> list[ModelConfigRead]:
        response = self._http_client.get("/model-configs")
        response.raise_for_status()
        return [ModelConfigRead.model_validate(item) for item in response.json()]

    def list_prompts(self) -> list[PromptRead]:
        response = self._http_client.get("/prompts")
        response.raise_for_status()
        return [PromptRead.model_validate(item) for item in response.json()]

    def list_experiments(self) -> list[ExperimentRead]:
        response = self._http_client.get("/experiments")
        response.raise_for_status()
        return [ExperimentRead.model_validate(item) for item in response.json()]

    def create_experiment(
        self, name: str, dataset_id: int, model_config_id: int, prompt_id: int
    ) -> ExperimentRead:
        response = self._http_client.post(
            "/experiments",
            json={
                "name": name,
                "dataset_id": dataset_id,
                "model_config_id": model_config_id,
                "prompt_id": prompt_id,
            },
        )
        response.raise_for_status()
        return ExperimentRead.model_validate(response.json())

    def get_or_create_experiment(
        self, dataset_id: int, model_config_id: int, prompt_id: int, name: str
    ) -> ExperimentRead:
        for experiment in self.list_experiments():
            if (
                experiment.dataset_id == dataset_id
                and experiment.model_config_id == model_config_id
                and experiment.prompt_id == prompt_id
            ):
                return experiment
        return self.create_experiment(
            name=name,
            dataset_id=dataset_id,
            model_config_id=model_config_id,
            prompt_id=prompt_id,
        )

    def run_experiment(self, experiment_id: int) -> ExperimentRunRead:
        response = self._http_client.post(f"/experiments/{experiment_id}/runs")
        response.raise_for_status()
        return ExperimentRunRead.model_validate(response.json())

    def evaluate_run(self, run_id: int) -> list[EvaluationResultRead]:
        response = self._http_client.post(f"/runs/{run_id}/evaluate")
        response.raise_for_status()
        return [EvaluationResultRead.model_validate(item) for item in response.json()]

    def compare_runs(self, run_ids: list[int]) -> ComparisonReportRead:
        response = self._http_client.get(
            "/compare", params={"run_ids": run_ids}
        )
        response.raise_for_status()
        return ComparisonReportRead.model_validate(response.json())
