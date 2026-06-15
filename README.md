# AutoMail Pro

AI-powered B2B lead outreach automation. Upload a CSV of leads, the system scrapes
their public web presence, Claude generates personalized cold emails, you review and
approve, and emails are sent through your own Gmail account with open tracking.

## Architecture

```
automail-frontend/   Vite + React + TypeScript (Render)
automail-backend/    FastAPI + Celery + PostgreSQL + Redis (Railway)
```

**Pipeline:**  
CSV upload → scraping (httpx + Playwright) → AI generation (Claude Haiku) →  
human review → Gmail send → open-pixel tracking → metrics dashboard

## Tech Stack

| Layer    | Technology                                        |
| -------- | ------------------------------------------------- |
| Backend  | FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2 |
| Queue    | Celery 5 + Redis                                  |
| Database | PostgreSQL 18                                     |
| AI       | Anthropic Claude Haiku (claude-haiku-4-5)         |
| Email    | Gmail API via OAuth 2.0                           |
| Frontend | React 18 + TypeScript + Tailwind CSS v4           |
| Data     | TanStack Query, react-hook-form + zod             |
| Deploy   | Railway (backend) + Render (frontend)             |

## Quickstart

### Backend

```bash
cd automail-backend
cp .env.example .env   # fill in secrets
uv sync
uv run uvicorn app.main:app --reload
# → http://localhost:8000
```

See [automail-backend/README.md](automail-backend/README.md) for full setup.

### Frontend

```bash
cd automail-frontend
cp .env.example .env
npm install
npm run dev
# → http://localhost:5173
```

See [automail-frontend/README.md](automail-frontend/README.md) for full setup.

## Development Status

| Stage | Description                           | Status  |
| ----- | ------------------------------------- | ------- |
| A     | Scaffold — FastAPI hello + Vite hello | ✅ Done |
| B     | PostgreSQL + SQLAlchemy + Alembic     | ⏳ Next |
| C     | Celery + Redis + smoke task           | —       |
| D     | CSV upload + lead persistence         | —       |
| E     | Scraping pipeline                     | —       |
| F     | Claude API + email generation         | —       |
| G     | Gmail OAuth + sending                 | —       |
| H     | Tracking pixel                        | —       |
| I     | React dashboard                       | —       |
| J     | Tests + security audit                | —       |
| K     | Deploy                                | —       |

## Security & Ethics

- Scraping respects `robots.txt` and rate limits (1 req/2 s per domain)
- Human approval required before every email send — no auto-send
- Gmail refresh tokens encrypted at rest (Fernet)
- Lead PII encrypted in PostgreSQL
- Tracking pixel URL signed with HMAC

## License

MIT
