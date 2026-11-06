"""FIF (d): coverage-contract issuers the broad panel does not carry.

The signed-in production check on 2026-11-01 found SNOW, a five-issuer
reference-release member, absent from the Fundamental Forensics page: the
state only listed tickers of ``data/edgar/statements_quarterly.parquet`` and
SNOW is not in that broad panel. ``compose_state`` now lists every contract
issuer, a missing one as a limited identity-only company (no findings, no
panel periods, every check not evaluable) joined to the issuer master by exact
CIK, so the page can open its generation-backed statements.

All offline: synthetic roots, the production store monkeypatched absent.
"""
from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

import scripts.build_fundamental_forensics as bff

ROOT = Path(__file__).resolve().parents[1]
GEN_AT = "2026-10-12T00:00:00+00:00"

# Panel carries PAN only; the contract names PAN (in the panel) plus two
# issuers the panel does not yield: QQQ (issuer-master row) and RRR (none).
CONTRACT = (
    ("PAN", "0000000011", "Panel Issuer Inc."),
    ("QQQ", "0000000012", "Contract Only Corp."),
    ("RRR", "0000000013", "  "),
)


def _write_root(root: Path, *, contract: bool = True, names: dict[str, str] | None = None) -> None:
    edgar = root / "data" / "edgar"
    edgar.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"ticker": "PAN", "fiscal_year": 2025, "fiscal_quarter": 2,
         "period_end": "2025-06-30", "filed": "2025-08-01"},
        {"ticker": "PAN", "fiscal_year": 2026, "fiscal_quarter": 2,
         "period_end": "2026-06-30", "filed": "2026-08-01"},
    ]).to_parquet(edgar / "statements_quarterly.parquet", index=False)
    pd.DataFrame({"cik": [11]}, index=pd.Index(["PAN"], name="ticker")).to_parquet(edgar / "fundamentals.parquet")

    if names:
        universe = root / "data" / "universe"
        universe.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([
            {"ticker": ticker, "name": name, "sector": "Technology", "active": True}
            for ticker, name in names.items()
        ]).to_parquet(universe / "membership.parquet", index=False)

    master = root / "data" / "reference" / "issuer_master.parquet"
    master.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"issuer_id": "ISS:TEST-PAN", "cik": "0000000011"},
        {"issuer_id": "ISS:TEST-QQQ", "cik": "0000000012"},
    ]).to_parquet(master, index=False)

    # the cohort projection loads the shipped governed registry before it
    # looks for a store, so each root stages the real catalog bytes
    metric_root = ROOT / "config" / "fundamental_forensics" / "metrics" / "v1"
    staged_root = root / "config" / "fundamental_forensics" / "metrics" / "v1"
    for relative in ("metric_catalog.yaml", "mappings/core.yaml", "formulas/core.yaml"):
        (staged_root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(metric_root / relative, staged_root / relative)

    if not contract:
        return
    issuers = [
        {
            "ticker": ticker.lower() if ticker == "QQQ" else ticker,
            "cik": cik,
            "legal_name": legal_name,
            "accessions": [{
                "accession": f"0000000-26-0000{index}",
                "form": "10-Q",
                "filing_date": "2026-07-15",
                "period_of_report": "2026-06-30",
                "retention_state": "not_retained",
            }],
        }
        for index, (ticker, cik, legal_name) in enumerate(CONTRACT)
    ]
    path = root / bff.COVERAGE_CONTRACT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": "synthetic_contract_issuers_v1",
        "issuers": issuers,
    }, indent=1), encoding="utf-8")


def _compose(root: Path, monkeypatch) -> dict:
    monkeypatch.setattr(bff, "build_production_dataset_store", lambda: None)
    return bff.compose_state(root, generated_at=GEN_AT)


