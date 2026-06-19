# Changelog

All notable changes to AutoMail Pro are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.1.0] — 2026-06-19

### Stage J — Production Readiness

#### Added

- Professional README with Mermaid architecture diagram, feature list, tech stack tables, quick start, and ethical considerations
- MIT LICENSE
- GitHub Actions CI: `backend-ci.yml` (Python 3.13 + uv, PostgreSQL 17, Redis 7) and `frontend-ci.yml` (Node 20, ESLint + Vitest + build)
- Security headers middleware: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`
- Enhanced `/health` endpoint with live DB / Redis / Celery checks, HTTP 503 on degraded, 5 s response cache
- Rate limiting via slowapi: 10/hour on campaign create, 5/hour on OAuth authorize, 100/hour on email approve
- `RATE_LIMITING_ENABLED` setting (default `true`; set `false` in CI/tests)
- `LOG_LEVEL` setting (default `INFO`)
- Startup warnings for missing optional secrets (ANTHROPIC_API_KEY, Google OAuth credentials, dev-default secret keys)
- FastAPI OpenAPI metadata: description, contact, license, per-tag descriptions
- SVG screenshot placeholders in `assets/screenshots/`
- Settings validation tests: `fernet_key` required, dev secrets rejected in production
- Frontend code splitting via `React.lazy` + per-route `<Suspense>` boundaries
- Vite `manualChunks`: vendor-react, vendor-ui, vendor-data, vendor-charts
- `RouteLoadingSkeleton` component for lazy-route loading states
- `pip-audit` added to dev dependencies (no vulnerabilities found)

#### Changed

- Logging format updated to `[LEVEL] module: message` with configurable level
- `main.py` refactored: security middleware, SlowAPI middleware, richer OpenAPI config

---

### Stage I — React Dashboard

#### Added

- Full React 19 + TypeScript + Tailwind CSS v4 frontend
- Campaign list, create, and detail pages (Overview / Leads / Emails / Metrics tabs)
- Email review dashboard: approve, reject, edit, bulk-send with sender-profile gate
- Sender profile (name + company) stored on the user model; settings sub-nav (Account / Gmail)
- `⌘K` command palette for quick navigation
- Open-rate metrics charts (Recharts)
- `useCampaign` polling — "review" status included in active states for live completion detection
- Lazy status recalculation in `get_campaign`: self-heals campaigns stuck in "review" after worker restarts

---

### Stage H — Tracking Pixel

#### Added

- HMAC-signed tracking pixel endpoint (`GET /api/track/open/{token}`)
- Returns transparent 1×1 PNG with no-cache headers
- Open events deduped per email+lead pair
- `TrackingEvent` model and migration

---

### Stage G — Gmail OAuth + Email Sending

#### Added

- Gmail OAuth 2.0 connect / disconnect / status endpoints
- Fernet-encrypted refresh and access tokens at rest
- Celery `send_email_task`: sends via Gmail API, updates lead status to `sent`
- Daily quota guard (50 emails/day, configurable)
- Bulk-send endpoint: dispatches all approved emails for a campaign
- `GmailCredential` model and migration

---

### Stage F — Claude Email Generation

#### Added

- Claude Haiku 4.5 integration (`llm_client.py`)
- `generate_email_draft` service: researched lead → personalized subject + body (text + HTML)
- Sender placeholder substitution: `[YOUR_NAME]` / `[YOUR_COMPANY]`
- `Email` model and migration; lead status lifecycle extended to `drafted`
- Celery `generate_email` task with auto-retry on network errors

---

### Stage E — Scraping Pipeline

#### Added

- Static scraper (httpx + BeautifulSoup4) with Playwright fallback for JS-heavy pages
- `robots.txt` compliance checker (Redis-cached 24 h)
- Redis-backed per-domain rate limiter (1 req / 2 s)
- 7-day scrape cache to avoid hammering repeat domains
- LinkedIn: company pages only (`/company/`); personal `/in/` profiles skipped
- `LeadResearch` model and migration

---

### Stage D — CSV Upload + Lead Persistence

#### Added

- `POST /api/campaigns` multipart CSV upload endpoint
- Client-side and server-side CSV validation (required columns, row limits)
- `Campaign` and `Lead` models with full status lifecycle
- Alembic migrations for campaigns and leads tables

---

### Stage C — Celery + Redis

#### Added

- Celery 5 application with Redis broker + result backend
- Smoke task (`ping`) with Flower monitoring UI
- `POST /api/tasks/ping` and `GET /api/tasks/{id}/status` endpoints

---

### Stage B — PostgreSQL + SQLAlchemy + Alembic

#### Added

- SQLAlchemy 2 async engine with `asyncpg` driver
- Alembic migration tooling with naming conventions
- `users` table with demo-user seed data
- Transactional test fixture using savepoints

---

### Stage A — Scaffold

#### Added

- Monorepo layout: `automail-backend/` (uv + FastAPI) + `automail-frontend/` (Vite + React + TypeScript)
- FastAPI app skeleton with CORS and `/health` endpoint
- Vite dev server with Tailwind CSS v4 and shadcn/ui bootstrap
