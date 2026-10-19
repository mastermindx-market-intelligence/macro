"""FIF C2 coverage proof (A36): predeclared thresholds proven by manifest.

Every fixture here is synthetic and small; the real census draft never enters
the repository.  Frozen-target checks are relaxed only through
``thresholds_from_mapping(..., enforce_frozen_targets=False)`` with small
targets (deep 2, core 3) plus a 4-direct/2-formula catalog fixture.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from engine.fundamental_forensics import coverage_proof as coverage_proof_module
from engine.fundamental_forensics.coverage_proof import (
    CoverageProofError,
    CoverageThresholds,
    HARD_MAX_MANIFEST_BYTES,
    load_manifest,
    load_metric_sets,
    load_thresholds,
    prove_coverage,
    render_print,
    thresholds_from_mapping,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_THRESHOLDS = (
    REPO_ROOT / "config" / "fundamental_forensics" / "coverage" / "c2_thresholds_v1.json"
)
REAL_CATALOG = (
    REPO_ROOT / "config" / "fundamental_forensics" / "metrics" / "v1" / "metric_catalog.yaml"
)
REAL_FORMULAS = (
    REPO_ROOT / "config" / "fundamental_forensics" / "metrics" / "v1" / "formulas" / "core.yaml"
)
CONTRACT_PATH = REPO_ROOT / "contracts" / "fundamental_forensics_coverage_proof.v1.schema.json"
CLI_PATH = REPO_ROOT / "scripts" / "fif_coverage_proof.py"

PROVED_AT = datetime(2026, 10, 19, tzinfo=timezone.utc)
THRESHOLDS_SCHEMA = "fundamental_forensics.coverage_thresholds/v1"
MANIFEST_SCHEMA = "fundamental_forensics.coverage_manifest/v1"

DIRECT_IDS = ("alpha", "beta", "gamma", "delta")
FORMULA_IDS = ("phi", "omega")
ALL_METRICS = DIRECT_IDS + FORMULA_IDS
DEEP_PERIODS = ("A1", "A2", "I1", "I2")
CORE_PERIODS = ("A1", "I1")
PACKAGE_ROLES = ("primary", "label")
# The frozen six roles the shipped c2_thresholds_v1 config predeclares; the
# alias tests exercise manifests and thresholds that cover all of them.
SIX_PACKAGE_ROLES = (
    "primary",
    "schema",
    "presentation",
    "calculation",
    "definition",
    "label",
)
STATEMENTS = ("income_statement",)
PACKS = ("PK01",)


# ---------------------------------------------------------------------------
# Fixtures and builders
# ---------------------------------------------------------------------------


def small_thresholds_mapping() -> dict:
    return {
        "schema": THRESHOLDS_SCHEMA,
        "thresholds_id": "test_small_v1",
        "freeze_ref": "tests/test_fundamental_forensics_coverage_proof.py",
        "census_identity": {
            "source_generation_id": "census-test",
            "cutoff_at": "2026-10-18T00:00:00Z",
            "manifest_draft_sha256_prefix": "0" * 20,
        },
        "metric_catalog_id": "fixture_small_catalog",
        "metric_count": 6,
        "direct_metric_count": 4,
        "formula_metric_count": 2,
        "tiers": {
            "deep": {
                "target": 2,
                "periods": list(DEEP_PERIODS),
                "required_package_roles": list(PACKAGE_ROLES),
                "required_statements": list(STATEMENTS),
                "specialist_packs": list(PACKS),
                "require_packet": True,
                "require_journey": True,
            },
            "core": {"target": 3, "periods": list(CORE_PERIODS)},
        },
        "field_presence_bands": [
            {"band": "complete", "min_rate": 1.0},
            {"band": "high", "min_rate": 0.9},
            {"band": "partial", "min_rate": 0.5},
            {"band": "low", "min_rate": 0.0},
        ],
    }


def small_thresholds(**overrides) -> CoverageThresholds:
    mapping = small_thresholds_mapping()
    mapping.update(overrides)
    return thresholds_from_mapping(mapping, enforce_frozen_targets=False)


def six_role_thresholds() -> CoverageThresholds:
    """small_thresholds with all six frozen package roles required."""
    mapping = small_thresholds_mapping()
    deep = dict(mapping["tiers"]["deep"])
    deep["required_package_roles"] = list(SIX_PACKAGE_ROLES)
    tiers = dict(mapping["tiers"])
    tiers["deep"] = deep
    mapping["tiers"] = tiers
    return thresholds_from_mapping(mapping, enforce_frozen_targets=False)


def write_small_catalog(tmp_path: Path) -> tuple[Path, Path]:
    catalog = {
        "schema": "fundamental_forensics.metric_catalog/v1",
        "catalog_id": "fixture_small_catalog",
        "catalog_version": "0.1.0",
        "available_at": "2026-01-01T00:00:00Z",
        "metrics": [{"metric_id": metric_id} for metric_id in ALL_METRICS],
    }
    formulas = {
        "schema": "fundamental_forensics.metric_formulas/v1",
        "formula_pack_id": "fixture_small_formulas",
        "formula_pack_version": "0.1.0",
        "available_at": "2026-01-01T00:00:00Z",
        "formulas": [{"metric_id": metric_id} for metric_id in FORMULA_IDS],
    }
    catalog_path = tmp_path / "metric_catalog.yaml"
    formulas_path = tmp_path / "core.yaml"
    # JSON is valid YAML; the loader reads these through yaml.safe_load.
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    formulas_path.write_text(json.dumps(formulas), encoding="utf-8")
    return catalog_path, formulas_path


def issuer(cik: str, ticker: str, tier: str, **fields) -> dict:
    entry = {
        "cik": cik,
        "ticker": ticker,
        "tier_assigned": tier,
        "deep_pass": False,
        "core_pass": False,
        "present_cells": 0,
        "absent_cells": 0,
        "na_cells": 0,
        "mandatory": False,
        "exclusion_reason": "",
    }
    entry.update(fields)
    return entry


def cell(cik: str, period: str, field_id: str, status: str = "present", **extra) -> dict:
    entry = {
        # cell.tier is deliberately "core" on every cell, including deep
        # members' cells: the proof must never read it as membership.
        "cik": cik,
        "ticker": "FIXT",
        "tier": "core",
        "period_id": period,
        "form": "10-K",
        "accession": "0000000000-00-000000",
        "field_id": field_id,
        "status": status,
        "source_generation_id": "census-test",
        "reason_code": "present" if status == "present" else "",
    }
    entry.update(extra)
    return entry


def standard_members() -> list[dict]:
    return [
        issuer("0000000001", "FAKE", "deep"),
        issuer("0000000002", "FBOGUS", "deep"),
        issuer("0000000003", "FNULL", "core"),
    ]


def deep_component_keys(
    package_roles: tuple[str, ...] = PACKAGE_ROLES,
) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    for period in DEEP_PERIODS:
        for role in package_roles:
            keys.append((period, f"package:{role}"))
        for statement in STATEMENTS:
            keys.append((period, f"statement:{statement}"))
    for pack in PACKS:
        keys.append(("*", f"specialist:{pack}"))
    keys.append(("*", "packet"))
    keys.append(("*", "journey"))
    return keys


def build_manifest(
    members: list[dict],
    *,
    draft: bool = True,
    attested: bool = False,
    drop: frozenset[tuple[str, str, str]] = frozenset(),
    statuses: dict[tuple[str, str, str], str] | None = None,
    header: dict | None = None,
    package_roles: tuple[str, ...] = PACKAGE_ROLES,
) -> dict:
    statuses = statuses or {}
    component_keys = deep_component_keys(package_roles)
    cells: list[dict] = []
    for member in members:
        cik = member["cik"]
        periods = DEEP_PERIODS if member["tier_assigned"] == "deep" else CORE_PERIODS
        for period in periods:
            for metric_id in ALL_METRICS:
                field_id = f"metric:{metric_id}"
                key = (cik, period, field_id)
                if key in drop:
                    continue
                cells.append(cell(cik, period, field_id, statuses.get(key, "present")))
        if member["tier_assigned"] == "deep":
            for period, field_id in component_keys:
                key = (cik, period, field_id)
                if key in drop:
                    continue
                cells.append(cell(cik, period, field_id, statuses.get(key, "present")))

    def scope_pass(cik: str, periods: tuple[str, ...], component_keys=None) -> bool:
        """Mirror the frozen pass rules for the fixture's own rollup fields."""
        for period in periods:
            for metric_id in ALL_METRICS:
                key = (cik, period, f"metric:{metric_id}")
                status = "missing" if key in drop else statuses.get(key, "present")
                if status in ("absent", "slot_absent", "missing") and metric_id not in FORMULA_IDS:
                    return False
        if component_keys is None:
            return True
        for period, field_id in component_keys:
            key = (cik, period, field_id)
            status = "missing" if key in drop else statuses.get(key, "present")
            if field_id.startswith("specialist:"):
                if status not in ("present", "not_applicable"):
                    return False
            elif status != "present":
                return False
        return True

    by_cik: dict[str, dict] = {member["cik"]: member for member in members}
    for cik, member in by_cik.items():
        owned = [item for item in cells if item["cik"] == cik]
        member["present_cells"] = sum(1 for item in owned if item["status"] == "present")
        member["absent_cells"] = sum(
            1 for item in owned if item["status"] in ("absent", "slot_absent")
        )
        member["na_cells"] = sum(1 for item in owned if item["status"] == "not_applicable")
        member["core_pass"] = scope_pass(cik, CORE_PERIODS)
        member["deep_pass"] = (
            scope_pass(cik, DEEP_PERIODS, component_keys)
            if member["tier_assigned"] == "deep"
            else False
        )

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "draft": draft,
        "attested": attested,
        "basis": "census_precheck_companyfacts",
        "cutoff_at": "2026-10-18T00:00:00Z",
        "source_generation_id": "census-test",
        "recorded_at": "2026-10-18T20:50:47Z",
        "cells": cells,
        "issuers": members,
    }
    if header is not None:
        manifest["header"] = header
    return manifest


