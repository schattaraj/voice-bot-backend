"""Analytics endpoints — consumed by the frontend's analytics.service.ts.

Evaluation rows are produced by the Evaluation Engine (Step 19); this
router is read-only.
"""

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import get_evaluation_repository
from app.core.exceptions import NotFoundError
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas.analytics import SessionScoreResponse

router = APIRouter()


@router.get("/sessions/{session_id}", response_model=SessionScoreResponse)
def get_session_score(
    session_id: uuid.UUID,
    repo: EvaluationRepository = Depends(get_evaluation_repository),
) -> SessionScoreResponse:
    evaluation = repo.get_by_session(session_id)
    if evaluation is None:
        raise NotFoundError("Evaluation", str(session_id))
    return evaluation


@router.get("/history", response_model=list[SessionScoreResponse])
def get_score_history(
    repo: EvaluationRepository = Depends(get_evaluation_repository),
) -> list[SessionScoreResponse]:
    return repo.list_all()
