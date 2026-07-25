"""Evaluation: the scored feedback report for one completed RoleplaySession.

Backend counterpart of the frontend's SessionScore (Step 7's Session
Analytics page): overall score, skill-breakdown metrics, strengths,
weaknesses, recommendations, and a talk-time timeline.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.roleplay_session import RoleplaySession


class Evaluation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluations"

    # unique=True is what makes this a one-to-one relationship at the DB
    # level: at most one Evaluation per session. Cascade-deletes with its
    # session, same reasoning as TranscriptMessage.
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roleplay_sessions.id", ondelete="CASCADE"), unique=True
    )

    overall_score: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)

    # Structured report data stored as JSON rather than normalized child
    # tables (e.g. a separate EvaluationMetric row per metric). These are
    # always produced and read as one cohesive report alongside their
    # parent Evaluation, never queried independently (no "average
    # Objection Handling score across all sessions" feature exists today).
    # If cross-session metric analytics become a real requirement,
    # `metrics` in particular is the field to normalize out into its own
    # table — everything else here is more naturally list-shaped.
    metrics: Mapped[list[dict]] = mapped_column(JSON, default=list)  # [{label, value, maxValue}]
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSON, default=list)
    timeline: Mapped[list[dict]] = mapped_column(JSON, default=list)  # [{minute, repSeconds, customerSeconds}]

    session: Mapped["RoleplaySession"] = relationship(back_populates="evaluation")
