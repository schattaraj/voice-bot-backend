"""Enums backing closed-set columns in the ORM models.

Only fields that are genuinely closed sets on the frontend too (a literal
union type, not just a configurable list of options) get a real DB enum
here — see the Step 12 design notes for why the other "dropdown" fields on
Persona (industry, company size, etc.) stay as plain strings instead.
"""

import enum


class PersonaDifficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SessionStatus(str, enum.Enum):
    IDLE = "idle"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"


class MessageSpeaker(str, enum.Enum):
    REP = "rep"
    AI_BUYER = "ai-buyer"
