# AutoMail Pro — Project Context for Claude Code

## What this is

An AI-powered lead outreach automation system. Users upload a CSV of leads,
the system scrapes each lead's public web presence (website, LinkedIn public
page), Claude generates personalized cold emails based on the research, the
user reviews/approves in a dashboard, and emails are sent via the user's
Gmail with open tracking (pixel-based). Built as a portfolio piece for
B2B/sales SaaS use cases.

## Owner

Jorge Decuir (github.com/jdecuirm). Solo developer.

## Core principles

- Build incrementally by stages (A through K). STOP at each checkpoint and
  wait for explicit green light before advancing.
- NO commits or pushes without explicit approval.
- Spec-first workflow via Superpowers plugin where applicable.
- Clean, production-quality code. This is a portfolio piece — it must impress.
- English for all code, comments, docs, UI, and commits (Conventional Commits).
- Type hints on all Python functions. Google-style docstrings on public APIs.
- Security and ethical scraping are NOT optional — see Security section.

## Tech stack (do not deviate without asking)

### Backend

- Python 3.13
- Package manager: uv (NOT pip/poetry directly)
- Web framework: FastAPI 0.115+ with uvicorn[standard]
- Validation: Pydantic v2 + pydantic-settings
- Database: PostgreSQL 18 (Railway PostgreSQL service in prod)
- ORM: SQLAlchemy 2.x (async) + Alembic for migrations
- Task queue: Celery 5.6.3 with Redis 5.2.1 as broker AND result backend
  (Celery pins Redis to <=5.2.1)
- Task monitoring: Flower (Celery monitoring UI)
- HTTP client: httpx (async)
- Scraping: BeautifulSoup4 for static pages, Playwright for JS-heavy pages
- LLM: Anthropic Claude API, model claude-haiku-4-5 ONLY (cost-efficient)
- Email sending: Google Gmail API via OAuth 2.0 (user delegates)
- Auth (app-level): JWT via python-jose OR simple session for portfolio scope

### Frontend

- Vite + React 18+ + TypeScript
- Styling: Tailwind CSS
- Data fetching: TanStack Query (React Query)
- Forms: react-hook-form + zod
- Charts (dashboard metrics): Recharts
- CSV parsing client-side: Papa Parse
- Routing: React Router v6+

### Deployment

- Backend + Worker: Railway (separate services share env vars)
- PostgreSQL: Railway PostgreSQL addon
- Redis: Railway Redis addon
- Frontend: Render static site
- Tracking pixel endpoint: same Railway backend (custom domain optional)

### Tooling

- Tests: pytest, pytest-asyncio
- Linting: ruff
- Type checking: mypy (strict on app/, lenient on tests/)
- Pre-commit hooks: ruff + mypy + detect-secrets

## Project structure

```
automail-pro/
├── CLAUDE.md
├── README.md
├── LICENSE
├── .gitignore
├── docs/
│   └── superpowers/specs/      # Spec docs per stage (Superpowers plugin)
├── automail-backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/                # DB migrations
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app
│   │   ├── config.py           # pydantic-settings
│   │   ├── celery_app.py       # Celery config
│   │   ├── database.py         # SQLAlchemy session
│   │   ├── models/             # SQLAlchemy models
│   │   │   ├── lead.py
│   │   │   ├── email.py
│   │   │   ├── campaign.py
│   │   │   └── tracking_event.py
│   │   ├── schemas/            # Pydantic schemas (request/response)
│   │   ├── api/                # FastAPI routers
│   │   │   ├── leads.py
│   │   │   ├── campaigns.py
│   │   │   ├── emails.py
│   │   │   ├── tracking.py     # Open tracking pixel endpoint
│   │   │   └── oauth.py        # Gmail OAuth callback
│   │   ├── services/           # Business logic
│   │   │   ├── csv_parser.py
│   │   │   ├── scraper.py
│   │   │   ├── llm_client.py   # Claude API wrapper
│   │   │   ├── email_generator.py
│   │   │   ├── gmail_sender.py
│   │   │   └── tracking.py
│   │   ├── tasks/              # Celery tasks
│   │   │   ├── scraping.py     # async scrape lead
│   │   │   ├── generation.py   # async generate email
│   │   │   └── sending.py      # async send via Gmail
│   │   └── utils/
│   │       ├── pii_redaction.py
│   │       ├── rate_limit.py
│   │       └── url_signer.py   # signed URLs for tracking
│   └── tests/
└── automail-frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── pages/
        │   ├── Dashboard.tsx
        │   ├── CampaignNew.tsx
        │   ├── CampaignDetail.tsx
        │   └── EmailReview.tsx
        ├── components/
        │   ├── LeadTable.tsx
        │   ├── EmailEditor.tsx
        │   ├── MetricsCharts.tsx
        │   └── CSVUpload.tsx
        ├── api/
        │   └── client.ts       # TanStack Query setup
        └── types/
            └── api.ts          # TypeScript types
```

## Domain model (PostgreSQL)

### Tables (high level — Alembic generates exact schema)

