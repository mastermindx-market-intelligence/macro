"""T05b — Semiconductor earnings intake generalization (identity-declared only).

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001.

Code-under-test: :mod:`scripts.refresh_event_workspaces`.  Verifies that:
  - ``DISCOVERY_TICKERS`` is exactly ``(*HOMEBUILDER_TICKERS, "TSM", "ON")``
    (the homebuilder tuple's value/meaning is preserved — see C1).
  - A results 6-K is admitted ONLY for an issuer whose identity declares
    ``external_ids["results_form"] == "6-K"`` (TSMC-style), via a narrow
    discriminator: a calendar-quarter-end reportDate PRE-FILTER (necessary,
    never sufficient — the quarter-closing month's monthly-revenue 6-K also
    reports a quarter-end date) plus the manifest discriminator on the
    EX-99.1 exhibit's SGML <DESCRIPTION> or filename. The fiscal period of a
    6-K is anchored on its filing date (its reportDate IS the period end).
  - Missing profile = REFUSED (fail closed), never Apple's span readers.
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

import json
from datetime import date
from typing import Mapping

import pytest

from engine.company_intelligence.event_workspace import apple_issuer
from engine.company_intelligence.identity import (
    IssuerIdentity,
    IssuerRegistry,
    ListingAlias,
    company_id_for_cik,
)
from engine.company_intelligence.issuer_profiles import HOMEBUILDER_TICKERS, IssuerProfile

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


def test_discovery_tickers_preserves_homebuilder_tuple_identity() -> None:  # noqa: D401
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

# ─────────────────────────────────────────────────────────────────────────────
# (k) The results-6-K MANIFEST discriminator — description OR filename, text
#     exhibits only, never reportDate, never a body.  Shapes mirror the real
#     filer's document map (types + description phrasing) with invented
#     filenames; no real manifest or body is committed.
# ─────────────────────────────────────────────────────────────────────────────


def _sgml(docs: list[tuple[str, str, str | None]]) -> str:
    body = ""
    for kind, name, desc in docs:
        body += f"&lt;DOCUMENT&gt;\n&lt;TYPE&gt;{kind}\n"
        if desc is not None:
            body += f"&lt;DESCRIPTION&gt;{desc}\n"
        body += f"&lt;FILENAME&gt;{name}\n&lt;/DOCUMENT&gt;\n"
    return f"<HTML><BODY><PRE>{body}</PRE></BODY></HTML>"


RESULTS_6K_SHAPE = [
    ("6-K", "fpi-20260716x6k.htm", "6-K"),
    ("EX-99.1", "a2q26e_withguidance.htm", "Earnings report with guidance"),
    ("EX-99.2", "a2q26presentation.htm", "Quarterly management report slides"),
]
MONTHLY_REVENUE_6K_SHAPE = [("6-K", "fpi-revenue20260713.htm", "6-K")]          # no EX-99 at all
MONTHLY_REVENUE_WITH_EXHIBIT_SHAPE = [
    ("6-K", "fpi-20260710x6k.htm", "6-K"),
    ("EX-99.1", "june_revenue.htm", "Monthly revenue report"),
]
DIVIDEND_6K_SHAPE = [("6-K", "fpi-20260605x6k.htm", "6-K"), ("EX-99.1", "notice.htm", "Dividend announcement")]
BOARD_6K_SHAPE = [("6-K", "fpi-20260605x6k.htm", "6-K"), ("EX-99.1", "resolutions.htm", "Board of directors resolutions")]


def test_manifest_parser_keeps_description_and_legacy_tuple_form_is_unchanged() -> None:
    entries = refresh_mod._parse_sgml_manifest_entries(_sgml(RESULTS_6K_SHAPE))
    assert entries[1] == {"type": "EX-99.1", "filename": "a2q26e_withguidance.htm",
                          "description": "Earnings report with guidance"}
    assert refresh_mod._parse_sgml_manifest(_sgml(RESULTS_6K_SHAPE)) == [
        ("6-K", "fpi-20260716x6k.htm"), ("EX-99.1", "a2q26e_withguidance.htm"),
        ("EX-99.2", "a2q26presentation.htm"),
    ]
    # a document without DESCRIPTION parses with an empty description
    assert refresh_mod._parse_sgml_manifest_entries(_sgml([("EX-99.1", "x.htm", None)]))[0]["description"] == ""


def test_results_six_k_manifest_admits_the_real_filer_shape_by_description_and_by_filename() -> None:
    admits = refresh_mod._results_six_k_manifest_admits
    assert admits(refresh_mod._parse_sgml_manifest_entries(_sgml(RESULTS_6K_SHAPE))) is True
    # description alone (opaque filename)
    assert admits([{"type": "EX-99.1", "filename": "ex991.htm", "description": "Earnings report with guidance"}]) is True
    assert admits([{"type": "EX-99.1", "filename": "ex991.htm", "description": "Quarterly Results for the second quarter"}]) is True
    # filename alone (no description): the a<q>q<yy>e… convention, or an earnings keyword
    assert admits([{"type": "EX-99.1", "filename": "a2q26e_withguidance.htm", "description": ""}]) is True
    assert admits([{"type": "EX-99.1", "filename": "earnings_release.htm", "description": ""}]) is True
    # bare EX-99 rescued by the ex99-1 filename hint, described as an earnings release
    assert admits([{"type": "EX-99", "filename": "ef20079200_ex99-1.htm", "description": "Earnings release"}]) is True


def test_results_six_k_manifest_refuses_revenue_reports_announcements_and_non_text() -> None:
    admits = refresh_mod._results_six_k_manifest_admits
    parse = refresh_mod._parse_sgml_manifest_entries
    assert admits(parse(_sgml(MONTHLY_REVENUE_6K_SHAPE))) is False            # no EX-99 document
    assert admits(parse(_sgml(MONTHLY_REVENUE_WITH_EXHIBIT_SHAPE))) is False   # "revenue" never admits
    assert admits(parse(_sgml(DIVIDEND_6K_SHAPE))) is False
    assert admits(parse(_sgml(BOARD_6K_SHAPE))) is False
    # results-described but not an EX-99.1 exhibit (e.g. the slide deck) never admits
    assert admits([{"type": "EX-99.2", "filename": "slides.htm", "description": "Earnings presentation"}]) is False
    # an EX-99.1 that is not a text document never admits
    assert admits([{"type": "EX-99.1", "filename": "a2q26e_withguidance.pdf", "description": "Earnings report"}]) is False
    assert admits([]) is False


def test_quarter_end_report_date_is_a_prefilter_not_the_discriminator() -> None:
    """The quarter-closing month's monthly-revenue 6-K reports a quarter-end
    date too, so the candidate selector keeps it — and the manifest
    discriminator is what refuses it."""
    tsm = _synthetic_issuer(cik="0001046179", ticker="TSM", external_ids={"results_form": "6-K"})
    rows = [
        {"form": "6-K", "accessionNumber": "0001046179-26-000447", "filingDate": "2026-07-13",
         "acceptanceDateTime": "2026-07-13T12:00:00.000Z", "reportDate": "2026-06-30", "items": "",
         "primaryDocument": "fpi-revenue20260713.htm"},
        {"form": "6-K", "accessionNumber": "0001046179-26-000440", "filingDate": "2026-06-10",
         "acceptanceDateTime": "2026-06-10T12:00:00.000Z", "reportDate": "2026-05-31", "items": "",
         "primaryDocument": "fpi-revenue20260610.htm"},
    ]
    selected = refresh_mod._select_results_candidates(rows, issuer=tsm)
    assert [r["accessionNumber"] for r in selected] == ["0001046179-26-000447"]  # pre-filter keeps the June one
    assert refresh_mod._results_six_k_manifest_admits(
        refresh_mod._parse_sgml_manifest_entries(_sgml(MONTHLY_REVENUE_6K_SHAPE))) is False


def test_bare_ex99_is_selected_only_as_the_sole_text_exhibit_of_a_results_8k() -> None:
    """A bare ``EX-99`` (no ``.1``) reaches this selector only for an 8-K row that
    already passed the Item 2.02 (results of operations) admission, so a SOLE
    bare EX-99 text exhibit is that filing's results release (onsemi's Q2-2026
    8-K 0001140361-26-030989 is typed exactly so). The rescue stays narrow:
    two bare exhibits, a non-text exhibit or an unnumbered EX-99.2 are refused."""
    select = refresh_mod._select_exhibit_99_1
    assert select([("EX-99", "attachment.htm")]) == "attachment.htm"
    assert select([("EX-99", "a.htm"), ("EX-99", "b.htm")]) is None
    assert select([("EX-99", "attachment.pdf")]) is None
    assert select([("EX-99.2", "presentation.htm")]) is None


# ─────────────────────────────────────────────────────────────────────────────
# (l) END-TO-END wiring through discover_new_homebuilder_revisions: fake
#     EDGAR (submissions JSON + SGML header + exhibit body), injected identity
#     + profile, no network, no real bodies.  These are the tests a wrong
#     implementation cannot pass: an unused discriminator, an unconditional
#     tolerance, a fail-open profile, or a wrong 6-K period anchor all fail.
# ─────────────────────────────────────────────────────────────────────────────


def _null_profile(ticker: str) -> IssuerProfile:
    return IssuerProfile(
        ticker=ticker,
        extract_release_facts=lambda **_kwargs: [],
        extract_transcript_claims=lambda **_kwargs: [],
        extract_guidance=lambda **_kwargs: [],
    )


def _exhibit(period_phrase: str) -> str:
    return (
        "<html><body><p>Synthetic Foundry Co. reports results for the "
        f"{period_phrase}. Net revenue was NT$1,234,567 million; every figure "
        "here is invented.</p></body></html>"
    )


def _run_discovery(monkeypatch, *, ticker, issuer, profile, rows, headers, exhibits):
    cik = issuer.cik
    cik_int = int(cik)
    cols = ("accessionNumber", "filingDate", "acceptanceDateTime", "reportDate", "form", "primaryDocument", "items")
    submissions = {"cik": cik, "filings": {"recent": {c: [r[c] for r in rows] for c in cols}}}

    def http_get(url: str) -> tuple[int, bytes]:
        if url == f"https://data.sec.gov/submissions/CIK{cik}.json":
            return 200, json.dumps(submissions).encode("utf-8")
        for acc, html in headers.items():
            base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc.replace('-', '')}"
            if url == f"{base}/{acc}-index-headers.html":
                return 200, html.encode("utf-8")
            for name, body in exhibits.get(acc, {}).items():
                if url == f"{base}/{name}":
                    return 200, body.encode("utf-8")
        return 404, b""

    def fetch_index(_base: str) -> dict:
        return {"schema": "mastermind.tx-index/v1", "symbols": {}, "revisions": {}, "dates": {},
                "body_count": 0, "symbol_count": 0, "generated_at": "2026-01-01T00:00:00Z"}

    def fetch_body(_base: str, _ref):  # pragma: no cover
        raise AssertionError("no transcript may be fetched")

    monkeypatch.setattr(refresh_mod, "production_registry", lambda: IssuerRegistry([apple_issuer(), issuer]))
    monkeypatch.setattr(refresh_mod.time, "sleep", lambda _s: None)
    return refresh_mod.discover_new_homebuilder_revisions(
        ticker, http_get=http_get, fetch_index=fetch_index, fetch_body_fn=fetch_body,
        chain_state_loader=lambda _event_id: [], issuer=issuer, profile=profile,
        today=date(2026, 9, 24),
    )


_RESULTS_ROW = {
    "form": "6-K", "accessionNumber": "0009990001-26-000451", "filingDate": "2026-07-16",
    "acceptanceDateTime": "2026-07-16T11:45:43.000Z", "reportDate": "2026-06-30", "items": "",
    "primaryDocument": "fpi-20260716x6k.htm",
}
_REVENUE_ROW = {
    "form": "6-K", "accessionNumber": "0009990001-26-000447", "filingDate": "2026-07-13",
    "acceptanceDateTime": "2026-07-13T12:00:00.000Z", "reportDate": "2026-06-30", "items": "",
    "primaryDocument": "fpi-revenue20260713.htm",
}
_REVENUE_WITH_EXHIBIT_ROW = {
    "form": "6-K", "accessionNumber": "0009990001-26-000440", "filingDate": "2026-04-10",
    "acceptanceDateTime": "2026-04-10T12:00:00.000Z", "reportDate": "2026-03-31", "items": "",
    "primaryDocument": "fpi-20260410x6k.htm",
}


def test_end_to_end_results_six_k_is_admitted_and_built_with_form_six_k(monkeypatch, capsys) -> None:
    fpi = _synthetic_issuer(cik="0009990001", ticker="FPI", external_ids={"results_form": "6-K"})
    revisions = _run_discovery(
        monkeypatch, ticker="FPI", issuer=fpi, profile=_null_profile("FPI"),
        rows=[_RESULTS_ROW, _REVENUE_ROW, _REVENUE_WITH_EXHIBIT_ROW],
        headers={
            _RESULTS_ROW["accessionNumber"]: _sgml(RESULTS_6K_SHAPE),
            _REVENUE_ROW["accessionNumber"]: _sgml(MONTHLY_REVENUE_6K_SHAPE),
            _REVENUE_WITH_EXHIBIT_ROW["accessionNumber"]: _sgml(MONTHLY_REVENUE_WITH_EXHIBIT_SHAPE),
        },
        exhibits={
            _RESULTS_ROW["accessionNumber"]: {"a2q26e_withguidance.htm": _exhibit("quarter ended June 30, 2026")},
            _REVENUE_WITH_EXHIBIT_ROW["accessionNumber"]: {"june_revenue.htm": _exhibit("quarter ended March 31, 2026")},
        },
    )
    assert len(revisions) == 1
    event_id, payload = revisions[0]
    assert payload["event_id"] == event_id
    assert "2026q2" in event_id                                  # anchored on the FILING date -> Q2, not Q1
    source = payload["sources"][0]
    assert source["form"] == "6-K"
    assert _RESULTS_ROW["accessionNumber"] in json.dumps(source)   # the admitted filing, whatever the key spelling
    assert _REVENUE_ROW["accessionNumber"] not in json.dumps(payload)
    assert _REVENUE_WITH_EXHIBIT_ROW["accessionNumber"] not in json.dumps(payload)
    out = capsys.readouterr().out
    # the quarter-end monthly-revenue 6-K (no EX-99) is skipped on the pre-existing path …
    assert "no usable EX-99.1 exhibit" in out
    # … and the revenue-described EX-99.1 is refused by the DISCRIMINATOR, with its own warning
    assert "6-K manifest refused by the results discriminator" in out
    assert _REVENUE_WITH_EXHIBIT_ROW["accessionNumber"] in out


def test_end_to_end_six_k_row_is_never_admitted_for_an_issuer_without_six_k_results_form(monkeypatch) -> None:
    """Identity law: the SAME rows for an 8-K issuer yield nothing — the
    8-K/2.02 rule is the only admission path there."""
    dom = _synthetic_issuer(cik="0009990001", ticker="FPI", external_ids={"results_form": "8-K"})
    revisions = _run_discovery(
        monkeypatch, ticker="FPI", issuer=dom, profile=_null_profile("FPI"),
        rows=[_RESULTS_ROW], headers={_RESULTS_ROW["accessionNumber"]: _sgml(RESULTS_6K_SHAPE)},
        exhibits={_RESULTS_ROW["accessionNumber"]: {"a2q26e_withguidance.htm": _exhibit("quarter ended June 30, 2026")}},
    )
    assert revisions == []


_ON_LIKE_ROW = {
    "form": "8-K", "accessionNumber": "0009990002-26-018868", "filingDate": "2026-05-04",
    "acceptanceDateTime": "2026-05-04T20:10:34.000Z", "reportDate": "2026-05-04", "items": "2.02,9.01",
    "primaryDocument": "dom-8k.htm",
}
_ON_LIKE_SGML = _sgml([("8-K", "dom-8k.htm", "8-K"), ("EX-99", "ef20072220_ex99-1.htm", "Press release")])


def _run_52_53(monkeypatch, *, external_ids, period_phrase):
    issuer = _synthetic_issuer(cik="0009990002", ticker="DOM", external_ids=external_ids)
    return _run_discovery(
        monkeypatch, ticker="DOM", issuer=issuer, profile=_null_profile("DOM"),
        rows=[_ON_LIKE_ROW], headers={_ON_LIKE_ROW["accessionNumber"]: _ON_LIKE_SGML},
        exhibits={_ON_LIKE_ROW["accessionNumber"]: {"ef20072220_ex99-1.htm": _exhibit(period_phrase)}},
    )


def test_end_to_end_52_53_week_tolerance_is_applied_only_for_the_declaring_issuer(monkeypatch, capsys) -> None:
    # derived quarter end for a 2026-05-04 press release, FYE Dec: 2026-03-31; stated April 3 -> 3-day drift
    admitted = _run_52_53(monkeypatch, external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
                          period_phrase="Quarters Ended April 3, 2026")
    assert len(admitted) == 1 and "2026q1" in admitted[0][0]
    assert admitted[0][1]["sources"][0]["form"] == "8-K"
    # within tolerance the EVENT carries the issuer's STATED period end, not the derived calendar end
    assert admitted[0][1]["fiscal_period"] == {"year": 2026, "quarter": 1, "calendar_end": "2026-04-03"}

    calendar_issuer = _run_52_53(monkeypatch, external_ids={"results_form": "8-K"},
                                 period_phrase="Quarters Ended April 3, 2026")
    assert calendar_issuer == []
    assert "drift=3d, tolerance=0d" in capsys.readouterr().out

    too_far = _run_52_53(monkeypatch, external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
                         period_phrase="Quarters Ended April 10, 2026")
    assert too_far == []
    assert "drift=10d, tolerance=6d" in capsys.readouterr().out


def test_end_to_end_all_caps_quarters_ended_header_locates_the_period(monkeypatch) -> None:
    admitted = _run_52_53(monkeypatch, external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
                          period_phrase="QUARTERS ENDED APRIL 3, 2026")
    assert len(admitted) == 1


def test_discover_refuses_an_identity_without_its_own_profile_fail_closed() -> None:
    """An injected identity whose ticker has no registered profile is REFUSED
    with RefreshError — never built through Apple's default span readers."""
    zzz = _synthetic_issuer(cik="0009990003", ticker="ZZZ", external_ids={"results_form": "6-K"})
    with pytest.raises(refresh_mod.RefreshError, match="identity/profile"):
        refresh_mod.discover_new_homebuilder_revisions(
            "ZZZ", http_get=lambda _url: (404, b""), chain_state_loader=lambda _eid: [], issuer=zzz,
        )


