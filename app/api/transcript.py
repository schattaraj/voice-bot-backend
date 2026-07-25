"""Transcript endpoints — consumed by the frontend's transcript.service.ts.

Mounted under the same "/roleplay/sessions" prefix as roleplay_sessions.py
(see app.api.router), since every route here is scoped to a single session.
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_roleplay_session_repository, get_transcript_repository
from app.core.exceptions import NotFoundError
from app.repositories.roleplay_session_repository import RoleplaySessionRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.transcript import AppendTranscriptMessageRequest, TranscriptMessageResponse

router = APIRouter()


@router.get("/{session_id}/transcript", response_model=list[TranscriptMessageResponse])
def get_transcript(
    session_id: uuid.UUID,
    session_repo: RoleplaySessionRepository = Depends(get_roleplay_session_repository),
    transcript_repo: TranscriptRepository = Depends(get_transcript_repository),
) -> list[TranscriptMessageResponse]:
    if session_repo.get_by_id(session_id) is None:
        raise NotFoundError("RoleplaySession", str(session_id))
    return transcript_repo.list_by_session(session_id)


@router.post(
    "/{session_id}/transcript",
    response_model=TranscriptMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def append_transcript_message(
    session_id: uuid.UUID,
    payload: AppendTranscriptMessageRequest,
    session_repo: RoleplaySessionRepository = Depends(get_roleplay_session_repository),
    transcript_repo: TranscriptRepository = Depends(get_transcript_repository),
) -> TranscriptMessageResponse:
    if session_repo.get_by_id(session_id) is None:
        raise NotFoundError("RoleplaySession", str(session_id))
    return transcript_repo.append(session_id, payload.speaker, payload.text, payload.timestamp_ms)
