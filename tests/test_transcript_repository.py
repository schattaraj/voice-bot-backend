"""Tests for TranscriptRepository against the real MySQL database (rolled
back per test via the db_session fixture)."""

from sqlalchemy.orm import Session

from app.repositories.persona_repository import PersonaRepository
from app.repositories.roleplay_session_repository import RoleplaySessionRepository
from app.repositories.transcript_repository import TranscriptRepository

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


def _make_session(db_session: Session):
    persona = PersonaRepository(db_session).create(PERSONA_DATA)
    return RoleplaySessionRepository(db_session).create(persona.id)


def test_append_creates_message(db_session: Session) -> None:
    session = _make_session(db_session)
    repo = TranscriptRepository(db_session)

    message = repo.append(session.id, "rep", "Hi, thanks for taking my call.", 0)

    assert message.id is not None
    assert message.session_id == session.id
    assert message.speaker.value == "rep"
    assert message.text == "Hi, thanks for taking my call."
    assert message.timestamp_ms == 0


def test_list_by_session_orders_by_timestamp_ms(db_session: Session) -> None:
    session = _make_session(db_session)
    repo = TranscriptRepository(db_session)
    repo.append(session.id, "ai-buyer", "Hello, this is Alicia.", 0)
    repo.append(session.id, "rep", "Hi Alicia, how are you?", 500)

    messages = repo.list_by_session(session.id)

    assert [m.timestamp_ms for m in messages] == [0, 500]
    assert [m.speaker.value for m in messages] == ["ai-buyer", "rep"]


def test_list_by_session_is_scoped_to_that_session(db_session: Session) -> None:
    session_one = _make_session(db_session)
    session_two = _make_session(db_session)
    repo = TranscriptRepository(db_session)
    repo.append(session_one.id, "rep", "For session one", 0)
    repo.append(session_two.id, "rep", "For session two", 0)

    messages = repo.list_by_session(session_one.id)

    assert len(messages) == 1
    assert messages[0].text == "For session one"
