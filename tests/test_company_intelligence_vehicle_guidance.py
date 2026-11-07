"""Real-engine tests for vehicle-delivery guidance extraction.

Every test binds a synthetic release body through the REAL
``engine.earnings_release.binding.bind_release_document`` pipeline (HTML
normalization, block parsing, body hashing) and exercises the PUBLIC
``extract_vehicle_guidance`` — no fakes, no monkeypatching, no private-helper
tests.  Fixtures are synthetic and carry at most 25 copied words per original
source.  The app-side glance formatter is deliberately NOT tested here; its
verification is a separate unit.
"""
from __future__ import annotations

import dataclasses
import hashlib

import pytest

from engine.company_intelligence.vehicle_guidance import extract_vehicle_guidance
from engine.earnings_release.binding import bind_release_document
from engine.earnings_release.receipts import (
    ReceiptReplayError,
    receipt_for_char_span,
    replay_receipt,
)


def _bound(body: str, *, accession: str = "0001104659-24-000001", report_date: str = ""):
    """Bind a synthetic EX-99.1-style body through the real pipeline."""
    return bind_release_document(
        cik="0001791706",
        accession=accession,
        body=body,
        form="6-K",
        filing_date="2024-02-26",
        report_date=report_date,
    )


def _extract(body: str, *, report_date: str = ""):
    bound = _bound(body, report_date=report_date)
    items = extract_vehicle_guidance(
        bound=bound, document_id="doc_test", event_id="evt_test"
    )
    return bound, items


def _page(*parts: str) -> str:
    return "<html><body>" + "".join(parts) + "</body></html>"


# ─────────────────────────────────────────────────────────────────────────────
# Introduced range, period inside the assertion
# ─────────────────────────────────────────────────────────────────────────────

ORIGINAL_BODY = _page(
    "<p>Beijing, February 26, 2024 — The Company announces unaudited results.</p>",
    "<h2>Business Outlook</h2>",
    "<p>For the first quarter of 2024, the Company expects: "
    "Deliveries of vehicles to be between 100,000 and 103,000 vehicles, "
    "representing an increase of 90.2% to 95.9% from the first quarter of 2023.</p>",
)


class TestIntroducedRange:
    def test_original_range_extracted(self):
        bound, items = _extract(ORIGINAL_BODY, report_date="2024-12-31")
        assert len(items) == 1
        item = items[0]
        assert item["schema"] == "guidance_item.v1"
        assert item["metric"] == "vehicle_deliveries"
        assert item["low"] == 100_000
        assert item["high"] == 103_000
        assert isinstance(item["low"], int) and isinstance(item["high"], int)
        assert item["unit"] == "vehicles"
        # Explicit text period wins; report_date (2024-12-31) must not leak in.
        assert item["horizon"] == "FY2024 Q1"
        assert item["status"] == "introduced"

    def test_source_span_is_byte_replayed_public_primary(self):
        bound, items = _extract(ORIGINAL_BODY)
        span = items[0]["source_span"]
        assert span["receipt_state"] == "byte_replayed"
        assert span["rights_profile"] == "rp_public_primary_v1"
        assert span["receipt"]["source_sha256"] == bound.revision.source_sha256

    def test_span_replays_against_raw_body_bytes(self):
        bound, items = _extract(ORIGINAL_BODY)
        receipt = items[0]["source_span"]["receipt"]
        encoded = bound.source.encode("utf-8")
        assert hashlib.sha256(encoded).hexdigest() == receipt["source_sha256"]
        sliced = encoded[receipt["span_start_byte"]:receipt["span_end_byte"]]
        assert hashlib.sha256(sliced).hexdigest() == receipt["text_sha256"]

    def test_comparison_period_is_not_the_horizon(self):
        # "from the first quarter of 2023" is a baseline, never the horizon.
        _, items = _extract(ORIGINAL_BODY)
        assert [i["horizon"] for i in items] == ["FY2024 Q1"]


# ─────────────────────────────────────────────────────────────────────────────
# Split assertion: intro paragraph ends with ":", range lives in the bullet
# ─────────────────────────────────────────────────────────────────────────────

SPLIT_BODY = _page(
    "<h2>Business Outlook</h2>",
    "<p>For the first quarter of 2024, the Company expects:</p>",
    "<p>Deliveries of vehicles to be between 100,000 and 103,000 vehicles, "
    "representing an increase of 90.2% to 95.9% from the first quarter of 2023.</p>",
)


def test_split_intro_and_bullet_blocks_extract():
    _, items = _extract(SPLIT_BODY)
    assert len(items) == 1
    assert (items[0]["low"], items[0]["high"]) == (100_000, 103_000)
    assert items[0]["horizon"] == "FY2024 Q1"
    assert items[0]["status"] == "introduced"


