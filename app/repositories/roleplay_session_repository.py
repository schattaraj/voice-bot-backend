"""Data-access layer for RoleplaySession."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import SessionStatus
from app.models.roleplay_session import RoleplaySession


class RoleplaySessionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[RoleplaySession]:
        return list(self._db.query(RoleplaySession).order_by(RoleplaySession.created_at.desc()).all())

    def get_by_id(self, session_id: uuid.UUID) -> RoleplaySession | None:
        return self._db.get(RoleplaySession, session_id)

    def create(self, persona_id: uuid.UUID) -> RoleplaySession:
        session = RoleplaySession(
            persona_id=persona_id,
            status=SessionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
        )
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def end(self, session: RoleplaySession) -> RoleplaySession:
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(UTC)
        self._db.commit()
        self._db.refresh(session)
        return session
