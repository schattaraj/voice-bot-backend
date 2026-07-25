"""Structured WebSocket message contracts for the realtime roleplay
session protocol (see app.api.websockets).

Every message sent over the socket, in either direction, is one of these
types, discriminated by `type`. Client and server agree on this schema
without either side needing to know about the LLM or voice provider
internals. The client transcribes the rep's speech itself (browser
SpeechRecognition) and sends only the resulting text as RepUtteranceMessage
— the backend never receives or processes raw audio. When no LLM key is
configured, the server falls back to a scripted mock conversation (see
api/websockets/mock_conversation.py) instead of driving a real model.
"""

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.conversation import ConversationState
from app.schemas.transcript import Speaker


class ConnectionStatusValue(str, Enum):
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"


class WsMessageType(str, Enum):
    CONNECTION_STATUS = "connection_status"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    TRANSCRIPT_MESSAGE = "transcript_message"
    MESSAGE_DELTA = "message_delta"
    SESSION_UPDATE = "session_update"
    ERROR = "error"
    REP_UTTERANCE = "rep_utterance"


class ConnectionStatusMessage(BaseModel):
    """Server -> client: acknowledges the socket's own connection state."""

    type: Literal[WsMessageType.CONNECTION_STATUS] = WsMessageType.CONNECTION_STATUS
    status: ConnectionStatusValue


class HeartbeatMessage(BaseModel):
    """Server -> client: liveness ping, expects a HeartbeatAckMessage back."""

    type: Literal[WsMessageType.HEARTBEAT] = WsMessageType.HEARTBEAT


class HeartbeatAckMessage(BaseModel):
    """Client -> server: response to a HeartbeatMessage."""

    type: Literal[WsMessageType.HEARTBEAT_ACK] = WsMessageType.HEARTBEAT_ACK


class RepUtteranceMessage(BaseModel):
    """Client -> server: one finalized rep utterance, transcribed client-side
    by the browser's SpeechRecognition API (see the frontend's
    use-speech-recognition hook) — the backend never receives raw audio."""

    type: Literal[WsMessageType.REP_UTTERANCE] = WsMessageType.REP_UTTERANCE
    text: str


class TranscriptMessagePayload(BaseModel):
    """Server -> client: one finalized turn appended to the transcript."""

    type: Literal[WsMessageType.TRANSCRIPT_MESSAGE] = WsMessageType.TRANSCRIPT_MESSAGE
    speaker: Speaker
    text: str
    timestamp_ms: int


class MessageDeltaPayload(BaseModel):
    """Server -> client: a turn's text arriving incrementally, before it's
    finalized as a TranscriptMessagePayload — the "streaming messages"
    requirement, simulating token-by-token LLM output.
    """

    type: Literal[WsMessageType.MESSAGE_DELTA] = WsMessageType.MESSAGE_DELTA
    speaker: Speaker
    text_so_far: str


class SessionUpdateMessage(BaseModel):
    """Server -> client: the full evolved ConversationState after a turn."""

    type: Literal[WsMessageType.SESSION_UPDATE] = WsMessageType.SESSION_UPDATE
    state: ConversationState


class ErrorMessage(BaseModel):
    type: Literal[WsMessageType.ERROR] = WsMessageType.ERROR
    message: str


WsOutboundMessage = (
    ConnectionStatusMessage
    | HeartbeatMessage
    | TranscriptMessagePayload
    | MessageDeltaPayload
    | SessionUpdateMessage
    | ErrorMessage
)

WsInboundMessage = Annotated[
    HeartbeatAckMessage | RepUtteranceMessage, Field(discriminator="type")
]
