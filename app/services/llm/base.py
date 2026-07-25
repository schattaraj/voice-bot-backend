"""Abstract LLM Service contract.

Every provider adapter (AnthropicLLMService, OpenAILLMService, ...)
satisfies this same interface, so the rest of the application depends only
on LLMService — never on a concrete provider class — and never needs to
know whether a given call went to Claude or GPT.
"""

from abc import ABC, abstractmethod

from app.schemas.llm import LLMRequest, LLMResponse


class LLMServiceError(Exception):
    """Raised when a provider call fails.

    Wraps the provider-specific SDK exception so callers only ever need to
    catch one error type, regardless of which provider is configured.
    """


class LLMService(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier for this provider, e.g. "anthropic" or "openai"."""
        raise NotImplementedError

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Sends a completion request and returns a structured response.

        Must raise LLMServiceError (never a provider-specific exception)
        on failure.
        """
        raise NotImplementedError
