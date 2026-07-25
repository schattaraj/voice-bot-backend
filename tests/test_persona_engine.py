"""Tests proving the Persona Engine is deterministic and rule-based."""

from app.schemas.persona_engine import PersonaEngineInput
from app.services.persona_engine import _PERSONA_NAME_POOL, PersonaEngine

ENGINE = PersonaEngine()

SAMPLE_INPUT = PersonaEngineInput(
    industry="SaaS / Technology",
    company_size="51-200 employees",
    personality="Analytical",
    difficulty="advanced",
    pain_points=["High operational costs", "Disconnected tools"],
    budget="$25,000 - $100,000",
    competitor="Salesforce",
    objections=["Price is too high"],
)


def test_same_input_produces_identical_output():
    first = ENGINE.generate(SAMPLE_INPUT)
    second = ENGINE.generate(SAMPLE_INPUT)
    assert first == second


def test_repeated_calls_across_instances_are_identical():
    # A fresh PersonaEngine() should behave identically to ENGINE — no
    # hidden per-instance state, no randomness seeded at construction time.
    assert PersonaEngine().generate(SAMPLE_INPUT) == PersonaEngine().generate(SAMPLE_INPUT)


def test_output_varies_with_input():
    other_input = SAMPLE_INPUT.model_copy(update={"industry": "Healthcare", "competitor": "HubSpot"})
    first = ENGINE.generate(SAMPLE_INPUT)
    second = ENGINE.generate(other_input)
    assert first.opening_line != second.opening_line


def test_known_personality_maps_to_expected_style():
    result = ENGINE.generate(SAMPLE_INPUT)
    assert "Data-driven" in result.communication_style


def test_known_difficulty_maps_to_expected_resistance():
    result = ENGINE.generate(SAMPLE_INPUT)
    assert result.resistance.level == "high"


def test_unknown_personality_and_difficulty_fall_back_gracefully():
    unusual_input = SAMPLE_INPUT.model_copy(update={"personality": "Mercurial", "difficulty": "nightmare"})
    result = ENGINE.generate(unusual_input)
    assert result.communication_style
    assert result.resistance.level == "medium"


def test_pain_points_and_objections_are_preserved_verbatim():
    result = ENGINE.generate(SAMPLE_INPUT)
    assert result.pain_points == SAMPLE_INPUT.pain_points
    assert result.objections == SAMPLE_INPUT.objections


def test_persona_name_comes_from_the_fixed_pool():
    result = ENGINE.generate(SAMPLE_INPUT)
    assert result.name in _PERSONA_NAME_POOL
