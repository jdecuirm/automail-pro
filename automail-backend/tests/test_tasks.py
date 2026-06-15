from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.tasks.smoke import ping


def test_smoke_task_direct() -> None:
    result = ping.apply(kwargs={"message": "hello"})
    assert result.successful()
    data = result.result
    assert data["message"] == "hello"
    assert "echoed_at" in data
    assert "worker_id" in data


async def test_ping_endpoint(celery_app_eager: object) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/tasks/ping")
    assert response.status_code == 200
    body = response.json()
    assert "task_id" in body
    assert body["status"] == "queued"


async def test_task_status_pending(celery_app_eager: object) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/tasks/00000000-0000-0000-0000-000000000000/status")
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "00000000-0000-0000-0000-000000000000"
    assert body["state"] == "PENDING"
    assert body["result"] is None


async def test_ping_then_status_success(celery_app_eager: object) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ping_resp = await client.post("/api/tasks/ping")
        task_id = ping_resp.json()["task_id"]
        status_resp = await client.get(f"/api/tasks/{task_id}/status")
    body = status_resp.json()
    assert body["state"] == "SUCCESS"
    assert body["result"]["message"] == "pong"
