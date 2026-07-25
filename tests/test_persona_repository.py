"""Tests for PersonaRepository against the real MSSQL database (rolled
back per test via the db_session fixture)."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.repositories.persona_repository import PersonaRepository

PERSONA_DATA = {
    "industry": "SaaS",
    "customer_personality": "skeptical",
    "difficulty": "intermediate",
    "company_size": "51-200",
    "decision_maker_role": "VP of Sales",
    "budget": "$50k-$100k",
    "pain_points": ["slow onboarding", "poor reporting"],
    "competitors": ["Acme Corp"],
    "possible_objections": ["too expensive", "already using a competitor"],
}


def test_create_and_get_by_id(db_session: Session) -> None:
    repo = PersonaRepository(db_session)
    created = repo.create(PERSONA_DATA)

    assert created.id is not None
    assert created.industry == "SaaS"
    assert created.difficulty.value == "intermediate"

    fetched = repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = PersonaRepository(db_session)
    assert repo.get_by_id(uuid.uuid4()) is None


def test_list_all_orders_by_created_at_desc(db_session: Session) -> None:
    repo = PersonaRepository(db_session)
    first = repo.create(PERSONA_DATA)
    second = repo.create({**PERSONA_DATA, "industry": "Fintech"})

    personas = repo.list_all()
    ids = [p.id for p in personas]
    assert ids.index(second.id) < ids.index(first.id)


def test_update_changes_only_provided_fields(db_session: Session) -> None:
    repo = PersonaRepository(db_session)
    persona = repo.create(PERSONA_DATA)

    updated = repo.update(persona, {"industry": "Healthcare", "difficulty": "advanced"})

    assert updated.industry == "Healthcare"
    assert updated.difficulty.value == "advanced"
    assert updated.customer_personality == "skeptical"  # unchanged


def test_delete_removes_persona(db_session: Session) -> None:
    repo = PersonaRepository(db_session)
    persona = repo.create(PERSONA_DATA)
    persona_id = persona.id

    repo.delete(persona)

    assert repo.get_by_id(persona_id) is None


@pytest.mark.parametrize("difficulty", ["beginner", "intermediate", "advanced"])
def test_create_accepts_every_difficulty(db_session: Session, difficulty: str) -> None:
    repo = PersonaRepository(db_session)
    created = repo.create({**PERSONA_DATA, "difficulty": difficulty})
    assert created.difficulty.value == difficulty
