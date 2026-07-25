"""Tests for RoleplaySessionRepository against the real MSSQL database
(rolled back per test via the db_session fixture)."""

import uuid

from sqlalchemy.orm import Session

from app.models.enums import SessionStatus
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


def _make_persona(db_session: Session):
    return PersonaRepository(db_session).create(PERSONA_DATA)


def test_create_starts_session_in_progress(db_session: Session) -> None:
    persona = _make_persona(db_session)
    repo = RoleplaySessionRepository(db_session)

    session = repo.create(persona.id)

    assert session.id is not None
    assert session.persona_id == persona.id
    assert session.status == SessionStatus.IN_PROGRESS
    assert session.started_at is not None
    assert session.ended_at is None


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = RoleplaySessionRepository(db_session)
    assert repo.get_by_id(uuid.uuid4()) is None


def test_end_marks_completed_with_ended_at(db_session: Session) -> None:
    persona = _make_persona(db_session)
    repo = RoleplaySessionRepository(db_session)
    session = repo.create(persona.id)

    ended = repo.end(session)

    assert ended.status == SessionStatus.COMPLETED
    assert ended.ended_at is not None


def test_list_all_orders_by_created_at_desc(db_session: Session) -> None:
    persona = _make_persona(db_session)
    repo = RoleplaySessionRepository(db_session)
    first = repo.create(persona.id)
    second = repo.create(persona.id)

    sessions = repo.list_all()
    ids = [s.id for s in sessions]
    assert ids.index(second.id) < ids.index(first.id)
