from __future__ import annotations

from pathlib import Path

import pytest

from app.services.csv_parser import parse_csv

FIXTURES = Path(__file__).parent / "fixtures"


def _read(filename: str) -> bytes:
    return (FIXTURES / filename).read_bytes()


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_parse_valid_csv() -> None:
    valid, errors = parse_csv(_read("sample_leads_valid.csv"), "valid.csv")
    assert len(valid) == 5
    assert len(errors) == 0
    emails = {lead.email for lead in valid}
    assert "alice@acme.com" in emails
    assert "eve@consulting.org" in emails


def test_parse_mixed_csv() -> None:
    valid, errors = parse_csv(_read("sample_leads_mixed.csv"), "mixed.csv")
    # 10 rows: 7 valid, 2 invalid email, 1 duplicate
    assert len(valid) == 7
    assert len(errors) == 3
    error_rows = {e.row_number for e in errors}
    assert 3 in error_rows  # Bob Smith — "not-an-email"
    assert 9 in error_rows  # Heidi Clark — "invalid-email-heidi"
    assert 11 in error_rows  # Alice Copy — duplicate of alice@acme.com


def test_parse_empty_csv() -> None:
    valid, errors = parse_csv(_read("sample_leads_empty.csv"), "empty.csv")
    assert valid == []
    assert errors == []


# ---------------------------------------------------------------------------
# Error / edge-case tests
# ---------------------------------------------------------------------------


def test_parse_missing_required_column() -> None:
    with pytest.raises(ValueError, match="missing required column"):
        parse_csv(_read("sample_leads_invalid_headers.csv"), "bad_headers.csv")


def test_parse_max_rows_exceeded() -> None:
    header = "name,email\n"
    # Generate 10_001 data rows (exceeds default max_rows=10_000)
    rows = "".join(f"Lead {i},lead{i}@example.com\n" for i in range(10_001))
    large_csv = (header + rows).encode("utf-8")
    with pytest.raises(ValueError, match="maximum of 10"):
        parse_csv(large_csv, "large.csv")


def test_parse_utf8_with_accents() -> None:
    csv_bytes = (
        "name,email,company\n"
        "José García,jose@example.com,Señal Corp\n"
        "María Álvarez,maria@example.com,Niño Tech\n"
    ).encode("utf-8")
    valid, errors = parse_csv(csv_bytes, "utf8.csv")
    assert len(valid) == 2
    assert len(errors) == 0
    names = {lead.name for lead in valid}
    assert "José García" in names
    assert "María Álvarez" in names


def test_parse_latin1_fallback() -> None:
    csv_bytes = (
        "name,email,company\n"
        "Ren\xe9 M\xfcller,rene@example.com,M\xfcller GmbH\n"
    )  # René Müller, Müller GmbH in latin-1
    valid, errors = parse_csv(csv_bytes.encode("latin-1"), "latin1.csv")
    assert len(valid) == 1
    assert len(errors) == 0
    assert "René" in valid[0].name


# ---------------------------------------------------------------------------
# Field validation tests
# ---------------------------------------------------------------------------


def test_parse_invalid_website_url() -> None:
    csv_bytes = (
        "name,email,website\n"
        "Alice,alice@example.com,not-a-url\n"
        "Bob,bob@example.com,https://valid.com\n"
    ).encode("utf-8")
    valid, errors = parse_csv(csv_bytes, "urls.csv")
    assert len(valid) == 1
    assert len(errors) == 1
    assert "website is not a valid URL" in errors[0].error


def test_parse_invalid_linkedin_url() -> None:
    csv_bytes = (
        "name,email,linkedin_url\n"
        "Alice,alice@example.com,https://twitter.com/alice\n"
        "Bob,bob@example.com,https://linkedin.com/in/bob\n"
    ).encode("utf-8")
    valid, errors = parse_csv(csv_bytes, "linkedin.csv")
    assert len(valid) == 1
    assert len(errors) == 1
    assert "linkedin.com" in errors[0].error


def test_parse_case_insensitive_headers() -> None:
    csv_bytes = ("Name,Email Address,Company Name\nAlice,alice@example.com,Acme\n").encode("utf-8")
    valid, errors = parse_csv(csv_bytes, "headers.csv")
    assert len(valid) == 1
    assert valid[0].name == "Alice"
    assert valid[0].email == "alice@example.com"
    assert valid[0].company == "Acme"
