"""Tracks active WebSocket connections, keyed by session id.

Kept intentionally simple — one connection per session — since a roleplay
call has exactly one participant. A future observer/monitoring feature
could extend this to track multiple sockets per session without changing
how route handlers use it.
"""

import logging

from fastapi import WebSocket

from app.schemas.websocket import WsOutboundMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id] = websocket

    def disconnect(self, session_id: str) -> None:
        self._connections.pop(session_id, None)

    def is_connected(self, session_id: str) -> bool:
        return session_id in self._connections

    async def send(self, session_id: str, message: WsOutboundMessage) -> None:
        """Sends a structured message if the session still has a live
        socket. Swallows send failures rather than raising — a send racing
        against a client disconnect shouldn't crash the caller (usually a
        background simulation task); the receive loop is the source of
        truth for noticing a disconnect and tearing the session down.
        """
        websocket = self._connections.get(session_id)
        if websocket is None:
            return
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception:
            logger.debug("Failed to send WebSocket message for session %s", session_id, exc_info=True)


connection_manager = ConnectionManager()
