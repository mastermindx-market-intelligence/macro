"""Option B lane K: typed statement refusal codes and conversion rule."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from collectors.sec_filing_parser import parse_sec_filing_document
from engine.fundamental_forensics.financial_intelligence_packet import load_core_registry
from engine.fundamental_forensics import statement_graph
from engine.fundamental_forensics.statement_graph import (
    GOLDEN_AAPL_FIXTURES,
    GoldenFilingPackage,
    PRIMARY_STATEMENT_ROLES,
    STATEMENT_REFUSAL_CODES,
    STATEMENT_TITLES,
    StatementGraphError,
    load_golden_aapl_package,
    reconstruct_primary_statements,
)

ROOT = Path(__file__).resolve().parents[1]
_STATEMENT_GRAPH = ROOT / "engine/fundamental_forensics/statement_graph.py"

_PINNED_RAISE_SITES = (
    (218, "StatementGraphError", None),    (225, "StatementGraphError", None),    (229, "StatementGraphError", None),    (231, "StatementGraphError", None),    (240, "StatementGraphError", None),    (244, "StatementGraphError", None),    (246, "StatementGraphError", None),    (248, "StatementGraphError", None),    (256, "StatementGraphError", None),    (258, "StatementGraphError", None),    (260, "StatementGraphError", None),    (263, "StatementGraphError", None),    (267, "StatementGraphError", None),    (269, "StatementGraphError", None),    (271, "StatementGraphError", None),    (280, "StatementGraphError", None),    (284, "StatementGraphError", None),    (286, "StatementGraphError", None),    (291, "StatementGraphError", None),    (293, "StatementGraphError", None),    (296, "StatementGraphError", None),    (298, "StatementGraphError", None),    (301, "StatementGraphError", None),    (304, "StatementGraphError", None),    (306, "StatementGraphError", None),    (310, "StatementGraphError", None),    (313, "StatementGraphError", None),    (319, "StatementGraphError", None),    (322, "StatementGraphError", None),    (325, "StatementGraphError", None),    (327, "StatementGraphError", None),    (339, "StatementGraphError", None),    (341, "StatementGraphError", None),    (347, "StatementGraphError", None),    (353, "StatementGraphError", None),    (356, "StatementGraphError", None),    (360, "StatementGraphError", None),    (363, "StatementGraphError", None),    (365, "StatementGraphError", None),    (374, "StatementGraphError", None),    (385, "StatementGraphError", None),    (387, "StatementGraphError", None),    (418, "StatementGraphError", None),    (430, "StatementGraphError", None),    (432, "StatementGraphError", None),    (435, "StatementGraphError", None),    (439, "StatementGraphError", None),    (488, "StatementGraphError", "statement_role_presentation_absent"),    (503, "StatementGraphError", None),    (521, "StatementGraphError", None),    (527, "StatementGraphError", None),    (588, "StatementGraphError", None),    (1007, "_layout_unsupported", "displayed_layout_unsupported"),    (1019, "_layout_unsupported", "displayed_layout_unsupported"),    (1026, "_layout_unsupported", "displayed_layout_unsupported"),    (1093, "_layout_unsupported", "displayed_layout_unsupported"),    (1103, "_layout_unsupported", "displayed_layout_unsupported"),    (1112, "_layout_unsupported", "displayed_layout_unsupported"),    (1121, "_layout_unsupported", "displayed_layout_unsupported"),    (1188, "_layout_unsupported", "displayed_layout_unsupported"),    (1691, "StatementGraphError", None),    (1704, "StatementGraphError", "displayed_table_absent"),    (1794, "_layout_unsupported", "displayed_layout_unsupported"),    (1799, "StatementGraphError", "displayed_columns_absent"),    (1809, "_layout_unsupported", "displayed_layout_unsupported"),    (1969, "StatementGraphError", "displayed_columns_absent"),    (1988, "StatementGraphError", "displayed_column_period_unbound"),    (1994, "StatementGraphError", "displayed_column_period_unbound"),    (2002, "StatementGraphError", "displayed_columns_absent"),    (2020, "StatementGraphError", "displayed_column_period_unbound"),    (2028, "StatementGraphError", "displayed_column_period_unbound"),    (2036, "StatementGraphError", "displayed_column_period_unbound"),    (2595, "StatementGraphError", "statement_role_not_consolidated"),    (2628, "StatementGraphError", None),    (2631, "StatementGraphError", None),    (2778, "StatementGraphError", None),)


def _collect_raise_sites() -> list[tuple[int, str, str | None]]:
    tree = ast.parse(_STATEMENT_GRAPH.read_text(encoding="utf-8"))
    sites: list[tuple[int, str, str | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exc = node.exc
        if not isinstance(exc, ast.Call):
            continue
        kind = None
        if isinstance(exc.func, ast.Name) and exc.func.id in {
            "StatementGraphError",
            "_layout_unsupported",
        }:
            kind = exc.func.id
        if kind is None:
            continue
        refusal = None
        for keyword in exc.keywords:
            if keyword.arg == "refusal_code" and isinstance(keyword.value, ast.Constant):
                refusal = keyword.value.value
        sites.append((node.lineno, kind, refusal))
    return sorted(sites)


def test_raise_site_census_matches_pin() -> None:
    assert _collect_raise_sites() == list(_PINNED_RAISE_SITES)


def test_statement_refusal_codes_export_order() -> None:
    assert STATEMENT_REFUSAL_CODES == (
        "displayed_layout_unsupported",
        "displayed_table_absent",
        "displayed_columns_absent",
        "statement_role_not_consolidated",
        "displayed_cell_period_mismatch",
        "displayed_column_period_unbound",
        "statement_role_presentation_absent",
    )


def _package_with_roles(manifest_patch: dict) -> GoldenFilingPackage:
    base = load_golden_aapl_package(ROOT, accession=sorted(GOLDEN_AAPL_FIXTURES)[0])
    manifest = dict(base.manifest)
    manifest.update(manifest_patch)
    return GoldenFilingPackage(manifest=manifest, members=dict(base.members))


def test_coded_errors_convert_to_refusal_entries() -> None:
    registry = load_core_registry(ROOT)
    package = _package_with_roles(
        {
            "statement_roles": {
                "income_statement": {
                    "role_uri": PRIMARY_STATEMENT_ROLES["income_statement"],
                    "title": STATEMENT_TITLES["income_statement"],
                    "title_search": "NO SUCH TABLE TITLE",
                },
                "balance_sheet": {
                    "role_uri": PRIMARY_STATEMENT_ROLES["balance_sheet"],
                    "title": STATEMENT_TITLES["balance_sheet"],
                    "title_search": STATEMENT_TITLES["balance_sheet"],
                },
                "cash_flow": {
                    "role_uri": PRIMARY_STATEMENT_ROLES["cash_flow"],
                    "title": STATEMENT_TITLES["cash_flow"],
                    "title_search": STATEMENT_TITLES["cash_flow"],
                },
            }
        }
    )
    result = reconstruct_primary_statements(package=package, registry=registry)
    income = next(s for s in result["statements"] if s["statement_type"] == "income_statement")
    assert income["refusal"] == {"code": "displayed_table_absent"}
    assert income["columns"] == []
    assert income["row_count"] == 0
    assert income["rows"] == []
    assert income["role_uri"]
    assert income["title"]


def test_statement_role_not_consolidated_entry_has_null_identity() -> None:
    registry = load_core_registry(ROOT)
    package = _package_with_roles(
        {
            "statement_roles": {
                "income_statement": {
                    "role_uri": "http://fasb.org/us-gaap/role/ParentCompanyInformationIncomeStatementDetails",
                    "title": "99556 - Disclosure - Parent Company Information - Income Statement (Details)",
                    "title_search": "Parent",
                },
                "balance_sheet": {
                    "role_uri": PRIMARY_STATEMENT_ROLES["balance_sheet"],
                    "title": STATEMENT_TITLES["balance_sheet"],
                    "title_search": STATEMENT_TITLES["balance_sheet"],
                },
                "cash_flow": {
                    "role_uri": PRIMARY_STATEMENT_ROLES["cash_flow"],
                    "title": STATEMENT_TITLES["cash_flow"],
                    "title_search": STATEMENT_TITLES["cash_flow"],
                },
            }
        }
    )
    result = reconstruct_primary_statements(package=package, registry=registry)
    income = next(s for s in result["statements"] if s["statement_type"] == "income_statement")
    assert income["refusal"] == {"code": "statement_role_not_consolidated"}
    assert income["role_uri"] is None
    assert income["title"] is None


def test_uncoded_statement_graph_error_reraises_from_primary_statements() -> None:
    registry = load_core_registry(ROOT)
    package = load_golden_aapl_package(ROOT, accession=sorted(GOLDEN_AAPL_FIXTURES)[0])

    def _boom(**_kwargs):
        raise StatementGraphError("displayed statement has no numeric rows: TEST")

    with patch(
        "engine.fundamental_forensics.statement_graph.reconstruct_statement",
        side_effect=_boom,
    ):
        with pytest.raises(StatementGraphError, match="no numeric rows"):
            reconstruct_primary_statements(package=package, registry=registry)


def test_non_statement_graph_error_reraises_from_primary_statements() -> None:
    registry = load_core_registry(ROOT)
    package = load_golden_aapl_package(ROOT, accession=sorted(GOLDEN_AAPL_FIXTURES)[0])

    def _boom(**_kwargs):
        raise RuntimeError("decode failed")

    with patch(
        "engine.fundamental_forensics.statement_graph.reconstruct_statement",
        side_effect=_boom,
    ):
        with pytest.raises(RuntimeError, match="decode failed"):
            reconstruct_primary_statements(package=package, registry=registry)


def test_role_guard_does_not_fire_on_golden_aapl_identities() -> None:
    registry = load_core_registry(ROOT)
    for accession in sorted(GOLDEN_AAPL_FIXTURES):
        package = load_golden_aapl_package(ROOT, accession=accession)
        result = reconstruct_primary_statements(package=package, registry=registry)
        for statement in result["statements"]:
            assert "refusal" not in statement


def test_r7_period_disagreement_is_coded() -> None:
    exc = statement_graph._cell_period_disagreement(
        1,
        "Total net sales",
        {"fact_id": "fact-7"},
        {"kind": "duration", "start_date": "2025-09-28", "end_date": "2026-09-26"},
        {"kind": "duration", "start": "2025-09-27", "end": "2026-09-26"},
        "duration start is not the grouped column start",
    )
    assert isinstance(exc, StatementGraphError)
    assert exc.refusal_code == "displayed_cell_period_mismatch"
    assert str(exc).startswith("displayed cell period disagrees with its column ")


def test_r7_refusal_becomes_a_coded_entry() -> None:
    registry = load_core_registry(ROOT)
    package = load_golden_aapl_package(ROOT, accession=sorted(GOLDEN_AAPL_FIXTURES)[0])
    real_reconstruct = statement_graph.reconstruct_statement

    def _r7_on_income(*, statement_type, **kwargs):
        if statement_type == "income_statement":
            raise statement_graph._cell_period_disagreement(
                0,
                "Net sales",
                {"fact_id": "fact-0"},
                {"kind": "duration", "start_date": "2025-09-28", "end_date": "2026-09-26"},
                {"kind": "duration", "start": "2025-09-27", "end": "2026-09-26"},
                "duration start is not the grouped column start",
            )
        return real_reconstruct(statement_type=statement_type, **kwargs)

    with patch(
        "engine.fundamental_forensics.statement_graph.reconstruct_statement",
        side_effect=_r7_on_income,
    ):
        result = reconstruct_primary_statements(package=package, registry=registry)
    assert [s["statement_type"] for s in result["statements"]] == [
        "income_statement",
        "balance_sheet",
        "cash_flow",
    ]
    income = result["statements"][0]
    assert income["refusal"] == {"code": "displayed_cell_period_mismatch"}
    assert income["rows"] == []
    assert income["row_count"] == 0
    assert income["columns"] == []
    assert income["role_uri"]
    assert income["title"]


def test_uncoded_statement_graph_error_still_reraises() -> None:
    registry = load_core_registry(ROOT)
    package = load_golden_aapl_package(ROOT, accession=sorted(GOLDEN_AAPL_FIXTURES)[0])
    real_reconstruct = statement_graph.reconstruct_statement

    def _uncoded_on_income(*, statement_type, **kwargs):
        if statement_type == "income_statement":
            raise StatementGraphError("displayed statement has no numeric rows: R7TEST")
        return real_reconstruct(statement_type=statement_type, **kwargs)

    with patch(
        "engine.fundamental_forensics.statement_graph.reconstruct_statement",
        side_effect=_uncoded_on_income,
    ):
        with pytest.raises(StatementGraphError, match="no numeric rows"):
            reconstruct_primary_statements(package=package, registry=registry)


def test_bsdate_family_sites_carry_their_ruled_codes() -> None:
    sites = _collect_raise_sites()
    period_unbound = [site for site in sites if site[2] == "displayed_column_period_unbound"]
    presentation_absent = [site for site in sites if site[2] == "statement_role_presentation_absent"]
    assert len(period_unbound) == 5
    assert all(site[1] == "StatementGraphError" for site in period_unbound)
    assert len(presentation_absent) == 1
    assert presentation_absent[0][1] == "StatementGraphError"
    assert not [site for site in sites if site[1] == "_layout_unsupported" and site[2] is None]


def test_bsdate_column_period_unbound_becomes_a_coded_entry() -> None:
    registry = load_core_registry(ROOT)
    package = load_golden_aapl_package(ROOT, accession=sorted(GOLDEN_AAPL_FIXTURES)[0])
    real_reconstruct = statement_graph.reconstruct_statement

    def _bsdate_on_balance(*, statement_type, **kwargs):
        if statement_type == "balance_sheet":
            raise StatementGraphError(
                "displayed balance-sheet column is not bound to the filing date",
                refusal_code="displayed_column_period_unbound",
            )
        return real_reconstruct(statement_type=statement_type, **kwargs)

    with patch(
        "engine.fundamental_forensics.statement_graph.reconstruct_statement",
        side_effect=_bsdate_on_balance,
    ):
        result = reconstruct_primary_statements(package=package, registry=registry)
    assert [s["statement_type"] for s in result["statements"]] == [
        "income_statement",
        "balance_sheet",
        "cash_flow",
    ]
    balance = result["statements"][1]
    assert balance["refusal"] == {"code": "displayed_column_period_unbound"}
    assert balance["rows"] == []
    assert balance["row_count"] == 0
    assert balance["columns"] == []
    assert balance["role_uri"]
    assert balance["title"]


def test_bsdate_presentation_absent_becomes_a_coded_entry() -> None:
    registry = load_core_registry(ROOT)
    package = load_golden_aapl_package(ROOT, accession=sorted(GOLDEN_AAPL_FIXTURES)[0])
    real_reconstruct = statement_graph.reconstruct_statement
    role_uri = PRIMARY_STATEMENT_ROLES["income_statement"]

    def _bsdate_on_income(*, statement_type, **kwargs):
        if statement_type == "income_statement":
            raise StatementGraphError(
                f"presentation role is absent: {role_uri}",
                refusal_code="statement_role_presentation_absent",
            )
        return real_reconstruct(statement_type=statement_type, **kwargs)

    with patch(
        "engine.fundamental_forensics.statement_graph.reconstruct_statement",
        side_effect=_bsdate_on_income,
    ):
        result = reconstruct_primary_statements(package=package, registry=registry)
    assert [s["statement_type"] for s in result["statements"]] == [
        "income_statement",
        "balance_sheet",
        "cash_flow",
    ]
    income = result["statements"][0]
    assert income["refusal"] == {"code": "statement_role_presentation_absent"}
    assert income["rows"] == []
    assert income["row_count"] == 0
    assert income["columns"] == []
    assert income["role_uri"]
    assert income["title"]


def test_bsdate_presentation_absent_raises_coded() -> None:
    role_uri = "http://fasb.org/us-gaap/role/StatementOfIncome"
    with pytest.raises(StatementGraphError) as caught:
        statement_graph.parse_presentation_tree(b"<linkbase/>", role_uri=role_uri)
    assert caught.value.refusal_code == "statement_role_presentation_absent"
    assert str(caught.value) == f"presentation role is absent: {role_uri}"


def test_bsdate_columns_from_display_codes() -> None:
    with pytest.raises(StatementGraphError) as unbound:
        statement_graph._columns_from_display(
            statement_type="balance_sheet",
            iso_dates=["2026-09-26", "2025-09-27"],
            displayed_rows=[],
            facts_by_id={},
            contexts={},
        )
    assert unbound.value.refusal_code == "displayed_column_period_unbound"
    assert str(unbound.value) == "displayed balance-sheet column is not bound to the filing date"
    with pytest.raises(StatementGraphError) as absent:
        statement_graph._columns_from_display(
            statement_type="balance_sheet",
            iso_dates=["2026-09-26"],
            displayed_rows=[],
            facts_by_id={},
            contexts={},
        )
    assert absent.value.refusal_code == "displayed_columns_absent"
    assert str(absent.value) == "displayed statement columns are absent"
