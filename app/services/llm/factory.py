"""Builds the configured LLMService implementation from settings.

This is the one place in the codebase that imports both provider classes —
everywhere else (including core/dependencies.py) only ever imports the
LLMService ABC.
"""

from app.config.settings import Settings
from app.services.llm.anthropic_provider import AnthropicLLMService
from app.services.llm.base import LLMService
from app.services.llm.openai_provider import OpenAILLMService


def build_llm_service(settings: Settings) -> LLMService:
    if settings.llm_provider == "anthropic":
        return AnthropicLLMService(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    if settings.llm_provider == "openai":
        return OpenAILLMService(api_key=settings.openai_api_key, model=settings.openai_model)
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
