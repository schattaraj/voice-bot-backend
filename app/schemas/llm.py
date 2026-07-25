"""Structured, provider-agnostic contracts for the LLM abstraction.

Every provider adapter (see app.services.llm) accepts an LLMRequest and
returns an LLMResponse — nothing about a specific provider's request or
response shape leaks past that layer.
"""

from enum import Enum

from pydantic import BaseModel, Field


class LLMRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    role: LLMRole
    content: str


class LLMRequest(BaseModel):
    """A provider-agnostic completion request.

    `system_prompt` and `messages` are kept separate here, matching
    Anthropic's native shape, even though OpenAI's API wants the system
    prompt folded into the messages list as a role="system" entry — that
    folding is exactly the kind of provider-specific adaptation this
    abstraction exists to hide (see services/llm/openai_provider.py).
    """

    system_prompt: str
    messages: list[LLMMessage] = Field(default_factory=list)
    max_tokens: int = 1024
    temperature: float = 1.0


class LLMUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class LLMResponse(BaseModel):
    """The structured response every provider adapter returns, regardless
    of which provider actually served the request."""

    content: str
    provider: str
    model: str
    usage: LLMUsage
    stop_reason: str | None = None
