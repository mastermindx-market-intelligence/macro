"""FIF S0/S0-b: displayed-statement table grid (rowspan/colspan, repeated rows, issuer-general headers)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from collectors.sec_filing_parser import parse_sec_filing_document
from engine.fundamental_forensics import disclosure_diff
from engine.fundamental_forensics import statement_graph
from engine.fundamental_forensics.financial_intelligence_packet import load_core_registry
from engine.fundamental_forensics.statement_graph import (
    GoldenFilingPackage,
    StatementGraphError,
    _iso_dates_from_text,
    _statement_identity,
    load_golden_aapl_package,
    parse_displayed_primary_table,
    reconstruct_statement,
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
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-ov-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
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


# --- S0-b: issuer-general headers (abbreviated dates, year rows, viewer chrome, declared identity) ---

SNOW_SHAPED_HTML = """
<html><body>
<div>SYNTHETIC STATEMENT OF OPERATIONS</div>
<table>
<tr><td></td><td></td><td></td><td></td><td></td><td></td></tr>
<tr><td colspan="2"></td><td colspan="4">Fiscal Year Ended January 31,</td></tr>
<tr><td colspan="2"></td><td>2026</td><td>2025</td><td>2024</td><td></td></tr>
<tr>
  <td colspan="2">Product revenue</td>
  <td><ix:nonFraction name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="c2026" id="syn-pr-2026" unitRef="usd" decimals="-6" scale="6">3,600</ix:nonFraction></td>
  <td><ix:nonFraction name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="c2025" id="syn-pr-2025" unitRef="usd" decimals="-6" scale="6">3,100</ix:nonFraction></td>
  <td><ix:nonFraction name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="c2024" id="syn-pr-2024" unitRef="usd" decimals="-6" scale="6">2,800</ix:nonFraction></td>
  <td></td>
</tr>
</table>
</body></html>
"""

BAC_VIEWER_SHAPED_HTML = """
<html><body>
<table class="report">
<tr>
  <th class="tl" colspan="1" rowspan="2"><div style="width: 200px;"><strong>Synthetic Statement of Income - USD ($)<br> shares in Millions, $ in Millions</strong></div></th>
  <th class="th" colspan="3">12 Months Ended</th>
</tr>
<tr>
  <th class="th"><div>Dec. 31, 2025</div></th>
  <th class="th"><div>Dec. 31, 2024</div></th>
  <th class="th"><div>Dec. 31, 2023</div></th>
</tr>
<tr class="ro">
  <td class="pl">Interest income</td>
  <td class="nump"><ix:nonFraction name="us-gaap:InterestAndDividendIncomeOperating" contextRef="c2025" id="syn-ii-2025" unitRef="usd" decimals="-6" scale="6">100</ix:nonFraction></td>
  <td class="nump"><ix:nonFraction name="us-gaap:InterestAndDividendIncomeOperating" contextRef="c2024" id="syn-ii-2024" unitRef="usd" decimals="-6" scale="6">90</ix:nonFraction></td>
  <td class="nump"><ix:nonFraction name="us-gaap:InterestAndDividendIncomeOperating" contextRef="c2023" id="syn-ii-2023" unitRef="usd" decimals="-6" scale="6">80</ix:nonFraction></td>
</tr>
<tr class="re">
  <td class="pl"><strong>Noninterest income</strong></td>
  <td class="text">&#160;</td>
  <td class="text">&#160;</td>
  <td class="text">&#160;</td>
</tr>
<tr class="rou">
  <td class="pl">Service charges</td>
  <td class="nump"><ix:nonFraction name="us-gaap:ServiceChargeFeeRevenue" contextRef="c2025" id="syn-sc-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
  <td class="nump"><ix:nonFraction name="us-gaap:ServiceChargeFeeRevenue" contextRef="c2024" id="syn-sc-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
  <td class="nump"><ix:nonFraction name="us-gaap:ServiceChargeFeeRevenue" contextRef="c2023" id="syn-sc-2023" unitRef="usd" decimals="-6" scale="6">8</ix:nonFraction></td>
