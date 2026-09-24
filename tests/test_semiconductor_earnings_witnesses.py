"""T05a — TSMC + onsemi witness issuers enrolled in the existing Earnings owner.

Two new issuers + profiles added by this module:

* ``TSM`` — Taiwan Semiconductor Manufacturing Company Limited (foreign
  private issuer; reports NT$ on Form 6-K, annual report Form 20-F;
  CIK 0001046179, MIC XNYS, ticker TSM NYSE ADR).  Listing
  ``valid_from = date(2026, 4, 16)`` attested by the FY2025 20-F cover.
  *No* TWSE "2330" alias is registered — the estate never sourced that
  venue, so a listing cannot be asserted for it.

* ``ON`` — ON Semiconductor Corporation (domestic 52/53-week filer;
  reports USD on 8-K/10-Q/10-K; CIK 0001097864, MIC XNAS, ticker ON
  Nasdaq).  Listing ``valid_from = date(2026, 5, 4)`` attested by the
  Q1-2026 results 8-K filing date (the 10-K filing date is not
  derivable offline; documented as a limitation).

Every fact here is a SYNTHETIC look-alike span — no real Exhibit 99.1 body
is committed.  TSM's NT$ figure cannot be emitted with a TWD unit because
the existing unit vocabulary (USD-prefixed only, ``engine.earnings_release
.figures._UNIT_BY_SCALE``) does not know one; per the docket no unit is
invented and no conversion is performed, so the TWD revenue emits a typed
absence with detail ``reporting_currency_twd_not_in_unit_vocabulary``.  The
USD-restated figure, where one is present in the release body, is
extracted as a normal present fact.

TSM stays OUT OF FIF (``engine.fundamental_forensics.metric_registry``
restricts FIF to 10-K/10-Q, us-gaap/dei, USD).  ``TSM_FIF_GAP`` is the
documented sentinel so a later surface can render the gap rather than
guess a metric.  This module does NOT widen any FIF constant.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from engine.company_intelligence.event_workspace import (
    AAPL_CIK,
    production_registry,
)
from engine.company_intelligence.event_workspace_build import build_event_workspace
from engine.company_intelligence.events import FiscalPeriod
from engine.company_intelligence.identity import ALIAS_EPOCH
from engine.company_intelligence.issuer_profiles import (
    HOMEBUILDER_TICKERS,
    TSM_CIK,
    TSM_FIF_GAP,
    ON_CIK,
    issuer_for_ticker,
    on_issuer,
    on_profile,
    profile_for_ticker,
    tsm_issuer,
    tsm_profile,
)
from engine.earnings_release.binding import bind_release_document
from engine.fundamental_forensics.metric_registry import (
    ALLOWED_CONFIDENCE,
    ALLOWED_FORMS,
    ALLOWED_PERIOD_KINDS,
    ALLOWED_TAXONOMIES,
    ALLOWED_UNITS,
)


# Synthetic (look-alike) exhibit bodies.  No real Exhibit 99.1 is committed.
TSM_SYNTHETIC_EXHIBIT = (
    "<html><body>"
    "<p>TSMC today announced consolidated revenue for the second quarter of 2026. "
    "Second quarter net revenue was NT$1,234,567 million, an increase from NT$999,999 million a year ago. "
    "In U.S. dollars, second quarter revenue was US$12.34 billion, compared with US$8.00 billion a year ago.</p>"
    "<table>"
    "<tr><td>Quarters Ended June 30,</td></tr>"
    "<tr><td>2026</td><td>2025</td></tr>"
    "</table>"
    "<p>In the first quarter of 2026 we had guided between US$11.0 billion and US$11.5 billion. "
    "Looking ahead to the third quarter of 2026, we expect revenue between "
    "US$13.0 billion and US$13.5 billion, assuming an exchange rate of 31.5 NTD per USD.</p>"
    "</body></html>"
)

ON_SYNTHETIC_EXHIBIT = (
    "<html><body>"
    "<p>onsemi today announced first quarter 2026 results.</p>"
    "<table>"
    "<tr><td>Quarters Ended</td></tr>"
    "<tr><td></td><td>April 3, 2026</td><td>April 4, 2025</td></tr>"
    "<tr><td>Revenue</td><td>$</td><td>$1,234.5 million</td><td>$</td><td>$1,500.0 million</td></tr>"
    "</table>"
    "<p>For the third quarter of 2026, we expect revenue in the range of "
    "$1,400 million to $1,500 million.</p>"
    "</body></html>"
)

TSM_ACCESSION = "0001046179-26-000451"  # Q2-2026 6-K (synthetic for test)
ON_ACCESSION = "0001140361-26-018868"  # Q1-2026 8-K (synthetic for test)


def _bind_tsm(exhibit_body: str = TSM_SYNTHETIC_EXHIBIT):
    return bind_release_document(
        cik=TSM_CIK,
        accession=TSM_ACCESSION,
        body=exhibit_body,
        form="6-K",
        filing_date="2026-07-16",
        acceptance_datetime="2026-07-16T11:45:43Z",
        report_date="2026-06-30",
        exhibit_url="https://example/tsm.htm",
    )


def _bind_on(exhibit_body: str = ON_SYNTHETIC_EXHIBIT):
    return bind_release_document(
        cik=ON_CIK,
        accession=ON_ACCESSION,
        body=exhibit_body,
        form="8-K",
        filing_date="2026-05-04",
        acceptance_datetime="2026-05-04T20:10:34Z",
        report_date="2026-04-03",
        exhibit_url="https://example/on.htm",
    )


# ─────────────────────────────────────────────────────────────────────────────
# (a) Production registry — 7 issuers, apple first, homebuilders unchanged,
# TSM and ON added at the end.
# ─────────────────────────────────────────────────────────────────────────────

def test_production_registry_has_seven_issuers_apple_first_then_homebuilders_then_semis() -> None:
    registry = production_registry()
    assert len(registry) == 7
    ordered = [issuer.company_id for issuer in registry]
    # Apple first, four homebuilders unchanged, TSM, then ON.
    assert ordered == [
        "cik:0000320193",  # AAPL
        "cik:0000882184",  # DHI
        "cik:0000822416",  # PHM
        "cik:0000795266",  # KBH
        "cik:0000794170",  # TOL
        "cik:0001046179",  # TSM
        "cik:0001097864",  # ON
    ]


def test_tsm_issuer_has_sec_attested_identity() -> None:
    issuer = tsm_issuer()
    assert issuer.cik == "0001046179"
    assert issuer.display_name == "Taiwan Semiconductor Manufacturing Company Limited"
    assert issuer.fiscal_year_end_month == 12
    assert issuer.reporting_currency == "TWD"
    assert issuer.issuer_kind == "foreign_private_issuer"
    assert issuer.external_ids == {
        "cik": TSM_CIK,
        "sec_entity_type": "other",
        "annual_report_form": "20-F",
        "results_form": "6-K",
    }
    assert len(issuer.listings) == 1
    listing = issuer.listings[0]
    assert listing.ticker == "TSM"
    assert listing.mic == "XNYS"
    assert listing.share_class == "ADR"
    assert listing.trading_currency == "USD"
    assert listing.is_primary is True
    # SEC-attested listing window: FY2025 20-F cover, valid_from 2026-04-16.
    assert listing.valid_from == date(2026, 4, 16)
    assert listing.valid_from != ALIAS_EPOCH


def test_on_issuer_has_sec_attested_identity() -> None:
    issuer = on_issuer()
    assert issuer.cik == "0001097864"
    assert issuer.display_name == "ON Semiconductor Corporation"
    assert issuer.fiscal_year_end_month == 12
    assert issuer.reporting_currency == "USD"
    assert issuer.issuer_kind == "domestic_52_53_week"
    assert issuer.external_ids == {
        "cik": ON_CIK,
        "sec_entity_type": "operating",
        "annual_report_form": "10-K",
        "results_form": "8-K",
        "fiscal_calendar": "52_53_week",
    }
    assert len(issuer.listings) == 1
    listing = issuer.listings[0]
    assert listing.ticker == "ON"
    assert listing.mic == "XNAS"
    assert listing.share_class == "common"
    assert listing.trading_currency == "USD"
    assert listing.is_primary is True
    # SEC-attested listing window: Q1-2026 results 8-K filing date 2026-05-04.
    # (10-K filing date is not derivable offline — limitation documented in
    # the issuer_profiles docstring.)
    assert listing.valid_from == date(2026, 5, 4)
    assert listing.valid_from != ALIAS_EPOCH


def test_no_twse_2330_alias_for_tsm() -> None:
    """The estate never sourced the TWSE venue, so a TWSE "2330" alias
    cannot be registered.  No listing ticker equals "2330" anywhere in the
    production registry."""
    registry = production_registry()
    for issuer in registry:
        for listing in issuer.listings:
            assert listing.ticker != "2330"


def test_tsm_resolves_only_after_listing_valid_from() -> None:
    registry = production_registry()
    assert registry.resolve_ticker("TSM", asof=date(2026, 3, 31)) is None
    assert registry.resolve_ticker("TSM", asof=date(2026, 4, 15)) is None
    resolution = registry.resolve_ticker("TSM", asof=date(2026, 7, 16))
    assert resolution is not None
    assert resolution.company_id == "cik:0001046179"
    assert resolution.ticker == "TSM"
    assert resolution.listing.valid_from == date(2026, 4, 16)


def test_on_resolves_only_after_listing_valid_from() -> None:
    registry = production_registry()
    assert registry.resolve_ticker("ON", asof=date(2026, 5, 3)) is None
    resolution = registry.resolve_ticker("ON", asof=date(2026, 5, 4))
    assert resolution is not None
    assert resolution.company_id == "cik:0001097864"
    assert resolution.ticker == "ON"
    assert resolution.listing.valid_from == date(2026, 5, 4)


def test_homebuilders_unchanged_in_seven_issuer_registry() -> None:
    """C1: the four homebuilders stay byte-identical in behaviour — same
    CIK, same listing valid_from (the homebuilders use ALIAS_EPOCH
    explicitly and that is unchanged here)."""
    registry = production_registry()
    for ticker, expected_cik in (
        ("DHI", "882184"), ("PHM", "822416"), ("KBH", "795266"), ("TOL", "794170"),
    ):
        resolved = registry.resolve_ticker(ticker, asof=date(2026, 8, 1))
        assert resolved is not None
        assert resolved.company_id == f"cik:{int(expected_cik):010d}"


# ─────────────────────────────────────────────────────────────────────────────
# (b) Profile resolution + the FIF gap sentinel (TSM stays out of FIF).
# ─────────────────────────────────────────────────────────────────────────────

def test_profile_for_ticker_returns_tsm_and_on_profiles() -> None:
    tsm = profile_for_ticker("TSM")
    on = profile_for_ticker("ON")
    assert tsm is not None
    assert tsm.ticker == "TSM"
    assert on is not None
    assert on.ticker == "ON"


def test_issuer_for_ticker_returns_tsm_and_on() -> None:
    assert issuer_for_ticker("TSM") is not None
    assert issuer_for_ticker("ON") is not None
    assert issuer_for_ticker("LEN") is None
    assert issuer_for_ticker("NVR") is None


def test_homebuilder_profiles_still_resolvable() -> None:
    for ticker in HOMEBUILDER_TICKERS:
        assert profile_for_ticker(ticker) is not None


def test_tsm_fif_gap_constant_is_typed() -> None:
    """TSM stays OUT OF FIF: the registry restricts forms to 10-K/10-Q,
    taxonomies to us-gaap/dei, and units to USD/shares/ratio — TSM's IFRS
    /TWD/20-F combination is none of those.  TSM_FIF_GAP is the typed
    sentinel; a later surface renders it, never an inferred metric."""
    assert TSM_FIF_GAP == "ifrs_twd_20f_outside_fif_registry"
    assert isinstance(TSM_FIF_GAP, str)


def test_fif_allowed_constants_byte_identical_to_base() -> None:
    """C3: no FIF constant widened — these frozensets are byte-identical
    to the pre-PR main values."""
    assert ALLOWED_CONFIDENCE == frozenset({"A", "B", "C", "D"})
    assert ALLOWED_UNITS == frozenset({"USD", "shares", "USD/shares", "ratio"})
    assert ALLOWED_PERIOD_KINDS == frozenset({"duration", "instant"})
    assert ALLOWED_FORMS == frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})
    assert ALLOWED_TAXONOMIES == frozenset({"us-gaap", "dei"})


# ─────────────────────────────────────────────────────────────────────────────
# (c) Transcript claims: TSMC + onsemi — no held transcript (mirrors the
# homebuilder "no call" convention).  Both extractors return ``[]``.
# ─────────────────────────────────────────────────────────────────────────────

def test_tsm_transcript_claims_are_empty() -> None:
    profile = tsm_profile()
    assert profile.extract_transcript_claims(segments=[], document_id="doc:x", body_sha256="", event_id="evt:x") == []


def test_on_transcript_claims_are_empty() -> None:
    profile = on_profile()
    assert profile.extract_transcript_claims(segments=[], document_id="doc:x", body_sha256="", event_id="evt:x") == []


# ─────────────────────────────────────────────────────────────────────────────
# (d) Release-fact extraction on SYNTHETIC exhibits.  Receipts must replay
# byte-for-byte against the bound source (same replay style the homebuilder
# tests use).
# ─────────────────────────────────────────────────────────────────────────────

def _verify_all_spans(facts: list[dict], *, bound) -> None:
    from engine.company_intelligence.documents import SourceSpan, verify_span
    for fact in facts:
        span_payload = fact.get("source_span")
        if span_payload is None:
            assert "typed_absence" in fact
            continue
        span = SourceSpan(
            span_id=span_payload["span_id"],
            document_id=span_payload["document_id"],
            document_version=span_payload["document_version"],
            locator=span_payload["locator"],
            receipt_state=span_payload["receipt_state"],
            text_sha256=span_payload["text_sha256"],
            display_excerpt=span_payload["display_excerpt"],
            rights_profile=span_payload["rights_profile"],
            receipt=span_payload["receipt"],
            unreplayable_reason=span_payload["unreplayable_reason"],
        )
        verify_span(span, segment_text=bound.source, body_sha256=bound.revision.source_sha256)


TSM_Q2 = FiscalPeriod(year=2026, quarter=2, calendar_end=date(2026, 6, 30))
ON_Q1 = FiscalPeriod(year=2026, quarter=1, calendar_end=date(2026, 4, 3))


def _tsm_facts(body: str = TSM_SYNTHETIC_EXHIBIT, *, fiscal_period=TSM_Q2):
    bound = _bind_tsm(body)
    facts = tsm_profile().extract_release_facts(
        bound=bound, document_id="doc:tsm-synthetic", event_id="evt_cik0001046179_2026q2_results",
        fiscal_period=fiscal_period,
    )
    _verify_all_spans(facts, bound=bound)
    return {fact["fact_id"]: fact for fact in facts}


def _on_facts(body: str = ON_SYNTHETIC_EXHIBIT, *, fiscal_period=ON_Q1):
    bound = _bind_on(body)
    facts = on_profile().extract_release_facts(
        bound=bound, document_id="doc:on-synthetic", event_id="evt_cik0001097864_2026q1_results",
        fiscal_period=fiscal_period,
    )
    _verify_all_spans(facts, bound=bound)
    return {fact["fact_id"]: fact for fact in facts}


def _tsm_guidance(body: str = TSM_SYNTHETIC_EXHIBIT):
    bound = _bind_tsm(body)
    items = tsm_profile().extract_guidance(
        bound=bound, release_document_id="doc:tsm-synthetic",
        segments=[], document_id="doc:tx", body_sha256="", event_id="evt_cik0001046179_2026q2_results",
        fiscal_period=TSM_Q2,
    )
    for item in items:
        _verify_all_spans([item], bound=bound)
    return items


def _on_guidance(body: str = ON_SYNTHETIC_EXHIBIT):
    bound = _bind_on(body)
    items = on_profile().extract_guidance(
        bound=bound, release_document_id="doc:on-synthetic",
        segments=[], document_id="doc:tx", body_sha256="", event_id="evt_cik0001097864_2026q1_results",
        fiscal_period=ON_Q1,
    )
    for item in items:
        _verify_all_spans([item], bound=bound)
    return items


def test_tsm_release_facts_bind_the_reported_quarter_figure_not_the_comparative() -> None:
    by_id = _tsm_facts()
    twd = by_id["fact_revenue_twd"]
    assert "value" not in twd
    assert twd["typed_absence"]["reason"] == "missing_units"          # literal present, receipted, no TWD unit
    assert "reporting_currency_twd_not_in_unit_vocabulary" in twd["typed_absence"]["detail"]
    usd = by_id["fact_revenue_usd"]
    assert "typed_absence" not in usd
    assert usd["metric"] == "revenue_usd"
    assert usd["unit"] == "usd_billions"
    assert usd["value"] == 12.34                                        # never the US$8.00 billion a year ago
    assert usd["period"] == "2026-06-30"
    assert "12.34" in usd["source_span"]["display_excerpt"]


def test_tsm_usd_year_ago_comparative_stated_first_is_still_not_the_fact() -> None:
    body = TSM_SYNTHETIC_EXHIBIT.replace(
        "In U.S. dollars, second quarter revenue was US$12.34 billion, compared with US$8.00 billion a year ago.",
        "In U.S. dollars, revenue was US$8.00 billion a year ago, compared with US$12.34 billion in the second quarter of 2026.",
    )
    usd = _tsm_facts(body)["fact_revenue_usd"]
    assert usd["value"] == 12.34


def test_tsm_usd_fact_is_absent_when_the_release_names_a_different_quarter() -> None:
    """A release whose narrative reports the FIRST quarter bound to a Q2 event
    (the shape the first fixture had) yields a typed absence, never a figure
    stamped with the wrong period."""
    body = TSM_SYNTHETIC_EXHIBIT.replace("second quarter", "first quarter").replace("Second quarter", "First quarter")
    by_id = _tsm_facts(body)
    assert "typed_absence" in by_id["fact_revenue_usd"]
    assert by_id["fact_revenue_usd"]["typed_absence"]["reason"] == "no_span_addressable_evidence"
    assert by_id["fact_revenue_twd"]["typed_absence"]["reason"] == "no_span_addressable_evidence"


def test_tsm_two_competing_period_bound_usd_figures_are_an_absence_not_a_pick() -> None:
    body = TSM_SYNTHETIC_EXHIBIT.replace(
        "compared with US$8.00 billion a year ago.",
        "compared with US$8.00 billion a year ago. Second quarter 2026 revenue was also stated as US$12.40 billion.",
    )
    usd = _tsm_facts(body)["fact_revenue_usd"]
    assert "typed_absence" in usd
    assert "2 period-bound candidate figures" in usd["typed_absence"]["detail"]


def test_tsm_twd_absence_reason_distinguishes_missing_literal_from_missing_unit() -> None:
    """C4: no NT$ figure → no_span_addressable_evidence; NT$ figure present →
    missing_units. Never a converted USD substitute in either state."""
    body = TSM_SYNTHETIC_EXHIBIT.replace(
        "Second quarter net revenue was NT$1,234,567 million, an increase from NT$999,999 million a year ago. ", "")
    twd = _tsm_facts(body)["fact_revenue_twd"]
    assert "value" not in twd
    assert twd["typed_absence"]["reason"] == "no_span_addressable_evidence"
    assert _tsm_facts()["fact_revenue_twd"]["typed_absence"]["reason"] == "missing_units"


def test_on_release_fact_reads_the_column_dated_with_the_reported_period_end() -> None:
    revenue = _on_facts()["fact_revenue"]
    assert "typed_absence" not in revenue
    assert revenue["metric"] == "revenue"
    assert revenue["unit"] == "usd_millions"
    assert revenue["value"] == 1234.5
    assert revenue["period"] == "2026-04-03"
    assert "1,234.5" in revenue["source_span"]["display_excerpt"]


def test_on_prior_year_column_listed_first_is_not_read_positionally() -> None:
    body = ON_SYNTHETIC_EXHIBIT.replace(
        "<tr><td></td><td>April 3, 2026</td><td>April 4, 2025</td></tr>"
        "<tr><td>Revenue</td><td>$</td><td>$1,234.5 million</td><td>$</td><td>$1,500.0 million</td></tr>",
        "<tr><td></td><td>April 4, 2025</td><td>April 3, 2026</td></tr>"
        "<tr><td>Revenue</td><td>$</td><td>$1,500.0 million</td><td>$</td><td>$1,234.5 million</td></tr>",
    )
    assert _on_facts(body)["fact_revenue"]["value"] == 1234.5


def test_on_release_fact_is_absent_when_no_column_matches_the_reported_period_end() -> None:
    body = ON_SYNTHETIC_EXHIBIT.replace("April 3, 2026", "July 3, 2026")
    revenue = _on_facts(body)["fact_revenue"]
    assert "typed_absence" in revenue
    assert "2026-04-03" in revenue["typed_absence"]["detail"]
    misaligned = ON_SYNTHETIC_EXHIBIT.replace("<td>$</td><td>$1,500.0 million</td>", "")
    assert "typed_absence" in _on_facts(misaligned)["fact_revenue"]


def test_tsm_leading_comparative_adverbial_qualifies_its_whole_sentence() -> None:
    """'A year ago, revenue was US$8.00 billion.' — the marker sits in a figure-less
    leading clause; it still redirects the figure that follows the comma."""
    body = TSM_SYNTHETIC_EXHIBIT.replace(
        "In U.S. dollars, second quarter revenue was US$12.34 billion, compared with US$8.00 billion a year ago.",
        "In U.S. dollars, second quarter 2026 revenue rose year-over-year to US$12.34 billion. A year ago, revenue was US$8.00 billion.",
    )
    usd = _tsm_facts(body)["fact_revenue_usd"]
    assert "typed_absence" not in usd and usd["value"] == 12.34
    for lead in ("In the prior year, ", "Last year, ", "Sequentially, "):
        variant = body.replace("A year ago, ", lead)
        assert _tsm_facts(variant)["fact_revenue_usd"]["value"] == 12.34, lead


def test_tsm_growth_qualifier_in_the_figure_clause_does_not_suppress_the_fact() -> None:
    body = TSM_SYNTHETIC_EXHIBIT.replace(
        "In U.S. dollars, second quarter revenue was US$12.34 billion, compared with US$8.00 billion a year ago.",
        "In U.S. dollars, second quarter 2026 revenue rose year-over-year to US$12.34 billion.",
    )
    assert _tsm_facts(body)["fact_revenue_usd"]["value"] == 12.34


def test_abbreviations_do_not_split_sentences_so_recap_markers_keep_their_range() -> None:
    recap = ("We previously guided that, in U.S. dollars, we expect revenue between "
             "US$11.0 billion and US$11.5 billion for the third quarter of 2026.")
    only_recap = TSM_SYNTHETIC_EXHIBIT.replace(
        "In the first quarter of 2026 we had guided between US$11.0 billion and US$11.5 billion. "
        "Looking ahead to the third quarter of 2026, we expect revenue between "
        "US$13.0 billion and US$13.5 billion, assuming an exchange rate of 31.5 NTD per USD.",
        recap,
    )
    assert _tsm_guidance(only_recap) == []
    inc = only_recap.replace("We previously guided that, in U.S. dollars,", "Prior guidance from TSMC Inc. was that")
    assert _tsm_guidance(inc) == []
    with_forward = TSM_SYNTHETIC_EXHIBIT.replace(
        "In the first quarter of 2026 we had guided between US$11.0 billion and US$11.5 billion. ", recap + " ")
    item = _tsm_guidance(with_forward)[0]
    assert (item["low"], item["high"]) == (13.0, 13.5)


def test_tsm_fx_assumption_is_the_rate_stated_in_the_forward_sentence_only() -> None:
    recap_rate = TSM_SYNTHETIC_EXHIBIT.replace(
        "In the first quarter of 2026 we had guided between US$11.0 billion and US$11.5 billion. ",
        "In the first quarter of 2026 we had guided between US$11.0 billion and US$11.5 billion, "
        "assuming an exchange rate of 28.0 NTD per USD. ",
    )
    assert _tsm_guidance(recap_rate)[0]["fx_assumption"] == "31.5 NTD per USD"
    forward_without_rate = recap_rate.replace(", assuming an exchange rate of 31.5 NTD per USD", "")
    item = _tsm_guidance(forward_without_rate)[0]
    assert item["fx_assumption"] is None and (item["low"], item["high"]) == (13.0, 13.5)


def test_a_horizon_not_after_the_reported_period_is_not_guidance() -> None:
    same_quarter = TSM_SYNTHETIC_EXHIBIT.replace("Looking ahead to the third quarter of 2026", "Looking ahead to the second quarter of 2026")
    assert _tsm_guidance(same_quarter) == []
    earlier = TSM_SYNTHETIC_EXHIBIT.replace("Looking ahead to the third quarter of 2026", "Looking ahead to the first quarter of 2026")
    assert _tsm_guidance(earlier) == []
    on_same = ON_SYNTHETIC_EXHIBIT.replace("For the third quarter of 2026", "For the first quarter of 2026")
    assert _on_guidance(on_same) == []


def test_on_duplicate_period_end_columns_are_refused_not_first_taken() -> None:
    body = ON_SYNTHETIC_EXHIBIT.replace("April 4, 2025", "April 3, 2026")
    revenue = _on_facts(body)["fact_revenue"]
    assert "typed_absence" in revenue
    assert "2 Quarters Ended columns" in revenue["typed_absence"]["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# (e) Guidance: the forward range only, horizon READ from the sentence,
# explicit currency/basis/fx_assumption keys; every number asserted.
# ─────────────────────────────────────────────────────────────────────────────

def test_tsm_guidance_is_the_forward_range_with_its_stated_horizon_and_fx() -> None:
    items = _tsm_guidance()
    assert len(items) == 1
    item = items[0]
    assert item["schema"] == "guidance_item.v1"
    assert item["metric"] == "revenue"
    assert (item["low"], item["high"]) == (13.0, 13.5)                 # never the recap 11.0/11.5
    assert item["unit"] == "usd_billions"
    assert item["horizon"] == "2026Q3"
    assert item["status"] == "introduced"
    assert item["currency"] == "USD"
    assert item["basis"] == "reported_ifrs"
    assert item["fx_assumption"] == "31.5 NTD per USD"
    assert "13.0" in item["source_span"]["display_excerpt"]


def test_tsm_guidance_horizon_is_read_from_the_text_not_assumed() -> None:
    body = TSM_SYNTHETIC_EXHIBIT.replace("Looking ahead to the third quarter of 2026", "Looking ahead to the fourth quarter of 2026")
    assert _tsm_guidance(body)[0]["horizon"] == "2026Q4"
    no_year = TSM_SYNTHETIC_EXHIBIT.replace("third quarter of 2026", "third quarter")
    assert _tsm_guidance(no_year) == []                                  # no year stated → no horizon → no item


def test_tsm_recap_only_or_ambiguous_forward_ranges_emit_nothing() -> None:
    recap_only = TSM_SYNTHETIC_EXHIBIT.replace(
        "Looking ahead to the third quarter of 2026, we expect revenue between US$13.0 billion and US$13.5 billion, ", "")
    assert _tsm_guidance(recap_only) == []
    two_forward = TSM_SYNTHETIC_EXHIBIT.replace(
        "</p></body>", " We expect fourth quarter of 2026 revenue between US$14.0 billion and US$14.5 billion.</p></body>")
    assert _tsm_guidance(two_forward) == []


def test_tsm_fx_assumption_is_none_when_the_release_states_none() -> None:
    body = TSM_SYNTHETIC_EXHIBIT.replace(", assuming an exchange rate of 31.5 NTD per USD", "")
    item = _tsm_guidance(body)[0]
    assert item["fx_assumption"] is None and "fx_assumption" in item
    assert (item["low"], item["high"], item["horizon"]) == (13.0, 13.5, "2026Q3")


def test_on_guidance_is_the_forward_range_with_its_stated_horizon() -> None:
    items = _on_guidance()
    assert len(items) == 1
    item = items[0]
    assert item["schema"] == "guidance_item.v1"
    assert item["metric"] == "revenue"
    assert (item["low"], item["high"]) == (1400.0, 1500.0)
    assert item["unit"] == "usd_millions"
    assert item["horizon"] == "2026Q3"
    assert item["status"] == "introduced"
    assert item["currency"] == "USD"
    assert item["basis"] == "reported_gaap"
    assert item["fx_assumption"] is None


def test_on_guidance_reads_decimals_billions_and_the_stated_quarter() -> None:
    body = ON_SYNTHETIC_EXHIBIT.replace(
        "For the third quarter of 2026, we expect revenue in the range of $1,400 million to $1,500 million.",
        "For the fourth quarter of 2026, we expect revenue between $1.40 billion and $1.50 billion.",
    )
    item = _on_guidance(body)[0]
    assert (item["low"], item["high"], item["unit"], item["horizon"]) == (1.4, 1.5, "usd_billions", "2026Q4")
    mixed = ON_SYNTHETIC_EXHIBIT.replace("$1,400 million to $1,500 million", "$1,400 million to $1.5 billion")
    assert _on_guidance(mixed) == []
    recap = ON_SYNTHETIC_EXHIBIT.replace("For the third quarter of 2026, we expect", "Last quarter we guided")
    assert _on_guidance(recap) == []


# ─────────────────────────────────────────────────────────────────────────────
# (f) build_event_workspace guards: profile=None + non-AAPL → profile_required;
# apple's default path still works (no profile passed).
# ─────────────────────────────────────────────────────────────────────────────

def test_build_event_workspace_raises_profile_required_for_non_aapl_when_profile_is_none() -> None:
    registry = production_registry()
    filing = {
        "cik": "0001046179",
        "accession": TSM_ACCESSION,
        "form": "6-K",
        "filing_date": "2026-07-16",
        "acceptance_datetime": "2026-07-16T11:45:43Z",
        "report_date": "2026-06-30",
        "exhibit_url": "https://example/tsm.htm",
    }
    from engine.company_intelligence.event_workspace import WorkspaceError
    with pytest.raises(WorkspaceError, match="profile_required"):
        build_event_workspace(
            registry=registry,
            ticker="TSM",
            asof=date(2026, 7, 16),
            fiscal_period=FiscalPeriod(year=2026, quarter=2, calendar_end=date(2026, 6, 30)),
            exhibit_body=TSM_SYNTHETIC_EXHIBIT,
            filing=filing,
            transcript=None,
            transcript_sha256=None,
            observed_at="2026-07-16T11:45:43Z",
            source_available_at="2026-07-16T11:45:43Z",
            # NOTE: no `profile` kwarg — the default must NOT silently fall
            # back to apple_profile() for a non-AAPL issuer.
        )


def test_build_event_workspace_apple_default_path_still_works_without_profile() -> None:
    """Apple's default path must continue to work when `profile=None`."""
    from engine.company_intelligence.event_workspace import apple_registry
    registry = apple_registry()
    filing = {
        "cik": AAPL_CIK,
        "accession": "0000320193-26-000099",
        "form": "8-K",
        "filing_date": "2026-07-30",
        "acceptance_datetime": "2026-07-30T16:30:00Z",
        "report_date": "2026-06-27",
        "exhibit_url": "https://example/aapl.htm",
    }
    payload = build_event_workspace(
        registry=registry,
        ticker="AAPL",
        asof=date(2026, 7, 30),
        fiscal_period=FiscalPeriod(year=2026, quarter=3, calendar_end=date(2026, 6, 27)),
        exhibit_body="<html><body>apple placeholder</body></html>",
        filing=filing,
        transcript={"segments": [{"text": "placeholder", "speaker": None, "role": None}]},
        transcript_sha256="0" * 64,
        observed_at="2026-07-30T16:30:00Z",
        source_available_at="2026-07-30T16:30:00Z",
    )
    assert payload["issuer"]["display_name"] == "Apple Inc."
    # Default Apple profile supplies the pre-A5A transcript/guidance path.
    assert isinstance(payload["claims"], list)


