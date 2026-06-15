from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
from celery import Celery
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.database import get_db
from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # NullPool avoids event-loop conflicts: each test gets fresh connections
    # rather than reusing a pool bound to the module-import-time event loop.
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
async def transactional_session() -> AsyncGenerator[AsyncSession, None]:
    """Session backed by a rolled-back outer transaction for test isolation.

    The service layer calls session.commit() freely; those commits go to a
    SAVEPOINT, not the real database.  The outer transaction rolls back at
    the end of the test, leaving the DB clean.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.connect() as conn:
        async with conn.begin() as outer_tx:
            session = async_sessionmaker(
                conn,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )()
            yield session
            await session.close()
            await outer_tx.rollback()
    await engine.dispose()


@pytest.fixture
async def campaign_client(
    transactional_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX test client wired to the transactional session."""

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield transactional_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Celery fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def celery_app_eager() -> Generator[Celery, Any, None]:
    from app.celery_app import celery_app
    from app.tasks.smoke import ping

    # Task.bind() reads from_config only once at import time, so updating conf
    # later doesn't change already-bound task attributes. We must patch both:
    # the conf (silences Celery's warning check) and the task class attribute
    # (the actual value used by celery.app.trace when deciding to store results).
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_store_eager_result=True,
    )
    ping.store_eager_result = True
    yield celery_app
    celery_app.conf.update(
        task_always_eager=False,
        task_eager_propagates=False,
        task_store_eager_result=False,
    )
    ping.store_eager_result = False