</tr>
</table>
</body></html>
"""


def test_abbreviated_month_dates_parse_to_iso() -> None:
    assert _iso_dates_from_text("Dec. 31, 2025") == ["2025-12-31"]
    assert _iso_dates_from_text("Sept. 27, 2025") == ["2025-09-27"]
    assert _iso_dates_from_text("Sep 27, 2025") == ["2025-09-27"]
    assert _iso_dates_from_text("Dec 31, 2025") == ["2025-12-31"]


def test_full_name_dates_keep_behaviour_and_order() -> None:
    text = "September 27, 2025 and September 28, 2024 then September 30, 2023"
    assert _iso_dates_from_text(text) == ["2025-09-27", "2024-09-28", "2023-09-30"]


def test_month_lookalikes_do_not_match() -> None:
    assert _iso_dates_from_text("Decimal 31, 2025") == []
    assert _iso_dates_from_text("Decor. 31, 2025") == []
    assert _iso_dates_from_text("Janet 5, 2026") == []


def test_snow_shaped_year_row_header_composes_dated_columns() -> None:
    parsed = parse_displayed_primary_table(SNOW_SHAPED_HTML, title=TITLE)
    assert parsed["columns_iso"] == ["2026-01-31", "2025-01-31", "2024-01-31"]
    assert parsed["columns_source"] == "composed_year_row"
    # The banner and year rows are consumed as the header, not emitted as display rows.
    assert [row["label"] for row in parsed["rows"]] == ["Product revenue"]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-pr-2026",
        "syn-pr-2025",
        "syn-pr-2024",
    ]


def test_ambiguous_month_day_banner_keeps_the_refusal() -> None:
    html = SNOW_SHAPED_HTML.replace(
        "Fiscal Year Ended January 31,",
        "Fiscal Year Ended January 31, As of September 30,",
    )
    with pytest.raises(StatementGraphError, match=r"^displayed statement columns are absent:"):
        parse_displayed_primary_table(html, title=TITLE)


def test_single_year_row_keeps_the_refusal() -> None:
    html = SNOW_SHAPED_HTML.replace(
        "<td>2026</td><td>2025</td><td>2024</td>", "<td>2026</td><td></td><td></td>"
    )
    with pytest.raises(StatementGraphError, match=r"^displayed statement columns are absent:"):
        parse_displayed_primary_table(html, title=TITLE)


def test_bac_viewer_chrome_expands_to_dated_columns() -> None:
    parsed = parse_displayed_primary_table(
        BAC_VIEWER_SHAPED_HTML, title="Synthetic Statement of Income"
    )
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31", "2023-12-31"]
    assert "columns_source" not in parsed
    # The chrome title row (rowspan=2 label th + colspan=3 period th) is kept for
    # grid structure only: it is not a display row and adds no phantom column.
    assert [row["label"] for row in parsed["rows"]] == [
        "Interest income",
        "Noninterest income",
        "Service charges",
    ]
    assert [item["fact_id"] for item in parsed["rows"][0]["value_facts"]] == [
        "syn-ii-2025",
        "syn-ii-2024",
        "syn-ii-2023",
    ]
    assert [item["fact_id"] for item in parsed["rows"][2]["value_facts"]] == [
        "syn-sc-2025",
        "syn-sc-2024",
        "syn-sc-2023",
    ]
    assert parsed["rows"][1]["abstract"] is True


def test_fact_bearing_ragged_body_row_is_refused() -> None:
    html = """
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr>
      <td>Line</td>
      <td>Sep. 27, 2025</td>
      <td>Sep. 28, 2024</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2025" id="syn-r-2025" unitRef="usd" decimals="-6" scale="6">10</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-r-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2023" id="syn-r-2023" unitRef="usd" decimals="-6" scale="6">8</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    # The right-edge pad widens the two-date banner onto the body's grid, so the
    # third value is caught by the values-beyond-dated-columns guard instead.
    with pytest.raises(StatementGraphError, match=r"^displayed statement layout unsupported: row 0 carries 3 values for 2 dated columns") as raised:
        parse_displayed_primary_table(html, title=TITLE)
    assert str(raised.value).startswith("displayed statement layout unsupported:")


