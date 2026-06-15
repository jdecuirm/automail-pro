from __future__ import annotations

import csv
import io
import logging
from urllib.parse import urlparse

from email_validator import EmailNotValidError, validate_email

from app.schemas.csv_upload import CSVValidationError
from app.schemas.lead import LeadCreate

logger = logging.getLogger(__name__)

# Canonical field → list of accepted header aliases (all lowercase, underscored)
_ALIASES: dict[str, list[str]] = {
    "name": ["name", "full_name", "contact_name", "lead_name"],
    "email": ["email", "email_address", "e_mail", "contact_email"],
    "company": ["company", "company_name", "organization", "org", "account"],
    "website": ["website", "url", "website_url", "site", "web", "homepage"],
    "linkedin_url": [
        "linkedin_url",
        "linkedin",
        "linkedin_profile",
        "linkedin_link",
        "linkedin_page",
    ],
}


def _normalize(value: str) -> str:
    return value.lower().strip().replace(" ", "_").replace("-", "_")


def _build_header_map(raw_headers: list[str]) -> dict[str, str]:
    """Map each raw CSV header to its canonical field name (or empty string)."""
    mapping: dict[str, str] = {}
    for raw in raw_headers:
        normalized = _normalize(raw)
        for canonical, aliases in _ALIASES.items():
            if normalized in aliases:
                mapping[raw] = canonical
                break
    return mapping


def _is_valid_email(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def parse_csv(
    file_bytes: bytes,
    filename: str,
    max_rows: int = 10_000,
) -> tuple[list[LeadCreate], list[CSVValidationError]]:
    """Parse a CSV file and return (valid_leads, validation_errors).

    Args:
        file_bytes: Raw file content.
        filename: Original filename (used only for logging).
        max_rows: Maximum number of data rows allowed.

    Returns:
        Tuple of (valid LeadCreate instances, CSVValidationError instances).

    Raises:
        ValueError: If the file exceeds max_rows or is missing required columns.
    """
    # Decode — try UTF-8 first, fall back to latin-1
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        logger.debug("csv_parser: UTF-8 decode failed for %s, retrying as latin-1", filename)
        text = file_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    raw_headers: list[str] = list(reader.fieldnames or [])
    if not raw_headers:
        return [], []

    header_map = _build_header_map(raw_headers)
    canonical_fields = set(header_map.values())

    missing_required = [f for f in ("name", "email") if f not in canonical_fields]
    if missing_required:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(missing_required)}. "
            f"Got headers: {', '.join(raw_headers)}"
        )

    rows = list(reader)
    if len(rows) > max_rows:
        raise ValueError(f"CSV exceeds the maximum of {max_rows} rows. Got {len(rows)} data rows.")

    valid_leads: list[LeadCreate] = []
    errors: list[CSVValidationError] = []
    seen_emails: set[str] = set()

    for row_idx, row in enumerate(rows, start=2):  # row 1 is the header
        # Map raw columns → canonical names
        mapped: dict[str, str] = {}
        for raw_key, value in row.items():
            if raw_key is None:
                continue
            canonical = header_map.get(raw_key)
            if canonical:
                mapped[canonical] = (value or "").strip()

        name = mapped.get("name", "")
        email = mapped.get("email", "")
        company = mapped.get("company") or None
        website = mapped.get("website") or None
        linkedin_url = mapped.get("linkedin_url") or None

        row_errors: list[str] = []

        # Validate name
        if not name:
            row_errors.append("name is required")
        elif len(name) > 200:
            row_errors.append("name exceeds 200 characters")

        # Validate email
        if not email:
            row_errors.append("email is required")
        elif not _is_valid_email(email):
            row_errors.append(f"email is invalid: {email!r}")
        elif email.lower() in seen_emails:
            row_errors.append(f"duplicate email: {email!r}")

        # Validate optional URL fields
        if website and not _is_valid_url(website):
            row_errors.append(f"website is not a valid URL: {website!r}")

        if linkedin_url and "linkedin.com" not in linkedin_url.lower():
            row_errors.append(f"linkedin_url must contain 'linkedin.com': {linkedin_url!r}")

        if row_errors:
            errors.append(
                CSVValidationError(
                    row_number=row_idx,
                    error="; ".join(row_errors),
                    raw_data={k: str(v or "") for k, v in row.items() if k is not None},
                )
            )
        else:
            seen_emails.add(email.lower())
            valid_leads.append(
                LeadCreate(
                    name=name[:200],
                    email=email.lower(),
                    company=company[:200] if company else None,
                    website=website,
                    linkedin_url=linkedin_url,
                )
            )

    return valid_leads, errors
