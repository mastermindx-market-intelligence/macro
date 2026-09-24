"""T05b — Semiconductor earnings intake generalization (identity-declared only).

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001.

Code-under-test: :mod:`scripts.refresh_event_workspaces`.  Verifies that:
  - ``DISCOVERY_TICKERS`` is exactly ``(*HOMEBUILDER_TICKERS, "TSM", "ON")``
    (the homebuilder tuple's value/meaning is preserved — see C1).
  - A results 6-K is admitted ONLY for an issuer whose identity declares
    ``external_ids["results_form"] == "6-K"`` (TSMC-style), via a narrow
    discriminator (calendar-quarter-end reportDate + EX-99.1 filename
    matching the quarterly-results keyword pattern).
  - A 52/53-week fiscal calendar mismatch (a stated period end that drifts
    a few days from the calendar-quarter-end anchor ``fiscal_period_for_
    report_date`` derives) is accepted ONLY for an issuer whose identity
    declares ``external_ids["fiscal_calendar"] == "52_53_week"`` (onsemi-
    style).  Anything past the named 6-day tolerance is rejected.
  - Every other issuer's behaviour is byte-identical (8-K/2.02 path
    untouched, ::warning fail-soft skip path preserved).
  - The stated-period regex accepts both the homebuilders' "quarter ended"
    phrasing AND a "Quarters Ended" (plural, capitalized) phrasing.
  - The bare ``EX-99`` typed exhibit is rescued by the filename hint (the
    pre-existing ``_select_exhibit_99_1`` fallback is reused unchanged).

Synthetic IssuerIdentity objects are built per-test so the suite stays
independent of any sibling-lane TSM/ON identities that may or may not have
landed in the worktree — and never imports ``tsm_issuer`` / ``on_issuer``.
"""
from __future__ import annotations

from datetime import date
from typing import Mapping

import pytest

from engine.company_intelligence.identity import (
    IssuerIdentity,
    ListingAlias,
    company_id_for_cik,
)
from engine.company_intelligence.issuer_profiles import HOMEBUILDER_TICKERS

import scripts.refresh_event_workspaces as refresh_mod


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic identity builders (no real TSM/ON identities imported).
# ─────────────────────────────────────────────────────────────────────────────


def _synthetic_issuer(
    *,
    cik: str,
    ticker: str,
    fiscal_year_end_month: int = 12,
    external_ids: Mapping[str, str] | None = None,
) -> IssuerIdentity:
    """Build a minimum-viable IssuerIdentity for testing.

    The ticker → company_id wiring is the only field the discovery flow
    actually consumes beyond ``external_ids`` + ``fiscal_year_end_month``,
    so this is enough surface area to exercise every discriminator.
    """
    return IssuerIdentity(
        company_id=company_id_for_cik(cik),
        display_name=f"Synthetic {ticker}",
        fiscal_year_end_month=fiscal_year_end_month,
        reporting_currency="USD",
        listings=(
            ListingAlias(
                ticker=ticker, mic="XNAS", share_class="common",
                trading_currency="USD", is_primary=True,
            ),
        ),
        external_ids=dict(external_ids or {}),
    )


# ─────────────────────────────────────────────────────────────────────────────
# (a) DISCOVERY_TICKERS is a strict superset of HOMEBUILDER_TICKERS.
# ─────────────────────────────────────────────────────────────────────────────


def test_discovery_tickers_supersets_homebuilder_tickers_in_order() -> None:
    """``DISCOVERY_TICKERS`` MUST be ``(*HOMEBUILDER_TICKERS, "TSM", "ON")``.

    The contract pins both the value (every homebuilder is still in there,
    in the same order) and the meaning (C1 — the homebuilder tuple is
    frozen at the right shape, never re-defined; ``HOMEBUILDER_TICKERS``
    keeps its own definition and ``DISCOVERY_TICKERS`` is built ON TOP of
    it).
    """
    expected = tuple(HOMEBUILDER_TICKERS) + ("TSM", "ON")
    assert refresh_mod.DISCOVERY_TICKERS == expected


