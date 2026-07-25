"""Abstract Voice Service contracts.

Three separate interfaces — SpeechToTextService, TextToSpeechService,
RealtimeVoiceService — not one. They're genuinely different capabilities:
a real deployment might pair a dedicated STT provider (Deepgram) with a
dedicated TTS provider (ElevenLabs), or use a single unified realtime
provider (OpenAI Realtime) instead of the STT/TTS pair entirely.
Application code depends only on these ABCs, never on a concrete provider
class, so which providers are actually configured is invisible past this
layer (see services/voice/factory.py and core/dependencies.py).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas.voice import (
    AudioChunk,
    RealtimeEvent,
    RealtimeSessionConfig,
    SynthesisRequest,
    SynthesisResult,
    TranscriptionResult,
)


class VoiceServiceError(Exception):
    """Raised when a provider call fails, wrapping the provider-specific error."""


class SpeechToTextService(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def transcribe(self, audio: AudioChunk) -> TranscriptionResult:
        """Transcribes a single chunk of recorded audio."""
        raise NotImplementedError


class TextToSpeechService(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesizes speech audio for a piece of text."""
        raise NotImplementedError


class RealtimeVoiceSession(ABC):
    """One live, bidirectional voice session.

    Session-based rather than request/response — a live call is inherently
    a persistent stream, not a series of independent calls — which is why
    this is a separate abstraction from SpeechToTextService/
    TextToSpeechService rather than just "call transcribe() in a loop".
    """

    @abstractmethod
    async def send_audio(self, chunk: AudioChunk) -> None:
        """Streams a chunk of microphone audio into the session."""
        raise NotImplementedError

    @abstractmethod
    def events(self) -> AsyncIterator[RealtimeEvent]:
        """Yields events (transcripts, response text/audio, errors) as they arrive."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError


class RealtimeVoiceService(ABC):
    """Opens RealtimeVoiceSession instances for a given call configuration."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def start_session(self, config: RealtimeSessionConfig) -> RealtimeVoiceSession:
        raise NotImplementedError
