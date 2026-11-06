"""FIF Lane C2: BAC consolidated period grammar and R7 per-cell period agreement.

Covers the three source-observed Bank of America consolidated header shapes
(glued day-year balance-sheet cells, N-months-ended duration groups over a
year row, blank interstitials) and the R7 rule that a displayed numeric cell
may never sit in a dated column its own inline-XBRL context contradicts.
Synthetic HTML only; no real filing bytes.
"""
from __future__ import annotations

import types

import pytest

from engine.fundamental_forensics.statement_graph import (
    GoldenFilingPackage,
    StatementGraphError,
    parse_displayed_primary_table,
    reconstruct_statement,
)

BS_TITLE = "Consolidated Balance Sheet"
INCOME_TITLE = "Consolidated Statement of Income"
CF_TITLE = "Consolidated Statement of Cash Flows"

_COLUMNS_ABSENT = r"^displayed statement columns are absent"


def _ix(context: str, fact_id: str, *, name: str = "us-gaap:Revenues", value: str = "100") -> str:
    return (
        f'<ix:nonFraction name="{name}" contextRef="{context}" id="{fact_id}" '
        f'unitRef="usd" decimals="-6" scale="6">{value}</ix:nonFraction>'
    )


# --- Lane C2 shape 1: glued "<Month> <day><4-digit year>" header cells ---


def _glued_bs_html(*, dates: tuple[str, str] = ("June 302025", "December 312024")) -> str:
    """The BAC 10-Q balance-sheet shape: glued date cells rowspan over a unit row."""
    return f"""
    <html><body>
    <table>
      <tr><td colspan="5">{BS_TITLE}</td></tr>
      <tr><td></td><td colspan="2" rowspan="2">{dates[0]}</td><td colspan="2" rowspan="2">{dates[1]}</td></tr>
      <tr><td>(Dollars in millions)</td></tr>
      <tr><td>Assets</td><td></td><td></td><td></td><td></td></tr>
      <tr><td>Cash and due from banks</td><td>$</td><td>{_ix("c2025", "c2-bs-25")}</td><td>$</td><td>{_ix("c2024", "c2-bs-24")}</td></tr>
      <tr><td>Total assets</td><td colspan="2">{_ix("c2025", "c2-bs-t25", name="us-gaap:Assets", value="200")}</td><td colspan="2">{_ix("c2024", "c2-bs-t24", name="us-gaap:Assets", value="180")}</td></tr>
    </table>
    </body></html>
    """


def test_glued_balance_sheet_header_reconstructs() -> None:
    parsed = parse_displayed_primary_table(_glued_bs_html(), title=BS_TITLE)
    assert parsed["columns_iso"] == ["2025-06-30", "2024-12-31"]
    assert [row["label"] for row in parsed["rows"]] == [
        "Assets", "Cash and due from banks", "Total assets",
    ]
    assert [f["fact_id"] for f in parsed["rows"][1]["value_facts"]] == ["c2-bs-25", "c2-bs-24"]
    assert [f["fact_id"] for f in parsed["rows"][2]["value_facts"]] == ["c2-bs-t25", "c2-bs-t24"]


def test_glued_header_with_unit_band_in_the_same_row_reconstructs() -> None:
    # The FY2025 Q2 variant prints the unit band on the glued-date row itself.
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="5">{BS_TITLE}</td></tr>
      <tr><td></td><td></td><td></td><td></td><td></td></tr>
      <tr><td>(Dollars in millions)</td><td colspan="2">June 302026</td><td colspan="2">December 312025</td></tr>
      <tr><td>Assets</td><td></td><td></td><td></td><td></td></tr>
      <tr><td>Cash and due from banks</td><td>$</td><td>{_ix("c2026", "c2-bs2-26")}</td><td>$</td><td>{_ix("c2025", "c2-bs2-25")}</td></tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=BS_TITLE)
    assert parsed["columns_iso"] == ["2026-06-30", "2025-12-31"]
    assert [row["label"] for row in parsed["rows"]] == ["Assets", "Cash and due from banks"]


def test_glued_leap_day_composes_only_in_a_leap_year() -> None:
    parsed = parse_displayed_primary_table(
        _glued_bs_html(dates=("February 292024", "December 312023")), title=BS_TITLE
    )
    assert parsed["columns_iso"] == ["2024-02-29", "2023-12-31"]


@pytest.mark.parametrize("dates", [
    ("February 292023", "December 312022"),  # Feb 29 in a non-leap year
    ("June 312025", "December 312024"),      # day invalid for the month
    ("June 3020255", "December 312024"),     # five digits after the month
    ("Jun302025", "December 312024"),        # abbreviation with no space
    ("June 302025abc", "December 312024"),   # trailing text
    ("December 311989", "December 311988"),  # year below the 1990 bound
    ("June 302101", "June 302102"),          # year above the 2100 bound
])
def test_glued_grammar_misforms_stay_unmatched(dates: tuple[str, str]) -> None:
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(_glued_bs_html(dates=dates), title=BS_TITLE)


def test_glued_token_in_a_fact_row_is_not_a_header() -> None:
    # The glued token sits below the first fact row; no header cell carries a
    # date, so the statement keeps refusing instead of minting columns.
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="5">{BS_TITLE}</td></tr>
      <tr><td>Line</td><td></td><td></td><td></td><td></td></tr>
      <tr><td>Balance at June 302025</td><td colspan="2">{_ix("c2025", "c2-bf-25")}</td><td colspan="2">{_ix("c2024", "c2-bf-24")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=BS_TITLE)


def test_glued_token_inside_a_sentence_is_not_a_header() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="5">{BS_TITLE}</td></tr>
      <tr><td>The quarter ended June 302025 per the filing</td><td>June 302025 and December 312024 noted</td><td></td><td></td><td></td></tr>
      <tr><td>Assets</td><td colspan="2">{_ix("c2025", "c2-bsen-25")}</td><td colspan="2">{_ix("c2024", "c2-bsen-24")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=BS_TITLE)


def test_glued_single_date_cell_is_not_two_columns() -> None:
    html = _glued_bs_html().replace(
        '<td colspan="2" rowspan="2">December 312024</td>', "<td></td><td></td>"
    )
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=BS_TITLE)


