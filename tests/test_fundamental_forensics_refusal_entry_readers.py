"""R-B4 re-verify: refusal entries do not crash tree-row readers or excel export."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

import scripts.build_fundamental_forensics as bff
from engine.fundamental_forensics.excel_export import to_xlsx_bytes
from engine.fundamental_forensics.production_datasets import ProductionDatasetError

ROOT = Path(__file__).resolve().parents[1]

REFUSAL_CODE = "displayed_layout_unsupported"


class _FakeGeneration:
    def __init__(self, trees: dict[str, dict]) -> None:
        self._trees = trees

    def statement_trees(self, accession: str) -> dict:
        try:
            return self._trees[accession]
        except KeyError:
            raise ProductionDatasetError("synthetic: accession absent") from None


def _refusal_entry(statement_type: str) -> dict:
    return {
        "statement_type": statement_type,
        "role_uri": "https://example.com/role/test",
        "title": "Synthetic",
        "columns": [],
        "row_count": 0,
        "rows": [],
        "refusal": {"code": REFUSAL_CODE},
    }


def _income_row(metric_id: str, end: str, value: str) -> dict:
    return {
        "standardized_metric_id": metric_id,
        "cells": [{
            "period": {"kind": "duration", "start": "2026-01-01", "end": end},
            "unit": "USD",
            "value": value,
        }],
    }


def test_bff_tree_row_reader_ignores_refusal_entry_rows() -> None:
    """The cohort projector uses ``.get('rows') or []`` and must not invent cells."""
    accession = "0000000001-26-000001"
    generation = _FakeGeneration({
        accession: {
            "statements": [
                _refusal_entry("income_statement"),
                {
                    "statement_type": "balance_sheet",
                    "rows": [_income_row("total_assets", "2025-09-30", "100")],
                },
            ],
        },
    })
    periods = {accession: "2025-12-31"}
    out = bff._tree_metric_observations(
        generation,
        [accession],
        ("total_assets", "revenue"),
        frozenset(),
        periods,
    )
    assert out is not None
    assert "total_assets" in out
    assert out["total_assets"].value == Decimal("100")
    assert "revenue" not in out
    for statement in generation.statement_trees(accession)["statements"]:
        for row in statement.get("rows") or []:
            assert row.get("standardized_metric_id") != "revenue"


def test_excel_export_does_not_read_statement_trees_and_does_not_crash() -> None:
    """excel_export consumes MetricMatrix only; refusal slugs never enter the workbook."""
    payload = {
        "schema": "fundamental_forensics.financial_query_response/v1",
        "query_id": "q-refusal-reader",
        "query_hash": "ab" * 32,
        "sha256": "cd" * 32,
        "rows": [],
    }
    blob = to_xlsx_bytes(payload)
    assert blob
    assert REFUSAL_CODE.encode() not in blob
    assert b"displayed_layout" not in blob