# ─────────────────────────────────────────────────────────────────────────────
# (g) extract_guidance receives bound= and release_document_id= kwargs from
# build_event_workspace; verify by inspecting the call.
# ─────────────────────────────────────────────────────────────────────────────

def test_build_event_workspace_passes_bound_and_release_document_id_to_extract_guidance() -> None:
    """The build_event_workspace call must hand the bound release and the
    release_document_id through to the profile's extract_guidance method."""
    seen_kwargs: dict = {}

    # Wrap the module-level guidance callable directly (the IssuerProfile
    # dataclass is frozen so it cannot be monkey-patched in place).
    import engine.company_intelligence.issuer_profiles as profiles_mod
    original_guidance = profiles_mod._tsm_extract_guidance

    def _spy_guidance(*args, **kwargs):
        seen_kwargs.update(kwargs)
        return original_guidance(*args, **kwargs)

    profiles_mod._tsm_extract_guidance = _spy_guidance
    try:
        registry = production_registry()
        filing = {
            "cik": TSM_CIK,
            "accession": TSM_ACCESSION,
            "form": "6-K",
            "filing_date": "2026-07-16",
            "acceptance_datetime": "2026-07-16T11:45:43Z",
            "report_date": "2026-06-30",
            "exhibit_url": "https://example/tsm.htm",
        }
        build_event_workspace(
            registry=registry,
            ticker="TSM",
            asof=date(2026, 7, 16),
            fiscal_period=FiscalPeriod(year=2026, quarter=2, calendar_end=date(2026, 6, 30)),
            exhibit_body=TSM_SYNTHETIC_EXHIBIT,
            filing=filing,
            transcript=None,
            transcript_sha256=None,
            observed_at="2026-07-16T11:45:43Z",
            source_available_at="2026-07-16T11:45:43Z",
            profile=tsm_profile(),
        )
    finally:
        profiles_mod._tsm_extract_guidance = original_guidance

    assert "bound" in seen_kwargs
    assert seen_kwargs["bound"].revision.source_sha256 == _bind_tsm().revision.source_sha256
    assert "release_document_id" in seen_kwargs
    assert isinstance(seen_kwargs["release_document_id"], str)
    assert seen_kwargs["release_document_id"] == _bind_tsm().revision.document_id


# ─────────────────────────────────────────────────────────────────────────────
# (h) ``TSM_CIK`` and ``ON_CIK`` carry the SEC-attested zero-padded values.
# The E3C prior-art "generic code never branches on ticker" law is already
# covered by tests/test_issuer_profiles_a5a.py
# test_no_ticker_branch_in_generic_build_event_workspace_source, which
# continues to gate this module after the T05a edits.
# ─────────────────────────────────────────────────────────────────────────────

def test_tsm_and_on_cik_constants_are_sec_attested() -> None:
    assert TSM_CIK == "0001046179"
    assert ON_CIK == "0001097864"