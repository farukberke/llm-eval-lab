from pydantic import BaseModel, ConfigDict


class RunComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

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


class ComparisonReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    runs: list[RunComparisonRead]
