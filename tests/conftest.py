"""Shared fixtures for repository/router tests.

db_session runs every test against the real MSSQL database configured in
Settings (see app.core.database) — there is no test-only substitute
database here. Each test runs inside an outer transaction that is always
rolled back afterwards, so tests never leave rows behind in voice_bot even
though the repositories under test call session.commit() internally: the
session is joined to the outer transaction in "create_savepoint" mode
(SQLAlchemy 2.0), so each internal commit() only releases/reopens a
SAVEPOINT rather than ending the outer transaction, which is what actually
gets rolled back at the end of the fixture.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.database import get_db
from app.main import app

engine = create_engine(get_settings().database_url)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """A TestClient wired to the same rolled-back transaction as db_session,
    so full-stack router tests hit the real MSSQL database without leaving
    any rows behind."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
