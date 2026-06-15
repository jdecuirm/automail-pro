from collections.abc import AsyncGenerator

import pytest
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
