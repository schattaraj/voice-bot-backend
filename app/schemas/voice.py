"""Structured, provider-agnostic contracts for the Voice Service abstraction.

Covers three distinct capabilities — Speech-to-Text, Text-to-Speech, and
Realtime Streaming — because they're genuinely separate concerns, not one
monolithic "voice call". A real deployment might mix a dedicated STT
provider with a dedicated TTS provider, or use a single unified realtime
provider instead of the STT/TTS pair entirely; these schemas are shared by
all three so that choice never leaks into application code.
"""

from enum import Enum

from pydantic import BaseModel


class AudioEncoding(str, Enum):
    PCM16 = "pcm16"
    MP3 = "mp3"
    OPUS = "opus"
    MULAW = "mulaw"


class AudioChunk(BaseModel):
    """Raw audio bytes plus enough metadata to interpret them."""

    data: bytes
    encoding: AudioEncoding
    sample_rate_hz: int = 16000


class TranscriptionResult(BaseModel):
    text: str
    is_final: bool = True
    confidence: float | None = None


class SynthesisRequest(BaseModel):
    text: str
    voice_id: str | None = None
    encoding: AudioEncoding = AudioEncoding.MP3


class SynthesisResult(BaseModel):
    audio: AudioChunk


class RealtimeSessionConfig(BaseModel):
    """Configuration for opening one live, bidirectional voice session."""

    system_prompt: str
    voice_id: str | None = None
    input_encoding: AudioEncoding = AudioEncoding.PCM16
    output_encoding: AudioEncoding = AudioEncoding.PCM16


class RealtimeEventType(str, Enum):
    PARTIAL_TRANSCRIPT = "partial_transcript"
    FINAL_TRANSCRIPT = "final_transcript"
    RESPONSE_TEXT_DELTA = "response_text_delta"
    RESPONSE_AUDIO_DELTA = "response_audio_delta"
    RESPONSE_COMPLETE = "response_complete"
    ERROR = "error"


class RealtimeEvent(BaseModel):
    """One event out of a RealtimeVoiceSession's event stream.

    Deliberately a single flat type covering every event kind (rather than
    a class per event) — RealtimeVoiceSession.events() is a plain
    AsyncIterator[RealtimeEvent], so consumers just switch on `type`
    instead of needing to know a provider-specific event class hierarchy.
    """

    type: RealtimeEventType
    text: str | None = None
    audio: AudioChunk | None = None
    error_message: str | None = None
