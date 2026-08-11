from tests.factories import make_experiment, make_model_config, make_prompt, make_test_case


def test_create_and_get_dataset(client):
    create_resp = client.post("/datasets", json={"name": "QA Smoke", "description": "test"})
    assert create_resp.status_code == 201
    dataset_id = create_resp.json()["id"]

    get_resp = client.get(f"/datasets/{dataset_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["name"] == "QA Smoke"
    assert body["test_cases"] == []


def test_list_datasets(client):
    client.post("/datasets", json={"name": "Dataset A"})
    client.post("/datasets", json={"name": "Dataset B"})

    resp = client.get("/datasets")
    assert resp.status_code == 200
    names = {d["name"] for d in resp.json()}
    assert {"Dataset A", "Dataset B"} <= names


def test_get_dataset_404(client):
    resp = client.get("/datasets/999999")
    assert resp.status_code == 404


def test_update_dataset(client):
    dataset_id = client.post("/datasets", json={"name": "Old Name"}).json()["id"]

    resp = client.patch(f"/datasets/{dataset_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_update_dataset_404(client):
    resp = client.patch("/datasets/999999", json={"name": "New Name"})
    assert resp.status_code == 404


def test_delete_dataset(client):
    dataset_id = client.post("/datasets", json={"name": "Throwaway"}).json()["id"]

    delete_resp = client.delete(f"/datasets/{dataset_id}")
    assert delete_resp.status_code == 204

    assert client.get(f"/datasets/{dataset_id}").status_code == 404


def test_delete_dataset_404(client):
    resp = client.delete("/datasets/999999")
    assert resp.status_code == 404


def test_delete_dataset_conflict_when_referenced_by_experiment(client, db_session):
    dataset = client.post("/datasets", json={"name": "In Use"}).json()
    make_test_case(db_session, dataset_id=dataset["id"])
    model_config = make_model_config(db_session)
    prompt = make_prompt(db_session)
    make_experiment(
        db_session,
        dataset_id=dataset["id"],
        model_config_id=model_config.id,
        prompt_id=prompt.id,
    )

    resp = client.delete(f"/datasets/{dataset['id']}")
    assert resp.status_code == 409
