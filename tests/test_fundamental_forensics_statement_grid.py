"""FIF S0: displayed-statement table grid (rowspan/colspan, repeated rows)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.fundamental_forensics import disclosure_diff
from engine.fundamental_forensics import statement_graph
from engine.fundamental_forensics.statement_graph import (
    StatementGraphError,
    parse_displayed_primary_table,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "fundamental_forensics" / "synthetic_statement_tables"
TITLE = "SYNTHETIC STATEMENT OF OPERATIONS"
AAPL_10K = ROOT / "tests" / "fixtures" / "fundamental_forensics" / "aapl_10k_2025" / "members" / "aapl-20250927.htm"


def _load_case(name: str) -> tuple[str, dict]:
    html = (FIXTURE_DIR / f"{name}.htm").read_text(encoding="utf-8")
    expected = json.loads((FIXTURE_DIR / f"{name}.expected.json").read_text(encoding="utf-8"))
    return html, expected


def _projection(parsed: dict) -> dict:
    return {
        "columns_iso": parsed["columns_iso"],
        "rows": [
            {
                "label": row["label"],
                "order": row["order"],
                "abstract": row["abstract"],
                "rowspan_carry": row["rowspan_carry"],
                "value_fact_ids": [str(item.get("fact_id") or "") for item in row["value_facts"]],
            }
            for row in parsed["rows"]
        ],
    }


def test_span_helpers_are_disclosure_diff_imports() -> None:
    assert statement_graph._attribute_map is disclosure_diff._attribute_map
    assert statement_graph._span_attribute is disclosure_diff._span_attribute
    assert statement_graph._span_overflow is disclosure_diff._span_overflow


def test_repeat_rows_stay_distinct_with_distinct_order() -> None:
    html, expected = _load_case("syn_a09_repeat_rows")
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert _projection(parsed) == expected
    assert [row["label"] for row in parsed["rows"]] == ["Sales", "Sales"]
    assert [row["order"] for row in parsed["rows"]] == [0, 1]


def test_rowspan_label_carries_and_keeps_column_assignment() -> None:
    html, expected = _load_case("syn_a09_rowspan_label")
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert _projection(parsed) == expected
    assert parsed["rows"][1]["rowspan_carry"] is True
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-cash-begin-2025",
        "syn-cash-begin-2024",
    ]
    assert [item["fact_id"] for item in parsed["rows"][1]["value_facts"]] == [
        "syn-cash-end-2025",
        "syn-cash-end-2024",
    ]


def test_colspan_period_group_maps_value_cells_to_dates() -> None:
    html, expected = _load_case("syn_a09_colspan_period_group")
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert _projection(parsed) == expected
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-rev-2025",
        "syn-rev-2024",
    ]


def test_colspan_spacer_parity_matches_source_order_assignment() -> None:
    html, expected = _load_case("syn_a09_colspan_spacer")
    parsed = parse_displayed_primary_table(html, title=TITLE)
    assert _projection(parsed) == expected
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-products-2025",
        "syn-products-2024",
    ]
    assert [item["fact_id"] for item in parsed["rows"][1]["value_facts"]] == [
        "syn-services-2025",
        "syn-services-2024",
    ]


def test_inconsistent_grid_is_refused() -> None:
    html = """
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr>
      <td>Line</td>
      <td>September 27, 2025</td>
      <td>September 28, 2024</td>
    </tr>
    <tr>
      <td>Anchor</td>
      <td rowspan="2">held</td>
      <td>right</td>
    </tr>
    <tr>
      <td colspan="2">overlap</td>
      <td>tail</td>
    </tr>
    </table>
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=r"^displayed statement layout unsupported:") as raised:
        parse_displayed_primary_table(html, title=TITLE)
    assert str(raised.value).startswith("displayed statement layout unsupported:")


def test_display_row_order_is_stable() -> None:
    html, expected = _load_case("syn_a09_repeat_rows")
    first = _projection(parse_displayed_primary_table(html, title=TITLE))
    second = _projection(parse_displayed_primary_table(html, title=TITLE))
    assert first == second == expected
    assert [row["order"] for row in first["rows"]] == [0, 1]


def test_aapl_operations_spacer_grid_preserves_row_and_fact_counts() -> None:
    html = AAPL_10K.read_text(encoding="utf-8")
    parsed = parse_displayed_primary_table(html, title="CONSOLIDATED STATEMENTS OF OPERATIONS")
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-28", "2023-09-30"]
    assert len(parsed["rows"]) == 24
    assert [len(row["value_facts"]) for row in parsed["rows"]] == [
        0, 3, 3, 3, 0, 3, 3, 3, 3, 0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 3, 3, 0, 3, 3,
    ]
    assert [item["fact_id"] for item in parsed["rows"][1]["value_facts"]] == ["f-72", "f-73", "f-74"]