def test_glued_second_header_row_with_different_dates_does_not_apply() -> None:
    # A later glued row with different dates must not be swallowed; the table
    # keeps the same refusal it reached before the glued composer applied.
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="5">{BS_TITLE}</td></tr>
      <tr><td></td><td colspan="2">June 302025</td><td colspan="2">December 312024</td></tr>
      <tr><td></td><td colspan="2">March 312025</td><td colspan="2">December 312023</td></tr>
      <tr><td>(Dollars in millions)</td></tr>
      <tr><td>Assets</td><td></td><td></td><td></td><td></td></tr>
      <tr><td>Cash and due from banks</td><td>$</td><td>{_ix("c2025", "c2-gd-25")}</td><td>$</td><td>{_ix("c2024", "c2-gd-24")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=BS_TITLE)


def test_glued_two_identical_header_rows_still_reconstruct() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="5">{BS_TITLE}</td></tr>
      <tr><td></td><td colspan="2">June 302025</td><td colspan="2">December 312024</td></tr>
      <tr><td></td><td colspan="2">June 302025</td><td colspan="2">December 312024</td></tr>
      <tr><td>(Dollars in millions)</td></tr>
      <tr><td>Assets</td><td></td><td></td><td></td><td></td></tr>
      <tr><td>Cash and due from banks</td><td>$</td><td>{_ix("c2025", "c2-gi-25")}</td><td>$</td><td>{_ix("c2024", "c2-gi-24")}</td></tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=BS_TITLE)
    assert parsed["columns_iso"] == ["2025-06-30", "2024-12-31"]


# --- Lane C2 shape 2/3: N-months-ended duration groups over a year row ---


def _grouped_income_html(*, year_row: str | None = None, fact_row: str | None = None) -> str:
    years = (
        "<td>(In millions, except per share information)</td>"
        "<td>2025</td><td></td><td>2024</td><td>2025</td><td></td><td>2024</td>"
        if year_row is None
        else year_row
    )
    facts = (
        "<td>Interest income</td><td>$</td><td>"
        + _ix("q3m25", "c2-inc-q25")
        + "</td><td>"
        + _ix("q3m24", "c2-inc-q24")
        + '</td><td>$</td><td>'
        + _ix("h6m25", "c2-inc-h25")
        + "</td><td>"
        + _ix("h6m24", "c2-inc-h24")
        + "</td>"
        if fact_row is None
        else fact_row
    )
    return f"""
    <html><body>
    <table>
      <tr><td colspan="7">{INCOME_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Three Months Ended June 30</td><td colspan="3">Six Months Ended June 30</td></tr>
      <tr>{years}</tr>
      <tr><td>Net interest income</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
      <tr>{facts}</tr>
    </table>
    </body></html>
    """


def test_grouped_two_group_income_reconstructs() -> None:
    parsed = parse_displayed_primary_table(_grouped_income_html(), title=INCOME_TITLE)
    assert parsed["columns_source"] == "composed_grouped_duration_year_row"
    assert parsed["columns_iso"] == ["2025-06-30", "2024-06-30", "2025-06-30", "2024-06-30"]
    assert parsed["columns_periods"] == [
        {"kind": "duration", "start": "2025-04-01", "end": "2025-06-30"},
        {"kind": "duration", "start": "2024-04-01", "end": "2024-06-30"},
        {"kind": "duration", "start": "2025-01-01", "end": "2025-06-30"},
        {"kind": "duration", "start": "2024-01-01", "end": "2024-06-30"},
    ]
    assert [row["label"] for row in parsed["rows"]] == ["Net interest income", "Interest income"]
    assert [f["fact_id"] for f in parsed["rows"][1]["value_facts"]] == [
        "c2-inc-q25", "c2-inc-q24", "c2-inc-h25", "c2-inc-h24",
    ]


def test_grouped_cash_flow_with_blank_row_reconstructs() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Six Months Ended June 30</td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td>(Dollars in millions)</td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Operating activities</td><td></td><td></td><td></td></tr>
      <tr><td>Net income</td><td>$</td><td>{_ix("h6m25", "c2-cf-25", name="us-gaap:NetIncomeLoss")}</td><td>{_ix("h6m24", "c2-cf-24", name="us-gaap:NetIncomeLoss")}</td></tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=CF_TITLE)
    assert parsed["columns_source"] == "composed_grouped_duration_year_row"
    assert parsed["columns_iso"] == ["2025-06-30", "2024-06-30"]
    assert parsed["columns_periods"] == [
        {"kind": "duration", "start": "2025-01-01", "end": "2025-06-30"},
        {"kind": "duration", "start": "2024-01-01", "end": "2024-06-30"},
    ]
    assert [f["fact_id"] for f in parsed["rows"][1]["value_facts"]] == ["c2-cf-25", "c2-cf-24"]


def test_grouped_two_unit_bands_between_banner_and_years_do_not_apply() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Six Months Ended June 30</td></tr>
      <tr><td colspan="4">(Dollars in millions)</td></tr>
      <tr><td colspan="4">(Millions of dollars)</td></tr>
      <tr><td>(Dollars in millions)</td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("h6m25", "c2-2u-25", name="us-gaap:NetIncomeLoss")}</td><td></td><td>{_ix("h6m24", "c2-2u-24", name="us-gaap:NetIncomeLoss")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=CF_TITLE)


def test_grouped_unit_band_row_between_banner_and_years_composes() -> None:
    # The year row also prints a unit label, so the single-banner composer's
    # pure-year row declines and only the grouped composer can cross the exact
    # unit band between the banner and its years.
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Six Months Ended June 30</td></tr>
      <tr><td colspan="4">(Dollars in millions)</td></tr>
      <tr><td>(Dollars in millions)</td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("h6m25", "c2-cfu-25", name="us-gaap:NetIncomeLoss")}</td><td></td><td>{_ix("h6m24", "c2-cfu-24", name="us-gaap:NetIncomeLoss")}</td></tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=CF_TITLE)
    assert parsed["columns_source"] == "composed_grouped_duration_year_row"
    assert parsed["columns_iso"] == ["2025-06-30", "2024-06-30"]


def test_grouped_non_blank_interstitial_stays_a_refusal() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Six Months Ended June 30</td></tr>
      <tr><td colspan="4">Prepared in accordance with U.S. GAAP</td></tr>
      <tr><td></td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("h6m25", "c2-cfn-25", name="us-gaap:NetIncomeLoss")}</td><td></td><td>{_ix("h6m24", "c2-cfn-24", name="us-gaap:NetIncomeLoss")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=CF_TITLE)


