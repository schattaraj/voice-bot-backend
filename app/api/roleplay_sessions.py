"""RoleplaySession CRUD endpoints — consumed by the frontend's
roleplay.service.ts. Session creation only; the actual conversation lives
on the WebSocket (app.api.websockets), not here.
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_persona_repository, get_roleplay_session_repository
from app.core.exceptions import NotFoundError
from app.repositories.persona_repository import PersonaRepository
from app.repositories.roleplay_session_repository import RoleplaySessionRepository
from app.schemas.roleplay_session import RoleplaySessionResponse, StartSessionRequest

router = APIRouter()


@router.get("", response_model=list[RoleplaySessionResponse])
def list_sessions(
    repo: RoleplaySessionRepository = Depends(get_roleplay_session_repository),
) -> list[RoleplaySessionResponse]:
    return repo.list_all()


@router.post("", response_model=RoleplaySessionResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    payload: StartSessionRequest,
    session_repo: RoleplaySessionRepository = Depends(get_roleplay_session_repository),
    persona_repo: PersonaRepository = Depends(get_persona_repository),
) -> RoleplaySessionResponse:
    if persona_repo.get_by_id(payload.persona_id) is None:
        raise NotFoundError("Persona", str(payload.persona_id))
    return session_repo.create(payload.persona_id)


@router.get("/{session_id}", response_model=RoleplaySessionResponse)
def get_session(
    session_id: uuid.UUID,
    repo: RoleplaySessionRepository = Depends(get_roleplay_session_repository),
) -> RoleplaySessionResponse:
    session = repo.get_by_id(session_id)
    if session is None:
        raise NotFoundError("RoleplaySession", str(session_id))
    return session


@router.post("/{session_id}/end", response_model=RoleplaySessionResponse)
def end_session(
    session_id: uuid.UUID,
    repo: RoleplaySessionRepository = Depends(get_roleplay_session_repository),
) -> RoleplaySessionResponse:
    session = repo.get_by_id(session_id)
    if session is None:
        raise NotFoundError("RoleplaySession", str(session_id))
    return repo.end(session)