# The measured real-EX-99.1 shape: the outlook bullet is laid out as a
# one-column layout TABLE, introduced by a prose paragraph.  Regression pin —
# a paragraph-only candidate filter misses this whole class of filings.
TABLE_BULLET_BODY = _page(
    "<p>For the first quarter of 2024, the Company expects:</p>",
    "<table><tr><td>· Deliveries of vehicles to be between 100,000 and "
    "103,000 vehicles, representing an increase of 90.2% to 95.9% from the "
    "first quarter of 2023.</td></tr></table>",
)


def test_table_laid_out_outlook_bullet_extracts():
    _, items = _extract(TABLE_BULLET_BODY, report_date="2024-12-31")
    assert len(items) == 1
    assert (items[0]["low"], items[0]["high"]) == (100_000, 103_000)
    assert items[0]["horizon"] == "FY2024 Q1"
    assert items[0]["status"] == "introduced"


def test_numeric_history_table_is_not_guidance():
    body = _page(
        "<table>"
        "<tr><td>Deliveries</td><td>FY 2023</td><td>2023 Q4</td><td>2023 Q3</td></tr>"
        "<tr><td>376,030</td><td>131,805</td><td>105,108</td><td>86,533</td></tr>"
        "</table>",
    )
    _, items = _extract(body)
    assert items == []


# ─────────────────────────────────────────────────────────────────────────────
# Adjacent outlook heading supplies the explicit period
# ─────────────────────────────────────────────────────────────────────────────

ADJACENT_HEADING_BODY = _page(
    "<h2>Business Outlook — First Quarter of 2024</h2>",
    "<p>The Company expects deliveries of vehicles to be between "
    "100,000 and 103,000 vehicles.</p>",
)


def test_adjacent_outlook_heading_supplies_period():
    _, items = _extract(ADJACENT_HEADING_BODY, report_date="2024-12-31")
    assert len(items) == 1
    assert items[0]["horizon"] == "FY2024 Q1"
    assert (items[0]["low"], items[0]["high"]) == (100_000, 103_000)


AMBIGUOUS_HEADING_BODY = _page(
    "<h2>Outlook for the First Quarter of 2024 and Second Quarter of 2024</h2>",
    "<p>The Company expects deliveries of vehicles to be between "
    "100,000 and 103,000 vehicles.</p>",
)


def test_ambiguous_adjacent_heading_rejected():
    _, items = _extract(AMBIGUOUS_HEADING_BODY)
    assert items == []


# ─────────────────────────────────────────────────────────────────────────────
# Numeric quarter form
# ─────────────────────────────────────────────────────────────────────────────

NUMERIC_QUARTER_BODY = _page(
    "<p>The Company expects deliveries of vehicles to be between "
    "200,000 and 210,000 vehicles for Q2 2024.</p>",
)


def test_numeric_quarter_form():
    _, items = _extract(NUMERIC_QUARTER_BODY)
    assert len(items) == 1
    assert items[0]["horizon"] == "FY2024 Q2"


# ─────────────────────────────────────────────────────────────────────────────
# Revision: current range wins, prior comparison range is not emitted
# ─────────────────────────────────────────────────────────────────────────────

REVISION_BODY = _page(
    "<p>Due to lower-than-expected order intake, the Company now expects its "
    "vehicle deliveries for the first quarter of 2024 to be between 76,000 and "
    "78,000 vehicles, revised from the previous vehicle delivery outlook of "
    "between 100,000 and 103,000 vehicles.</p>",
)


def test_revision_uses_current_range_and_status():
    _, items = _extract(REVISION_BODY)
    assert len(items) == 1
    item = items[0]
    assert (item["low"], item["high"]) == (76_000, 78_000)
    assert item["horizon"] == "FY2024 Q1"
    assert item["status"] == "revised"


def test_revision_does_not_emit_prior_range():
    _, items = _extract(REVISION_BODY)
    assert all((i["low"], i["high"]) != (100_000, 103_000) for i in items)


def test_prior_range_without_revision_language_stays_introduced():
    body = _page(
        "<p>The Company expects deliveries of vehicles to be between 90,000 and "
        "95,000 vehicles for the first quarter of 2024, compared to the previous "
        "outlook of between 100,000 and 103,000 vehicles.</p>",
    )
    _, items = _extract(body)
    assert len(items) == 1
    assert (items[0]["low"], items[0]["high"]) == (90_000, 95_000)
    assert items[0]["status"] == "introduced"


# ─────────────────────────────────────────────────────────────────────────────
# Missing period must NEVER fall back to report_date
# ─────────────────────────────────────────────────────────────────────────────

NO_PERIOD_BODY = _page(
    "<p>The Company expects deliveries of vehicles to be between "
    "100,000 and 103,000 vehicles.</p>",
)


def test_missing_period_despite_report_date_returns_empty():
    _, items = _extract(NO_PERIOD_BODY, report_date="2024-03-31")
    assert items == []


def test_empty_report_date_also_returns_empty():
    _, items = _extract(NO_PERIOD_BODY, report_date="")
    assert items == []