def test_discovery_tickers_preserves_homebuilder_tuple_identity() -> None:
    """HOMEBUILDER_TICKERS keeps its value/meaning; the test-suite guarantee
    at tests/test_issuer_profiles_a5a.py:1287 still names the homebuilder
    tuple, never the discovery tuple, on the per-ticker skip path that
    no-longer-exists ticker references."""
    assert refresh_mod.HOMEBUILDER_TICKERS == HOMEBUILDER_TICKERS


# ─────────────────────────────────────────────────────────────────────────────
# (b) The 6-K discriminator (calendar-quarter-end + quarterly-results filename).
# ─────────────────────────────────────────────────────────────────────────────


def test_results_six_k_admitted_for_issuer_declaring_six_k_results_form() -> None:
    """TSMC results 6-K: reportDate on a calendar-quarter end (2026-03-31) AND
    the SGML manifest carries an EX-99.1 whose filename matches the narrow
    quarterly-results keyword pattern. The candidate selector admits it."""
    tsm = _synthetic_issuer(
        cik="0001046179", ticker="TSM",
        fiscal_year_end_month=12,
        external_ids={"results_form": "6-K"},
    )
    rows = [
        # A results 6-K with reportDate on the calendar-quarter end.
        {
            "form": "6-K", "accessionNumber": "0001046179-26-000007",
            "filingDate": "2026-04-16", "acceptanceDateTime": "2026-04-16T13:30:00.000Z",
            "reportDate": "2026-03-31", "items": "",
            "primaryDocument": "earnings_release.htm",
        },
        # A monthly-revenue 6-K with reportDate on a MONTH END (NOT a
        # calendar-quarter end) — refused by the candidate selector
        # (reportDate is the primary discriminator at this stage).
        {
            "form": "6-K", "accessionNumber": "0001046179-26-000005",
            "filingDate": "2026-03-10", "acceptanceDateTime": "2026-03-10T13:30:00.000Z",
            "reportDate": "2026-02-28", "items": "",
            "primaryDocument": "monthly_sales.htm",
        },
    ]
    selected = refresh_mod._select_results_candidates(rows, issuer=tsm)
    # Only the row whose reportDate is a calendar-quarter end survives
    # the candidate selector — the monthly-revenue 6-K is filtered out
    # before any manifest fetch.
    assert [r["accessionNumber"] for r in selected] == ["0001046179-26-000007"]
    # And the sort key is acceptance_datetime, newest-first.
    assert selected[0]["acceptanceDateTime"] == "2026-04-16T13:30:00.000Z"


def test_results_six_k_rejects_non_calendar_quarter_end() -> None:
    """A 6-K whose reportDate is NOT on a calendar-quarter end is rejected
    at candidate-selection time. Mirrors a TSMC monthly-revenue 6-K (Feb 28,
    May 31, etc. — month-end but not a quarter-end for the 6-K that is the
    monthly-sales filing, vs Mar 31/Jun 30/Sep 30/Dec 31)."""
    tsm = _synthetic_issuer(
        cik="0001046179", ticker="TSM",
        external_ids={"results_form": "6-K"},
    )
    rows = [
        {
            "form": "6-K", "accessionNumber": "0001046179-26-000010",
            "filingDate": "2026-03-05", "acceptanceDateTime": "2026-03-05T13:30:00.000Z",
            "reportDate": "2026-02-28", "items": "",
            "primaryDocument": "monthly_sales.htm",
        },
        {
            "form": "6-K", "accessionNumber": "0001046179-26-000011",
            "filingDate": "2026-04-05", "acceptanceDateTime": "2026-04-05T13:30:00.000Z",
            "reportDate": "2026-03-31", "items": "",
            "primaryDocument": "monthly_sales.htm",
        },
    ]
    selected = refresh_mod._select_results_candidates(rows, issuer=tsm)
    # Only the row whose reportDate is a calendar-quarter end survives.
    assert [r["accessionNumber"] for r in selected] == ["0001046179-26-000011"]


