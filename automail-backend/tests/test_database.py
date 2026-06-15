from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.user import User


async def test_database_connection(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


async def test_user_campaign_lead_smoke(db_session: AsyncSession) -> None:
    user = User(email="smoke@example.com")
    db_session.add(user)
    await db_session.flush()

    campaign = Campaign(user_id=user.id, name="Smoke Campaign")
    db_session.add(campaign)
    await db_session.flush()

    lead = Lead(campaign_id=campaign.id, name="Jane Doe", email="jane@example.com")
    db_session.add(lead)
    await db_session.flush()

    assert user.id is not None
    assert campaign.id is not None
    assert lead.id is not None

    stmt = (
        select(Lead)
        .where(Lead.id == lead.id)
        .options(selectinload(Lead.campaign).selectinload(Campaign.user))
    )
    result = await db_session.execute(stmt)
    fetched = result.scalar_one()

    assert fetched.campaign.name == "Smoke Campaign"
    assert fetched.campaign.user.email == "smoke@example.com"
