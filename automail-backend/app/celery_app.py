from celery import Celery

from app.config import get_settings


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
celery_app.autodiscover_tasks(["app"])
