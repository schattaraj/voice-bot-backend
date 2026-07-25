"""Translates a persisted Persona (DB model) into the Persona Engine's
input contract.

Neither existing module wants this logic: persona_engine.py is pure
generation with no DB knowledge, and persona_repository.py has no
schema-translation responsibility (see both modules' docstrings) — this is
a genuinely separate concern, so it gets its own module.
"""

from app.models.persona import Persona
from app.schemas.persona_engine import PersonaEngineInput


def build_persona_engine_input(persona: Persona) -> PersonaEngineInput:
    # PersonaEngineInput wants a single competitor; the DB model stores a
    # list (a persona can list several). The first one is as good a choice
    # as any for "who the AI buyer currently uses" — falling back to a
    # generic label rather than crashing if the list is empty.
    competitor = persona.competitors[0] if persona.competitors else "a competitor"

    return PersonaEngineInput(
        industry=persona.industry,
        company_size=persona.company_size,
        personality=persona.customer_personality,
        difficulty=persona.difficulty.value,
        pain_points=list(persona.pain_points),
        budget=persona.budget,
        competitor=competitor,
        objections=list(persona.possible_objections),
    )
