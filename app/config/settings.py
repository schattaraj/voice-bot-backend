"""Environment-based application settings, loaded via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Sales Roleplay API"
    app_version: str = "0.1.0"
    environment: str = "development"

    cors_origins: list[str] = ["http://localhost:8000"]

    db_server: str = "localhost"
    db_port: int = 3306
    db_name: str = "voice_bot"
    db_user: str = "root"
    db_password: str = ""

    # Which provider app.services.llm hands out via dependency injection.
    # Swapping this (and restarting the app) is the only thing required to
    # move the whole application from Claude to GPT or back.
    llm_provider: Literal["anthropic", "openai"] = "anthropic"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Which providers app.services.voice hands out via dependency
    # injection — same swap-by-config pattern as llm_provider above.
    stt_provider: Literal["deepgram"] = "deepgram"
    tts_provider: Literal["elevenlabs"] = "elevenlabs"
    realtime_voice_provider: Literal["openai_realtime"] = "openai_realtime"

    deepgram_api_key: str = ""
    deepgram_model: str = "nova-2"

    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_turbo_v2_5"

    # Realtime voice reuses the same OpenAI account/key as the LLM
    # provider (openai_api_key above) — only the model differs.
    openai_realtime_model: str = "gpt-4o-realtime-preview"

    # Timing for the roleplay WebSocket (app.api.websockets). Exposed as
    # settings — not bare module constants — so tests can construct a
    # Settings with tiny intervals instead of waiting on real wall-clock
    # delays, the same way every other provider choice here is testable.
    # ws_mock_message_interval_seconds only paces the scripted mock
    # fallback (see llm_is_configured below) — the real, LLM-driven
    # conversation has no fixed pre-turn delay, since the LLM call's own
    # latency already provides that pause naturally.
    ws_heartbeat_interval_seconds: float = 20.0
    ws_mock_message_interval_seconds: float = 3.5
    ws_mock_stream_chunk_delay_seconds: float = 0.05

    @property
    def llm_is_configured(self) -> bool:
        """Whether the configured LLM provider actually has a usable key.

        Lets the roleplay WebSocket fall back to the scripted mock
        conversation instead of driving a real model call that would just
        fail (see app.api.websockets.roleplay_socket) — a developer without
        any provider key configured still gets a working demo.
        """
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        return bool(self.anthropic_api_key)

    @property
    def database_url(self) -> str:
        """SQLAlchemy connection URL for MySQL via the PyMySQL driver."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_server}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
