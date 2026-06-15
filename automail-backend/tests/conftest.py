from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


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
