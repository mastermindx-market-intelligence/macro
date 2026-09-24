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
    "<p>TSMC today announced consolidated revenue for the first quarter of 2026. "
    "First quarter net revenue was NT$1,234,567 million. "
    "In U.S. dollars, revenue was US$12.34 billion.</p>"
    "<table>"
    "<tr><td>Quarters Ended March 31,</td></tr>"
    "<tr><td>2026</td><td>2025</td></tr>"
    "</table>"
    "<p>Looking ahead to the second quarter of 2026, we expect revenue between "
    "US$13.0 billion and US$13.5 billion, assuming an exchange rate of 31.5 NTD per USD.</p>"
    "</body></html>"
)

ON_SYNTHETIC_EXHIBIT = (
    "<html><body>"
    "<p>onsemi today announced first quarter 2026 results.</p>"
    "<table>"
    "<tr><td>Quarters Ended</td></tr>"
    "<tr><td>April 3, 2026</td><td>April 4, 2025</td></tr>"
    "<tr><td>Revenue</td><td>$1,234.5 million</td><td>$1,500.0 million</td></tr>"
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


def test_tsm_release_facts_on_synthetic_exhibit() -> None:
    bound = _bind_tsm()
    fiscal_period = FiscalPeriod(year=2026, quarter=2, calendar_end=date(2026, 6, 30))
    facts = tsm_profile().extract_release_facts(
        bound=bound, document_id="doc:tsm-synthetic", event_id="evt_cik0001046179_2026q2_results",
        fiscal_period=fiscal_period,
    )
    by_id = {fact["fact_id"]: fact for fact in facts}
    # TSM emits at minimum: NT$ net revenue (typed absence — TWD unit missing
    # from vocabulary) AND a USD-restated revenue (present, unit usd_billions).
    assert "fact_revenue_twd" in by_id
    assert "fact_revenue_usd" in by_id

    # TWD fact: typed absence with the documented detail string; no value.
    twd_fact = by_id["fact_revenue_twd"]
    assert "typed_absence" in twd_fact
    assert "value" not in twd_fact
    assert twd_fact["typed_absence"]["reason"] == "no_span_addressable_evidence"
    assert twd_fact["metric"] == "revenue"
    assert "reporting_currency_twd_not_in_unit_vocabulary" in twd_fact["typed_absence"]["detail"]

    # USD fact: present, unit usd_billions, receipted against the
    # "US$12.34 billion" literal.
    usd_fact = by_id["fact_revenue_usd"]
    assert "typed_absence" not in usd_fact
    assert usd_fact["metric"] == "revenue_usd"
    assert usd_fact["unit"] == "usd_billions"
    assert "12.34" in usd_fact["source_span"]["display_excerpt"]
    _verify_all_spans(facts, bound=bound)


def test_on_release_facts_on_synthetic_exhibit() -> None:
    bound = _bind_on()
    fiscal_period = FiscalPeriod(year=2026, quarter=1, calendar_end=date(2026, 4, 3))
    facts = on_profile().extract_release_facts(
        bound=bound, document_id="doc:on-synthetic", event_id="evt_cik0001097864_2026q1_results",
        fiscal_period=fiscal_period,
    )
    by_id = {fact["fact_id"]: fact for fact in facts}
    assert "fact_revenue" in by_id
    revenue = by_id["fact_revenue"]
    assert "typed_absence" not in revenue
    assert revenue["metric"] == "revenue"
    assert revenue["unit"] == "usd_millions"
    assert "1,234.5" in revenue["source_span"]["display_excerpt"]
    _verify_all_spans(facts, bound=bound)


def test_tsm_release_facts_absence_when_no_twd_unit_in_vocabulary_is_not_an_arithmetic_substitute() -> None:
    """C4: zero arithmetic — a missing TWD unit must NOT be substituted by
    an inferred USD conversion.  The TWD fact must be typed absence, never
    a present fact with a converted value."""
    bound = _bind_tsm()
    fiscal_period = FiscalPeriod(year=2026, quarter=2, calendar_end=date(2026, 6, 30))
    facts = tsm_profile().extract_release_facts(
        bound=bound, document_id="doc:tsm-synthetic", event_id="evt:x", fiscal_period=fiscal_period,
    )
    by_id = {fact["fact_id"]: fact for fact in facts}
    twd_fact = by_id["fact_revenue_twd"]
    # Never an inferred/converted present fact.
    assert "value" not in twd_fact
    assert twd_fact["typed_absence"]["reason"] == "no_span_addressable_evidence"


# ─────────────────────────────────────────────────────────────────────────────
# (e) Guidance: NEXT-quarter revenue range, with explicit currency/basis/
# fx_assumption keys; horizon different from the reported quarter.
# ─────────────────────────────────────────────────────────────────────────────

def test_tsm_guidance_extracts_next_quarter_revenue_with_fx_assumption() -> None:
    bound = _bind_tsm()
    fiscal_period = FiscalPeriod(year=2026, quarter=2, calendar_end=date(2026, 6, 30))
    guidance = tsm_profile().extract_guidance(
        bound=bound, release_document_id="doc:tsm-synthetic",
        segments=[], document_id="doc:tx", body_sha256="", event_id="evt_cik0001046179_2026q2_results",
    )
    assert len(guidance) == 1
    item = guidance[0]
    assert item["schema"] == "guidance_item.v1"
    assert item["metric"] == "revenue"
    assert item["currency"] == "USD"
    assert item["basis"] == "reported_ifrs"
    # Horizon differs from reported quarter (Q2 reported → Q3 next).
    assert item["horizon"] == "2026Q3"
    # fx_assumption is a verbatim phrase from the release body.
    assert isinstance(item["fx_assumption"], str)
    assert "exchange rate" in item["fx_assumption"].lower() or "NTD per USD" in item["fx_assumption"]
    # Source span replays.
    assert "source_span" in item


def test_on_guidance_extracts_next_quarter_revenue_with_no_fx_assumption() -> None:
    bound = _bind_on()
    fiscal_period = FiscalPeriod(year=2026, quarter=1, calendar_end=date(2026, 4, 3))
    guidance = on_profile().extract_guidance(
        bound=bound, release_document_id="doc:on-synthetic",
        segments=[], document_id="doc:tx", body_sha256="", event_id="evt_cik0001097864_2026q1_results",
    )
    assert len(guidance) == 1
    item = guidance[0]
    assert item["schema"] == "guidance_item.v1"
    assert item["metric"] == "revenue"
    assert item["currency"] == "USD"
    assert item["basis"] == "reported_gaap"
    # ON reports USD; no FX assumption.
    assert item["fx_assumption"] is None
    # Horizon differs from reported quarter (Q1 reported → Q3 next, per the
    # synthetic exhibit guidance sentence).
    assert item["horizon"] == "2026Q3"


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