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

# Apply migrations (includes demo user seed data)
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
```

## API endpoints (Stage D)

> **Note:** Authentication is not yet implemented. All endpoints use a hardcoded
> demo user (`demo@automail.local`). This is temporary and will be replaced in
> Stage J.

### Sample CSV format

```csv
name,email,company,website,linkedin_url
Alice Johnson,alice@acme.com,Acme Corp,https://acme.com,https://linkedin.com/in/alice
Bob Smith,bob@startup.io,Startup Inc,,
```

Required columns: `name`, `email`  
Optional: `company`, `website`, `linkedin_url`  
Column names are case-insensitive. Common aliases like `full_name`, `email_address`,
`company_name`, `organization` are also accepted.

### Campaigns

```bash
# Upload a CSV and create a campaign
curl -X POST http://localhost:8000/api/campaigns \
  -F "name=My Campaign" \
  -F "file=@leads.csv;type=text/csv"
# → 201 { campaign_id, total_rows, valid_leads, invalid_leads, validation_errors }

# List all campaigns
curl http://localhost:8000/api/campaigns
# → 200 [{ id, name, status, total_leads, created_at }]

# Get campaign detail
curl http://localhost:8000/api/campaigns/<campaign_id>
# → 200 { id, name, status, csv_filename, total_leads, created_at, updated_at }

# List leads (paginated)
curl "http://localhost:8000/api/campaigns/<campaign_id>/leads?page=1&page_size=50"
# → 200 { items, total, page, page_size }
```

### Background tasks (smoke test)

```bash
# Fire a smoke ping task
curl -s -X POST http://localhost:8000/api/tasks/ping | python3 -m json.tool

# Check task status
curl -s http://localhost:8000/api/tasks/<task_id>/status | python3 -m json.tool
```

## Scraping pipeline (Stage E)

When a CSV is uploaded, a `leads.scrape` Celery task is dispatched for each lead
**after the DB transaction commits** (prevents workers from querying uncommitted rows).

### Pipeline flow per lead

```
cache check ──► robots.txt check ──► rate limiter wait ──► scrape_static (httpx + BS4)
                                                               │
                                               empty/JS? ──►  scrape_dynamic (Playwright)
                                                               │
                                               both fail? ──►  Lead.status = failed
                                                               │
                                                          ──►  LeadResearch created
                                                               Lead.status = researched
```

### Ethical scraping principles (non-negotiable)

- **robots.txt**: checked before every domain. `404` → allow, `403` → deny, timeout → allow.
- **Rate limiting**: max 1 request per 2 seconds per domain (Redis-backed, worker-safe).
- **User-Agent**: honest — `AutoMailPro/1.0 (+https://github.com/jdecuirm/automail-pro)`
- **Cache**: scraped content cached 7 days in Redis (avoids hammering same domain).
- **LinkedIn**: only `/company/` public pages. Personal `/in/` profiles are skipped — they require login (ToS violation).
- **No stealth**: no anti-detection plugins, no headless fingerprint spoofing.

### Scraping dependencies

```bash
# Playwright browser (one-time download, ~113 MB)
uv run playwright install chromium
```

## Email generation pipeline (Stage F)

When a lead's scraping completes and `LeadResearch` is persisted, a `leads.generate`
Celery task is automatically dispatched. The task calls **Claude Haiku 4.5** to write a
personalized B2B cold email based on the scraped research.

### Generation flow

```
scraping completes → leads.generate dispatched → Claude Haiku 4.5 called
                                                       │
                                   parse JSON response (subject + body_text + body_html)
                                                       │
                                        Email row persisted (status = draft)
                                                       │
                                        Lead.status = drafted
```

### Email review endpoint

```bash
# List all email drafts for a campaign (status = draft)
curl http://localhost:8000/api/campaigns/<campaign_id>/emails | python3 -m json.tool
# → 200 [{ id, lead_id, lead_name, subject, body_text, body_html, status, created_at }]
```

### PII safety

- Lead email addresses are **never sent to Claude**. `build_user_prompt()` accepts
  `lead_email` but intentionally excludes it from the prompt.
- Only the lead's first name, company name, and scraped research summary are included.
- The Claude model is locked to `claude-haiku-4-5` (cost-efficient, set in `config.py`).

### Retry behavior

The `leads.generate` task retries automatically on:

- `httpx.TimeoutException`
- `anthropic.APIConnectionError`

Up to 2 retries with exponential backoff (max 120s).

## Test

Tests require both PostgreSQL 18 and Redis to be running locally.

Endpoint tests use SQLAlchemy savepoints (`join_transaction_mode="create_savepoint"`)
for isolation — all DB changes from tests are rolled back automatically.

```bash
uv run pytest
uv run pytest -v                              # verbose
uv run pytest -x                              # stop on first failure
uv run pytest tests/test_csv_parser.py        # CSV parser tests only
uv run pytest tests/test_campaign_endpoints.py  # endpoint tests only
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
