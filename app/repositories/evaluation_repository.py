"""Data-access layer for Evaluation."""

import uuid

from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation


class EvaluationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_session(self, session_id: uuid.UUID) -> Evaluation | None:
        return self._db.query(Evaluation).filter(Evaluation.session_id == session_id).first()

    def list_all(self) -> list[Evaluation]:
        return list(self._db.query(Evaluation).order_by(Evaluation.created_at.desc()).all())
