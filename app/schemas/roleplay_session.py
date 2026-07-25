"""REST request/response schemas for the RoleplaySession resource.

Note the field is personaId, not scenarioId — the frontend's original
RoleplaySession type used "scenarioId" (Step 1, before Persona existed as
a rich entity); this REST contract uses the actual backend relationship,
and the frontend type was updated to match (see Step 20 notes).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.base import CamelCaseModel

# Re-declared rather than imported from models.enums — see that module's
# docstring for why schemas/ stays independent of the ORM layer.
RoleplaySessionStatus = Literal["idle", "in-progress", "completed"]


class StartSessionRequest(CamelCaseModel):
    persona_id: UUID


class RoleplaySessionResponse(CamelCaseModel):
    id: UUID
    persona_id: UUID
    status: RoleplaySessionStatus
    started_at: datetime | None
    ended_at: datetime | None