def test_refresh_source_names_discovery_tickers_not_the_homebuilder_tuple() -> None:
    """Static pin only: ``refresh()`` references DISCOVERY_TICKERS and no longer
    references HOMEBUILDER_TICKERS. The RUNTIME property (every ticker in the
    superset is attempted and every failure is a ::warning skip) is pinned by
    tests/test_issuer_profiles_a5a.py::test_refresh_is_fail_soft_per_homebuilder,
    which runs a real refresh() and asserts the skipped set equals
    DISCOVERY_TICKERS."""
    names = refresh_mod.refresh.__code__.co_names
    assert "DISCOVERY_TICKERS" in names and "HOMEBUILDER_TICKERS" not in names


def test_press_release_described_exhibits_never_admit_on_their_own() -> None:
    """'Press release' is the commonest EX-99.1 description on EDGAR and names
    revenue reports and dividend notices as often as results; it must not be
    a results token by itself."""
    admits = refresh_mod._results_six_k_manifest_admits
    assert admits([{"type": "EX-99.1", "filename": "june_revenue.htm", "description": "Press Release"}]) is False
    assert admits([{"type": "EX-99.1", "filename": "dividend_announcement.htm", "description": "Press release"}]) is False
    assert admits([{"type": "EX-99.1", "filename": "press_release.htm", "description": ""}]) is False
    # the verified filer shape still admits twice over: by description and by filename convention
    assert admits([{"type": "EX-99.1", "filename": "ex991.htm", "description": "Earnings report with guidance"}]) is True
    assert admits([{"type": "EX-99.1", "filename": "a2q26e_withguidance.htm", "description": "Press release"}]) is True


