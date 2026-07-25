"""Tests for the /api/v1/roleplay/sessions/{id}/transcript router,
full-stack against the real MSSQL database via the client fixture (rolled
back per test)."""

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


def _create_session(client: TestClient) -> str:
    persona_id = client.post("/api/v1/personas", json=PERSONA_PAYLOAD).json()["id"]
    return client.post("/api/v1/roleplay/sessions", json={"personaId": persona_id}).json()["id"]


def test_append_and_get_transcript(client: TestClient) -> None:
    session_id = _create_session(client)

    append_response = client.post(
        f"/api/v1/roleplay/sessions/{session_id}/transcript",
        json={"speaker": "rep", "text": "Hi, thanks for taking my call.", "timestampMs": 0},
    )
    assert append_response.status_code == 201
    body = append_response.json()
    assert body["speaker"] == "rep"
    assert body["text"] == "Hi, thanks for taking my call."
    assert body["timestampMs"] == 0

    get_response = client.get(f"/api/v1/roleplay/sessions/{session_id}/transcript")
    assert get_response.status_code == 200
    messages = get_response.json()
    assert len(messages) == 1
    assert messages[0]["id"] == body["id"]


def test_get_transcript_is_ordered_by_timestamp(client: TestClient) -> None:
    session_id = _create_session(client)
    client.post(
        f"/api/v1/roleplay/sessions/{session_id}/transcript",
        json={"speaker": "ai-buyer", "text": "Hello, this is Alicia.", "timestampMs": 0},
    )
    client.post(
        f"/api/v1/roleplay/sessions/{session_id}/transcript",
        json={"speaker": "rep", "text": "Hi Alicia.", "timestampMs": 500},
    )

    response = client.get(f"/api/v1/roleplay/sessions/{session_id}/transcript")

    messages = response.json()
    assert [m["timestampMs"] for m in messages] == [0, 500]


def test_get_transcript_404_when_session_missing(client: TestClient) -> None:
    response = client.get(f"/api/v1/roleplay/sessions/{uuid.uuid4()}/transcript")
    assert response.status_code == 404


def test_append_transcript_404_when_session_missing(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/roleplay/sessions/{uuid.uuid4()}/transcript",
        json={"speaker": "rep", "text": "hi", "timestampMs": 0},
    )
    assert response.status_code == 404
