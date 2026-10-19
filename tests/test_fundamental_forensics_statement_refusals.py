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
    (195, "StatementGraphError", None),
    (202, "StatementGraphError", None),
    (206, "StatementGraphError", None),
    (208, "StatementGraphError", None),
    (217, "StatementGraphError", None),
    (221, "StatementGraphError", None),
    (223, "StatementGraphError", None),
    (225, "StatementGraphError", None),
    (233, "StatementGraphError", None),
    (235, "StatementGraphError", None),
    (237, "StatementGraphError", None),
    (240, "StatementGraphError", None),
    (244, "StatementGraphError", None),
    (246, "StatementGraphError", None),
    (248, "StatementGraphError", None),
    (257, "StatementGraphError", None),
    (261, "StatementGraphError", None),
    (263, "StatementGraphError", None),
    (268, "StatementGraphError", None),
    (270, "StatementGraphError", None),
    (273, "StatementGraphError", None),
    (275, "StatementGraphError", None),
    (278, "StatementGraphError", None),
    (281, "StatementGraphError", None),
    (283, "StatementGraphError", None),
    (287, "StatementGraphError", None),
    (290, "StatementGraphError", None),
    (296, "StatementGraphError", None),
    (299, "StatementGraphError", None),
    (302, "StatementGraphError", None),
    (304, "StatementGraphError", None),
    (316, "StatementGraphError", None),
    (318, "StatementGraphError", None),
    (324, "StatementGraphError", None),
    (330, "StatementGraphError", None),
    (333, "StatementGraphError", None),
    (337, "StatementGraphError", None),
    (340, "StatementGraphError", None),
    (342, "StatementGraphError", None),
    (351, "StatementGraphError", None),
    (362, "StatementGraphError", None),
    (364, "StatementGraphError", None),
    (395, "StatementGraphError", None),
    (407, "StatementGraphError", None),
    (409, "StatementGraphError", None),
    (412, "StatementGraphError", None),
    (416, "StatementGraphError", None),
    (465, "StatementGraphError", None),
    (477, "StatementGraphError", None),
    (495, "StatementGraphError", None),
    (501, "StatementGraphError", None),
    (562, "StatementGraphError", None),
    (841, "_layout_unsupported", "displayed_layout_unsupported"),
    (853, "_layout_unsupported", "displayed_layout_unsupported"),
    (860, "_layout_unsupported", None),
    (924, "_layout_unsupported", None),
    (931, "_layout_unsupported", None),
    (937, "_layout_unsupported", None),
    (943, "_layout_unsupported", None),
    (1007, "_layout_unsupported", None),
    (1279, "StatementGraphError", None),
    (1285, "StatementGraphError", "displayed_table_absent"),
    (1373, "_layout_unsupported", None),
    (1377, "StatementGraphError", "displayed_columns_absent"),
    (1387, "_layout_unsupported", None),
    (1482, "StatementGraphError", None),
    (1498, "StatementGraphError", None),
    (1501, "StatementGraphError", None),
    (1506, "StatementGraphError", None),
    (1521, "StatementGraphError", None),
    (1526, "StatementGraphError", None),
    (1531, "StatementGraphError", None),
    (1987, "StatementGraphError", "statement_role_not_consolidated"),
    (2015, "StatementGraphError", None),
    (2018, "StatementGraphError", None),
    (2164, "StatementGraphError", None),
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
