from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from app.api.campaigns import router as campaigns_router
from app.api.emails import router as emails_router
from app.api.oauth import router as oauth_router
from app.api.tasks import router as tasks_router
from app.api.tracking import router as tracking_router
from app.api.users import router as users_router
from app.celery_app import celery_app
from app.config import get_settings
from app.database import get_session_context
from app.limiter import limiter

logger = logging.getLogger(__name__)

_HEALTH_CACHE_TTL = 5.0
_health_cache: dict[str, Any] = {}


class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    logger.info("AutoMail Pro backend starting — base_url=%s", settings.app_base_url)

    if settings.anthropic_api_key is None:
        logger.warning("ANTHROPIC_API_KEY not set — email generation will fail")
    if not settings.google_client_id:
        logger.warning("GOOGLE_CLIENT_ID not set — Gmail OAuth will fail")
    if settings.google_client_secret is None:
        logger.warning("GOOGLE_CLIENT_SECRET not set — Gmail OAuth will fail")
    if settings.app_secret_key.get_secret_value() == "dev-secret-change-me":
        logger.warning(
            "APP_SECRET_KEY is using the insecure dev default — set a strong value in .env"
        )
    if settings.tracking_secret_key.get_secret_value() == "dev-tracking-key-change-me":
        logger.warning(
            "TRACKING_SECRET_KEY is using the insecure dev default — set a strong value in .env"
        )

    yield
    logger.info("AutoMail Pro backend shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title="AutoMail Pro API",
        description=(
            "AI-powered B2B lead outreach automation. Upload a CSV of leads, "
            "scrape their public web presence, generate personalized cold emails "
            "with Claude Haiku, review and approve in a dashboard, then send via Gmail "
            "with HMAC-signed open tracking."
        ),
        version="0.1.0",
        contact={"name": "Jorge Decuir", "url": "https://github.com/jdecuirm"},
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        openapi_tags=[
            {
                "name": "campaigns",
                "description": "Campaign lifecycle: create from CSV, list, detail, bulk-send.",
            },
            {
                "name": "emails",
                "description": "Email draft management: approve, reject, edit individual drafts.",
            },
            {
                "name": "oauth",
                "description": "Gmail OAuth 2.0: connect, disconnect, and check connection status.",
            },
            {
                "name": "tracking",
                "description": "Open-pixel tracking endpoint — HMAC-signed 1×1 PNG.",
            },
            {
                "name": "users",
                "description": "Sender profile: name and company used in AI-generated signatures.",
            },
            {
                "name": "tasks",
                "description": "Background task smoke-test endpoints (ping / status).",
            },
            {
                "name": "health",
                "description": "Service health check with dependency probes (DB, Redis, Celery).",
            },
        ],
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(_SecurityHeadersMiddleware)

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)

    application.include_router(campaigns_router)
    application.include_router(emails_router)
    application.include_router(tasks_router)
    application.include_router(oauth_router)
    application.include_router(tracking_router)
    application.include_router(users_router)

    return application


app = create_app()


async def _check_database() -> str:
    try:
        async with asyncio.timeout(2):
            async with get_session_context() as session:
                await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


async def _check_redis() -> str:
    import redis.asyncio as aioredis

    settings = get_settings()
    r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        async with asyncio.timeout(2):
            await r.ping()
        return "ok"
    except Exception as exc:
        return f"error: {exc}"
    finally:
        await r.aclose()


async def _check_celery() -> str:
    def _sync_ping() -> bool:
        inspect = celery_app.control.inspect(timeout=1)
        result = inspect.ping()
        return bool(result)

    try:
        has_workers = await asyncio.wait_for(asyncio.to_thread(_sync_ping), timeout=2)
        return "ok" if has_workers else "no workers available"
    except asyncio.TimeoutError:
        return "timeout"
    except Exception as exc:
        return f"error: {exc}"


@app.get("/health", tags=["health"], summary="Service health check")
async def health() -> JSONResponse:
    """Check liveness of all dependencies: PostgreSQL, Redis, and Celery worker."""
    now = time.monotonic()
    if _health_cache and (now - float(_health_cache["ts"])) < _HEALTH_CACHE_TTL:
        return JSONResponse(
            content=_health_cache["data"],
            status_code=int(_health_cache["code"]),
        )

    db_status, redis_status, celery_status = await asyncio.gather(
        _check_database(),
        _check_redis(),
        _check_celery(),
    )

    checks = {"database": db_status, "redis": redis_status, "celery": celery_status}
    all_ok = all(v == "ok" for v in checks.values())
    overall = "ok" if all_ok else "degraded"
    http_code = 200 if all_ok else 503

    data: dict[str, Any] = {
        "status": overall,
        "version": "0.1.0",
        "checks": checks,
    }
    _health_cache.update({"ts": now, "data": data, "code": http_code})
    return JSONResponse(content=data, status_code=http_code)


@app.get("/", tags=["health"], summary="Root — API info", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "AutoMail Pro API", "docs": "/docs"}
