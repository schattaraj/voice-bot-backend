"""Tests for the Voice Service abstraction: provider adapters (Deepgram
STT, ElevenLabs TTS, OpenAI Realtime), error wrapping, interchangeability,
and the FastAPI dependency-injection wiring."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from deepgram.core.api_error import ApiError as DeepgramApiError
from elevenlabs.core.api_error import ApiError as ElevenLabsApiError
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from openai import OpenAIError

from app.config.settings import Settings
from app.core.dependencies import get_realtime_voice_service
from app.schemas.voice import (
    AudioChunk,
    AudioEncoding,
    RealtimeEventType,
    RealtimeSessionConfig,
    SynthesisRequest,
)
from app.services.voice import (
    RealtimeVoiceService,
    SpeechToTextService,
    TextToSpeechService,
    VoiceServiceError,
    build_realtime_voice_service,
    build_speech_to_text_service,
    build_text_to_speech_service,
)
from app.services.voice.deepgram_provider import DeepgramSpeechToTextService
from app.services.voice.elevenlabs_provider import ElevenLabsTextToSpeechService
from app.services.voice.openai_realtime_provider import OpenAIRealtimeSession, OpenAIRealtimeVoiceService

AUDIO_IN = AudioChunk(data=b"fake-audio-bytes", encoding=AudioEncoding.PCM16)


# -- Deepgram STT ---------------------------------------------------------


def _fake_deepgram_response(transcript: str, confidence: float):
    alternative = SimpleNamespace(transcript=transcript, confidence=confidence)
    channel = SimpleNamespace(alternatives=[alternative])
    results = SimpleNamespace(channels=[channel])
    return SimpleNamespace(results=results)


async def test_deepgram_provider_maps_response_correctly():
    service = DeepgramSpeechToTextService(api_key="test-key")
    service._client.listen.v1.media.transcribe_file = AsyncMock(
        return_value=_fake_deepgram_response("hello there", 0.97)
    )

    result = await service.transcribe(AUDIO_IN)

    assert result.text == "hello there"
    assert result.confidence == 0.97
    assert result.is_final is True


async def test_deepgram_errors_are_wrapped():
    service = DeepgramSpeechToTextService(api_key="test-key")
    service._client.listen.v1.media.transcribe_file = AsyncMock(
        side_effect=DeepgramApiError(status_code=500, body="boom")
    )

    try:
        await service.transcribe(AUDIO_IN)
        assert False, "expected VoiceServiceError"
    except VoiceServiceError:
        pass


def test_deepgram_satisfies_speech_to_text_interface():
    assert isinstance(DeepgramSpeechToTextService(api_key="k"), SpeechToTextService)


# -- ElevenLabs TTS ---------------------------------------------------------


async def _fake_audio_stream():
    for piece in (b"chunk-1-", b"chunk-2-", b"chunk-3"):
        yield piece


async def test_elevenlabs_provider_joins_streamed_audio_chunks():
    service = ElevenLabsTextToSpeechService(api_key="test-key")
    service._client.text_to_speech.convert = MagicMock(return_value=_fake_audio_stream())

    result = await service.synthesize(SynthesisRequest(text="Hello there"))

    assert result.audio.data == b"chunk-1-chunk-2-chunk-3"
    assert result.audio.encoding == AudioEncoding.MP3


async def test_elevenlabs_errors_are_wrapped():
    service = ElevenLabsTextToSpeechService(api_key="test-key")

    def _raise(*args, **kwargs):
        raise ElevenLabsApiError(status_code=500, body="boom")

    service._client.text_to_speech.convert = _raise

    try:
        await service.synthesize(SynthesisRequest(text="Hello there"))
        assert False, "expected VoiceServiceError"
    except VoiceServiceError:
        pass


def test_elevenlabs_satisfies_text_to_speech_interface():
    assert isinstance(ElevenLabsTextToSpeechService(api_key="k"), TextToSpeechService)


# -- OpenAI Realtime ---------------------------------------------------------


class _FakeRealtimeConnection:
    def __init__(self, events: list[object]):
        self._events = list(events)
        self.sent: list[object] = []
        self.closed = False

    async def send(self, event):
        self.sent.append(event)

    async def recv(self):
        return self._events.pop(0)

    async def close(self):
        self.closed = True


async def test_realtime_session_maps_transcript_and_audio_events():
    connection = _FakeRealtimeConnection(
        [
            SimpleNamespace(type="conversation.item.input_audio_transcription.delta", delta="Hel"),
            SimpleNamespace(
                type="conversation.item.input_audio_transcription.completed", transcript="Hello"
            ),
            SimpleNamespace(type="response.text.delta", delta="Hi "),
            SimpleNamespace(type="response.audio.delta", delta="ZmFrZS1hdWRpbw=="),  # b"fake-audio"
            SimpleNamespace(type="response.done"),
        ]
    )
    session = OpenAIRealtimeSession(connection, output_encoding=AudioEncoding.PCM16)

    events = []
    async for event in session.events():
        events.append(event)
        if event.type == RealtimeEventType.RESPONSE_COMPLETE:
            break

    types = [e.type for e in events]
    assert types == [
        RealtimeEventType.PARTIAL_TRANSCRIPT,
        RealtimeEventType.FINAL_TRANSCRIPT,
        RealtimeEventType.RESPONSE_TEXT_DELTA,
        RealtimeEventType.RESPONSE_AUDIO_DELTA,
        RealtimeEventType.RESPONSE_COMPLETE,
    ]
    assert events[1].text == "Hello"
    assert events[3].audio.data == b"fake-audio"


async def test_realtime_session_drops_unrecognized_event_types():
    connection = _FakeRealtimeConnection(
        [
            SimpleNamespace(type="session.created"),  # not mapped -> dropped
            SimpleNamespace(type="response.done"),
        ]
    )
    session = OpenAIRealtimeSession(connection, output_encoding=AudioEncoding.PCM16)

    events = [event async for event in _take(session.events(), 1)]

    assert len(events) == 1
    assert events[0].type == RealtimeEventType.RESPONSE_COMPLETE


async def _take(aiter, n):
    count = 0
    async for item in aiter:
        yield item
        count += 1
        if count >= n:
            return


async def test_realtime_session_send_audio_base64_encodes():
    connection = _FakeRealtimeConnection([])
    session = OpenAIRealtimeSession(connection, output_encoding=AudioEncoding.PCM16)

    await session.send_audio(AudioChunk(data=b"mic-audio", encoding=AudioEncoding.PCM16))

    assert connection.sent[0]["type"] == "input_audio_buffer.append"
    import base64

    assert base64.b64decode(connection.sent[0]["audio"]) == b"mic-audio"


async def test_realtime_session_close_delegates_to_connection():
    connection = _FakeRealtimeConnection([])
    session = OpenAIRealtimeSession(connection, output_encoding=AudioEncoding.PCM16)

    await session.close()

    assert connection.closed is True


def test_openai_realtime_satisfies_realtime_voice_service_interface():
    assert isinstance(OpenAIRealtimeVoiceService(api_key="k"), RealtimeVoiceService)


async def test_realtime_send_wraps_errors():
    connection = _FakeRealtimeConnection([])
    connection.send = AsyncMock(side_effect=OpenAIError("rate limited"))
    session = OpenAIRealtimeSession(connection, output_encoding=AudioEncoding.PCM16)

    try:
        await session.send_audio(AUDIO_IN)
        assert False, "expected VoiceServiceError"
    except VoiceServiceError:
        pass


# -- Factory + DI ---------------------------------------------------------


def test_factories_select_providers_from_settings():
    settings = Settings(
        stt_provider="deepgram",
        tts_provider="elevenlabs",
        realtime_voice_provider="openai_realtime",
        deepgram_api_key="k",
        elevenlabs_api_key="k",
        openai_api_key="k",
    )

    assert isinstance(build_speech_to_text_service(settings), DeepgramSpeechToTextService)
    assert isinstance(build_text_to_speech_service(settings), ElevenLabsTextToSpeechService)
    assert isinstance(build_realtime_voice_service(settings), OpenAIRealtimeVoiceService)


def test_dependency_injection_is_overridable_in_a_real_fastapi_app():
    """Proves get_realtime_voice_service() is genuine FastAPI DI: a route
    depending on it via Depends() picks up an overridden fake without any
    route code changing — the same proof used for the LLM service."""

    app = FastAPI()

    @app.post("/start-call")
    async def start_call(service: RealtimeVoiceService = Depends(get_realtime_voice_service)):
        session = await service.start_session(RealtimeSessionConfig(system_prompt="You are a customer."))
        await session.close()
        return {"provider": service.provider_name}

    class FakeRealtimeVoiceService(RealtimeVoiceService):
        @property
        def provider_name(self) -> str:
            return "fake_realtime"

        async def start_session(self, config):
            return OpenAIRealtimeSession(
                _FakeRealtimeConnection([]), output_encoding=AudioEncoding.PCM16
            )

    app.dependency_overrides[get_realtime_voice_service] = lambda: FakeRealtimeVoiceService()
    client = TestClient(app)

    result = client.post("/start-call").json()

    assert result == {"provider": "fake_realtime"}
