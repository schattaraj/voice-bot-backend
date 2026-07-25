# AI Sales Roleplay — Backend

FastAPI backend for the AI Sales Roleplay application. This is the API
counterpart to the Next.js frontend (`c:\nextjs\voice-bot`), consumed via
the Axios-based service layer configured there.

**Status: scaffold only.** No endpoints, models, or business logic are
implemented yet — see [What's scaffolded vs. not](#whats-scaffolded-vs-not).

## Tech stack

- Python 3.13 (see note below), FastAPI, Uvicorn
- Pydantic v2 / pydantic-settings
- SQLAlchemy 2.x + Alembic
- Microsoft SQL Server via `pyodbc` (`mssql+pyodbc` dialect)
- Poetry for dependency management

> **Python version note:** the task specified Python 3.12, but only 3.13
> and 3.14 were available on this machine and 3.13 was chosen instead
> (confirmed with the project owner). Everything used here fully supports
> 3.13; if 3.12 is later required, install it and run
> `poetry env use 3.12`.

## Prerequisites

1. **Python 3.13** and **Poetry** (`pip install poetry`, or see
   [python-poetry.org](https://python-poetry.org/docs/#installation) for
   other install methods).
2. **Microsoft ODBC Driver for SQL Server** (17 or 18) installed on the
   host machine. This is an OS-level driver, not a Python package — search
   "ODBC Driver for SQL Server download" on Microsoft's official site (Microsoft
   Learn) for the current installer. Without it, `pyodbc` cannot connect to
   SQL Server at all (you'll see a `Data source name not found` error).
3. A reachable SQL Server instance (local, Docker, or Azure SQL) once you're
   ready to run migrations — not required just to boot the API.

## Setup

```bash
poetry install
copy .env.example .env   # then fill in DB_* values
poetry run uvicorn app.main:app --reload
```

The API boots and serves interactive docs at `http://localhost:8000/docs`
even with zero DB connectivity, since no routes touch the database yet.

## Project structure

```
app/
├── main.py          FastAPI app instance, CORS, router registration
├── api/             HTTP layer — routers/endpoints (empty so far)
├── core/            Cross-cutting infra: DB engine/session, security, logging
├── config/          Environment-based settings (pydantic-settings)
├── models/          SQLAlchemy ORM models
├── schemas/         Pydantic v2 request/response DTOs
├── repositories/    Data-access layer, wraps SQLAlchemy queries
├── services/        Business logic / use-case orchestration
├── prompts/         LLM prompt templates for the AI buyer persona
├── voice/           Speech-to-text / text-to-speech integration
└── evaluation/      Session scoring: strengths/weaknesses/recommendations

alembic/             Migrations (empty — no models yet to autogenerate from)
```

Each package's `__init__.py` has a short docstring describing its
responsibility and where its boundaries are (e.g. `api/` never talks to the
database directly; `services/` never touches HTTP).

## Database migrations (Alembic)

`alembic/env.py` is wired to `app.config.settings.get_settings().database_url`
and `app.models.base.Base.metadata`, so migrations always target the same
database as the running app and can autogenerate from models once they
exist. Once you have models and a reachable database:

```bash
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
```

## What's scaffolded vs. not

Done:
- Poetry project with all required dependencies installed and locked
- All 9 required `app/` subpackages, each documented with its architectural role
- FastAPI app instance with CORS middleware, boots and serves `/docs`
- Settings loaded from `.env` via pydantic-settings
- SQLAlchemy engine/session factory and declarative `Base`
- Alembic initialized and wired to settings + model metadata

Not done (by design — see task scope):
- No API endpoints/routers registered (`api_router` is empty)
- No SQLAlchemy models, Pydantic schemas, repositories, or services
- No prompt templates, voice integration, or evaluation logic
- No live database connection or migrations have been run
