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
from engine.company_intelligence.guidance_history import assess_management_sequence
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
TSM_HEADLINE = ("HSINCHU, Taiwan, R.O.C., Jul. 16, 2026 -- TSMC (TWSE: 2330, NYSE: TSM) today announced consolidated "
                "revenue of NT$1,234.56 billion, net income of NT$700.00 billion, and diluted earnings per share of "
                "NT$27.00 (US$4.30 per ADR unit) for the second quarter ended June 30, 2026.")
TSM_USD_SENTENCE = ("In US dollars, second quarter revenue was $12.34 billion, which increased 33.7% year-over-year "
                    "and increased 12.0% from the previous quarter.")
TSM_GUIDANCE_LEAD = ("Based on the Company's current business outlook, management expects the overall performance "
                     "for third quarter 2026 to be as follows:")
TSM_GUIDANCE_REVENUE = "•Revenue is expected to be between US$13.0 billion and US$13.5 billion;"
TSM_GUIDANCE_FX = "And, based on the exchange rate assumption of 1 US dollar to 32 NT dollars,"

# Synthetic look-alike of TSMC's real EX-99.1 structure (6-K 0001046179-26-000451):
# headline dated by quarter end, USD restatement sentence, quoted outlook prose,
# lead sentence + bullets, results-table caption. Figures are invented.
TSM_SYNTHETIC_EXHIBIT = (
    "<html><body>"
    "<p>TSMC Reports Second Quarter EPS of NT$27.00</p>"
    f"<p>{TSM_HEADLINE}</p>"
    "<p>Year-over-year, second quarter revenue increased 36.0%, while net income and diluted EPS both increased "
    "77.4%. Compared to first quarter 2026, second quarter results represented a 12.0% increase in revenue and a "
    "23.4% increase in net income. All figures were prepared in accordance with TIFRS on a consolidated basis.</p>"
    f"<p>{TSM_USD_SENTENCE} Gross margin for the quarter was 67.7%, operating margin was 60.3%, and net profit "
    "margin was 55.6%.</p>"
    "<p>\"Our business in the second quarter was supported by strong demand,\" said a synthetic CFO. "
    "\"Moving into third quarter 2026, we expect our business to be supported by continued strong demand.\"</p>"
    f"<p>{TSM_GUIDANCE_LEAD}</p>"
    f"<p>{TSM_GUIDANCE_REVENUE}</p>"
    f"<p>{TSM_GUIDANCE_FX}</p>"
    "<p>•Gross profit margin is expected to be between 65% and 67%;</p>"
    "<p>•Operating profit margin is expected to be between 56% and 58%.</p>"
    "<p>TSMC's 2026 second quarter consolidated results:</p>"
    "<p>(Unit: NT$ million, except for EPS)</p>"
    "</body></html>"
)


def _cells(*texts: str) -> str:
    return "".join(f"<td>{t}</td>" for t in texts)


ON_SUMMARY_LABEL_ROW = _cells("(Revenue and Net Income in millions)", "", "", "Q1 2026", "", "", "", "Q4 2025", "", "", "",
                              "Q1 2025", "", "", "", "Q1 2026", "", "", "", "Q4 2025", "", "", "", "Q1 2025", "")
ON_SUMMARY_REVENUE_ROW = _cells("Revenue", "", "$", "1,234.5", "", "", "$", "1,300.1", "", "", "$", "1,180.7", "", "",
                                "$", "1,234.5", "", "", "$", "1,300.1", "", "", "$", "1,180.7", "")
ON_OUTLOOK_LEAD = "The following table outlines onsemi's projected second quarter of 2026 GAAP and non-GAAP outlook."
ON_OUTLOOK_HEADER_ROW = _cells("", "", "Total onsemi GAAP", "", "Special Items **", "", "Total onsemi Non-GAAP***")
ON_OUTLOOK_REVENUE_ROW = _cells("Revenue", "", "$1,400 to $1,500 million", "", "-", "", "$1,400 to $1,500 million")
ON_IS_DATE_ROW = _cells("", "", "April 3, 2026", "", "", "January 2, 2026", "", "", "March 28, 2025", "")