def test_numbered_ex99_1_keeps_precedence_over_a_bare_ex99() -> None:
    select = refresh_mod._select_exhibit_99_1
    assert select([("8-K", "form8k.htm"), ("EX-99", "bare.htm"), ("EX-99.1", "release.htm")]) == "release.htm"
    assert select([("8-K", "form8k.htm"), ("EX-99", "ex99.htm")]) == "ex99.htm"


# ── 52/53-week: multi-quarter headers name the period among several dates (real onsemi Q2-2026 shape) ──

ON_Q2_FCF_HEADER = "Quarters Ended October 3, 2025 December 31, 2025 April 3, 2026 July 3, 2026"


def _q2_exhibit(header: str) -> str:
    return (
        "<html><body><p>Synthetic Semiconductor Co. reports results.</p>"
        f"<table><tr><td>FREE CASH FLOW</td></tr><tr><td>{header}</td></tr></table>"
        "<p>Every figure here is invented.</p></body></html>"
    )


_ON_LIKE_Q2_ROW = {
    "form": "8-K", "accessionNumber": "0009990002-26-000777", "filingDate": "2026-08-03",
    "acceptanceDateTime": "2026-08-03T20:54:23.000Z", "reportDate": "2026-08-03", "items": "2.02,9.01",
    "primaryDocument": "dom-8k.htm",
}