def run_proof(manifest: dict, thresholds: CoverageThresholds | None = None) -> dict:
    active = thresholds if thresholds is not None else small_thresholds()
    sha = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()
    return prove_coverage(
        manifest, sha, active, DIRECT_IDS, FORMULA_IDS, proved_at=PROVED_AT
    )


def entry_for(report: dict, cik: str) -> dict:
    return next(item for item in report["issuers"] if item["cik"] == cik)


def refuse(manifest: dict, code: str, thresholds: CoverageThresholds | None = None) -> None:
    with pytest.raises(CoverageProofError) as excinfo:
        run_proof(manifest, thresholds)
    assert excinfo.value.code == code


# ---------------------------------------------------------------------------
# 1. Shipped thresholds + real repository catalog
# ---------------------------------------------------------------------------


def test_shipped_thresholds_and_real_catalog() -> None:
    thresholds = load_thresholds(SHIPPED_THRESHOLDS)
    assert thresholds.deep_target == 250
    assert thresholds.core_target == 1000
    assert thresholds.deep_periods == ("A1", "A2", "I1", "I2")
    assert thresholds.core_periods == ("A1", "I1")
    assert thresholds.content_sha256 == hashlib.sha256(SHIPPED_THRESHOLDS.read_bytes()).hexdigest()

    direct_ids, formula_ids = load_metric_sets(REAL_CATALOG, REAL_FORMULAS, thresholds)
    assert len(direct_ids) == 40
    assert len(formula_ids) == 10
    assert not set(direct_ids) & set(formula_ids)
    assert len(set(direct_ids) | set(formula_ids)) == thresholds.metric_count

    # The predeclared counts bind the catalog: a small-thresholds view of the
    # real catalog is refused as drift.
    with pytest.raises(CoverageProofError) as excinfo:
        load_metric_sets(REAL_CATALOG, REAL_FORMULAS, small_thresholds())
    assert excinfo.value.code == "catalog_drift"