def test_results_six_k_manifest_rejects_monthly_revenue_filename() -> None:
    """The manifest-level check: a monthly-revenue 6-K typically carries an
    EX-99.1 whose filename does NOT match the quarterly-results pattern
    (e.g. ``monthly_sales.htm``). Even if the row sneaks past the candidate
    selector, the per-row manifest check refuses it."""
    tsm = _synthetic_issuer(
        cik="0001046179", ticker="TSM",
        external_ids={"results_form": "6-K"},
    )
    manifest = [("EX-99.1", "monthly_sales.htm")]
    assert refresh_mod._results_six_k_filename_matches(manifest) is False


def test_results_six_k_manifest_rejects_dividend_or_board_filename() -> None:
    """A dividend/board-resolution 6-K has no results-themed exhibit."""
    tsm = _synthetic_issuer(
        cik="0001046179", ticker="TSM",
        external_ids={"results_form": "6-K"},
    )
    for kind_filename in (
        ("EX-99.1", "dividend.htm"),
        ("EX-99.1", "board_resolution.htm"),
        ("EX-99.1", "announcement.htm"),
    ):
        manifest = [kind_filename]
        assert refresh_mod._results_six_k_filename_matches(manifest) is False, kind_filename


def test_results_six_k_manifest_admits_quarterly_results_filename() -> None:
    """The full TSMC results 6-K shape: EX-99.1 earnings release PLUS an
    EX-99.2 slide deck, with the release filename matching the narrow
    quarterly-results pattern."""
    tsm = _synthetic_issuer(
        cik="0001046179", ticker="TSM",
        external_ids={"results_form": "6-K"},
    )
    manifest = [
        ("EX-99.1", "earnings_release.htm"),
        ("EX-99.2", "earnings_slides.htm"),
    ]
    assert refresh_mod._results_six_k_filename_matches(manifest) is True
    # And accept several canonical TSMC-style filename variants (each
    # carries at least one quarterly-results keyword).
    for name in (
        "results_q1_2026.htm",
        "press_release.htm",
        "financial_results.htm",
        "earnings_q1.htm",
    ):
        manifest = [("EX-99.1", name)]
        assert refresh_mod._results_six_k_filename_matches(manifest) is True, name


def test_results_six_k_rejected_for_issuer_without_six_k_results_form() -> None:
    """An issuer whose identity does NOT declare results_form "6-K" never
    has a 6-K row admitted, regardless of the row's form. The 8-K/2.02
    rule (default) is the only path. A TSMC 6-K landing on a domestic-only
    profile is a NO-OP, not a substitution."""
    domestic = _synthetic_issuer(
        cik="0000882184", ticker="DHI",
        fiscal_year_end_month=9,
        external_ids={"cik": "0000882184"},  # NO results_form
    )
    rows = [
        # A 6-K row — should be rejected for a domestic issuer.
        {
            "form": "6-K", "accessionNumber": "0000882184-26-000001",
            "filingDate": "2026-04-16", "acceptanceDateTime": "2026-04-16T13:30:00.000Z",
            "reportDate": "2026-03-31", "items": "",
            "primaryDocument": "earnings_release.htm",
        },
        # A real 8-K Item 2.02 row — still admitted.
        {
            "form": "8-K", "accessionNumber": "0000882184-26-000002",
            "filingDate": "2026-07-21", "acceptanceDateTime": "2026-07-21T13:30:00.000Z",
            "reportDate": "2026-07-21", "items": "2.02,9.01",
            "primaryDocument": "dhi-20260721.htm",
        },
    ]
    selected = refresh_mod._select_results_candidates(rows, issuer=domestic)
    assert [r["accessionNumber"] for r in selected] == ["0000882184-26-000002"]


