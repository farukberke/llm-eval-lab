from difflib import SequenceMatcher

from llm_eval_lab.evaluation.base import EvaluationScore


def _normalize(text: str) -> str:
    """lowercase, strip, and collapse internal whitespace so evaluators aren't
    tripped up by cosmetic formatting differences."""
    return " ".join(text.lower().split())


class ExactMatchEvaluator:
    metric_name = "exact_match"

    def evaluate(self, response_text: str, expected_answer: str) -> EvaluationScore:
        is_match = _normalize(response_text) == _normalize(expected_answer)
        return EvaluationScore(value=1.0 if is_match else 0.0)


class NormalizedSimilarityEvaluator:
    metric_name = "normalized_similarity"

    def evaluate(self, response_text: str, expected_answer: str) -> EvaluationScore:
        ratio = SequenceMatcher(
            None, _normalize(response_text), _normalize(expected_answer)
        ).ratio()
        return EvaluationScore(value=ratio)
