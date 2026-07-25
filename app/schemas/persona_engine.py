"""Structured input/output contracts for the deterministic Persona Engine.

See app.services.persona_engine for the generation logic. Kept separate
from a future schemas/persona.py (the persisted-Persona API contract, once
that's implemented): this engine's output is a richer, roleplay-ready
profile — a name, communication style, resistance posture, opening line —
not necessarily the same shape as a database row.
"""

from pydantic import BaseModel, Field


class PersonaEngineInput(BaseModel):
    """Raw configuration a caller supplies to generate a persona."""

    industry: str
    company_size: str
    personality: str
    difficulty: str
    pain_points: list[str] = Field(default_factory=list)
    budget: str
    competitor: str
    objections: list[str] = Field(default_factory=list)


class ResistanceProfile(BaseModel):
    """How hard this persona pushes back during the call, derived from difficulty."""

    level: str
    description: str


class EngineeredPersona(BaseModel):
    """The structured Persona object returned by PersonaEngine.generate()."""

    name: str
    industry: str
    company_size: str
    personality: str
    difficulty: str
    pain_points: list[str]
    budget: str
    competitor: str
    objections: list[str]
    communication_style: str
    resistance: ResistanceProfile
    opening_line: str