def _run_52_53_q2(monkeypatch, *, external_ids, body):
    issuer = _synthetic_issuer(cik="0009990002", ticker="DOM", external_ids=external_ids)
    return _run_discovery(
        monkeypatch, ticker="DOM", issuer=issuer, profile=_null_profile("DOM"),
        rows=[_ON_LIKE_Q2_ROW], headers={_ON_LIKE_Q2_ROW["accessionNumber"]: _ON_LIKE_SGML},
        exhibits={_ON_LIKE_Q2_ROW["accessionNumber"]: {"ef20072220_ex99-1.htm": body}},
    )


def test_stated_period_end_candidates_collects_every_date_under_one_header() -> None:
    body = _q2_exhibit(ON_Q2_FCF_HEADER)
    assert refresh_mod._stated_period_end(body) == date(2025, 10, 3)              # first-match rule, unchanged
    assert refresh_mod._stated_period_end_candidates(body) == [
        date(2025, 10, 3), date(2025, 12, 31), date(2026, 4, 3), date(2026, 7, 3)]
    assert refresh_mod._stated_period_end_candidates("<p>no period phrase</p>") == []


def test_end_to_end_52_53_week_issuer_is_admitted_on_the_unique_in_tolerance_date(monkeypatch, capsys) -> None:
    # derived quarter end for a 2026-08-03 release, FYE Dec: 2026-06-30; the header's first date is 270 days off
    admitted = _run_52_53_q2(monkeypatch, external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
                             body=_q2_exhibit(ON_Q2_FCF_HEADER))
    assert len(admitted) == 1 and "2026q2" in admitted[0][0]
    assert admitted[0][1]["fiscal_period"] == {"year": 2026, "quarter": 2, "calendar_end": "2026-07-03"}
    assert "stated period end 2026-07-03 in place of the derived calendar quarter end 2026-06-30" in capsys.readouterr().out


