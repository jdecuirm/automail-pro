from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter

from app.celery_app import celery_app

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/ping")
async def ping_task() -> dict[str, str]:
    from app.tasks.smoke import ping

    result = ping.delay(message="pong")
    return {"task_id": result.id, "status": "queued"}


@router.get("/{task_id}/status")
async def task_status(task_id: str) -> dict[str, Any]:
    result = AsyncResult(task_id, app=celery_app)
    state = result.state
    payload: dict[str, Any] = {
        "task_id": task_id,
        "state": state,
        "result": None,
        "error": None,
    }
    if state == "SUCCESS":
        payload["result"] = result.result
    elif state == "FAILURE":
        payload["error"] = str(result.info)
    return payload
