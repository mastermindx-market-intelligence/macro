"""FIF P1-b (I5, wave 2): the state peer-cohort projection from the store.

Covers the projection ``compose_state`` attaches as ``payload.peer_cohort``:
members come from the pinned coverage contract, issuer ids from the exact-CIK
issuer-master join, each admitted member's table identity (cik and listing
label) from its generation's owner binding (A14), observations from
precomputed statement trees on a (verified-fake) production dataset store,
values on a Decimal basis, and every absence typed in ``member_exclusions``
with the closed code set. All offline: the store and generation loaders are
monkeypatched, never a network call, and the golden provider is proven absent
from the process.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

import scripts.build_fundamental_forensics as bff
from engine.fundamental_forensics.detectors import issuer_class_for_sic
from engine.fundamental_forensics.metric_registry import _content_digest
from engine.fundamental_forensics.peer_cohort import (
    CohortDefinition,
    CohortMember,
    MetricObservation,
    build_cohort_table,
)
from engine.fundamental_forensics.production_datasets import (
    ProductionDatasetError,
    snapshot_core_registry_payload,
)
from engine.fundamental_forensics.query_service import CanonicalEntityBinding

ROOT = Path(__file__).resolve().parents[1]
GEN_AT = "2026-10-12T00:00:00+00:00"
CONTRACT_ID = "synthetic_five_v1"
_MODULES_BEFORE: set = set()

# Five synthetic members (contract order is load-bearing: tables follow it).
#   AAA/BBB/CCC  admitted (sic pinned, generation with trees)
#   CCC          bank SIC: its not-applicable set is exactly the shipped
#                catalog's bank class closure (G0-b), never a ticker key
#   DDD          sic pinned but NO generation      -> production_dataset_absent
#   EEE          generation but NO pinned sic      -> issuer_sic_unavailable
MEMBERS: tuple[tuple[str, str, str | None], ...] = (
    ("AAA", "0000000001", "3571"),
    ("BBB", "0000000002", "7372"),
    ("CCC", "0000000003", "6199"),
    ("DDD", "0000000004", "6022"),
    ("EEE", "0000000005", None),
)
ADMITTED = tuple(entry for entry in MEMBERS if entry[0] in {"AAA", "BBB", "CCC"})
PERIOD_END = "2026-06-30"
REVENUE = {"AAA": "101", "BBB": "202", "CCC": "303", "EEE": "404"}
NET_INCOME = {"AAA": "11", "BBB": "22", "CCC": "33", "EEE": "44"}
# gross_profit is the one cohort metric inside the shipped bank class
# closure, so the bank-SIC member is not applicable for it and only it —
# the class-realistic replacement for the retired ticker-keyed
# field-denominator overlay.
GROSS_PROFIT = {"AAA": "61", "BBB": "122", "CCC": "244", "EEE": "488"}


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
            "issuer_class": issuer_class_for_sic(sic) if sic is not None else "unknown",
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
            "metric_ids": ["revenue", "ni", "gross_profit"],
        },
    }
    path = root / bff.COVERAGE_CONTRACT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=1), encoding="utf-8")

    # The projection derives every class exclusion from the shipped governed
    # registry (G0-b), so each synthetic root stages the REAL catalog bytes —
    # plus the two companion files the loader requires — never a stub: the
    # bank closure exercised below is the shipped one.
    metric_root = ROOT / "config" / "fundamental_forensics" / "metrics" / "v1"
    staged_root = root / "config" / "fundamental_forensics" / "metrics" / "v1"
    (staged_root / "mappings").mkdir(parents=True, exist_ok=True)
    (staged_root / "formulas").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(metric_root / "metric_catalog.yaml", staged_root / "metric_catalog.yaml")
    shutil.copyfile(metric_root / "mappings" / "core.yaml", staged_root / "mappings" / "core.yaml")
    shutil.copyfile(metric_root / "formulas" / "core.yaml", staged_root / "formulas" / "core.yaml")


def _member_tree(ticker: str) -> dict:
    """One precomputed statement tree: revenue + ni cells for the member."""
    rows = []
    for metric_id, value in (
        ("revenue", REVENUE[ticker]),
        ("ni", NET_INCOME[ticker]),
        ("gross_profit", GROSS_PROFIT[ticker]),
    ):
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
    """Only the APIs the projection reads: statement_trees(accession), binding.

    ``binding`` mirrors the real generation property: a manifest with no
    issuer block (``cik=None``) raises ``ProductionDatasetError``, and a
    present block returns the admission-time owner binding verbatim —
    including cik text shapes ``_cik10`` may or may not normalize.
    """

    def __init__(
        self, trees: dict[str, dict], *, cik: str | None = None, ticker: str | None = None
    ) -> None:
        self._trees = trees
        self._binding = (
            CanonicalEntityBinding(
                entity_id=_issuer_id(ticker or ""),
                cik=cik,
                ticker=ticker or "",
                source_entity_id=cik,
            )
            if cik is not None else None
        )

    @property
    def binding(self):
        if self._binding is None:
            raise ProductionDatasetError("synthetic: manifest issuer block absent")
        return self._binding

    def statement_trees(self, accession: str) -> dict:
        try:
            return self._trees[accession]
        except KeyError:
            raise ProductionDatasetError("synthetic: accession absent") from None


def _member_cik(ticker: str) -> str:
    return next(cik for name, cik, _ in MEMBERS if name == ticker)


def _fake_generations(*tickers: str, trees: dict[str, dict] | None = None) -> dict:
    """One admitted-shape generation per ticker; binding = its contract row.

    ``trees`` substitutes per-ticker statement trees (ticker → tree); each is
    wrapped under the member's contract accession as the store would.
    """
    return {
        _issuer_id(ticker): _FakeGeneration(
            {f"0000000-26-00000{ticker[-1]}": (trees or {}).get(ticker) or _member_tree(ticker)},
            cik=_member_cik(ticker),
            ticker=ticker,
        )
        for ticker in tickers
    }


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
    for ticker, _, sic in ADMITTED:
        # the bank-class member is not applicable for exactly the shipped
        # catalog's bank closure (gross_profit here); no ticker key exists
        bank = issuer_class_for_sic(sic) == "bank"
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
                applicable=True,
            ),
            "gross_profit": MetricObservation(
                value=Decimal(GROSS_PROFIT[ticker]),
                period_end=date.fromisoformat(PERIOD_END),
                period_basis="duration",
                applicable=not bank,
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
    generations = _fake_generations("AAA", "BBB", "CCC", "EEE")  # DDD deliberately has none
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
            metric_ids=("revenue", "ni", "gross_profit"),
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

    # ranked vs below-min-n both appear (AAA/BBB/CCC rank revenue and ni;
    # gross_profit loses the bank-SIC member to the shipped catalog's bank
    # class closure, leaving two rows under min_n). The anchor_unavailable
    # emission is covered in tests/test_fundamental_forensics_peer_comparability.py.
    revenue_emission = next(
        e for t in tables for e in t["emissions"] if e["metric_id"] == "revenue"
    )
    assert revenue_emission["emission_state"] == "ranked"
    assert revenue_emission["ranks"] is not None
    ni_emission = next(e for t in tables for e in t["emissions"] if e["metric_id"] == "ni")
    assert ni_emission["emission_state"] == "ranked"
    gross_profit_emission = next(
        e for t in tables for e in t["emissions"] if e["metric_id"] == "gross_profit"
    )
    assert gross_profit_emission["emission_state"] == "below_min_n"
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
    generations = _fake_generations("AAA", "BBB", "CCC", "EEE")
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


def _with_revenue_cells(ticker: str, *cells: tuple[str, str]) -> dict:
    """The member tree with its revenue row carrying the given (start, value) cells."""
    tree = _member_tree(ticker)
    row = next(
        r for r in tree["statements"][0]["rows"] if r["standardized_metric_id"] == "revenue"
    )
    template = row["cells"][0]
    row["cells"] = [
        {**template, "period": {**template["period"], "start": start}, "value": value}
        for start, value in cells
    ]
    return tree


def test_state_peer_cohort_aligns_a_same_end_tie_to_each_anchor(
    tmp_path: Path, monkeypatch
) -> None:
    """Composer wiring: a peer's quarter/year-to-date tie resolves per anchor.

    AAA reports only year-to-date revenue, CCC only the quarter, and BBB both
    on the same end date (year-to-date cell first). AAA's table carries BBB's
    year-to-date value and drops CCC under A35-D1; BBB's and CCC's tables carry
    BBB's quarter value, the default shortest pick.
    """
    trees = {
        "AAA": _with_revenue_cells("AAA", ("2026-01-01", "1001")),
        "BBB": _with_revenue_cells("BBB", ("2026-01-01", "2002"), ("2026-04-01", "202")),
        "CCC": _member_tree("CCC"),
        "EEE": _member_tree("EEE"),
    }
    generations = _fake_generations("AAA", "BBB", "CCC", "EEE", trees=trees)
    _install_store(monkeypatch, generations=generations)
    _write_root(tmp_path)
    cohort = bff.compose_state(tmp_path, generated_at=GEN_AT)["payload"]["peer_cohort"]
    assert cohort is not None
    tables = {table["anchor_issuer_id"]: table for table in cohort["tables"]}

    def revenue_value(anchor: str, member: str) -> str | None:
        emission = next(
            e for e in tables[_issuer_id(anchor)]["emissions"] if e["metric_id"] == "revenue"
        )
        return next(
            (row["value"] for row in emission["rows"] if row["issuer_id"] == _issuer_id(member)),
            None,
        )

    def revenue_codes(anchor: str, member: str) -> set[str]:
        return {
            x["code"] for x in tables[_issuer_id(anchor)]["exclusions"]
            if x["metric_id"] == "revenue" and x["issuer_id"] == _issuer_id(member)
        }

    assert revenue_value("AAA", "AAA") == "1001"
    assert revenue_value("AAA", "BBB") == "2002"
    assert revenue_codes("AAA", "BBB") == set()
    assert revenue_value("AAA", "CCC") is None
    assert "A35-D1" in revenue_codes("AAA", "CCC")
    assert revenue_value("BBB", "BBB") == "202"
    assert revenue_value("CCC", "BBB") == "202"
    assert revenue_codes("CCC", "BBB") == set()


def _registry_role_bytes(*, revenue_version: str | None = None) -> bytes:
    """The shipped registry snapshot as a generation's registry role payload."""
    payload = copy.deepcopy(snapshot_core_registry_payload(ROOT))
    if revenue_version is not None:
        entry = next(
            m for m in payload["catalog"]["metrics"] if m["metric_id"] == "revenue"
        )
        entry["rule"] = {**entry["rule"], "version": revenue_version}
        # a real re-versioned catalog re-pins its own content digest
        payload["catalog"]["content_sha256"] = _content_digest(payload["catalog"])
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _cohort_codes(cohort: dict, anchor: str, member: str, metric_id: str) -> set[str]:
    table = next(
        t for t in cohort["tables"] if t["anchor_issuer_id"] == _issuer_id(anchor)
    )
    return {
        x["code"] for x in table["exclusions"]
        if x["metric_id"] == metric_id and x["issuer_id"] == _issuer_id(member)
    }


