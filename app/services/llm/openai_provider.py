"""OpenAI provider adapter."""

from openai import AsyncOpenAI, OpenAIError

from app.schemas.llm import LLMRequest, LLMResponse, LLMUsage
from app.services.llm.base import LLMService, LLMServiceError


class OpenAILLMService(LLMService):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Constructed lazily on first use.

        This SDK's client validates credentials at construction time,
        unlike Anthropic's (see anthropic_provider.py) — without this,
        simply selecting "openai" via settings with no key configured yet
        would crash immediately instead of failing only when a call is
        actually attempted, unlike every other provider in this codebase.
        """
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "openai"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # OpenAI has no separate system-prompt parameter — the abstraction
        # hides that by folding it into the messages list here, so callers
        # never need to know this provider works differently from Anthropic.
        messages = [{"role": "system", "content": request.system_prompt}] + [
            {"role": turn.role.value, "content": turn.content} for turn in request.messages
        ]

        try:
            completion = await self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        except OpenAIError as error:
            raise LLMServiceError(f"OpenAI request failed: {error}") from error

        choice = completion.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=completion.model,
            usage=LLMUsage(
                input_tokens=completion.usage.prompt_tokens,
                output_tokens=completion.usage.completion_tokens,
            ),
            stop_reason=choice.finish_reason,
        )
