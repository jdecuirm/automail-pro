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

## Background tasks (Celery + Redis)

Requires Redis running locally on port 6379.

```bash
# Start the Celery worker
uv run celery -A app.celery_app:celery_app worker --loglevel=info

# Start Flower monitoring UI (http://localhost:5555)
uv run celery -A app.celery_app:celery_app flower --port=5555

# Smoke-test the task queue
curl -s -X POST http://localhost:8000/api/tasks/ping | python3 -m json.tool
# Copy the task_id from above, then:
curl -s http://localhost:8000/api/tasks/<task_id>/status | python3 -m json.tool
```

## Test

Tests require both PostgreSQL 18 and Redis to be running locally.
Celery task tests run in eager mode (synchronous, no real broker needed for task logic,
but Redis is still used for the result backend in status-endpoint tests).

```bash
uv run pytest
uv run pytest -v          # verbose
uv run pytest -x          # stop on first failure
uv run pytest tests/test_tasks.py   # Celery tests only
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
