"""Tests for the roleplay WebSocket endpoint: connection lifecycle,
session/persona resolution, heartbeat, the real LLM-driven conversation
loop (with a fake LLMService), the scripted-mock fallback when no LLM key
is configured, and disconnect cleanup.

Runs against the real MSSQL database via the db_session/client fixtures in
conftest.py (each test rolled back afterwards) — a real Persona and
RoleplaySession are created for every test, since the endpoint now
resolves session_id against the database rather than accepting any
string.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.websockets.connection_manager import connection_manager
from app.config.settings import Settings, get_settings
from app.core.dependencies import get_llm_service
from app.main import app
from app.repositories.persona_repository import PersonaRepository
from app.repositories.roleplay_session_repository import RoleplaySessionRepository
from app.schemas.llm import LLMRequest, LLMResponse, LLMUsage
from app.services.llm import LLMService, LLMServiceError
from app.services.persona_engine import persona_engine
from app.services.persona_mapping import build_persona_engine_input

PERSONA_DATA = {
    "industry": "SaaS",
    "customer_personality": "skeptical",
    "difficulty": "intermediate",
    "company_size": "51-200",
    "decision_maker_role": "VP of Sales",
    "budget": "$50k-$100k",
    "pain_points": ["slow onboarding", "poor reporting"],
    "competitors": ["Acme Corp"],
    "possible_objections": ["too expensive", "already using a competitor"],
}

FAKE_AI_REPLY = "Sure, walk me through the pricing."

# openai_api_key here is a dummy — it only needs to be non-empty so
# Settings.llm_is_configured is True and the route takes the live
# (LLM-driven) branch. get_llm_service is separately overridden with a
# fake, so this key is never actually used to build a real client.
FAST_LIVE_SETTINGS = Settings(
    ws_heartbeat_interval_seconds=0.05,
    ws_mock_stream_chunk_delay_seconds=0.001,
    llm_provider="openai",
    openai_api_key="test-key",
)

FAST_MOCK_FALLBACK_SETTINGS = Settings(
    ws_heartbeat_interval_seconds=0.05,
    ws_mock_message_interval_seconds=0.02,
    ws_mock_stream_chunk_delay_seconds=0.001,
    llm_provider="openai",
    openai_api_key="",
)


class _FakeLLMService(LLMService):
    def __init__(self, content: str) -> None:
        self._content = content
        self.last_request: LLMRequest | None = None

    @property
    def provider_name(self) -> str:
        return "fake"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(
            content=self._content,
            provider="fake",
            model="fake-model",
            usage=LLMUsage(input_tokens=10, output_tokens=10),
        )


class _RaisingLLMService(LLMService):
    @property
    def provider_name(self) -> str:
        return "fake"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise LLMServiceError("simulated provider failure")


@pytest.fixture()
def persona(db_session):
    return PersonaRepository(db_session).create(PERSONA_DATA)


@pytest.fixture()
def roleplay_session(db_session, persona):
    return RoleplaySessionRepository(db_session).create(persona.id)


@pytest.fixture()
def fake_llm() -> _FakeLLMService:
    return _FakeLLMService(FAKE_AI_REPLY)


@pytest.fixture()
def live_client(client: TestClient, fake_llm: _FakeLLMService):
    app.dependency_overrides[get_settings] = lambda: FAST_LIVE_SETTINGS
    app.dependency_overrides[get_llm_service] = lambda: fake_llm
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_llm_service, None)


@pytest.fixture()
def raising_client(client: TestClient):
    app.dependency_overrides[get_settings] = lambda: FAST_LIVE_SETTINGS
    app.dependency_overrides[get_llm_service] = lambda: _RaisingLLMService()
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_llm_service, None)


@pytest.fixture()
def mock_fallback_client(client: TestClient):
    app.dependency_overrides[get_settings] = lambda: FAST_MOCK_FALLBACK_SETTINGS
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)


def _receive_until_type(websocket, expected_type: str, max_messages: int = 300) -> dict:
    for _ in range(max_messages):
        message = websocket.receive_json()
        if message.get("type") == expected_type:
            return message
    raise AssertionError(f"Did not receive a message of type {expected_type!r} within {max_messages} messages")


def test_connect_sends_connection_status_first(live_client, roleplay_session):
    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        message = websocket.receive_json()
        assert message == {"type": "connection_status", "status": "connected"}


def test_unknown_session_id_sends_error(live_client):
    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{uuid.uuid4()}") as websocket:
        websocket.receive_json()  # connection_status
        error = websocket.receive_json()
        assert error["type"] == "error"


def test_malformed_session_id_sends_error(live_client):
    with live_client.websocket_connect("/api/v1/ws/roleplay/not-a-uuid") as websocket:
        websocket.receive_json()  # connection_status
        error = websocket.receive_json()
        assert error["type"] == "error"


def test_completed_session_sends_error(live_client, db_session, roleplay_session):
    RoleplaySessionRepository(db_session).end(roleplay_session)

    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status
        error = websocket.receive_json()
        assert error["type"] == "error"


def test_sends_opening_line_as_ai_buyer_first_turn(live_client, persona, roleplay_session):
    expected_persona = persona_engine.generate(build_persona_engine_input(persona))

    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status

        transcript_message = _receive_until_type(websocket, "transcript_message")
        assert transcript_message["speaker"] == "ai-buyer"
        assert transcript_message["text"] == expected_persona.opening_line
        assert transcript_message["timestamp_ms"] == 0


def test_rep_utterance_gets_llm_reply_and_updates_state(live_client, roleplay_session):
    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status
        _receive_until_type(websocket, "transcript_message")  # opening line
        _receive_until_type(websocket, "session_update")  # state after opening line

        websocket.send_text(json.dumps({"type": "rep_utterance", "text": "Hi, thanks for taking my call."}))

        rep_echo = _receive_until_type(websocket, "transcript_message")
        assert rep_echo["speaker"] == "rep"
        assert rep_echo["text"] == "Hi, thanks for taking my call."

        rep_state_update = _receive_until_type(websocket, "session_update")
        assert rep_state_update["state"]["turn_count"] == 2

        ai_reply = _receive_until_type(websocket, "transcript_message")
        assert ai_reply["speaker"] == "ai-buyer"
        assert ai_reply["text"] == FAKE_AI_REPLY

        ai_state_update = _receive_until_type(websocket, "session_update")
        assert ai_state_update["state"]["turn_count"] == 3


def test_prompt_sent_to_llm_includes_persona_and_history(live_client, persona, roleplay_session, fake_llm):
    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status
        _receive_until_type(websocket, "transcript_message")  # opening line

        websocket.send_text(json.dumps({"type": "rep_utterance", "text": "Tell me about your pricing."}))
        _receive_until_type(websocket, "transcript_message")  # ai reply

    assert fake_llm.last_request is not None
    assert persona.industry in fake_llm.last_request.system_prompt
    assert "Tell me about your pricing." in fake_llm.last_request.system_prompt
    assert fake_llm.last_request.messages == []


def test_llm_error_sends_error_without_crashing_socket(raising_client, roleplay_session):
    with raising_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status
        _receive_until_type(websocket, "transcript_message")  # opening line

        websocket.send_text(json.dumps({"type": "rep_utterance", "text": "Hi there."}))

        error = _receive_until_type(websocket, "error")
        assert "AI buyer" in error["message"]

        # connection survives the failed turn — a heartbeat still arrives
        heartbeat = _receive_until_type(websocket, "heartbeat")
        assert heartbeat == {"type": "heartbeat"}


def test_heartbeat_is_sent_periodically(live_client, roleplay_session):
    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status
        heartbeat = _receive_until_type(websocket, "heartbeat")
        assert heartbeat == {"type": "heartbeat"}


def test_client_can_ack_heartbeat_without_breaking_the_connection(live_client, roleplay_session):
    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status
        _receive_until_type(websocket, "heartbeat")
        websocket.send_text(json.dumps({"type": "heartbeat_ack"}))

        # connection should still be alive and able to carry a real turn
        websocket.send_text(json.dumps({"type": "rep_utterance", "text": "Still there?"}))
        ai_reply = _receive_until_type(websocket, "transcript_message")
        assert ai_reply["speaker"] in {"ai-buyer", "rep"}


def test_disconnect_cleans_up_the_connection_manager(live_client, roleplay_session):
    session_id = str(roleplay_session.id)
    with live_client.websocket_connect(f"/api/v1/ws/roleplay/{session_id}") as websocket:
        websocket.receive_json()
        assert connection_manager.is_connected(session_id)

    assert not connection_manager.is_connected(session_id)


def test_falls_back_to_mock_conversation_when_no_llm_key_configured(mock_fallback_client, roleplay_session):
    with mock_fallback_client.websocket_connect(f"/api/v1/ws/roleplay/{roleplay_session.id}") as websocket:
        websocket.receive_json()  # connection_status

        transcript_message = _receive_until_type(websocket, "transcript_message")
        assert transcript_message["text"] == "Hello, this is Alicia. I only have a few minutes."
        assert transcript_message["speaker"] == "ai-buyer"