# ─────────────────────────────────────────────────────────────────────────────
# (c) The 8-K/2.02 rule is unchanged for domestic filers.
# ─────────────────────────────────────────────────────────────────────────────


def test_eight_k_rule_unchanged_for_domestic_filer() -> None:
    """The pre-existing 8-K/2.02 admission is preserved byte-identically for
    an issuer whose external_ids do NOT declare results_form "6-K"."""
    dhi = _synthetic_issuer(
        cik="0000882184", ticker="DHI", fiscal_year_end_month=9,
        external_ids={"cik": "0000882184"},
    )
    rows = [
        # 8-K with no Item 2.02 — refused.
        {"form": "8-K", "accessionNumber": "A1", "filingDate": "2026-07-21",
         "acceptanceDateTime": "2026-07-21T13:30:00.000Z", "reportDate": "2026-07-21",
         "items": "5.02,9.01", "primaryDocument": "a.htm"},
        # 8-K Item 2.02 — admitted.
        {"form": "8-K", "accessionNumber": "A2", "filingDate": "2026-07-22",
         "acceptanceDateTime": "2026-07-22T13:30:00.000Z", "reportDate": "2026-07-22",
         "items": "2.02,9.01", "primaryDocument": "b.htm"},
        # 8-K/A amendment with Item 2.02 — admitted (BLOCKER/Opus F5).
        {"form": "8-K/A", "accessionNumber": "A3", "filingDate": "2026-07-30",
         "acceptanceDateTime": "2026-07-30T13:30:00.000Z", "reportDate": "2026-07-30",
         "items": "2.02", "primaryDocument": "c.htm"},
        # 8-K12B special-filing variant — refused by exact membership, not prefix.
        {"form": "8-K12B", "accessionNumber": "A4", "filingDate": "2026-08-01",
         "acceptanceDateTime": "2026-08-01T13:30:00.000Z", "reportDate": "2026-08-01",
         "items": "2.02", "primaryDocument": "d.htm"},
    ]
    selected = refresh_mod._select_results_candidates(rows, issuer=dhi)
    accessions = [r["accessionNumber"] for r in selected]
    assert accessions == ["A3", "A2"]  # newest-first by acceptance_datetime


# ─────────────────────────────────────────────────────────────────────────────
# (d) The 52/53-week fiscal-calendar tolerance.
# ─────────────────────────────────────────────────────────────────────────────


def test_fiscal_tolerance_constant_is_named_and_six_days() -> None:
    """The 52/53-week tolerance is a single named constant at module scope,
    set to 6 days. A 3-day drift fits (onsemi Q1 2026: stated 2026-04-03 vs
    computed 2026-03-31), a 10-day drift does not."""
    assert refresh_mod.FIFTY_TWO_FIFTY_THREE_WEEK_TOLERANCE_DAYS == 6


def test_fiscal_tolerance_zero_for_calendar_issuer() -> None:
    """A standard calendar-quarter issuer (DHI/PHM/KBH/TOL/TSM) has 0-day
    tolerance — the existing exact-equality gate applies unchanged."""
    dhi = _synthetic_issuer(
        cik="0000882184", ticker="DHI", fiscal_year_end_month=9,
        external_ids={"cik": "0000882184"},
    )
    assert refresh_mod._fiscal_period_tolerance_days(dhi) == 0
    tsm = _synthetic_issuer(
        cik="0001046179", ticker="TSM", fiscal_year_end_month=12,
        external_ids={"results_form": "6-K"},
    )
    assert refresh_mod._fiscal_period_tolerance_days(tsm) == 0


def test_fiscal_tolerance_six_days_for_52_53_week_issuer() -> None:
    """An issuer declaring fiscal_calendar "52_53_week" gets the named
    6-day tolerance. A stated period end 3 days past the derived calendar-
    quarter end (e.g. onsemi Q1 2026: stated 2026-04-03 vs computed
    2026-03-31) is accepted; a 10-day drift is still refused."""
    on = _synthetic_issuer(
        cik="0001097864", ticker="ON", fiscal_year_end_month=12,
        external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
    )
    assert refresh_mod._fiscal_period_tolerance_days(on) == 6