def test_grouped_span_not_covering_the_year_run_refuses() -> None:
    # The Q1 income shape: the single banner spans only the first year cell,
    # so the second year column's duration is not proven by the display.
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="5">{INCOME_TITLE}</td></tr>
      <tr><td></td><td colspan="2">Three Months Ended March 31</td><td></td><td></td></tr>
      <tr><td>(In millions, except per share information)</td><td>2025</td><td></td><td></td><td>2024</td></tr>
      <tr><td>Interest income</td><td>{_ix("q1m25", "c2-q1-25")}</td><td></td><td></td><td>{_ix("q1m24", "c2-q1-24")}</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: grouped duration banner does not cover"
        r" an exact contiguous run of year cells$",
    ):
        parse_displayed_primary_table(html, title=INCOME_TITLE)


def test_grouped_junk_inside_a_group_span_refuses() -> None:
    year_row = (
        "<td>(In millions, except per share information)</td>"
        "<td>2025</td><td>Change</td><td>2024</td><td>2025</td><td></td><td>2024</td>"
    )
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: grouped duration banner does not cover",
    ):
        parse_displayed_primary_table(_grouped_income_html(year_row=year_row), title=INCOME_TITLE)


def test_grouped_count_mismatch_refuses() -> None:
    # Two groups x two years compose four columns, but the fact rows print three.
    fact_row = (
        "<td>Interest income</td><td>$</td><td>"
        + _ix("q3m25", "c2-cm-q25")
        + "</td><td>"
        + _ix("q3m24", "c2-cm-q24")
        + '</td><td>$</td><td>'
        + _ix("h6m25", "c2-cm-h25")
        + "</td><td>11%</td>"
    )
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: grouped duration groups do not match"
        r" the displayed fact columns$",
    ):
        parse_displayed_primary_table(_grouped_income_html(fact_row=fact_row), title=INCOME_TITLE)


def test_grouped_years_not_strictly_descending_refuse() -> None:
    year_row = (
        "<td>(In millions, except per share information)</td>"
        "<td>2024</td><td></td><td>2025</td><td>2025</td><td></td><td>2024</td>"
    )
    with pytest.raises(
        StatementGraphError,
        match=r"^displayed statement layout unsupported: grouped duration years are not"
        r" strictly descending$",
    ):
        parse_displayed_primary_table(_grouped_income_html(year_row=year_row), title=INCOME_TITLE)


def test_grouped_banner_keeps_the_single_banner_composer_priority() -> None:
    # The CAT quarterly shape (banner with a trailing comma over pure years)
    # must keep composing through the single-banner path, not the grouped one.
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td>Three Months Ended March 31,</td><td colspan="3"></td></tr>
      <tr><td></td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("q1m25", "c2-cat-25", name="us-gaap:NetIncomeLoss")}</td><td></td><td>{_ix("q1m24", "c2-cat-24", name="us-gaap:NetIncomeLoss")}</td></tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=CF_TITLE)
    assert parsed["columns_source"] == "composed_year_row"
    assert parsed["columns_iso"] == ["2025-03-31", "2024-03-31"]


# --- R7: per-cell period agreement over a synthetic iXBRL package ---


_ROLE = "http://synthetic.example/role/Income"
_LABEL_PERIOD_START = "http://www.xbrl.org/2003/role/periodStartLabel"
_LABEL_PERIOD_END = "http://www.xbrl.org/2003/role/periodEndLabel"
_CF_ROLE = "http://synthetic.example/role/CashFlow"


def _linkbases(
    role: str,
    *,
    presentation_arcs: list[tuple[str, str, str | None]] | None = None,
) -> dict[str, bytes]:
    if presentation_arcs is None:
        presentation_arcs = [("root", "line", None)]
    _known_loc_hrefs = {
        "root": "syn.htm#us-gaap_RevenuesAbstract",
        "line": "syn.htm#us-gaap_Revenues",
        "cashroot": "syn.htm#us-gaap_StatementOfCashFlowsAbstract",
        "cashline": "syn.htm#us-gaap_CashCashEquivalentsAtCarryingValue",
        # Two locators on one concept: a cash flow presents cash twice.
        "cashbeg": "syn.htm#us-gaap_CashCashEquivalentsAtCarryingValue",
        "cashend": "syn.htm#us-gaap_CashCashEquivalentsAtCarryingValue",
    }
    loc_labels: set[str] = set()
    loc_hrefs = dict(_known_loc_hrefs)
    for frm, to, _pref in presentation_arcs:
        loc_labels.add(frm)
        loc_labels.add(to)
    for label in loc_labels:
        loc_hrefs.setdefault(label, f"syn.htm#{label.replace(':', '_')}")
    arcs_xml = "".join(
        f'<link:presentationArc xlink:type="arc" xlink:from="{frm}" xlink:to="{to}" order="{i}"'
        + (f' preferredLabel="{pref}"' if pref else "")
        + "/>"
        for i, (frm, to, pref) in enumerate(presentation_arcs, start=1)
    )
    locs_xml = "".join(
        f'<link:loc xlink:label="{label}" xlink:href="{loc_hrefs[label]}"/>'
        for label in sorted(loc_labels)
    )
    presentation = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink">'
        f'<link:presentationLink xlink:role="{role}">'
        f"{locs_xml}{arcs_xml}"
        "</link:presentationLink></link:linkbase>"
    ).encode("utf-8")
    empty = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"/>'
    ).encode("utf-8")
    return {"presentation.xml": presentation, "label.xml": empty, "calculation.xml": empty}


def _duration(cid: str, start: str, end: str, dims: list | None = None) -> dict:
    return {
        "context_id": cid,
        "period": {"kind": "duration", "start_date": start, "end_date": end},
        "dimensions": dims or [],
        "entity": {"identifier": "0000070858"},
    }


def _instant(cid: str, day: str, dims: list | None = None) -> dict:
    return {
        "context_id": cid,
        "period": {"kind": "instant", "instant_date": day},
        "dimensions": dims or [],
        "entity": {"identifier": "0000070858"},
    }


def _fact(fid: str, context: str, *, name: str = "us-gaap:Revenues", value: str = "100") -> dict:
    return {
        "fact_id": fid,
        "concept_qname": name,
        "context_ref": context,
        "unit_ref": "usd",
        "normalized_value": value,
        "scale": "6",
        "decimals": "-6",
        "nil": False,
        "source_span": {"start": 0, "end": 1},
    }


_REGISTRY = types.SimpleNamespace(contracts=None)