def test_end_to_end_calendar_issuer_keeps_first_match_semantics_on_the_same_header(monkeypatch, capsys) -> None:
    refused = _run_52_53_q2(monkeypatch, external_ids={"results_form": "8-K"}, body=_q2_exhibit(ON_Q2_FCF_HEADER))
    assert refused == []
    assert "drift=270d, tolerance=0d" in capsys.readouterr().out


def test_end_to_end_52_53_week_issuer_refuses_two_in_tolerance_dates_as_ambiguous(monkeypatch, capsys) -> None:
    ambiguous = _run_52_53_q2(monkeypatch, external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
                              body=_q2_exhibit("Quarters Ended October 3, 2025 June 30, 2026 July 3, 2026"))
    assert ambiguous == []
    assert "drift=270d, tolerance=6d" in capsys.readouterr().out


def test_end_to_end_52_53_week_issuer_still_refuses_when_no_named_date_is_in_tolerance(monkeypatch, capsys) -> None:
    refused = _run_52_53_q2(monkeypatch, external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
                            body=_q2_exhibit("Quarters Ended October 3, 2025 December 31, 2025 April 3, 2026"))
    assert refused == []
    assert "drift=270d, tolerance=6d" in capsys.readouterr().out


def test_stated_period_end_candidates_parse_comma_tight_dates_and_stop_on_prose() -> None:
    cands = refresh_mod._stated_period_end_candidates(_q2_exhibit("Quarters Ended July 3,2026 April 3, 2026"))
    assert cands == [date(2026, 7, 3), date(2026, 4, 3)]
    assert refresh_mod._stated_period_end_candidates(
        _q2_exhibit("quarter ended July 3, 2026. On July 8, 2026 the Company")) == [date(2026, 7, 3)]


