"""Bare-year displayed columns composed from the filing's document period end."""
from __future__ import annotations

import pytest

from engine.fundamental_forensics import statement_graph
from engine.fundamental_forensics.statement_graph import (
    StatementGraphError,
    parse_displayed_primary_table,
)

_TITLE = "Consolidated Statements of Operations"
_DEI = "{http://xbrl.sec.gov/dei/2024}"


def _statement_table(header_rows: str, *, values: int = 2) -> str:
    """Lane C shape with caller-supplied header rows over one fact row."""
    cells = "".join(
        f'<td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d{index}" '
        f'id="ywm-ni-{index}" unitRef="usd" decimals="-6" scale="6">{100 - index}'
        "</ix:nonFraction></td>"
        for index in range(values)
    )
    return f"""
    <table>
    <tr><td>{_TITLE}</td></tr>
    {header_rows}
    <tr><td>Net income</td>{cells}</tr>
    </table>
    """


def _year_row(*years: str, lead: str = "") -> str:
    return f"<tr><td>{lead}</td>" + "".join(f"<td>{year}</td>" for year in years) + "</tr>"


def _rows(parsed: dict) -> list[dict]:
    return [
        {
            "label": row["label"],
            "facts": [str(item.get("fact_id") or "") for item in row["value_facts"]],
        }
        for row in parsed["rows"]
    ]


def _refused(html: str, period_end: str | None) -> StatementGraphError:
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_TITLE, period_end=period_end)
    return excinfo.value


def test_ywm1_bare_year_row_takes_document_period_month_day() -> None:
    html = _statement_table(_year_row("2025", "2024"))
    parsed = parse_displayed_primary_table(html, title=_TITLE, period_end="2025-09-27")
    # Each year takes the document period end's month-day. A 52/53-week fiscal
    # year can end on a different day in the prior year; that column then fails
    # its exact context binding downstream instead of serving a wrong period.
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-27"]
    assert parsed["columns_source"] == "composed_bare_year_row"
    assert _rows(parsed) == [{"label": "Net income", "facts": ["ywm-ni-0", "ywm-ni-1"]}]


def test_ywm1_caption_led_year_row_composes() -> None:
    html = _statement_table(_year_row("2025", "2024", lead="(In millions)"))
    parsed = parse_displayed_primary_table(html, title=_TITLE, period_end="2025-12-31")
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31"]
    assert parsed["columns_source"] == "composed_bare_year_row"
    assert [row["label"] for row in parsed["rows"]] == ["Net income"]


def test_ywm1_three_year_row_composes() -> None:
    html = _statement_table(_year_row("2025", "2024", "2023"), values=3)
    parsed = parse_displayed_primary_table(html, title=_TITLE, period_end="2025-12-31")
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31", "2023-12-31"]
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ywm-ni-0", "ywm-ni-1", "ywm-ni-2"]}
    ]


def test_ywm1_blank_row_above_and_label_row_below_keep_their_places() -> None:
    html = _statement_table(
        "<tr><td></td><td></td><td></td></tr>"
        + _year_row("2025", "2024")
        + "<tr><td>Revenue</td><td></td><td></td></tr>"
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE, period_end="2025-06-30")
    assert parsed["columns_iso"] == ["2025-06-30", "2024-06-30"]
    assert [row["label"] for row in parsed["rows"]] == ["Revenue", "Net income"]
    assert parsed["rows"][0]["abstract"] is True


def test_ywm1_without_period_end_bare_years_still_refuse() -> None:
    html = _statement_table(_year_row("2025", "2024"))
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_TITLE)
    assert excinfo.value.refusal_code == "displayed_columns_absent"


