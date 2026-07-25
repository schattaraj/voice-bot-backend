"""Persona-specific prompt sections: who the AI is playing and their situation.

Consumes an EngineeredPersona (app.services.persona_engine) — the same
deterministic profile built in Step 13 — so "the configured customer" the
model plays is exactly the object the Persona Engine produced, not a
separate ad hoc representation.
"""

from app.schemas.persona_engine import EngineeredPersona


def render_identity_section(persona: EngineeredPersona) -> str:
    return f"""<persona_identity>
You are {persona.name}, a decision-maker at a {persona.company_size} company in the
{persona.industry} industry. Your personality type is {persona.personality}.
</persona_identity>"""


def render_context_section(persona: EngineeredPersona) -> str:
    pain_points = "\n".join(f"- {point}" for point in persona.pain_points) or "- None specified"
    objections = "\n".join(f"- {objection}" for objection in persona.objections) or "- None specified"

    return f"""<persona_context>
Communication style: {persona.communication_style}
Resistance level: {persona.resistance.level} — {persona.resistance.description}
Budget available: {persona.budget}
Currently using: {persona.competitor}

Pain points you are experiencing:
{pain_points}

Objections you may raise during the call, when they naturally fit:
{objections}
</persona_context>"""
