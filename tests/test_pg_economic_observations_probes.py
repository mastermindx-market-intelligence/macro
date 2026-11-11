"""Frozen acceptance probes for CDV-1 Task 1 (PR #7905), round-2 Opus review.

Each test encodes one adversarial probe (P1-P11) or mutant gap (M2) from
OPUS_T1_PR_REVIEW_R2 against SEAT_RULING_T1_PR_R1 items R1-R6.  Every test
FAILED at head bc33493b for the reason stated in its docstring; the repair lane
must make them green WITHOUT editing this module.

Scope-bearing HTML bodies below are hand-authored LITERAL strings in P&G release
conventions ("<Ordinal> Quarter Fiscal Year <FY>", "Three Months Ended <Month D,
YYYY>", calendar-year period columns).  They are never generated from a
fiscal scope, so the fixture and the extractor cannot co-vary.  All figures are
synthetic (3.07/3.11 current, 2.93/2.97 prior); none is a reported P&G value.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date
import hashlib
from pathlib import Path

import pytest

import engine.company_intelligence as company_intelligence
from engine.company_intelligence.documents import text_span
from engine.company_intelligence.economic_observations import (
    EconomicObservationError,
    validate_selected_facts,
)
from engine.company_intelligence.event_workspace_build import build_event_workspace
from engine.company_intelligence.events import FiscalPeriod
from engine.company_intelligence.pg_profile import (
    PG_DEFINITIONS,
    PG_PRIVATE_RIGHTS_PROFILE,
    parse_pg_literal,
    pg_private_registry,
    pg_profile,
)
from engine.company_intelligence.qa_exchange import RIGHTS_PROFILES
from tests.earnings_economic_fixtures import (
    CIK,
    FISCAL_SCOPE,
    bind_release_document,
    pg_source_texts,
    pg_workspace_case,
)


# --------------------------------------------------------------------------
# Literal bodies (never derived from a scope)
# --------------------------------------------------------------------------

Q4_FY2026_BODY = """<html><head><title>Synthetic consumer release</title></head><body>
<h1>Fourth Quarter Fiscal Year 2026 Results</h1>
<p>This original synthetic release has no source relationship to any real company filing.</p>
<h2>Three Months Ended June 30, 2026</h2>
<table>
<tr><td></td><td>2026</td><td>2025</td></tr>
<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$2.93</td></tr>
<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>
</table>
<h2>Fiscal Year 2026 Results</h2>
<h2>Twelve Months Ended June 30, 2026</h2>
<table>
<tr><td></td><td>2026</td><td>2025</td></tr>
<tr><td>Diluted Net Earnings per Common Share</td><td>$12.07</td><td>$11.93</td></tr>
<tr><td>Core EPS</td><td>$12.11</td><td>$11.97</td></tr>
</table>
</body></html>"""

ANNUAL_ONLY_FY2026_BODY = """<html><head><title>Synthetic consumer annual summary</title></head><body>
<h1>Fiscal Year 2026 Results</h1>
<p>This original synthetic summary has no source relationship to any real company filing.</p>
<h2>Twelve Months Ended June 30, 2026</h2>
<table>
<tr><td></td><td>2026</td><td>2025</td></tr>
<tr><td>Diluted Net Earnings per Common Share</td><td>$12.07</td><td>$11.93</td></tr>
<tr><td>Core EPS</td><td>$12.11</td><td>$11.97</td></tr>
</table>
</body></html>"""

Q1_FY2027_BODY = """<html><head><title>Synthetic consumer release</title></head><body>
<h1>First Quarter Fiscal Year 2027</h1>
<p>This original synthetic release has no source relationship to any real company filing.</p>
<h2>Three Months Ended September 30, 2026</h2>
<table>
<tr><td></td><td>2026</td><td>2025</td></tr>
<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$2.93</td></tr>
<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>
</table>
</body></html>"""

Q4_FY2027_BODY = """<html><head><title>Synthetic consumer release</title></head><body>
<h1>Fourth Quarter Fiscal Year 2027</h1>
<p>This original synthetic release has no source relationship to any real company filing.</p>
<h2>Three Months Ended June 30, 2027</h2>
<table>
<tr><td></td><td>2027</td><td>2026</td></tr>
<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$2.93</td></tr>
<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>
</table>
</body></html>"""

UNIT_MISMATCH_Q4_FY2026_BODY = """<html><head><title>Synthetic consumer release</title></head><body>
<h1>Fourth Quarter Fiscal Year 2026 Results</h1>
<p>This original synthetic release has no source relationship to any real company filing.</p>
<h2>Three Months Ended June 30, 2026</h2>
<table>
<tr><td></td><td>2026</td><td>2025</td></tr>
<tr><td>Diluted Net Earnings per Common Share</td><td>$1.25)</td><td>$2.93</td></tr>
<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>
</table>
<h2>Net Sales Change Drivers 2026 vs. 2025</h2>
<h2>Three Months Ended June 30, 2026</h2>
<table>
<tr><td></td><td>Volume with Acquisitions &amp; Divestitures</td><td>Volume Excluding Acquisitions &amp; Divestitures</td><td>Foreign Exchange</td><td>Price</td><td>Mix</td><td>Other</td><td>Net Sales Growth</td></tr>
<tr><td>Total P&amp;G</td><td>1%</td><td>1%</td><td>(1)%</td><td>(1.25%</td><td>0%</td><td>0%</td><td>1%</td></tr>
</table>
</body></html>"""

COMBINED_ONLY_Q4_FY2026_BODY = """<html><head><title>Synthetic consumer release</title></head><body>
<h1>Fourth Quarter Fiscal Year 2026 Results</h1>
<p>This original synthetic release has no source relationship to any real company filing.</p>
<h2>Net Sales Change Drivers 2026 vs. 2025</h2>
<h2>Three Months Ended June 30, 2026</h2>
<table>
<tr><td></td><td>Volume/Mix</td><td>Foreign Exchange</td><td>Price</td><td>Other</td><td>Net Sales Growth</td></tr>
<tr><td>Total P&amp;G</td><td>2%</td><td>(1)%</td><td>1%</td><td>0%</td><td>2%</td></tr>
</table>
</body></html>"""

DASH_NO_CONVENTION_Q4_FY2026_BODY = """<html><head><title>Synthetic consumer release</title></head><body>
<h1>Fourth Quarter Fiscal Year 2026 Results</h1>
<p>This original synthetic release has no source relationship to any real company filing.</p>
<h2>Net Sales Change Drivers 2026 vs. 2025</h2>
<h2>Three Months Ended June 30, 2026</h2>
<table>
<tr><td></td><td>Volume with Acquisitions &amp; Divestitures</td><td>Volume Excluding Acquisitions &amp; Divestitures</td><td>Foreign Exchange</td><td>Price</td><td>Mix</td><td>Other</td><td>Net Sales Growth</td></tr>
<tr><td>Total P&amp;G</td><td>1%</td><td>—</td><td>(1)%</td><td>1%</td><td>0%</td><td>0%</td><td>1%</td></tr>
</table>
</body></html>"""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Case:
    scope: tuple[str, str, str, str]
    fiscal_year: int
    fiscal_quarter: int
    period_end: date
    filing_date: str
    acceptance: str
    observed_at: str
    accession: str


Q4_FY2026 = Case(("2026-04-01", "2026-06-30", "2025-04-01", "2025-06-30"), 2026, 4, date(2026, 6, 30),
                 "2026-07-29", "2026-07-29T11:00:00Z", "2026-07-29T11:05:00Z", "0000080424-26-000101")
Q1_FY2027 = Case(("2026-07-01", "2026-09-30", "2025-07-01", "2025-09-30"), 2027, 1, date(2026, 9, 30),
                 "2026-10-20", "2026-10-20T11:00:00Z", "2026-10-20T11:05:00Z", "0000080424-26-000102")
Q4_FY2027 = Case(("2027-04-01", "2027-06-30", "2026-04-01", "2026-06-30"), 2027, 4, date(2027, 6, 30),
                 "2027-07-29", "2027-07-29T11:00:00Z", "2027-07-29T11:05:00Z", "0000080424-27-000103")

EPS_METRICS = {"pg_diluted_eps", "pg_prior_diluted_eps", "pg_core_eps", "pg_prior_core_eps"}


def _definition(metric: str):
    return next(item for item in PG_DEFINITIONS if item.metric == metric)


def _literal_workspace(body: str, case: Case, slug: str, *, quarter: int | None = None):
    filing = {
        "cik": CIK,
        "accession": case.accession,
        "form": "8-K",
        "filing_date": case.filing_date,
        "acceptance_datetime": case.acceptance,
        "report_date": case.filing_date,
        "exhibit_url": f"https://synthetic.invalid/{slug}.htm",
    }
    bound = bind_release_document(
        cik=CIK, accession=case.accession, body=body, form="8-K",
        filing_date=case.filing_date, acceptance_datetime=case.acceptance,
        report_date=case.filing_date, exhibit_url=filing["exhibit_url"],
        content_type="text/html",
    )
    workspace = build_event_workspace(
        registry=pg_private_registry(),
        ticker="PG",
        asof=date.fromisoformat(case.filing_date),
        fiscal_period=FiscalPeriod(
            year=case.fiscal_year,
            quarter=case.fiscal_quarter if quarter is None else quarter,
            calendar_end=case.period_end,
        ),
        exhibit_body=bound.source,
        filing=filing,
        transcript=None,
        observed_at=case.observed_at,
        source_available_at=case.acceptance,
        profile=pg_profile(fiscal_scope=case.scope),
    )
    return workspace, {bound.revision.document_id: bound.source}


def _pg_rows(workspace) -> dict:
    return {
        row["metric"]: row for row in workspace["facts"]
        if isinstance(row, dict) and str(row.get("metric", "")).startswith("pg_")
    }


def _present(workspace) -> dict:
    return {metric: row for metric, row in _pg_rows(workspace).items() if "value" in row}


def _validate(workspace, texts, scope):
    return validate_selected_facts(workspace, source_texts=texts, fiscal_scope=scope)


def _refused(workspace, texts, scope=FISCAL_SCOPE) -> None:
    with pytest.raises(EconomicObservationError):
        _validate(workspace, texts, scope)


def _fixture_case(kind: str = "annual_first"):
    workspace, texts = copy.deepcopy(pg_workspace_case(kind)), pg_source_texts(kind)
    # Control: the untampered workspace must validate, so a later refusal is
    # caused by the tamper under test and not by an unrelated scope error.
    _validate(copy.deepcopy(workspace), texts, FISCAL_SCOPE)
    return workspace, texts


# --------------------------------------------------------------------------
# R2 — replay must bind the span to the stored period and metric (P1-P3)
# --------------------------------------------------------------------------

def test_p1_current_fact_cannot_carry_the_prior_period_cell() -> None:
    """R2 (period half), probe P1.

    pg_diluted_eps is re-pointed at the prior-period cell with the prior value.
    At bc33493b this is ACCEPTED: the validator compares the replayed number to
    the stored value but never ties the span to the column of the stored period.
    """
    workspace, texts = _fixture_case()
    rows = _pg_rows(workspace)
    current, prior = rows["pg_diluted_eps"], rows["pg_prior_diluted_eps"]
    assert "value" in current and "value" in prior and current["value"] != prior["value"]
    current["source_span"] = copy.deepcopy(prior["source_span"])
    current["value"] = prior["value"]
    _refused(workspace, texts)


def test_p2_non_gaap_metric_cannot_be_proven_by_a_gaap_cell() -> None:
    """R2 (span-to-row binding), probe P2.

    pg_core_eps is re-pointed at the GAAP diluted EPS cell and value.  At
    bc33493b this is ACCEPTED: replay proves "some bytes parse to this number",
    not "this metric's cell".
    """
    workspace, texts = _fixture_case()
    rows = _pg_rows(workspace)
    core, diluted = rows["pg_core_eps"], rows["pg_diluted_eps"]
    assert "value" in core and "value" in diluted and core["value"] != diluted["value"]
    core["source_span"] = copy.deepcopy(diluted["source_span"])
    core["value"] = diluted["value"]
    _refused(workspace, texts)


def test_p3_swapped_current_prior_pair_with_values_refused() -> None:
    """R2 named tamper "a swapped current/prior span pair", probe P3.

    Spans AND values of pg_diluted_eps / pg_prior_diluted_eps are swapped
    coherently.  At bc33493b this is ACCEPTED (the shipped "span pair" test
    swaps two driver rows, never the current/prior pair).
    """
    workspace, texts = _fixture_case()
    rows = _pg_rows(workspace)
    current, prior = rows["pg_diluted_eps"], rows["pg_prior_diluted_eps"]
    assert "value" in current and "value" in prior and current["value"] != prior["value"]
    current["source_span"], prior["source_span"] = prior["source_span"], current["source_span"]
    current["value"], prior["value"] = prior["value"], current["value"]
    _refused(workspace, texts)


# --------------------------------------------------------------------------
# R5 — workspace quarter is the FISCAL quarter (P4, mutant M2)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("body", "case", "quarter", "accepted"),
    [
        (Q4_FY2026_BODY, Q4_FY2026, 4, True),
        (Q4_FY2026_BODY, Q4_FY2026, 2, False),
        (Q1_FY2027_BODY, Q1_FY2027, 1, True),
        (Q1_FY2027_BODY, Q1_FY2027, 3, False),
    ],
    ids=["fq4-june-accepted", "calendar-q2-refused", "fq1-september-accepted", "calendar-q3-refused"],
)
def test_p4_workspace_quarter_is_the_pg_fiscal_quarter(body, case, quarter, accepted) -> None:
    """R5 quarter check, probe P4 + mutant M2 gap.

    P&G's fiscal year ends in June, so the June-30 quarter is fiscal Q4 and the
    September-30 quarter is fiscal Q1.  At bc33493b economic_observations.py:80
    derives the CALENDAR quarter ((month+2)//3), so the correctly labelled
    fiscal quarters are REFUSED and the calendar labels ACCEPTED; with the check
    deleted (M2) the shipped suite stayed 33/33 green.
    """
    workspace, texts = _literal_workspace(body, case, f"p4-{case.fiscal_year}-{quarter}", quarter=quarter)
    if accepted:
        rows = _validate(workspace, texts, case.scope)
        assert len(rows) == len(PG_DEFINITIONS)
    else:
        _refused(workspace, texts, case.scope)


# --------------------------------------------------------------------------
# R1 — vocabulary is derived from fiscal_scope in P&G conventions (P5, P6)
# --------------------------------------------------------------------------

def _assert_eps_bound(workspace, case: Case) -> None:
    present = _present(workspace)
    current_end, prior_end = case.scope[1], case.scope[3]
    expected = {
        "pg_diluted_eps": (3.07, current_end),
        "pg_core_eps": (3.11, current_end),
        "pg_prior_diluted_eps": (2.93, prior_end),
        "pg_prior_core_eps": (2.97, prior_end),
    }
    assert {m: (present[m]["value"], present[m]["period"]) for m in expected if m in present} == expected
    # Nothing else binds: the body carries only the quarterly EPS table.
    assert set(present) == set(expected)


def test_p5_q1_fy2027_binds_from_fiscal_year_heading_and_three_months_ended() -> None:
    """R1, probe P5.

    Q1 FY2027 scope (quarter ended September 30, 2026; prior column 2025),
    literal body headed "First Quarter Fiscal Year 2027" / "Three Months Ended
    September 30, 2026".  At bc33493b NO EPS fact binds: the extractor looks for
    "Fourth Quarter <calendar year> Results" and ISO-date column headers.
    """
    workspace, texts = _literal_workspace(Q1_FY2027_BODY, Q1_FY2027, "p5-q1-fy2027")
    _assert_eps_bound(workspace, Q1_FY2027)
    _validate(workspace, texts, Q1_FY2027.scope)


def test_p6_three_months_ended_heading_binds_and_annual_tables_never_bind() -> None:
    """R1, probe P6 + annual-form refusal.

    A Q4 release carrying both the "Three Months Ended June 30, 2026" table and
    the "Fiscal Year 2026 Results" / "Twelve Months Ended June 30, 2026" table:
    only the quarterly values bind.  An annual-only body under the same
    quarterly scope binds NOTHING.  At bc33493b the first assertion fails: no
    EPS fact binds from the "Three Months Ended" heading.
    """
    workspace, texts = _literal_workspace(Q4_FY2026_BODY, Q4_FY2026, "p6-q4-fy2026")
    _assert_eps_bound(workspace, Q4_FY2026)
    assert not {row["value"] for row in _present(workspace).values()} & {12.07, 12.11, 11.93, 11.97}
    _validate(workspace, texts, Q4_FY2026.scope)

    annual, annual_texts = _literal_workspace(ANNUAL_ONLY_FY2026_BODY, Q4_FY2026, "p6-annual-fy2026")
    assert _present(annual) == {}
    _validate(annual, annual_texts, Q4_FY2026.scope)


def test_prior_period_column_binds_only_as_prior_for_fy2027() -> None:
    """R1 required test: FY2027 scope against a body that also carries the
    prior-year 2026 column; 2027 binds as current, 2026 only as prior, nothing
    else binds.  Prior values sit in the prior-period COLUMN of the same rows,
    never in a "Prior ... EPS" row.  At bc33493b nothing binds (fixture-only
    "Prior Diluted EPS" rows and ISO headers are required).
    """
    workspace, texts = _literal_workspace(Q4_FY2027_BODY, Q4_FY2027, "prior-column-fy2027")
    _assert_eps_bound(workspace, Q4_FY2027)
    present = _present(workspace)
    assert all(present[m]["period"] == "2026-06-30" for m in ("pg_prior_diluted_eps", "pg_prior_core_eps"))
    assert all(present[m]["value"] not in {2.93, 2.97} for m in ("pg_diluted_eps", "pg_core_eps"))
    _validate(workspace, texts, Q4_FY2027.scope)


# --------------------------------------------------------------------------
# R4 — unit-aware parsing, typed unit_mismatch (P7)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("literal", ["(1.25%", "1.25%)"])
def test_p7_unbalanced_parentheses_are_not_percent_numbers(literal) -> None:
    """R4, probe P7.  At bc33493b pg_profile.py:112 coerces unbalanced
    parentheses: '(1.25%' -> -1.25 and '1.25%)' -> 1.25."""
    assert parse_pg_literal(literal, unit="percent") is None


def test_p7_unit_shape_mismatch_is_a_typed_unit_mismatch_absence() -> None:
    """R4 typed absence, probe P7 + the missing_units deviation.

    '$1.25)' in the diluted EPS cell and '(1.25%' in the Price driver cell must
    each yield a typed absence with reason ``unit_mismatch``.  At bc33493b
    neither row is located in P&G conventions, and the shipped reason token is
    ``missing_units`` (``unit_mismatch`` is not in ABSENCE_REASONS).
    """
    workspace, texts = _literal_workspace(UNIT_MISMATCH_Q4_FY2026_BODY, Q4_FY2026, "p7-unit-mismatch")
    rows = _pg_rows(workspace)
    for metric in ("pg_diluted_eps", "pg_price_contribution_pp"):
        assert "value" not in rows[metric]
        assert rows[metric]["typed_absence"]["reason"] == "unit_mismatch"
    assert rows["pg_prior_diluted_eps"].get("value") == 2.93
    _validate(workspace, texts, Q4_FY2026.scope)


# --------------------------------------------------------------------------
# R5 — combined-only volume/mix (P8)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("source", ["literal", "fixture"])
def test_p8_combined_volume_mix_yields_named_absences_for_volume_and_mix(source) -> None:
    """R5 combined-only, probe P8.

    A body reporting ONLY a combined volume/mix line must yield typed absences
    for total volume, organic volume and mix, and the total-volume and mix
    absence subjects must name the combined presentation (both "volume" and
    "mix").  At bc33493b the fixture's "combined" case still binds
    pg_mix_contribution_pp = 0.5 from split driver columns, and absence subjects
    are the bare metric key.
    """
    if source == "literal":
        workspace, texts = _literal_workspace(COMBINED_ONLY_Q4_FY2026_BODY, Q4_FY2026, "p8-combined")
        scope = Q4_FY2026.scope
    else:
        workspace, texts = _fixture_case("combined_volume_only")
        scope = FISCAL_SCOPE
    rows = _pg_rows(workspace)
    for metric in ("pg_total_volume_growth_pct", "pg_organic_volume_growth_pct", "pg_mix_contribution_pp"):
        assert "value" not in rows[metric], metric
        assert "typed_absence" in rows[metric], metric
    for metric in ("pg_total_volume_growth_pct", "pg_mix_contribution_pp"):
        subject = rows[metric]["typed_absence"]["subject"].casefold()
        assert "volume" in subject and "mix" in subject, subject
    _validate(workspace, texts, scope)


# --------------------------------------------------------------------------
# R2/R6 — dash replay requires the neutral-zero convention (P9)
# --------------------------------------------------------------------------

def test_p9_forged_neutral_zero_on_a_dash_without_convention_refused() -> None:
    """R2/R6 dash semantics, probe P9.

    A present 0.0 row is forged for pg_organic_volume_growth_pct with a valid
    byte receipt on a dash cell whose table states no dash-means-zero
    convention.  At bc33493b this is ACCEPTED: economic_observations.py:216
    maps any replayed dash to 0.0 without the convention the extractor demands.
    """
    workspace, texts = _literal_workspace(DASH_NO_CONVENTION_Q4_FY2026_BODY, Q4_FY2026, "p9-dash")
    # Control: the honest workspace validates, so the refusal below is the dash's.
    _validate(copy.deepcopy(workspace), texts, Q4_FY2026.scope)
    (document_id, source), = texts.items()
    source_bytes = source.encode("utf-8")
    marker = "<td>—</td>".encode("utf-8")
    assert source_bytes.count(marker) == 1
    start = source_bytes.index(marker) + len(b"<td>")
    end = start + len("—".encode("utf-8"))
    span = text_span(
        document_id=document_id,
        document_version=1,
        body_sha256=hashlib.sha256(source_bytes).hexdigest(),
        segment_index=0,
        segment_text=source,
        start_byte=start,
        end_byte=end,
        text="—",
        rights_profile=PG_PRIVATE_RIGHTS_PROFILE,
    ).to_payload()
    metric = "pg_organic_volume_growth_pct"
    definition = _definition(metric)
    rows = _pg_rows(workspace)
    forged = {
        "schema": "event_fact.v1",
        "fact_id": rows[metric]["fact_id"],
        "event_id": workspace["event_id"],
        "metric": metric,
        "value": 0.0,
        "unit": definition.unit,
        "period": Q4_FY2026.scope[1],
        "basis": definition.basis,
        "source_span": span,
    }
    workspace["facts"] = [forged if row is rows[metric] else row for row in workspace["facts"]]
    _refused(workspace, texts, Q4_FY2026.scope)


# --------------------------------------------------------------------------
# R6 — fact identity (P10), document binding (P11), single rights registry
# --------------------------------------------------------------------------

def test_p10_fact_id_is_event_scoped_and_duplicates_refused() -> None:
    """R6 fact_id derivation, probe P10.

    fact_id must derive from (event, metric, period, basis): the same metric in
    two events gets two ids, a fact_id borrowed from another event is refused,
    and a duplicate fact_id inside one event is refused.  At bc33493b both
    events mint ``fact_pg_diluted_eps`` (pg_profile.py:201/217).
    """
    q4, q4_texts = _literal_workspace(Q4_FY2026_BODY, Q4_FY2026, "p10-q4-fy2026")
    q1, _ = _literal_workspace(Q1_FY2027_BODY, Q1_FY2027, "p10-q1-fy2027")
    assert q4["event_id"] != q1["event_id"]
    q4_id = _pg_rows(q4)["pg_diluted_eps"]["fact_id"]
    q1_id = _pg_rows(q1)["pg_diluted_eps"]["fact_id"]
    assert q4_id != q1_id
    _validate(copy.deepcopy(q4), q4_texts, Q4_FY2026.scope)

    borrowed = copy.deepcopy(q4)
    _pg_rows(borrowed)["pg_diluted_eps"]["fact_id"] = q1_id
    _refused(borrowed, q4_texts, Q4_FY2026.scope)

    duplicate = copy.deepcopy(q4)
    rows = _pg_rows(duplicate)
    rows["pg_core_eps"]["fact_id"] = rows["pg_diluted_eps"]["fact_id"]
    _refused(duplicate, q4_texts, Q4_FY2026.scope)


@pytest.mark.parametrize("target", ["absence", "span"])
def test_p11_document_id_must_be_the_workspace_document(target) -> None:
    """R6 absence/span binding, probe P11.

    An absence row or a present span re-labelled to a foreign document id that
    the caller also supplies (same bytes) must be refused: document identity is
    bound to the workspace's own document, not to whatever the caller passes in
    source_texts.  At bc33493b both are ACCEPTED (economic_observations.py:152,
    :181-183 check membership in source_texts only).
    """
    workspace, texts = _fixture_case()
    (_document_id, source), = texts.items()
    rows = _pg_rows(workspace)
    if target == "absence":
        row = next(row for row in rows.values() if "typed_absence" in row)
        row["typed_absence"]["document_id"] = "doc_foreign_synthetic"
    else:
        row = rows["pg_diluted_eps"]
        assert "source_span" in row
        row["source_span"]["document_id"] = "doc_foreign_synthetic"
    _refused(workspace, {**texts, "doc_foreign_synthetic": source})


def test_private_rights_token_is_the_single_registry_entry() -> None:
    """R6 single rights registry (registry found: engine/company_intelligence/
    qa_exchange.py:26 ``RIGHTS_PROFILES``).

    The private token pg_profile stamps must be the registry's entry and the
    literal must be declared in exactly one module of the package — the
    registry.  At bc33493b the equality holds but the literal is declared twice
    (qa_exchange.py:26 and pg_profile.py:26) and the registry is read by nothing.
    """
    assert PG_PRIVATE_RIGHTS_PROFILE in RIGHTS_PROFILES
    registered = next(item for item in RIGHTS_PROFILES if item == PG_PRIVATE_RIGHTS_PROFILE)
    assert registered == PG_PRIVATE_RIGHTS_PROFILE
    package = Path(company_intelligence.__file__).parent
    declaring = sorted(
        path.name for path in package.glob("*.py")
        if f'"{PG_PRIVATE_RIGHTS_PROFILE}"' in path.read_text(encoding="utf-8")
        or f"'{PG_PRIVATE_RIGHTS_PROFILE}'" in path.read_text(encoding="utf-8")
    )
    assert declaring == ["qa_exchange.py"]
