"""Shared base for REST-facing Pydantic schemas.

Every schema exposed over HTTP inherits from CamelCaseModel so the JSON
wire format matches the frontend's TypeScript field names (industry,
customerPersonality, ...) exactly, while Python code stays idiomatic
snake_case internally. Internal-only schemas (llm.py, voice.py,
persona_engine.py, conversation.py, transcript.py) intentionally do NOT
use this — they're never serialized to an HTTP client directly, so
there's nothing to bridge.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
