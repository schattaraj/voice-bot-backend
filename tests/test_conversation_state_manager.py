"""Tests for the Conversation State Manager: tracking behavior, and proof
that the abstract interface is actually swappable."""

from app.schemas.conversation import (
    ConversationStage,
    ConversationState,
    CustomerSentiment,
    NextExpectedAction,
)
from app.schemas.persona_engine import PersonaEngineInput
from app.schemas.transcript import TranscriptTurn
from app.services.conversation_state_manager import (
    ConversationStateManager,
    RuleBasedConversationStateManager,
)
from app.services.persona_engine import persona_engine

MANAGER = RuleBasedConversationStateManager()

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


def _turn(speaker: str, text: str, timestamp_ms: int = 0) -> TranscriptTurn:
    return TranscriptTurn(speaker=speaker, text=text, timestamp_ms=timestamp_ms)


def test_initial_state_has_sensible_defaults():
    state = MANAGER.initial_state()
    assert state.stage == ConversationStage.OPENING
    assert state.interest_level == 50
    assert state.customer_sentiment == CustomerSentiment.NEUTRAL
    assert state.objections_raised == []
    assert state.next_expected_action == NextExpectedAction.BUILD_RAPPORT


def test_turn_count_increments_on_every_update():
    state = MANAGER.initial_state()
    state = MANAGER.update(state, _turn("rep", "Hi, thanks for taking my call."), PERSONA)
    assert state.turn_count == 1
    state = MANAGER.update(state, _turn("ai-buyer", "Sure, go ahead."), PERSONA)
    assert state.turn_count == 2


def test_detects_a_known_objection_and_routes_to_objection_handling():
    state = ConversationState(turn_count=3, stage=ConversationStage.DISCOVERY)
    state = MANAGER.update(
        state, _turn("ai-buyer", "Look, the price is too high for our budget."), PERSONA
    )
    assert "Price is too high" in state.objections_raised
    assert state.stage == ConversationStage.OBJECTION_HANDLING
    assert state.next_expected_action == NextExpectedAction.ADDRESS_OBJECTION


def test_rep_can_resolve_a_raised_objection():
    state = ConversationState(turn_count=3, stage=ConversationStage.DISCOVERY)
    state = MANAGER.update(
        state, _turn("ai-buyer", "Look, the price is too high for our budget."), PERSONA
    )
    state = MANAGER.update(
        state,
        _turn("rep", "I hear that the price feels too high right now, but let's look at ROI."),
        PERSONA,
    )
    assert "Price is too high" in state.resolved_objections
    assert state.next_expected_action != NextExpectedAction.ADDRESS_OBJECTION


def test_sentiment_only_reacts_to_the_buyer_not_the_rep():
    state = MANAGER.initial_state()
    # Rep saying something upbeat should not move the *customer's* sentiment.
    state = MANAGER.update(state, _turn("rep", "This sounds good for your team!"), PERSONA)
    assert state.customer_sentiment == CustomerSentiment.NEUTRAL

    state = MANAGER.update(state, _turn("ai-buyer", "Okay, that sounds good, tell me more."), PERSONA)
    assert state.customer_sentiment == CustomerSentiment.POSITIVE


def test_buying_signals_and_interest_level_increase_from_buyer_language():
    state = MANAGER.initial_state()
    state = MANAGER.update(
        state, _turn("ai-buyer", "That sounds good — can you tell me more about pricing?"), PERSONA
    )
    assert "pricing" in state.buying_signals
    assert state.interest_level > 50


def test_products_discussed_are_tracked():
    state = MANAGER.initial_state()
    state = MANAGER.update(
        state,
        _turn("rep", "Let me show you our dashboard and how the platform fits your workflow."),
        PERSONA,
    )
    assert "dashboard" in state.products_discussed
    assert "platform" in state.products_discussed


def test_end_transitions_to_ended_stage():
    state = MANAGER.initial_state()
    ended = MANAGER.end(state)
    assert ended.stage == ConversationStage.ENDED


def test_update_is_deterministic():
    state = ConversationState(turn_count=3, stage=ConversationStage.DISCOVERY)
    turn = _turn("ai-buyer", "The price is too high and I'm not sure this is worth it.")
    first = MANAGER.update(state, turn, PERSONA)
    second = MANAGER.update(state, turn, PERSONA)
    assert first == second


def test_update_does_not_mutate_the_input_state():
    state = MANAGER.initial_state()
    MANAGER.update(state, _turn("ai-buyer", "The price is too high."), PERSONA)
    assert state.turn_count == 0
    assert state.objections_raised == []


def test_an_alternate_implementation_satisfies_the_same_interface():
    """Proves the ABC is actually swappable, not just documented as such."""

    class AlwaysOpeningStateManager(ConversationStateManager):
        def initial_state(self) -> ConversationState:
            return ConversationState()

        def update(self, state, turn, persona) -> ConversationState:
            return state.model_copy(update={"turn_count": state.turn_count + 1})

        def end(self, state) -> ConversationState:
            return state.model_copy(update={"stage": ConversationStage.ENDED})

    def run_one_turn(manager: ConversationStateManager) -> ConversationState:
        state = manager.initial_state()
        return manager.update(state, _turn("rep", "Hello!"), PERSONA)

    rule_based_result = run_one_turn(RuleBasedConversationStateManager())
    alternate_result = run_one_turn(AlwaysOpeningStateManager())

    assert isinstance(rule_based_result, ConversationState)
    assert isinstance(alternate_result, ConversationState)
    assert rule_based_result.turn_count == alternate_result.turn_count == 1
