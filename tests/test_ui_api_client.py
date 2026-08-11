import json

import httpx
import pytest

from llm_eval_lab.ui.api_client import ApiClient


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(handler))


def test_list_datasets_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/datasets"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "QA Model Comparison",
                    "description": None,
                    "created_at": "2026-08-11T00:00:00",
                }
            ],
        )

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    datasets = client.list_datasets()

    assert len(datasets) == 1
    assert datasets[0].id == 1
    assert datasets[0].name == "QA Model Comparison"


def test_list_model_configs_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/model-configs"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "strong",
                    "provider": "ollama",
                    "model_name": "qwen2.5:7b",
                    "parameters": None,
                    "created_at": "2026-08-11T00:00:00",
                }
            ],
        )

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    model_configs = client.list_model_configs()

    assert model_configs[0].model_name == "qwen2.5:7b"


def test_list_prompts_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/prompts"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "concise QA",
                    "template": "Answer concisely: {question}",
                    "created_at": "2026-08-11T00:00:00",
                }
            ],
        )

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    prompts = client.list_prompts()

    assert prompts[0].template == "Answer concisely: {question}"


def _experiment_json(**overrides):
    base = {
        "id": 1,
        "name": "UI Demo",
        "description": None,
        "dataset_id": 1,
        "model_config_id": 1,
        "prompt_id": 1,
        "created_at": "2026-08-11T00:00:00",
    }
    base.update(overrides)
    return base


def test_get_or_create_experiment_reuses_matching_experiment():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        assert request.method == "GET"
        assert request.url.path == "/experiments"
        return httpx.Response(
            200,
            json=[
                _experiment_json(id=1, dataset_id=1, model_config_id=2, prompt_id=3),
                _experiment_json(id=2, dataset_id=9, model_config_id=9, prompt_id=9),
            ],
        )

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    experiment = client.get_or_create_experiment(
        dataset_id=1, model_config_id=2, prompt_id=3, name="unused"
    )

    assert experiment.id == 1
    assert calls == ["GET"]


def test_get_or_create_experiment_creates_when_no_match():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        assert request.method == "POST"
        assert request.url.path == "/experiments"
        payload = json.loads(request.read())
        assert payload == {
            "name": "UI Demo - modelA - datasetX - promptY",
            "dataset_id": 1,
            "model_config_id": 2,
            "prompt_id": 3,
        }
        return httpx.Response(201, json=_experiment_json(dataset_id=1, model_config_id=2, prompt_id=3))

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    experiment = client.get_or_create_experiment(
        dataset_id=1,
        model_config_id=2,
        prompt_id=3,
        name="UI Demo - modelA - datasetX - promptY",
    )

    assert experiment.dataset_id == 1
    assert experiment.model_config_id == 2
    assert experiment.prompt_id == 3


def test_run_experiment_posts_to_runs_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/experiments/7/runs"
        return httpx.Response(
            201,
            json={
                "id": 42,
                "experiment_id": 7,
                "status": "completed",
                "started_at": "2026-08-11T00:00:00",
                "completed_at": "2026-08-11T00:01:00",
                "created_at": "2026-08-11T00:00:00",
            },
        )

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    run = client.run_experiment(7)

    assert run.id == 42
    assert run.status == "completed"


def test_evaluate_run_posts_to_evaluate_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/runs/42/evaluate"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "response_id": 1,
                    "metric_name": "exact_match",
                    "score": 1.0,
                    "details": None,
                    "created_at": "2026-08-11T00:00:00",
                }
            ],
        )

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    results = client.evaluate_run(42)

    assert results[0].metric_name == "exact_match"


def test_compare_runs_passes_run_ids_and_parses_report():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/compare"
        assert request.url.params.get_list("run_ids") == ["42", "43"]
        return httpx.Response(
            200,
            json={
                "runs": [
                    {
                        "run_id": 42,
                        "experiment_name": "strong",
                        "model_name": "qwen2.5:7b",
                        "total_responses": 10,
                        "succeeded": 10,
                        "success_rate": 1.0,
                        "avg_latency_ms": 800.0,
                        "avg_prompt_tokens": 40.0,
                        "avg_completion_tokens": 5.0,
                        "avg_scores": {"exact_match": 0.4, "normalized_similarity": 0.66},
                    }
                ]
            },
        )

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))
    report = client.compare_runs([42, 43])

    assert len(report.runs) == 1
    assert report.runs[0].model_name == "qwen2.5:7b"
    assert report.runs[0].avg_scores["exact_match"] == 0.4


def test_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    client = ApiClient(base_url="http://testserver", http_client=_mock_client(handler))

    with pytest.raises(httpx.HTTPStatusError):
        client.list_datasets()
