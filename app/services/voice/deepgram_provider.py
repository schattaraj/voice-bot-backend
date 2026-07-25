"""Deepgram Speech-to-Text provider adapter."""

from deepgram import AsyncDeepgramClient
from deepgram.core.api_error import ApiError as DeepgramApiError

from app.schemas.voice import AudioChunk, AudioEncoding, TranscriptionResult
from app.services.voice.base import SpeechToTextService, VoiceServiceError

# Deepgram only needs an explicit `encoding` for raw/headerless audio.
# Compressed, self-describing formats like MP3 are auto-detected, so they
# map to None here rather than a (nonexistent) Deepgram literal.
_ENCODING_MAP: dict[AudioEncoding, str | None] = {
    AudioEncoding.PCM16: "linear16",
    AudioEncoding.OPUS: "opus",
    AudioEncoding.MULAW: "mulaw",
    AudioEncoding.MP3: None,
}


class DeepgramSpeechToTextService(SpeechToTextService):
    def __init__(self, api_key: str, model: str = "nova-2") -> None:
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "deepgram"

    async def transcribe(self, audio: AudioChunk) -> TranscriptionResult:
        try:
            response = await self._client.listen.v1.media.transcribe_file(
                request=audio.data,
                model=self._model,
                encoding=_ENCODING_MAP[audio.encoding],
                punctuate=True,
                smart_format=True,
            )
        except DeepgramApiError as error:
            raise VoiceServiceError(f"Deepgram transcription failed: {error}") from error

        alternative = response.results.channels[0].alternatives[0]

        return TranscriptionResult(
            text=alternative.transcript,
            is_final=True,
            confidence=alternative.confidence,
        )
