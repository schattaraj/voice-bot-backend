"""Tests for the LLM abstraction: provider adapters, error wrapping,
interchangeability, and the FastAPI dependency-injection wiring."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from anthropic import AnthropicError
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from openai import OpenAIError

from app.config.settings import Settings
from app.core.dependencies import get_llm_service
from app.schemas.llm import LLMMessage, LLMRequest, LLMResponse, LLMRole
from app.services.llm import LLMService, LLMServiceError, build_llm_service
from app.services.llm.anthropic_provider import AnthropicLLMService
from app.services.llm.openai_provider import OpenAILLMService

REQUEST = LLMRequest(
    system_prompt="You are a helpful test persona.",
    messages=[LLMMessage(role=LLMRole.USER, content="Hi there")],
)


def _fake_anthropic_message():
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Hello from Claude")],
        model="claude-sonnet-4-5-20250929",
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=12, output_tokens=8),
    )


def _fake_openai_completion():
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content="Hello from GPT"), finish_reason="stop")
        ],
        model="gpt-4o",
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=6),
    )


async def test_anthropic_provider_maps_response_correctly():
    service = AnthropicLLMService(api_key="test-key", model="claude-sonnet-4-5-20250929")
    service._client.messages.create = AsyncMock(return_value=_fake_anthropic_message())

    response = await service.complete(REQUEST)

    assert isinstance(response, LLMResponse)
    assert response.content == "Hello from Claude"
    assert response.provider == "anthropic"
    assert response.model == "claude-sonnet-4-5-20250929"
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 8
    assert response.stop_reason == "end_turn"


async def test_openai_provider_maps_response_correctly():
    service = OpenAILLMService(api_key="test-key", model="gpt-4o")
    service.client.chat.completions.create = AsyncMock(return_value=_fake_openai_completion())

    response = await service.complete(REQUEST)

    assert isinstance(response, LLMResponse)
    assert response.content == "Hello from GPT"
    assert response.provider == "openai"
    assert response.model == "gpt-4o"
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 6
    assert response.stop_reason == "stop"


async def test_openai_provider_folds_system_prompt_into_messages():
    service = OpenAILLMService(api_key="test-key", model="gpt-4o")
    mock_create = AsyncMock(return_value=_fake_openai_completion())
    service.client.chat.completions.create = mock_create

    await service.complete(REQUEST)

    sent_messages = mock_create.call_args.kwargs["messages"]
    assert sent_messages[0] == {"role": "system", "content": REQUEST.system_prompt}
    assert sent_messages[1] == {"role": "user", "content": "Hi there"}


async def test_anthropic_errors_are_wrapped_in_llm_service_error():
    service = AnthropicLLMService(api_key="test-key", model="claude-sonnet-4-5-20250929")
    service._client.messages.create = AsyncMock(side_effect=AnthropicError("rate limited"))

    try:
        await service.complete(REQUEST)
        assert False, "expected LLMServiceError"
    except LLMServiceError:
        pass


async def test_openai_errors_are_wrapped_in_llm_service_error():
    service = OpenAILLMService(api_key="test-key", model="gpt-4o")
    service.client.chat.completions.create = AsyncMock(side_effect=OpenAIError("rate limited"))

    try:
        await service.complete(REQUEST)
        assert False, "expected LLMServiceError"
    except LLMServiceError:
        pass


def test_both_providers_satisfy_the_llm_service_interface():
    assert isinstance(AnthropicLLMService(api_key="k", model="m"), LLMService)
    assert isinstance(OpenAILLMService(api_key="k", model="m"), LLMService)


async def test_calling_code_only_needs_the_llm_service_type():
    """Proves 'the rest of the application should not know which provider is
    used': the exact same function, typed only against LLMService, works
    identically against both concrete providers."""

    async def ask_persona(service: LLMService, request: LLMRequest) -> str:
        response = await service.complete(request)
        return response.content

    anthropic_service = AnthropicLLMService(api_key="k", model="m")
    anthropic_service._client.messages.create = AsyncMock(return_value=_fake_anthropic_message())

    openai_service = OpenAILLMService(api_key="k", model="m")
    openai_service.client.chat.completions.create = AsyncMock(return_value=_fake_openai_completion())

    assert await ask_persona(anthropic_service, REQUEST) == "Hello from Claude"
    assert await ask_persona(openai_service, REQUEST) == "Hello from GPT"


def test_factory_selects_provider_from_settings():
    anthropic_settings = Settings(llm_provider="anthropic", anthropic_api_key="k", anthropic_model="m")
    openai_settings = Settings(llm_provider="openai", openai_api_key="k", openai_model="m")

    assert isinstance(build_llm_service(anthropic_settings), AnthropicLLMService)
    assert isinstance(build_llm_service(openai_settings), OpenAILLMService)


def test_dependency_injection_is_overridable_in_a_real_fastapi_app():
    """Proves get_llm_service() is genuine FastAPI DI, not just a plain
    function call: a route depending on it via Depends() picks up an
    overridden fake implementation without any route code changing."""

    app = FastAPI()

    @app.post("/ask")
    async def ask(service: LLMService = Depends(get_llm_service)):
        response = await service.complete(REQUEST)
        return {"content": response.content, "provider": response.provider}

    class FakeLLMService(LLMService):
        @property
        def provider_name(self) -> str:
            return "fake"

        async def complete(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                content="canned response",
                provider="fake",
                model="fake-model",
                usage={"input_tokens": 1, "output_tokens": 1},
            )

    app.dependency_overrides[get_llm_service] = lambda: FakeLLMService()
    client = TestClient(app)

    result = client.post("/ask").json()

    assert result == {"content": "canned response", "provider": "fake"}