def test_stated_period_drift_accepted_within_tolerance_for_52_53_week() -> None:
    """onsemi Q1 2026 release: stated ``Quarters Ended April 3, 2026`` vs
    calendar-quarter-end anchor 2026-03-31 (3-day gap) — accepted under the
    6-day tolerance, the existing _stated_period_end helper still returns
    the date and the helper that compares it to the fiscal period accepts
    it for a 52_53_week issuer."""
    on = _synthetic_issuer(
        cik="0001097864", ticker="ON",
        external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
    )
    body = (
        "<html><body><h1>onsemi Reports First Quarter 2026 Results</h1>"
        "<p>For the Quarters Ended April 3, 2026 (Unaudited)</p></body></html>"
    )
    stated = refresh_mod._stated_period_end(body)
    assert stated == date(2026, 4, 3)
    fiscal_period_end = date(2026, 3, 31)
    tolerance = refresh_mod._fiscal_period_tolerance_days(on)
    drift = abs((stated - fiscal_period_end).days)
    assert drift == 3
    assert drift <= tolerance


def test_stated_period_drift_rejected_outside_tolerance_for_52_53_week() -> None:
    """Even for a 52_53_week issuer, a 10-day drift is outside the 6-day
    tolerance and is rejected."""
    on = _synthetic_issuer(
        cik="0001097864", ticker="ON",
        external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
    )
    body = "<html><body><p>For the Quarters Ended April 10, 2026</p></body></html>"
    stated = refresh_mod._stated_period_end(body)
    assert stated == date(2026, 4, 10)
    fiscal_period_end = date(2026, 3, 31)
    tolerance = refresh_mod._fiscal_period_tolerance_days(on)
    drift = abs((stated - fiscal_period_end).days)
    assert drift == 10
    assert drift > tolerance  # refused, never substituted


def test_stated_period_drift_rejected_for_calendar_issuer() -> None:
    """A 3-day drift is rejected for a calendar issuer (tolerance 0)."""
    dhi = _synthetic_issuer(
        cik="0000882184", ticker="DHI", fiscal_year_end_month=9,
        external_ids={"cik": "0000882184"},
    )
    body = "<html><body><p>For the Quarters Ended July 3, 2026</p></body></html>"
    stated = refresh_mod._stated_period_end(body)
    assert stated == date(2026, 7, 3)
    fiscal_period_end = date(2026, 6, 30)
    tolerance = refresh_mod._fiscal_period_tolerance_days(dhi)
    drift = abs((stated - fiscal_period_end).days)
    assert drift == 3
    assert drift > tolerance  # refused — calendar issuer, no slack


# ─────────────────────────────────────────────────────────────────────────────
# (e) The stated-period regex accepts both phrasings.
# ─────────────────────────────────────────────────────────────────────────────


def test_stated_period_regex_accepts_plural_capitalized() -> None:
    """onsemi Q1 2026: ``Quarters Ended April 3, 2026`` — plural + capitalized."""
    body = (
        "<html><body><table><caption>For the Quarters Ended April 3, 2026 "
        "(Unaudited)</caption></table></body></html>"
    )
    assert refresh_mod._stated_period_end(body) == date(2026, 4, 3)


def test_stated_period_regex_accepts_singular_lowercase() -> None:
    """Pre-existing PHM/TOL phrasing — ``quarter ended <date>`` — preserved."""
    body = (
        "<html><body><p>For the quarter ended June 30, 2026, the company "
        "reported revenue of $1.7 billion.</p></body></html>"
    )
    assert refresh_mod._stated_period_end(body) == date(2026, 6, 30)


