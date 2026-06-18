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


# ---------------------------------------------------------------------------
# Email listing
# ---------------------------------------------------------------------------


async def test_list_emails_empty(campaign_client, transactional_session):
    """GET /api/campaigns/{id}/emails returns empty list when no drafts."""
    import uuid

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="Email List Test",
        status=CampaignStatus.generating,
        total_leads=0,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    resp = await campaign_client.get(f"/api/campaigns/{campaign.id}/emails")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_emails_returns_drafts(campaign_client, transactional_session):
    """GET /api/campaigns/{id}/emails returns Email rows for leads in that campaign."""
    import uuid

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.email import Email, EmailStatus
    from app.models.lead import Lead, LeadStatus

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="Draft Email Campaign",
        status=CampaignStatus.review,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Alice",
        email="alice@acme.com",
        status=LeadStatus.drafted,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    email = Email(
        lead_id=lead.id,
        subject="Quick question about Acme",
        body_text="Hi Alice,\n\nI noticed...",
        body_html="<p>Hi Alice,</p>",
        status=EmailStatus.draft,
    )
    transactional_session.add(email)
    await transactional_session.flush()

    resp = await campaign_client.get(f"/api/campaigns/{campaign.id}/emails")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["subject"] == "Quick question about Acme"
    assert data[0]["status"] == "draft"
    assert data[0]["lead_name"] == "Alice"


async def test_list_emails_campaign_not_found(campaign_client):
    import uuid

    resp = await campaign_client.get(f"/api/campaigns/{uuid.uuid4()}/emails")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Campaign stats
# ---------------------------------------------------------------------------


async def test_get_campaign_includes_stats_object(campaign_client: AsyncClient) -> None:
    """GET /api/campaigns/{id} must include a stats object with all 11 counters."""
    with patch("app.services.campaign_service.scrape_lead") as mock_task:
        mock_task.delay = MagicMock()
        create_resp = await campaign_client.post(
            "/api/campaigns",
            files=_csv_file("valid.csv", _VALID_CSV),
            data={"name": "Stats Shape Test"},
        )
    campaign_id = create_resp.json()["campaign_id"]

    resp = await campaign_client.get(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "stats" in body
    stats = body["stats"]
    expected_keys = {
        "uploaded",
        "scraping",
        "researched",
        "generating",
        "drafted",
        "approved",
        "rejected",
        "sending",
        "sent",
        "opened",
        "failed",
    }
    assert set(stats.keys()) == expected_keys
    for key in expected_keys:
        assert isinstance(stats[key], int)


async def test_get_campaign_stats_match_lead_counts(
    campaign_client: AsyncClient,
    transactional_session,
) -> None:
    """Stats counters must reflect actual per-status lead counts."""
    import uuid as uuid_mod

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid_mod.UUID(settings.demo_user_id),
        name="Stats Count Test",
        status=CampaignStatus.scraping,
        total_leads=5,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    statuses = [
        LeadStatus.uploaded,
        LeadStatus.uploaded,
        LeadStatus.researched,
        LeadStatus.researched,
        LeadStatus.drafted,
    ]
    for i, status in enumerate(statuses):
        transactional_session.add(
            Lead(
                campaign_id=campaign.id,
                name=f"Lead {i}",
                email=f"lead{i}@test.com",
                status=status,
            )
        )
    await transactional_session.flush()

    resp = await campaign_client.get(f"/api/campaigns/{campaign.id}")
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["uploaded"] == 2
    assert stats["researched"] == 2
    assert stats["drafted"] == 1
    # All other statuses are zero
    for key in (
        "scraping",
        "generating",
        "approved",
        "rejected",
        "sending",
        "sent",
        "opened",
        "failed",
    ):
        assert stats[key] == 0


async def test_get_campaign_stats_zero_when_no_leads(
    campaign_client: AsyncClient,
    transactional_session,
) -> None:
    """A campaign with no leads must return all stats at zero."""
    import uuid as uuid_mod

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid_mod.UUID(settings.demo_user_id),
        name="Empty Stats Test",
        status=CampaignStatus.draft,
        total_leads=0,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    resp = await campaign_client.get(f"/api/campaigns/{campaign.id}")
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    for val in stats.values():
        assert val == 0
