"""Scripted mock conversation used to simulate a live roleplay call over
the WebSocket.

No LLM or voice provider is called anywhere in this module — per this
step's scope ("Do not integrate voice yet. Use mock messages."), the
persona is generated once by the (deterministic, LLM-free) Persona Engine
from Step 13, and the transcript is a fixed script, matching the same
"Alicia / Salesforce" narrative already used in the frontend's mock data
and Step 13/14/15's tests.
"""

from app.schemas.persona_engine import PersonaEngineInput
from app.schemas.transcript import TranscriptTurn

MOCK_PERSONA_INPUT = PersonaEngineInput(
    industry="SaaS / Technology",
    company_size="51-200 employees",
    personality="Skeptical",
    difficulty="advanced",
    pain_points=["High operational costs", "Disconnected tools / data silos"],
    budget="$25,000 - $100,000",
    competitor="Salesforce",
    objections=["Price is too high", "Happy with current vendor"],
)

MOCK_TRANSCRIPT: list[TranscriptTurn] = [
    TranscriptTurn(
        speaker="ai-buyer",
        text="Hello, this is Alicia. I only have a few minutes.",
        timestamp_ms=0,
    ),
    TranscriptTurn(
        speaker="rep",
        text="Thanks for taking the call, Jordan sent me over. I'll keep it brief.",
        timestamp_ms=3200,
    ),
    TranscriptTurn(
        speaker="ai-buyer",
        text="Okay. We're already using Salesforce for that, honestly.",
        timestamp_ms=6400,
    ),
    TranscriptTurn(
        speaker="rep",
        text="Got it — a lot of our customers came from Salesforce. Can I ask about your reporting setup?",
        timestamp_ms=9600,
    ),
    TranscriptTurn(
        speaker="ai-buyer",
        text="Sure, it's fine, but the price is too high for anything new right now.",
        timestamp_ms=12800,
    ),
]
