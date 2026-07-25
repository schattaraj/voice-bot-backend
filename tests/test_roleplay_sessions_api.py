"""Tests for the /api/v1/roleplay/sessions router, full-stack against the
real MSSQL database via the client fixture (rolled back per test)."""

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


def _create_persona(client: TestClient) -> str:
    return client.post("/api/v1/personas", json=PERSONA_PAYLOAD).json()["id"]


def test_start_session_returns_in_progress_session(client: TestClient) -> None:
    persona_id = _create_persona(client)

    response = client.post("/api/v1/roleplay/sessions", json={"personaId": persona_id})

    assert response.status_code == 201
    body = response.json()
    assert body["personaId"] == persona_id
    assert body["status"] == "in-progress"
    assert body["startedAt"] is not None
    assert body["endedAt"] is None


def test_start_session_404_when_persona_missing(client: TestClient) -> None:
    response = client.post("/api/v1/roleplay/sessions", json={"personaId": str(uuid.uuid4())})
    assert response.status_code == 404


def test_get_session(client: TestClient) -> None:
    persona_id = _create_persona(client)
    created = client.post("/api/v1/roleplay/sessions", json={"personaId": persona_id}).json()

    response = client.get(f"/api/v1/roleplay/sessions/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_session_404_when_missing(client: TestClient) -> None:
    response = client.get(f"/api/v1/roleplay/sessions/{uuid.uuid4()}")
    assert response.status_code == 404


def test_end_session_marks_completed(client: TestClient) -> None:
    persona_id = _create_persona(client)
    created = client.post("/api/v1/roleplay/sessions", json={"personaId": persona_id}).json()

    response = client.post(f"/api/v1/roleplay/sessions/{created['id']}/end")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["endedAt"] is not None


def test_end_session_404_when_missing(client: TestClient) -> None:
    response = client.post(f"/api/v1/roleplay/sessions/{uuid.uuid4()}/end")
    assert response.status_code == 404


def test_list_sessions_includes_created_session(client: TestClient) -> None:
    persona_id = _create_persona(client)
    created = client.post("/api/v1/roleplay/sessions", json={"personaId": persona_id}).json()

    response = client.get("/api/v1/roleplay/sessions")

    assert response.status_code == 200
    ids = [s["id"] for s in response.json()]
    assert created["id"] in ids