- `users` — app users (the freelancers/sales people using AutoMail)
- `gmail_credentials` — encrypted refresh tokens per user
- `campaigns` — outreach campaigns (a CSV upload = a campaign)
- `leads` — one row per lead in a CSV
- `lead_research` — scraped data per lead (raw + summary)
- `emails` — generated emails (one per lead, lifecycle: draft to approved to sent)
- `tracking_events` — opens (and clicks if extended later)

### Lead lifecycle status

`uploaded -> scraping -> researched -> generating -> drafted ->
approved/rejected -> sending -> sent -> opened`

## Pipeline flow

1. User uploads CSV (name, email, company, website, linkedin_url optional)
2. Backend parses CSV, creates campaign + N leads (status=uploaded)
3. Celery dispatches scraping tasks (one per lead, rate-limited)
4. Scraper extracts company info + LinkedIn public bio if available
5. Celery dispatches LLM tasks: Claude Haiku 4.5 summarizes research +
   generates personalized email draft
6. Frontend dashboard shows campaign progress, lets user review/edit/approve
   each email
7. User clicks "Send approved" -> Celery dispatches sending task
8. Gmail API sends email through user's account (OAuth-delegated)
9. Email includes invisible tracking pixel: GET /api/track/open/{signed_token}
10. When pixel loads -> tracking endpoint logs event, updates lead status to opened
11. Dashboard updates with real-time open rate metrics

## Security & ethics (NOT NEGOTIABLE)

### Scraping ethics

- Always respect robots.txt — use a robots.txt parser before scraping
- Rate-limit per domain: max 1 request per 2 seconds
- User-Agent: identify ourselves honestly (not impersonate browsers)
- ONLY scrape publicly accessible pages (no login bypass)
- Cache scraped content for 7 days (avoid hammering same domain)
- LinkedIn: ONLY public profile pages, NO logged-in scraping (violates ToS)

### Secrets handling

- Anthropic API key, Google OAuth secrets ONLY in .env (never committed)
- Gmail refresh tokens encrypted at rest (use cryptography.Fernet)
- JWT secret rotates per environment
- pre-commit hook with detect-secrets to prevent accidental commits

### PII handling

- Lead emails are PII — encrypt at rest in PostgreSQL (pgcrypto or app-level)
- Redact PII before sending to Claude API where possible
- Logs MUST NOT contain raw email addresses or scraped personal data
- Compliance disclaimer in README: this tool is for B2B outreach with
  legitimate interest only (GDPR/CAN-SPAM compliance is user's responsibility)

### Tracking pixel security

- URL signed with HMAC to prevent forgery:
  /api/track/open/{base64(lead_id|email_id|signature)}
- Tracking events deduped (one open per lead+email pair counts once)
- Pixel returns transparent 1x1 PNG with no-cache headers
- Allow user opt-out per email (footer link disables tracking for that lead)

### Email deliverability

- DKIM/SPF: user's Gmail handles this automatically (we don't touch it)
- Rate-limit sending: max 50 emails/day per Gmail account (free tier limit)
- Honor unsubscribe: every email includes unsubscribe link (mailto: footer)
- NEVER auto-send: human approval required for every email

## Build stages & checkpoints

- Stage A: Scaffold (monorepo structure, uv init, FastAPI hello, Vite hello) ✅
- Stage B: PostgreSQL + SQLAlchemy + Alembic + initial migrations ✅
- Stage C: Celery + Redis setup + smoke task ✅
- Stage D: CSV upload + lead parsing + DB persistence ✅
- Stage E: Scraping pipeline (httpx + BeautifulSoup + Playwright fallback) ✅
- Stage F: Claude API integration + email generation prompt ✅
- Stage G: Gmail OAuth + email sending ✅
- Stage H: Tracking pixel endpoint (Pro Lite feature) ✅
- Stage I: React dashboard (campaigns + leads + email review) ✅
- Stage J: README + LICENSE + CI + tests + security audit ✅
- Stage K: Deploy (Railway backend + worker + Postgres + Redis, Render frontend)

At each checkpoint: report what was done, confirm it runs, WAIT for green light.

## Config defaults (app/config.py via pydantic-settings)

```
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/automail

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Anthropic
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-haiku-4-5
CLAUDE_MAX_TOKENS=1024

# Google OAuth (Gmail)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/oauth/google/callback

# App
APP_SECRET_KEY=        # JWT signing
TRACKING_SECRET_KEY=   # HMAC for tracking URLs
APP_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:5173

# Scraping
SCRAPE_RATE_LIMIT_SECONDS=2
SCRAPE_CACHE_TTL_DAYS=7
SCRAPE_USER_AGENT=AutoMailPro/1.0 (+https://github.com/jdecuirm/automail-pro)

# Email
MAX_EMAILS_PER_USER_PER_DAY=50
```

## What NOT to do

- Do not use localStorage for sensitive data (only for UI state)
- Do not hardcode secrets or API keys
- Do not push to git without explicit approval
- Do not bypass robots.txt or LinkedIn ToS
- Do not auto-send emails without human approval
- Do not log raw email addresses or PII in plaintext
- Do not skip migrations (always create Alembic revision for schema changes)
- Do not store Gmail refresh tokens unencrypted
- When creating folders for project assets (screenshots, diagrams,
  branding images, marketing materials), use `assets/` NOT `docs/`.
  The `docs/` folder is reserved for the Superpowers plugin
  workspace and should not be used for public documentation.
