"""OpenAI Realtime provider adapter.

Session-based, unlike the other two adapters: OpenAIRealtimeSession wraps a
live websocket connection (via the openai SDK's realtime.connect()), so
send_audio()/events()/close() map onto that connection's
send()/recv()/close() rather than independent request/response calls.
"""

import base64
from collections.abc import AsyncIterator

from openai import AsyncOpenAI, OpenAIError

from app.schemas.voice import (
    AudioChunk,
    AudioEncoding,
    RealtimeEvent,
    RealtimeEventType,
    RealtimeSessionConfig,
)
from app.services.voice.base import RealtimeVoiceService, RealtimeVoiceSession, VoiceServiceError


class OpenAIRealtimeSession(RealtimeVoiceSession):
    def __init__(self, connection, *, output_encoding: AudioEncoding) -> None:
        self._connection = connection
        self._output_encoding = output_encoding

    async def send_audio(self, chunk: AudioChunk) -> None:
        try:
            await self._connection.send(
                {
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(chunk.data).decode("ascii"),
                }
            )
        except OpenAIError as error:
            raise VoiceServiceError(f"OpenAI Realtime send failed: {error}") from error

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        while True:
            try:
                raw_event = await self._connection.recv()
            except OpenAIError as error:
                raise VoiceServiceError(f"OpenAI Realtime stream failed: {error}") from error

            mapped = self._map_event(raw_event)
            if mapped is not None:
                yield mapped

    async def close(self) -> None:
        await self._connection.close()

    def _map_event(self, event: object) -> RealtimeEvent | None:
        event_type = getattr(event, "type", None)

        if event_type == "conversation.item.input_audio_transcription.delta":
            return RealtimeEvent(type=RealtimeEventType.PARTIAL_TRANSCRIPT, text=event.delta)
        if event_type == "conversation.item.input_audio_transcription.completed":
            return RealtimeEvent(type=RealtimeEventType.FINAL_TRANSCRIPT, text=event.transcript)
        if event_type == "response.text.delta":
            return RealtimeEvent(type=RealtimeEventType.RESPONSE_TEXT_DELTA, text=event.delta)
        if event_type == "response.audio.delta":
            return RealtimeEvent(
                type=RealtimeEventType.RESPONSE_AUDIO_DELTA,
                audio=AudioChunk(data=base64.b64decode(event.delta), encoding=self._output_encoding),
            )
        if event_type == "response.done":
            return RealtimeEvent(type=RealtimeEventType.RESPONSE_COMPLETE)
        if event_type == "error":
            message = getattr(getattr(event, "error", None), "message", "Unknown realtime error")
            return RealtimeEvent(type=RealtimeEventType.ERROR, error_message=message)

        # Event types we don't map onto RealtimeEvent (session/rate-limit
        # bookkeeping, etc.) are intentionally dropped rather than surfaced.
        return None


class OpenAIRealtimeVoiceService(RealtimeVoiceService):
    def __init__(self, api_key: str, model: str = "gpt-4o-realtime-preview") -> None:
        self._api_key = api_key
        self._model = model
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Constructed lazily — see OpenAILLMService.client for why: this
        SDK's client validates credentials at construction time, and
        realtime_voice_provider defaults to this very provider, so an eager
        client here would crash on first use in any fresh setup that
        hasn't configured OPENAI_API_KEY yet.
        """
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "openai_realtime"

    async def start_session(self, config: RealtimeSessionConfig) -> RealtimeVoiceSession:
        try:
            # .enter() rather than `async with` on purpose: the connection
            # must outlive this method call, closed explicitly later via
            # RealtimeVoiceSession.close().
            connection = await self.client.realtime.connect(model=self._model).enter()
            await connection.send(
                {
                    "type": "session.update",
                    "session": {"instructions": config.system_prompt, "voice": config.voice_id},
                }
            )
        except OpenAIError as error:
            raise VoiceServiceError(f"OpenAI Realtime session start failed: {error}") from error

        return OpenAIRealtimeSession(connection, output_encoding=config.output_encoding)