# ---------------------------------------------------------------------------
# 2. Frozen targets and band shape
# ---------------------------------------------------------------------------


def test_frozen_target_and_band_shape_refusals() -> None:
    base = json.loads(SHIPPED_THRESHOLDS.read_text())

    for tier, value in (("deep", 249), ("deep", 251), ("core", 1001)):
        mutated = copy.deepcopy(base)
        mutated["tiers"][tier]["target"] = value
        with pytest.raises(CoverageProofError) as excinfo:
            thresholds_from_mapping(mutated)
        assert excinfo.value.code == "frozen_target"

    band_cases: list[dict] = [
        # Not strictly descending.
        [
            {"band": "complete", "min_rate": 1.0},
            {"band": "high", "min_rate": 0.9},
            {"band": "partial", "min_rate": 0.9},
            {"band": "low", "min_rate": 0.0},
        ],
        # Ascending order.
        [
            {"band": "low", "min_rate": 0.0},
            {"band": "partial", "min_rate": 0.5},
            {"band": "high", "min_rate": 0.9},
            {"band": "complete", "min_rate": 1.0},
        ],
        # First band is not complete at 1.0.
        [
            {"band": "complete", "min_rate": 0.9},
            {"band": "high", "min_rate": 0.5},
            {"band": "low", "min_rate": 0.0},
        ],
        # Last band does not sit at 0.0.
        [
            {"band": "complete", "min_rate": 1.0},
            {"band": "high", "min_rate": 0.9},
            {"band": "low", "min_rate": 0.1},
        ],
    ]
    for bands in band_cases:
        mutated = copy.deepcopy(base)
        mutated["field_presence_bands"] = bands
        with pytest.raises(CoverageProofError) as excinfo:
            thresholds_from_mapping(mutated)
        assert excinfo.value.code == "band_shape"


# ---------------------------------------------------------------------------
# 3. Membership comes from issuers[]
# ---------------------------------------------------------------------------


def test_membership_comes_from_issuers_not_cells() -> None:
    members = standard_members()
    manifest = build_manifest(members)
    # Two extra CIKs appear only in cells[]; they are orphans, never members.
    manifest["cells"].append(cell("0000000099", "A1", "metric:alpha"))
    manifest["cells"].append(cell("0000000098", "I1", "metric:beta"))
    report = run_proof(manifest)

    assert report["tiers"]["core"]["members"] == 3
    assert report["tiers"]["deep"]["members"] == 2
    assert report["orphan_cells"] == 2
    # Every cell is tagged tier "core" by the builder (including the deep
    # members' A2/I2 cells); deep membership and deep pass still hold.
    deep_entries = [item for item in report["issuers"] if item["tier"] == "deep"]
    assert {item["cik"] for item in deep_entries} == {"0000000001", "0000000002"}
    assert all(item["deep_pass"] for item in deep_entries)


