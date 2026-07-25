"""Transcript turn contract for prompt building, plus the REST
request/response schemas for the transcript resource (Step 20).

TranscriptTurn is independent of models.TranscriptMessage on purpose: the
prompt builder only needs speaker/text/timing, not id/session_id/
created_at, and shouldn't require a DB row to be called (e.g. from a unit
test). TranscriptMessageResponse is the REST-facing counterpart that does
carry the persisted fields, for the frontend's transcript.service.ts.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import CamelCaseModel

Speaker = Literal["rep", "ai-buyer"]


class TranscriptTurn(BaseModel):
    speaker: Speaker
    text: str
    timestamp_ms: int


class AppendTranscriptMessageRequest(CamelCaseModel):
    speaker: Speaker
    text: str
    timestamp_ms: int


class TranscriptMessageResponse(CamelCaseModel):
    id: UUID
    speaker: Speaker
    text: str
    timestamp_ms: int
