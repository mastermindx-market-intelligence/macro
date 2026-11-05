"""Tests for utils.py helpers: slugify, build_pdf_filename, humanize_age, sha256_bytes."""
from __future__ import annotations

from marketdesk_extractor.utils import (
    build_pdf_filename,
    humanize_age,
    sha256_bytes,
    slugify,
)


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------

def test_slugify_basic() -> None:
    assert slugify("Hello World") == "hello-world"


def test_slugify_removes_special_chars() -> None:
    assert slugify("J.P. Morgan: Q2 Outlook!") == "j-p-morgan-q2-outlook"


def test_slugify_collapses_repeated_hyphens() -> None:
    result = slugify("a -- b --- c")
    assert "--" not in result


def test_slugify_truncates_at_max_len() -> None:
    long_title = "a" * 200
    result = slugify(long_title, max_len=80)
    assert len(result) <= 80


def test_slugify_empty_string_returns_untitled() -> None:
    assert slugify("") == "untitled"
    assert slugify("   ") == "untitled"


def test_slugify_unicode_normalized() -> None:
    # accented characters should be stripped/normalized
    result = slugify("Résumé café")
    assert "e" in result or result == "resum-caf"
    assert all(c.isascii() for c in result)


def test_slugify_custom_max_len() -> None:
    result = slugify("hello world test string", max_len=10)
    assert len(result) <= 10


def test_slugify_strips_leading_trailing_hyphens() -> None:
    result = slugify("---hello---")
    assert not result.startswith("-")
    assert not result.endswith("-")


# ---------------------------------------------------------------------------
# build_pdf_filename
# ---------------------------------------------------------------------------

def test_build_pdf_filename_basic_shape() -> None:
    name = build_pdf_filename(
        date_str="2026-07-07",
        institution="JPM",
        title="Earnings Upgrade Catalyst",
        blob_id="abc123",
    )
    assert name.startswith("2026-07-07_")
    assert name.endswith("_abc123.pdf")
    assert "jpm" in name
    assert "earnings-upgrade-catalyst" in name


def test_build_pdf_filename_none_institution_uses_unknown() -> None:
    name = build_pdf_filename(
        date_str="2026-07-07",
        institution=None,
        title="Some Paper",
        blob_id="xyz",
    )
    assert "unknown" in name


def test_build_pdf_filename_has_pdf_extension() -> None:
    name = build_pdf_filename(
        date_str="2026-07-07",
        institution="GS",
        title="Tech Outlook",
        blob_id="id1",
    )
    assert name.endswith(".pdf")


def test_build_pdf_filename_no_spaces() -> None:
    name = build_pdf_filename(
        date_str="2026-07-07",
        institution="Morgan Stanley",
        title="Q3 Rates and Macro Outlook",
        blob_id="ms1",
    )
    assert " " not in name


def test_build_pdf_filename_blob_id_preserved() -> None:
    blob_id = "unique-blob-9999"
    name = build_pdf_filename(
        date_str="2026-07-07",
        institution="Citi",
        title="Credit Markets",
        blob_id=blob_id,
    )
    assert blob_id in name


# ---------------------------------------------------------------------------
# sha256_bytes
# ---------------------------------------------------------------------------

def test_sha256_bytes_returns_64_hex_chars() -> None:
    digest = sha256_bytes(b"hello world")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_sha256_bytes_deterministic() -> None:
    data = b"test data 12345"
    assert sha256_bytes(data) == sha256_bytes(data)


def test_sha256_bytes_known_value() -> None:
    # sha256 of empty bytes is a known constant
    import hashlib
    expected = hashlib.sha256(b"").hexdigest()
    assert sha256_bytes(b"") == expected


def test_sha256_bytes_different_inputs_differ() -> None:
    assert sha256_bytes(b"aaa") != sha256_bytes(b"bbb")


# ---------------------------------------------------------------------------
# humanize_age
# ---------------------------------------------------------------------------

_BASE = 1_700_000_000  # fixed reference "now" for deterministic tests


def test_humanize_age_none_returns_none() -> None:
    assert humanize_age(None) is None


def test_humanize_age_minutes() -> None:
    t = _BASE - 300  # 5 minutes ago
    result = humanize_age(t, now=_BASE)
    assert result == "5 min"


def test_humanize_age_one_minute_minimum() -> None:
    t = _BASE - 30  # 30 seconds ago — rounds up to 1 min
    result = humanize_age(t, now=_BASE)
    assert result == "1 min"


def test_humanize_age_hours() -> None:
    t = _BASE - 7200  # 2 hours ago
    result = humanize_age(t, now=_BASE)
    assert result == "2 hr"


def test_humanize_age_days_returns_month_day() -> None:
    t = _BASE - 86400 * 2  # 2 days ago — should return "Mon D" format
    result = humanize_age(t, now=_BASE)
    assert result is not None
    # Should be like "Nov 13" — not a "min" or "hr" string
    assert "min" not in result
    assert "hr" not in result


def test_humanize_age_exactly_one_hour_boundary() -> None:
    t = _BASE - 3600
    result = humanize_age(t, now=_BASE)
    assert result == "1 hr"


def test_humanize_age_zero_delta() -> None:
    result = humanize_age(_BASE, now=_BASE)
    assert result == "1 min"  # max(1, 0//60) = 1
