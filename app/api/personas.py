"""Persona CRUD endpoints — consumed by the frontend's persona.service.ts."""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_persona_repository
from app.core.exceptions import NotFoundError
from app.repositories.persona_repository import PersonaRepository
from app.schemas.persona import PersonaCreateRequest, PersonaResponse, PersonaUpdateRequest

router = APIRouter()


@router.get("", response_model=list[PersonaResponse])
def list_personas(repo: PersonaRepository = Depends(get_persona_repository)) -> list[PersonaResponse]:
    return repo.list_all()


@router.post("", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona(
    payload: PersonaCreateRequest, repo: PersonaRepository = Depends(get_persona_repository)
) -> PersonaResponse:
    return repo.create(payload.model_dump())


@router.get("/{persona_id}", response_model=PersonaResponse)
def get_persona(
    persona_id: uuid.UUID, repo: PersonaRepository = Depends(get_persona_repository)
) -> PersonaResponse:
    persona = repo.get_by_id(persona_id)
    if persona is None:
        raise NotFoundError("Persona", str(persona_id))
    return persona


@router.patch("/{persona_id}", response_model=PersonaResponse)
def update_persona(
    persona_id: uuid.UUID,
    payload: PersonaUpdateRequest,
    repo: PersonaRepository = Depends(get_persona_repository),
) -> PersonaResponse:
    persona = repo.get_by_id(persona_id)
    if persona is None:
        raise NotFoundError("Persona", str(persona_id))
    return repo.update(persona, payload.model_dump(exclude_unset=True))


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    persona_id: uuid.UUID, repo: PersonaRepository = Depends(get_persona_repository)
) -> None:
    persona = repo.get_by_id(persona_id)
    if persona is None:
        raise NotFoundError("Persona", str(persona_id))
    repo.delete(persona)
