"""Top-level API router.

Domain routers (personas, roleplay sessions, transcripts, analytics) are
included here as they're implemented.
"""

from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.personas import router as personas_router
from app.api.roleplay_sessions import router as roleplay_sessions_router
from app.api.transcript import router as transcript_router
from app.api.websockets.roleplay_socket import router as roleplay_websocket_router

api_router = APIRouter()
api_router.include_router(personas_router, prefix="/personas", tags=["personas"])
api_router.include_router(roleplay_sessions_router, prefix="/roleplay/sessions", tags=["roleplay-sessions"])
api_router.include_router(transcript_router, prefix="/roleplay/sessions", tags=["transcript"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(roleplay_websocket_router, prefix="/ws", tags=["websocket"])
