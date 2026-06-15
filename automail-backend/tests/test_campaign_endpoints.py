from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from httpx import AsyncClient

FIXTURES = Path(__file__).parent / "fixtures"

_VALID_CSV = (FIXTURES / "sample_leads_valid.csv").read_bytes()
_MIXED_CSV = (FIXTURES / "sample_leads_mixed.csv").read_bytes()


def _csv_file(filename: str, content: bytes) -> dict:
    return {"file": (filename, content, "text/csv")}


# ---------------------------------------------------------------------------
# Campaign creation
# ---------------------------------------------------------------------------


async def test_create_campaign_with_valid_csv(campaign_client: AsyncClient) -> None:
    with patch("app.services.campaign_service.scrape_lead") as mock_task:
        mock_task.delay = MagicMock()
        resp = await campaign_client.post(
            "/api/campaigns",
            files=_csv_file("valid.csv", _VALID_CSV),
            data={"name": "Valid Campaign"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert uuid.UUID(body["campaign_id"])
    assert body["total_rows"] == 5
    assert body["valid_leads"] == 5
    assert body["invalid_leads"] == 0
    assert body["validation_errors"] == []


async def test_create_campaign_with_invalid_csv(campaign_client: AsyncClient) -> None:
    """All rows have bad emails → no valid leads → 422."""
    bad_csv = b"name,email\nAlice,not-email\nBob,also-bad\n"
    resp = await campaign_client.post(
        "/api/campaigns",
        files=_csv_file("bad.csv", bad_csv),
        data={"name": "Bad Campaign"},
    )
    assert resp.status_code == 422
    assert "No valid leads" in resp.json()["detail"]


async def test_create_campaign_too_large(campaign_client: AsyncClient) -> None:
    """File exceeding 5 MB → 413."""
    large_content = b"name,email\n" + b"Alice,alice@example.com\n" * 300_000
    resp = await campaign_client.post(
        "/api/campaigns",
        files=_csv_file("big.csv", large_content),
        data={"name": "Large Campaign"},
    )
    assert resp.status_code == 413


async def test_create_campaign_dispatches_scrape_tasks(campaign_client: AsyncClient) -> None:
    """Verify scrape_lead.delay() is called once per valid lead."""
    with patch("app.services.campaign_service.scrape_lead") as mock_task:
        mock_task.delay = MagicMock()
        resp = await campaign_client.post(
            "/api/campaigns",
            files=_csv_file("valid.csv", _VALID_CSV),
            data={"name": "Dispatch Test"},
        )

    assert resp.status_code == 201
    # 5 valid leads in sample_leads_valid.csv
    assert mock_task.delay.call_count == 5
    # Each call receives a string UUID
    for call in mock_task.delay.call_args_list:
        uuid.UUID(call.args[0])  # raises if not a valid UUID


async def test_create_campaign_mixed_csv(campaign_client: AsyncClient) -> None:
    """Mixed CSV: 7 valid + 3 errors reported in response."""
    with patch("app.services.campaign_service.scrape_lead") as mock_task:
        mock_task.delay = MagicMock()
        resp = await campaign_client.post(
            "/api/campaigns",
            files=_csv_file("mixed.csv", _MIXED_CSV),
            data={"name": "Mixed Campaign"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["valid_leads"] == 7
    assert body["invalid_leads"] == 3
    assert len(body["validation_errors"]) == 3


# ---------------------------------------------------------------------------
# Listing campaigns
# ---------------------------------------------------------------------------


async def test_list_campaigns(campaign_client: AsyncClient) -> None:
    with patch("app.services.campaign_service.scrape_lead") as mock_task:
        mock_task.delay = MagicMock()
        create_resp = await campaign_client.post(
            "/api/campaigns",
            files=_csv_file("valid.csv", _VALID_CSV),
            data={"name": "List Test Campaign"},
        )
    campaign_id = create_resp.json()["campaign_id"]

    list_resp = await campaign_client.get("/api/campaigns")
    assert list_resp.status_code == 200
    campaigns = list_resp.json()
    ids = [c["id"] for c in campaigns]
    assert campaign_id in ids

    # Check required fields
    found = next(c for c in campaigns if c["id"] == campaign_id)
    assert found["name"] == "List Test Campaign"
    assert found["total_leads"] == 5
    assert "status" in found
    assert "created_at" in found


# ---------------------------------------------------------------------------
# Campaign detail
# ---------------------------------------------------------------------------


async def test_get_campaign_detail(campaign_client: AsyncClient) -> None:
    with patch("app.services.campaign_service.scrape_lead") as mock_task:
        mock_task.delay = MagicMock()
        create_resp = await campaign_client.post(
            "/api/campaigns",
            files=_csv_file("valid.csv", _VALID_CSV),
            data={"name": "Detail Campaign"},
        )
    campaign_id = create_resp.json()["campaign_id"]

    resp = await campaign_client.get(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == campaign_id
    assert body["name"] == "Detail Campaign"
    assert body["total_leads"] == 5
    assert body["csv_filename"] == "valid.csv"
    assert "updated_at" in body


async def test_get_campaign_not_found(campaign_client: AsyncClient) -> None:
    fake_id = "00000000-0000-0000-0000-999999999999"
    resp = await campaign_client.get(f"/api/campaigns/{fake_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Lead listing with pagination
# ---------------------------------------------------------------------------


async def test_list_leads_paginated(campaign_client: AsyncClient) -> None:
    with patch("app.services.campaign_service.scrape_lead") as mock_task:
        mock_task.delay = MagicMock()
        create_resp = await campaign_client.post(
            "/api/campaigns",
            files=_csv_file("valid.csv", _VALID_CSV),
            data={"name": "Pagination Campaign"},
        )
    campaign_id = create_resp.json()["campaign_id"]

    # Page 1 with page_size=3 from 5 total leads
    resp = await campaign_client.get(
        f"/api/campaigns/{campaign_id}/leads", params={"page": 1, "page_size": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 3
    assert len(body["items"]) == 3

    # Page 2 should have the remaining 2 leads
    resp2 = await campaign_client.get(
        f"/api/campaigns/{campaign_id}/leads", params={"page": 2, "page_size": 3}
    )
    body2 = resp2.json()
    assert len(body2["items"]) == 2
    assert body2["total"] == 5

    # Leads should have status=uploaded
    for lead in body["items"] + body2["items"]:
        assert lead["status"] == "uploaded"
        assert "email" in lead
        assert "name" in lead