def test_rowspan_overrun_is_refused() -> None:
    html = """
    <html><body>
    <div>SYNTHETIC STATEMENT OF OPERATIONS</div>
    <table>
    <tr>
      <td>Line</td>
      <td>Sep. 27, 2025</td>
      <td>Sep. 28, 2024</td>
    </tr>
    <tr>
      <td>Revenue</td>
      <td rowspan="3">held</td>
      <td><ix:nonFraction name="us-gaap:Revenues" contextRef="c2024" id="syn-r-2024" unitRef="usd" decimals="-6" scale="6">9</ix:nonFraction></td>
    </tr>
    </table>
    </body></html>
    """
    with pytest.raises(StatementGraphError, match=r"^displayed statement layout unsupported: rowspan overruns"):
        parse_displayed_primary_table(html, title=TITLE)


def _package(manifest: dict) -> GoldenFilingPackage:
    return GoldenFilingPackage(manifest=manifest, members={})


def test_non_aapl_package_without_statement_roles_is_refused() -> None:
    package = _package({"accession": "0000070858-26-000123", "cik": "0000070858"})
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        with pytest.raises(
            StatementGraphError,
            match=f"^statement identity is not declared for issuer: {kind}$",
        ):
            _statement_identity(package, kind)


def test_declared_statement_roles_carry_title_search_list() -> None:
    package = _package(
        {
            "accession": "0000070858-26-000123",
            "statement_roles": {
                "income_statement": {
                    "role_uri": "http://www.example.com/role/ConsolidatedStatementOfIncome",
                    "title": "Consolidated Statement of Income",
                    "title_search": ["Consolidated Statements of Income", "Consolidated Statement of Income"],
                }
            },
        }
    )
    role_uri, title, search = _statement_identity(package, "income_statement")
    assert role_uri == "http://www.example.com/role/ConsolidatedStatementOfIncome"
    assert title == "Consolidated Statement of Income"
    assert search == ["Consolidated Statements of Income", "Consolidated Statement of Income"]


def test_aapl_default_identity_stays_byte_pinned() -> None:
    package = _package({"accession": "0000320193-25-000079"})
    for kind, role, title in (
        ("income_statement", "http://www.apple.com/role/CONSOLIDATEDSTATEMENTSOFOPERATIONS", "CONSOLIDATED STATEMENTS OF OPERATIONS"),
        ("balance_sheet", "http://www.apple.com/role/CONSOLIDATEDBALANCESHEETS", "CONSOLIDATED BALANCE SHEETS"),
        ("cash_flow", "http://www.apple.com/role/CONSOLIDATEDSTATEMENTSOFCASHFLOWS", "CONSOLIDATED STATEMENTS OF CASH FLOWS"),
    ):
        assert _statement_identity(package, kind) == (role, title, title)


def test_title_search_list_picks_first_present_title() -> None:
    parsed = parse_displayed_primary_table(
        BAC_VIEWER_SHAPED_HTML,
        title=["SYNTHETIC STATEMENT OF OPERATIONS", "synthetic statement of income"],
    )
    assert parsed["columns_iso"] == ["2025-12-31", "2024-12-31", "2023-12-31"]


# Canonical-JSON sha256 of reconstruct_statement output on the committed golden
# AAPL 10-K fixture, measured at the S0 head (471703401f) BEFORE the S0-b edits.
# These remain the digests under the committed metric registry 1.0.0 root.
_AAPL_BASE_DIGESTS = {
    "income_statement": "f4b541e8d561e2758c1057de3246a6bdcee89f8f40852791cdb1b7831cb58e22",
    "balance_sheet": "42afb15512efb22d06eb2bea3b9fdb9f10378ef7aa39db2ee9724954bafb4119",
    "cash_flow": "8a38bedfdefc194a57d6bb8c593d791bf0b5d8f75909ccda08991ee58423fda4",
}
# Re-pinned 2026-10-19 by seat ruling R-9761-CLK (c): under the live 1.1.0
# registry the LiabilitiesAndStockholdersEquity row aliases total_assets at
# priority 20, below Assets at 10, so it stays unmapped with an alias_priority
# receipt. That one receipt is the only byte change (asserted below).
_AAPL_LIVE_DIGESTS = {
    **_AAPL_BASE_DIGESTS,
    "balance_sheet": "f50b2f3f95ae42207530ce3b2145bdab9b1b40e7fe9bed5b54759c749b55ea4d",
}
_REGISTRY_V1_0_0_ROOT = ROOT / "tests" / "fixtures" / "fundamental_forensics_registry_v1_0_0"


