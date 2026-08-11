from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EvaluationScore:
    value: float
    details: dict[str, Any] | None = None


class Evaluator(Protocol):
    metric_name: str

    def evaluate(self, response_text: str, expected_answer: str) -> EvaluationScore: ...
