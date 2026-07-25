"""LLM prompt templates for the AI buyer persona and evaluation calls.

Each module owns one section of a prompt and exposes plain functions that
take structured input (schemas/) and return a string. Nothing in here
calls a model — see app.services.prompt_builder for the service that
composes these sections into a complete system prompt.
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

__all__ = [
    "render_character_rules",
    "render_closing_reminder",
    "render_response_style",
    "render_conversation_state_section",
    "render_transcript_section",
    "render_context_section",
    "render_identity_section",
]