def _reconstruct(
    html: str,
    facts: list[dict],
    contexts: list[dict],
    *,
    statement_type: str = "income_statement",
    role: str = _ROLE,
    title: str = INCOME_TITLE,
    presentation_arcs: list[tuple[str, str, str | None]] | None = None,
) -> dict:
    manifest = {
        "primary_document": "syn.htm",
        "members": [
            {"name": name, "state": "stored", "role": role_name, "content_sha256": "0" * 64}
            for name, role_name in (
                ("syn.htm", "primary"),
                ("presentation.xml", "presentation"),
                ("label.xml", "label"),
                ("calculation.xml", "calculation"),
            )
        ],
        "statement_roles": {
            statement_type: {"role_uri": role, "title": title, "title_search": title}
        },
    }
    members = {
        "syn.htm": html.encode("utf-8"),
        **_linkbases(role, presentation_arcs=presentation_arcs),
    }
    package = GoldenFilingPackage(manifest=manifest, members=members)
    parsed_instance = {
        "facts": facts,
        "contexts": contexts,
        "units": [
            {
                "unit_id": "usd",
                "numerator_measures": ["{http://www.xbrl.org/2003/iso4217}USD"],
                "denominator_measures": [],
            }
        ],
    }
    return reconstruct_statement(
        statement_type=statement_type,
        package=package,
        parsed_instance=parsed_instance,
        registry=_REGISTRY,
    )


_R7_PREFIX = r"^displayed cell period disagrees with its column "


def _grouped_income_facts_rows() -> str:
    return (
        "<td>Interest income</td><td>$</td><td>"
        + _ix("q3m25", "c2r-q25")
        + "</td><td>"
        + _ix("q3m24", "c2r-q24")
        + '</td><td>$</td><td>'
        + _ix("h6m25", "c2r-h25")
        + "</td><td>"
        + _ix("h6m24", "c2r-h24")
        + "</td>"
    )


_GROUPED_INCOME_CONTEXTS = [
    _duration("q3m25", "2025-04-01", "2025-06-30"),
    _duration("q3m24", "2024-04-01", "2024-06-30"),
    _duration("h6m25", "2025-01-01", "2025-06-30"),
    _duration("h6m24", "2024-01-01", "2024-06-30"),
]


def test_r7_grouped_income_agreeing_cells_reconstruct() -> None:
    html = _grouped_income_html(
        fact_row=_grouped_income_facts_rows(),
    )
    facts = [
        _fact("c2r-q25", "q3m25"),
        _fact("c2r-q24", "q3m24"),
        _fact("c2r-h25", "h6m25"),
        _fact("c2r-h24", "h6m24"),
    ]
    result = _reconstruct(html, facts, _GROUPED_INCOME_CONTEXTS)
    assert [c["start"] for c in result["columns"]] == [
        "2025-04-01", "2024-04-01", "2025-01-01", "2024-01-01",
    ]
    assert [cell["period"]["end"] for cell in result["rows"][-1]["cells"]] == [
        "2025-06-30", "2024-06-30", "2025-06-30", "2024-06-30",
    ]
    assert all(cell["quality_state"] == "available" for cell in result["rows"][-1]["cells"])


