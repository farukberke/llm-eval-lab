import pytest

from llm_eval_lab.evaluation.deterministic import (
    ExactMatchEvaluator,
    NormalizedSimilarityEvaluator,
)


@pytest.mark.parametrize(
    "response_text,expected_answer,expected_score",
    [
        ("Paris", "Paris", 1.0),
        ("paris", "Paris", 1.0),  # case-insensitive
        ("  Paris  ", "Paris", 1.0),  # leading/trailing whitespace
        ("Paris   is   great", "Paris is great", 1.0),  # collapsed internal whitespace
        ("Paris", "London", 0.0),
        ("Paris", "Paris, France", 0.0),  # not a substring match, must be exact
    ],
)
def test_exact_match_evaluator(response_text, expected_answer, expected_score):
    result = ExactMatchEvaluator().evaluate(response_text, expected_answer)
    assert result.value == expected_score


def test_normalized_similarity_evaluator_identical_strings():
    result = NormalizedSimilarityEvaluator().evaluate("Paris", "Paris")
    assert result.value == 1.0


def test_normalized_similarity_evaluator_ignores_case_and_whitespace():
    result = NormalizedSimilarityEvaluator().evaluate("  PARIS  ", "paris")
    assert result.value == 1.0


def test_normalized_similarity_evaluator_completely_different_strings():
    result = NormalizedSimilarityEvaluator().evaluate("Paris", "xyz123")
    assert result.value == 0.0


def test_normalized_similarity_evaluator_partial_overlap_is_between_zero_and_one():
    result = NormalizedSimilarityEvaluator().evaluate("Paris, France", "Paris")
    assert 0.0 < result.value < 1.0
