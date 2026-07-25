"""Voice Service abstraction: provider-agnostic Speech-to-Text,
Text-to-Speech, and Realtime Streaming, so the rest of the application
never depends on Deepgram, ElevenLabs, or OpenAI Realtime specifically.

Import the three ABCs and VoiceServiceError to depend on this layer.
Concrete provider classes and the build_*() factory functions exist for
core.dependencies and tests — application code should never need them
directly.
"""

from app.services.voice.base import (
    RealtimeVoiceService,
    RealtimeVoiceSession,
    SpeechToTextService,
    TextToSpeechService,
    VoiceServiceError,
)
from app.services.voice.factory import (
    build_realtime_voice_service,
    build_speech_to_text_service,
    build_text_to_speech_service,
)

__all__ = [
    "SpeechToTextService",
    "TextToSpeechService",
    "RealtimeVoiceService",
    "RealtimeVoiceSession",
    "VoiceServiceError",
    "build_speech_to_text_service",
    "build_text_to_speech_service",
    "build_realtime_voice_service",
]
