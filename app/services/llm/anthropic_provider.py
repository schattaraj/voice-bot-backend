"""Anthropic Claude provider adapter."""

from anthropic import AnthropicError, AsyncAnthropic

from app.schemas.llm import LLMRequest, LLMResponse, LLMUsage
from app.services.llm.base import LLMService, LLMServiceError


class AnthropicLLMService(LLMService):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            message = await self._client.messages.create(
                model=self._model,
                system=request.system_prompt,
                messages=[
                    {"role": turn.role.value, "content": turn.content} for turn in request.messages
                ],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        except AnthropicError as error:
            raise LLMServiceError(f"Anthropic request failed: {error}") from error

        text = "".join(block.text for block in message.content if block.type == "text")

        return LLMResponse(
            content=text,
            provider=self.provider_name,
            model=message.model,
            usage=LLMUsage(
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens,
            ),
            stop_reason=message.stop_reason,
        )
