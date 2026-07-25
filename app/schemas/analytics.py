"""REST response schemas for the Analytics resource.

Matches the frontend's SessionScore/PerformanceMetric/TimelinePoint types
exactly (types/analytics.ts) — this is what models.Evaluation rows get
mapped into for the frontend's analytics.service.ts.
"""

from uuid import UUID

from app.schemas.base import CamelCaseModel


class PerformanceMetricResponse(CamelCaseModel):
    label: str
    value: int
    max_value: int


class TimelinePointResponse(CamelCaseModel):
    minute: int
    rep_seconds: int
    customer_seconds: int


class SessionScoreResponse(CamelCaseModel):
    session_id: UUID
    overall_score: int
    metrics: list[PerformanceMetricResponse]
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    timeline: list[TimelinePointResponse]
    summary: str