def test_generation_metric_versions_reads_each_member_registry() -> None:
    """A35-V1 input: the version comes from the member's pinned registry role."""
    metric_ids = ("revenue", "net_income_loss", "no_such_metric")
    assert bff._generation_metric_versions(_FakeGeneration({}), metric_ids) == {}
    broken = _FakeGeneration({})
    broken.role_payloads = {"registry_json": b"{not json"}
    assert bff._generation_metric_versions(broken, metric_ids) == {}
    malformed = _FakeGeneration({})
    malformed.role_payloads = {"registry_json": b'{"catalog": {}}'}
    assert bff._generation_metric_versions(malformed, metric_ids) == {}

    generation = _FakeGeneration({})
    generation.role_payloads = {"registry_json": _registry_role_bytes()}
    cache: dict = {}
    versions = bff._generation_metric_versions(generation, metric_ids, cache)
    assert versions == {"revenue": "1.0.0", "net_income_loss": "1.0.0"}
    assert bff._generation_metric_versions(generation, metric_ids, cache) is versions

    bumped = _FakeGeneration({})
    bumped.role_payloads = {"registry_json": _registry_role_bytes(revenue_version="1.0.1")}
    assert bff._generation_metric_versions(bumped, metric_ids, cache) == {
        "revenue": "1.0.1",
        "net_income_loss": "1.0.0",
    }


