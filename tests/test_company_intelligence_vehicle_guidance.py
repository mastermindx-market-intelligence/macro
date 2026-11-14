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
from engine.company_intelligence.documents import DocumentError, SourceSpan, verify_span
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


def test_explicit_same_period_prior_comparison_is_revised():
    body = _page(
        "<p>The Company expects deliveries of vehicles to be between 90,000 and "
        "95,000 vehicles for the first quarter of 2024, compared to the previous "
        "vehicle delivery outlook of between 100,000 and 103,000 vehicles for "
        "the same quarter.</p>",
    )
    bound, items = _extract(body)
    assert len(items) == 1
    assert (items[0]["low"], items[0]["high"]) == (90_000, 95_000)
    assert items[0]["status"] == "revised"
    evidence = _verified_evidence(bound, items[0])
    assert "previous" in evidence and "same quarter" in evidence
    assert "100,000 and 103,000" in evidence


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
    bound, items = _extract(ORIGINAL_BODY)
    assert items, "baseline extraction must succeed before tampering"
    span = _native_span(items[0]["source_span"])
    verify_span(span, segment_text=bound.source, body_sha256=bound.revision.source_sha256)
    receipt = dict(span.receipt)
    receipt["span_start_byte"] += 1
    tampered = dataclasses.replace(span, receipt=receipt)
    with pytest.raises(DocumentError, match="replayed bytes"):
        verify_span(tampered, segment_text=bound.source,
                    body_sha256=bound.revision.source_sha256)


# Source-association regressions for PR7575 findings5755465666. These call the
# real public extractor and native binding/replay APIs, without provider data.
def _native_span(payload):
    return SourceSpan(**{
        field.name: payload[field.name] for field in dataclasses.fields(SourceSpan)
    })


def _verified_evidence(bound, item):
    span = _native_span(item["source_span"])
    verify_span(span, segment_text=bound.source,
                body_sha256=bound.revision.source_sha256)
    raw = bound.source.encode("utf-8")
    receipt = span.receipt
    return raw[receipt["span_start_byte"]:receipt["span_end_byte"]].decode("utf-8")


@pytest.mark.parametrize("actual_first", [False, True])
def test_receipt_stays_on_the_selected_plain_digit_forecast(actual_first):
    actual = (
        "<p>Actual deliveries were between 100,000 and 103,000 vehicles "
        "in the fourth quarter of 2023.</p>"
    )
    forecast = (
        "<p>The Company expects deliveries of vehicles to be between "
        "100000 and 103000 vehicles for the first quarter of 2024.</p>"
    )
    parts = (actual, forecast) if actual_first else (forecast, actual)
    bound, items = _extract(_page(*parts))
    assert len(items) == 1
    item = items[0]
    assert (item["low"], item["high"], item["horizon"]) == (100000, 103000, "FY2024 Q1")
    evidence = _verified_evidence(bound, item)
    assert "The Company expects" in evidence
    assert "100000 and 103000" in evidence
    assert "first quarter of 2024" in evidence
    assert "Actual deliveries" not in evidence
    assert "fourth quarter of 2023" not in evidence


@pytest.mark.parametrize("body", [SPLIT_BODY, ADJACENT_HEADING_BODY, TABLE_BULLET_BODY])
def test_receipt_includes_the_native_context_used_for_the_assertion(body):
    bound, items = _extract(body)
    assert len(items) == 1
    evidence = _verified_evidence(bound, items[0])
    assert "Company expects" in evidence
    assert "100,000" in evidence and "103,000" in evidence
    assert "quarter of 2024" in evidence.lower()


def test_unicode_and_inline_markup_keep_native_byte_coordinates():
    body = _page(
        "<p>北京 — The Company expects deliveries of vehicles to be between "
        "<b>100000</b> and <b>103000</b> vehicles for Q1 2024.</p>"
    )
    bound, items = _extract(body)
    assert len(items) == 1
    evidence = _verified_evidence(bound, items[0])
    assert "北京" in evidence and "<b>100000</b>" in evidence
    assert "The Company expects" in evidence and "Q1 2024" in evidence


@pytest.mark.parametrize("false_assertion", [
    "The Company does not expect deliveries to be between 100,000 and 103,000 vehicles for Q1 2024.",
    "The Company expects deliveries not to be between 100,000 and 103,000 vehicles for Q1 2024.",
    "The Company expects production to be between 100,000 and 103,000 vehicles for Q1 2024.",
    "Actual deliveries were between 100,000 and 103,000 vehicles for Q1 2024.",
    "The Company expects revenue growth. Actual deliveries were between 100,000 and 103,000 vehicles for Q1 2024.",
    "Analysts expect deliveries to be between 100,000 and 103,000 vehicles for Q1 2024.",
    "The Company expects its competitor's deliveries to be between 100,000 and 103,000 vehicles for Q1 2024.",
    "If the Company expects deliveries to be between 100,000 and 103,000 vehicles for Q1 2024, capacity will suffice.",
    "It is not true that the Company expects deliveries to be between 100,000 and 103,000 vehicles for Q1 2024.",
])
def test_false_affirmative_or_metric_scope_cannot_borrow_outlook(false_assertion):
    body = _page(
        "<h2>Business Outlook — Q1 2024</h2>",
        f"<p>{false_assertion}</p>",
        "<p>The Company expects deliveries of vehicles to be between "
        "50,000 and 60,000 vehicles for Q2 2024.</p>",
    )
    bound, items = _extract(body)
    assert [(item["low"], item["high"], item["horizon"]) for item in items] == [
        (50_000, 60_000, "FY2024 Q2")
    ]
    assert "50,000 and 60,000" in _verified_evidence(bound, items[0])