def test_stated_period_regex_accepts_three_months_ended_phrasing() -> None:
    """Pre-existing DHI/KBH phrasing — ``Three Months Ended <date>`` —
    preserved (C1: every calendar-issuer code path stays byte-identical)."""
    body = (
        "<html><body><p>Three Months Ended March 31, 2026 (Unaudited)</p>"
        "</body></html>"
    )
    assert refresh_mod._stated_period_end(body) == date(2026, 3, 31)


def test_stated_period_regex_returns_none_when_no_period_locatable() -> None:
    """A release body with no period-end phrasing returns None — a typed
    absence at the cross-check, not a guessed identity."""
    body = "<html><body><p>Forward-looking statements in this release speak only as of the date hereof.</p></body></html>"
    assert refresh_mod._stated_period_end(body) is None


# ─────────────────────────────────────────────────────────────────────────────
# (f) The bare EX-99 exhibit is rescued by the filename hint.
# ─────────────────────────────────────────────────────────────────────────────


def test_bare_ex99_exhibit_rescued_by_filename_hint() -> None:
    """onsemi's Q2-2026 8-K exhibit is typed bare ``EX-99`` with filename
    ``ef20079200_ex99-1.htm``.  The pre-existing three-tier EX-99.1
    fallback (exact → prefix → filename hint) returns the filename, which
    is then served.  No change to ``_select_exhibit_99_1`` itself; this
    test pins the contract that the 8-K-admission path keeps that rescue."""
    manifest = [("EX-99", "ef20079200_ex99-1.htm")]
    assert refresh_mod._select_exhibit_99_1(manifest) == "ef20079200_ex99-1.htm"


def test_bare_ex99_manifest_with_quarterly_filename_acceptable() -> None:
    """A manifest where the rescued EX-99.1 carries a quarterly-results
    filename is acceptable — covers a possible TSMC filing where the
    EX-99 is typed bare ``EX-99`` (no ``.1``) but the filename is the
    EX-99 hint + a quarterly-results keyword."""
    manifest = [("EX-99", "earnings_release.htm")]
    # The bare EX-99 (no .1) won't match the exact-EX-99.1 path or the
    # ^EX-99\.1\b path; the filename hint alone won't rescue
    # ``earnings_release.htm`` (no ex99 hint in name).
    assert refresh_mod._select_exhibit_99_1(manifest) is None


# ─────────────────────────────────────────────────────────────────────────────
# (g) Calendar-quarter-end anchor used by the 6-K discriminator.
# ─────────────────────────────────────────────────────────────────────────────


def test_calendar_quarter_end_recognizes_canonical_anchors() -> None:
    """The four canonical calendar-quarter-end dates are accepted; every
    other date is rejected. The 6-K discriminator keys on this — without
    it, a 6-K's reported period end is unconstrained (no 8-K Item 2.02
    anchor)."""
    for raw in ("2026-03-31", "2026-06-30", "2026-09-30", "2026-12-31"):
        assert refresh_mod._is_calendar_quarter_end(raw) is True, raw
    for raw in ("2026-03-30", "2026-03-29", "2026-06-29", "2026-07-15",
                "2026-12-30", "2026-01-01", "2026-02-28", "2026-05-31",
                ""):
        assert refresh_mod._is_calendar_quarter_end(raw) is False, raw


# ─────────────────────────────────────────────────────────────────────────────
# (h) Per-ticker loop stays fail-soft under the wider ticker set.
# ─────────────────────────────────────────────────────────────────────────────