def _golden_aapl_trees(registry_root: Path) -> dict[str, dict]:
    package = load_golden_aapl_package(ROOT)
    registry = load_core_registry(registry_root)
    parsed = parse_sec_filing_document(
        package.members[package.manifest["primary_document"]],
        document_name=package.manifest["primary_document"],
    )
    return {
        kind: reconstruct_statement(
            statement_type=kind,
            package=package,
            parsed_instance=parsed,
            registry=registry,
        )
        for kind in _AAPL_BASE_DIGESTS
    }


def _tree_digest(tree: dict) -> str:
    blob = json.dumps(tree, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_golden_aapl_reconstruction_is_byte_identical() -> None:
    live = _golden_aapl_trees(ROOT)
    for kind, expected in _AAPL_LIVE_DIGESTS.items():
        assert _tree_digest(live[kind]) == expected, kind
    v1_0_0 = _golden_aapl_trees(_REGISTRY_V1_0_0_ROOT)
    for kind, expected in _AAPL_BASE_DIGESTS.items():
        assert _tree_digest(v1_0_0[kind]) == expected, kind

    live_rows = live["balance_sheet"]["rows"]
    old_rows = v1_0_0["balance_sheet"]["rows"]
    assert {k: v for k, v in live["balance_sheet"].items() if k != "rows"} == {
        k: v for k, v in v1_0_0["balance_sheet"].items() if k != "rows"
    }
    assert len(live_rows) == len(old_rows)
    differing = [index for index, (new, old) in enumerate(zip(live_rows, old_rows)) if new != old]
    assert differing == [34]
    new, old = live_rows[34], old_rows[34]
    assert new["concept"] == old["concept"]
    assert new["concept"].endswith("LiabilitiesAndStockholdersEquity")
    assert {key for key in new if new[key] != old[key]} == {"mapping_receipt"}
    assert (old["standardized_metric_id"], old["mapping_state"], old["mapping_receipt"]) == (
        None,
        "unmapped",
        None,
    )
    assert (new["standardized_metric_id"], new["mapping_state"]) == (None, "unmapped")
    assert new["mapping_receipt"] == {
        "taxonomy": "us-gaap",
        "concept": "LiabilitiesAndStockholdersEquity",
        "reason": "alias_priority",
        "metric_id": "total_assets",
        "priority": 20,
        "governing_concept": "Assets",
        "governing_priority": 10,
    }
    # R-9761-CLK (e): exactly one standardized total_assets row (and cell per column).
    total_assets_rows = [row for row in live_rows if row["standardized_metric_id"] == "total_assets"]
    assert len(total_assets_rows) == 1
    assert total_assets_rows[0]["concept"].endswith(":Assets")
    mapped = [row["standardized_metric_id"] for row in live_rows if row["standardized_metric_id"]]
    assert len(mapped) == len(set(mapped))


def _mapped_row(concept: str, metric_id: str) -> dict:
    taxonomy, local = concept.split(":", 1)
    return {
        "concept": concept,
        "standardized_metric_id": metric_id,
        "mapping_state": "mapped",
        "mapping_receipt": {"taxonomy": taxonomy, "concept": local, "metric_id": metric_id},
    }


def test_alias_priority_keeps_the_lone_alias_and_demotes_a_lower_priority_twin() -> None:
    registry = load_core_registry(ROOT)
    alias_only = [_mapped_row("us-gaap:LiabilitiesAndStockholdersEquity", "total_assets")]
    statement_graph._apply_alias_priority(alias_only, registry)
    assert alias_only == [_mapped_row("us-gaap:LiabilitiesAndStockholdersEquity", "total_assets")]

    both = [
        _mapped_row("us-gaap:LiabilitiesAndStockholdersEquity", "total_assets"),
        _mapped_row("us-gaap:Assets", "total_assets"),
    ]
    statement_graph._apply_alias_priority(both, registry)
    assert both[1] == _mapped_row("us-gaap:Assets", "total_assets")
    assert (both[0]["standardized_metric_id"], both[0]["mapping_state"]) == (None, "unmapped")
    assert both[0]["mapping_receipt"]["reason"] == "alias_priority"
    assert both[0]["mapping_receipt"]["governing_concept"] == "Assets"

    tied = [_mapped_row("us-gaap:Assets", "total_assets"), _mapped_row("us-gaap:Assets", "total_assets")]
    statement_graph._apply_alias_priority(tied, registry)
    assert tied == [_mapped_row("us-gaap:Assets", "total_assets")] * 2


def _instant_cell(period_label: str, value) -> dict:
    return {
        "period": {"kind": "instant", "start": None, "end": period_label, "label": period_label},
        "value": value,
    }


def test_alias_priority_receipt_names_recoverable_columns() -> None:
    # #9761 follow-up (minor 3): whole-row demotion must not strand a value
    # only the loser carries. The receipt names the columns the governing row
    # leaves null, so a consumer can recover the binding from the demoted row.
    registry = load_core_registry(ROOT)
    governing = _mapped_row("us-gaap:Assets", "total_assets")
    governing["cells"] = [_instant_cell("2025-09-27", "100"), _instant_cell("2024-09-28", None)]
    demoted = _mapped_row("us-gaap:LiabilitiesAndStockholdersEquity", "total_assets")
    demoted["cells"] = [_instant_cell("2025-09-27", "100"), _instant_cell("2024-09-28", "95")]
    rows = [governing, demoted]
    statement_graph._apply_alias_priority(rows, registry)
    assert rows[0]["standardized_metric_id"] == "total_assets"
    assert rows[1]["mapping_receipt"]["recoverable_columns"] == ["2024-09-28"]

    # A winner that fills every column the loser carries stays key-free — the
    # AAPL golden balance-sheet shape, so committed bytes do not move.
    full_winner = _mapped_row("us-gaap:Assets", "total_assets")
    full_winner["cells"] = [_instant_cell("2025-09-27", "100"), _instant_cell("2024-09-28", "97")]
    loser = _mapped_row("us-gaap:LiabilitiesAndStockholdersEquity", "total_assets")
    loser["cells"] = [_instant_cell("2025-09-27", "100"), _instant_cell("2024-09-28", "95")]
    rows = [full_winner, loser]
    statement_graph._apply_alias_priority(rows, registry)
    assert rows[1]["mapping_receipt"]["reason"] == "alias_priority"
    assert "recoverable_columns" not in rows[1]["mapping_receipt"]


def test_alias_priority_prefers_a_total_label_for_total_metrics() -> None:
    # #9761 follow-up (minor 4): with the real registry, Assets@10 on a plain
    # "Assets" label used to beat LiabilitiesAndStockholdersEquity@20 on
    # "Total Liabilities and Stockholders' Equity", moving total_assets onto a
    # non-total line. A total_* metric first prefers total-labelled rows.
    registry = load_core_registry(ROOT)
    component = _mapped_row("us-gaap:Assets", "total_assets")
    component["as_reported_label"] = "Assets"
    total_line = _mapped_row("us-gaap:LiabilitiesAndStockholdersEquity", "total_assets")
    total_line["as_reported_label"] = "Total Liabilities and Stockholders' Equity"
    rows = [component, total_line]
    statement_graph._apply_alias_priority(rows, registry)
    assert rows[1]["standardized_metric_id"] == "total_assets"
    assert rows[1]["as_reported_label"].startswith("Total")
    assert (rows[0]["standardized_metric_id"], rows[0]["mapping_state"]) == (None, "unmapped")
    assert rows[0]["mapping_receipt"]["reason_detail"] == "total_label_preferred"

    # Both contenders on Total labels (the AAPL golden shape) keeps the
    # existing lowest-priority rule and the receipt keys unchanged.
    both_total = [
        {**_mapped_row("us-gaap:Assets", "total_assets"), "as_reported_label": "Total assets"},
        {
            **_mapped_row("us-gaap:LiabilitiesAndStockholdersEquity", "total_assets"),
            "as_reported_label": "Total liabilities and stockholders' equity",
        },
    ]
    statement_graph._apply_alias_priority(both_total, registry)
    assert both_total[0]["standardized_metric_id"] == "total_assets"
    assert (both_total[1]["standardized_metric_id"], both_total[1]["mapping_state"]) == (
        None,
        "unmapped",
    )
    assert "reason_detail" not in both_total[1]["mapping_receipt"]