def test_contract_issuer_missing_from_the_panel_is_listed_as_limited(tmp_path: Path, monkeypatch) -> None:
    _write_root(tmp_path)
    state = _compose(tmp_path, monkeypatch)
    companies = state["companies"]

    assert list(companies) == ["PAN", "QQQ", "RRR"]  # panel first, then contract order
    qqq = companies["QQQ"]
    assert qqq == {
        "symbol": "QQQ",
        "name": "Contract Only Corp.",
        "sector": "Unclassified",
        "cik": 12,
        "entity_id": "ISS:TEST-QQQ",
        "entity_id_reason": "issuer_master_row",
        "latest_period": "",
        "latest_filed": "",
        "action": {
            "key": "limited",
            "en": "Checks not run: not yet evaluable from the broad statements panel",
            "zh": "未运行检查：尚无法从广覆盖报表面板评估",
        },
        "coverage": {
            "periods": 0,
            "metrics_pct": 0.0,
            "detectors_evaluable": 0,
            "detectors_total": len(bff.DETECTORS),
            "basis": "coverage_contract_catalog_only",
        },
        "findings": [],
        "periods": [],
    }
    # the exact-CIK join is the panel path's own
    assert companies["PAN"]["entity_id"] == "ISS:TEST-PAN"
    assert companies["PAN"]["entity_id_reason"] == "issuer_master_row"

    # no issuer-master row: null id with a machine-readable reason, and a
    # blank legal name falls back to the ticker
    rrr = companies["RRR"]
    assert rrr["entity_id"] is None
    assert rrr["entity_id_reason"] == "issuer_master_row_absent_for_cik"
    assert rrr["cik"] == 13
    assert rrr["name"] == "RRR"

    summary = state["summary"]
    assert summary["companies"] == 3
    assert summary["contract_only_companies"] == 2
    assert summary["findings"] == len(state["ranked_findings"])
    assert all(row["symbol"] == "PAN" for row in state["ranked_findings"])


def test_contract_only_rows_never_move_the_default_or_the_as_of(tmp_path: Path, monkeypatch) -> None:
    _write_root(tmp_path)
    with_contract = _compose(tmp_path, monkeypatch)
    _write_root(tmp_path / "bare", contract=False)
    without = _compose(tmp_path / "bare", monkeypatch)

    assert with_contract["default_symbol"] == without["default_symbol"] == "PAN"
    assert with_contract["as_of"] == without["as_of"]
    assert with_contract["companies"]["PAN"] == without["companies"]["PAN"]
    assert with_contract["ranked_findings"] == without["ranked_findings"]


def test_no_contract_adds_no_company(tmp_path: Path, monkeypatch) -> None:
    _write_root(tmp_path, contract=False)
    state = _compose(tmp_path, monkeypatch)
    assert list(state["companies"]) == ["PAN"]
    assert state["summary"]["contract_only_companies"] == 0


def test_universe_name_outranks_the_contract_legal_name(tmp_path: Path, monkeypatch) -> None:
    _write_root(tmp_path, names={"QQQ": "Universe Name Ltd"})
    state = _compose(tmp_path, monkeypatch)
    assert state["companies"]["QQQ"]["name"] == "Universe Name Ltd"
    assert state["companies"]["QQQ"]["sector"] == "Technology"


def test_public_summary_projection_stays_two_counts(tmp_path: Path, monkeypatch) -> None:
    _write_root(tmp_path)
    state = _compose(tmp_path, monkeypatch)
    assert bff.public_summary_projection(state["summary"]) == {"companies": 3, "findings": state["summary"]["findings"]}


def test_contract_only_path_carries_no_ticker_or_cik_literal() -> None:
    """A33: the producer selects contract issuers by data, never by name."""
    tree = ast.parse((ROOT / "scripts" / "build_fundamental_forensics.py").read_text(encoding="utf-8"))
    sources = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {"_contract_only_company", "_contract_members"}:
            sources.append(ast.get_source_segment(
                (ROOT / "scripts" / "build_fundamental_forensics.py").read_text(encoding="utf-8"), node))
    assert len(sources) == 2
    for source in sources:
        for literal in ("SNOW", "AAPL", "CAT", "BAC", "GOOGL", "1640147", "320193", "ISS:"):
            assert literal not in source


