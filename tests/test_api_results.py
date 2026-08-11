from typing import Any

from llm_eval_lab.llm.base import LLMResponse
from llm_eval_lab.runner.experiment_runner import run_experiment
from tests.factories import make_dataset, make_experiment, make_model_config, make_prompt, make_test_case


class ScriptedLLMClient:
    """Returns a fixed response text per prompt — lets a test build a real,
    already-evaluated run without hitting live Ollama, since evaluate/compare
    endpoints don't call the LLM themselves."""

    def __init__(self, answers: dict[str, str]):
        self.answers = answers

    def generate(
        self, model: str, prompt: str, parameters: dict[str, Any] | None = None
    ) -> LLMResponse:
        return LLMResponse(
            text=self.answers[prompt], latency_ms=1.0, prompt_tokens=1, completion_tokens=1, raw={}
        )


def _make_run(session, name: str, answers: dict[str, str]):
    dataset = make_dataset(session, name=f"{name} dataset")
    for prompt_text in answers:
        question = prompt_text.removeprefix("Answer concisely: ")
        make_test_case(session, dataset_id=dataset.id, question=question, expected_answer=question)
    model_config = make_model_config(session, name=f"{name} model")
    prompt = make_prompt(session)
    experiment = make_experiment(
        session,
        dataset_id=dataset.id,
        model_config_id=model_config.id,
        prompt_id=prompt.id,
        name=name,
    )
    return run_experiment(
        session, experiment_id=experiment.id, llm_client=ScriptedLLMClient(answers)
    )


def test_get_run_endpoint(client, db_session):
    run = _make_run(db_session, "Run A", {"Answer concisely: Paris": "Paris"})

    resp = client.get(f"/runs/{run.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert len(body["responses"]) == 1
    assert body["responses"][0]["response_text"] == "Paris"
    assert body["responses"][0]["evaluation_results"] == []


def test_get_run_endpoint_404(client):
    resp = client.get("/runs/999999")
    assert resp.status_code == 404


def test_evaluate_run_endpoint(client, db_session):
    run = _make_run(
        db_session,
        "Run B",
        {"Answer concisely: Paris": "Paris", "Answer concisely: London": "wrong"},
    )

    resp = client.post(f"/runs/{run.id}/evaluate")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 4  # 2 responses x 2 deterministic evaluators

    detail = client.get(f"/runs/{run.id}").json()
    scored = {r["response_text"]: r["evaluation_results"] for r in detail["responses"]}
    assert any(e["metric_name"] == "exact_match" and e["score"] == 1.0 for e in scored["Paris"])


def test_evaluate_run_endpoint_404(client):
    resp = client.post("/runs/999999/evaluate")
    assert resp.status_code == 404


def test_compare_runs_endpoint(client, db_session):
    strong = _make_run(db_session, "Strong", {"Answer concisely: Paris": "Paris"})
    weak = _make_run(db_session, "Weak", {"Answer concisely: Paris": "nope"})
    client.post(f"/runs/{strong.id}/evaluate")
    client.post(f"/runs/{weak.id}/evaluate")

    resp = client.get("/compare", params={"run_ids": [strong.id, weak.id]})
    assert resp.status_code == 200
    runs = {r["run_id"]: r for r in resp.json()["runs"]}
    assert runs[strong.id]["avg_scores"]["exact_match"] == 1.0
    assert runs[weak.id]["avg_scores"]["exact_match"] == 0.0


def test_compare_runs_endpoint_404(client):
    resp = client.get("/compare", params={"run_ids": [999999]})
    assert resp.status_code == 404