def test_state_peer_cohort_excludes_a_peer_whose_metric_version_differs(
    tmp_path: Path, monkeypatch
) -> None:
    """A35-V1 fires through the composer, not only in the kernel.

    BBB's generation pins a registry whose revenue rule is 1.0.1 while every
    other member pins 1.0.0: revenue is excluded both ways across that line,
    and ni (same version everywhere) is untouched.
    """
    generations = _fake_generations("AAA", "BBB", "CCC", "EEE")
    for ticker in ("AAA", "BBB", "CCC", "EEE"):
        generations[_issuer_id(ticker)].role_payloads = {
            "registry_json": _registry_role_bytes(
                revenue_version="1.0.1" if ticker == "BBB" else None
            )
        }
    _install_store(monkeypatch, generations=generations)
    _write_root(tmp_path)
    cohort = bff.compose_state(tmp_path, generated_at=GEN_AT)["payload"]["peer_cohort"]
    assert cohort is not None

    assert "A35-V1" in _cohort_codes(cohort, "AAA", "BBB", "revenue")
    assert "A35-V1" in _cohort_codes(cohort, "BBB", "AAA", "revenue")
    assert "A35-V1" in _cohort_codes(cohort, "BBB", "CCC", "revenue")
    assert _cohort_codes(cohort, "AAA", "CCC", "revenue") == set()
    assert _cohort_codes(cohort, "AAA", "BBB", "ni") == set()


