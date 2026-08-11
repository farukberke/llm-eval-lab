import pytest

from tests.factories import make_dataset, make_test_case


def test_create_and_list_model_configs(client):
    create_resp = client.post(
        "/model-configs",
        json={"name": "Qwen", "provider": "ollama", "model_name": "qwen2.5:7b"},
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["model_name"] == "qwen2.5:7b"

    list_resp = client.get("/model-configs")
    assert list_resp.status_code == 200
    assert any(c["name"] == "Qwen" for c in list_resp.json())


def test_create_and_list_prompts(client):
    create_resp = client.post(
        "/prompts", json={"name": "Concise", "template": "Answer concisely: {question}"}
    )
    assert create_resp.status_code == 201

    list_resp = client.get("/prompts")
    assert list_resp.status_code == 200
    assert any(p["name"] == "Concise" for p in list_resp.json())


def test_create_and_get_experiment(client, db_session):
    dataset = make_dataset(db_session)
    model_config_id = client.post(
        "/model-configs",
        json={"name": "Qwen", "provider": "ollama", "model_name": "qwen2.5:7b"},
    ).json()["id"]
    prompt_id = client.post(
        "/prompts", json={"name": "Concise", "template": "Answer concisely: {question}"}
    ).json()["id"]

    create_resp = client.post(
        "/experiments",
        json={
            "name": "My Experiment",
            "dataset_id": dataset.id,
            "model_config_id": model_config_id,
            "prompt_id": prompt_id,
        },
    )
    assert create_resp.status_code == 201
    experiment_id = create_resp.json()["id"]

    get_resp = client.get(f"/experiments/{experiment_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "My Experiment"

    list_resp = client.get("/experiments")
    assert any(e["id"] == experiment_id for e in list_resp.json())


def test_get_experiment_404(client):
    resp = client.get("/experiments/999999")
    assert resp.status_code == 404


def test_run_experiment_endpoint_404_for_unknown_experiment(client):
    resp = client.post("/experiments/999999/runs")
    assert resp.status_code == 404


@pytest.mark.integration
def test_run_experiment_endpoint_hits_real_ollama(client, db_session):
    dataset = make_dataset(db_session)
    make_test_case(db_session, dataset_id=dataset.id, question="2+2", expected_answer="4")
    model_config_id = client.post(
        "/model-configs",
        json={"name": "Qwen", "provider": "ollama", "model_name": "qwen2.5:7b"},
    ).json()["id"]
    prompt_id = client.post(
        "/prompts", json={"name": "Concise", "template": "Answer concisely: {question}"}
    ).json()["id"]
    experiment_id = client.post(
        "/experiments",
        json={
            "name": "Live Experiment",
            "dataset_id": dataset.id,
            "model_config_id": model_config_id,
            "prompt_id": prompt_id,
        },
    ).json()["id"]

    resp = client.post(f"/experiments/{experiment_id}/runs")
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"
