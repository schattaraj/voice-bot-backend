"""REST request/response schemas for the Persona resource.

The wire contract consumed by the frontend's services/persona.service.ts —
field names here are the snake_case source that CamelCaseModel serializes
as camelCase, matching frontend/types/persona.ts exactly.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.base import CamelCaseModel

# Re-declared rather than imported from models.enums — see that module's
# docstring for why schemas/ stays independent of the ORM layer.
PersonaDifficulty = Literal["beginner", "intermediate", "advanced"]


class PersonaCreateRequest(CamelCaseModel):
    industry: str
    customer_personality: str
    difficulty: PersonaDifficulty
    company_size: str
    decision_maker_role: str
    budget: str
    pain_points: list[str]
    competitors: list[str]
    possible_objections: list[str]


class PersonaUpdateRequest(CamelCaseModel):
    """All fields optional — a PATCH only needs to send what's changing."""

    industry: str | None = None
    customer_personality: str | None = None
    difficulty: PersonaDifficulty | None = None
    company_size: str | None = None
    decision_maker_role: str | None = None
    budget: str | None = None
    pain_points: list[str] | None = None
    competitors: list[str] | None = None
    possible_objections: list[str] | None = None


class PersonaResponse(CamelCaseModel):
    id: UUID
    industry: str
    customer_personality: str
    difficulty: PersonaDifficulty
    company_size: str
    decision_maker_role: str
    budget: str
    pain_points: list[str]
    competitors: list[str]
    possible_objections: list[str]
    created_at: datetime
