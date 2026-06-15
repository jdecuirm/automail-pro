from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_MAX_TEXT = 5000


class ScrapeResult(BaseModel):
    url: str
    title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    headings: list[str] = []
    main_text: str = ""
    contact_emails: list[str] = []
    social_links: dict[str, str] = {}
    raw_html: str | None = None
    scraper_used: str = "static"  # "static" | "dynamic"

    @field_validator("main_text")
    @classmethod
    def truncate_text(cls, v: str) -> str:
        return v[:_MAX_TEXT]

    @field_validator("contact_emails")
    @classmethod
    def lowercase_emails(cls, v: list[str]) -> list[str]:
        return [e.lower() for e in v]

    @model_validator(mode="after")
    def ensure_absolute_url(self) -> ScrapeResult:
        return self

    def to_extracted_data(self) -> dict[str, Any]:
        """Serialise to JSONB-friendly dict for LeadResearch.extracted_data."""
        return {
            "title": self.title,
            "meta_description": self.meta_description,
            "og_title": self.og_title,
            "og_description": self.og_description,
            "headings": self.headings,
            "contact_emails": self.contact_emails,
            "social_links": self.social_links,
            "scraper_used": self.scraper_used,
            "source_url": self.url,
        }

    def build_summary(self) -> str:
        """Compact text summary for Stage F (Claude API)."""
        parts: list[str] = []
        if self.title:
            parts.append(f"Title: {self.title}")
        desc = self.og_description or self.meta_description
        if desc:
            parts.append(f"Description: {desc}")
        if self.headings:
            parts.append("Headings: " + " | ".join(self.headings[:3]))
        if self.main_text:
            parts.append(f"Content: {self.main_text[:800]}")
        return "\n".join(parts) if parts else "No content extracted."
