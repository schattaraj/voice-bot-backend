"""ElevenLabs Text-to-Speech provider adapter."""

from elevenlabs.client import AsyncElevenLabs
from elevenlabs.core.api_error import ApiError as ElevenLabsApiError

from app.schemas.voice import AudioChunk, AudioEncoding, SynthesisRequest, SynthesisResult
from app.services.voice.base import TextToSpeechService, VoiceServiceError

_OUTPUT_FORMAT_MAP: dict[AudioEncoding, str] = {
    AudioEncoding.MP3: "mp3_44100_128",
    AudioEncoding.PCM16: "pcm_16000",
    AudioEncoding.OPUS: "opus_48000_64",
    AudioEncoding.MULAW: "ulaw_8000",
}

_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs' standard "Rachel" voice


class ElevenLabsTextToSpeechService(TextToSpeechService):
    def __init__(self, api_key: str, model_id: str = "eleven_turbo_v2_5") -> None:
        self._client = AsyncElevenLabs(api_key=api_key)
        self._model_id = model_id

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        try:
            chunks = self._client.text_to_speech.convert(
                request.voice_id or _DEFAULT_VOICE_ID,
                text=request.text,
                model_id=self._model_id,
                output_format=_OUTPUT_FORMAT_MAP[request.encoding],
            )
            audio_bytes = b"".join([chunk async for chunk in chunks])
        except ElevenLabsApiError as error:
            raise VoiceServiceError(f"ElevenLabs synthesis failed: {error}") from error

        return SynthesisResult(
            audio=AudioChunk(data=audio_bytes, encoding=request.encoding)
        )
