"""LLM abstraction: a provider-agnostic interface over Anthropic Claude and
OpenAI, so the rest of the application never depends on a specific
provider's SDK.

Import LLMService (the ABC) and LLMServiceError to depend on this layer.
Concrete provider classes and build_llm_service() exist for
core.dependencies and tests — application code should never need them
directly.
"""

from app.services.llm.base import LLMService, LLMServiceError
from app.services.llm.factory import build_llm_service

__all__ = ["LLMService", "LLMServiceError", "build_llm_service"]
