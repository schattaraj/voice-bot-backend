"""Data-access layer for Persona.

Plain class, not an ABC + implementation — unlike services/llm or
services/voice, there's exactly one storage technology in play (SQLAlchemy
against the configured database), so there's no alternate implementation
to swap in. The Repository pattern itself is the abstraction that keeps
SQL/session handling out of routers.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import PersonaDifficulty
from app.models.persona import Persona


class PersonaRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Persona]:
        return list(self._db.query(Persona).order_by(Persona.created_at.desc()).all())

    def get_by_id(self, persona_id: uuid.UUID) -> Persona | None:
        return self._db.get(Persona, persona_id)

    def create(self, data: dict[str, Any]) -> Persona:
        persona = Persona(
            industry=data["industry"],
            customer_personality=data["customer_personality"],
            difficulty=PersonaDifficulty(data["difficulty"]),
            company_size=data["company_size"],
            decision_maker_role=data["decision_maker_role"],
            budget=data["budget"],
            pain_points=data["pain_points"],
            competitors=data["competitors"],
            possible_objections=data["possible_objections"],
        )
        self._db.add(persona)
        self._db.commit()
        self._db.refresh(persona)
        return persona

    def update(self, persona: Persona, data: dict[str, Any]) -> Persona:
        for field, value in data.items():
            if field == "difficulty":
                value = PersonaDifficulty(value)
            setattr(persona, field, value)
        self._db.commit()
        self._db.refresh(persona)
        return persona

    def delete(self, persona: Persona) -> None:
        self._db.delete(persona)
        self._db.commit()
