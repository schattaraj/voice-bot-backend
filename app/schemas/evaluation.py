"""Structured input/output contracts for the Evaluation Engine.

Distinct from models.Evaluation (the persisted DB row, Step 12) — this is
the LLM's structured judgment about a transcript, before anything is
saved. A future step mapping EvaluationResult onto a persisted Evaluation
row is where those two shapes would meet.
"""

from pydantic import BaseModel, Field

from app.schemas.transcript import TranscriptTurn


class EvaluationRequest(BaseModel):
    transcript: list[TranscriptTurn]


class EvaluationResult(BaseModel):
    """The four requested skill dimensions are explicit named fields, not
    a generic list — the Evaluation Engine's contract is exactly these
    four scores, not an open-ended set the LLM could shrink or pad."""

    overall_score: int = Field(ge=0, le=100)
    discovery_score: int = Field(ge=0, le=100)
    objection_handling_score: int = Field(ge=0, le=100)
    communication_score: int = Field(ge=0, le=100)
    closing_score: int = Field(ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