def test_end_to_end_ambiguous_refusal_names_the_ambiguity(monkeypatch, capsys) -> None:
    ambiguous = _run_52_53_q2(monkeypatch, external_ids={"results_form": "8-K", "fiscal_calendar": "52_53_week"},
                              body=_q2_exhibit("Quarters Ended October 3, 2025 June 30, 2026 July 3, 2026"))
    assert ambiguous == []
    assert "ambiguous: 2 named period ends within tolerance" in capsys.readouterr().out


def test_end_to_end_unparseable_filing_date_is_skipped_not_raised(monkeypatch, capsys) -> None:
    dom = _synthetic_issuer(cik="0009990002", ticker="DOM", external_ids={"results_form": "8-K"})
    bad_row = {**_ON_LIKE_Q2_ROW, "filingDate": "2026-08-03T00:00:00Z"}
    revisions = _run_discovery(
        monkeypatch, ticker="DOM", issuer=dom, profile=_null_profile("DOM"),
        rows=[bad_row], headers={bad_row["accessionNumber"]: _ON_LIKE_SGML},
        exhibits={bad_row["accessionNumber"]: {"ef20072220_ex99-1.htm": _exhibit("quarter ended June 30, 2026")}},
    )
    assert revisions == []
    assert "unparseable filingDate" in capsys.readouterr().out