# ---------------------------------------------------------------------------
# 4. Missing required cell
# ---------------------------------------------------------------------------


def test_missing_required_cell_fails_with_cell_missing() -> None:
    members = standard_members()
    manifest = build_manifest(members, drop=frozenset({("0000000001", "A1", "metric:alpha")}))
    report = run_proof(manifest)

    entry = entry_for(report, "0000000001")
    assert entry["core_pass"] is False
    assert "A1/metric:alpha:cell_missing" in entry["failed_fields"]
    assert "0000000001" in report["incomplete_issuers"]["core"]
    assert "0000000001" in report["incomplete_issuers"]["deep"]
    assert report["tiers"]["core"]["failing_reasons"]["cell_missing"] == 1


# ---------------------------------------------------------------------------
# 5. slot_absent and not_applicable
# ---------------------------------------------------------------------------


def test_slot_absent_counts_absent_and_not_applicable_leaves_denominator() -> None:
    members = standard_members()
    statuses = {
        ("0000000003", "A1", "metric:alpha"): "slot_absent",
        ("0000000003", "I1", "metric:beta"): "not_applicable",
    }
    report = run_proof(build_manifest(members, statuses=statuses))

    assert report["status_normalised"] == {"slot_absent": 1}
    entry = entry_for(report, "0000000003")
    assert entry["core_pass"] is False
    assert "A1/metric:alpha:slot_absent" in entry["failed_fields"]

    core_fields = report["tiers"]["core"]["fields"]
    # Deep members: 12/12 each; core member: 10 present, 1 slot_absent
    # (applicable, not present), 1 explicit N/A outside the denominator.
    assert core_fields["present"] == 12 + 12 + 10
    assert core_fields["applicable"] == 12 + 12 + 11
    assert core_fields["not_applicable"] == 1
    assert core_fields["rate"] == (12 + 12 + 10) / (12 + 12 + 11)


# ---------------------------------------------------------------------------
# 6. Formula withheld vs direct absent
# ---------------------------------------------------------------------------


def test_absent_formula_withheld_and_absent_direct_fails() -> None:
    members = standard_members()
    withheld_manifest = build_manifest(
        members, statuses={("0000000003", "A1", "metric:phi"): "absent"}
    )
    report = run_proof(withheld_manifest)
    entry = entry_for(report, "0000000003")
    assert entry["core_pass"] is True
    assert "A1/metric:phi:absent" in entry["withheld_fields"]
    assert entry["failed_fields"] == []
    core_fields = report["tiers"]["core"]["fields"]
    # The withheld cell sits in applicable but not in present.
    assert core_fields["present"] == 35
    assert core_fields["applicable"] == 36
    assert core_fields["withheld"] == 1

    direct_manifest = build_manifest(
        members, statuses={("0000000003", "A1", "metric:alpha"): "absent"}
    )
    report2 = run_proof(direct_manifest)
    entry2 = entry_for(report2, "0000000003")
    assert entry2["core_pass"] is False
    assert "A1/metric:alpha:absent" in entry2["failed_fields"]


# ---------------------------------------------------------------------------
# 7. Deep components
# ---------------------------------------------------------------------------


def test_deep_pass_requires_every_component() -> None:
    members = standard_members()
    manifest = build_manifest(members, drop=frozenset({("0000000001", "A2", "package:label")}))
    report = run_proof(manifest)

    failing = entry_for(report, "0000000001")
    assert failing["deep_pass"] is False
    assert failing["core_pass"] is True
    assert "A2/package:label:cell_missing" in failing["failed_fields"]
    assert report["tiers"]["deep"]["pass"] == 1
    assert report["tiers"]["core"]["pass"] == 3
    assert report["tiers"]["deep"]["components"]["package:label"]["missing"] == 1

    # A specialist cell that is explicitly not_applicable does not fail deep.
    ok_statuses = {("0000000001", "*", "specialist:PK01"): "not_applicable"}
    ok_report = run_proof(build_manifest(members, statuses=ok_statuses))
    assert entry_for(ok_report, "0000000001")["deep_pass"] is True
    assert ok_report["tiers"]["deep"]["components"]["specialist:PK01"]["not_applicable"] == 1

    # A missing journey cell fails deep while core still passes.
    journey_report = run_proof(
        build_manifest(members, drop=frozenset({("0000000002", "*", "journey")}))
    )
    assert entry_for(journey_report, "0000000002")["deep_pass"] is False
    assert journey_report["tiers"]["core"]["pass"] == 3


# ---------------------------------------------------------------------------
# 8. Field-presence denominators follow membership
# ---------------------------------------------------------------------------


