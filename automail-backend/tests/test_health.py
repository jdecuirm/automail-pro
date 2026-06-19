from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_returns_expected_structure() -> None:
    """Health endpoint always returns the correct JSON structure.

    Status is 200 ("ok") when all deps are reachable, 503 ("degraded") when any
    dependency is unavailable.  In the test environment Redis and Celery are
    typically not present, so we accept either — the structure is what matters.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "0.1.0"
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "celery" in data["checks"]
