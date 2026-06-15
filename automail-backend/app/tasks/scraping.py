import logging
import time
from typing import Any

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="leads.scrape", bind=True, max_retries=3)
def scrape_lead(self: Any, lead_id: str) -> dict[str, str]:
    logger.info("TODO: scrape lead %s (will be implemented in Stage E)", lead_id)
    time.sleep(1)
    return {"lead_id": lead_id, "status": "placeholder"}
