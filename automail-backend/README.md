# automail-backend

FastAPI backend for AutoMail Pro — an AI-powered lead outreach automation system.

## Setup

```bash
cp .env.example .env
# Edit .env and fill in your API keys and secrets
uv sync
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

## Test

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check .
uv run ruff format .
```
