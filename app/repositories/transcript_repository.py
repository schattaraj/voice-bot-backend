"""Data-access layer for TranscriptMessage."""

import uuid

from sqlalchemy.orm import Session

from app.models.enums import MessageSpeaker
from app.models.transcript_message import TranscriptMessage


class TranscriptRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_session(self, session_id: uuid.UUID) -> list[TranscriptMessage]:
        return list(
            self._db.query(TranscriptMessage)
            .filter(TranscriptMessage.session_id == session_id)
            .order_by(TranscriptMessage.timestamp_ms)
            .all()
        )

    def append(self, session_id: uuid.UUID, speaker: str, text: str, timestamp_ms: int) -> TranscriptMessage:
        message = TranscriptMessage(
            session_id=session_id,
            speaker=MessageSpeaker(speaker),
            text=text,
            timestamp_ms=timestamp_ms,
        )
        self._db.add(message)
        self._db.commit()
        self._db.refresh(message)
        return message
