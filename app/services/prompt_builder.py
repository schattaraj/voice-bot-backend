"""Prompt Builder service.

Assembles a complete Claude system prompt from Persona + ConversationState +
previous transcript, by composing the modular section templates in
app.prompts. This service owns section *ordering* and *composition* only —
all actual prompt text lives in app.prompts, so those sections stay
independently reusable (e.g. by a future evaluation prompt) and
independently testable.

Section order is deliberate:
1. Identity — who the model is playing, established first.
2. Character rules — the hard constraints, placed early for primacy.
3. Response style — how to speak, not just who to be.
4. Persona context — the details that inform *what* the persona says.
5. Conversation state — situational guidance for right now.
6. Conversation history — what's actually been said so far.
7. Closing reminder — the constraints again, placed last for recency,
   right before the model generates its next turn.
"""

from app.prompts.character_rules import (
    render_character_rules,
    render_closing_reminder,
    render_response_style,
)
from app.prompts.conversation_prompts import (
    render_conversation_state_section,
    render_transcript_section,
)
from app.prompts.persona_prompts import render_context_section, render_identity_section
from app.schemas.conversation import ConversationState
from app.schemas.persona_engine import EngineeredPersona
from app.schemas.transcript import TranscriptTurn


class PromptBuilder:
    """Builds the complete Claude system prompt for one roleplay turn."""

    def build_system_prompt(
        self,
        *,
        persona: EngineeredPersona,
        conversation_state: ConversationState,
        transcript: list[TranscriptTurn],
    ) -> str:
        sections = [
            render_identity_section(persona),
            render_character_rules(),
            render_response_style(),
            render_context_section(persona),
            render_conversation_state_section(conversation_state),
            render_transcript_section(transcript),
            render_closing_reminder(persona),
        ]
        return "\n\n".join(sections)


prompt_builder = PromptBuilder()
