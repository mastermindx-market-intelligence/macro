"""FIF coverage step 6 (b3): coverage manifest producer tests (hermetic).

The served issuer is the existing golden AAPL package pair published through
the EXISTING publish path (the ``a1_store`` assembly in
``tests/test_fif_a1_journey_ledger.py``) under a SYNTHETIC identity — entity
``ISS:SYN-ONE``, ticker ``ZZSYNA`` — so no issuer identity literal is needed
here; the CIK is read at runtime from the admitted package manifest.  Two
more core members are never served: one is bound to an issuer with no
generation, the other has no binding at all.

The manifest is checked by the coverage proof itself
(``engine/fundamental_forensics/coverage_proof.py``, merged to main through
the FIF merge train); the proof recomputes every rollup independently, so a
manifest the proof accepts with zero rollup mismatches and zero orphan cells
is a manifest whose cells and rollups agree.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.fundamental_forensics import coverage_manifest as CM  # noqa: E402

PRODUCER = ROOT / "engine" / "fundamental_forensics" / "coverage_manifest.py"
QUERY_SERVICE = ROOT / "engine" / "fundamental_forensics" / "query_service.py"
CLI = ROOT / "scripts" / "fif_coverage_manifest.py"
FIVE_ISSUER = ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"

SYN_ENTITY = "ISS:SYN-ONE"
SYN_TICKER = "ZZSYNA"
SYN_NAME = "Synthetic One Inc."
NINE = "9" * 10
EIGHT = "8" * 10
T_ADMITTED = datetime(2026, 10, 14, tzinfo=timezone.utc)
# After the generation's admission and the tiers cutoff.
AS_OF = "2026-10-22T00:00:00Z"
TIERS_CUTOFF = "2026-10-18T00:00:00Z"

EXPECTED_BLOCKERS = {
    "manifest_draft",
    "manifest_unattested",
    "deep_target_not_met",
    "core_target_not_met",
    "census_identity_mismatch",
    "mixed_source_generations",
}
# The frozen C2 thresholds ship with the coverage proof on main (#9773); a
# stacked tree that predates them cannot build a manifest at all, so every
# test that builds one skips there (the unit tests below still run).
THRESHOLDS_ABSENT = "frozen C2 thresholds are not in this tree (they land with the coverage proof)"
NEEDS_THRESHOLDS = pytest.mark.skipif(not CM.DEFAULT_THRESHOLDS.is_file(), reason=THRESHOLDS_ABSENT)
BARE_REASON = re.compile(r"[a-z0-9_]+")
NP_FIELDS = (
    "np_kind",
    "np_rule_id",
    "np_rule_version",
    "np_rules_sha256",
    "np_parent_concepts",
    "np_roles_checked",
    "np_children_n",
    "np_children_with_fact_n",
    "np_footing",
    "np_cal_sha256",
    "np_pre_sha256",
    "np_accession",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    """A local production store holding one synthetic-identity generation."""
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
    from engine.fundamental_forensics.ixbrl_raw_ledger import (
        GOLDEN_AAPL_QUERY_ACCESSIONS,
        parse_and_convert_golden_packages,
    )
    from engine.fundamental_forensics.production_lineage import (
        mint_production_lineage_evidence,
    )
    from engine.fundamental_forensics.query_service import CanonicalEntityBinding
    from engine.fundamental_forensics.statement_graph import (
        GOLDEN_AAPL_FIXTURES,
        admit_golden_aapl_package,
    )

    base = tmp_path_factory.mktemp("b3-store")
    fixture_root = base / "fixture-inputs"
    packages = []
    for accession in GOLDEN_AAPL_QUERY_ACCESSIONS:
        source = ROOT / GOLDEN_AAPL_FIXTURES[accession]
        copied = fixture_root / source.name
        shutil.copytree(source, copied)
        packages.append(admit_golden_aapl_package(copied))
    ciks = {package.manifest["cik"] for package in packages}
    assert len(ciks) == 1
    (cik,) = ciks
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    lineage = mint_production_lineage_evidence(
        ledger, tuple(packages), system_available_at=T_ADMITTED
    )
    material = PDS.ProductionDatasetMaterial(
        binding=CanonicalEntityBinding(
            entity_id=SYN_ENTITY, cik=cik, ticker=SYN_TICKER, source_entity_id=cik
        ),
        entity=EntityInput(
            entity_id=SYN_ENTITY,
            cik=cik,
            ticker=SYN_TICKER,
            name=SYN_NAME,
            identity_basis="sec-cik",
            source_entity_id=cik,
        ),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=T_ADMITTED,
        packages=tuple(packages),
        lineage_evidence=lineage,
        security_id="SEC:SYN-ONE",
        listing_key="SYN-ONE",
    )
    store_dir = base / "store"
    publication = PDS.publish_production_dataset(
        PDS.build_production_dataset_store(store_dir), material
    )
    by_form = {package.manifest["form"]: package.manifest for package in packages}
    return {
        "base": base,
        "store_dir": store_dir,
        "cik": cik,
        "generation_id": publication.generation_id,
        "accessions": [package.manifest["accession"] for package in packages],
        "by_form": by_form,
    }


def _contract(served, *, served_binding_cik=None, extra=()):
    cik = served["cik"]
    issuers = [
        {
            "cik": cik,
            "ticker": SYN_TICKER,
            "accessions": [{"accession": a} for a in served["accessions"]],
            "security_master_binding": {
                "issuer_id": SYN_ENTITY,
                "issuer_cik": served_binding_cik or cik,
            },
        },
        {
            "cik": NINE,
            "ticker": "ZZNINE",
            "accessions": [{"accession": "9999999999-26-000001"}],
            "security_master_binding": {"issuer_id": "ISS:SYN-NINE", "issuer_cik": NINE},
        },
        {
            "cik": EIGHT,
            "ticker": "ZZEIGHT",
            "accessions": [{"accession": "8888888888-26-000001"}],
            "security_master_binding": None,
        },
        *extra,
    ]
    return {"schema": CM.COVERAGE_CONTRACT_SCHEMA, "issuers": issuers}


def _tiers(served, *, deep_r2=None):
    cik = served["cik"]
    deep = [{"canonical_cik": cik, "ticker": SYN_TICKER, "mandatory": True}]
    return {
        "schema": CM.TIERS_SCHEMA,
        "cutoff_at": TIERS_CUTOFF,
        "recorded_at": TIERS_CUTOFF,
        "core_1000": [
            {"canonical_cik": cik, "ticker": SYN_TICKER},
            {"canonical_cik": NINE, "ticker": "ZZNINE"},
            {"canonical_cik": EIGHT, "ticker": "ZZEIGHT"},
        ],
        "deep_R1": deep,
        "deep_R2": deep if deep_r2 is None else deep_r2,
    }


def _write(path: Path, document) -> Path:
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def inputs(served, tmp_path_factory):
    if not CM.DEFAULT_THRESHOLDS.is_file():
        pytest.skip(THRESHOLDS_ABSENT)
    base = tmp_path_factory.mktemp("b3-inputs")
    return {
        "tiers_file": _write(base / "tiers.json", _tiers(served)),
        "coverage_file": _write(base / "coverage.json", _contract(served)),
        "store_dir": served["store_dir"],
    }


@pytest.fixture(scope="module")
def manifest(inputs):
    return CM.build_coverage_manifest(as_of=AS_OF, **inputs)


def _cells_for(manifest, cik):
    return [cell for cell in manifest["cells"] if cell["cik"] == cik]


def _issuer(manifest, cik):
    (issuer,) = [issuer for issuer in manifest["issuers"] if issuer["cik"] == cik]
    return issuer


def _prove(manifest_bytes: bytes):
    proof = pytest.importorskip("engine.fundamental_forensics.coverage_proof")
    thresholds = proof.load_thresholds(CM.DEFAULT_THRESHOLDS)
    direct, formula = proof.load_metric_sets(CM.DEFAULT_CATALOG, CM.DEFAULT_FORMULAS, thresholds)
    return proof.prove_coverage(
        manifest_bytes,
        thresholds,
        direct,
        formula,
        proved_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# The proof accepts the manifest
# ---------------------------------------------------------------------------


def test_proof_accepts_the_manifest_with_no_mismatch_and_no_orphans(manifest) -> None:
    report = _prove(CM.render_manifest(manifest))

    assert report["manifest_rollup_mismatch"] == []
    assert report["orphan_cells"] == 0
    assert set(report["orphan_reasons"].values()) <= {0}
    blockers = set(report["acceptance_blockers"])
    assert "rollup_mismatch" not in blockers
    assert "orphan_cells" not in blockers
    # Only the seat-ruled expected blockers of a served-only draft remain.
    assert blockers <= EXPECTED_BLOCKERS
    assert {"manifest_draft", "manifest_unattested"} <= blockers
    assert report["acceptance_eligible"] is False


def test_proof_failing_reasons_are_bare_kernel_codes(manifest) -> None:
    """The proof keys failures by the text after the last ``:`` of a label.

    A verbatim kernel reason (``"<code>: <detail>"``) as ``reason_code``
    would make every failing key a free-text detail; the keys must be the
    bare codes the kernel emits.
    """
    report = _prove(CM.render_manifest(manifest))
    reasons: dict[str, int] = {}
    for tier in report["tiers"].values():
        for reason, count in tier["failing_reasons"].items():
            reasons[reason] = reasons.get(reason, 0) + count
    assert reasons
    assert all(BARE_REASON.fullmatch(reason) for reason in reasons), sorted(reasons)
    assert "missing_standard_fact" in reasons
    assert "slot_not_filed" in reasons
    for cell in manifest["cells"]:
        if "reason_code" in cell:
            assert BARE_REASON.fullmatch(cell["reason_code"]), cell
        if "kernel_reason" in cell:
            code = cell["kernel_reason"].split(":", 1)[0].strip()
            assert cell["reason_code"] in {code, "kernel_reason_unspecified"}, cell


def test_manifest_top_level_shape(manifest, served) -> None:
    assert manifest["schema"] == CM.MANIFEST_SCHEMA
    assert manifest["draft"] is True
    assert manifest["attested"] is False
    assert manifest["basis"] == "served_only"
    assert re.fullmatch(r"served-set/sha256:[0-9a-f]{64}", manifest["source_generation_id"])
    assert manifest["cutoff_at"] == TIERS_CUTOFF
    assert manifest["recorded_at"] == AS_OF
    header = manifest["header"]
    assert set(header["inputs_sha256"]) == {
        "tiers",
        "coverage_contract",
        "thresholds",
        "metric_catalog",
        "metric_formulas",
    }
    assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in header["inputs_sha256"].values())
    assert set(header["not_presented_pack"]) == {
        "pack_id",
        "pack_version",
        "content_sha256",
        "applied_by_kernel",
    }
    # The kernel is built as query_service builds it: no pack is applied.
    assert header["not_presented_pack"]["applied_by_kernel"] is False
    assert header["served_set"] == [
        {"cik": served["cik"], "generation_id": served["generation_id"]}
    ]
    ciks = [issuer["cik"] for issuer in manifest["issuers"]]
    assert ciks == sorted(ciks)
    keys = [(c["cik"], c["period_id"], c["field_id"]) for c in manifest["cells"]]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)
    # No host path rides on the manifest.
    rendered = CM.render_manifest(manifest).decode("utf-8")
    assert str(served["base"]) not in rendered
    assert str(ROOT) not in rendered


def test_rerun_is_byte_identical(inputs, manifest) -> None:
    again = CM.build_coverage_manifest(as_of=AS_OF, **inputs)
    assert CM.render_manifest(again) == CM.render_manifest(manifest)
    assert CM.render_manifest(manifest).endswith(b"\n")


# ---------------------------------------------------------------------------
# Serve states
# ---------------------------------------------------------------------------


def test_unserved_members_get_not_served_on_every_cell(manifest) -> None:
    direct, formula = CM.load_metric_ids(
        CM.DEFAULT_CATALOG.read_bytes(), CM.DEFAULT_FORMULAS.read_bytes()
    )
    metric_count = len(direct) + len(formula)
    expected = {NINE: "no_generation", EIGHT: "no_binding"}
    for cik, state in expected.items():
        issuer = _issuer(manifest, cik)
        assert issuer["serve_state"] == state
        assert issuer["tier_assigned"] == "core"
        assert "generation_id" not in issuer
        assert "deep_pass" not in issuer
        cells = _cells_for(manifest, cik)
        assert len(cells) == 2 * metric_count  # A1 and I1
        assert {c["period_id"] for c in cells} == {"A1", "I1"}
        assert {(c["status"], c["reason_code"]) for c in cells} == {("absent", "not_served")}
        assert {c["source_generation_id"] for c in cells} == {f"unserved:{state}"}
        assert issuer["core_pass"] is False
        assert issuer["present_cells"] == 0
        assert issuer["absent_cells"] == len(cells)


def test_served_member_slots_cells_and_counts(manifest, served) -> None:
    issuer = _issuer(manifest, served["cik"])
    assert issuer["serve_state"] == "served"
    assert issuer["tier_assigned"] == "deep"
    assert issuer["ticker"] == SYN_TICKER
    assert issuer["generation_id"] == served["generation_id"]
    annual = served["by_form"]["10-K"]
    interim = served["by_form"]["10-Q"]
    assert issuer["slots"] == {
        "A1": {"accession": annual["accession"], "period_of_report": annual["period_of_report"]},
        "A2": None,
        "I1": {"accession": interim["accession"], "period_of_report": interim["period_of_report"]},
        "I2": None,
    }
    cells = _cells_for(manifest, served["cik"])
    assert {c["source_generation_id"] for c in cells} == {served["generation_id"]}
    by_key = {(c["period_id"], c["field_id"]): c for c in cells}
    # A served issuer's empty slot is unfiled — never a fallback, and not
    # confused with an unserved issuer.
    for period in ("A2", "I2"):
        slot_cells = [c for c in cells if c["period_id"] == period]
        assert slot_cells
        assert {c["reason_code"] for c in slot_cells} == {"slot_not_filed"}
    assert not any(c.get("reason_code") == "not_served" for c in cells)
    # Production serves no not-presented verdicts: none is counted.
    assert not any(c.get("na_basis") == "not_presented_item" for c in cells)
    assert not any("qualifier" in c for c in cells)
    # Every stored role of the served annual package is present.
    for role in ("primary", "schema", "presentation", "calculation", "definition", "label"):
        assert by_key[("A1", f"package:{role}")]["status"] == "present"
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        assert by_key[("A1", f"statement:{kind}")]["status"] == "present"
    # Windowless components have no production producer yet.
    for pack in [f"PK{n:02d}" for n in range(1, 13)]:
        assert by_key[("*", f"specialist:{pack}")]["reason_code"] == "no_production_producer"
    assert by_key[("*", "journey")]["reason_code"] == "no_production_producer"
    assert by_key[("*", "packet")]["reason_code"] == "packet_request_unfrozen"
    # Kernel answers land unchanged: some values are present on both slots.
    for period in ("A1", "I1"):
        metric_cells = [
            c for c in cells if c["period_id"] == period and c["field_id"].startswith("metric:")
        ]
        assert len(metric_cells) == 50
        assert any(c["status"] == "present" for c in metric_cells)
        for cell in metric_cells:
            if cell["status"] == "absent":
                assert BARE_REASON.fullmatch(cell["reason_code"]), cell
    assert issuer["deep_pass"] is False
    counts = {
        "present": issuer["present_cells"],
        "absent": issuer["absent_cells"],
        "na": issuer["na_cells"],
        "total": len(cells),
    }
    assert sum(counts[k] for k in ("present", "absent", "na")) == counts["total"]
    print("served-issuer cell counts:", json.dumps(counts, sort_keys=True))
    by_reason: dict[str, int] = {}
    for cell in cells:
        label = f"{cell['status']}:{cell.get('reason_code', '')}"
        by_reason[label] = by_reason.get(label, 0) + 1
    print("served-issuer reasons:", json.dumps(by_reason, sort_keys=True))


def test_admitted_after_as_of_is_not_served(inputs, served) -> None:
    early = CM.build_coverage_manifest(as_of="2026-10-13T00:00:00Z", **inputs)
    issuer = _issuer(early, served["cik"])
    assert issuer["serve_state"] == "admitted_after_as_of"
    cells = _cells_for(early, served["cik"])
    assert {(c["status"], c["reason_code"]) for c in cells} == {("absent", "not_served")}
    assert early["header"]["served_set"] == []


@NEEDS_THRESHOLDS
def test_binding_cik_disagreement_is_binding_mismatch(served, tmp_path) -> None:
    coverage = _write(tmp_path / "coverage.json", _contract(served, served_binding_cik=NINE))
    tiers = _write(tmp_path / "tiers.json", _tiers(served))
    out = CM.build_coverage_manifest(
        tiers_file=tiers, coverage_file=coverage, store_dir=served["store_dir"], as_of=AS_OF
    )
    assert _issuer(out, served["cik"])["serve_state"] == "binding_mismatch"


class _MovedDelivery:
    """Wraps a real provider and reports a different delivered generation."""

    def __init__(self, inner):
        self._inner = inner

    def resolve(self, *args):
        result = self._inner.resolve(*args)
        delivery = dict(result.delivery)
        delivery["dataset_generation_id"] = "moved-generation"
        return SimpleNamespace(**{**vars(result), "delivery": delivery})


@pytest.mark.parametrize("moved", ["query", "statement"])
def test_a_moved_generation_refuses_the_manifest(served, moved) -> None:
    from engine.fundamental_forensics.production_datasets import build_production_dataset_store
    from engine.fundamental_forensics.production_provider import (
        ProductionFinancialQueryProvider,
        ProductionFinancialStatementProvider,
    )

    store = build_production_dataset_store(served["store_dir"])
    query = ProductionFinancialQueryProvider(store)
    statement = ProductionFinancialStatementProvider(store)
    if moved == "query":
        query = _MovedDelivery(query)
    else:
        statement = _MovedDelivery(statement)
    as_of = CM.parse_as_of(AS_OF)
    with pytest.raises(CM.CoverageManifestError) as caught:
        CM.serve_issuer(
            served["cik"],
            {"security_master_binding": {"issuer_id": SYN_ENTITY, "issuer_cik": served["cik"]}},
            store=store,
            as_of=as_of,
            policy=CM.QueryPolicy(
                selection=CM.QUERY_SELECTION,
                source_snapshot_at=AS_OF,
                recorded_at=AS_OF,
            ),
            query_provider=query,
            statement_provider=statement,
        )
    assert caught.value.code == "generation_moved"


# ---------------------------------------------------------------------------
# Input refusals
# ---------------------------------------------------------------------------


@NEEDS_THRESHOLDS
def test_deep_rounds_must_agree(served, tmp_path) -> None:
    tiers = _write(
        tmp_path / "tiers.json",
        _tiers(served, deep_r2=[{"canonical_cik": NINE, "ticker": "ZZNINE", "mandatory": True}]),
    )
    coverage = _write(tmp_path / "coverage.json", _contract(served))
    with pytest.raises(CM.CoverageManifestError) as caught:
        CM.build_coverage_manifest(
            tiers_file=tiers, coverage_file=coverage, store_dir=served["store_dir"], as_of=AS_OF
        )
    assert caught.value.code == "deep_rounds_disagree"


def _tiers_doc(deep_r2_ticker: str) -> bytes:
    return json.dumps(
        {
            "schema": CM.TIERS_SCHEMA,
            "cutoff_at": TIERS_CUTOFF,
            "core_1000": [{"canonical_cik": NINE, "ticker": "ZZNINE"}],
            "deep_R1": [{"canonical_cik": NINE, "ticker": "ZZNINE", "mandatory": True}],
            "deep_R2": [{"canonical_cik": NINE, "ticker": deep_r2_ticker, "mandatory": True}],
        }
    ).encode("utf-8")


def test_deep_rounds_must_agree_on_tickers() -> None:
    (member,) = CM.load_tiers(_tiers_doc("ZZNINE")).members
    assert (member.cik, member.ticker, member.tier_assigned) == (NINE, "ZZNINE", "deep")
    with pytest.raises(CM.CoverageManifestError) as caught:
        CM.load_tiers(_tiers_doc("ZZOTHER"))
    assert caught.value.code == "deep_rounds_disagree"
    assert "tickers" in caught.value.message


@NEEDS_THRESHOLDS
def test_a_repeated_contract_cik_refuses(served, tmp_path) -> None:
    repeated = {
        "cik": NINE,
        "ticker": "ZZDUP",
        "accessions": [{"accession": "9999999999-26-000002"}],
        "security_master_binding": None,
    }
    coverage = _write(tmp_path / "coverage.json", _contract(served, extra=(repeated,)))
    tiers = _write(tmp_path / "tiers.json", _tiers(served))
    with pytest.raises(CM.CoverageManifestError) as caught:
        CM.build_coverage_manifest(
            tiers_file=tiers, coverage_file=coverage, store_dir=served["store_dir"], as_of=AS_OF
        )
    assert caught.value.code == "contract_malformed"


@pytest.mark.parametrize(
    "as_of, store, code",
    [
        ("2026-10-22T00:00:00", "store", "as_of_invalid"),
        (AS_OF, "missing", "store_unavailable"),
    ],
)
def test_clock_and_store_refusals(inputs, tmp_path, as_of, store, code) -> None:
    store_dir = inputs["store_dir"] if store == "store" else tmp_path / "absent"
    with pytest.raises(CM.CoverageManifestError) as caught:
        CM.build_coverage_manifest(
            tiers_file=inputs["tiers_file"],
            coverage_file=inputs["coverage_file"],
            store_dir=store_dir,
            as_of=as_of,
        )
    assert caught.value.code == code


# ---------------------------------------------------------------------------
# Slots and periods (unit)
# ---------------------------------------------------------------------------


def _pkg(accession, form, por, filed, accepted):
    return SimpleNamespace(
        manifest={
            "accession": accession,
            "form": form,
            "period_of_report": por,
            "filing_date": filed,
            "source_accepted_at": accepted,
        }
    )


def test_slot_selection_rules() -> None:
    packages = [
        _pkg("0000000001-25-000010", "10-K", "2025-09-27", "2025-10-31", "2025-10-31T10:00:00Z"),
        _pkg("0000000001-25-000011", "10-K/A", "2025-09-27", "2025-12-01", "2025-12-01T10:00:00Z"),
        _pkg("0000000001-24-000010", "20-F/A", "2024-09-28", "2024-11-01", "2024-11-01T10:00:00Z"),
        _pkg("0000000001-26-000020", "10-Q", "2026-06-27", "2026-07-31", "2026-07-31T10:00:00Z"),
        _pkg("0000000001-26-000021", "10-Q", "2026-06-27", "2026-07-31", "2026-07-31T10:00:00Z"),
        _pkg("0000000001-26-000030", "10-Q", "2026-09-26", "2026-10-30", "2026-10-30T10:00:00Z"),
        _pkg("0000000001-26-000040", "8-K", "2026-08-01", "2026-08-01", "2026-08-01T10:00:00Z"),
        # Accepted after the cutoff although filed before it: invisible.
        _pkg("0000000001-26-000050", "10-Q", "2026-03-28", "2026-10-21", "2026-10-22T00:00:01Z"),
    ]
    slots = CM.select_slots(packages, CM.parse_as_of("2026-10-22T00:00:00Z"))
    # The original outranks the later amendment for the same period.
    assert slots[("annual", 1)].accession == "0000000001-25-000010"
    # An amendment alone still fills its period.
    assert slots[("annual", 2)].accession == "0000000001-24-000010"
    # Same period, same clock: the greater accession wins.
    assert slots[("interim", 1)].accession == "0000000001-26-000021"
    assert ("interim", 2) not in slots
    assert slots[("interim", 1)].period_of_report == "2026-06-27"
    assert set(slots) == {("annual", 1), ("annual", 2), ("interim", 1)}


def test_a_filing_dated_after_the_cutoff_is_invisible_though_accepted_before() -> None:
    """Both clocks gate visibility: a filing_date after as_of hides the filing."""
    as_of = CM.parse_as_of("2026-10-22T00:00:00Z")
    early = _pkg("0000000001-26-000020", "10-Q", "2026-06-27", "2026-07-31", "2026-07-31T10:00:00Z")
    late_dated = _pkg(
        "0000000001-26-000060", "10-Q", "2026-09-26", "2026-10-23", "2026-10-21T10:00:00Z"
    )
    slots = CM.select_slots([early, late_dated], as_of)
    assert set(slots) == {("interim", 1)}
    assert slots[("interim", 1)].accession == "0000000001-26-000020"


@pytest.mark.parametrize(
    "field, value",
    [
        ("period_of_report", "20250927"),
        ("period_of_report", "2025-09-27T00:00:00"),
        ("period_of_report", "2025-W39-6"),
        ("filing_date", "20251031"),
    ],
)
def test_a_non_strict_date_makes_a_filing_invisible(field, value) -> None:
    as_of = CM.parse_as_of("2026-10-22T00:00:00Z")
    good = _pkg("0000000001-25-000010", "10-K", "2025-09-27", "2025-10-31", "2025-10-31T10:00:00Z")
    assert set(CM.select_slots([good], as_of)) == {("annual", 1)}
    bad = _pkg("0000000001-25-000010", "10-K", "2025-09-27", "2025-10-31", "2025-10-31T10:00:00Z")
    bad.manifest[field] = value
    assert CM.select_slots([bad], as_of) == {}


def test_duration_choice_longest_annual_shortest_interim() -> None:
    universe = [
        ("2024-09-29", "2025-09-27"),
        ("2025-06-29", "2025-09-27"),
        ("2025-09-28", "2026-06-27"),
        ("2026-03-29", "2026-06-27"),
    ]
    assert CM.duration_for_slot(universe, "2025-09-27", "annual") == ("2024-09-29", "2025-09-27")
    assert CM.duration_for_slot(universe, "2026-06-27", "interim") == ("2026-03-29", "2026-06-27")
    assert CM.duration_for_slot(universe, "2024-12-31", "annual") is None


# ---------------------------------------------------------------------------
# Kernel cell mapping (constructed cells only: production serves no
# not-presented verdicts today, so the mapping is proven on built cells)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def np_pack():
    from engine.fundamental_forensics.not_presented import load_not_presented_pack

    return load_not_presented_pack()


def _np_evidence():
    from engine.fundamental_forensics.not_presented import (
        FOOTING_EXACT,
        NP_KIND_ITEM,
        NotPresentedEvidence,
    )

    return NotPresentedEvidence(
        np_kind=NP_KIND_ITEM,
        rule_id="not_presented.synthetic_item",
        rule_version="1",
        rules_sha256="a" * 64,
        parent_concepts=("us-gaap:DebtCurrent",),
        roles_checked=1,
        children_n=2,
        children_with_fact_n=1,
        footing=FOOTING_EXACT,
        cal_sha256="b" * 64,
        pre_sha256="c" * 64,
        accession="0000000001-25-000010",
    )


def _cell(state, *, reason=None, na_basis=None, evidence=None, qualified=(), metric_id="revenue"):
    from engine.fundamental_forensics.query import PeriodRequest

    return SimpleNamespace(
        metric_id=metric_id,
        period=PeriodRequest.instant("2025-09-27"),
        state=state,
        reason=reason,
        provenance=SimpleNamespace(
            na_basis=na_basis,
            not_presented=evidence,
            qualified_not_presented=qualified,
            reason=None,
        ),
    )


def _map(cell, np_pack, period_id="A1"):
    return CM.map_metric_cell(
        cell, cik=NINE, period_id=period_id, source_generation_id="g", np_pack=np_pack
    )


def test_not_presented_cell_carries_every_evidence_field(np_pack) -> None:
    from engine.fundamental_forensics.query import CellState

    evidence = _np_evidence()
    kernel_text = "not_presented_item: synthetic parent has no presented child"
    mapped = _map(
        _cell(
            CellState.NOT_APPLICABLE,
            reason=kernel_text,
            na_basis="not_presented_item",
            evidence=evidence,
            metric_id="short_term_debt",
        ),
        np_pack,
    )
    assert mapped == {
        "cik": NINE,
        "period_id": "A1",
        "field_id": "metric:short_term_debt",
        "source_generation_id": "g",
        "status": "not_applicable",
        "reason_code": "not_presented_item",
        "kernel_reason": kernel_text,
        "na_basis": "not_presented_item",
        **evidence.to_dict(),
    }
    assert set(NP_FIELDS) <= set(mapped)


def test_qualified_value_carries_a_qualifier_and_policy(np_pack) -> None:
    from engine.fundamental_forensics.query import CellState

    mapped = _map(
        _cell(CellState.VALUE, qualified=("short_term_debt",), metric_id="total_debt"), np_pack
    )
    assert mapped == {
        "cik": NINE,
        "period_id": "A1",
        "field_id": "metric:total_debt",
        "source_generation_id": "g",
        "status": "present",
        "reason_code": "present",
        "qualifier": "qualified_not_presented: short_term_debt",
        "qualifier_policy": f"{np_pack.pack_id}/{np_pack.pack_version}",
    }
    assert re.fullmatch(r"\S+/\S+", mapped["qualifier_policy"])
    plain = _map(_cell(CellState.VALUE, metric_id="total_debt"), np_pack)
    assert "qualifier" not in plain and "qualifier_policy" not in plain


class _CollidingEvidence:
    """A not-presented evidence object whose dict names a cell key."""

    def __init__(self, key: str) -> None:
        self._key = key

    def to_dict(self):
        return {"np_kind": "item_not_in_composition", self._key: "overwritten"}


@pytest.mark.parametrize(
    "key",
    [
        "status",
        "cik",
        "field_id",
        "source_generation_id",
        "period_id",
        "reason_code",
        "kernel_reason",
        "na_basis",
    ],
)
def test_not_presented_evidence_cannot_overwrite_a_cell_key(np_pack, key) -> None:
    from engine.fundamental_forensics.query import CellState

    cell = _cell(
        CellState.NOT_APPLICABLE,
        reason="not_presented_item: x",
        na_basis="not_presented_item",
        evidence=_CollidingEvidence(key),
    )
    with pytest.raises(CM.CoverageManifestError) as caught:
        _map(cell, np_pack)
    assert caught.value.code == "not_presented_evidence_collision"
    assert key in caught.value.message


def test_class_kernel_and_absent_mapping(np_pack) -> None:
    from engine.fundamental_forensics.query import CellState

    kwargs = dict(cik=NINE, period_id="I1", source_generation_id="g", np_pack=np_pack)
    klass = CM.map_metric_cell(
        _cell(CellState.NOT_APPLICABLE, reason="not_applicable_for_issuer_class"), **kwargs
    )
    assert (klass["na_basis"], klass["reason_code"], klass["kernel_reason"]) == (
        "class_policy",
        "not_applicable_for_issuer_class",
        "not_applicable_for_issuer_class",
    )
    # The class rule matches on the bare code, detail or not.
    detailed = CM.map_metric_cell(
        _cell(CellState.NOT_APPLICABLE, reason="not_applicable_for_issuer_class: sic 6021"),
        **kwargs,
    )
    assert (detailed["na_basis"], detailed["reason_code"]) == (
        "class_policy",
        "not_applicable_for_issuer_class",
    )
    assert detailed["kernel_reason"] == "not_applicable_for_issuer_class: sic 6021"
    kernel = CM.map_metric_cell(_cell(CellState.NOT_APPLICABLE, reason="other"), **kwargs)
    assert kernel["na_basis"] == "kernel"
    missing = CM.map_metric_cell(_cell(CellState.MISSING), **kwargs)
    assert missing == {
        "cik": NINE,
        "period_id": "I1",
        "field_id": "metric:revenue",
        "source_generation_id": "g",
        "status": "absent",
        "reason_code": "kernel_reason_unspecified",
        "kernel_state": "missing",
    }
    evaluable = CM.map_metric_cell(_cell(CellState.NOT_EVALUABLE, reason="why"), **kwargs)
    assert (evaluable["reason_code"], evaluable["kernel_state"]) == ("why", "not_evaluable")
    assert evaluable["kernel_reason"] == "why"


@pytest.mark.parametrize(
    "kernel_text, code",
    [
        ("missing_standard_fact: revenue has no fact for 2025-09-27", "missing_standard_fact"),
        ("missing_dependency: a: b: c", "missing_dependency"),
        ("incompatible_revision_basis", "incompatible_revision_basis"),
        ("Free text without a code", "kernel_reason_unspecified"),
        (": detail only", "kernel_reason_unspecified"),
    ],
)
def test_reason_code_is_the_bare_kernel_code(np_pack, kernel_text, code) -> None:
    from engine.fundamental_forensics.query import CellState

    mapped = _map(_cell(CellState.MISSING, reason=kernel_text), np_pack)
    assert mapped["reason_code"] == code
    assert ":" not in mapped["reason_code"]
    assert mapped["kernel_reason"] == kernel_text


# ---------------------------------------------------------------------------
# Producer hygiene
# ---------------------------------------------------------------------------


def test_producer_carries_no_issuer_identity_literal() -> None:
    contract = json.loads(FIVE_ISSUER.read_text(encoding="utf-8"))
    literals: set[str] = set()
    for issuer in contract["issuers"]:
        literals.add(issuer["ticker"])
        literals.add(issuer["cik"])
        literals.add(str(int(issuer["cik"])))
        for key in ("legal_name", "name"):
            if isinstance(issuer.get(key), str):
                literals.add(issuer[key])
    assert len(literals) >= 15
    for path in (PRODUCER, CLI):
        text = path.read_text(encoding="utf-8")
        for literal in literals:
            pattern = r"(?<![A-Za-z0-9_])" + re.escape(literal) + r"(?![A-Za-z0-9_])"
            assert re.search(pattern, text) is None, (path.name, literal)


def test_producer_never_imports_the_proof_or_scripts() -> None:
    tree = ast.parse(PRODUCER.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(("." * node.level) + (node.module or ""))
    assert imported
    assert not any("coverage_proof" in name for name in imported)
    assert not any(name.split(".")[0] == "scripts" for name in imported)
    assert "yaml.safe_load" in PRODUCER.read_text(encoding="utf-8")
    assert "yaml.load(" not in PRODUCER.read_text(encoding="utf-8")


def _kernel_constructions(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (getattr(node.func, "id", None) or getattr(node.func, "attr", None))
        == "BitemporalMetricQueryEngine"
    ]


def test_kernel_is_built_with_exactly_the_query_service_keywords() -> None:
    """The served-only basis: the producer's kernel is the served kernel.

    ``query_service`` passes no not-presented pack and no filing packages, so
    the producer must not either (production serves no NP verdicts today).
    """
    (producer,) = _kernel_constructions(PRODUCER)
    (service,) = _kernel_constructions(QUERY_SERVICE)
    for call in (producer, service):
        assert not call.args
        assert all(keyword.arg is not None for keyword in call.keywords)  # no **kwargs
    producer_keys = sorted(keyword.arg for keyword in producer.keywords)
    service_keys = sorted(keyword.arg for keyword in service.keywords)
    assert "not_presented_pack" not in producer_keys
    assert "filing_packages" not in producer_keys
    assert producer_keys == service_keys


def test_the_built_kernel_receives_only_the_query_service_keywords(
    inputs, manifest, monkeypatch
) -> None:
    (service,) = _kernel_constructions(QUERY_SERVICE)
    service_keys = {keyword.arg for keyword in service.keywords}
    real = CM.BitemporalMetricQueryEngine
    seen: list[set[str]] = []

    def recording(*args, **kwargs):
        assert not args
        seen.append(set(kwargs))
        return real(**kwargs)

    monkeypatch.setattr(CM, "BitemporalMetricQueryEngine", recording)
    again = CM.build_coverage_manifest(as_of=AS_OF, **inputs)
    assert seen
    assert all(keys == service_keys for keys in seen), seen
    assert CM.render_manifest(again) == CM.render_manifest(manifest)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_writes_the_same_bytes(inputs, manifest, tmp_path) -> None:
    out = tmp_path / "manifest.json"
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--tiers-file",
            str(inputs["tiers_file"]),
            "--coverage-file",
            str(inputs["coverage_file"]),
            "--store-dir",
            str(inputs["store_dir"]),
            "--as-of",
            AS_OF,
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert out.read_bytes() == CM.render_manifest(manifest)
    assert "3 issuers, 1 served" in result.stderr


def test_cli_refusal_exits_two_with_the_code(inputs, tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--tiers-file",
            str(inputs["tiers_file"]),
            "--coverage-file",
            str(inputs["coverage_file"]),
            "--store-dir",
            str(tmp_path / "absent"),
            "--as-of",
            AS_OF,
            "--out",
            str(tmp_path / "manifest.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert "store_unavailable" in result.stderr
    assert not (tmp_path / "manifest.json").exists()
