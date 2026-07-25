"""Tests for the Prompt Builder: structure, the in-character constraints,
transcript handling, and determinism."""

from app.schemas.conversation import ConversationState
from app.schemas.persona_engine import PersonaEngineInput
from app.schemas.transcript import TranscriptTurn
from app.services.persona_engine import persona_engine
from app.services.prompt_builder import PromptBuilder

BUILDER = PromptBuilder()

PERSONA = persona_engine.generate(
    PersonaEngineInput(
        industry="SaaS / Technology",
        company_size="51-200 employees",
        personality="Skeptical",
        difficulty="advanced",
        pain_points=["High operational costs"],
        budget="$25,000 - $100,000",
        competitor="Salesforce",
        objections=["Price is too high"],
    )
)

TRANSCRIPT = [
    TranscriptTurn(speaker="ai-buyer", text="Hello, this is Alicia.", timestamp_ms=0),
    TranscriptTurn(speaker="rep", text="Hi Alicia, thanks for taking the call.", timestamp_ms=3200),
]


def _build(state: ConversationState, transcript: list[TranscriptTurn] | None = None) -> str:
    return BUILDER.build_system_prompt(
        persona=PERSONA,
        conversation_state=state,
        transcript=transcript if transcript is not None else [],
    )


def test_prompt_is_deterministic():
    state = ConversationState(status="in-progress", turn_count=2, elapsed_seconds=45)
    first = _build(state, TRANSCRIPT)
    second = _build(state, TRANSCRIPT)
    assert first == second


def test_prompt_contains_all_modular_sections():
    prompt = _build(ConversationState(status="idle", turn_count=0, elapsed_seconds=0))
    for tag in (
        "persona_identity",
        "non_negotiable_rules",
        "response_style",
        "persona_context",
        "conversation_state",
        "conversation_history",
        "reminder",
    ):
        assert f"<{tag}>" in prompt
        assert f"</{tag}>" in prompt


def test_prompt_enforces_character_constraints():
    prompt = _build(ConversationState(status="in-progress", turn_count=1, elapsed_seconds=10))
    lowered = prompt.lower()
    assert "not an ai assistant" in lowered
    assert "never coach" in lowered
    assert "never break character" in lowered
    assert "reveal" in lowered  # instructions must not be revealed


def test_prompt_includes_persona_details():
    prompt = _build(ConversationState(status="in-progress", turn_count=1, elapsed_seconds=10))
    assert PERSONA.name in prompt
    assert PERSONA.industry in prompt
    assert PERSONA.competitor in prompt
    assert "High operational costs" in prompt
    assert "Price is too high" in prompt


def test_prompt_includes_transcript_when_present():
    prompt = _build(ConversationState(status="in-progress", turn_count=2, elapsed_seconds=10), TRANSCRIPT)
    assert "Hello, this is Alicia." in prompt
    assert "Salesperson: Hi Alicia, thanks for taking the call." in prompt


def test_prompt_handles_empty_transcript():
    prompt = _build(ConversationState(status="idle", turn_count=0, elapsed_seconds=0), [])
    assert "No prior messages" in prompt


def test_conversation_state_guidance_varies_by_phase():
    opening = _build(ConversationState(status="idle", turn_count=0, elapsed_seconds=0))
    ongoing = _build(ConversationState(status="in-progress", turn_count=3, elapsed_seconds=60))
    closing = _build(ConversationState(status="completed", turn_count=10, elapsed_seconds=300))

    assert "just started" in opening
    assert "in progress" in ongoing
    assert "wrapping up" in closing
    assert opening != ongoing != closing
