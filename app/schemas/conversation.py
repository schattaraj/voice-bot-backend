"""Conversation-state contract for prompt building and state tracking.

Deliberately re-declares status/stage/sentiment/action values instead of
importing from models/enums.py — schemas/ should stay free to evolve
without depending on the ORM layer. See the equivalent note there.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

ConversationStatus = Literal["idle", "in-progress", "completed"]


class ConversationStage(str, Enum):
    OPENING = "opening"
    DISCOVERY = "discovery"
    PITCH = "pitch"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    ENDED = "ended"


class CustomerSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class NextExpectedAction(str, Enum):
    BUILD_RAPPORT = "build_rapport"
    ASK_DISCOVERY_QUESTION = "ask_discovery_question"
    PRESENT_VALUE = "present_value"
    ADDRESS_OBJECTION = "address_objection"
    PROPOSE_NEXT_STEPS = "propose_next_steps"
    CONTINUE_CONVERSATION = "continue_conversation"


class ConversationState(BaseModel):
    """Everything tracked about a roleplay call as it progresses.

    Produced and evolved by a ConversationStateManager implementation (see
    app.services.conversation_state_manager) — this model is just the data
    shape, deliberately free of any update logic itself, so a future state
    machine implementation only needs to produce/consume this same shape.
    """

    # Session-level (Step 14)
    status: ConversationStatus = "idle"
    turn_count: int = 0
    elapsed_seconds: int = 0

    # Conversation-tracking (Step 15)
    stage: ConversationStage = ConversationStage.OPENING
    interest_level: int = Field(default=50, ge=0, le=100)
    objections_raised: list[str] = Field(default_factory=list)
    resolved_objections: list[str] = Field(default_factory=list)
    customer_sentiment: CustomerSentiment = CustomerSentiment.NEUTRAL
    products_discussed: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    next_expected_action: NextExpectedAction = NextExpectedAction.BUILD_RAPPORT