# ---------------------------------------------------------------------------
# CIK de-duplication (2026-11-02): one SEC registrant is listed once even when
# the contract names it under a different ticker than the panel, and the
# contract-only copy no longer claims the issuer is missing from the panel's
# source universe — the panel yields only issuers with a prior-year same
# quarter, so absence does not mean the issuer is unknown to it.
# ---------------------------------------------------------------------------


def _set_panel_cik(root: Path, cik: int | str) -> None:
    """Store the panel company's CIK in either shape fundamentals may carry."""
    pd.DataFrame({"cik": [cik]}, index=pd.Index(["PAN"], name="ticker")).to_parquet(
        root / "data" / "edgar" / "fundamentals.parquet"
    )


def _write_contract(root: Path, members: tuple[tuple[str, str, str], ...]) -> None:
    """Stage a coverage contract carrying exactly these issuer rows."""
    issuers = [
        {
            "ticker": ticker,
            "cik": cik,
            "legal_name": legal_name,
            "accessions": [{
                "accession": f"0000000-26-0000{index}",
                "form": "10-Q",
                "filing_date": "2026-07-15",
                "period_of_report": "2026-06-30",
                "retention_state": "not_retained",
            }],
        }
        for index, (ticker, cik, legal_name) in enumerate(members)
    ]
    path = root / bff.COVERAGE_CONTRACT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": "synthetic_contract_issuers_v1",
        "issuers": issuers,
    }, indent=1), encoding="utf-8")


def test_contract_member_sharing_a_panel_cik_under_another_ticker_is_not_listed(
    tmp_path: Path, monkeypatch
) -> None:
    _write_root(tmp_path, contract=False)
    _write_contract(tmp_path, (("ZZZ", "0000000011", "Panel Share Class Inc."),))
    state = _compose(tmp_path, monkeypatch)

    assert "ZZZ" not in state["companies"]
    assert state["summary"]["companies"] == 1  # exactly the panel count
    assert state["summary"]["contract_only_companies"] == 0


@pytest.mark.parametrize("panel_cik", [11, "0000000011"], ids=["int", "text"])
def test_shared_cik_member_is_skipped_for_int_and_digit_text_panel_cik(
    tmp_path: Path, monkeypatch, panel_cik: int | str
) -> None:
    _write_root(tmp_path, contract=False)
    _set_panel_cik(tmp_path, panel_cik)
    _write_contract(tmp_path, (("ZZZ", "0000000011", "Panel Share Class Inc."),))
    state = _compose(tmp_path, monkeypatch)

    assert "ZZZ" not in state["companies"]
    assert state["summary"]["companies"] == 1
    assert state["summary"]["contract_only_companies"] == 0


def test_two_contract_members_sharing_one_cik_list_only_the_first(
    tmp_path: Path, monkeypatch
) -> None:
    _write_root(tmp_path, contract=False)
    _write_contract(tmp_path, (
        ("SSS", "0000000021", "First Share Class Inc."),
        ("TTT", "0000000021", "Second Share Class Inc."),
    ))
    state = _compose(tmp_path, monkeypatch)

    assert list(state["companies"]) == ["PAN", "SSS"]
    assert state["summary"]["companies"] == 2
    assert state["summary"]["contract_only_companies"] == 1
    assert state["companies"]["SSS"]["cik"] == 21


def test_contract_only_row_carries_the_not_evaluable_copy(tmp_path: Path, monkeypatch) -> None:
    _write_root(tmp_path)
    state = _compose(tmp_path, monkeypatch)
    for ticker in ("QQQ", "RRR"):
        assert state["companies"][ticker]["action"] == {
            "key": "limited",
            "en": "Checks not run: not yet evaluable from the broad statements panel",
            "zh": "未运行检查：尚无法从广覆盖报表面板评估",
        }