def test_state_peer_cohort_drops_cells_without_a_unit_or_period_kind(
    tmp_path: Path, monkeypatch
) -> None:
    """A35-K1/U1 input: an observation of unknown basis or unit is not comparable.

    BBB's revenue cell states no unit and CCC's ni cell no period kind; each
    contributes nothing, so the member reports a missing observation rather
    than slipping past the anchor's unit and basis controls.
    """
    trees = {ticker: _member_tree(ticker) for ticker in ("AAA", "BBB", "CCC", "EEE")}
    for ticker, metric_id, mutate in (
        ("BBB", "revenue", lambda cell: {**cell, "unit": None}),
        ("CCC", "ni", lambda cell: {**cell, "period": {**cell["period"], "kind": None}}),
    ):
        row = next(
            r for r in trees[ticker]["statements"][0]["rows"]
            if r["standardized_metric_id"] == metric_id
        )
        row["cells"] = [mutate(cell) for cell in row["cells"]]
    generations = _fake_generations("AAA", "BBB", "CCC", "EEE", trees=trees)
    _install_store(monkeypatch, generations=generations)
    _write_root(tmp_path)
    cohort = bff.compose_state(tmp_path, generated_at=GEN_AT)["payload"]["peer_cohort"]
    assert cohort is not None

    assert "A35-X1" in _cohort_codes(cohort, "AAA", "BBB", "revenue")
    assert "A35-X1" in _cohort_codes(cohort, "AAA", "CCC", "ni")
    assert _cohort_codes(cohort, "AAA", "BBB", "ni") == set()
    assert _cohort_codes(cohort, "AAA", "CCC", "revenue") == set()


def test_a14_two_share_classes_with_one_owner_binding_cik_collapse() -> None:
    """A14 (a): the collapse key is the owner-binding cik the caller supplies.

    Two listings admitted as separate dataset issuers whose owner bindings
    carry ONE cik (the synthetic two-share-class shape) enter the definition
    as two members; the kernel keeps one, the dropped alias emits ``A35-I1``,
    and the kept member's ``tickers`` carries both listing labels.
    """
    issuer_class = issuer_class_for_sic("3571")
    owner_cik = "0000000042"
    members = (
        CohortMember(issuer_id="ISS:TEST-CLSA", cik=owner_cik, tickers=("CLSA",),
                     issuer_class=issuer_class, sic="3571"),
        CohortMember(issuer_id="ISS:TEST-CLSB", cik=owner_cik, tickers=("CLSB",),
                     issuer_class=issuer_class, sic="3571"),
        CohortMember(issuer_id="ISS:TEST-SOLO", cik="0000000043", tickers=("SOLO",),
                     issuer_class=issuer_class, sic="3571"),
    )
    observations = {
        member.issuer_id: {
            "revenue": MetricObservation(
                value=Decimal(index),
                period_end=date.fromisoformat(PERIOD_END),
                period_basis="duration",
                applicable=True,
            ),
        }
        for index, member in enumerate(members, start=1)
    }
    table = build_cohort_table(
        CohortDefinition(
            cohort_id="synthetic:a14",
            anchor_issuer_id="ISS:TEST-CLSA",
            members=members,
            metric_ids=("revenue",),
        ),
        observations,
    )
    assert table.members_n == 2
    kept = {member.issuer_id: member for member in table.members}
    assert set(kept) == {"ISS:TEST-CLSA", "ISS:TEST-SOLO"}
    assert kept["ISS:TEST-CLSA"].cik == owner_cik
    assert kept["ISS:TEST-CLSA"].tickers == ("CLSA", "CLSB")  # both listing labels
    assert [
        (x.issuer_id, x.metric_id, x.code, x.reason)
        for x in table.exclusions if x.code == "A35-I1"
    ] == [("ISS:TEST-CLSB", "", "A35-I1", "duplicate_share_class")]