def test_r7_instant_fact_under_a_grouped_duration_column_refuses() -> None:
    # The first row binds every grouped column; the instant placed beneath the
    # 3-month column then contradicts the column it is displayed in.
    html = _grouped_income_html(fact_row=_grouped_income_facts_rows())
    html = html.replace(
        "</table>",
        "<tr><td>Balance line</td><td>"
        + _ix("mid", "c2r-inst")
        + "</td><td></td><td></td><td></td><td></td><td></td></tr></table>",
    )
    contexts = _GROUPED_INCOME_CONTEXTS + [_instant("mid", "2025-05-15")]
    facts = [
        _fact("c2r-q25", "q3m25"),
        _fact("c2r-q24", "q3m24"),
        _fact("c2r-h25", "h6m25"),
        _fact("c2r-h24", "h6m24"),
        _fact("c2r-inst", "mid"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: "):
        _reconstruct(html, facts, contexts)


def test_r7_duration_ending_on_the_wrong_date_refuses() -> None:
    html = _grouped_income_html(fact_row=_grouped_income_facts_rows())
    html = html.replace(
        "</table>",
        "<tr><td>Restated line</td><td>"
        + _ix("q3m25off", "c2r-off")
        + "</td><td></td><td></td><td></td><td></td><td></td></tr></table>",
    )
    contexts = _GROUPED_INCOME_CONTEXTS + [
        _duration("q3m25off", "2025-04-01", "2025-06-29")
    ]
    facts = [
        _fact("c2r-q25", "q3m25"),
        _fact("c2r-q24", "q3m24"),
        _fact("c2r-h25", "h6m25"),
        _fact("c2r-h24", "h6m24"),
        _fact("c2r-off", "q3m25off"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: "):
        _reconstruct(html, facts, contexts)


def test_r7_six_month_fact_under_a_grouped_three_month_column_refuses() -> None:
    html = _grouped_income_html(
        fact_row=_grouped_income_facts_rows(),
    )
    contexts = [
        _duration("q3m25", "2025-04-01", "2025-06-30"),
        _duration("q3m24", "2024-04-01", "2024-06-30"),
        _duration("h6m25", "2025-01-01", "2025-06-30"),
        _duration("h6m24", "2024-01-01", "2024-06-30"),
        _duration("h6m25b", "2025-01-01", "2025-06-30"),
    ]
    facts = [
        _fact("c2r-q25", "q3m25"),
        _fact("c2r-q24", "q3m24"),
        _fact("c2r-h25", "h6m25"),
        _fact("c2r-h24", "h6m24"),
        _fact("c2r-six", "h6m25b", value="55"),
    ]
    html = html.replace(
        "</table>",
        "<tr><td>Six-month line</td><td>"
        + _ix("h6m25b", "c2r-six", value="55")
        + "</td><td></td><td></td><td></td><td></td><td></td></tr></table>",
    )
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: "):
        _reconstruct(html, facts, contexts)


def test_r7_six_month_fact_under_a_dated_three_month_column_refuses() -> None:
    # Non-grouped path: the column prints a full date and binds its period
    # from the first same-column fact, so a 6-month context placed beneath it
    # is caught by the statement-period length rule.
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="3">{INCOME_TITLE}</td></tr>
      <tr><td>Line</td><td>June 30, 2025</td><td>June 30, 2024</td></tr>
      <tr><td>Interest income</td><td>{_ix("q3m25", "c2f-q25")}</td><td>{_ix("q3m24", "c2f-q24")}</td></tr>
      <tr><td>Six-month line</td><td>{_ix("h6m25", "c2f-six")}</td><td>{_ix("h6m24", "c2f-six24")}</td></tr>
    </table>
    </body></html>
    """
    contexts = [
        _duration("q3m25", "2025-04-01", "2025-06-30"),
        _duration("q3m24", "2024-04-01", "2024-06-30"),
        _duration("h6m25", "2025-01-01", "2025-06-30"),
        _duration("h6m24", "2024-01-01", "2024-06-30"),
    ]
    facts = [
        _fact("c2f-q25", "q3m25"),
        _fact("c2f-q24", "q3m24"),
        _fact("c2f-six", "h6m25"),
        _fact("c2f-six24", "h6m24"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: "):
        _reconstruct(html, facts, contexts)


def _annual_cf_year_ended_html(*, extra_row: str) -> str:
    return f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td>Year Ended December 31,</td><td colspan="3"></td></tr>
      <tr><td></td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("y25", "c2k-ni25", name="us-gaap:NetIncomeLoss")}</td><td></td><td>{_ix("y24", "c2k-ni24", name="us-gaap:NetIncomeLoss")}</td></tr>
      {extra_row}
    </table>
    </body></html>
    """


_ANNUAL_CF_CONTEXTS = [
    _duration("y25", "2025-01-01", "2025-12-31"),
    _duration("y24", "2024-01-01", "2024-12-31"),
]


def _annual_cf_net_income_facts() -> list[dict]:
    return [
        _fact("c2k-ni25", "y25", name="us-gaap:NetIncomeLoss"),
        _fact("c2k-ni24", "y24", name="us-gaap:NetIncomeLoss"),
    ]


def _cash_presentation_arcs(*, preferred: str | None) -> list[tuple[str, str, str | None]]:
    return [
        ("cashroot", "cashline", preferred),
    ]


@pytest.mark.parametrize(
    "presentation_arcs",
    [
        _cash_presentation_arcs(preferred=None),
        _cash_presentation_arcs(preferred=_LABEL_PERIOD_END),
    ],
)
def test_r7_prior_year_end_instant_under_current_year_column_refuses(
    presentation_arcs: list[tuple[str, str, str | None]],
) -> None:
    html = _annual_cf_year_ended_html(
        extra_row=(
            "<tr><td>Cash at end of year</td><td>"
            + _ix(
                "prior",
                "c2k-ce",
                name="us-gaap:CashCashEquivalentsAtCarryingValue",
                value="555",
            )
            + "</td><td>-</td><td></td></tr>"
        ),
    )
    contexts = _ANNUAL_CF_CONTEXTS + [_instant("prior", "2024-12-31")]
    facts = _annual_cf_net_income_facts() + [
        _fact(
            "c2k-ce",
            "prior",
            name="us-gaap:CashCashEquivalentsAtCarryingValue",
            value="555",
        ),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX):
        _reconstruct(
            html,
            facts,
            contexts,
            statement_type="cash_flow",
            title=CF_TITLE,
            role=_CF_ROLE,
            presentation_arcs=presentation_arcs,
        )


def test_r7_beginning_cash_with_period_start_label_reconstructs() -> None:
    html = _annual_cf_year_ended_html(
        extra_row=(
            "<tr><td>Cash at beginning of year</td><td>"
            + _ix(
                "b25",
                "c2k-b25",
                name="us-gaap:CashCashEquivalentsAtCarryingValue",
                value="10",
            )
            + "</td><td></td><td>"
            + _ix(
                "b24",
                "c2k-b24",
                name="us-gaap:CashCashEquivalentsAtCarryingValue",
                value="9",
            )
            + "</td></tr>"
        ),
    )
    contexts = _ANNUAL_CF_CONTEXTS + [
        _instant("b25", "2024-12-31"),
        _instant("b24", "2023-12-31"),
    ]
    facts = _annual_cf_net_income_facts() + [
        _fact("c2k-b25", "b25", name="us-gaap:CashCashEquivalentsAtCarryingValue", value="10"),
        _fact("c2k-b24", "b24", name="us-gaap:CashCashEquivalentsAtCarryingValue", value="9"),
    ]
    result = _reconstruct(
        html,
        facts,
        contexts,
        statement_type="cash_flow",
        title=CF_TITLE,
        role=_CF_ROLE,
        presentation_arcs=_cash_presentation_arcs(preferred=_LABEL_PERIOD_START),
    )
    cash_row = result["rows"][-1]
    assert cash_row["cells"][0]["value"] == "10"
    assert cash_row["cells"][1]["value"] == "9"


def test_r7_beginning_cash_with_wrong_end_instant_under_current_year_refuses() -> None:
    html = _annual_cf_year_ended_html(
        extra_row=(
            "<tr><td>Cash at beginning of year</td><td>"
            + _ix(
                "bad",
                "c2k-bad",
                name="us-gaap:CashCashEquivalentsAtCarryingValue",
                value="10",
            )
            + "</td><td></td><td>"
            + _ix(
                "b24",
                "c2k-b24",
                name="us-gaap:CashCashEquivalentsAtCarryingValue",
                value="9",
            )
            + "</td></tr>"
        ),
    )
    contexts = _ANNUAL_CF_CONTEXTS + [
        _instant("bad", "2025-12-31"),
        _instant("b24", "2023-12-31"),
    ]
    facts = _annual_cf_net_income_facts() + [
        _fact("c2k-bad", "bad", name="us-gaap:CashCashEquivalentsAtCarryingValue", value="10"),
        _fact("c2k-b24", "b24", name="us-gaap:CashCashEquivalentsAtCarryingValue", value="9"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX):
        _reconstruct(
            html,
            facts,
            contexts,
            statement_type="cash_flow",
            title=CF_TITLE,
            role=_CF_ROLE,
            presentation_arcs=_cash_presentation_arcs(preferred=_LABEL_PERIOD_START),
        )


def test_r7_assets_instant_under_wrong_income_column_refuses() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="3">{INCOME_TITLE}</td></tr>
      <tr><td>Line</td><td>December 31, 2025</td><td>December 31, 2024</td></tr>
      <tr><td>Revenues</td><td>{_ix("y25", "c2k-r25")}</td><td>{_ix("y24", "c2k-r24")}</td></tr>
      <tr><td>Assets</td><td>{_ix("ast", "c2k-ast", name="us-gaap:Assets", value="500")}</td><td></td></tr>
    </table>
    </body></html>
    """
    contexts = [
        _duration("y25", "2025-01-01", "2025-12-31"),
        _duration("y24", "2024-01-01", "2024-12-31"),
        _instant("ast", "2024-12-31"),
    ]
    facts = [
        _fact("c2k-r25", "y25"),
        _fact("c2k-r24", "y24"),
        _fact("c2k-ast", "ast", name="us-gaap:Assets", value="500"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX):
        _reconstruct(html, facts, contexts)


def _cash_position_case(
    beginning_label: str, ending_label: str
) -> tuple[str, list[dict], list[dict]]:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Six Months Ended June 30</td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td>(Dollars in millions)</td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("h6m25", "c2p-ni25", name="us-gaap:NetIncomeLoss")}</td><td></td><td>{_ix("h6m24", "c2p-ni24", name="us-gaap:NetIncomeLoss")}</td></tr>
      <tr><td>{beginning_label}</td><td>{_ix("b2024", "c2p-b25", name="us-gaap:CashCashEquivalentsAtCarryingValue")}</td><td></td><td>{_ix("b2023", "c2p-b24", name="us-gaap:CashCashEquivalentsAtCarryingValue")}</td></tr>
      <tr><td>{ending_label}</td><td>{_ix("e2025", "c2p-e25", name="us-gaap:CashCashEquivalentsAtCarryingValue")}</td><td></td><td>{_ix("e2024", "c2p-e24", name="us-gaap:CashCashEquivalentsAtCarryingValue")}</td></tr>
    </table>
    </body></html>
    """
    contexts = [
        _duration("h6m25", "2025-01-01", "2025-06-30"),
        _duration("h6m24", "2024-01-01", "2024-06-30"),
        _instant("b2024", "2024-12-31"),
        _instant("b2023", "2023-12-31"),
        _instant("e2025", "2025-06-30"),
        _instant("e2024", "2024-06-30"),
    ]
    facts = [
        _fact("c2p-ni25", "h6m25", name="us-gaap:NetIncomeLoss"),
        _fact("c2p-ni24", "h6m24", name="us-gaap:NetIncomeLoss"),
        _fact("c2p-b25", "b2024", name="us-gaap:CashCashEquivalentsAtCarryingValue"),
        _fact("c2p-b24", "b2023", name="us-gaap:CashCashEquivalentsAtCarryingValue"),
        _fact("c2p-e25", "e2025", name="us-gaap:CashCashEquivalentsAtCarryingValue"),
        _fact("c2p-e24", "e2024", name="us-gaap:CashCashEquivalentsAtCarryingValue"),
    ]
    return html, facts, contexts


_CASH_TWICE_ARCS = [
    ("cashroot", "cashbeg", _LABEL_PERIOD_START),
    ("cashroot", "cashend", _LABEL_PERIOD_END),
]


def test_r7_cash_position_instants_agree_with_their_duration_columns() -> None:
    # The canonical cash-flow positions: an instant at the column end (ending
    # cash) and at the day before the column start (beginning cash) agree. The
    # beginning row carries its periodStartLabel role, as real filings do.
    html, facts, contexts = _cash_position_case(
        "Cash and cash equivalents at beginning of period",
        "Cash and cash equivalents at end of period",
    )
    result = _reconstruct(
        html,
        facts,
        contexts,
        statement_type="cash_flow",
        title=CF_TITLE,
        role=_CF_ROLE,
        presentation_arcs=_CASH_TWICE_ARCS,
    )
    assert [c["start"] for c in result["columns"]] == ["2025-01-01", "2024-01-01"]
    assert result["row_count"] == 3
    assert [row["preferred_label_role"] for row in result["rows"][1:]] == [
        _LABEL_PERIOD_START,
        _LABEL_PERIOD_END,
    ]


def test_r7_beginning_cash_without_a_start_role_refuses() -> None:
    # The anchor follows the presentation role, never the label: a beginning
    # balance whose row carries no periodStartLabel is held to the column end.
    html, facts, contexts = _cash_position_case(
        "Cash and cash equivalents at beginning of period",
        "Cash and cash equivalents at end of period",
    )
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: .*period anchor"):
        _reconstruct(
            html,
            facts,
            contexts,
            statement_type="cash_flow",
            title=CF_TITLE,
            role=_CF_ROLE,
        )


def test_r7_concept_presented_twice_maps_rows_to_occurrences_in_order() -> None:
    # Labels that name neither "beginning" nor "ending": the k-th displayed
    # row of the concept takes the k-th presentation occurrence's role.
    html, facts, contexts = _cash_position_case("Cash, opening", "Cash, closing")
    result = _reconstruct(
        html,
        facts,
        contexts,
        statement_type="cash_flow",
        title=CF_TITLE,
        role=_CF_ROLE,
        presentation_arcs=_CASH_TWICE_ARCS,
    )
    opening, closing = result["rows"][1], result["rows"][2]
    assert opening["preferred_label_role"] == _LABEL_PERIOD_START
    assert closing["preferred_label_role"] == _LABEL_PERIOD_END
    assert [cell["value"] for cell in closing["cells"]] == ["100", "100"]


def test_r7_closing_cash_under_a_start_role_refuses() -> None:
    # Presentation order reversed: the second displayed row now carries the
    # start role, so its column-end instants no longer sit at its anchor.
    html, facts, contexts = _cash_position_case("Cash, opening", "Cash, closing")
    with pytest.raises(StatementGraphError, match=_R7_PREFIX):
        _reconstruct(
            html,
            facts,
            contexts,
            statement_type="cash_flow",
            title=CF_TITLE,
            role=_CF_ROLE,
            presentation_arcs=[
                ("cashroot", "cashend", _LABEL_PERIOD_END),
                ("cashroot", "cashbeg", _LABEL_PERIOD_START),
            ],
        )


# --- R7: a concept displayed a different number of times than presented ---

_CASH = "us-gaap:CashCashEquivalentsAtCarryingValue"
_LABEL_NEGATED_PERIOD_START = "http://www.xbrl.org/2009/role/negatedPeriodStartLabel"
_BEGIN_CASH = "Cash and cash equivalents at beginning of year"
_END_CASH = "Cash and cash equivalents at end of year"

_ANNUAL_CASH_CONTEXTS = [
    _duration("y25", "2025-01-01", "2025-12-31"),
    _duration("y24", "2024-01-01", "2024-12-31"),
    _instant("i2025", "2025-12-31"),
    _instant("i2024", "2024-12-31"),
    _instant("i2023", "2023-12-31"),
]


def _annual_cash_html(rows: str) -> str:
    return f"""
    <html><body>
    <table>
      <tr><td colspan="3">{CF_TITLE}</td></tr>
      <tr><td>Years Ended December 31,</td><td colspan="2"></td></tr>
      <tr><td></td><td>2025</td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("y25", "c2n-ni25", name="us-gaap:NetIncomeLoss")}</td><td>{_ix("y24", "c2n-ni24", name="us-gaap:NetIncomeLoss")}</td></tr>
      {rows}
    </table>
    </body></html>
    """


def _cash_row(label: str, first: str, second: str) -> str:
    return f"<tr><td>{label}</td><td>{first}</td><td>{second}</td></tr>"


def _cash_ix(context: str, fact_id: str, value: str) -> str:
    return _ix(context, fact_id, name=_CASH, value=value)


_BEGIN_ROW = _cash_row(
    _BEGIN_CASH, _cash_ix("i2024", "c2n-b25", "300"), _cash_ix("i2023", "c2n-b24", "200")
)
_END_ROW = _cash_row(
    _END_CASH, _cash_ix("i2025", "c2n-e25", "400"), _cash_ix("i2024", "c2n-e24", "300")
)
# An "end of year" row whose current-year cell is an untagged dash: positional
# binding places its one tagged fact, the prior year-end instant, under 2025.
_SHIFTED_END_ROW = _cash_row(_END_CASH, "&#8212;", _cash_ix("i2024", "c2n-e24", "300"))


def _annual_cash_facts(*fact_ids: str) -> list[dict]:
    contexts = {
        "c2n-b25": ("i2024", "300"),
        "c2n-b24": ("i2023", "200"),
        "c2n-e25": ("i2025", "400"),
        "c2n-e24": ("i2024", "300"),
        "c2n-r24": ("i2024", "300"),
    }
    facts = [
        _fact("c2n-ni25", "y25", name="us-gaap:NetIncomeLoss"),
        _fact("c2n-ni24", "y24", name="us-gaap:NetIncomeLoss"),
    ]
    for fact_id in fact_ids:
        context, value = contexts[fact_id]
        facts.append(_fact(fact_id, context, name=_CASH, value=value))
    return facts


def _reconstruct_annual_cash(
    rows: str,
    facts: list[dict],
    presentation_arcs: list[tuple[str, str, str | None]],
) -> dict:
    return _reconstruct(
        _annual_cash_html(rows),
        facts,
        _ANNUAL_CASH_CONTEXTS,
        statement_type="cash_flow",
        title=CF_TITLE,
        role=_CF_ROLE,
        presentation_arcs=presentation_arcs,
    )


def test_r7_cash_presented_twice_displayed_twice_reconstructs() -> None:
    result = _reconstruct_annual_cash(
        _BEGIN_ROW + _END_ROW,
        _annual_cash_facts("c2n-b25", "c2n-b24", "c2n-e25", "c2n-e24"),
        _CASH_TWICE_ARCS,
    )
    beginning, ending = result["rows"][1], result["rows"][2]
    assert [cell["value"] for cell in beginning["cells"]] == ["300", "200"]
    assert [cell["value"] for cell in ending["cells"]] == ["400", "300"]


def test_r7_extra_displayed_row_of_a_twice_presented_concept_refuses() -> None:
    # Displayed three times, presented twice: the repeated "end of year" row
    # has no presentation occurrence of its own, so it takes no start role and
    # its shifted prior year-end instant must not pass as the 2025 balance.
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: .*period anchor"):
        _reconstruct_annual_cash(
            _BEGIN_ROW
            + _END_ROW
            + _cash_row(_END_CASH, "&#8212;", _cash_ix("i2024", "c2n-r24", "300")),
            _annual_cash_facts("c2n-b25", "c2n-b24", "c2n-e25", "c2n-e24", "c2n-r24"),
            _CASH_TWICE_ARCS,
        )


def test_r7_single_shifted_row_of_a_twice_presented_concept_refuses() -> None:
    # Displayed once, presented twice: the row cannot claim the first
    # occurrence's start role, so the prior year-end instant shifted under
    # 2025 is held to the column end and refuses.
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: .*period anchor"):
        _reconstruct_annual_cash(
            _SHIFTED_END_ROW,
            _annual_cash_facts("c2n-e24"),
            _CASH_TWICE_ARCS,
        )


def test_r7_single_unshifted_row_of_a_twice_presented_concept_reconstructs() -> None:
    # The honest version of the row above anchors at each column end.
    result = _reconstruct_annual_cash(
        _END_ROW,
        _annual_cash_facts("c2n-e25", "c2n-e24"),
        _CASH_TWICE_ARCS,
    )
    ending = result["rows"][1]
    assert [cell["value"] for cell in ending["cells"]] == ["400", "300"]
    assert [cell["period"]["end"] for cell in ending["cells"]] == [
        "2025-12-31", "2024-12-31",
    ]


def test_r7_two_rows_selecting_the_same_start_occurrence_refuse() -> None:
    # Ending cash presented before beginning cash: the "beginning" label picks
    # the start occurrence and the shifted "end of year" row's ordinal picks it
    # again. Counts match, but both rows cannot carry the start role, so the
    # shifted prior year-end instant must not pass as the 2025 balance.
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: .*period anchor"):
        _reconstruct_annual_cash(
            _BEGIN_ROW + _SHIFTED_END_ROW,
            _annual_cash_facts("c2n-b25", "c2n-b24", "c2n-e24"),
            [
                ("cashroot", "cashend", _LABEL_PERIOD_END),
                ("cashroot", "cashbeg", _LABEL_PERIOD_START),
            ],
        )


def test_r7_shifted_end_row_displayed_before_beginning_row_refuses() -> None:
    # Standard presentation order, but the shifted "end of year" row comes
    # first: its ordinal picks the start occurrence and the "beginning" label
    # picks it again, so neither row may anchor at the day before the start.
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: .*period anchor"):
        _reconstruct_annual_cash(
            _SHIFTED_END_ROW + _BEGIN_ROW,
            _annual_cash_facts("c2n-b25", "c2n-b24", "c2n-e24"),
            _CASH_TWICE_ARCS,
        )


def test_r7_beginning_cash_with_negated_period_start_label_reconstructs() -> None:
    result = _reconstruct_annual_cash(
        _BEGIN_ROW + _END_ROW,
        _annual_cash_facts("c2n-b25", "c2n-b24", "c2n-e25", "c2n-e24"),
        [
            ("cashroot", "cashbeg", _LABEL_NEGATED_PERIOD_START),
            ("cashroot", "cashend", _LABEL_PERIOD_END),
        ],
    )
    beginning = result["rows"][1]
    assert beginning["preferred_label_role"] == _LABEL_NEGATED_PERIOD_START
    assert [cell["value"] for cell in beginning["cells"]] == ["300", "200"]


def test_r7_dimensioned_fact_with_agreeing_period_stays() -> None:
    html = _glued_bs_html()
    dims = [
        {
            "kind": "explicit",
            "dimension_qname": "{http://fasb.org/srt/2023}ProductOrServiceAxis",
            "member_qname": "{http://synthetic.example}ConsolidatedVIEsMember",
        }
    ]
    contexts = [
        _instant("c2025", "2025-06-30", dims=dims),
        _instant("c2024", "2024-12-31"),
        _instant("c2025n", "2025-06-30"),
        _instant("c2024n", "2024-12-31"),
    ]
    facts = [
        _fact("c2-bs-25", "c2025", name="us-gaap:OtherAssets"),
        _fact("c2-bs-24", "c2024", name="us-gaap:OtherAssets"),
        _fact("c2-bs-t25", "c2025n", name="us-gaap:Assets"),
        _fact("c2-bs-t24", "c2024n", name="us-gaap:Assets"),
    ]
    result = _reconstruct(
        html, facts, contexts, statement_type="balance_sheet", title=BS_TITLE,
        role="http://synthetic.example/role/Balance",
    )
    assert result["statement_type"] == "balance_sheet"
    assert [cell["dimensions"] for cell in result["rows"][1]["cells"]] == [
        [
            {
                "kind": "explicit",
                "dimension_qname": "{http://fasb.org/srt/2023}ProductOrServiceAxis",
                "member_qname": "{http://synthetic.example}ConsolidatedVIEsMember",
            }
        ],
        [],
    ]


def test_r7_duration_fact_under_an_instant_column_refuses() -> None:
    html = _glued_bs_html()
    contexts = [
        _duration("d2025", "2025-01-01", "2025-06-30"),
        _instant("c2024", "2024-12-31"),
        _instant("c2025n", "2025-06-30"),
        _instant("c2024n", "2024-12-31"),
    ]
    facts = [
        _fact("c2-bs-25", "d2025", name="us-gaap:OtherAssets"),
        _fact("c2-bs-24", "c2024", name="us-gaap:OtherAssets"),
        _fact("c2-bs-t25", "c2025n", name="us-gaap:Assets"),
        _fact("c2-bs-t24", "c2024n", name="us-gaap:Assets"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: "):
        _reconstruct(
            html, facts, contexts, statement_type="balance_sheet", title=BS_TITLE,
            role="http://synthetic.example/role/Balance",
        )


def test_r7_instant_fact_with_the_wrong_date_under_an_instant_column_refuses() -> None:
    html = _glued_bs_html()
    contexts = [
        _instant("c2025", "2025-06-29"),
        _instant("c2024", "2024-12-31"),
        _instant("c2025n", "2025-06-30"),
        _instant("c2024n", "2024-12-31"),
    ]
    facts = [
        _fact("c2-bs-25", "c2025", name="us-gaap:OtherAssets"),
        _fact("c2-bs-24", "c2024", name="us-gaap:OtherAssets"),
        _fact("c2-bs-t25", "c2025n", name="us-gaap:Assets"),
        _fact("c2-bs-t24", "c2024n", name="us-gaap:Assets"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: "):
        _reconstruct(
            html, facts, contexts, statement_type="balance_sheet", title=BS_TITLE,
            role="http://synthetic.example/role/Balance",
        )


def test_r7_untagged_cell_in_a_dated_column_stays_as_today() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{CF_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Six Months Ended June 30</td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td>(Dollars in millions)</td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Net income</td><td>{_ix("h6m25", "c2u-ni25", name="us-gaap:NetIncomeLoss")}</td><td>n/a</td><td>{_ix("h6m24", "c2u-ni24", name="us-gaap:NetIncomeLoss")}</td></tr>
    </table>
    </body></html>
    """
    contexts = [
        _duration("h6m25", "2025-01-01", "2025-06-30"),
        _duration("h6m24", "2024-01-01", "2024-06-30"),
    ]
    facts = [
        _fact("c2u-ni25", "h6m25", name="us-gaap:NetIncomeLoss"),
        _fact("c2u-ni24", "h6m24", name="us-gaap:NetIncomeLoss"),
    ]
    result = _reconstruct(
        html,
        facts,
        contexts,
        statement_type="cash_flow",
        title=CF_TITLE,
        role="http://synthetic.example/role/CashFlow",
    )
    cells = result["rows"][0]["cells"]
    assert [cell["quality_state"] for cell in cells] == ["available", "available"]
    assert cells[0]["value"] == "100"


def test_r7_same_fact_twice_with_contradicting_contexts_refuses() -> None:
    html = _grouped_income_html(
        fact_row=_grouped_income_facts_rows(),
    )
    html = html.replace(
        "</table>",
        "<tr><td>Interest income (comparative repeat)</td><td>"
        + _ix("q3m24", "c2r-rep0")
        + "</td><td>"
        + _ix("q3m25", "c2r-rep1")
        + '</td><td>$</td><td>'
        + _ix("h6m25", "c2r-rep2")
        + "</td><td>"
        + _ix("h6m24", "c2r-rep3")
        + "</td><td></td></tr></table>",
    )
    contexts = _GROUPED_INCOME_CONTEXTS
    facts = [
        _fact("c2r-q25", "q3m25"),
        _fact("c2r-q24", "q3m24"),
        _fact("c2r-h25", "h6m25"),
        _fact("c2r-h24", "h6m24"),
        _fact("c2r-rep0", "q3m24"),
        _fact("c2r-rep1", "q3m25"),
        _fact("c2r-rep2", "h6m25"),
        _fact("c2r-rep3", "h6m24"),
    ]
    with pytest.raises(StatementGraphError, match=_R7_PREFIX + r"0: "):
        _reconstruct(html, facts, contexts)
