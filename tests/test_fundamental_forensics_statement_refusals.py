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
    (194, "StatementGraphError", None),    (201, "StatementGraphError", None),    (205, "StatementGraphError", None),    (207, "StatementGraphError", None),    (216, "StatementGraphError", None),    (220, "StatementGraphError", None),    (222, "StatementGraphError", None),    (224, "StatementGraphError", None),    (232, "StatementGraphError", None),    (234, "StatementGraphError", None),    (236, "StatementGraphError", None),    (239, "StatementGraphError", None),    (243, "StatementGraphError", None),    (245, "StatementGraphError", None),    (247, "StatementGraphError", None),    (256, "StatementGraphError", None),    (260, "StatementGraphError", None),    (262, "StatementGraphError", None),    (267, "StatementGraphError", None),    (269, "StatementGraphError", None),    (272, "StatementGraphError", None),    (274, "StatementGraphError", None),    (277, "StatementGraphError", None),    (280, "StatementGraphError", None),    (282, "StatementGraphError", None),    (286, "StatementGraphError", None),    (289, "StatementGraphError", None),    (295, "StatementGraphError", None),    (298, "StatementGraphError", None),    (301, "StatementGraphError", None),    (303, "StatementGraphError", None),    (315, "StatementGraphError", None),    (317, "StatementGraphError", None),    (323, "StatementGraphError", None),    (329, "StatementGraphError", None),    (332, "StatementGraphError", None),    (336, "StatementGraphError", None),    (339, "StatementGraphError", None),    (341, "StatementGraphError", None),    (350, "StatementGraphError", None),    (361, "StatementGraphError", None),    (363, "StatementGraphError", None),    (394, "StatementGraphError", None),    (406, "StatementGraphError", None),    (408, "StatementGraphError", None),    (411, "StatementGraphError", None),    (415, "StatementGraphError", None),    (464, "StatementGraphError", None),    (476, "StatementGraphError", None),    (494, "StatementGraphError", None),    (500, "StatementGraphError", None),    (561, "StatementGraphError", None),    (840, "_layout_unsupported", "displayed_layout_unsupported"),    (852, "_layout_unsupported", "displayed_layout_unsupported"),    (859, "_layout_unsupported", None),    (923, "_layout_unsupported", None),    (930, "_layout_unsupported", None),    (936, "_layout_unsupported", None),    (942, "_layout_unsupported", None),    (1006, "_layout_unsupported", None),    (1278, "StatementGraphError", None),    (1284, "StatementGraphError", "displayed_table_absent"),    (1372, "_layout_unsupported", None),    (1376, "StatementGraphError", "displayed_columns_absent"),    (1386, "_layout_unsupported", None),    (1481, "StatementGraphError", None),    (1497, "StatementGraphError", None),    (1500, "StatementGraphError", None),    (1505, "StatementGraphError", None),    (1520, "StatementGraphError", None),    (1525, "StatementGraphError", None),    (1530, "StatementGraphError", None),    (2086, "StatementGraphError", "statement_role_not_consolidated"),    (2114, "StatementGraphError", None),    (2117, "StatementGraphError", None),    (2264, "StatementGraphError", None),)


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
