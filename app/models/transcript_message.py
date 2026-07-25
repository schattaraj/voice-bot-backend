"""TranscriptMessage: one turn in a RoleplaySession's conversation.

Mirrors the frontend's TranscriptMessage/TranscriptPanel contract exactly
(speaker, text, elapsed-time offset).
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MessageSpeaker
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.roleplay_session import RoleplaySession


class TranscriptMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transcript_messages"

    # Cascade-deletes with its session (see RoleplaySession) — messages
    # never outlive the call they belong to. Indexed since "messages for
    # this session, in order" is the only way this table is ever queried.
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roleplay_sessions.id", ondelete="CASCADE"), index=True
    )

    speaker: Mapped[MessageSpeaker] = mapped_column(Enum(MessageSpeaker, name="message_speaker"))
    text: Mapped[str] = mapped_column(Text)

    # Milliseconds elapsed since the call started — NOT a wall-clock
    # timestamp. This is the same "elapsed time" the frontend already
    # formats via formatDuration(timestampMs / 1000); created_at (from
    # TimestampMixin) covers the actual insertion wall-clock time
    # separately, which is a different, DB-audit concern.
    timestamp_ms: Mapped[int] = mapped_column(Integer)

    session: Mapped["RoleplaySession"] = relationship(back_populates="transcript_messages")