@pytest.mark.parametrize("assertion", [
    "The Company expects deliveries to be between 100,000 and 103,000 vehicles next quarter. Revenue grew in Q1 2024.",
    "The Company expects deliveries to be between 100,000 and 103,000 vehicles for the second quarter.",
    "The Company expects deliveries to be between 100,000 and 103,000 vehicles for Q1 2024 and Q2 2024.",
    "The Company expects deliveries to be between 100,000 and 103,000 vehicles for Q5 2024.",
])
def test_unrelated_or_conflicting_period_cannot_be_donated(assertion):
    body = _page("<h2>Business Outlook — Q1 2024</h2>", f"<p>{assertion}</p>")
    _, items = _extract(body, report_date="2024-03-31")
    assert items == []


def test_compatible_partial_quarter_uses_the_adjacent_explicit_heading():
    body = _page(
        "<h2>Business Outlook — Q2 2024</h2>",
        "<p>The Company expects deliveries to be between 100000 and 103000 "
        "vehicles for the second quarter.</p>",
    )
    bound, items = _extract(body)
    assert len(items) == 1 and items[0]["horizon"] == "FY2024 Q2"
    assert "Q2 2024" in _verified_evidence(bound, items[0])


@pytest.mark.parametrize("placement", ["before_sentence", "after_sentence", "same_clause"])
def test_unrelated_previous_factory_does_not_mark_guidance_revised(placement):
    assertion = (
        "The Company expects deliveries to be between 100,000 and 103,000 "
        "vehicles for Q1 2024."
    )
    factory = "The Company previously opened a factory."
    text = factory + " " + assertion if placement == "before_sentence" else assertion + " " + factory
    if placement == "same_clause":
        text = "Having previously opened a factory, " + assertion
    bound, items = _extract(_page(f"<p>{text}</p>"))
    assert len(items) == 1 and items[0]["status"] == "introduced"
    _verified_evidence(bound, items[0])


@pytest.mark.parametrize("prior_period,accepted", [
    ("Q1 2024", True), ("Q2 2024", False), ("Q1 2023", False),
])
def test_prior_comparison_must_identify_the_same_delivery_period(prior_period, accepted):
    body = _page(
        "<p>The Company expects deliveries to be between 76,000 and 78,000 "
        "vehicles for Q1 2024, compared to its previous vehicle delivery "
        f"outlook of between 100,000 and 103,000 vehicles for {prior_period}.</p>"
    )
    bound, items = _extract(body)
    if not accepted:
        assert items == []
        return
    assert len(items) == 1
    assert (items[0]["low"], items[0]["high"], items[0]["status"]) == (76000, 78000, "revised")
    evidence = _verified_evidence(bound, items[0])
    assert "previous vehicle delivery outlook" in evidence and prior_period in evidence


@pytest.mark.parametrize("comparison", [
    "compared to the previous outlook of between 100,000 and 103,000 vehicles",
    "with the previous vehicle delivery outlook of between 100,000 and 103,000 vehicles",
    "as a revised delivery outlook",
])
def test_ambiguous_previous_outlook_cannot_invent_revision_status(comparison):
    body = _page(
        "<p>The Company expects deliveries to be between 90,000 and 95,000 "
        f"vehicles for Q1 2024, {comparison}.</p>"
    )
    _, items = _extract(body)
    assert items == []


@pytest.mark.parametrize("split", [False, True])
def test_native_unread_boundary_blocks_context_donation(split):
    if split:
        parts = [
            "<p>For the first quarter of 2024, the Company expects:</p>",
            "<center>The preceding outlook is unrelated.</center>",
            "<p>Deliveries of vehicles to be between 100,000 and 103,000 vehicles.</p>",
        ]
    else:
        parts = [
            "<h2>Business Outlook — Q1 2024</h2>",
            "<center>The preceding outlook is unrelated.</center>",
            "<p>The Company expects deliveries to be between 100,000 and 103,000 vehicles.</p>",
        ]
    _, items = _extract(_page(*parts))
    assert items == []


