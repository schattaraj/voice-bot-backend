"""Tests for the /api/v1/personas router, full-stack against the real
MySQL database via the client fixture (rolled back per test)."""

import uuid

from fastapi.testclient import TestClient

PERSONA_PAYLOAD = {
    "industry": "SaaS",
    "customerPersonality": "skeptical",
    "difficulty": "intermediate",
    "companySize": "51-200",
    "decisionMakerRole": "VP of Sales",
    "budget": "$50k-$100k",
    "painPoints": ["slow onboarding"],
    "competitors": ["Acme Corp"],
    "possibleObjections": ["too expensive"],
}


def test_create_and_get_persona(client: TestClient) -> None:
    create_response = client.post("/api/v1/personas", json=PERSONA_PAYLOAD)
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["industry"] == "SaaS"
    assert body["customerPersonality"] == "skeptical"
    assert body["difficulty"] == "intermediate"

    get_response = client.get(f"/api/v1/personas/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


def test_get_persona_404_when_missing(client: TestClient) -> None:
    response = client.get(f"/api/v1/personas/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_personas_includes_created_persona(client: TestClient) -> None:
    created = client.post("/api/v1/personas", json=PERSONA_PAYLOAD).json()

    response = client.get("/api/v1/personas")

    assert response.status_code == 200
    ids = [p["id"] for p in response.json()]
    assert created["id"] in ids


def test_update_persona_patches_only_given_fields(client: TestClient) -> None:
    created = client.post("/api/v1/personas", json=PERSONA_PAYLOAD).json()

    response = client.patch(f"/api/v1/personas/{created['id']}", json={"industry": "Healthcare"})

    assert response.status_code == 200
    body = response.json()
    assert body["industry"] == "Healthcare"
    assert body["customerPersonality"] == "skeptical"


def test_update_persona_404_when_missing(client: TestClient) -> None:
    response = client.patch(f"/api/v1/personas/{uuid.uuid4()}", json={"industry": "Healthcare"})
    assert response.status_code == 404


def test_delete_persona_then_get_404(client: TestClient) -> None:
    created = client.post("/api/v1/personas", json=PERSONA_PAYLOAD).json()

    delete_response = client.delete(f"/api/v1/personas/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/personas/{created['id']}")
    assert get_response.status_code == 404


def test_delete_persona_404_when_missing(client: TestClient) -> None:
    response = client.delete(f"/api/v1/personas/{uuid.uuid4()}")
    assert response.status_code == 404
