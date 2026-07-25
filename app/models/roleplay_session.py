"""RoleplaySession: one practice call against a Persona.

Corresponds to the frontend's CallScreen/session-store: a session is
created against a Persona, moves idle -> in-progress -> completed, and
owns an ordered transcript plus (once completed) one Evaluation.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SessionStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation
    from app.models.persona import Persona
    from app.models.transcript_message import TranscriptMessage


class RoleplaySession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roleplay_sessions"

    # No ondelete=CASCADE here on purpose: a Persona is a reusable template,
    # and RoleplaySessions are historical records. Deleting a Persona that
    # still has sessions should fail (the DB's default NO ACTION) rather
    # than silently wiping call history — callers must archive/reassign
    # sessions first. Indexed since "sessions for this persona" is a core
    # lookup (e.g. reuse history on the persona detail view).
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id"), index=True)

    # Frontend type has startedAt as always-set, but the DB model is
    # intentionally more permissive: a row can exist in "idle" status
    # before the call actually connects, so both are nullable until the
    # corresponding transition happens.
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), default=SessionStatus.IDLE
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    persona: Mapped["Persona"] = relationship(back_populates="roleplay_sessions")

    # Transcript messages and the evaluation have no meaning without their
    # parent session, so both cascade-delete at the ORM and DB level.
    transcript_messages: Mapped[list["TranscriptMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TranscriptMessage.timestamp_ms",
    )
    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
