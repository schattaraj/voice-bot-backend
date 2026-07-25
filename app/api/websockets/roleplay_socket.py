"""WebSocket endpoint for one live roleplay session.

Streams connection status, heartbeats, the realtime transcript (as both
incremental deltas and finalized messages), and session/state updates to
the client. When a real LLM provider key is configured (see
Settings.llm_is_configured), the AI buyer's replies are generated live by
the Persona Engine (Step 13) + Prompt Builder (Step 14) + Conversation
State Manager (Step 15) + LLM Service (Step 16), driven by the rep's own
speech — transcribed client-side by the browser and sent as a
RepUtteranceMessage (see app.schemas.websocket); the backend never receives
or processes raw audio. Without a configured key, the connection falls back
to the scripted mock conversation in mock_conversation.py instead.
"""

import asyncio
import contextlib
import time
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from app.api.websockets.connection_manager import connection_manager
from app.api.websockets.mock_conversation import MOCK_PERSONA_INPUT, MOCK_TRANSCRIPT
from app.config.settings import Settings, get_settings
from app.core.dependencies import (
    get_llm_service,
    get_persona_repository,
    get_roleplay_session_repository,
    get_transcript_repository,
)
from app.models.enums import SessionStatus
from app.models.persona import Persona
from app.repositories.persona_repository import PersonaRepository
from app.repositories.roleplay_session_repository import RoleplaySessionRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.conversation import ConversationState
from app.schemas.llm import LLMRequest
from app.schemas.persona_engine import EngineeredPersona
from app.schemas.transcript import TranscriptTurn
from app.schemas.websocket import (
    ConnectionStatusMessage,
    ConnectionStatusValue,
    ErrorMessage,
    HeartbeatMessage,
    MessageDeltaPayload,
    RepUtteranceMessage,
    SessionUpdateMessage,
    TranscriptMessagePayload,
    WsInboundMessage,
)
from app.services.conversation_state_manager import conversation_state_manager
from app.services.llm import LLMService, LLMServiceError
from app.services.persona_engine import persona_engine
from app.services.persona_mapping import build_persona_engine_input
from app.services.prompt_builder import prompt_builder

router = APIRouter()

# Module constants, not Settings fields — mirrors evaluation/engine.py's
# _EVALUATION_TEMPERATURE/_EVALUATION_MAX_TOKENS precedent. Higher
# temperature than evaluation's 0.3: natural, varied spoken replies matter
# more here than consistent scoring. max_tokens kept low since the prompt's
# response_style section already asks for short, spoken-style turns.
_ROLEPLAY_LLM_TEMPERATURE = 0.8
_ROLEPLAY_LLM_MAX_TOKENS = 300

_inbound_adapter: TypeAdapter[WsInboundMessage] = TypeAdapter(WsInboundMessage)


@router.websocket("/roleplay/{session_id}")
async def roleplay_socket(
    websocket: WebSocket,
    session_id: str,
    settings: Settings = Depends(get_settings),
    persona_repository: PersonaRepository = Depends(get_persona_repository),
    roleplay_session_repository: RoleplaySessionRepository = Depends(get_roleplay_session_repository),
    transcript_repository: TranscriptRepository = Depends(get_transcript_repository),
    llm_service: LLMService = Depends(get_llm_service),
) -> None:
    await connection_manager.connect(session_id, websocket)
    await connection_manager.send(
        session_id, ConnectionStatusMessage(status=ConnectionStatusValue.CONNECTED)
    )

    resolved = _resolve_session(session_id, roleplay_session_repository, persona_repository)
    if resolved is None:
        await connection_manager.send(session_id, ErrorMessage(message="Session not found."))
        connection_manager.disconnect(session_id)
        await websocket.close(code=4404)
        return

    session_uuid, persona_row = resolved
    engineered_persona = persona_engine.generate(build_persona_engine_input(persona_row))

    history_rows = transcript_repository.list_by_session(session_uuid)
    transcript_turns = [
        TranscriptTurn(speaker=row.speaker.value, text=row.text, timestamp_ms=row.timestamp_ms)
        for row in history_rows
    ]
    # ConversationState is never persisted — only transcript rows are — so
    # a reconnect mid-call (the frontend already auto-reconnects with
    # backoff) must deterministically rebuild identical state by replaying
    # history through the same pure update() function, rather than
    # resetting to "opening".
    replayed_state = conversation_state_manager.initial_state()
    for turn in transcript_turns:
        replayed_state = conversation_state_manager.update(replayed_state, turn, engineered_persona)

    queue: asyncio.Queue[str] = asyncio.Queue()
    use_mock = not settings.llm_is_configured

    tasks = {
        asyncio.create_task(_receive_loop(websocket, queue)),
        asyncio.create_task(_heartbeat_loop(session_id, settings)),
        asyncio.create_task(
            _run_mock_conversation(session_id, settings, transcript_repository, session_uuid)
            if use_mock
            else _run_live_conversation(
                session_id,
                session_uuid,
                settings,
                engineered_persona,
                transcript_turns,
                replayed_state,
                queue,
                transcript_repository,
                llm_service,
            )
        ),
    }

    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            # Broad suppress is deliberate: this is best-effort cleanup of
            # background tasks after the connection is already ending, not
            # the main request-handling path — a send racing a disconnect
            # (already guarded in ConnectionManager.send) or a cancellation
            # here must never crash the endpoint. asyncio.CancelledError is
            # listed explicitly because it's a BaseException subclass (since
            # Python 3.8, precisely so bare `except Exception` doesn't
            # swallow it by accident) — the task.cancel() calls above are
            # expected to make every `await task` below raise exactly this.
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        connection_manager.disconnect(session_id)