def test_state_peer_cohort_excludes_a_contract_cik_disagreeing_with_owner_binding(
    tmp_path: Path, monkeypatch
) -> None:
    """A14 (b): a contract cik naming a different issuer never enters a table.

    BBB's generation binds a different issuer's cik than its contract row:
    the member is excluded through the identity exclusion with the
    disagreement reason, never silently re-keyed, and appears in no table —
    not even as an anchor.
    """
    generations = _fake_generations("AAA", "CCC", "EEE")
    generations[_issuer_id("BBB")] = _FakeGeneration(
        {f"0000000-26-00000{'BBB'[-1]}": _member_tree("BBB")},
        cik="0000000099",  # a different issuer than the contract row's cik
        ticker="BBB",
    )
    _install_store(monkeypatch, generations=generations)
    _write_root(tmp_path)
    cohort = bff.compose_state(tmp_path, generated_at=GEN_AT)["payload"]["peer_cohort"]
    assert cohort is not None
    by_ticker = {row["ticker"]: row for row in cohort["member_exclusions"]}
    assert by_ticker["BBB"]["code"] == "issuer_identity_unresolved"
    assert by_ticker["BBB"]["reason"] == (
        "contract cik disagrees with owner binding cik 0000000099"
    )
    assert by_ticker["BBB"]["issuer_id"] == _issuer_id("BBB")
    # never enters any table, as member or anchor
    for table in cohort["tables"]:
        assert _issuer_id("BBB") not in {m["issuer_id"] for m in table["members"]}
    assert [t["anchor_issuer_id"] for t in cohort["tables"]] == [
        _issuer_id(ticker) for ticker in ("AAA", "CCC")
    ]


def test_state_peer_cohort_excludes_a_member_with_no_owner_binding(
    tmp_path: Path, monkeypatch
) -> None:
    """A14 (c): a peer whose generation yields no owner binding is dataset-absent.

    BBB's manifest carries no issuer block at all (the binding property
    raises, as the real generation does) and CCC's binds a cik with no cik10
    form; both are excluded with the dataset-absent code, and the anchor
    table still builds from the remaining members.
    """
    generations = _fake_generations("AAA", "EEE")
    generations[_issuer_id("BBB")] = _FakeGeneration(
        {f"0000000-26-00000{'BBB'[-1]}": _member_tree("BBB")}
        # no cik: the manifest issuer block is absent, binding raises
    )
    generations[_issuer_id("CCC")] = _FakeGeneration(
        {f"0000000-26-00000{'CCC'[-1]}": _member_tree("CCC")},
        cik="not-a-cik",  # present block, cik text with no cik10 form
        ticker="CCC",
    )
    _install_store(monkeypatch, generations=generations)
    _write_root(tmp_path)
    cohort = bff.compose_state(tmp_path, generated_at=GEN_AT)["payload"]["peer_cohort"]
    assert cohort is not None
    by_ticker = {row["ticker"]: row for row in cohort["member_exclusions"]}
    assert by_ticker["BBB"]["code"] == "production_dataset_absent"
    assert by_ticker["CCC"]["code"] == "production_dataset_absent"
    # the anchor table still builds from the remaining members
    assert [t["anchor_issuer_id"] for t in cohort["tables"]] == [_issuer_id("AAA")]
    table_ids = {m["issuer_id"] for t in cohort["tables"] for m in t["members"]}
    assert _issuer_id("BBB") not in table_ids
    assert _issuer_id("CCC") not in table_ids


def test_state_peer_cohort_member_identity_comes_from_the_owner_binding(
    tmp_path: Path, monkeypatch
) -> None:
    """A14 (d): the table's member cik and listing label are the binding's.

    BBB's generation binds the SAME issuer cik in an unpadded text shape and
    a different listing label than its contract row: the member is admitted
    (a text-shape variant is not a disagreement) and its row carries the
    binding's cik in canonical cik10 form and the binding's ticker — the
    contract row's own values never reach the table.
    """
    generations = _fake_generations("AAA", "CCC", "EEE")
    generations[_issuer_id("BBB")] = _FakeGeneration(
        {f"0000000-26-00000{'BBB'[-1]}": _member_tree("BBB")},
        cik="2",  # the contract row's cik 0000000002, unpadded text shape
        ticker="BIND",
    )
    _install_store(monkeypatch, generations=generations)
    _write_root(tmp_path)
    cohort = bff.compose_state(tmp_path, generated_at=GEN_AT)["payload"]["peer_cohort"]
    assert cohort is not None
    assert not [row for row in cohort["member_exclusions"] if row["ticker"] == "BBB"]
    table = next(
        t for t in cohort["tables"] if t["anchor_issuer_id"] == _issuer_id("AAA")
    )
    member = next(m for m in table["members"] if m["issuer_id"] == _issuer_id("BBB"))
    assert member["cik"] == "0000000002"  # _cik10 of the binding's "2"
    assert member["tickers"] == ["BIND"]  # the binding's label, not the contract's
