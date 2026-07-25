"""Tests for EvaluationRepository against the real MSSQL database (rolled
back per test via the db_session fixture).

EvaluationRepository is read-only (Evaluation rows are produced by the
Evaluation Engine, Step 19) so these tests insert Evaluation rows directly
via the ORM rather than through the repository.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.persona_repository import PersonaRepository
from app.repositories.roleplay_session_repository import RoleplaySessionRepository

PERSONA_DATA = {
    "industry": "SaaS",
    "customer_personality": "skeptical",
    "difficulty": "intermediate",
    "company_size": "51-200",
    "decision_maker_role": "VP of Sales",
    "budget": "$50k-$100k",
    "pain_points": ["slow onboarding"],
    "competitors": ["Acme Corp"],
    "possible_objections": ["too expensive"],
}


def _make_evaluation(db_session: Session, *, overall_score: int = 82) -> Evaluation:
    persona = PersonaRepository(db_session).create(PERSONA_DATA)
    session = RoleplaySessionRepository(db_session).create(persona.id)
    evaluation = Evaluation(
        session_id=session.id,
        overall_score=overall_score,
        summary="Solid discovery, weak close.",
        metrics=[{"label": "Discovery", "value": 8, "maxValue": 10}],
        strengths=["Asked open-ended questions"],
        weaknesses=["Didn't ask for the sale"],
        recommendations=["Practice closing techniques"],
        timeline=[{"minute": 1, "repSeconds": 30, "customerSeconds": 30}],
    )
    db_session.add(evaluation)
    db_session.commit()
    db_session.refresh(evaluation)
    return evaluation


def test_get_by_session_returns_matching_evaluation(db_session: Session) -> None:
    evaluation = _make_evaluation(db_session)
    repo = EvaluationRepository(db_session)

    fetched = repo.get_by_session(evaluation.session_id)

    assert fetched is not None
    assert fetched.id == evaluation.id
    assert fetched.overall_score == 82


def test_get_by_session_returns_none_when_missing(db_session: Session) -> None:
    repo = EvaluationRepository(db_session)
    assert repo.get_by_session(uuid.uuid4()) is None


def test_list_all_orders_by_created_at_desc(db_session: Session) -> None:
    first = _make_evaluation(db_session, overall_score=70)
    second = _make_evaluation(db_session, overall_score=90)
    repo = EvaluationRepository(db_session)

    evaluations = repo.list_all()
    ids = [e.id for e in evaluations]

    assert ids.index(second.id) < ids.index(first.id)