def test_field_denominators_follow_membership_not_cell_census() -> None:
    members = standard_members()
    manifest = build_manifest(members)
    report = run_proof(manifest)

    deep_fields = report["tiers"]["deep"]["fields"]
    core_fields = report["tiers"]["core"]["fields"]
    # Deep: 2 deep members x 6 metrics x 4 deep periods.
    assert deep_fields["applicable"] == 2 * 6 * 4
    assert deep_fields["present"] == 2 * 6 * 4
    # Core: all 3 core members (deep included) x 6 metrics x 2 core periods.
    assert core_fields["applicable"] == 3 * 6 * 2
    assert core_fields["present"] == 3 * 6 * 2
    # The census-print formula — every issuer's metric cells over every period
    # — would count 2*24 + 1*12 = 60, which is neither denominator.
    all_metric_cells = sum(
        1 for item in manifest["cells"] if item["field_id"].startswith("metric:")
    )
    assert all_metric_cells == 60
    assert all_metric_cells not in (deep_fields["applicable"], core_fields["applicable"])


# ---------------------------------------------------------------------------
# 9. Incomplete lists and untruncated failed fields
# ---------------------------------------------------------------------------


def test_incomplete_lists_match_members_minus_pass() -> None:
    members = standard_members()
    statuses = {
        ("0000000001", "A1", "metric:alpha"): "absent",
        ("0000000001", "I1", "metric:beta"): "absent",
        ("0000000002", "A2", "metric:gamma"): "absent",
    }
    report = run_proof(build_manifest(members, statuses=statuses))

    core = report["tiers"]["core"]
    deep = report["tiers"]["deep"]
    # Member 2's absent cell sits on A2, a deep-only period: it fails deep but
    # not core. Member 1 fails both tiers; member 3 passes core.
    assert core["pass"] == 2
    assert deep["pass"] == 0
    assert report["incomplete_issuers"]["core"] == ["0000000001"]
    assert report["incomplete_issuers"]["deep"] == ["0000000001", "0000000002"]
    assert len(report["incomplete_issuers"]["core"]) == core["members"] - core["pass"]
    assert len(report["incomplete_issuers"]["deep"]) == deep["members"] - deep["pass"]

    first = entry_for(report, "0000000001")
    assert set(first["failed_fields"]) == {
        "A1/metric:alpha:absent",
        "I1/metric:beta:absent",
    }


# ---------------------------------------------------------------------------
# 10. Manifest rollup mismatch
# ---------------------------------------------------------------------------


def test_manifest_rollup_mismatch_reports_both_values() -> None:
    members = standard_members()
    manifest = build_manifest(members)
    # Member 1 has 24 metric + 8 package + 4 statement + 1 specialist + 1
    # packet + 1 journey = 39 present cells; the manifest rollup lies.
    manifest["issuers"][0]["present_cells"] = 999
    manifest["issuers"][2]["core_pass"] = False  # proof says True
    report = run_proof(manifest)

    mismatches = {
        (item["cik"], item["field"]): item for item in report["manifest_rollup_mismatch"]
    }
    present = mismatches[("0000000001", "present_cells")]
    assert present["manifest_value"] == 999
    assert present["proof_value"] == 39
    core_pass = mismatches[("0000000003", "core_pass")]
    assert core_pass["manifest_value"] is False
    assert core_pass["proof_value"] is True
    # Deep members compare deep_pass; core-only issuers do not.
    assert ("0000000001", "deep_pass") not in mismatches


# ---------------------------------------------------------------------------
# 11. Acceptance eligibility
# ---------------------------------------------------------------------------


def test_acceptance_eligibility_requires_attested_non_draft() -> None:
    members = standard_members()

    draft_report = run_proof(build_manifest(members, draft=True, attested=False))
    assert draft_report["tiers"]["deep"]["target_met"] is True
    assert draft_report["tiers"]["core"]["target_met"] is True
    assert draft_report["acceptance_eligible"] is False
    assert draft_report["acceptance_blockers"] == ["manifest_draft", "manifest_unattested"]

    attested_report = run_proof(build_manifest(members, draft=False, attested=True))
    assert attested_report["acceptance_eligible"] is True
    assert attested_report["acceptance_blockers"] == []

    missing = build_manifest(members)
    del missing["draft"]
    del missing["attested"]
    missing_report = run_proof(missing)
    assert missing_report["manifest"]["draft"] is None
    assert missing_report["manifest"]["attested"] is None
    assert missing_report["acceptance_eligible"] is False
    assert "manifest_draft" in missing_report["acceptance_blockers"]
    assert "manifest_unattested" in missing_report["acceptance_blockers"]

    shortfall = build_manifest(members, drop=frozenset({("0000000002", "*", "journey")}))
    shortfall_report = run_proof(shortfall)
    assert shortfall_report["acceptance_eligible"] is False
    assert "deep_target_not_met" in shortfall_report["acceptance_blockers"]


# ---------------------------------------------------------------------------
# 12. Refusals with their codes
# ---------------------------------------------------------------------------


