"""Generate personalized cold email drafts via Claude."""

from __future__ import annotations

import json
import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email, EmailStatus
from app.models.lead import Lead, LeadStatus
from app.models.lead_research import LeadResearch
from app.services.campaign_advance import advance_campaign_if_done
from app.services.llm_client import complete

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert B2B cold email copywriter. Your job is to write short, \
personalized, honest outreach emails on behalf of a sales professional.

Rules:
- Maximum 150 words in body_text
- Conversational, not salesy — no buzzwords, no hype
- ONE specific observation about the company (from the research provided)
- ONE clear, low-friction call to action (e.g. "open to a quick chat?")
- Subject line: under 60 characters, no clickbait
- Sign off with "Best," and use [YOUR_NAME] as a placeholder for the sender's name
- If you need to mention the sender's company, use [YOUR_COMPANY] as a placeholder

Respond ONLY with a JSON object (no markdown fences) with these exact keys:
{
  "subject": "...",
  "body_text": "...",
  "body_html": "..."
}

body_html must be the HTML equivalent of body_text (use <p> tags for paragraphs, \
<br> for line breaks within a paragraph).
"""


def build_user_prompt(
    lead_name: str,
    company: str,
    research_summary: str,
    lead_email: str | None = None,
) -> str:
    """Build the user-turn prompt for Claude. lead_email is accepted but NOT included.

    Args:
        lead_name: Full name of the lead contact.
        company: Name of the lead's company.
        research_summary: Scraped and summarized research about the company.
        lead_email: Lead's email address — accepted for API compatibility but
            intentionally excluded from the prompt to avoid PII leakage.

    Returns:
        Formatted prompt string safe to send to Claude.
    """
    first_name = lead_name.split()[0] if lead_name else lead_name
    return (
        f"Write a cold outreach email to {first_name} ({lead_name}) at {company}.\n\n"
        f"Research about {company}:\n{research_summary}\n\n"
        "Generate the email now."
    )


def parse_claude_response(raw: str) -> dict[str, str]:
    """Extract JSON from Claude's response and validate required keys.

    Args:
        raw: Raw text returned by Claude, possibly wrapped in markdown fences.

    Returns:
        Dict with keys "subject", "body_text", and "body_html".

    Raises:
        ValueError: If the response is not valid JSON or is missing required keys.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        # strict=False allows literal control characters (e.g. real newlines) inside
        # JSON string values, which Claude sometimes produces despite instructions.
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned invalid JSON: {exc}\nRaw:\n{raw}") from exc

    for key in ("subject", "body_text", "body_html"):
        if key not in data:
            raise ValueError(f"Claude response missing required key: {key!r}")
    return {k: str(data[k]) for k in ("subject", "body_text", "body_html")}


def _apply_sender_placeholders(
    parsed: dict[str, str],
    sender_name: str | None,
    sender_company: str | None,
) -> dict[str, str]:
    """Replace [YOUR_NAME] and [YOUR_COMPANY] with real values when available."""
    for field in ("body_text", "body_html"):
        if sender_name:
            parsed[field] = parsed[field].replace("[YOUR_NAME]", sender_name)
        if sender_company:
            parsed[field] = parsed[field].replace("[YOUR_COMPANY]", sender_company)
    return parsed


async def generate_email_draft(lead_id: uuid.UUID, session: AsyncSession) -> Email | None:
    """Load lead + research, call Claude, persist Email, update Lead status.

    Args:
        lead_id: UUID of the lead to generate an email for.
        session: Active async SQLAlchemy session.

    Returns:
        The persisted Email model on success, or None if generation failed.
    """
    from app.config import get_settings
    from app.models.campaign import Campaign
    from app.models.user import User

    settings = get_settings()

    lead: Lead | None = (
        await session.execute(select(Lead).where(Lead.id == lead_id))
    ).scalar_one_or_none()
    if lead is None:
        logger.error("email_generator: lead %s not found", lead_id)
        return None

    lead.status = LeadStatus.generating
    await session.flush()

    research: LeadResearch | None = (
        await session.execute(select(LeadResearch).where(LeadResearch.lead_id == lead_id))
    ).scalar_one_or_none()
    if research is None:
        logger.warning("email_generator: no research for lead=%s — marking failed", lead_id)
        lead.status = LeadStatus.failed
        lead.error_message = "No research data available for email generation"
        await advance_campaign_if_done(lead, session)
        await session.commit()
        return None

    # Load sender profile from the campaign owner — may be null if not yet configured.
    campaign: Campaign | None = await session.get(Campaign, lead.campaign_id)
    sender_name: str | None = None
    sender_company: str | None = None
    if campaign:
        user: User | None = await session.get(User, campaign.user_id)
        if user:
            sender_name = user.sender_name
            sender_company = user.sender_company

    user_prompt = build_user_prompt(
        lead_name=lead.name,
        company=lead.company or "their company",
        research_summary=research.summary,
        lead_email=lead.email,
    )

    try:
        raw = await complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
        )
        parsed = parse_claude_response(raw)
    except Exception as exc:
        logger.error("email_generator: Claude call failed for lead=%s: %s", lead_id, exc)
        lead.status = LeadStatus.failed
        lead.error_message = f"generation_failed: {exc}"
        await advance_campaign_if_done(lead, session)
        await session.commit()
        return None

    # Replace sender placeholders with real values if the profile is already configured.
    # Placeholders remain visible in the preview so the user knows to complete their profile.
    parsed = _apply_sender_placeholders(parsed, sender_name, sender_company)

    email = Email(
        lead_id=lead.id,
        subject=parsed["subject"],
        body_html=parsed["body_html"],
        body_text=parsed["body_text"],
        status=EmailStatus.draft,
    )
    session.add(email)
    lead.status = LeadStatus.drafted
    lead.error_message = None
    await advance_campaign_if_done(lead, session)
    await session.commit()

    logger.info("email_generator: lead=%s → drafted (subject=%r)", lead_id, parsed["subject"])
    return email
