"""Builds the configured Speech-to-Text, Text-to-Speech, and Realtime
Voice implementations from settings.

These are the only places in the codebase that import concrete provider
classes — everywhere else (including core/dependencies.py) only ever
imports the ABCs from services/voice/base.py.
"""

from app.config.settings import Settings
from app.services.voice.base import RealtimeVoiceService, SpeechToTextService, TextToSpeechService
from app.services.voice.deepgram_provider import DeepgramSpeechToTextService
from app.services.voice.elevenlabs_provider import ElevenLabsTextToSpeechService
from app.services.voice.openai_realtime_provider import OpenAIRealtimeVoiceService


def build_speech_to_text_service(settings: Settings) -> SpeechToTextService:
    if settings.stt_provider == "deepgram":
        return DeepgramSpeechToTextService(api_key=settings.deepgram_api_key, model=settings.deepgram_model)
    raise ValueError(f"Unsupported STT provider: {settings.stt_provider}")


def build_text_to_speech_service(settings: Settings) -> TextToSpeechService:
    if settings.tts_provider == "elevenlabs":
        return ElevenLabsTextToSpeechService(
            api_key=settings.elevenlabs_api_key, model_id=settings.elevenlabs_model
        )
    raise ValueError(f"Unsupported TTS provider: {settings.tts_provider}")


def build_realtime_voice_service(settings: Settings) -> RealtimeVoiceService:
    if settings.realtime_voice_provider == "openai_realtime":
        return OpenAIRealtimeVoiceService(
            api_key=settings.openai_api_key, model=settings.openai_realtime_model
        )
    raise ValueError(f"Unsupported realtime voice provider: {settings.realtime_voice_provider}")
