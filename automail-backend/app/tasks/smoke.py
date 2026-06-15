import logging
import time
from datetime import UTC, datetime
from typing import Any

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="smoke.ping", bind=True)
def ping(self: Any, message: str = "ping") -> dict[str, Any]:
    logger.info("smoke.ping message=%r task_id=%s", message, self.request.id)
    if not self.request.called_directly:
        time.sleep(2)
    return {
        "message": message,
        "echoed_at": datetime.now(UTC).isoformat(),
        "worker_id": self.request.hostname or "local",
    }
