"""FIF P1-b (I5, wave 2): the state peer-cohort projection from the store.

Covers the projection ``compose_state`` attaches as ``payload.peer_cohort``:
members come from the pinned coverage contract, issuer ids from the exact-CIK
issuer-master join, observations from precomputed statement trees on a
(verified-fake) production dataset store, values on a Decimal basis, and every
absence typed in ``member_exclusions`` with the closed code set. All offline:
the store and generation loaders are monkeypatched, never a network call, and
the golden provider is proven absent from the process.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

import scripts.build_fundamental_forensics as bff
from engine.fundamental_forensics.detectors import issuer_class_for_sic
from engine.fundamental_forensics.peer_cohort import (
    CohortDefinition,
    CohortMember,
    MetricObservation,
    build_cohort_table,
)
from engine.fundamental_forensics.production_datasets import ProductionDatasetError

ROOT = Path(__file__).resolve().parents[1]
GEN_AT = "2026-10-12T00:00:00+00:00"
CONTRACT_ID = "synthetic_five_v1"
_MODULES_BEFORE: set = set()

# Five synthetic members (contract order is load-bearing: tables follow it).
#   AAA/BBB/CCC  admitted (sic pinned, generation with trees)
#   DDD          sic pinned but NO generation      -> production_dataset_absent
#   EEE          generation but NO pinned sic      -> issuer_sic_unavailable
MEMBERS: tuple[tuple[str, str, str | None], ...] = (
    ("AAA", "0000000001", "3571"),
    ("BBB", "0000000002", "7372"),
    ("CCC", "0000000003", "3500"),
    ("DDD", "0000000004", "6022"),
    ("EEE", "0000000005", None),
)
ADMITTED = tuple(entry for entry in MEMBERS if entry[0] in {"AAA", "BBB", "CCC"})
PERIOD_END = "2026-06-30"
REVENUE = {"AAA": "101", "BBB": "202", "CCC": "303", "EEE": "404"}
NET_INCOME = {"AAA": "11", "BBB": "22", "CCC": "33", "EEE": "44"}
# AAA's ni is not applicable per the contract's field-denominator map.
NOT_APPLICABLE = {"AAA": {"ni": "synthetic class exclusion"}}


def _issuer_id(ticker: str) -> str:
    return f"ISS:TEST-{ticker}"


def _write_root(root: Path, *, members: tuple = MEMBERS, master_rows: list | None = None) -> None:
    """Panel + issuer master + synthetic coverage contract under one root."""
    q_dir = root / "data" / "edgar"
    q_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"ticker": "TST", "fiscal_year": 2025, "fiscal_quarter": 2,
         "period_end": "2025-06-30", "filed": "2025-08-01"},
        {"ticker": "TST", "fiscal_year": 2026, "fiscal_quarter": 2,
         "period_end": "2026-06-30", "filed": "2026-08-01"},
    ]).to_parquet(q_dir / "statements_quarterly.parquet", index=False)

    rows = master_rows
    if rows is None:
        rows = [{"issuer_id": _issuer_id(ticker), "cik": cik} for ticker, cik, _ in members]
    target = root / "data" / "reference" / "issuer_master.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(target, index=False)

    issuers = []
    for ticker, cik, sic in members:
        issuer = {
            "ticker": ticker,
            "cik": cik,
            "fiscal_year_end": "--06-30",
            "identity_binding_state": "synthetic",
            "issuer_class": "industrial",
            "legal_name": ticker,
            "accessions": [{
                "accession": f"0000000-26-00000{ticker[-1]}",
                "form": "10-Q",
                "filing_date": "2026-07-15",
                "period_of_report": PERIOD_END,
                "retention_state": "not_retained",
            }],
        }
        if sic is not None:
            issuer["sic"] = sic
        issuers.append(issuer)
    contract = {
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": CONTRACT_ID,
        "issuers": issuers,
        "field_denominator": {
            "metric_ids": ["revenue", "ni"],
            "not_applicable": NOT_APPLICABLE,
        },
    }
    path = root / bff.COVERAGE_CONTRACT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=1), encoding="utf-8")


def _member_tree(ticker: str) -> dict:
    """One precomputed statement tree: revenue + ni cells for the member."""
    rows = []
    for metric_id, value in (("revenue", REVENUE[ticker]), ("ni", NET_INCOME[ticker])):
        rows.append({
            "order": len(rows),
            "depth": 0,
            "concept": f"us-gaap:{metric_id}",
            "abstract": False,
            "as_reported_label": metric_id,
            "preferred_label_role": None,
            "label_role_used": None,
            "presentation_path": (),
            "standardized_metric_id": metric_id,
            "mapping_state": "mapped",
            "mapping_receipt": None,
            "formula_dependencies": (),
            "cells": [{
                "period": {"kind": "duration", "start": "2026-04-01",
                           "end": PERIOD_END, "label": PERIOD_END},
                "value": value,
                "unit": "USD",
                "scale": 0,
                "decimals": 0,
                "dimensions": [],
                "direct_or_calculated": "direct",
                "quality_state": "available",
                "source_receipt": None,
            }],
        })
    return {
        "parsed_document_kind": "inline_xbrl",
        "fact_count": len(rows),
        "context_count": 1,
        "statements": [{
            "statement_type": "income_statement",
            "role_uri": "https://example.com/role/income",
            "title": "Income Statement",
            "columns": [{"kind": "duration", "start": "2026-04-01",
                         "end": PERIOD_END, "label": PERIOD_END}],
            "row_count": len(rows),
            "rows": rows,
        }],
    }


class _FakeGeneration:
    """Only the one API the projection reads: statement_trees(accession)."""

    def __init__(self, trees: dict[str, dict]) -> None:
        self._trees = trees

    def statement_trees(self, accession: str) -> dict:
        try:
            return self._trees[accession]
        except KeyError:
            raise ProductionDatasetError("synthetic: accession absent") from None


def _install_store(monkeypatch, *, generations: dict[str, _FakeGeneration] | None,
                   store_present: bool = True) -> list:
    loads: list[str] = []
    monkeypatch.setattr(
        bff, "build_production_dataset_store",
        lambda: object() if store_present else None,
    )

    def _load(store, issuer_id):
        loads.append(issuer_id)
        if generations is None:
            return None
        return generations.get(issuer_id)

    monkeypatch.setattr(bff, "load_latest_generation", _load)
    return loads


def _expected_observations() -> dict[str, dict[str, MetricObservation]]:
    observations: dict[str, dict[str, MetricObservation]] = {}
    for ticker, _, _ in ADMITTED:
        observations[_issuer_id(ticker)] = {
            "revenue": MetricObservation(
                value=Decimal(REVENUE[ticker]),
                period_end=date.fromisoformat(PERIOD_END),
                period_basis="duration",
                applicable=True,
            ),
            "ni": MetricObservation(
                value=Decimal(NET_INCOME[ticker]),
                period_end=date.fromisoformat(PERIOD_END),
                period_basis="duration",
                # the contract's field-denominator map excludes AAA's ni
                applicable=ticker not in NOT_APPLICABLE or "ni" not in NOT_APPLICABLE[ticker],
            ),
        }
    return observations


def _walk_for_floats(node, path="payload") -> None:
    if isinstance(node, float):
        raise AssertionError(f"binary float leaked into the state {path}")
    if isinstance(node, dict):
        for key, value in node.items():
            _walk_for_floats(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk_for_floats(value, f"{path}[{index}]")


def test_state_peer_cohort_projection_from_store(tmp_path: Path, monkeypatch) -> None:
    _MODULES_BEFORE.update(sys.modules)
    generations = {
        _issuer_id(ticker): _FakeGeneration({f"0000000-26-00000{ticker[-1]}": _member_tree(ticker)})
        for ticker in ("AAA", "BBB", "CCC", "EEE")  # DDD deliberately has none
    }
    sic_calls: list = []
    real_class_for_sic = bff.issuer_class_for_sic
    monkeypatch.setattr(
        bff, "issuer_class_for_sic",
        lambda value: (sic_calls.append(value), real_class_for_sic(value))[1],
    )
    import engine.fundamental_forensics.detectors as detectors
    gated_calls: list = []
    real_gated = detectors._gated_issuer_class
    monkeypatch.setattr(
        detectors, "_gated_issuer_class",
        lambda *args, **kwargs: (gated_calls.append(args), real_gated(*args, **kwargs))[1],
    )
    _install_store(monkeypatch, generations=generations)

    _write_root(tmp_path)
    state = bff.compose_state(tmp_path, generated_at=GEN_AT)
    cohort = state["payload"]["peer_cohort"]
    assert cohort is not None

    # the policy echo equals the imported C1 CohortDefinition defaults
    probe = CohortDefinition(cohort_id="", anchor_issuer_id="", members=(), metric_ids=())
    assert cohort["policy"] == {
        "alignment_mode": probe.alignment_mode,
        "period_tolerance_days": probe.period_tolerance_days,
        "min_n": probe.min_n,
    }
    assert (probe.alignment_mode, probe.period_tolerance_days, probe.min_n) == ("exclude", 45, 3)
    assert cohort["contract_id"] == CONTRACT_ID

    # anchor-each: one table per admitted member, in contract issuer order
    tables = cohort["tables"]
    assert [table["anchor_issuer_id"] for table in tables] == [
        _issuer_id(ticker) for ticker, _, _ in ADMITTED
    ]

    # tables equal build_cohort_table(...).to_dict() byte-for-byte
    expected_members = tuple(
        CohortMember(
            issuer_id=_issuer_id(ticker),
            cik=cik,
            tickers=(ticker,),
            issuer_class=issuer_class_for_sic(sic),
            sic=sic,
        )
        for ticker, cik, sic in ADMITTED
    )
    expected_observations = _expected_observations()
    for anchor_ticker, _, _ in ADMITTED:
        anchor_id = _issuer_id(anchor_ticker)
        definition = CohortDefinition(
            cohort_id=f"{CONTRACT_ID}:{anchor_id}",
            anchor_issuer_id=anchor_id,
            members=expected_members,
            metric_ids=("revenue", "ni"),
        )
        expected = build_cohort_table(definition, expected_observations).to_dict()
        actual = next(t for t in tables if t["anchor_issuer_id"] == anchor_id)
        assert json.dumps(actual, sort_keys=True) == json.dumps(
            {**expected, "anchor_issuer_id": anchor_id}, sort_keys=True
        )
        assert set(actual) == set(expected) | {"anchor_issuer_id"}  # nothing invented
        # the emission keeps C1's `ranks` key, never `rank`
        assert '"ranks"' in json.dumps(actual)
        assert '"rank":' not in json.dumps(actual)

    # Decimal basis: every emitted row value is canonical decimal text, and no
    # binary float appears anywhere in the payload.
    for table in tables:
        admitted_ids = {_issuer_id(t) for t, _, _ in ADMITTED}
        assert {member["issuer_id"] for member in table["members"]} == admitted_ids
        for emission in table["emissions"]:
            for row in emission["rows"]:
                assert isinstance(row["value"], str)
                assert str(Decimal(row["value"])) == row["value"]  # canonical text, not a float
    _walk_for_floats(state["payload"])

    # ranked vs below-min-n both appear (AAA/BBB/CCC rank revenue; ni loses AAA
    # to the contract's class exclusion, leaving two rows under min_n)
    revenue_emission = next(
        e for t in tables for e in t["emissions"] if e["metric_id"] == "revenue"
    )
    assert revenue_emission["emission_state"] == "ranked"
    assert revenue_emission["ranks"] is not None
    ni_emission = next(e for t in tables for e in t["emissions"] if e["metric_id"] == "ni")
    assert ni_emission["emission_state"] == "below_min_n"
    assert any(
        exclusion["code"] == "A35-B1"
        for t in tables for exclusion in t["exclusions"]
    )

    # member exclusions: exactly one typed row per excluded member, closed codes
    exclusions = cohort["member_exclusions"]
    assert {row["ticker"] for row in exclusions} == {"DDD", "EEE"}
    assert len(exclusions) == 2
    by_ticker = {row["ticker"]: row for row in exclusions}
    assert by_ticker["DDD"]["code"] == "production_dataset_absent"
    assert by_ticker["DDD"]["issuer_id"] == _issuer_id("DDD")
    assert by_ticker["EEE"]["code"] == "issuer_sic_unavailable"
    assert by_ticker["EEE"]["issuer_id"] == _issuer_id("EEE")
    for row in exclusions:
        assert set(row) == {"ticker", "cik", "issuer_id", "code", "reason"}
        assert row["code"] in {
            "issuer_sic_unavailable", "production_dataset_absent", "issuer_identity_unresolved",
        }

    # the SIC-less member never reaches a class or applicability call
    assert set(sic_calls) <= {sic for _, _, sic in ADMITTED}
    assert None not in sic_calls
    assert gated_calls == []

    # the golden provider is never imported or called by the projection itself
    # (sibling suites may import it into this process; only additions count)
    provider_added = {
        name for name in sys.modules
        if name.startswith("engine.fundamental_forensics.") and name not in _MODULES_BEFORE
    }
    assert "engine.fundamental_forensics.production_provider" not in provider_added
    assert "engine.fundamental_forensics.ixbrl_raw_ledger" not in provider_added
    source = (ROOT / "scripts" / "build_fundamental_forensics.py").read_text(encoding="utf-8")
    assert "production_provider" not in source
    assert "GOLDEN_AAPL" not in source
    assert "ISS:" not in source


def test_state_peer_cohort_store_absent_excludes_every_member(tmp_path: Path, monkeypatch) -> None:
    """R4: an unconfigured store is typed for every member — never silent."""
    loads = _install_store(monkeypatch, generations=None, store_present=False)
    _write_root(tmp_path)
    state = bff.compose_state(tmp_path, generated_at=GEN_AT)
    payload = state["payload"]
    assert payload["peer_cohort"] is None
    assert payload["peer_cohort_reason"] == "production_dataset_absent"
    assert payload["schema"] == "fundamental_forensics_state_payload.v1"
    assert loads == []  # no store, no per-issuer reads
    # the state document remains a lawful transport object
    bff._write_state_atomic(tmp_path / "state.json.gz", state)


def test_state_peer_cohort_generation_absent_is_typed_per_member(tmp_path: Path, monkeypatch) -> None:
    """A configured store with no generations at all: same typed reason."""
    _install_store(monkeypatch, generations={}, store_present=True)
    _write_root(tmp_path)
    state = bff.compose_state(tmp_path, generated_at=GEN_AT)
    payload = state["payload"]
    assert payload["peer_cohort"] is None
    assert payload["peer_cohort_reason"] == "production_dataset_absent"


def test_state_peer_cohort_identity_unresolved_is_typed(tmp_path: Path, monkeypatch) -> None:
    """A member whose CIK has no unambiguous authority row never joins a cohort."""
    generations = {
        _issuer_id(ticker): _FakeGeneration({f"0000000-26-00000{ticker[-1]}": _member_tree(ticker)})
        for ticker in ("AAA", "BBB", "CCC", "EEE")
    }
    _install_store(monkeypatch, generations=generations)
    # drop DDD's authority row entirely: its identity is unresolvable
    master_rows = [
        {"issuer_id": _issuer_id(ticker), "cik": cik}
        for ticker, cik, _ in MEMBERS if ticker != "DDD"
    ]
    _write_root(tmp_path, master_rows=master_rows)
    state = bff.compose_state(tmp_path, generated_at=GEN_AT)
    cohort = state["payload"]["peer_cohort"]
    assert cohort is not None
    by_ticker = {row["ticker"]: row for row in cohort["member_exclusions"]}
    assert by_ticker["DDD"]["code"] == "issuer_identity_unresolved"
    assert by_ticker["DDD"]["issuer_id"] is None
    assert by_ticker["EEE"]["code"] == "issuer_sic_unavailable"
    # the three admitted members still produce their anchor tables
    assert [t["anchor_issuer_id"] for t in cohort["tables"]] == [
        _issuer_id(ticker) for ticker, _, _ in ADMITTED
    ]
