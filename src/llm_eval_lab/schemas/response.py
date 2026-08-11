from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResponseRead(BaseModel):
    """DTO for a Response row. Deliberately omits raw_response (Ollama's raw
    JSONB output) — that field exists in the ORM only as a debugging aid, per
    the plan's decisions, and has no reason to be exposed over the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_run_id: int
    test_case_id: int
    response_text: str | None
    latency_ms: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    error: str | None
    created_at: datetime