def test_refusals_carry_their_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    members = standard_members()

    duplicate = build_manifest(members)
    duplicate["cells"].append(dict(duplicate["cells"][0]))
    refuse(duplicate, "duplicate_cell")

    unknown_status = build_manifest(
        members, statuses={("0000000003", "A1", "metric:alpha"): "maybe"}
    )
    refuse(unknown_status, "status_vocabulary")

    # A dot form whose role is not one of the thresholds config's
    # required_package_roles (primary, label here) is not the declared
    # vocabulary and is still refused.
    dot_form = build_manifest(members)
    dot_form["cells"].append(cell("0000000003", "A1", "package.presentation"))
    refuse(dot_form, "cell_shape")

    no_source = build_manifest(members)
    del no_source["cells"][0]["source_generation_id"]
    refuse(no_source, "cell_shape")

    bad_schema = build_manifest(members)
    bad_schema["schema"] = "fundamental_forensics.coverage_manifest/v2"
    refuse(bad_schema, "manifest_schema")

    bad_tier = build_manifest(members)
    bad_tier["issuers"][2]["tier_assigned"] = "whale"
    refuse(bad_tier, "tier_vocabulary")

    naive = build_manifest(members)
    with pytest.raises(CoverageProofError) as excinfo:
        prove_coverage(
            naive,
            "0" * 64,
            small_thresholds(),
            DIRECT_IDS,
            FORMULA_IDS,
            proved_at=datetime(2026, 10, 19),
        )
    assert excinfo.value.code == "naive_clock"

    oversize = tmp_path / "oversize.json"
    oversize.write_text(" " * 64, encoding="utf-8")
    monkeypatch.setattr(coverage_proof_module, "HARD_MAX_MANIFEST_BYTES", 32)
    with pytest.raises(CoverageProofError) as excinfo:
        load_manifest(oversize)
    assert excinfo.value.code == "manifest_oversize"


# ---------------------------------------------------------------------------
# 12b. Declared legacy alias package.<role> (seat ruling K-V1A-R1)
# ---------------------------------------------------------------------------


def dotted_package_variant(manifest: dict) -> dict:
    """The same manifest with every package cell in the legacy dot spelling."""
    dotted = copy.deepcopy(manifest)
    for item in dotted["cells"]:
        if item["field_id"].startswith("package:"):
            item["field_id"] = "package." + item["field_id"][len("package:"):]
    return dotted


def test_legacy_alias_proves_same_tiers_and_blocks_acceptance() -> None:
    thresholds = six_role_thresholds()
    members = standard_members()
    colon = build_manifest(members, package_roles=SIX_PACKAGE_ROLES)
    dotted_manifest = dotted_package_variant(colon)

    colon_report = run_proof(colon, thresholds)
    dotted_report = run_proof(dotted_manifest, thresholds)

    # All six roles dotted on both deep members across the four deep periods:
    # 2 x 4 x 6 = 48 rewritten cells, and no other cell is affected.
    assert dotted_report["field_id_aliases_applied"] == {"package.": 48}
    assert dotted_report["acceptance_eligible"] is False
    assert dotted_report["acceptance_blockers"] == [
        "legacy_field_id_alias",
        "manifest_draft",
        "manifest_unattested",
    ]
    # Exactly the same tier results as the same manifest in colon form.
    assert dotted_report["tiers"] == colon_report["tiers"]
    assert (
        dotted_report["incomplete_issuers"] == colon_report["incomplete_issuers"]
    )
    assert (
        dotted_report["manifest_rollup_mismatch"]
        == colon_report["manifest_rollup_mismatch"]
    )
    assert dotted_report["orphan_cells"] == colon_report["orphan_cells"]
    assert dotted_report["status_normalised"] == colon_report["status_normalised"]
    assert [entry["deep_pass"] for entry in dotted_report["issuers"]] == [
        entry["deep_pass"] for entry in colon_report["issuers"]
    ]
    assert [entry["core_pass"] for entry in dotted_report["issuers"]] == [
        entry["core_pass"] for entry in colon_report["issuers"]
    ]
    assert dotted_report["tiers"]["deep"]["pass"] == 2
    assert dotted_report["tiers"]["core"]["pass"] == 3


def test_canonical_manifest_reports_zero_aliases() -> None:
    report = run_proof(build_manifest(standard_members()))
    assert report["field_id_aliases_applied"] == {"package.": 0}
    assert "legacy_field_id_alias" not in report["acceptance_blockers"]
    assert report["acceptance_blockers"] == [
        "manifest_draft",
        "manifest_unattested",
    ]


def test_legacy_alias_refuses_unknown_dotted_forms() -> None:
    members = standard_members()
    # None of these roles is one of the small thresholds' required_package_roles
    # (primary, label), and metric.<id> / bare package. are not the declared
    # alias shape at all.
    for bad_field_id in ("package.unknownrole", "metric.revenue", "package."):
        manifest = build_manifest(members)
        manifest["cells"].append(cell("0000000003", "A1", bad_field_id))
        refuse(manifest, "cell_shape")