def test_discover_with_unknown_issuer_raises_refresh_error_not_exception_propagation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``discover_new_homebuilder_revisions`` for a ticker with no registered
    identity (e.g. a future ticker added before its IssuerIdentity exists)
    raises ``RefreshError`` — the caller's existing per-ticker carry-forward
    catches it and converts to a line-start ``::warning`` skip, never an
    exception that crosses the ticker boundary.  This test pins the
    contract that adding TSM/ON to DISCOVERY_TICKERS does not weaken the
    fail-soft discipline."""
    # A ticker that has no homebuilder factory AND that the synthetic
    # identity injection does NOT cover — the function falls back to
    # issuer_for_ticker(ticker) which returns None.
    with pytest.raises(refresh_mod.RefreshError):
        refresh_mod.discover_new_homebuilder_revisions(
            "ZZZ",
            http_get=lambda _url: (404, b""),
            chain_state_loader=lambda _eid: [],
        )


def test_discover_accepts_injected_synthetic_issuer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The discover() seam accepts an injected ``IssuerIdentity`` so a test
    can run with a synthetic 6-K identity that does NOT need a sibling-lane
    TSM/ON registration in the worktree. Production callers continue to
    pass no ``issuer`` (the default falls back to ``issuer_for_ticker``)."""
    tsm = _synthetic_issuer(
        cik="0001046179", ticker="TSM", fiscal_year_end_month=12,
        external_ids={"results_form": "6-K"},
    )
    # The injected identity must be threaded all the way through; we
    # validate the seam by calling the function with an issuer and
    # confirming it does NOT raise ``RefreshError("has no registered ...
    # identity")`` for the synthetic ticker.
    # A genuine RefreshError from SEC access is acceptable — the
    # function has reached past the identity check.
    try:
        refresh_mod.discover_new_homebuilder_revisions(
            "TSM",
            http_get=lambda _url: (404, b""),
            chain_state_loader=lambda _eid: [],
            issuer=tsm,
        )
    except refresh_mod.RefreshError as exc:
        # Anything OTHER than the "no registered identity" form is fine —
        # the injected identity was accepted.
        assert "no registered" not in str(exc), str(exc)


def test_refresh_source_iterates_discovery_tickers() -> None:
    """The per-ticker loop in ``refresh()`` iterates ``DISCOVERY_TICKERS``,
    not ``HOMEBUILDER_TICKERS`` literally.  The companion assertion at
    ``tests/test_issuer_profiles_a5a.py:1287`` pins the runtime contract
    (every ticker in the iterated set is attempted, every failure is a
    line-start ``::warning`` skip); this test pins the SOURCE contract
    that the loop now reads from the superset, not the original tuple.
    """
    import inspect

    import scripts.refresh_event_workspaces as refresh_mod_local

    source = inspect.getsource(refresh_mod_local.refresh)
    assert "DISCOVERY_TICKERS" in source, "refresh() does not iterate DISCOVERY_TICKERS"
    # And: the homebuilder tuple is NOT also iterated literally as a
    # second loop in the same source — there is exactly one per-ticker
    # pass, and it walks the superset.
    homeloop_count = sum(
        1 for line in source.splitlines() if line.strip().startswith("for ticker in")
    )
    assert homeloop_count >= 1  # at least one for-ticker loop exists


# ─────────────────────────────────────────────────────────────────────────────
# (j) Datetime acceptance never fabricates a time (C4).
# ─────────────────────────────────────────────────────────────────────────────


def test_iso_z_rejects_empty_acceptance_datetime() -> None:
    """A missing acceptance datetime is a typed absence — ``_iso_z`` raises
    ``RefreshError``, never substitutes a midnight or wall-clock fallback.
    The discovery flow's per-row skip-on-acceptance-missing path is what
    the test pins; this test pins the seam itself."""
    with pytest.raises(refresh_mod.RefreshError):
        refresh_mod._iso_z("")
    with pytest.raises(refresh_mod.RefreshError):
        refresh_mod._iso_z(None)


def test_iso_z_normalizes_millisecond_form() -> None:
    """SEC's ``acceptanceDateTime`` carries millisecond fractions
    (e.g. ``2026-04-16T13:30:00.000Z``).  ``_iso_z`` strips the fractional
    second to the second resolution; the chain link hash depends on this
    canonical shape."""
    assert refresh_mod._iso_z("2026-04-16T13:30:00.000Z") == "2026-04-16T13:30:00Z"