def test_ywm1_full_date_header_unchanged_by_period_end() -> None:
    html = _statement_table(
        "<tr><td>Line</td><td>September 27, 2025</td><td>September 28, 2024</td></tr>"
    )
    with_end = parse_displayed_primary_table(html, title=_TITLE, period_end="2025-12-31")
    without = parse_displayed_primary_table(html, title=_TITLE)
    assert with_end == without
    assert with_end["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert "columns_source" not in with_end


def test_ywm1_printed_month_day_banner_wins_over_period_end() -> None:
    html = _statement_table(
        "<tr><td></td><td>Fiscal Year Ended September 27,</td></tr>"
        + _year_row("2025", "2024")
    )
    parsed = parse_displayed_primary_table(html, title=_TITLE, period_end="2025-09-30")
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-27"]
    assert parsed["columns_source"] != "composed_bare_year_row"


@pytest.mark.parametrize(
    "banner_row",
    [
        "<tr><td></td><td>Fiscal years (September)</td></tr>",
        "<tr><td></td><td>Three Months Ended</td></tr>",
        "<tr><td></td><td>Fifty-two weeks</td></tr>",
        "<tr><td></td><td>Fourth Quarter</td></tr>",
        "<tr><td></td><td>Twelve months</td></tr>",
    ],
)
def test_ywm1_period_words_anywhere_in_header_refuse(banner_row: str) -> None:
    html = _statement_table(banner_row + _year_row("2025", "2024"))
    assert _refused(html, "2025-09-27").refusal_code == "displayed_columns_absent"


def test_ywm1_non_year_cell_on_the_year_row_refuses() -> None:
    # A word beside the years makes the row not a bare-year row at all, so the
    # composer never sees it; the period-word guard itself is exercised by the
    # banner cases above (each one composes if the guard is removed).
    html = _statement_table(_year_row("2025", "2024", lead="Quarter"))
    assert _refused(html, "2025-09-27").refusal_code == "displayed_columns_absent"


@pytest.mark.parametrize(
    ("header_rows", "period_end", "values"),
    [
        (_year_row("2024", "2023"), "2025-09-27", 2),
        (_year_row("2025", "2024") + _year_row("2025", "2024"), "2025-09-27", 2),
        (_year_row("2025"), "2025-09-27", 1),
        (_year_row("2025", "2025"), "2025-09-27", 2),
        (_year_row("2024", "2023"), "2024-02-29", 2),
        (_year_row("2025", "2024", lead="Line"), "2025-09-27", 2),
        (_year_row("2025", "2024"), "not-a-date", 2),
    ],
    ids=[
        "latest-year-not-period-end-year",
        "two-year-rows",
        "single-year",
        "repeated-year",
        "leap-day-not-real-in-prior-year",
        "label-beside-years",
        "unreadable-period-end",
    ],
)
def test_ywm1_unsafe_bare_year_shapes_refuse(
    header_rows: str, period_end: str, values: int
) -> None:
    html = _statement_table(header_rows, values=values)
    assert _refused(html, period_end).refusal_code == "displayed_columns_absent"


_CONTEXTS = {
    "c0": {"context_id": "c0", "dimensions": []},
    "c1": {"context_id": "c1", "dimensions": []},
    "cdim": {"context_id": "cdim", "dimensions": [{"dimension": "x", "member": "y"}]},
}


def _dped(
    *,
    normalized: str | None = None,
    raw: str | None = None,
    context: str = "c0",
    kind: str = "nonnumeric",
    namespace: str = _DEI,
) -> dict:
    return {
        "concept_qname": f"{namespace}DocumentPeriodEndDate",
        "kind": kind,
        "context_ref": context,
        "raw_value": raw,
        "normalized_value": normalized,
    }


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        ([_dped(normalized="2025-09-27", raw="September 27, 2025")], "2025-09-27"),
        ([_dped(raw="September 27, 2025")], "2025-09-27"),
        ([_dped(raw="2025-09-27")], "2025-09-27"),
        (
            [_dped(normalized="2025-09-27"), _dped(normalized="2025-09-27", context="c1")],
            "2025-09-27",
        ),
        (
            [_dped(normalized="2025-09-27"), _dped(normalized="2024-12-31", context="cdim")],
            "2025-09-27",
        ),
        (
            [_dped(normalized="2025-09-27"), _dped(normalized="2024-12-31", context="c1")],
            None,
        ),
        ([_dped(normalized="2025-09-27", kind="numeric")], None),
        (
            [_dped(normalized="2025-09-27", namespace="{http://fasb.org/us-gaap/2024}")],
            None,
        ),
        ([_dped(raw="FY2025")], None),
        ([_dped(normalized="2025-09-27", context="missing")], None),
        ([], None),
    ],
    ids=[
        "iso-normalized",
        "printed-raw",
        "iso-raw",
        "agreeing-contexts",
        "dimensioned-ignored",
        "two-dates",
        "numeric-kind-ignored",
        "non-dei-namespace-ignored",
        "unreadable-value",
        "unknown-context-ignored",
        "no-facts",
    ],
)
def test_ywm1_document_period_end(facts: list[dict], expected: str | None) -> None:
    assert statement_graph._document_period_end(facts, _CONTEXTS) == expected