def test_legacy_alias_and_canonical_spelling_is_duplicate() -> None:
    members = standard_members()
    # build_manifest already carries ("0000000001", "A1", "package:primary");
    # the same cell in the legacy spelling is the same canonical cell.
    manifest = build_manifest(members)
    manifest["cells"].append(cell("0000000001", "A1", "package.primary"))
    refuse(manifest, "duplicate_cell")


# ---------------------------------------------------------------------------
# 13. Zero-denominator issuer
# ---------------------------------------------------------------------------


def test_zero_denominator_gets_null_rate_and_no_applicable_band() -> None:
    members = standard_members()
    statuses = {
        ("0000000003", period, f"metric:{metric_id}"): "not_applicable"
        for period in CORE_PERIODS
        for metric_id in ALL_METRICS
    }
    report = run_proof(build_manifest(members, statuses=statuses))

    entry = entry_for(report, "0000000003")
    assert entry["field_rate"] is None
    assert entry["band"] == "no_applicable_fields"
    assert report["tiers"]["core"]["bands"]["no_applicable_fields"] == 1
    # An explicitly not_applicable metric never fails its issuer.
    assert entry["core_pass"] is True
    core_fields = report["tiers"]["core"]["fields"]
    assert core_fields["applicable"] == 24
    assert core_fields["not_applicable"] == 12
    assert core_fields["rate"] == 1.0


# ---------------------------------------------------------------------------
# 14. Contract conformance
# ---------------------------------------------------------------------------


def test_reports_conform_to_contract() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    members = standard_members()
    statuses = {
        ("0000000001", "A1", "metric:alpha"): "slot_absent",
        ("0000000003", "I1", "metric:beta"): "not_applicable",
        ("0000000003", "A1", "metric:phi"): "absent",
    }
    manifest = build_manifest(members, statuses=statuses)
    manifest["issuers"][0]["present_cells"] = 7
    report = run_proof(manifest)
    jsonschema.validate(report, contract)
    assert report["manifest_rollup_mismatch"]

    clean = run_proof(build_manifest(members, draft=False, attested=True))
    jsonschema.validate(clean, contract)
    jsonschema.validate(run_proof(build_manifest(members)), contract)

    # Alias reports carry the new required key and still conform.
    thresholds = six_role_thresholds()
    colon = build_manifest(standard_members(), package_roles=SIX_PACKAGE_ROLES)
    jsonschema.validate(run_proof(colon, thresholds), contract)
    jsonschema.validate(run_proof(dotted_package_variant(colon), thresholds), contract)


# ---------------------------------------------------------------------------
# 15. CLI
# ---------------------------------------------------------------------------


def _frozen_manifest(tmp_path: Path) -> Path:
    """A full-size synthetic manifest that meets the frozen 250/1000 targets."""
    direct_ids, formula_ids = load_metric_sets(REAL_CATALOG, REAL_FORMULAS)
    metric_ids = sorted(set(direct_ids) | set(formula_ids))
    deep_component_specs: list[tuple[str, str]] = []
    for period in ("A1", "A2", "I1", "I2"):
        for role in ("primary", "schema", "presentation", "calculation", "definition", "label"):
            deep_component_specs.append((period, f"package:{role}"))
        for statement in ("income_statement", "balance_sheet", "cash_flow"):
            deep_component_specs.append((period, f"statement:{statement}"))
    for pack in (f"PK{number:02d}" for number in range(1, 13)):
        deep_component_specs.append(("*", f"specialist:{pack}"))
    deep_component_specs.append(("*", "packet"))
    deep_component_specs.append(("*", "journey"))

    cells: list[dict] = []
    issuers: list[dict] = []
    for number in range(1, 1001):
        cik = f"{number:010d}"
        ticker = f"Z{number:04d}"
        is_deep = number <= 250
        issuers.append(issuer(cik, ticker, "deep" if is_deep else "core"))
        periods = ("A1", "A2", "I1", "I2") if is_deep else ("A1", "I1")
        for period in periods:
            for metric_id in metric_ids:
                cells.append(cell(cik, period, f"metric:{metric_id}"))
        if is_deep:
            for period, field_id in deep_component_specs:
                cells.append(cell(cik, period, field_id))
    manifest_path = tmp_path / "frozen_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": MANIFEST_SCHEMA,
                "draft": True,
                "attested": False,
                "basis": "census_precheck_companyfacts",
                "cutoff_at": "2026-10-18T00:00:00Z",
                "source_generation_id": "census-test",
                "recorded_at": "2026-10-18T20:50:47Z",
                "cells": cells,
                "issuers": issuers,
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


PRINT_PREFIXES = (
    "C2 coverage  cutoff=",
    "deep issuers:   ",
    "core issuers:   ",
    "deep fields:    ",
    "core fields:    ",
    "deep bands:     ",
    "core bands:     ",
    "incomplete:     ",
    "exclusions:     ",
    "acceptance:     ",
)


