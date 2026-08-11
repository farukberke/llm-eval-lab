from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMResponse:
    text: str
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    raw: dict[str, Any]


class LLMClient(Protocol):
    def generate(
        self,
        model: str,
        prompt: str,
        parameters: dict[str, Any] | None = None,
    ) -> LLMResponse: ...