def _resolve_session(
    session_id: str,
    roleplay_session_repository: RoleplaySessionRepository,
    persona_repository: PersonaRepository,
) -> tuple[uuid.UUID, Persona] | None:
    """Validates that session_id is a real, still-open RoleplaySession with
    a resolvable Persona. Returns None for any failure — bad UUID, unknown
    session, an already-completed session (e.g. a stale reconnect racing a
    just-clicked "End Call"), or (unreachable given the FK constraint, but
    checked defensively) a missing persona.
    """
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        return None

    session = roleplay_session_repository.get_by_id(session_uuid)
    if session is None or session.status == SessionStatus.COMPLETED:
        return None

    persona = persona_repository.get_by_id(session.persona_id)
    if persona is None:
        return None

    return session_uuid, persona


async def _receive_loop(websocket: WebSocket, queue: asyncio.Queue[str]) -> None:
    """Listens for client messages. A finalized rep utterance (transcribed
    client-side) is handed off to the conversation task via the queue;
    a heartbeat ack is liveness-only and needs no further action; anything
    else (malformed frames, unrecognized types) is ignored.
    """
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = _inbound_adapter.validate_json(raw)
            except ValidationError:
                continue
            if isinstance(message, RepUtteranceMessage):
                await queue.put(message.text)
    except WebSocketDisconnect:
        return


async def _heartbeat_loop(session_id: str, settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.ws_heartbeat_interval_seconds)
        await connection_manager.send(session_id, HeartbeatMessage())