def test_cli_exit_codes_and_print_block(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)

    def run_cli(*extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "prove",
                "--manifest",
                str(manifest_path),
                "--thresholds",
                str(SHIPPED_THRESHOLDS),
                "--proved-at",
                "2026-10-19T00:00:00Z",
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    ok = run_cli("--print")
    assert ok.returncode == 0, ok.stderr
    report = json.loads(ok.stdout)
    assert report["schema"] == "fundamental_forensics.coverage_proof/v1"
    assert report["tiers"]["deep"]["pass"] == 250
    assert report["tiers"]["core"]["pass"] == 1000
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["manifest_draft", "manifest_unattested"]

    lines = ok.stderr.splitlines()
    assert len(lines) == len(PRINT_PREFIXES)
    for line, prefix in zip(lines, PRINT_PREFIXES):
        assert line.startswith(prefix), line
    assert lines[0].startswith("C2 coverage  cutoff=2026-10-18T00:00:00Z")
    assert lines[1].startswith("deep issuers:   250 / 250")
    assert lines[2].startswith("core issuers:   1000 / 1000")
    assert lines[8] == "exclusions:     none"
    assert lines[9] == "acceptance:     eligible=false  blockers=manifest_draft,manifest_unattested"

    # --out writes the same single JSON document.
    out_path = tmp_path / "report.json"
    filed = run_cli("--out", str(out_path))
    assert filed.returncode == 0, filed.stderr
    assert json.loads(out_path.read_text(encoding="utf-8")) == report

    gated = run_cli("--require-acceptance")
    assert gated.returncode == 4

    bad_thresholds = tmp_path / "bad_thresholds.json"
    mutated = json.loads(SHIPPED_THRESHOLDS.read_text())
    mutated["tiers"]["deep"]["target"] = 249
    bad_thresholds.write_text(json.dumps(mutated), encoding="utf-8")
    refused = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "prove",
            "--manifest",
            str(manifest_path),
            "--thresholds",
            str(bad_thresholds),
            "--proved-at",
            "2026-10-19T00:00:00Z",
        ],
        capture_output=True,
        text=True,
    )
    assert refused.returncode == 2
    assert "frozen_target" in refused.stderr

    naive = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "prove",
            "--manifest",
            str(manifest_path),
            "--thresholds",
            str(SHIPPED_THRESHOLDS),
            "--proved-at",
            "2026-10-19T00:00:00",
        ],
        capture_output=True,
        text=True,
    )
    assert naive.returncode == 2
    assert "naive_clock" in naive.stderr


def test_render_print_block_shape() -> None:
    members = standard_members()
    report = run_proof(build_manifest(members, draft=False, attested=True))
    block = render_print(report)
    lines = block.splitlines()
    assert len(lines) == 10
    assert lines[0] == (
        "C2 coverage  cutoff=2026-10-18T00:00:00Z  "
        "source_generation=census-test  "
        f"manifest={report['manifest']['sha256'][:20]}"
    )
    assert lines[1] == "deep issuers:   2 / 2     (members=2)"
    assert lines[2] == "core issuers:   3 / 3     (members=3)"
    assert lines[3] == "deep fields:    48 / 48   (deep members x A1,A2,I1,I2; N/A excluded; withheld=0)"
    assert lines[4] == "core fields:    36 / 36   (core members x A1,I1; N/A excluded; withheld=0)"
    assert lines[9] == "acceptance:     eligible=true  blockers=none"


def test_cli_threads_alias_roles_into_load_manifest(tmp_path: Path) -> None:
    """The CLI passes the thresholds' role set so a dotted draft is measured."""
    colon = build_manifest(standard_members(), package_roles=SIX_PACKAGE_ROLES)
    manifest_path = tmp_path / "dotted_draft.json"
    manifest_path.write_text(
        json.dumps(dotted_package_variant(colon)), encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "prove",
            "--manifest",
            str(manifest_path),
            "--thresholds",
            str(SHIPPED_THRESHOLDS),
            "--proved-at",
            "2026-10-19T00:00:00Z",
            "--print",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    # 2 deep members x 4 deep periods x 6 roles rewritten by the CLI path too.
    assert report["field_id_aliases_applied"] == {"package.": 48}
    assert "legacy_field_id_alias" in report["acceptance_blockers"]
    assert report["acceptance_eligible"] is False
    acceptance_line = result.stderr.splitlines()[-1]
    assert acceptance_line.startswith("acceptance:     eligible=false")
    assert "legacy_field_id_alias" in acceptance_line


# ---------------------------------------------------------------------------
# 16. Source hygiene scan
# ---------------------------------------------------------------------------


def test_coverage_proof_source_is_pure_and_literal_free() -> None:
    source = (
        REPO_ROOT / "engine" / "fundamental_forensics" / "coverage_proof.py"
    ).read_text(encoding="utf-8")
    for token in ("datetime.now", "time.time", "utcnow", "urllib", "requests", "socket", "boto"):
        assert token not in source, token
    assert re.search(r"[0-9]{10}", source) is None
    for ticker in ("AAPL", "MSFT", "NVDA", "AIR", "ABT"):
        assert ticker not in source
