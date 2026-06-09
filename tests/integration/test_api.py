import pytest
from fastapi.testclient import TestClient

from agentstatelib.api import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "test.db")))


AUTH_HEADERS = {"x-api-key": "dev-key-123"}


def test_health_no_auth_required(client):
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "version" in response.json()


def test_create_workflow_requires_auth(client):
    response = client.post(
        "/v1/workflows",
        json={
            "goal": "test",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "invalid_api_key"


def test_create_workflow(client):
    response = client.post(
        "/v1/workflows",
        headers=AUTH_HEADERS,
        json={
            "goal": "test goal",
            "workflow_type": "research",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert "workflow_id" in data
    assert data["goal"] == "test goal"


def test_create_and_retrieve_workflow(client):
    create_response = client.post(
        "/v1/workflows",
        headers=AUTH_HEADERS,
        json={
            "goal": "test goal",
        },
    )

    workflow_id = create_response.json()["workflow_id"]

    response = client.get(
        f"/v1/workflows/{workflow_id}",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["workflow_id"] == workflow_id


def test_list_workflows(client):
    response_1 = client.post(
        "/v1/workflows",
        headers=AUTH_HEADERS,
        json={"goal": "workflow 1"},
    )

    response_2 = client.post(
        "/v1/workflows",
        headers=AUTH_HEADERS,
        json={"goal": "workflow 2"},
    )

    workflow_id_1 = response_1.json()["workflow_id"]
    workflow_id_2 = response_2.json()["workflow_id"]

    response = client.get(
        "/v1/workflows",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 2

    assert workflow_id_1 in data["workflow_ids"]
    assert workflow_id_2 in data["workflow_ids"]


def test_patch_updates_state(client):
    create_response = client.post(
        "/v1/workflows",
        headers=AUTH_HEADERS,
        json={
            "goal": "test goal",
        },
    )

    workflow_id = create_response.json()["workflow_id"]

    patch_response = client.post(
        f"/v1/workflows/{workflow_id}/patches",
        headers=AUTH_HEADERS,
        json={
            "agent_id": "test",
            "target": "facts.test_key",
            "value": "hello",
            "reason": "test patch",
        },
    )

    assert patch_response.status_code == 200

    response = client.get(
        f"/v1/workflows/{workflow_id}",
        headers=AUTH_HEADERS,
    )

    assert response.json()["facts"]["test_key"] == "hello"


def test_get_unknown_workflow_returns_404(client):
    response = client.get(
        "/v1/workflows/nonexistent-workflow-id",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404

    assert response.json()["detail"]["error_code"] == "workflow_not_found"
