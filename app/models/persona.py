"""Persona: a reusable AI buyer configuration a rep can practice against.

Mirrors the frontend's Persona Configuration form (industry, personality,
difficulty, company profile, pain points, competitors, objections) — see
the frontend's components/personas/schema.ts for the matching contract.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PersonaDifficulty
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.roleplay_session import RoleplaySession


class Persona(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "personas"

    # Plain strings, not enums: these are populated from a configurable
    # options list on the frontend (see PersonaConfigForm), not a fixed
    # literal-union type, so new values shouldn't require a migration.
    industry: Mapped[str] = mapped_column(String(120))
    customer_personality: Mapped[str] = mapped_column(String(60))
    company_size: Mapped[str] = mapped_column(String(60))
    decision_maker_role: Mapped[str] = mapped_column(String(120))
    budget: Mapped[str] = mapped_column(String(60))

    # difficulty IS a genuine closed set on the frontend (a literal-union
    # type shared with Scenario), so it gets a real enum here.
    difficulty: Mapped[PersonaDifficulty] = mapped_column(Enum(PersonaDifficulty, name="persona_difficulty"))

    # Free-form tag lists. Stored as JSON rather than normalized child
    # tables — see the Step 12 design notes: they're always read/written as
    # a whole alongside their parent Persona, never queried independently.
    pain_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    competitors: Mapped[list[str]] = mapped_column(JSON, default=list)
    possible_objections: Mapped[list[str]] = mapped_column(JSON, default=list)

    roleplay_sessions: Mapped[list["RoleplaySession"]] = relationship(back_populates="persona")
