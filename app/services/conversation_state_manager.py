"""Conversation State Manager.

Tracks stage, interest level, objections (raised/resolved), sentiment,
products discussed, buying signals, and the next expected action as a
roleplay call progresses, one transcript turn at a time.

Split into an abstract contract (ConversationStateManager) and one concrete
implementation (RuleBasedConversationStateManager) on purpose: calling code
should only ever depend on the ABC, never on the concrete class, so a
future implementation — an LLM-based classifier, a trained model, a real
finite-state-machine library — can replace RuleBasedConversationStateManager
entirely without any caller changing. Swap what `conversation_state_manager`
points to at the bottom of this file, and every consumer picks it up.
"""

import re
from abc import ABC, abstractmethod

from app.schemas.conversation import (
    ConversationStage,
    ConversationState,
    CustomerSentiment,
    NextExpectedAction,
)
from app.schemas.persona_engine import EngineeredPersona
from app.schemas.transcript import TranscriptTurn


class ConversationStateManager(ABC):
    """Abstract contract for turn-by-turn conversation state tracking.

    A pure state-machine shape: an initial state, a transition function,
    and a terminal transition. Implementations must be side-effect free —
    given the same (state, turn, persona), update() must always return the
    same next state — so callers can reason about state changes the same
    way they reason about the rest of this codebase's deterministic
    services (Persona Engine, Prompt Builder).
    """

    @abstractmethod
    def initial_state(self) -> ConversationState:
        """The state a brand-new conversation starts in."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        state: ConversationState,
        turn: TranscriptTurn,
        persona: EngineeredPersona,
    ) -> ConversationState:
        """Given the current state and a new transcript turn, returns the next state.

        Must not mutate `state` in place — return a new ConversationState.
        """
        raise NotImplementedError

    @abstractmethod
    def end(self, state: ConversationState) -> ConversationState:
        """Transitions a state to its terminal (call-ended) form."""
        raise NotImplementedError


_STOPWORDS = {
    "a", "an", "the", "is", "are", "to", "of", "in", "with", "for", "on", "we", "i",
    "our", "your", "this", "that", "already", "and", "or", "it", "be", "have", "has",
}  # fmt: skip


class RuleBasedConversationStateManager(ConversationStateManager):
    """Deterministic, keyword-heuristic implementation.

    Intentionally simple: this exists to satisfy the
    ConversationStateManager contract with a working default, not to be a
    sophisticated NLU system. No LLM calls, no randomness — every heuristic
    below is a plain keyword/overlap check, which is what makes this safe
    to unit test with fixed expected outputs.
    """

    _POSITIVE_KEYWORDS = (
        "great", "interesting", "like that", "makes sense", "helpful", "sounds good",
    )  # fmt: skip
    _NEGATIVE_KEYWORDS = (
        "expensive", "not sure", "don't think", "too much", "not interested", "no thanks",
    )  # fmt: skip
    _BUYING_SIGNAL_KEYWORDS = (
        "pricing", "price", "cost", "timeline", "contract", "trial", "demo",
        "next steps", "when can we start",
    )  # fmt: skip
    _PRODUCT_KEYWORDS = (
        "platform", "product", "solution", "dashboard", "integration", "feature", "tool",
    )  # fmt: skip

    def initial_state(self) -> ConversationState:
        return ConversationState()

    def update(
        self,
        state: ConversationState,
        turn: TranscriptTurn,
        persona: EngineeredPersona,
    ) -> ConversationState:
        text = turn.text.lower()
        turn_count = state.turn_count + 1

        objections_raised = self._track_objections_raised(state, persona, text)
        resolved_objections = self._track_objections_resolved(state, turn, objections_raised, text)
        sentiment = self._detect_sentiment(state, turn, text)
        buying_signals = self._collect_matches(state.buying_signals, self._BUYING_SIGNAL_KEYWORDS, text)
        products_discussed = self._collect_matches(state.products_discussed, self._PRODUCT_KEYWORDS, text)
        interest_level = self._update_interest_level(state, turn, text)

        unresolved = [o for o in objections_raised if o not in resolved_objections]
        stage = self._next_stage(state.stage, turn_count, unresolved, buying_signals)
        next_action = self._next_expected_action(stage, unresolved, buying_signals)

        return state.model_copy(
            update={
                "turn_count": turn_count,
                "stage": stage,
                "interest_level": interest_level,
                "objections_raised": objections_raised,
                "resolved_objections": resolved_objections,
                "customer_sentiment": sentiment,
                "products_discussed": products_discussed,
                "buying_signals": buying_signals,
                "next_expected_action": next_action,
            }
        )

    def end(self, state: ConversationState) -> ConversationState:
        return state.model_copy(
            update={"stage": ConversationStage.ENDED, "next_expected_action": NextExpectedAction.CONTINUE_CONVERSATION}
        )

    # -- objection tracking --------------------------------------------

    def _track_objections_raised(
        self, state: ConversationState, persona: EngineeredPersona, text: str
    ) -> list[str]:
        objections_raised = list(state.objections_raised)
        for objection in persona.objections:
            if objection not in objections_raised and self._mentions(text, objection):
                objections_raised.append(objection)
        return objections_raised

    def _track_objections_resolved(
        self,
        state: ConversationState,
        turn: TranscriptTurn,
        objections_raised: list[str],
        text: str,
    ) -> list[str]:
        resolved_objections = list(state.resolved_objections)
        if turn.speaker != "rep":
            return resolved_objections
        # Heuristic: the rep responding with language that overlaps an
        # already-raised objection is treated as addressing it.
        for objection in objections_raised:
            if objection not in resolved_objections and self._mentions(text, objection):
                resolved_objections.append(objection)
        return resolved_objections

    @staticmethod
    def _significant_words(phrase: str) -> set[str]:
        return {w for w in re.findall(r"[a-z']+", phrase.lower()) if w not in _STOPWORDS and len(w) > 2}

    @classmethod
    def _mentions(cls, text: str, phrase: str) -> bool:
        words = cls._significant_words(phrase)
        if not words:
            return False
        matches = sum(1 for word in words if word in text)
        return (matches / len(words)) >= 0.5

    # -- sentiment / signals / products ---------------------------------

    @classmethod
    def _detect_sentiment(
        cls, state: ConversationState, turn: TranscriptTurn, text: str
    ) -> CustomerSentiment:
        if turn.speaker != "ai-buyer":
            return state.customer_sentiment
        positive_hits = sum(1 for kw in cls._POSITIVE_KEYWORDS if kw in text)
        negative_hits = sum(1 for kw in cls._NEGATIVE_KEYWORDS if kw in text)
        if positive_hits > negative_hits:
            return CustomerSentiment.POSITIVE
        if negative_hits > positive_hits:
            return CustomerSentiment.NEGATIVE
        return state.customer_sentiment

    @staticmethod
    def _collect_matches(existing: list[str], keywords: tuple[str, ...], text: str) -> list[str]:
        matches = list(existing)
        for keyword in keywords:
            if keyword in text and keyword not in matches:
                matches.append(keyword)
        return matches

    @classmethod
    def _update_interest_level(cls, state: ConversationState, turn: TranscriptTurn, text: str) -> int:
        if turn.speaker != "ai-buyer":
            return state.interest_level
        delta = 0
        if any(kw in text for kw in cls._POSITIVE_KEYWORDS):
            delta += 10
        if any(kw in text for kw in cls._NEGATIVE_KEYWORDS):
            delta -= 10
        if any(kw in text for kw in cls._BUYING_SIGNAL_KEYWORDS):
            delta += 5
        return max(0, min(100, state.interest_level + delta))

    # -- stage / next action ---------------------------------------------

    @staticmethod
    def _next_stage(
        current: ConversationStage,
        turn_count: int,
        unresolved_objections: list[str],
        buying_signals: list[str],
    ) -> ConversationStage:
        if current == ConversationStage.ENDED:
            return current
        if unresolved_objections:
            return ConversationStage.OBJECTION_HANDLING
        if buying_signals and current in (ConversationStage.PITCH, ConversationStage.OBJECTION_HANDLING):
            return ConversationStage.CLOSING
        if turn_count <= 2:
            return ConversationStage.OPENING
        if current == ConversationStage.OPENING:
            return ConversationStage.DISCOVERY
        if current == ConversationStage.DISCOVERY and turn_count >= 4:
            return ConversationStage.PITCH
        return current

    @staticmethod
    def _next_expected_action(
        stage: ConversationStage,
        unresolved_objections: list[str],
        buying_signals: list[str],
    ) -> NextExpectedAction:
        if unresolved_objections:
            return NextExpectedAction.ADDRESS_OBJECTION
        if stage == ConversationStage.CLOSING:
            return NextExpectedAction.PROPOSE_NEXT_STEPS
        if stage == ConversationStage.OPENING:
            return NextExpectedAction.BUILD_RAPPORT
        if stage == ConversationStage.DISCOVERY:
            return NextExpectedAction.ASK_DISCOVERY_QUESTION
        if stage == ConversationStage.PITCH:
            return NextExpectedAction.PRESENT_VALUE
        return NextExpectedAction.CONTINUE_CONVERSATION


conversation_state_manager: ConversationStateManager = RuleBasedConversationStateManager()