async def _run_live_conversation(
    session_id: str,
    session_uuid: uuid.UUID,
    settings: Settings,
    persona: EngineeredPersona,
    transcript: list[TranscriptTurn],
    state: ConversationState,
    queue: asyncio.Queue[str],
    transcript_repository: TranscriptRepository,
    llm_service: LLMService,
) -> None:
    """Drives one real, LLM-backed conversation for the lifetime of the
    connection: the AI opens (on a brand-new session), then every rep
    utterance pulled off `queue` gets a real reply. Never calls
    conversation_state_manager.end() — this only happens via the rep's
    "End Call" action (REST endSession + closing the socket), not from
    anything the conversation itself detects.
    """
    clock_start = time.monotonic()
    base_ms = transcript[-1].timestamp_ms if transcript else 0

    def next_timestamp_ms() -> int:
        return base_ms + int((time.monotonic() - clock_start) * 1000)

    if not transcript:
        opening_turn = TranscriptTurn(speaker="ai-buyer", text=persona.opening_line, timestamp_ms=0)
        await _stream_message(session_id, opening_turn, settings)
        await connection_manager.send(
            session_id,
            TranscriptMessagePayload(speaker="ai-buyer", text=opening_turn.text, timestamp_ms=0),
        )
        transcript_repository.append(session_uuid, "ai-buyer", opening_turn.text, 0)
        transcript.append(opening_turn)
        state = conversation_state_manager.update(state, opening_turn, persona)
        await connection_manager.send(session_id, SessionUpdateMessage(state=state))

    while True:
        rep_text = await queue.get()

        rep_timestamp = next_timestamp_ms()
        rep_turn = TranscriptTurn(speaker="rep", text=rep_text, timestamp_ms=rep_timestamp)
        transcript_repository.append(session_uuid, "rep", rep_text, rep_timestamp)
        await connection_manager.send(
            session_id,
            TranscriptMessagePayload(speaker="rep", text=rep_text, timestamp_ms=rep_timestamp),
        )
        state = conversation_state_manager.update(state, rep_turn, persona)
        await connection_manager.send(session_id, SessionUpdateMessage(state=state))
        transcript.append(rep_turn)

        system_prompt = prompt_builder.build_system_prompt(
            persona=persona, conversation_state=state, transcript=transcript
        )
        # Signals "AI is composing" the instant the call starts, rather
        # than leaving a silent gap for however long the LLM takes to
        # respond — CallScreen already flips its "streaming" indicator on
        # any message_delta regardless of content.
        await connection_manager.send(
            session_id, MessageDeltaPayload(speaker="ai-buyer", text_so_far="")
        )

        try:
            response = await llm_service.complete(
                LLMRequest(
                    system_prompt=system_prompt,
                    messages=[],
                    max_tokens=_ROLEPLAY_LLM_MAX_TOKENS,
                    temperature=_ROLEPLAY_LLM_TEMPERATURE,
                )
            )
        except LLMServiceError as error:
            # Per design: one bad LLM call doesn't end the roleplay session
            # — surface it and let the rep just speak again.
            await connection_manager.send(
                session_id, ErrorMessage(message=f"The AI buyer couldn't respond: {error}")
            )
            continue

        ai_timestamp = next_timestamp_ms()
        ai_turn = TranscriptTurn(
            speaker="ai-buyer", text=response.content.strip(), timestamp_ms=ai_timestamp
        )
        await _stream_message(session_id, ai_turn, settings)
        await connection_manager.send(
            session_id,
            TranscriptMessagePayload(speaker="ai-buyer", text=ai_turn.text, timestamp_ms=ai_timestamp),
        )
        transcript_repository.append(session_uuid, "ai-buyer", ai_turn.text, ai_timestamp)
        transcript.append(ai_turn)
        state = conversation_state_manager.update(state, ai_turn, persona)
        await connection_manager.send(session_id, SessionUpdateMessage(state=state))


async def _run_mock_conversation(
    session_id: str,
    settings: Settings,
    transcript_repository: TranscriptRepository,
    session_uuid: uuid.UUID,
) -> None:
    """Fallback for when no LLM key is configured (settings.llm_is_configured
    is False) — the scripted "Alicia / Salesforce" conversation, ignoring
    whichever persona is actually configured for this session. Each turn is
    persisted so analytics/evaluation still work end-to-end when demoing
    without a key.
    """
    persona = persona_engine.generate(MOCK_PERSONA_INPUT)
    state = conversation_state_manager.initial_state()

    for turn in MOCK_TRANSCRIPT:
        await asyncio.sleep(settings.ws_mock_message_interval_seconds)
        await _stream_message(session_id, turn, settings)

        await connection_manager.send(
            session_id,
            TranscriptMessagePayload(speaker=turn.speaker, text=turn.text, timestamp_ms=turn.timestamp_ms),
        )
        transcript_repository.append(session_uuid, turn.speaker, turn.text, turn.timestamp_ms)

        state = conversation_state_manager.update(state, turn, persona)
        await connection_manager.send(session_id, SessionUpdateMessage(state=state))

    state = conversation_state_manager.end(state)
    await connection_manager.send(session_id, SessionUpdateMessage(state=state))


async def _stream_message(session_id: str, turn: TranscriptTurn, settings: Settings) -> None:
    """Sends a turn's text as incremental deltas, simulating token-by-token
    LLM output, before the finalized TranscriptMessagePayload is sent. Used
    by both the live and mock conversation paths.
    """
    words = turn.text.split(" ")
    accumulated = ""
    for word in words:
        accumulated = f"{accumulated} {word}".strip()
        await connection_manager.send(
            session_id, MessageDeltaPayload(speaker=turn.speaker, text_so_far=accumulated)
        )
        await asyncio.sleep(settings.ws_mock_stream_chunk_delay_seconds)
