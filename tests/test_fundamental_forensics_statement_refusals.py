"""Option B lane K: typed statement refusal codes and conversion rule."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from collectors.sec_filing_parser import parse_sec_filing_document
from engine.fundamental_forensics.financial_intelligence_packet import load_core_registry
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
    (193, "StatementGraphError", None),
    (200, "StatementGraphError", None),
    (204, "StatementGraphError", None),
    (206, "StatementGraphError", None),
    (215, "StatementGraphError", None),
    (219, "StatementGraphError", None),
    (221, "StatementGraphError", None),
    (223, "StatementGraphError", None),
    (231, "StatementGraphError", None),
    (233, "StatementGraphError", None),
    (235, "StatementGraphError", None),
    (238, "StatementGraphError", None),
    (242, "StatementGraphError", None),
    (244, "StatementGraphError", None),
    (246, "StatementGraphError", None),
    (255, "StatementGraphError", None),
    (259, "StatementGraphError", None),
    (261, "StatementGraphError", None),
    (266, "StatementGraphError", None),
    (268, "StatementGraphError", None),
    (271, "StatementGraphError", None),
    (273, "StatementGraphError", None),
    (276, "StatementGraphError", None),
    (279, "StatementGraphError", None),
    (281, "StatementGraphError", None),
    (285, "StatementGraphError", None),
    (288, "StatementGraphError", None),
    (294, "StatementGraphError", None),
    (297, "StatementGraphError", None),
    (300, "StatementGraphError", None),
    (302, "StatementGraphError", None),
    (314, "StatementGraphError", None),
    (316, "StatementGraphError", None),
    (322, "StatementGraphError", None),
    (328, "StatementGraphError", None),
    (331, "StatementGraphError", None),
    (335, "StatementGraphError", None),
    (338, "StatementGraphError", None),
    (340, "StatementGraphError", None),
    (349, "StatementGraphError", None),
    (360, "StatementGraphError", None),
    (362, "StatementGraphError", None),
    (393, "StatementGraphError", None),
    (405, "StatementGraphError", None),
    (407, "StatementGraphError", None),
    (410, "StatementGraphError", None),
    (414, "StatementGraphError", None),
    (463, "StatementGraphError", None),
    (475, "StatementGraphError", None),
    (493, "StatementGraphError", None),
    (499, "StatementGraphError", None),
    (560, "StatementGraphError", None),
    (839, "_layout_unsupported", "displayed_layout_unsupported"),
    (851, "_layout_unsupported", "displayed_layout_unsupported"),
    (858, "_layout_unsupported", None),
    (922, "_layout_unsupported", None),
    (929, "_layout_unsupported", None),
    (935, "_layout_unsupported", None),
    (941, "_layout_unsupported", None),
    (1005, "_layout_unsupported", None),
    (1277, "StatementGraphError", None),
    (1283, "StatementGraphError", "displayed_table_absent"),
    (1371, "_layout_unsupported", None),
    (1375, "StatementGraphError", "displayed_columns_absent"),
    (1385, "_layout_unsupported", None),
    (1480, "StatementGraphError", None),
    (1496, "StatementGraphError", None),
    (1499, "StatementGraphError", None),
    (1504, "StatementGraphError", None),
    (1519, "StatementGraphError", None),
    (1524, "StatementGraphError", None),
    (1529, "StatementGraphError", None),
    (2084, "StatementGraphError", "statement_role_not_consolidated"),
    (2112, "StatementGraphError", None),
    (2115, "StatementGraphError", None),
    (2262, "StatementGraphError", None),
)


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
