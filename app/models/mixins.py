"""Shared column patterns reused across models, kept out of Base itself so
each model opts in explicitly (e.g. join tables, if any get added later,
may not want a surrogate UUID PK)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Client-generated UUID primary key.

    Generated in Python (default=uuid.uuid4) rather than left to the
    database, so the application/repository layer knows a new row's id
    immediately after constructing it — no round trip required before it
    can be referenced (e.g. to attach transcript messages to a session in
    the same unit of work).
    """

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Server-computed creation timestamp for auditing/ordering."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
