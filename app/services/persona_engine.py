"""Deterministic Persona Engine.

Turns raw persona configuration into a structured, roleplay-ready profile:
a name, a communication style, a resistance posture, and an opening line.
Pure rule-based logic only — dictionary lookups and string templating, no
LLM calls and no randomness. The same input always produces the exact same
output, which is what makes this safe to unit test with fixed expected
values (see tests/test_persona_engine.py) and safe to call from
request-handling code without worrying about latency, cost, or
nondeterminism. A later step is expected to feed this structured object
into an actual LLM prompt (see prompts/) — this engine only prepares the
data, it never talks to a model itself.
"""

import hashlib

from app.schemas.persona_engine import EngineeredPersona, PersonaEngineInput, ResistanceProfile

_PERSONA_NAME_POOL: tuple[str, ...] = (
    "Jordan Blake",
    "Priya Nair",
    "Marcus Lee",
    "Alicia Gomez",
    "Sam Whitfield",
    "Dana Ellsworth",
    "Chidi Okafor",
    "Elena Vasquez",
)

_COMMUNICATION_STYLES: dict[str, str] = {
    "analytical": (
        "Data-driven and methodical. Wants numbers, case studies, and proof before "
        "committing to anything; asks precise, detail-oriented questions."
    ),
    "amiable": (
        "Warm and relationship-focused. Responds well to rapport-building but avoids "
        "confrontation, so objections tend to surface indirectly."
    ),
    "driver": (
        "Direct and results-oriented. Wants the bottom line fast, gets impatient with "
        "long explanations, and values confidence over politeness."
    ),
    "expressive": (
        "Enthusiastic and story-driven. Engages readily but can be easily distracted; "
        "needs the conversation anchored back to concrete next steps."
    ),
    "skeptical": (
        "Guarded by default. Assumes a sales pitch is coming and pushes back early to "
        "test how the rep handles pressure."
    ),
}
_DEFAULT_COMMUNICATION_STYLE = (
    "Engages on their own terms and forms opinions as the conversation develops, "
    "without a strongly telegraphed default stance."
)

_RESISTANCE_BY_DIFFICULTY: dict[str, ResistanceProfile] = {
    "beginner": ResistanceProfile(
        level="low",
        description=(
            "Open to the conversation, asks straightforward questions, and doesn't "
            "push back hard on price or claims."
        ),
    ),
    "intermediate": ResistanceProfile(
        level="medium",
        description=(
            "Asks pointed follow-up questions, compares against alternatives, and "
            "needs solid justification before moving forward."
        ),
    ),
    "advanced": ResistanceProfile(
        level="high",
        description=(
            "Skeptical by default, challenges claims directly, and raises objections "
            "early and often."
        ),
    ),
}
_DEFAULT_RESISTANCE = ResistanceProfile(
    level="medium",
    description="Engages with reasonable scrutiny; pushes back when unconvinced.",
)


class PersonaEngine:
    """Deterministically builds a structured, roleplay-ready Persona profile."""

    def generate(self, data: PersonaEngineInput) -> EngineeredPersona:
        name = self._pick_name(data)
        communication_style = _COMMUNICATION_STYLES.get(
            data.personality.strip().lower(), _DEFAULT_COMMUNICATION_STYLE
        )
        resistance = _RESISTANCE_BY_DIFFICULTY.get(
            data.difficulty.strip().lower(), _DEFAULT_RESISTANCE
        )

        return EngineeredPersona(
            name=name,
            industry=data.industry,
            company_size=data.company_size,
            personality=data.personality,
            difficulty=data.difficulty,
            pain_points=list(data.pain_points),
            budget=data.budget,
            competitor=data.competitor,
            objections=list(data.objections),
            communication_style=communication_style,
            resistance=resistance,
            opening_line=self._build_opening_line(name, data),
        )

    @staticmethod
    def _pick_name(data: PersonaEngineInput) -> str:
        """Selects a name deterministically from the input.

        Same inputs always resolve to the same name; personas that differ
        by even one field are likely (not guaranteed — it's a fixed-size
        pool) to land on a different one. Uses a hash rather than
        `random` specifically because `random` without a fixed seed is
        nondeterministic across processes/runs.
        """
        fingerprint = "|".join(
            [
                data.industry,
                data.company_size,
                data.personality,
                data.difficulty,
                data.budget,
                data.competitor,
                ",".join(sorted(data.pain_points)),
                ",".join(sorted(data.objections)),
            ]
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        index = int(digest, 16) % len(_PERSONA_NAME_POOL)
        return _PERSONA_NAME_POOL[index]

    @staticmethod
    def _build_opening_line(name: str, data: PersonaEngineInput) -> str:
        first_name = name.split(" ")[0]
        return (
            f"Hi, this is {first_name}. I run a {data.company_size} team in "
            f"{data.industry}, and we're currently using {data.competitor}. "
            "You've got a few minutes — what makes this worth my time?"
        )


persona_engine = PersonaEngine()
