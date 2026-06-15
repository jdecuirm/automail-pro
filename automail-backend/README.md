# automail-backend

FastAPI backend for AutoMail Pro — an AI-powered lead outreach automation system.

## Setup

```bash
cp .env.example .env
# Fill in DATABASE_URL, API keys, and secrets
uv sync
```

## Database setup

Requires PostgreSQL 18 running locally.

```bash
# Create the database and user (run as postgres superuser)
psql -c "CREATE USER automail WITH PASSWORD 'yourpassword';"
psql -c "CREATE DATABASE automail OWNER automail;"

# Apply migrations
uv run alembic upgrade head
```

## Run

```bash
uv run uvicorn app.main:app --reload
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

## Test

Tests use the same database with per-test rollbacks (NullPool, no shared state).

```bash
uv run pytest
uv run pytest -v          # verbose
uv run pytest -x          # stop on first failure
```

## Lint

```bash
uv run ruff check .
uv run ruff format .
```

## Migrations

```bash
# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "describe what changed"

# Apply pending migrations
uv run alembic upgrade head

# Roll back one step
uv run alembic downgrade -1

# Roll back to clean state
uv run alembic downgrade base
```
