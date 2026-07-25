"""FastAPI dependency providers.

Route handlers request infrastructure (the LLM service, DB sessions, etc.)
via Depends() on functions like get_llm_service() rather than importing
concrete implementations directly. That indirection is what makes
implementations swappable via configuration (see config/settings.py's
llm_provider) and overridable in tests
(app.dependency_overrides[get_llm_service] = ...) without touching any
route code.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.database import get_db
from app.evaluation.engine import EvaluationEngine
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.persona_repository import PersonaRepository
from app.repositories.roleplay_session_repository import RoleplaySessionRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.services.llm import LLMService, build_llm_service
from app.services.voice import (
    RealtimeVoiceService,
    SpeechToTextService,
    TextToSpeechService,
    build_realtime_voice_service,
    build_speech_to_text_service,
    build_text_to_speech_service,
)


def get_persona_repository(db: Session = Depends(get_db)) -> PersonaRepository:
    return PersonaRepository(db)


def get_roleplay_session_repository(db: Session = Depends(get_db)) -> RoleplaySessionRepository:
    return RoleplaySessionRepository(db)


def get_transcript_repository(db: Session = Depends(get_db)) -> TranscriptRepository:
    return TranscriptRepository(db)


def get_evaluation_repository(db: Session = Depends(get_db)) -> EvaluationRepository:
    return EvaluationRepository(db)


@lru_cache
def get_llm_service() -> LLMService:
    return build_llm_service(get_settings())


def get_evaluation_engine(llm_service: LLMService = Depends(get_llm_service)) -> EvaluationEngine:
    """Demonstrates dependency composition: this depends on get_llm_service()
    rather than building its own LLMService, so overriding get_llm_service in
    a test (or swapping llm_provider in settings) automatically changes which
    provider the Evaluation Engine uses too — no separate wiring needed.
    """
    return EvaluationEngine(llm_service=llm_service)


@lru_cache
def get_speech_to_text_service() -> SpeechToTextService:
    return build_speech_to_text_service(get_settings())


@lru_cache
def get_text_to_speech_service() -> TextToSpeechService:
    return build_text_to_speech_service(get_settings())


@lru_cache
def get_realtime_voice_service() -> RealtimeVoiceService:
    return build_realtime_voice_service(get_settings())
