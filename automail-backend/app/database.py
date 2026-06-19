import contextlib
from collections.abc import AsyncGenerator, AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    # NullPool required: Celery workers call asyncio.run() which creates a new event loop
    # per task. asyncpg connections are loop-bound, so a persistent pool would fail with
    # "Future attached to a different loop". NullPool creates a fresh connection per session.
    return create_async_engine(settings.database_url, echo=False, poolclass=NullPool)


engine = _build_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@contextlib.asynccontextmanager
async def get_session_context() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextlib.asynccontextmanager
async def get_task_session() -> AsyncIterator[AsyncSession]:
    """Session for Celery tasks.

    Creates a fresh engine inside the running event loop so asyncpg connections
    are bound to the correct loop (asyncio.run() creates a new loop per task;
    module-level engines are attached to the parent process loop after fork).
    """
    task_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    factory = async_sessionmaker(task_engine, expire_on_commit=False)
    try:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    finally:
        await task_engine.dispose()
