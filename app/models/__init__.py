"""SQLAlchemy ORM models — the persisted database schema.

Every model is imported here so that importing `app.models` (as
alembic/env.py does) registers all of them on Base.metadata before
autogenerate inspects it.
"""

from app.models.base import Base
from app.models.evaluation import Evaluation
from app.models.persona import Persona
from app.models.roleplay_session import RoleplaySession
from app.models.transcript_message import TranscriptMessage

__all__ = [
    "Base",
    "Persona",
    "RoleplaySession",
    "TranscriptMessage",
    "Evaluation",
]
