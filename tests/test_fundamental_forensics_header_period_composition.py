"""FIF displayed header period composition (DEC:FIF-DISPLAYED-HEADER-PERIOD-COMPOSITION-20261103).

Covers the three source-observed annual header shapes that previously left a
statement with no displayed columns: a month-day banner printed in the same
row as its bare years, a banner reaching its year row across fully blank
rows, and a year row that leads with a whole-cell unit caption. Also covers
the group-banner grammar that keeps "Three Months Ended June 30," (trailing
comma) and the glued "EndedJune 30" on the duration-group composer. Every
composed column still binds to its own facts' filing contexts downstream.
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

_COLUMNS_ABSENT = r"^displayed statement columns are absent"


def _ix(context: str, fact_id: str, *, name: str = "us-gaap:Revenues", value: str = "100") -> str:
    return (
        f'<ix:nonFraction name="{name}" contextRef="{context}" id="{fact_id}" '
        f'unitRef="usd" decimals="-6" scale="6">{value}</ix:nonFraction>'
    )


def _income_html(header_rows: str, *, first: str = "y1", second: str = "y2") -> str:
    """An income statement whose header rows are supplied verbatim over two fact columns."""
    return f"""
    <html><body>
    <table>
      <tr><td colspan="3">{INCOME_TITLE}</td></tr>
      {header_rows}
      <tr><td>Revenues</td><td>{_ix(first, "hp-r1")}</td><td>{_ix(second, "hp-r2")}</td></tr>
    </table>
    </body></html>
    """


def _bac_bs_html(*, banner: str = "December 31", gap: str = "<tr><td></td><td></td><td></td><td></td><td></td></tr>",
                 year_row: str | None = None) -> str:
    """The BAC 10-K balance-sheet shape: banner / blank row / caption-led year row."""
    years = (
        '<tr><td>(Dollars in millions)</td><td colspan="2">2025</td><td colspan="2">2024</td></tr>'
        if year_row is None
        else year_row
    )
    return f"""
    <html><body>
    <table>
      <tr><td colspan="5">{BS_TITLE}</td></tr>
      <tr><td></td><td colspan="4">{banner}</td></tr>
      {gap}
      {years}
      <tr><td>Assets</td><td></td><td></td><td></td><td></td></tr>
      <tr><td>Cash and due from banks</td><td>$</td><td>{_ix("c2025", "hp-bs-25")}</td><td>$</td><td>{_ix("c2024", "hp-bs-24")}</td></tr>
      <tr><td>Total assets</td><td colspan="2">{_ix("c2025", "hp-bs-t25", name="us-gaap:Assets", value="200")}</td><td colspan="2">{_ix("c2024", "hp-bs-t24", name="us-gaap:Assets", value="180")}</td></tr>
    </table>
    </body></html>
    """


def _grouped_html(banners: tuple[str, str]) -> str:
    return f"""
    <html><body>
    <table>
      <tr><td colspan="7">{INCOME_TITLE}</td></tr>
      <tr><td></td><td colspan="3">{banners[0]}</td><td colspan="3">{banners[1]}</td></tr>
      <tr><td>(In millions, except per share information)</td><td>2025</td><td></td><td>2024</td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Interest income</td><td>$</td><td>{_ix("q3m25", "hp-q25")}</td><td>{_ix("q3m24", "hp-q24")}</td><td>$</td><td>{_ix("h6m25", "hp-h25")}</td><td>{_ix("h6m24", "hp-h24")}</td></tr>
    </table>
    </body></html>
    """


# --- Same-row banner: the banner and its years print in one header row ---


def test_same_row_banner_with_unit_text_composes() -> None:
    html = _income_html(
        "<tr><td>years ended December 31 (in millions, except per share data)</td>"
        "<td>2024</td><td>2023</td></tr>"
    )
    parsed = parse_displayed_primary_table(html, title=INCOME_TITLE)
    assert parsed["columns_source"] == "composed_same_row"
    assert parsed["columns_iso"] == ["2024-12-31", "2023-12-31"]
    assert [f["fact_id"] for f in parsed["rows"][0]["value_facts"]] == ["hp-r1", "hp-r2"]


def test_same_row_banner_under_a_caption_row_composes() -> None:
    html = _income_html(
        "<tr><td>(Dollars in millions, except per share data)</td><td></td><td></td></tr>"
        "<tr><td>Year Ended December 31,</td><td>2025</td><td>2024</td></tr>"
    )
    parsed = parse_displayed_primary_table(html, title=INCOME_TITLE)
    assert parsed["columns_source"] == "composed_same_row"
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]


def test_same_row_banner_keeps_ascending_display_order() -> None:
    html = _income_html("<tr><td>Year Ended April 30,</td><td>2023</td><td>2024</td></tr>")
    parsed = parse_displayed_primary_table(html, title=INCOME_TITLE)
    assert parsed["columns_source"] == "composed_same_row"
    assert parsed["columns_iso"] == ["2023-04-30", "2024-04-30"]


@pytest.mark.parametrize(
    "header",
    [
        # Two distinct month-days in the lead cell.
        "<tr><td>Years ended December 31 and June 30</td><td>2024</td><td>2023</td></tr>",
        # The lead already carries a full date.
        "<tr><td>As of December 31, 2024</td><td>2024</td><td>2023</td></tr>",
        # A non-year cell among the years.
        "<tr><td>Years ended December 31</td><td>2024</td><td>Restated</td></tr>",
        # Only one year.
        "<tr><td>Years ended December 31</td><td>2024</td><td></td></tr>",
        # Not a real calendar date.
        "<tr><td>Years ended February 30</td><td>2024</td><td>2023</td></tr>",
        # Day zero is not a calendar day.
        "<tr><td>Years ended December 0</td><td>2024</td><td>2023</td></tr>",
    ],
)
def test_same_row_misforms_keep_the_refusal(header: str) -> None:
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(_income_html(header), title=INCOME_TITLE)


def test_same_row_group_banner_is_not_a_same_row_banner() -> None:
    html = _income_html("<tr><td>Three Months Ended June 30</td><td>2025</td><td>2024</td></tr>")
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=INCOME_TITLE)


# --- Blank gap / leading unit caption between banner and years ---


def test_bac_balance_sheet_caption_year_row_across_a_blank_row_composes() -> None:
    parsed = parse_displayed_primary_table(_bac_bs_html(), title=BS_TITLE)
    assert parsed["columns_source"] == "composed_caption_year_row"
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]
    assert [f["fact_id"] for f in parsed["rows"][1]["value_facts"]] == ["hp-bs-25", "hp-bs-24"]


def test_blank_gap_without_caption_composes() -> None:
    html = _bac_bs_html(
        year_row='<tr><td></td><td colspan="2">2025</td><td colspan="2">2024</td></tr>'
    )
    parsed = parse_displayed_primary_table(html, title=BS_TITLE)
    assert parsed["columns_source"] == "composed_blank_gap_year_row"
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]


@pytest.mark.parametrize(
    "caption",
    [
        "In millions, except par value",
        "(in millions)",
        "(Dollars in millions, except per share data)",
        "(Millions of dollars)",
        "(Amounts in thousands)",
    ],
)
def test_caption_led_year_row_directly_under_the_banner_composes(caption: str) -> None:
    html = _bac_bs_html(
        banner="December 31,",
        gap="",
        year_row=f'<tr><td>{caption}</td><td colspan="2">2024</td><td colspan="2">2023</td></tr>',
    )
    parsed = parse_displayed_primary_table(html, title=BS_TITLE)
    assert parsed["columns_source"] == "composed_caption_year_row"
    assert parsed["columns_iso"] == ["2024-12-31", "2023-12-31"]


@pytest.mark.parametrize(
    "gap, year_row",
    [
        # A non-blank interstitial is never skipped.
        (
            "<tr><td>Unaudited</td><td></td><td></td><td></td><td></td></tr>",
            '<tr><td></td><td colspan="2">2025</td><td colspan="2">2024</td></tr>',
        ),
        # A caption alone on its own row is not skipped by this composition.
        (
            "<tr><td>(in millions)</td><td></td><td></td><td></td><td></td></tr>",
            '<tr><td></td><td colspan="2">2025</td><td colspan="2">2024</td></tr>',
        ),
        # The caption must lead the year row.
        ("", '<tr><td></td><td>2025</td><td>(in millions)</td><td colspan="2">2024</td></tr>'),
        # A lead that is not a unit caption.
        ("", '<tr><td>Unaudited</td><td colspan="2">2025</td><td colspan="2">2024</td></tr>'),
        # A non-year cell after the caption.
        ("", '<tr><td>(in millions)</td><td colspan="2">2025</td><td colspan="2">Restated</td></tr>'),
        # Fewer than two years.
        ("", '<tr><td>(in millions)</td><td colspan="2">2025</td><td colspan="2"></td></tr>'),
    ],
)
def test_gap_and_caption_misforms_keep_the_refusal(gap: str, year_row: str) -> None:
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(_bac_bs_html(gap=gap, year_row=year_row), title=BS_TITLE)


def test_caption_year_row_rejects_an_impossible_banner_date() -> None:
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(_bac_bs_html(banner="February 30"), title=BS_TITLE)


def test_two_distinct_banner_month_days_keep_the_refusal() -> None:
    html = _bac_bs_html(banner="December 31 and June 30")
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=BS_TITLE)


def test_leap_day_banner_composes_when_every_year_is_a_leap_year() -> None:
    html = _bac_bs_html(
        banner="February 29",
        year_row='<tr><td>(in millions)</td><td colspan="2">2024</td><td colspan="2">2020</td></tr>',
    )
    parsed = parse_displayed_primary_table(html, title=BS_TITLE)
    assert parsed["columns_source"] == "composed_caption_year_row"
    assert parsed["columns_iso"] == ["2024-02-29", "2020-02-29"]


def test_leap_day_banner_over_a_common_year_keeps_the_refusal() -> None:
    html = _bac_bs_html(
        banner="February 29",
        year_row='<tr><td>(in millions)</td><td colspan="2">2024</td><td colspan="2">2023</td></tr>',
    )
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=BS_TITLE)


def test_exact_year_row_directly_under_the_banner_keeps_its_own_tag() -> None:
    html = _bac_bs_html(
        gap="",
        year_row='<tr><td></td><td colspan="2">2025</td><td colspan="2">2024</td></tr>',
    )
    parsed = parse_displayed_primary_table(html, title=BS_TITLE)
    assert parsed["columns_source"] == "composed_year_row"
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]


# --- Group banners keep the duration-group composer ---


@pytest.mark.parametrize(
    "banners",
    [
        ("Three Months Ended June 30,", "Six Months Ended June 30,"),
        ("Three Months EndedJune 30", "Six Months EndedJune 30"),
    ],
)
def test_group_banner_variants_compose_duration_groups(banners: tuple[str, str]) -> None:
    parsed = parse_displayed_primary_table(_grouped_html(banners), title=INCOME_TITLE)
    assert parsed["columns_source"] == "composed_grouped_duration_year_row"
    assert parsed["columns_periods"] == [
        {"kind": "duration", "start": "2025-04-01", "end": "2025-06-30"},
        {"kind": "duration", "start": "2024-04-01", "end": "2024-06-30"},
        {"kind": "duration", "start": "2025-01-01", "end": "2025-06-30"},
        {"kind": "duration", "start": "2024-01-01", "end": "2024-06-30"},
    ]


def test_mixed_group_banner_row_over_a_blank_row_keeps_the_refusal() -> None:
    # One N-months-ended cell in the banner row keeps the new compositions off.
    html = _income_html(
        "<tr><td>Three Months Ended June 30</td><td>Year Ended June 30</td><td></td></tr>"
        "<tr><td></td><td></td><td></td></tr>"
        "<tr><td></td><td>2025</td><td>2024</td></tr>"
    )
    with pytest.raises(StatementGraphError, match=_COLUMNS_ABSENT):
        parse_displayed_primary_table(html, title=INCOME_TITLE)


def test_group_banner_over_a_blank_row_never_takes_the_caption_composition() -> None:
    html = f"""
    <html><body>
    <table>
      <tr><td colspan="4">{INCOME_TITLE}</td></tr>
      <tr><td></td><td colspan="3">Six Months Ended June 30,</td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td>(in millions)</td><td>2025</td><td></td><td>2024</td></tr>
      <tr><td>Revenues</td><td>$</td><td>{_ix("h6m25", "hp-g25")}</td><td>{_ix("h6m24", "hp-g24")}</td></tr>
    </table>
    </body></html>
    """
    parsed = parse_displayed_primary_table(html, title=INCOME_TITLE)
    assert parsed["columns_source"] == "composed_grouped_duration_year_row"
    assert parsed["columns_periods"] == [
        {"kind": "duration", "start": "2025-01-01", "end": "2025-06-30"},
        {"kind": "duration", "start": "2024-01-01", "end": "2024-06-30"},
    ]


# --- Composed columns still bind to the filing contexts ---


def _linkbases(role: str) -> dict[str, bytes]:
    presentation = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink">'
        f'<link:presentationLink xlink:role="{role}">'
        '<link:loc xlink:label="line" xlink:href="syn.htm#us-gaap_Revenues"/>'
        '<link:loc xlink:label="root" xlink:href="syn.htm#us-gaap_RevenuesAbstract"/>'
        '<link:presentationArc xlink:type="arc" xlink:from="root" xlink:to="line" order="1"/>'
        "</link:presentationLink></link:linkbase>"
    ).encode("utf-8")
    empty = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"/>'
    ).encode("utf-8")
    return {"presentation.xml": presentation, "label.xml": empty, "calculation.xml": empty}


def _duration(cid: str, start: str, end: str) -> dict:
    return {
        "context_id": cid,
        "period": {"kind": "duration", "start_date": start, "end_date": end},
        "dimensions": [],
        "entity": {"identifier": "0000000001"},
    }


def _instant(cid: str, day: str) -> dict:
    return {
        "context_id": cid,
        "period": {"kind": "instant", "instant_date": day},
        "dimensions": [],
        "entity": {"identifier": "0000000001"},
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


def _reconstruct(html: str, facts: list[dict], contexts: list[dict], *, statement_type: str,
                 title: str, role: str) -> dict:
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
    package = GoldenFilingPackage(
        manifest=manifest, members={"syn.htm": html.encode("utf-8"), **_linkbases(role)}
    )
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


_BS_ROLE = "http://synthetic.example/role/Balance"
_INCOME_ROLE = "http://synthetic.example/role/Income"

_BS_FACTS = [
    _fact("hp-bs-25", "c2025", name="us-gaap:CashAndDueFromBanks"),
    _fact("hp-bs-24", "c2024", name="us-gaap:CashAndDueFromBanks"),
    _fact("hp-bs-t25", "c2025", name="us-gaap:Assets", value="200"),
    _fact("hp-bs-t24", "c2024", name="us-gaap:Assets", value="180"),
]


def test_bac_balance_sheet_composed_columns_bind_to_filing_instants() -> None:
    contexts = [_instant("c2025", "2025-12-31"), _instant("c2024", "2024-12-31")]
    result = _reconstruct(
        _bac_bs_html(), _BS_FACTS, contexts,
        statement_type="balance_sheet", title=BS_TITLE, role=_BS_ROLE,
    )
    assert [(c["kind"], c["end"]) for c in result["columns"]] == [
        ("instant", "2025-12-31"),
        ("instant", "2024-12-31"),
    ]


def test_composed_balance_sheet_column_without_a_matching_instant_refuses() -> None:
    contexts = [_instant("c2025", "2025-06-30"), _instant("c2024", "2024-12-31")]
    with pytest.raises(StatementGraphError) as caught:
        _reconstruct(
            _bac_bs_html(), _BS_FACTS, contexts,
            statement_type="balance_sheet", title=BS_TITLE, role=_BS_ROLE,
        )
    assert caught.value.refusal_code == "displayed_column_period_unbound"


def test_same_row_income_columns_bind_to_filing_durations() -> None:
    html = _income_html(
        "<tr><td>years ended December 31 (in millions, except per share data)</td>"
        "<td>2024</td><td>2023</td></tr>"
    )
    contexts = [
        _duration("y1", "2024-01-01", "2024-12-31"),
        _duration("y2", "2023-01-01", "2023-12-31"),
    ]
    facts = [_fact("hp-r1", "y1"), _fact("hp-r2", "y2")]
    result = _reconstruct(
        html, facts, contexts, statement_type="income_statement", title=INCOME_TITLE, role=_INCOME_ROLE,
    )
    assert [(c["kind"], c["start"], c["end"]) for c in result["columns"]] == [
        ("duration", "2024-01-01", "2024-12-31"),
        ("duration", "2023-01-01", "2023-12-31"),
    ]


def test_same_row_income_column_ending_elsewhere_refuses() -> None:
    html = _income_html(
        "<tr><td>years ended December 31 (in millions, except per share data)</td>"
        "<td>2024</td><td>2023</td></tr>"
    )
    contexts = [
        _duration("y1", "2024-01-01", "2024-12-31"),
        _duration("y2", "2023-01-01", "2023-09-30"),
    ]
    facts = [_fact("hp-r1", "y1"), _fact("hp-r2", "y2")]
    with pytest.raises(StatementGraphError) as caught:
        _reconstruct(
            html, facts, contexts, statement_type="income_statement", title=INCOME_TITLE,
            role=_INCOME_ROLE,
        )
    assert caught.value.refusal_code == "displayed_column_period_unbound"
