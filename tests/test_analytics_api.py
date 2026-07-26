"""Tests for the /api/v1/analytics router, full-stack against the real
MySQL database via the client fixture (rolled back per test).

Evaluation rows are produced by the Evaluation Engine (Step 19), so these
tests insert an Evaluation directly via the ORM rather than through the
(read-only) analytics endpoints.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation

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


def _create_session_with_evaluation(client: TestClient, db_session: Session) -> str:
    persona_id = client.post("/api/v1/personas", json=PERSONA_PAYLOAD).json()["id"]
    session_id = client.post("/api/v1/roleplay/sessions", json={"personaId": persona_id}).json()["id"]

    evaluation = Evaluation(
        session_id=uuid.UUID(session_id),
        overall_score=82,
        summary="Solid discovery, weak close.",
        metrics=[{"label": "Discovery", "value": 8, "maxValue": 10}],
        strengths=["Asked open-ended questions"],
        weaknesses=["Didn't ask for the sale"],
        recommendations=["Practice closing techniques"],
        timeline=[{"minute": 1, "repSeconds": 30, "customerSeconds": 30}],
    )
    db_session.add(evaluation)
    db_session.commit()
    return session_id


def test_get_session_score(client: TestClient, db_session: Session) -> None:
    session_id = _create_session_with_evaluation(client, db_session)

    response = client.get(f"/api/v1/analytics/sessions/{session_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["sessionId"] == session_id
    assert body["overallScore"] == 82
    assert body["metrics"] == [{"label": "Discovery", "value": 8, "maxValue": 10}]
    assert body["timeline"] == [{"minute": 1, "repSeconds": 30, "customerSeconds": 30}]


def test_get_session_score_404_when_missing(client: TestClient) -> None:
    response = client.get(f"/api/v1/analytics/sessions/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_score_history_includes_created_evaluation(client: TestClient, db_session: Session) -> None:
    session_id = _create_session_with_evaluation(client, db_session)

    response = client.get("/api/v1/analytics/history")

    assert response.status_code == 200
    session_ids = [s["sessionId"] for s in response.json()]
    assert session_id in session_ids