# ─────────────────────────────────────────────────────────────────────────────
# Malformed, fractional, negative, reversed, ambiguous
# ─────────────────────────────────────────────────────────────────────────────

def _outlook_body(range_phrase: str, period: str = "for the first quarter of 2024") -> str:
    return _page(
        f"<p>The Company expects deliveries of vehicles to be between "
        f"{range_phrase} vehicles {period}.</p>"
    )


def test_malformed_grouping_rejected():
    _, items = _extract(_outlook_body("1,00,000 and 103,000"))
    assert items == []


def test_malformed_short_grouping_rejected():
    _, items = _extract(_outlook_body("10,0,000 and 103,000"))
    assert items == []


def test_fractional_bounds_rejected():
    _, items = _extract(_outlook_body("76,000.5 and 78,000"))
    assert items == []


def test_negative_bounds_rejected():
    _, items = _extract(_outlook_body("-100,000 and -80,000"))
    assert items == []


def test_reversed_bounds_rejected():
    _, items = _extract(_outlook_body("80,000 and 76,000"))
    assert items == []


def test_conflicting_ranges_for_same_period_rejected():
    body = _page(
        "<p>The Company expects deliveries of vehicles to be between 100,000 and "
        "103,000 vehicles for the first quarter of 2024; it also expects "
        "deliveries to be between 90,000 and 95,000 vehicles.</p>",
    )
    _, items = _extract(body)
    assert items == []


# ─────────────────────────────────────────────────────────────────────────────
# Equal bounds are a valid single-point expectation
# ─────────────────────────────────────────────────────────────────────────────

def test_equal_bounds_allowed():
    body = _page(
        "<p>The Company expects deliveries of vehicles to be between 80,000 and "
        "80,000 vehicles for the first quarter of 2024.</p>",
    )
    _, items = _extract(body)
    assert len(items) == 1
    assert (items[0]["low"], items[0]["high"]) == (80_000, 80_000)
    assert items[0]["horizon"] == "FY2024 Q1"


# ─────────────────────────────────────────────────────────────────────────────
# Actuals-only documents yield no guidance
# ─────────────────────────────────────────────────────────────────────────────

ACTUALS_BODY = _page(
    "<p>The Company delivered 28,984 vehicles in March 2024, increasing by 39.2% "
    "year over year.</p>",
    "<p>This brought the Company's first-quarter deliveries to 80,400, up 52.9% "
    "year over year.</p>",
)


def test_actuals_only_returns_empty():
    _, items = _extract(ACTUALS_BODY, report_date="2024-03-31")
    assert items == []


def test_actual_delivered_range_is_not_guidance():
    body = _page(
        "<p>For the first quarter of 2024 the Company delivered between 80,400 "
        "and 80,400 vehicles.</p>",
    )
    _, items = _extract(body)
    assert items == []


def test_no_vehicle_content_returns_empty():
    body = _page("<p>The Company expects revenue growth in the coming quarter.</p>")
    _, items = _extract(body)
    assert items == []


def test_empty_document_returns_empty():
    bound = _bound(_page("<p> </p>"))
    assert extract_vehicle_guidance(
        bound=bound, document_id="doc_test", event_id="evt_test"
    ) == []


# ─────────────────────────────────────────────────────────────────────────────
# Fail-closed receipts: tampered SHA, drifted body bytes
# ─────────────────────────────────────────────────────────────────────────────

def test_tampered_body_sha_fails_closed():
    bound = _bound(ORIGINAL_BODY)
    tampered = dataclasses.replace(
        bound,
        revision=dataclasses.replace(bound.revision, source_sha256="b" * 64),
    )
    items = extract_vehicle_guidance(
        bound=tampered, document_id="doc_test", event_id="evt_test"
    )
    assert items == []


def test_receipt_replay_refuses_edited_body():
    # A minted receipt must not replay against a body whose bytes drifted.
    bound = _bound(ORIGINAL_BODY)
    source = bound.source
    receipt = receipt_for_char_span(
        source=source,
        source_sha256=bound.revision.source_sha256,
        char_start=source.index("between 100,000"),
        char_end=source.index("between 100,000") + len("between 100,000 and 103,000 vehicles"),
    )
    edited = source.replace("103,000", "108,000", 1)
    with pytest.raises(ReceiptReplayError):
        replay_receipt(receipt, source=edited)


def test_tampered_span_address_refuses():
    # A span whose bytes no longer reproduce the cited text cannot verify.
    bound = _bound(ORIGINAL_BODY)
    items = extract_vehicle_guidance(
        bound=bound, document_id="doc_test", event_id="evt_test"
    )
    assert items, "baseline extraction must succeed before tampering"
    receipt = dict(items[0]["source_span"]["receipt"])
    receipt["text_sha256"] = "0" * 64
    encoded = bound.source.encode("utf-8")
    sliced = encoded[receipt["span_start_byte"]:receipt["span_end_byte"]]
    assert hashlib.sha256(sliced).hexdigest() != receipt["text_sha256"]
