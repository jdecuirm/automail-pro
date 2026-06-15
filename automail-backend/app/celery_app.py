from celery import Celery
from celery.signals import worker_process_init

from app.config import get_settings


@worker_process_init.connect
def _reinit_db_engine(**kwargs: object) -> None:
    """Reinitialize the async DB engine after Celery forks a worker process.

    Each forked worker must own its own engine so asyncpg connections are
    created inside the worker's own event loop (not the parent's).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    import app.database as db

    db.engine = db._build_engine()
    db.AsyncSessionLocal = async_sessionmaker(db.engine, expire_on_commit=False)


def _create_celery() -> Celery:
    settings = get_settings()
    app = Celery("automail")
    app.conf.update(
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,
        task_soft_time_limit=540,
        worker_max_tasks_per_child=100,
        result_expires=3600,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = _create_celery()
# Explicit include as fallback — autodiscover_tasks(["app"]) is deferred and
# may not fire before a task is dispatched in some startup sequences.
celery_app.conf.include = [
    "app.tasks.smoke",
    "app.tasks.scraping",
    "app.tasks.generation",
    # "app.tasks.sending",  # Stage G — add when gmail_sender.py is implemented
]