def test_tampered_parsed_block_cannot_override_native_source_text():
    bound = _bound(ORIGINAL_BODY)
    blocks = list(bound.document.blocks)
    index = next(i for i, block in enumerate(blocks) if "100,000" in block.text)
    blocks[index] = dataclasses.replace(blocks[index],
                                        text=blocks[index].text.replace("100,000", "90,000"))
    tampered = dataclasses.replace(
        bound, document=dataclasses.replace(bound.document, blocks=tuple(blocks))
    )
    assert extract_vehicle_guidance(
        bound=tampered, document_id="doc_test", event_id="evt_test"
    ) == []


@pytest.mark.parametrize("introduction", [
    "<p>The Company expects for Q1 2024:</p>",
    "<p>For Q1 2024:</p><p>The Company expects:</p>",
    "<p>The Company expects vehicle deliveries for Q1 2024:</p>",
])
def test_explicit_split_introduction_orders_keep_their_source_context(introduction):
    body = _page(
        introduction,
        "<p>Deliveries of vehicles to be between 100000 and 103000 vehicles.</p>",
    )
    bound, items = _extract(body)
    assert len(items) == 1
    assert items[0]["horizon"] == "FY2024 Q1"
    evidence = _verified_evidence(bound, items[0])
    assert "Company expects" in evidence and "Q1 2024" in evidence


@pytest.mark.parametrize("assertion", [
    "The Company expects deliveries to be between 100000 and 103000 vehicles, and revenue grew in Q1 2024.",
    "The Company expects deliveries to be between 100000 and 103000 vehicles and revenue grew in Q1 2024.",
    "Revenue grew in Q1 2024, and the Company expects deliveries to be between 100000 and 103000 vehicles.",
])
def test_another_metrics_period_cannot_qualify_the_delivery_range(assertion):
    _, items = _extract(_page(f"<p>{assertion}</p>"), report_date="2024-03-31")
    assert items == []


@pytest.mark.parametrize("introduction", [
    "It is not true that the Company expects for Q1 2024:",
    "If the Company expects for Q1 2024:",
    "Analysts say the Company expects for Q1 2024:",
    "For next quarter, the Company expects:",
    "For Q5 2024, the Company expects:",
])
def test_split_introduction_requires_an_affirmative_issuer(introduction):
    body = _page(
        f"<p>{introduction}</p>",
        "<p>Deliveries of vehicles to be between 100000 and 103000 vehicles.</p>",
    )
    _, items = _extract(body)
    assert items == []


@pytest.mark.parametrize("earlier,expected", [
    ("The Company expects revenue growth.", []),
    ("The Company expects deliveries to be between 50000 and 60000 vehicles for Q2 2024.",
     [(50000, 60000, "FY2024 Q2")]),
])
def test_explicit_other_pronoun_antecedent_cannot_borrow_the_issuer(earlier, expected):
    body = _page(
        f"<p>{earlier} A competitor says it expects deliveries to be between "
        "100000 and 103000 vehicles for Q1 2024.</p>"
    )
    bound, items = _extract(body)
    assert [(item["low"], item["high"], item["horizon"]) for item in items] == expected
    for item in items:
        _verified_evidence(bound, item)


def test_preposed_previous_range_is_refused_instead_of_labeled_introduced():
    body = _page(
        "<p>Compared to its previous vehicle delivery outlook of between 100000 "
        "and 103000 vehicles for Q1 2024, the Company expects deliveries to be "
        "between 76000 and 78000 vehicles for Q1 2024.</p>"
    )
    _, items = _extract(body)
    assert items == []


@pytest.mark.parametrize("assertion", [
    "The Company expects deliveries to be between 100000 and 103000 vehicles for Q1 <b>2024</b>.",
    "The Company ex<b>pect</b>s deliveries to be between 100000 and 103000 vehicles for Q1 2024.",
    "The Company expects deliveries to be between 100<b>000</b> and 103<b>000</b> vehicles for Q1 2024.",
    "The Company expects deliveries to be between 100,<b>000</b> and 103,<b>000</b> vehicles for Q1 2024.",
])
def test_inline_markup_uses_native_parser_semantics_and_exact_raw_receipts(assertion):
    bound, items = _extract(_page(f"<p>{assertion}</p>"))
    assert len(items) == 1
    assert (items[0]["low"], items[0]["high"], items[0]["horizon"]) == (
        100000, 103000, "FY2024 Q1"
    )
    evidence = _verified_evidence(bound, items[0])
    assert assertion in evidence


def test_tampered_native_table_cell_cannot_override_the_raw_source():
    bound = _bound(TABLE_BULLET_BODY)
    blocks = list(bound.document.blocks)
    index = next(i for i, block in enumerate(blocks) if block.table is not None)
    table = blocks[index].table
    cell = dataclasses.replace(table.rows[0][0],
                               text=table.rows[0][0].text.replace("100,000", "90,000"))
    tampered_table = dataclasses.replace(table, rows=((cell,),))
    blocks[index] = dataclasses.replace(blocks[index], table=tampered_table)
    tampered = dataclasses.replace(
        bound, document=dataclasses.replace(bound.document, blocks=tuple(blocks))
    )
    assert extract_vehicle_guidance(
        bound=tampered, document_id="doc_test", event_id="evt_test"
    ) == []