# Synthetic look-alike of onsemi's real EX-99.1 structure (8-K 0001140361-26-018868):
# highlights bullet (rounded), captioned GAAP/Non-GAAP summary table with
# fiscal-quarter labels, segment table, outlook heading + lead + table with a
# "Total onsemi GAAP" column, and the income statement dated by quarter end.
ON_SYNTHETIC_EXHIBIT = (
    "<html><body>"
    "<p>PHOENIX, Ariz. - May 4, 2026 - onsemi (Nasdaq: ON) today announced results for the first quarter of 2026 "
    "with the following highlights:</p>"
    f"<table><tr>{_cells('•', 'Revenue of $1,235 million, increasing 5% year-over-year')}</tr></table>"
    "<p>Selected financial results for the quarter are shown below with comparable periods (unaudited):</p>"
    "<table>"
    f"<tr>{_cells('', '', 'GAAP', '', '', 'Non-GAAP', '')}</tr>"
    f"<tr>{ON_SUMMARY_LABEL_ROW}</tr>"
    f"<tr>{ON_SUMMARY_REVENUE_ROW}</tr>"
    f"<tr>{_cells('Gross Margin', '', '', '38.4', '%', '', '', '38.5', '%', '', '', '37.6', '%', '', '', '39.3', '%', '', '', '38.5', '%', '', '', '37.6', '%')}</tr>"
    "</table>"
    "<p>Revenue Summary</p><p>(in millions)</p>"
    "<table>"
    f"<tr>{_cells('', '', 'Quarters Ended', '', '', '', '', '', '', '')}</tr>"
    f"<tr>{_cells('Business Segment', '', '', 'Q1 2026', '', '', '', 'Q4 2025', '', '', '', 'Q1 2025', '', '', 'Sequential Change', '', '', 'Year-over-Year Change', '')}</tr>"
    f"<tr>{_cells('PSG', '', '$', '700.0', '', '', '$', '720.0', '', '', '$', '650.0', '', '', '', '(3', ')%', '', '', '8', '%')}</tr>"
    f"<tr>{_cells('Total', '', '$', '1,234.5', '', '', '$', '1,300.1', '', '', '$', '1,180.7', '', '', '', '(5', ')%', '', '', '5', '%')}</tr>"
    "</table>"
    "<p>SECOND QUARTER 2026 OUTLOOK</p>"
    f"<p>{ON_OUTLOOK_LEAD}</p>"
    "<table>"
    f"<tr>{ON_OUTLOOK_HEADER_ROW}</tr>"
    f"<tr>{ON_OUTLOOK_REVENUE_ROW}</tr>"
    f"<tr>{_cells('Gross Margin', '', '39.9% to 41.9%', '', '0.1%', '', '40.0% to 42.0%')}</tr>"
    "</table>"
    "<p>(in millions, except per share data)</p>"
    "<table>"
    f"<tr>{_cells('', '', 'Quarters Ended', '', '', '', '', '', '', '')}</tr>"
    f"<tr>{ON_IS_DATE_ROW}</tr>"
    f"<tr>{_cells('Revenue', '', '$', '1,234.5', '', '', '$', '1,300.1', '', '', '$', '1,180.7', '')}</tr>"
    f"<tr>{_cells('Cost of revenue', '', '', '760.0', '', '', '', '800.0', '', '', '', '740.0', '')}</tr>"
    "</table>"
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


def _usd(body: str = TSM_SYNTHETIC_EXHIBIT):
    return _tsm_facts(body)["fact_revenue_usd"]


def _twd(body: str = TSM_SYNTHETIC_EXHIBIT):
    return _tsm_facts(body)["fact_revenue_twd"]


def _on_rev(body: str = ON_SYNTHETIC_EXHIBIT, **kw):
    return _on_facts(body, **kw)["fact_revenue"]


def _is_absent(fact, reason: str = "no_span_addressable_evidence") -> bool:
    return "typed_absence" in fact and fact["typed_absence"]["reason"] == reason


# ── TSM release facts: closed template, anchored on the headline's quarter-end date ──

def test_tsm_release_facts_bind_the_template_sentence_and_receipt_the_headline() -> None:
    by_id = _tsm_facts()
    usd, twd = by_id["fact_revenue_usd"], by_id["fact_revenue_twd"]
    assert (usd["value"], usd["unit"], usd["period"]) == (12.34, "usd_billions", "2026-06-30")
    assert _is_absent(twd, "missing_units")
    assert "NT$1,234.56 billion" in twd["typed_absence"]["detail"] or "headline" in twd["typed_absence"]["detail"]


@pytest.mark.parametrize("headline", [
    TSM_HEADLINE.replace("second quarter ended June 30, 2026", "first quarter ended March 31, 2026"),   # other quarter
    TSM_HEADLINE.replace("June 30, 2026", "June 30, 2025"),                                             # other year
    TSM_HEADLINE.replace("June 30, 2026", "June 29, 2026"),                                             # date one day off
    TSM_HEADLINE.replace("second quarter", "first quarter"),                                            # ordinal/date disagree
    TSM_HEADLINE.replace("today announced consolidated revenue of", "today reported revenue of"),      # not the template
    "",
])
def test_tsm_without_exactly_one_date_anchored_headline_every_fact_is_absent(headline: str) -> None:
    body = TSM_SYNTHETIC_EXHIBIT.replace(TSM_HEADLINE, headline)
    by_id = _tsm_facts(body)
    assert _is_absent(by_id["fact_revenue_usd"]) and _is_absent(by_id["fact_revenue_twd"])
    assert "headline" in by_id["fact_revenue_usd"]["typed_absence"]["detail"]
    two = TSM_SYNTHETIC_EXHIBIT.replace(f"<p>{TSM_HEADLINE}</p>", f"<p>{TSM_HEADLINE}</p><p>{TSM_HEADLINE}</p>")
    assert "2 headline blocks" in _usd(two)["typed_absence"]["detail"]


def test_tsm_usd_template_requires_the_reported_ordinal_and_sentence_start() -> None:
    other_quarter = TSM_SYNTHETIC_EXHIBIT.replace("In US dollars, second quarter revenue", "In US dollars, first quarter revenue")
    assert _is_absent(_usd(other_quarter)) and "0 'In US dollars" in _usd(other_quarter)["typed_absence"]["detail"]
    mid_sentence = TSM_SYNTHETIC_EXHIBIT.replace("In US dollars, second quarter revenue", "As previously reported, In US dollars, second quarter revenue")
    assert _is_absent(_usd(mid_sentence))
    restated_twice = TSM_SYNTHETIC_EXHIBIT.replace(
        f"<p>{TSM_USD_SENTENCE}", f"<p>In US dollars, second quarter revenue was $12.00 billion in the prior-year period. {TSM_USD_SENTENCE}")
    assert _is_absent(_usd(restated_twice)) and "2 'In US dollars" in _usd(restated_twice)["typed_absence"]["detail"]
    dotted = TSM_SYNTHETIC_EXHIBIT.replace("In US dollars,", "In U.S. dollars,")
    assert _usd(dotted)["value"] == 12.34
    us_prefixed = TSM_SYNTHETIC_EXHIBIT.replace("revenue was $12.34 billion", "revenue was US$12.34 billion")
    assert _usd(us_prefixed)["value"] == 12.34


@pytest.mark.parametrize("prose", [
    # every construction that leaked a wrong value in review rounds 1-4: none is the template
    "Second quarter revenue exceeded US$8.00 billion.",
    "Second quarter revenue was 17.8% above US$8.00 billion.",
    "Second quarter revenue more than doubled from US$8.00 billion.",
    "Second quarter revenue was an improvement from US$8.00 billion.",
    "Second quarter revenue was flat relative to US$8.00 billion.",
    "Second quarter revenue rose in comparison with US$8.00 billion.",
    "Compared with the like period, revenue was US$8.00 billion.",
    "Revenue grew from US$8.00 billion.",
    "In the year-earlier quarter, revenue was US$8.00 billion.",
    "In the second quarter of 2025, revenue was US$8.00 billion.",
    "Revenue for the second quarter of 2025 was US$8.00 billion.",
    "Revenue for the quarter ended June 30, 2025 was US$8.00 billion.",
    "In the second quarter of FY2025, revenue was US$8.00 billion.",
    "Q2 FY2025 revenue was US$8.00 billion.",
    "In the fiscal 2025 second quarter, revenue was US$8.00 billion.",
    "Revenue for the six months ended June 30, 2026 was US$23.00 billion.",
    "Full-year 2025 revenue was US$8.00 billion.",
    "Second quarter revenue guidance was US$11.00 billion.",
    "Second quarter revenue is expected to be US$13.00 billion.",
    "Second quarter revenue would have been US$11.00 billion excluding the divestiture.",
    "Second quarter 2026 revenue on a pro forma basis was US$11.00 billion.",
    "Excluding the joint venture, second quarter revenue was US$11.00 billion.",
    "As previously reported, second quarter revenue was US$12.00 billion.",
    "Revenue in the second quarter of 2026 of our Arizona fab was US$1.00 billion.",
    "Second quarter revenue per wafer was US$1.00 billion.",
    "Second quarter 2026 gross profit was US$7.00 billion.",
    "Revenue was US$12.00 billion.",
    "A year ago, revenue was US$8.00 billion.",
    "Capacity expansion completes in the fourth quarter of 2026 at TSMC Corp. Revenue was US$8.00 billion.",
])
def test_tsm_prose_that_is_not_the_template_never_binds(prose: str) -> None:
    """With the template sentence removed, the prose alone yields an absence;
    with the template sentence present, the prose never displaces it."""
    alone = TSM_SYNTHETIC_EXHIBIT.replace(TSM_USD_SENTENCE, prose)
    assert _is_absent(_usd(alone)), prose
    beside = TSM_SYNTHETIC_EXHIBIT.replace(TSM_USD_SENTENCE, f"{prose} {TSM_USD_SENTENCE}")
    assert _usd(beside)["value"] == 12.34, prose


def test_tsm_over_suppression_cannot_promote_a_survivor_because_nothing_is_suppressed() -> None:
    """Re-verify #3/#4 blocker 1: the six-month figure and a merged first-quarter
    clause sit beside the template sentence; the template binds 12.34 and the
    other figures are simply not candidates."""
    body = TSM_SYNTHETIC_EXHIBIT.replace(
        TSM_USD_SENTENCE,
        "Revenue for the six months ended June 30, 2026 was US$23.00 billion. Advanced technologies accounted for "
        f"74% of total wafer revenue in the first quarter of 2026 at TSMC Corp. {TSM_USD_SENTENCE} "
        "Revenue for the quarter ended June 30, 2025 was $8.00 billion.")
    assert _usd(body)["value"] == 12.34


def test_tsm_twd_absence_reason_distinguishes_receipted_literal_from_missing_literal() -> None:
    assert _is_absent(_twd(), "missing_units")
    # the anchor still matches but the NT$ literal is duplicated in the block → not uniquely receiptable
    dup = TSM_SYNTHETIC_EXHIBIT.replace(f"<p>{TSM_HEADLINE}</p>", f"<p>{TSM_HEADLINE} (NT$1,234.56 billion)</p>")
    assert _is_absent(_twd(dup))


def test_tsm_facts_need_a_reported_period() -> None:
    by_id = _tsm_facts(fiscal_period=None)
    assert _is_absent(by_id["fact_revenue_usd"]) and _is_absent(by_id["fact_revenue_twd"])


# ── TSM guidance: lead sentence + bullet window ──

def test_tsm_guidance_is_the_revenue_bullet_under_the_one_lead_with_its_fx_clause() -> None:
    (item,) = _tsm_guidance()
    assert (item["low"], item["high"], item["unit"], item["horizon"]) == (13.0, 13.5, "usd_billions", "2026Q3")
    assert item["fx_assumption"] == "1 US dollar to 32 NT dollars"
    assert item["basis"] == "reported_ifrs" and item["currency"] == "USD" and item["status"] == "introduced"


@pytest.mark.parametrize("mutation", [
    lambda b: b.replace(TSM_GUIDANCE_LEAD, ""),                                                            # no lead
    lambda b: b.replace(f"<p>{TSM_GUIDANCE_LEAD}</p>", f"<p>{TSM_GUIDANCE_LEAD}</p><p>{TSM_GUIDANCE_LEAD}</p>"),  # two leads
    lambda b: b.replace("for third quarter 2026 to be as follows", "for second quarter 2026 to be as follows"),  # horizon == reported
    lambda b: b.replace("for third quarter 2026 to be as follows", "for first quarter 2026 to be as follows"),   # horizon before reported
    lambda b: b.replace(TSM_GUIDANCE_REVENUE, ""),                                                         # no revenue bullet
    lambda b: b.replace(f"<p>{TSM_GUIDANCE_REVENUE}</p>", f"<p>{TSM_GUIDANCE_REVENUE}</p><p>•Revenue is expected to be between US$14.0 billion and US$14.5 billion;</p>"),  # two bullets
    lambda b: b.replace(f"<p>{TSM_GUIDANCE_REVENUE}</p>", "<p>We remain confident in our outlook.</p>" + f"<p>{TSM_GUIDANCE_REVENUE}</p>"),  # bullet outside the window
    lambda b: b.replace(TSM_GUIDANCE_REVENUE, "Revenue in the third quarter of 2026 will be between US$13.0 billion and US$13.5 billion."),  # range in prose, not the bullet template
    lambda b: b.replace(TSM_GUIDANCE_FX, "And, based on the exchange rate assumption of 1 US dollar to 32 NT dollars, and based on the exchange rate assumption of 1 US dollar to 31 NT dollars,"),  # two different FX clauses
])
def test_tsm_guidance_refuses_every_non_template_shape(mutation) -> None:
    assert _tsm_guidance(mutation(TSM_SYNTHETIC_EXHIBIT)) == []


def test_tsm_guidance_fx_is_none_when_the_window_states_none_and_recaps_are_ignored() -> None:
    no_fx = TSM_SYNTHETIC_EXHIBIT.replace(f"<p>{TSM_GUIDANCE_FX}</p>", "")
    (item,) = _tsm_guidance(no_fx)
    assert item["fx_assumption"] is None and (item["low"], item["high"]) == (13.0, 13.5)
    recap = TSM_SYNTHETIC_EXHIBIT.replace(
        f"<p>{TSM_GUIDANCE_LEAD}</p>",
        "<p>In April we had guided that revenue would be between US$11.0 billion and US$11.5 billion, assuming an "
        f"exchange rate of 31.7 NT dollars.</p><p>{TSM_GUIDANCE_LEAD}</p>")
    (item,) = _tsm_guidance(recap)
    assert (item["low"], item["high"], item["fx_assumption"]) == (13.0, 13.5, "1 US dollar to 32 NT dollars")


def test_tsm_guidance_horizon_is_read_from_the_lead_not_assumed() -> None:
    body = TSM_SYNTHETIC_EXHIBIT.replace("for third quarter 2026 to be as follows", "for fourth quarter 2026 to be as follows")
    assert _tsm_guidance(body)[0]["horizon"] == "2026Q4"
    rollover = TSM_SYNTHETIC_EXHIBIT.replace("for third quarter 2026 to be as follows", "for first quarter 2027 to be as follows")
    assert _tsm_guidance(rollover)[0]["horizon"] == "2027Q1"


def test_guidance_without_a_reported_period_emits_nothing() -> None:
    for profile, body, binder, doc in (
        (tsm_profile(), TSM_SYNTHETIC_EXHIBIT, _bind_tsm, "doc:tsm-synthetic"),
        (on_profile(), ON_SYNTHETIC_EXHIBIT, _bind_on, "doc:on-synthetic"),
    ):
        assert profile.extract_guidance(
            bound=binder(body), release_document_id=doc, segments=[], document_id="doc:tx",
            body_sha256="", event_id="evt_x") == []


# ── ON release facts: label-bound summary table ──

def test_on_release_fact_binds_the_cells_under_the_reported_label_never_a_position() -> None:
    fact = _on_rev()
    assert (fact["value"], fact["unit"], fact["period"]) == (1234.5, "usd_millions", "2026-04-03")
    # swap the GAAP column order: the value still follows the label
    swapped = ON_SYNTHETIC_EXHIBIT.replace(ON_SUMMARY_LABEL_ROW, ON_SUMMARY_LABEL_ROW.replace("Q1 2026", "TMP").replace("Q4 2025", "Q1 2026").replace("TMP", "Q4 2025"))
    assert _on_rev(swapped)["value"] == 1300.1


@pytest.mark.parametrize("mutation, detail", [
    (lambda b: b.replace("Q1 2026", "Q1 2025"), "0 captioned summary tables"),                        # label absent
    (lambda b: b.replace("(Revenue and Net Income in millions)", "(Revenue and Net Income)"), "0 captioned"),  # no unit caption
    (lambda b: b.replace(ON_SUMMARY_REVENUE_ROW, ON_SUMMARY_REVENUE_ROW.replace("1,234.5", "1,234.6", 1)), "disagree"),  # GAAP vs non-GAAP disagree
    (lambda b: b.replace(ON_SUMMARY_REVENUE_ROW, ON_SUMMARY_REVENUE_ROW.replace("1,234.5", "$1,234.5 million", 1)), "not plain figures"),
    (lambda b: b.replace(ON_IS_DATE_ROW, ON_IS_DATE_ROW.replace("April 3, 2026", "April 4, 2026")), "no Quarters Ended table dates"),  # document never names the period end
    (lambda b: b.replace(ON_SUMMARY_REVENUE_ROW, ""), "0 Revenue rows"),
    (lambda b: b.replace(ON_SUMMARY_REVENUE_ROW, ON_SUMMARY_REVENUE_ROW.replace("1,234.5", "(1,234.5)")), "not plain figures"),  # parenthesised cell: typed absence, never a parsed or sign-blind value
    (lambda b: b.replace(ON_SUMMARY_REVENUE_ROW, ON_SUMMARY_REVENUE_ROW.replace("1,234.5", "(1,234.5)", 1)), "not plain figures"),  # GAAP negative vs non-GAAP positive never agree
])
def test_on_release_fact_is_absent_for_every_non_template_table(mutation, detail: str) -> None:
    fact = _on_rev(mutation(ON_SYNTHETIC_EXHIBIT))
    assert _is_absent(fact) and detail in fact["typed_absence"]["detail"], fact["typed_absence"]["detail"]


def test_on_release_fact_ignores_the_rounded_highlight_and_the_segment_total() -> None:
    """The highlights bullet ('Revenue of $1,235 million') and the segment
    table total are not the captioned summary table; only the label-bound cell is."""
    assert _on_rev()["value"] == 1234.5
    no_summary = ON_SYNTHETIC_EXHIBIT.replace("(Revenue and Net Income in millions)", "")
    assert _is_absent(_on_rev(no_summary))


def test_on_release_fact_needs_a_reported_period() -> None:
    assert _is_absent(_on_rev(fiscal_period=None))


# ── ON guidance: outlook lead + GAAP column ──

def test_on_guidance_is_the_gaap_range_under_the_one_outlook_lead() -> None:
    (item,) = _on_guidance()
    assert (item["low"], item["high"], item["unit"], item["horizon"]) == (1400.0, 1500.0, "usd_millions", "2026Q2")
    assert item["fx_assumption"] is None and item["basis"] == "reported_gaap"


@pytest.mark.parametrize("mutation", [
    lambda b: b.replace(ON_OUTLOOK_LEAD, ""),                                                              # no lead
    lambda b: b.replace(f"<p>{ON_OUTLOOK_LEAD}</p>", f"<p>{ON_OUTLOOK_LEAD}</p><p>{ON_OUTLOOK_LEAD}</p>"),  # two leads
    lambda b: b.replace("projected second quarter of 2026", "projected first quarter of 2026"),           # horizon == reported
    lambda b: b.replace("Total onsemi GAAP", "Total onsemi"),                                              # no GAAP header label
    lambda b: b.replace(ON_OUTLOOK_REVENUE_ROW, ON_OUTLOOK_REVENUE_ROW.replace("$1,400 to $1,500 million", "$1,400 to $1,500", 1)),  # malformed cell
    lambda b: b.replace(ON_OUTLOOK_REVENUE_ROW, ON_OUTLOOK_REVENUE_ROW.replace("$1,400 to $1,500 million", "$1,400 to $1,500 million*", 1)),  # valid prefix + footnote marker: fullmatch only
    lambda b: b.replace(ON_OUTLOOK_REVENUE_ROW, ON_OUTLOOK_REVENUE_ROW.replace("$1,400 to $1,500 million", "$1,400 to $1,500 million excluding the 53rd week", 1)),  # valid prefix + trailing qualifier
    lambda b: b.replace(ON_OUTLOOK_REVENUE_ROW, ""),                                                       # no revenue row
    lambda b: b.replace(f"<p>{ON_OUTLOOK_LEAD}</p><table>", f"<p>{ON_OUTLOOK_LEAD}</p><p>x</p><p>y</p><table>"),  # table not adjacent
])
def test_on_guidance_refuses_every_non_template_shape(mutation) -> None:
    assert _on_guidance(mutation(ON_SYNTHETIC_EXHIBIT)) == []


def test_on_guidance_reads_the_gaap_column_by_label_not_position_and_billions() -> None:
    reordered = ON_SYNTHETIC_EXHIBIT.replace(
        ON_OUTLOOK_HEADER_ROW, _cells("", "", "Total onsemi Non-GAAP***", "", "Special Items **", "", "Total onsemi GAAP")).replace(
        ON_OUTLOOK_REVENUE_ROW, _cells("Revenue", "", "$1,405 to $1,505 million", "", "-", "", "$1,400 to $1,500 million"))
    (item,) = _on_guidance(reordered)
    assert (item["low"], item["high"]) == (1400.0, 1500.0)
    billions = ON_SYNTHETIC_EXHIBIT.replace("$1,400 to $1,500 million", "$1.40 to $1.50 billion")
    (item,) = _on_guidance(billions)
    assert (item["low"], item["high"], item["unit"]) == (1.4, 1.5, "usd_billions")


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

# ── T06 alignment: release facts and guidance items state the SAME closed definition tokens ──

def _composer_actual(fact: dict, fiscal_period: str) -> dict:
    """The shape engine.market_ontology.semiconductor_theme_research._build_economics hands to
    assess_management_sequence for the actual — except that the composer reads fiscal_period from
    its projected `reported` row (YYYYQn), which a raw fact does not carry (its `period` is the ISO
    calendar end); the projector owns that translation, so the caller supplies it here."""
    actual = {"metric": fact["metric"], "value": fact["value"], "unit": fact["unit"], "fiscal_period": fiscal_period,
              "source_span": {"event_id": fact["event_id"]}}
    for optional in ("basis", "currency", "perimeter", "definition"):
        if optional in fact:
            actual[optional] = fact[optional]
    return actual


@pytest.mark.parametrize("facts_fn, guidance_fn, fact_id, reported, position", [
    (_tsm_facts, _tsm_guidance, "fact_revenue_usd", "2026Q2", "below_range"),   # 12.34 vs a 13.0–13.5 prior range
    (_on_facts, _on_guidance, "fact_revenue", "2026Q1", "below_range"),         # 1234.5 vs a 1400–1500 prior range
])
def test_release_fact_and_guidance_definitions_compare_like_for_like(facts_fn, guidance_fn, fact_id, reported, position) -> None:
    fact = facts_fn()[fact_id]
    (new_outlook,) = guidance_fn()
    for field in ("metric", "unit", "basis", "currency"):
        assert fact[field] == new_outlook[field], (field, fact[field], new_outlook[field])
    prior = {**new_outlook, "horizon": reported}  # the previous release's outlook for the reported quarter
    result = assess_management_sequence(prior, _composer_actual(fact, reported), new_outlook)
    assert result["comparisons"]["prior_vs_actual"] == {"status": "comparable", "reason": None, "position": position}
    assert result["comparisons"]["actual_vs_new_outlook"]["reason"] == "different_period"
    assert "definition_unqualified:perimeter" in result["limitations"] and "definition_unqualified:definition" in result["limitations"]
    assert not any(token.startswith("comparison_refused") for token in result["limitations"])
    assert all(v is False for v in result["authority"].values())
