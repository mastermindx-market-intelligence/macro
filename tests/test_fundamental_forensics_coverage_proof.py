"""FIF C2 coverage proof (A36): predeclared thresholds proven by manifest.

Every fixture here is synthetic and small; the real census draft never enters
the repository.  Frozen-target checks are relaxed only through
``thresholds_from_mapping(..., enforce_frozen_targets=False)`` with small
targets (deep 2, core 3) plus a 4-direct/2-formula catalog fixture.
"""
from __future__ import annotations

import copy
from collections.abc import Iterator
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
# The four orphan reason keys every report carries, zeros included (ruling
# V1-a r4, R2).
R4_ORPHAN_REASONS = {
    "cik_not_member": 0,
    "period_outside_windows": 0,
    "windowless_period_on_windowed_family": 0,
    "deep_component_not_deep_member": 0,
}


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


def small_thresholds_with_prefix(prefix: str) -> CoverageThresholds:
    """small_thresholds whose census pin is the given draft-sha prefix."""
    mapping = small_thresholds_mapping()
    mapping["census_identity"] = {
        **mapping["census_identity"],
        "manifest_draft_sha256_prefix": prefix,
    }
    return thresholds_from_mapping(mapping, enforce_frozen_targets=False)


def six_role_thresholds(manifest: dict | None = None) -> CoverageThresholds:
    """small_thresholds with all six frozen package roles required.

    With a manifest, the census pin matches that manifest's draft identity
    (see ``identity_prefix_for``)."""
    mapping = small_thresholds_mapping()
    deep = dict(mapping["tiers"]["deep"])
    deep["required_package_roles"] = list(SIX_PACKAGE_ROLES)
    tiers = dict(mapping["tiers"])
    tiers["deep"] = deep
    mapping["tiers"] = tiers
    if manifest is not None:
        mapping["census_identity"] = {
            **mapping["census_identity"],
            "manifest_draft_sha256_prefix": identity_prefix_for(manifest),
        }
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


def cell(
    cik: str,
    period: str,
    field_id: str,
    status: str = "present",
    generation: str = "census-test",
    **extra,
) -> dict:
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
        "source_generation_id": generation,
        # A present cell carries no reason (ruling V1-a r2, F4); every other
        # status may carry one.
        "reason_code": None if status == "present" else "",
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
        """Mirror the frozen pass rules for the fixture's own rollup fields.

        Ruling V1-a r2: a withheld formula metric fails the pass decision,
        and an issuer with zero applicable metric fields never passes, so
        the mirror fails on any non-present applicable metric and on an
        empty applicable set.
        """
        applicable = 0
        for period in periods:
            for metric_id in ALL_METRICS:
                key = (cik, period, f"metric:{metric_id}")
                status = "missing" if key in drop else statuses.get(key, "present")
                if status == "not_applicable":
                    continue
                applicable += 1
                if status != "present":
                    return False
        if applicable == 0:
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
    if attested and not draft:
        # Ruling V1-a r3 (M4): the attestation step records which draft it
        # attests — here the sha256 of the same content in draft form.
        draft_view = dict(manifest)
        draft_view["draft"] = True
        draft_view["attested"] = False
        manifest["manifest_draft_sha256"] = hashlib.sha256(
            manifest_bytes(draft_view)
        ).hexdigest()
    return manifest


def manifest_bytes(manifest: dict) -> bytes:
    """The canonical fixture serialization: what run_proof hands the prover."""
    return json.dumps(manifest, sort_keys=True).encode("utf-8")


def identity_prefix_for(manifest: dict) -> str:
    """The 20-hex census pin a threshold author would pin for this manifest.

    Ruling V1-a r3 (M4): the draft identity is the manifest bytes' sha256 for
    a draft and the declared top-level ``manifest_draft_sha256`` otherwise.
    A non-draft manifest without a valid declaration has no identity, so the
    pin falls back to a value nothing matches.  This mirrors how the real
    c2_thresholds_v1 pin was authored: the sha prefix of the real draft.
    """
    declared = manifest.get("manifest_draft_sha256")
    if manifest.get("draft") is True:
        return hashlib.sha256(manifest_bytes(manifest)).hexdigest()[:20]
    if isinstance(declared, str) and re.fullmatch(r"[0-9a-f]{64}", declared):
        return declared[:20]
    return "0" * 20


def small_thresholds_for(manifest: dict, **overrides) -> CoverageThresholds:
    """small_thresholds whose census pin matches the manifest's draft identity."""
    mapping = small_thresholds_mapping()
    mapping.update(overrides)
    mapping["census_identity"] = {
        **mapping["census_identity"],
        "manifest_draft_sha256_prefix": identity_prefix_for(manifest),
    }
    return thresholds_from_mapping(mapping, enforce_frozen_targets=False)


def run_proof(manifest: dict, thresholds: CoverageThresholds | None = None) -> dict:
    active = thresholds if thresholds is not None else small_thresholds_for(manifest)
    return prove_coverage(
        manifest_bytes(manifest), active, DIRECT_IDS, FORMULA_IDS, proved_at=PROVED_AT
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
    # Ruling V1-a r2 (F1): a withheld formula metric is a failed field for
    # the pass decision, so the issuer no longer passes; it is still
    # reported under withheld and keeps the issuer out of band complete.
    assert entry["core_pass"] is False
    assert "A1/metric:phi:absent" in entry["withheld_fields"]
    assert entry["failed_fields"] == ["A1/metric:phi:formula_inputs_absent"]
    # 11/12 applicable present -> the high band, not complete.
    assert entry["band"] == "high"
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
    assert present["reason"] == "rollup_value_mismatch"
    core_pass = mismatches[("0000000003", "core_pass")]
    assert core_pass["manifest_value"] is False
    assert core_pass["proof_value"] is True
    assert core_pass["reason"] == "rollup_value_mismatch"
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
            manifest_bytes(naive),
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
    members = standard_members()
    colon = build_manifest(members, package_roles=SIX_PACKAGE_ROLES)
    dotted_manifest = dotted_package_variant(colon)
    # The census pin matches the dotted draft's computed identity, so the
    # asserted blocker list isolates the alias blocker.
    thresholds = six_role_thresholds(dotted_manifest)

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
    # Ruling V1-a r2 (F3): an issuer with zero applicable fields never
    # counts toward a tier, so it never passes even though it has no failed
    # field.
    assert entry["core_pass"] is False
    assert entry["failed_fields"] == []
    assert report["tiers"]["core"]["pass"] == 2
    assert report["tiers"]["core"]["target_met"] is False
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
    shipped = json.loads(SHIPPED_THRESHOLDS.read_text())
    shipped_generation = shipped["census_identity"]["source_generation_id"]
    shipped_cutoff = shipped["census_identity"]["cutoff_at"]
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
                cells.append(cell(cik, period, f"metric:{metric_id}", generation=shipped_generation))
        if is_deep:
            for period, field_id in deep_component_specs:
                cells.append(cell(cik, period, field_id, generation=shipped_generation))
    # The manifest's own rollup fields must agree with the proof (every cell
    # present, every issuer complete), or the rollup mismatch itself blocks.
    owned_counts: dict[str, int] = {}
    for item in cells:
        owned_counts[item["cik"]] = owned_counts.get(item["cik"], 0) + 1
    for entry in issuers:
        entry["present_cells"] = owned_counts.get(entry["cik"], 0)
        entry["core_pass"] = True
        entry["deep_pass"] = True
    manifest_path = tmp_path / "frozen_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": MANIFEST_SCHEMA,
                "draft": True,
                "attested": False,
                "basis": "census_precheck_companyfacts",
                "cutoff_at": shipped_cutoff,
                "source_generation_id": shipped_generation,
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
    "deep labels:    ",
    "core labels:    ",
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
    # The synthetic draft's computed sha256 does not start with the shipped
    # pin (the pin is the real draft's prefix) and the manifest is an
    # unattested draft, so ruling V1-a r3 blocks acceptance.  The shipped
    # freeze_ref names the coverage freeze record committed to this
    # repository (#9609), so it resolves and is not a blocker.
    assert report["thresholds"]["freeze_ref_exists"] is True
    assert report["acceptance_blockers"] == [
        "census_identity_mismatch",
        "manifest_draft",
        "manifest_unattested",
    ]

    lines = ok.stderr.splitlines()
    assert len(lines) == len(PRINT_PREFIXES)
    for line, prefix in zip(lines, PRINT_PREFIXES):
        assert line.startswith(prefix), line
    assert lines[0].startswith("C2 coverage  cutoff=2026-10-18T00:00:00Z")
    assert lines[1].startswith("deep issuers:   250 / 250")
    assert lines[2].startswith("core issuers:   1000 / 1000")
    assert lines[10] == "exclusions:     none"
    assert lines[11] == (
        "acceptance:     eligible=false  "
        "blockers=census_identity_mismatch,"
        "manifest_draft,manifest_unattested"
    )

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
    assert len(lines) == 12
    assert lines[0] == (
        "C2 coverage  cutoff=2026-10-18T00:00:00Z  "
        "source_generation=census-test  "
        f"manifest={report['manifest']['sha256'][:20]}"
    )
    assert lines[1] == "deep issuers:   2 / 2     (members=2)"
    assert lines[2] == "core issuers:   3 / 3     (members=3)"
    assert lines[3] == "deep fields:    48 / 48   (deep members x A1,A2,I1,I2; N/A excluded; withheld=0)"
    assert lines[4] == "core fields:    36 / 36   (core members x A1,I1; N/A excluded; withheld=0)"
    assert lines[5] == (
        "deep bands:     complete=2 complete_strict=2 high=0 partial=0 low=0 "
        "no_applicable_fields=0"
    )
    assert lines[6] == (
        "core bands:     complete=3 complete_strict=3 high=0 partial=0 low=0 "
        "no_applicable_fields=0"
    )
    assert lines[7] == (
        "deep labels:    present_strict=48 present_qualified=0 present_composed=0 "
        "na_kernel=0 na_not_presented=0 na_class=0"
    )
    assert lines[8] == (
        "core labels:    present_strict=36 present_qualified=0 present_composed=0 "
        "na_kernel=0 na_not_presented=0 na_class=0"
    )
    assert lines[11] == "acceptance:     eligible=true  blockers=none"


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
# 16. Review-lane rulings V1-a r2 (2026-10-19): probes P1-P5 and blockers
# ---------------------------------------------------------------------------


def test_probe_p2_all_formula_withheld_blocks_pass_and_target() -> None:
    """Reviewer probe P2: every formula metric withheld must not pass."""
    members = standard_members()
    statuses = {
        (member["cik"], period, f"metric:{metric_id}"): "slot_absent"
        for member in members
        for period in (
            DEEP_PERIODS if member["tier_assigned"] == "deep" else CORE_PERIODS
        )
        for metric_id in FORMULA_IDS
    }
    report = run_proof(
        build_manifest(members, statuses=statuses, draft=False, attested=True)
    )

    # Every issuer lands in the partial band (4/6 applicable present) and
    # none counts toward either tier.
    for entry in report["issuers"]:
        assert entry["band"] == "partial", entry
        assert entry["core_pass"] is False
        if entry["tier"] == "deep":
            assert entry["deep_pass"] is False
    assert report["tiers"]["deep"]["pass"] == 0
    assert report["tiers"]["core"]["pass"] == 0
    assert report["tiers"]["deep"]["target_met"] is False
    assert report["tiers"]["core"]["target_met"] is False
    withheld_entry = entry_for(report, "0000000003")
    assert "A1/metric:phi:slot_absent" in withheld_entry["withheld_fields"]
    assert "A1/metric:phi:formula_inputs_absent" in withheld_entry["failed_fields"]
    # 3 core members x 2 core periods x 2 formula metrics withheld in core;
    # 2 deep members x 4 deep periods x 2 in deep.
    assert report["tiers"]["core"]["fields"]["withheld"] == 12
    assert report["tiers"]["deep"]["fields"]["withheld"] == 16
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == [
        "core_target_not_met",
        "deep_target_not_met",
    ]


def test_probe_p1_foreign_identity_and_mixed_generations_block() -> None:
    """Reviewer probe P1: a foreign census identity with cells from three
    generations must not be acceptance-eligible."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["source_generation_id"] = "OTHER"
    manifest["cutoff_at"] = "1999-01-01"
    for index, item in enumerate(manifest["cells"]):
        item["source_generation_id"] = ("OTHER", "gen-a", "gen-b")[index % 3]
    report = run_proof(manifest)

    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == [
        "census_identity_mismatch",
        "mixed_source_generations",
    ]
    identity = report["census_identity"]
    assert identity["mismatched_fields"] == ["cutoff_at", "source_generation_id"]
    assert identity["manifest"]["source_generation_id"] == "OTHER"
    assert identity["thresholds"]["source_generation_id"] == "census-test"
    assert identity["mixed_source_generations"] is True
    counts = identity["cell_source_generation_counts"]
    assert set(counts) == {"OTHER", "gen-a", "gen-b"}
    assert sum(counts.values()) == len(manifest["cells"])


def test_census_identity_blockers_individually() -> None:
    members = standard_members()

    # Blocker 1 (source_generation_id): the manifest's generation differs
    # from the thresholds' pin while its cells stay consistent with it.
    wrong_generation = build_manifest(members, draft=False, attested=True)
    wrong_generation["source_generation_id"] = "census-other"
    for item in wrong_generation["cells"]:
        item["source_generation_id"] = "census-other"
    report = run_proof(wrong_generation)
    assert report["census_identity"]["mismatched_fields"] == ["source_generation_id"]
    assert report["acceptance_blockers"] == ["census_identity_mismatch"]

    # Blocker 1 (cutoff_at): the manifest's cutoff differs from the pin.
    wrong_cutoff = build_manifest(members, draft=False, attested=True)
    wrong_cutoff["cutoff_at"] = "1999-01-01"
    report = run_proof(wrong_cutoff)
    assert report["census_identity"]["mismatched_fields"] == ["cutoff_at"]
    assert report["acceptance_blockers"] == ["census_identity_mismatch"]

    # Blocker 3 (prefix): the thresholds' pin must prefix the draft
    # identity.  For a non-draft manifest the identity is the declared
    # top-level manifest_draft_sha256 (ruling V1-a r3, M4); a pin that does
    # not prefix it is a census identity mismatch.
    wrong_prefix = build_manifest(members, draft=False, attested=True)
    declared_identity = wrong_prefix["manifest_draft_sha256"]
    assert declared_identity[:20] != "f" * 20
    report = run_proof(wrong_prefix, small_thresholds_with_prefix("f" * 20))
    assert report["census_identity"]["mismatched_fields"] == [
        "manifest_draft_sha256_prefix"
    ]
    assert report["census_identity"]["draft_identity"] == declared_identity
    assert (
        report["census_identity"]["draft_identity_basis"]
        == "declared_unverified"
    )
    assert report["acceptance_blockers"] == ["census_identity_mismatch"]
    assert report["manifest_sha256"] == report["manifest"]["sha256"]

    # A pin that prefixes the declared identity adds no blocker.
    right_prefix = build_manifest(members, draft=False, attested=True)
    assert (
        run_proof(
            right_prefix,
            small_thresholds_with_prefix(
                right_prefix["manifest_draft_sha256"][:20]
            ),
        )["acceptance_blockers"]
        == []
    )


def test_mixed_source_generations_blocker_with_counts() -> None:
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["cells"][0]["source_generation_id"] = "gen-a"
    manifest["cells"][1]["source_generation_id"] = "gen-b"
    report = run_proof(manifest)

    assert report["census_identity"]["mismatched_fields"] == []
    counts = report["census_identity"]["cell_source_generation_counts"]
    assert counts == {
        "census-test": len(manifest["cells"]) - 2,
        "gen-a": 1,
        "gen-b": 1,
    }
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["mixed_source_generations"]


def test_freeze_ref_missing_blocks_and_reports_relative_path() -> None:
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    thresholds = small_thresholds_for(manifest, freeze_ref="docs/NO_SUCH_FREEZE.md")
    report = run_proof(manifest, thresholds)
    assert report["thresholds"]["freeze_ref"] == "docs/NO_SUCH_FREEZE.md"
    # Ruling V1-a r3 (M2): the report carries the declared relative path and
    # its resolution flags — never an absolute host path.
    assert "freeze_ref_path" not in report["thresholds"]
    assert report["thresholds"]["freeze_ref_valid"] is True
    assert report["thresholds"]["freeze_ref_exists"] is False
    assert report["thresholds"]["freeze_ref_sha256"] is None
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["freeze_ref_missing"]

    # The small fixture's own freeze_ref (this test file) exists: no blocker.
    ok_report = run_proof(build_manifest(members, draft=False, attested=True))
    assert ok_report["thresholds"]["freeze_ref_exists"] is True
    assert ok_report["thresholds"]["freeze_ref_sha256"] == hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    assert "freeze_ref_missing" not in ok_report["acceptance_blockers"]


def test_probe_p3_zero_applicable_issuer_never_counts() -> None:
    """Reviewer probe P3: an all-not_applicable issuer must not count."""
    members = standard_members()
    statuses = {
        ("0000000001", period, f"metric:{metric_id}"): "not_applicable"
        for period in DEEP_PERIODS
        for metric_id in ALL_METRICS
    }
    report = run_proof(build_manifest(members, statuses=statuses))

    entry = entry_for(report, "0000000001")
    assert entry["band"] == "no_applicable_fields"
    assert entry["field_rate"] is None
    assert entry["failed_fields"] == []
    assert entry["core_pass"] is False
    assert entry["deep_pass"] is False
    assert report["tiers"]["core"]["bands"]["no_applicable_fields"] == 1
    assert report["tiers"]["deep"]["bands"]["no_applicable_fields"] == 1
    assert report["tiers"]["deep"]["pass"] == 1
    assert report["tiers"]["core"]["pass"] == 2
    assert "deep_target_not_met" in report["acceptance_blockers"]
    assert "core_target_not_met" in report["acceptance_blockers"]
    assert report["acceptance_eligible"] is False


def test_probe_p4_present_cell_with_reason_is_refused() -> None:
    """Reviewer probe P4: a present cell carrying a reason is refused."""
    members = standard_members()
    manifest = build_manifest(members)
    manifest["cells"][0]["reason_code"] = "late_filing"
    refuse(manifest, "present_cell_carries_reason")


@pytest.mark.parametrize(
    "status",
    ["stale", "failed_extraction", "incomparable"],
)
def test_new_statuses_fail_and_keep_own_counts(status: str) -> None:
    members = standard_members()
    statuses = {
        ("0000000003", "A1", "metric:alpha"): status,
        ("0000000001", "A2", "metric:alpha"): status,
    }
    report = run_proof(build_manifest(members, statuses=statuses))

    core_entry = entry_for(report, "0000000003")
    deep_entry = entry_for(report, "0000000001")
    assert core_entry["core_pass"] is False
    assert f"A1/metric:alpha:{status}" in core_entry["failed_fields"]
    assert deep_entry["deep_pass"] is False
    assert f"A2/metric:alpha:{status}" in deep_entry["failed_fields"]

    core_fields = report["tiers"]["core"]["fields"]
    deep_fields = report["tiers"]["deep"]["fields"]
    # The status counts in applicable, is reported in its own count, and
    # never merges into absent or withheld.
    assert core_fields[status] == 1
    assert deep_fields[status] == 1
    assert core_fields["applicable"] == 36
    assert deep_fields["applicable"] == 48
    assert core_fields["present"] == 35
    assert deep_fields["present"] == 47
    assert core_fields["withheld"] == 0
    assert deep_fields["withheld"] == 0


def test_new_status_on_deep_component_fails_and_counts() -> None:
    members = standard_members()
    statuses = {("0000000001", "A2", "package:label"): "incomparable"}
    report = run_proof(build_manifest(members, statuses=statuses))

    entry = entry_for(report, "0000000001")
    assert entry["deep_pass"] is False
    assert "A2/package:label:incomparable" in entry["failed_fields"]
    bucket = report["tiers"]["deep"]["components"]["package:label"]
    assert bucket["incomparable"] == 1
    assert bucket["present"] == 7


def test_probe_p5_orphans_and_rollup_mismatch_block() -> None:
    """Reviewer probe P5: orphan cells and rollup lies must block."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["cells"].append(cell("0000000099", "A1", "metric:alpha"))
    manifest["issuers"][0]["present_cells"] = 999
    report = run_proof(manifest)

    assert report["orphan_cells"] == 1
    assert report["orphan_reasons"] == {
        **R4_ORPHAN_REASONS,
        "cik_not_member": 1,
    }
    assert report["manifest_rollup_mismatch"]
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["orphan_cells", "rollup_mismatch"]


def test_out_of_window_metric_cell_is_an_orphan() -> None:
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    # A core member's cell on a deep-only period and a deep member's cell on
    # an undeclared period: both outside the member's declared windows.
    manifest["cells"].append(cell("0000000003", "A2", "metric:alpha"))
    manifest["cells"].append(cell("0000000001", "A3", "metric:alpha"))
    report = run_proof(manifest)

    assert report["orphan_cells"] == 2
    assert report["orphan_reasons"] == {
        **R4_ORPHAN_REASONS,
        "period_outside_windows": 2,
    }
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["orphan_cells"]
    # Neither cell leaks into any denominator.
    assert report["tiers"]["core"]["fields"]["applicable"] == 36
    assert report["tiers"]["deep"]["fields"]["applicable"] == 48


def test_core_periods_outside_deep_are_refused() -> None:
    mapping = small_thresholds_mapping()
    mapping["tiers"]["core"]["periods"] = ["A1", "Q3"]
    with pytest.raises(CoverageProofError) as excinfo:
        thresholds_from_mapping(mapping, enforce_frozen_targets=False)
    assert excinfo.value.code == "period_windows"


def test_real_run_sanity_shipped_thresholds_block(tmp_path: Path) -> None:
    """Real-run sanity: the CLI on the shipped thresholds config with a
    small synthetic manifest reports acceptance_eligible false whenever any
    blocker condition holds."""
    small = build_manifest(standard_members(), draft=True, attested=False)
    shipped = json.loads(SHIPPED_THRESHOLDS.read_text())
    identity = shipped["census_identity"]

    def run_cli(manifest_path: Path) -> subprocess.CompletedProcess[str]:
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
                "--print",
            ],
            capture_output=True,
            text=True,
        )

    # The fixture's census-test identity is not the shipped pin.  The shipped
    # freeze_ref names the committed coverage freeze record, so it resolves.
    mismatched_path = tmp_path / "small_mismatched.json"
    mismatched_path.write_text(json.dumps(small), encoding="utf-8")
    result = run_cli(mismatched_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["acceptance_eligible"] is False
    assert "freeze_ref_missing" not in report["acceptance_blockers"]
    for blocker in (
        "census_identity_mismatch",
        "manifest_draft",
        "manifest_unattested",
        "deep_target_not_met",
        "core_target_not_met",
    ):
        assert blocker in report["acceptance_blockers"], blocker

    # With the shipped identity pinned on the same manifest, the identity
    # blockers disappear; every remaining blocker condition still holds
    # acceptance false.  A non-draft manifest's draft identity is its
    # declared manifest_draft_sha256 (ruling V1-a r3, M4), so the attested
    # fixture declares one that starts with the shipped pin.
    pinned = copy.deepcopy(small)
    pinned["source_generation_id"] = identity["source_generation_id"]
    pinned["cutoff_at"] = identity["cutoff_at"]
    for item in pinned["cells"]:
        item["source_generation_id"] = identity["source_generation_id"]
    pinned["draft"] = False
    pinned["attested"] = True
    pinned["manifest_draft_sha256"] = (
        identity["manifest_draft_sha256_prefix"] + "a" * 44
    )
    pinned_path = tmp_path / "small_pinned.json"
    pinned_path.write_text(json.dumps(pinned), encoding="utf-8")
    pinned_result = run_cli(pinned_path)
    assert pinned_result.returncode == 0, pinned_result.stderr
    pinned_report = json.loads(pinned_result.stdout)
    assert "census_identity_mismatch" not in pinned_report["acceptance_blockers"]
    assert "mixed_source_generations" not in pinned_report["acceptance_blockers"]
    assert pinned_report["acceptance_eligible"] is False
    assert "freeze_ref_missing" not in pinned_report["acceptance_blockers"]
    assert "deep_target_not_met" in pinned_report["acceptance_blockers"]
    assert "core_target_not_met" in pinned_report["acceptance_blockers"]
    line = pinned_result.stderr.splitlines()[-1]
    assert line.startswith("acceptance:     eligible=false")


# ---------------------------------------------------------------------------
# 17. Review-lane rulings V1-a r3 (2026-10-19): gap G1 and findings M1-M5
# ---------------------------------------------------------------------------


def test_present_cells_may_carry_present_or_empty_reason() -> None:
    """G1: the real census draft stamps its present cells with reason_code
    "present" (79,385 cells) or "" (2,832 cells); both spellings are
    accepted.  BASE refused every non-empty reason_code, so this probe
    failed there with present_cell_carries_reason."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    seen: set[str] = set()
    for index, item in enumerate(manifest["cells"]):
        if item["status"] == "present":
            item["reason_code"] = "present" if index % 2 == 0 else ""
            seen.add(item["reason_code"])
    assert seen == {"present", ""}
    report = run_proof(manifest)
    assert report["acceptance_blockers"] == []
    assert report["tiers"]["deep"]["fields"]["present"] == 48
    assert report["tiers"]["core"]["fields"]["present"] == 36


def test_present_cell_with_absent_dependency_reason_is_refused() -> None:
    members = standard_members()
    manifest = build_manifest(members)
    manifest["cells"][0]["reason_code"] = "absent_dependency"
    refuse(manifest, "present_cell_carries_reason")


def test_freeze_ref_absolute_path_is_invalid() -> None:
    """M1: an absolute freeze_ref breaks the relative-POSIX rule and adds
    freeze_ref_invalid; the proof still reports."""
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    thresholds = small_thresholds_for(manifest, freeze_ref="/etc/passwd")
    report = run_proof(manifest, thresholds)
    assert report["thresholds"]["freeze_ref"] == "/etc/passwd"
    assert report["thresholds"]["freeze_ref_valid"] is False
    assert report["thresholds"]["freeze_ref_exists"] is False
    assert report["thresholds"]["freeze_ref_sha256"] is None
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["freeze_ref_invalid"]


def test_freeze_ref_traversal_and_bad_segments_are_invalid() -> None:
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    for bad in ("../outside.md", "engine/..", "docs//map.md", "docs\\map.md"):
        thresholds = small_thresholds_for(manifest, freeze_ref=bad)
        report = run_proof(manifest, thresholds)
        assert report["thresholds"]["freeze_ref_valid"] is False, bad
        assert report["thresholds"]["freeze_ref_sha256"] is None, bad
        assert "freeze_ref_invalid" in report["acceptance_blockers"], bad
        assert "freeze_ref_missing" not in report["acceptance_blockers"], bad


def test_freeze_ref_directory_is_invalid() -> None:
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    thresholds = small_thresholds_for(manifest, freeze_ref="engine")
    report = run_proof(manifest, thresholds)
    assert report["thresholds"]["freeze_ref_valid"] is False
    assert report["thresholds"]["freeze_ref_exists"] is False
    assert report["acceptance_blockers"] == ["freeze_ref_invalid"]


def test_shipped_freeze_ref_is_a_valid_relative_path() -> None:
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    # The shipped census pin does not match this fixture's identity; only
    # the freeze_ref ruling is under test here.
    report = run_proof(manifest, load_thresholds(SHIPPED_THRESHOLDS))
    assert report["thresholds"]["freeze_ref"] == (
        "research/financial_intelligence_fabric/FIF_C2_COVERAGE_FREEZE.md"
    )
    assert report["thresholds"]["freeze_ref_valid"] is True
    assert "freeze_ref_invalid" not in report["acceptance_blockers"]


def _all_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)


def test_report_carries_no_absolute_host_path() -> None:
    """M2: the report is host-independent — no string value starts with "/"
    or names the checkout root — and freeze_ref_sha256 is the sha256 of the
    referenced file's bytes."""
    report = run_proof(build_manifest(standard_members(), draft=False, attested=True))
    for text in _all_strings(report):
        assert not text.startswith("/"), text
        assert str(REPO_ROOT) not in text, text
    assert "freeze_ref_path" not in report["thresholds"]
    fixture_freeze = (
        REPO_ROOT / "tests" / "test_fundamental_forensics_coverage_proof.py"
    )
    assert report["thresholds"]["freeze_ref_sha256"] == hashlib.sha256(
        fixture_freeze.read_bytes()
    ).hexdigest()


def test_missing_rollup_field_blocks_with_field_invalid() -> None:
    """M3: a missing rollup field is a reported mismatch, never a skip."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    del manifest["issuers"][0]["present_cells"]
    report = run_proof(manifest)
    mismatches = {
        (item["cik"], item["field"]): item
        for item in report["manifest_rollup_mismatch"]
    }
    entry = mismatches[("0000000001", "present_cells")]
    assert entry["manifest_value"] is None
    assert entry["proof_value"] == 39
    assert entry["reason"] == "rollup_field_invalid"
    assert report["acceptance_eligible"] is False
    assert "rollup_mismatch" in report["acceptance_blockers"]


def test_ill_typed_rollup_fields_block_with_field_invalid() -> None:
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    manifest["issuers"][2]["core_pass"] = "yes"
    manifest["issuers"][0]["na_cells"] = None
    report = run_proof(manifest)
    mismatches = {
        (item["cik"], item["field"]): item
        for item in report["manifest_rollup_mismatch"]
    }
    for key in (("0000000003", "core_pass"), ("0000000001", "na_cells")):
        entry = mismatches[key]
        assert entry["manifest_value"] is None, key
        assert entry["reason"] == "rollup_field_invalid", key
    assert report["acceptance_blockers"] == ["rollup_mismatch"]


def test_correct_rollups_give_no_mismatch_entry() -> None:
    report = run_proof(build_manifest(standard_members(), draft=False, attested=True))
    assert report["manifest_rollup_mismatch"] == []
    assert "rollup_mismatch" not in report["acceptance_blockers"]


def test_caller_can_no_longer_inject_a_hash() -> None:
    """M4: prove_coverage takes the manifest bytes; the r2 call shape (a
    parsed manifest plus a caller-computed sha256) is refused outright."""
    manifest = build_manifest(standard_members())
    # The exact r2 call no longer even parses: the hash parameter is gone.
    with pytest.raises(TypeError):
        prove_coverage(
            manifest,
            "0" * 64,
            small_thresholds(),
            DIRECT_IDS,
            FORMULA_IDS,
            proved_at=PROVED_AT,
        )
    # Handing over a parsed manifest in the new shape is a typed refusal.
    with pytest.raises(CoverageProofError) as excinfo:
        prove_coverage(
            manifest,
            small_thresholds(),
            DIRECT_IDS,
            FORMULA_IDS,
            proved_at=PROVED_AT,
        )
    assert excinfo.value.code == "manifest_bytes"


def test_draft_prefix_pin_passes_and_fails_on_computed_sha() -> None:
    """M4: for a draft the identity is the bytes' sha256, computed by the
    prover; the pin check always runs."""
    manifest = build_manifest(standard_members())  # a draft
    computed = hashlib.sha256(manifest_bytes(manifest)).hexdigest()
    assert computed[:20] != "f" * 20

    report = run_proof(manifest, small_thresholds_with_prefix(computed[:20]))
    assert report["manifest"]["sha256"] == computed
    assert report["manifest_sha256"] == computed
    assert report["census_identity"]["draft_identity"] == computed
    assert report["census_identity"]["draft_identity_basis"] == "manifest_bytes_sha256"
    assert report["census_identity"]["mismatched_fields"] == []

    failing = run_proof(manifest, small_thresholds_with_prefix("f" * 20))
    assert failing["census_identity"]["mismatched_fields"] == [
        "manifest_draft_sha256_prefix"
    ]
    assert "census_identity_mismatch" in failing["acceptance_blockers"]


def test_attested_manifest_without_declared_draft_sha256_is_blocked() -> None:
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    del manifest["manifest_draft_sha256"]
    report = run_proof(manifest, small_thresholds_for(manifest))
    assert report["census_identity"]["draft_identity"] is None
    # Ruling V1-a r4 (R3): every non-draft's basis is declared_unverified —
    # with or without a well-formed declaration; the r3 three-way split is
    # gone and the null identity plus the pin mismatch carry the absence.
    assert report["census_identity"]["draft_identity_basis"] == (
        "declared_unverified"
    )
    assert report["census_identity"]["draft_identity_trust"] == (
        "attestation_required"
    )
    assert report["census_identity"]["mismatched_fields"] == [
        "manifest_draft_sha256_prefix"
    ]
    assert report["manifest"]["manifest_draft_sha256"] is None
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["census_identity_mismatch"]


def test_attested_manifest_with_matching_declared_sha_is_not_blocked() -> None:
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    declared = manifest["manifest_draft_sha256"]
    report = run_proof(manifest, small_thresholds_with_prefix(declared[:20]))
    assert report["census_identity"]["draft_identity"] == declared
    assert report["census_identity"]["draft_identity_basis"] == (
        "declared_unverified"
    )
    assert report["census_identity"]["mismatched_fields"] == []
    assert report["manifest"]["manifest_draft_sha256"] == declared
    assert report["acceptance_blockers"] == []


def test_package_cell_on_core_only_member_is_an_orphan() -> None:
    """M5 (r3) as generalized by ruling V1-a r4 (R2): a package cell on a
    member that is not deep is an orphan under deep_component_not_deep_member."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["cells"].append(cell("0000000003", "A1", "package:primary"))
    report = run_proof(manifest)
    assert report["orphan_cells"] == 1
    assert report["orphan_reasons"]["deep_component_not_deep_member"] == 1
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["orphan_cells"]


def test_legacy_spelled_package_cell_on_core_member_is_an_orphan() -> None:
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["cells"].append(cell("0000000003", "A1", "package.label"))
    report = run_proof(manifest)
    assert report["orphan_reasons"]["deep_component_not_deep_member"] == 1
    assert "orphan_cells" in report["acceptance_blockers"]
    # The legacy spelling also trips the alias blocker; both block.
    assert "legacy_field_id_alias" in report["acceptance_blockers"]


def test_package_cell_outside_windows_is_an_orphan() -> None:
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    # A deep member's package cell on an undeclared period: the window check
    # covers every field family (M5), so it is a period orphan even though
    # the member is deep.
    manifest["cells"].append(cell("0000000001", "A3", "package:primary"))
    report = run_proof(manifest)
    assert report["orphan_cells"] == 1
    assert report["orphan_reasons"]["period_outside_windows"] == 1
    assert report["orphan_reasons"]["deep_component_not_deep_member"] == 0
    assert report["acceptance_blockers"] == ["orphan_cells"]


def test_real_draft_package_shape_gives_zero_orphans() -> None:
    """M5: the real census draft's package cells sit on deep members in A2
    and I2; a fixture in that shape gives zero orphans."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    package_a2_i2 = [
        item
        for item in manifest["cells"]
        if item["field_id"].startswith("package:")
        and item["period_id"] in ("A2", "I2")
    ]
    assert package_a2_i2
    assert all(item["cik"] in {"0000000001", "0000000002"} for item in package_a2_i2)
    report = run_proof(manifest)
    assert report["orphan_cells"] == 0
    assert report["orphan_reasons"] == dict(R4_ORPHAN_REASONS)


# ---------------------------------------------------------------------------
# 18. Review-lane rulings V1-a r4 (2026-10-19): R1 wildcard escape, R2
#     deep-only families, R3 declared-unverified identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_id",
    ["metric:alpha", "package:primary", "statement:income_statement"],
)
def test_wildcard_period_on_windowed_family_is_an_orphan(field_id: str) -> None:
    """R1: a metric, package or statement cell with period_id "*" is an
    orphan under windowless_period_on_windowed_family, never a counted cell."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    # build_manifest's own rollup for member 1 excludes the appended cell, so
    # a proof that (wrongly) counts it would also report a present_cells
    # rollup mismatch of 39 vs 40.
    manifest["cells"].append(cell("0000000001", "*", field_id))
    report = run_proof(manifest)

    assert report["orphan_cells"] == 1
    assert report["orphan_reasons"] == {
        **R4_ORPHAN_REASONS,
        "windowless_period_on_windowed_family": 1,
    }
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["orphan_cells"]
    # Not counted in present_cells: no present_cells mismatch appears for the
    # member and the tier's present totals are untouched.
    assert [
        item
        for item in report["manifest_rollup_mismatch"]
        if item["cik"] == "0000000001" and item["field"] == "present_cells"
    ] == []
    assert report["tiers"]["deep"]["fields"]["present"] == 48
    assert report["tiers"]["core"]["fields"]["present"] == 36


def test_probe_wildcard_metric_cell_passes_r2_fails_base_passes_head() -> None:
    """R1 reviewer probe: green at r2, red at r3 BASE, green at HEAD.

    A wildcard-period metric cell on a deep member was an orphan at r2 (the
    wildcard period sits outside the member's windows); r3 BASE exempted
    every "*" cell from the window test, so the cell was silently counted in
    present_cells (the reviewer's 38 became 39); HEAD orphans it again under
    windowless_period_on_windowed_family.  The probe asserts the r2/HEAD
    shared invariant — an orphan, never counted — not the reason key, which
    r2 spelled period_outside_windows.  The TypeError arm runs the same
    scenario through r2's call shape (a parsed manifest plus the caller's
    sha256), which r3 removed."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["cells"].append(cell("0000000001", "*", "metric:alpha"))
    thresholds = small_thresholds_for(manifest)
    payload = manifest_bytes(manifest)
    try:
        report = prove_coverage(
            payload, thresholds, DIRECT_IDS, FORMULA_IDS, proved_at=PROVED_AT
        )
    except TypeError:
        report = prove_coverage(
            manifest,
            hashlib.sha256(payload).hexdigest(),
            thresholds,
            DIRECT_IDS,
            FORMULA_IDS,
            proved_at=PROVED_AT,
        )

    assert report["orphan_cells"] == 1
    # Not counted in present_cells: the manifest's own rollup (39 for member
    # 1, without the appended cell) agrees with the proof, and the tier's
    # present totals are untouched.  At r3 BASE the proof counted the cell,
    # producing a 39-vs-40 present_cells mismatch here.
    assert [
        item
        for item in report["manifest_rollup_mismatch"]
        if item["cik"] == "0000000001" and item["field"] == "present_cells"
    ] == []
    assert report["tiers"]["deep"]["fields"]["present"] == 48
    assert report["tiers"]["core"]["fields"]["present"] == 36


def test_wildcard_period_on_windowless_families_stays_exempt() -> None:
    """R1: packet, journey and specialist cells keep their wildcard periods
    and stay exempt from the window test."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    wildcard_families = {
        item["field_id"]
        for item in manifest["cells"]
        if item["period_id"] == "*"
    }
    assert wildcard_families == {"specialist:PK01", "packet", "journey"}
    report = run_proof(manifest)
    assert report["orphan_cells"] == 0
    assert report["orphan_reasons"] == dict(R4_ORPHAN_REASONS)
    assert report["acceptance_blockers"] == []
    # The wildcard cells are counted present on the deep members, not orphaned.
    assert report["tiers"]["deep"]["pass"] == 2


@pytest.mark.parametrize(
    "field_id,period",
    [
        ("package:primary", "A1"),
        ("statement:income_statement", "A1"),
        ("specialist:PK01", "*"),
        ("packet", "*"),
        ("journey", "*"),
    ],
)
def test_deep_only_family_cell_on_core_member_is_an_orphan(
    field_id: str, period: str
) -> None:
    """R2: every deep-only family (package, statement, specialist, packet,
    journey — the frozen deep tier's own component set) on a member that is
    not deep is an orphan under deep_component_not_deep_member."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["cells"].append(cell("0000000003", period, field_id))
    report = run_proof(manifest)

    assert report["orphan_cells"] == 1
    assert report["orphan_reasons"] == {
        **R4_ORPHAN_REASONS,
        "deep_component_not_deep_member": 1,
    }
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["orphan_cells"]
    # The orphaned cell never reaches the rollup comparison.
    assert report["manifest_rollup_mismatch"] == []


def test_metric_cell_on_core_only_member_is_not_an_orphan() -> None:
    """R2: metric is not a deep-only family; an in-window metric cell on a
    core-only member is counted present, never orphaned."""
    members = standard_members()
    manifest = build_manifest(members, draft=False, attested=True)
    manifest["cells"] = [
        item
        for item in manifest["cells"]
        if not (
            item["cik"] == "0000000003"
            and item["period_id"] == "A1"
            and item["field_id"] == "metric:alpha"
        )
    ]
    manifest["cells"].append(cell("0000000003", "A1", "metric:alpha"))
    report = run_proof(manifest)

    assert report["orphan_cells"] == 0
    assert report["orphan_reasons"] == dict(R4_ORPHAN_REASONS)
    assert report["acceptance_eligible"] is True
    assert report["acceptance_blockers"] == []
    # Counted present: the re-added cell keeps every rollup in agreement.
    assert report["manifest_rollup_mismatch"] == []


def test_real_draft_shape_gives_zero_deep_component_orphans() -> None:
    """R2: the real census draft puts its deep-only components on deep
    members only; a fixture in that shape reports zero orphans of the new
    reason (also covered by test_real_draft_package_shape_gives_zero_orphans,
    which now asserts the full four-key zero map)."""
    report = run_proof(build_manifest(standard_members(), draft=False, attested=True))
    assert report["orphan_reasons"]["deep_component_not_deep_member"] == 0
    assert report["orphan_cells"] == 0


def test_attested_manifest_identity_is_declared_unverified() -> None:
    """R3: a non-draft's draft identity is declared, never proved; the basis
    says so and the report asks for the attestation (non-blocking field)."""
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    declared = manifest["manifest_draft_sha256"]
    report = run_proof(manifest, small_thresholds_with_prefix(declared[:20]))
    identity = report["census_identity"]
    assert identity["draft_identity"] == declared
    assert identity["draft_identity_basis"] == "declared_unverified"
    assert identity["draft_identity_trust"] == "attestation_required"
    assert identity["mismatched_fields"] == []
    assert report["acceptance_blockers"] == []


def test_draft_identity_basis_is_bytes_and_carries_no_trust_field() -> None:
    """R3: only a draft's identity is proved from its bytes; the trust field
    belongs to the declared basis alone."""
    manifest = build_manifest(standard_members())  # a draft
    report = run_proof(manifest, small_thresholds_for(manifest))
    identity = report["census_identity"]
    assert identity["draft_identity_basis"] == "manifest_bytes_sha256"
    assert identity["draft_identity"] == hashlib.sha256(
        manifest_bytes(manifest)
    ).hexdigest()
    assert "draft_identity_trust" not in identity


def test_declared_prefix_differing_from_pin_blocks() -> None:
    """R3: a manifest that declares its own manifest_draft_sha256_prefix
    must declare the thresholds' pin exactly; a difference is its own
    mismatched field and blocks through census_identity_mismatch."""
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    thresholds = small_thresholds_for(manifest)
    manifest["manifest_draft_sha256_prefix"] = "f" * 20
    report = run_proof(manifest, thresholds)

    assert report["census_identity"]["mismatched_fields"] == [
        "manifest_draft_sha256_prefix_declared"
    ]
    assert (
        report["census_identity"]["manifest"]["manifest_draft_sha256_prefix"]
        == "f" * 20
    )
    assert report["acceptance_eligible"] is False
    assert report["acceptance_blockers"] == ["census_identity_mismatch"]


def test_declared_prefix_equal_to_pin_does_not_block() -> None:
    """R3: a declared prefix equal to the thresholds' pin adds nothing."""
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    thresholds = small_thresholds_for(manifest)
    manifest["manifest_draft_sha256_prefix"] = (
        thresholds.census_identity["manifest_draft_sha256_prefix"]
    )
    report = run_proof(manifest, thresholds)

    assert report["census_identity"]["mismatched_fields"] == []
    assert report["acceptance_eligible"] is True
    assert report["acceptance_blockers"] == []


def test_forged_padded_draft_sha_still_passes_pin_but_is_marked_unverified() -> None:
    """R3: the reviewer's forgery — the pinned prefix padded with zeros —
    still satisfies the prefix pin (bytes cannot disprove it), but the report
    now names the trust boundary instead of implying a proved identity."""
    manifest = build_manifest(standard_members(), draft=False, attested=True)
    pin = small_thresholds_for(manifest).census_identity[
        "manifest_draft_sha256_prefix"
    ]
    manifest["manifest_draft_sha256"] = pin + "0" * 44
    report = run_proof(manifest, small_thresholds_with_prefix(pin))
    identity = report["census_identity"]
    assert identity["draft_identity"] == pin + "0" * 44
    assert identity["draft_identity_basis"] == "declared_unverified"
    assert identity["draft_identity_trust"] == "attestation_required"
    assert identity["mismatched_fields"] == []


# ---------------------------------------------------------------------------
# 19. Source hygiene scan
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


# ---------------------------------------------------------------------------
# 20. Seat ruling BLOCKER-1 (2026-10-19): na_basis / qualifier / derivation
#     labels and the complete_strict band
# ---------------------------------------------------------------------------

# A wider synthetic direct-metric set so one core-only issuer's core scope
# holds 24 cells: (10 direct + 2 formula) x A1, I1.
WIDE_DIRECT_IDS = tuple(f"wide{number:02d}" for number in range(1, 11))
WIDE_METRICS = tuple(sorted(WIDE_DIRECT_IDS + FORMULA_IDS))
WIDE_LABEL_KEYS = ("na_basis", "qualifier", "qualifier_policy", "derivation", "derivation_policy")
QUALIFIER_POLICY = "fif.coverage_writer.cover_date_as_of/1.0.0"
DERIVATION_POLICY = "fif.coverage_writer.subtotal_composition/1.0.0"


def qualified(**extra) -> dict:
    return {"qualifier": "cover_date_as_of", "qualifier_policy": QUALIFIER_POLICY, **extra}


def composed(**extra) -> dict:
    return {"derivation": "subtotal_composition", "derivation_policy": DERIVATION_POLICY, **extra}


def wide_manifest(
    statuses: dict[tuple[str, str], str], labels: dict[tuple[str, str], dict]
) -> tuple[dict, str]:
    """One core-only issuer over WIDE_METRICS; ``(period, metric_id)`` keys."""
    cik = format(1, "010d")
    member = issuer(cik, f"Z{1:04d}", "core")
    cells = [
        cell(
            cik,
            period,
            f"metric:{metric_id}",
            statuses.get((period, metric_id), "present"),
            **labels.get((period, metric_id), {}),
        )
        for period in CORE_PERIODS
        for metric_id in WIDE_METRICS
    ]
    member["present_cells"] = sum(1 for item in cells if item["status"] == "present")
    member["na_cells"] = sum(1 for item in cells if item["status"] == "not_applicable")
    member["core_pass"] = all(item["status"] in ("present", "not_applicable") for item in cells)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "draft": True,
        "attested": False,
        "basis": "census_precheck_companyfacts",
        "cutoff_at": "2026-10-18T00:00:00Z",
        "source_generation_id": "census-test",
        "recorded_at": "2026-10-18T20:50:47Z",
        "cells": cells,
        "issuers": [member],
    }
    return manifest, cik


def run_wide(manifest: dict) -> dict:
    return prove_coverage(
        manifest_bytes(manifest),
        small_thresholds_for(manifest),
        WIDE_DIRECT_IDS,
        FORMULA_IDS,
        proved_at=PROVED_AT,
    )


def strip_labels(manifest: dict) -> dict:
    stripped = copy.deepcopy(manifest)
    for item in stripped["cells"]:
        for key in WIDE_LABEL_KEYS:
            item.pop(key, None)
    return stripped


def cell_key(item: dict) -> tuple[str, str, str]:
    return item["cik"], item["period_id"], item["field_id"]


def ruling_case_manifest(*, labelled: bool = True) -> tuple[dict, str]:
    """7 not_applicable + 8 present-qualified cells over the wide core scope."""
    direct_keys = [(period, metric_id) for period in CORE_PERIODS for metric_id in WIDE_DIRECT_IDS]
    na_keys, qualified_keys = direct_keys[:7], direct_keys[7:15]
    statuses = {key: "not_applicable" for key in na_keys}
    labels: dict[tuple[str, str], dict] = {}
    if labelled:
        labels.update({key: {"na_basis": "not_presented_item"} for key in na_keys})
        labels.update({key: qualified() for key in qualified_keys})
    return wide_manifest(statuses, labels)


def composed_case_manifest() -> tuple[dict, str]:
    """One composed cell and one cell carrying both present labels."""
    first, second = (CORE_PERIODS[0], WIDE_DIRECT_IDS[0]), (CORE_PERIODS[1], WIDE_DIRECT_IDS[1])
    return wide_manifest({}, {first: composed(), second: {**qualified(), **composed()}})


def deep_component_case_manifest() -> tuple[dict, list[dict]]:
    """Deep member one: a qualified component; deep member two: a not-presented N/A pack."""
    members = standard_members()
    first_deep, second_deep = members[0]["cik"], members[1]["cik"]
    pack_key = (second_deep, "*", f"specialist:{PACKS[0]}")
    manifest = build_manifest(members, statuses={pack_key: "not_applicable"})
    statement_key = (first_deep, "A1", f"statement:{STATEMENTS[0]}")
    for item in manifest["cells"]:
        if cell_key(item) == statement_key:
            item.update(qualified())
        if cell_key(item) == pack_key:
            item["na_basis"] = "not_presented_item"
    return manifest, members


def test_blocker1_ruling_case_is_complete_but_not_strict() -> None:
    manifest, cik = ruling_case_manifest()
    report = run_wide(manifest)
    core = report["tiers"]["core"]
    entry = entry_for(report, cik)
    assert entry["band"] == "complete"
    assert core["bands"]["complete"] == 1
    assert core["complete_strict"] == 0
    assert entry["complete_strict"] is False
    assert entry["na_not_presented"] == 7
    assert entry["present_qualified"] == 8
    assert entry["na_class"] == 0
    assert entry["present_composed"] == 0
    assert core["fields"]["na_not_presented"] == 7
    assert core["fields"]["present_qualified"] == 8
    assert core["fields"]["present_strict"] == 9
    assert core["fields"]["present"] == 17
    assert core["fields"]["applicable"] == 17
    assert core["qualifier_policies"] == {QUALIFIER_POLICY: 8}
    assert core["derivation_policies"] == {}

    # Labels are reporting only: the same manifest stripped of them passes,
    # bands and counts exactly as before.
    stripped = run_wide(strip_labels(manifest))
    assert entry["core_pass"] is True
    assert entry["core_pass"] == entry_for(stripped, cik)["core_pass"]
    assert core["pass"] == stripped["tiers"]["core"]["pass"]
    assert core["bands"] == stripped["tiers"]["core"]["bands"]
    for key in ("present", "applicable", "not_applicable", "withheld", "rate"):
        assert core["fields"][key] == stripped["tiers"]["core"]["fields"][key]
    assert report["acceptance_blockers"] == stripped["acceptance_blockers"]

    block = render_print(report)
    assert "complete=1 complete_strict=0" in block
    assert (
        "core labels:    present_strict=9 present_qualified=8 present_composed=0 "
        "na_kernel=0 na_not_presented=7 na_class=0"
    ) in block.splitlines()


def test_blocker1_kernel_na_and_unqualified_cells_are_strict() -> None:
    manifest, cik = ruling_case_manifest(labelled=False)
    report = run_wide(manifest)
    core = report["tiers"]["core"]
    entry = entry_for(report, cik)
    assert core["bands"]["complete"] == 1
    assert core["complete_strict"] == 1
    assert entry["complete_strict"] is True
    assert core["fields"]["na_kernel"] == 7
    assert core["fields"]["na_not_presented"] == 0
    assert core["fields"]["present_strict"] == 17
    # An explicit "kernel" basis and a JSON null both read as the kernel's own.
    for basis in ("kernel", None):
        relabelled = copy.deepcopy(manifest)
        for item in relabelled["cells"]:
            if item["status"] == "not_applicable":
                item["na_basis"] = basis
        again = run_wide(relabelled)
        assert again["tiers"]["core"]["complete_strict"] == 1
        assert again["tiers"]["core"]["fields"]["na_kernel"] == 7


def test_blocker1_composed_and_double_labelled_cells() -> None:
    first = (CORE_PERIODS[0], WIDE_DIRECT_IDS[0])
    only_composed, cik = wide_manifest({}, {first: composed()})
    report = run_wide(only_composed)
    core = report["tiers"]["core"]
    assert core["fields"]["present_composed"] == 1
    assert core["bands"]["complete"] == 1
    assert core["complete_strict"] == 0
    assert entry_for(report, cik)["present_composed"] == 1
    assert core["derivation_policies"] == {DERIVATION_POLICY: 1}

    both, cik = composed_case_manifest()
    report = run_wide(both)
    fields = report["tiers"]["core"]["fields"]
    assert fields["present"] == 24
    assert fields["present_composed"] == 2
    assert fields["present_qualified"] == 1
    assert fields["present_strict"] == 22
    assert report["tiers"]["core"]["complete_strict"] == 0
    assert report["tiers"]["core"]["qualifier_policies"] == {QUALIFIER_POLICY: 1}
    assert report["tiers"]["core"]["derivation_policies"] == {DERIVATION_POLICY: 2}


def test_blocker1_label_refusals_carry_their_codes() -> None:
    core_cik = standard_members()[2]["cik"]
    na_key = (core_cik, "I1", "metric:beta")
    present_key = (core_cik, "A1", "metric:alpha")

    def labelled(key: tuple[str, str, str], **labels) -> dict:
        manifest = build_manifest(standard_members(), statuses={na_key: "not_applicable"})
        for item in manifest["cells"]:
            if cell_key(item) == key:
                item.update(labels)
        return manifest

    cases = [
        (present_key, {"na_basis": "kernel"}, "na_basis_on_applicable_cell"),
        (na_key, {"na_basis": "inferred"}, "na_basis_vocabulary"),
        (na_key, {"na_basis": ["kernel"]}, "na_basis_vocabulary"),
        (na_key, qualified(), "label_on_non_present_cell"),
        (na_key, composed(), "label_on_non_present_cell"),
        (present_key, {"qualifier": "", "qualifier_policy": QUALIFIER_POLICY}, "qualifier_shape"),
        (present_key, {"qualifier": " \t", "qualifier_policy": QUALIFIER_POLICY}, "qualifier_shape"),
        (present_key, {"qualifier": "cover_date_as_of"}, "qualifier_policy_missing"),
        (
            present_key,
            {"qualifier": "cover_date_as_of", "qualifier_policy": "unversioned"},
            "qualifier_policy_missing",
        ),
        (present_key, {"qualifier_policy": QUALIFIER_POLICY}, "qualifier_policy_without_qualifier"),
        (present_key, {"derivation": 7, "derivation_policy": DERIVATION_POLICY}, "derivation_shape"),
        (present_key, {"derivation": "subtotal_composition"}, "derivation_policy_missing"),
        (
            present_key,
            {"derivation_policy": DERIVATION_POLICY},
            "derivation_policy_without_derivation",
        ),
    ]
    codes = set()
    for key, labels, code in cases:
        refuse(labelled(key, **labels), code)
        codes.add(code)
    assert len(codes) == 9

    # JSON null is an absent label on any status; unknown extra keys stay unread.
    nulls = {key: None for key in WIDE_LABEL_KEYS}
    clean = labelled(present_key, as_of="2026-01-31", **nulls)
    for item in clean["cells"]:
        if cell_key(item) == na_key:
            item.update(nulls)
    report = run_proof(clean)
    assert report["tiers"]["core"]["complete_strict"] == report["tiers"]["core"]["bands"]["complete"]


def test_blocker1_deep_component_labels_break_deep_strictness_only() -> None:
    manifest, members = deep_component_case_manifest()
    report = run_proof(manifest)
    unlabelled = run_proof(strip_labels(manifest))
    deep = report["tiers"]["deep"]
    assert deep["component_labelled"] == 2
    assert deep["bands"]["complete"] == 2
    assert deep["complete_strict"] == 0
    assert deep["pass"] == unlabelled["tiers"]["deep"]["pass"] == 2
    assert unlabelled["tiers"]["deep"]["complete_strict"] == 2
    assert unlabelled["tiers"]["deep"]["component_labelled"] == 0
    for member in members[:2]:
        entry = entry_for(report, member["cik"])
        assert entry["deep_pass"] is True
        assert entry["complete_strict"] is False
    # Component labels sit outside every metric scope: core strictness and
    # the metric label counts are untouched.
    assert report["tiers"]["core"]["complete_strict"] == 3
    assert deep["fields"]["present_qualified"] == 0
    assert deep["fields"]["na_not_presented"] == 0


def _assert_label_invariants(report: dict) -> None:
    for tier in ("core", "deep"):
        block = report["tiers"][tier]
        fields = block["fields"]
        assert fields["present_strict"] <= fields["present"]
        assert fields["na_kernel"] + fields["na_not_presented"] + fields["na_class"] == (
            fields["not_applicable"]
        )
        assert block["complete_strict"] <= block["bands"]["complete"]
        assert block["complete_strict"] <= block["pass"]
        assert sum(block["qualifier_policies"].values()) == fields["present_qualified"]
        assert sum(block["derivation_policies"].values()) == fields["present_composed"]


def test_blocker1_invariants_on_the_mixed_fixture() -> None:
    # The mixed fixture of the contract-conformance test, keyed by member.
    members = standard_members()
    first_deep, second_deep, core_only = (member["cik"] for member in members)
    statuses = {
        (first_deep, "A1", "metric:alpha"): "slot_absent",
        (core_only, "I1", "metric:beta"): "not_applicable",
        (core_only, "A1", "metric:phi"): "absent",
    }
    manifest = build_manifest(members, statuses=statuses)
    report = run_proof(manifest)
    _assert_label_invariants(report)
    for tier in ("core", "deep"):
        fields = report["tiers"][tier]["fields"]
        # No labels: every present cell is strict, every N/A the kernel's own.
        assert fields["present_strict"] == fields["present"]
        assert fields["na_kernel"] == fields["not_applicable"]

    labelled = copy.deepcopy(manifest)
    for item in labelled["cells"]:
        if cell_key(item) == (core_only, "I1", "metric:beta"):
            item["na_basis"] = "class_policy"
        if cell_key(item) == (second_deep, "I2", "metric:gamma"):
            item.update(qualified())
    report = run_proof(labelled)
    _assert_label_invariants(report)
    core_fields = report["tiers"]["core"]["fields"]
    deep_fields = report["tiers"]["deep"]["fields"]
    assert core_fields["na_class"] == 1
    assert deep_fields["present_qualified"] == 1
    # I2 sits outside the core periods: the core scope never sees that cell.
    assert core_fields["present_qualified"] == 0
    for tier in ("core", "deep"):
        fields = report["tiers"][tier]["fields"]
        assert (
            fields["present_strict"] + fields["present_qualified"] + fields["present_composed"]
            == fields["present"]
        )


def test_blocker1_reports_conform_to_contract() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(run_wide(ruling_case_manifest()[0]), contract)
    jsonschema.validate(run_wide(composed_case_manifest()[0]), contract)
    jsonschema.validate(run_proof(deep_component_case_manifest()[0]), contract)


# ---------------------------------------------------------------------------
# 21. Seat ruling V1A-S1 (2026-10-19): complete_strict requires the tier pass
# ---------------------------------------------------------------------------


def test_v1a_s1_strict_requires_the_tier_pass() -> None:
    members = standard_members()
    first_deep = members[0]["cik"]
    # A missing packet cell fails deep while the metric band stays complete
    # and no cell carries a label.
    manifest = build_manifest(members, drop=frozenset({(first_deep, "A2", "package:label")}))
    report = run_proof(manifest)
    deep = report["tiers"]["deep"]
    assert deep["bands"]["complete"] == 2
    assert deep["pass"] == 1
    assert deep["complete_strict"] == 1
    entry = entry_for(report, first_deep)
    assert entry["band"] == "complete"
    assert entry["deep_pass"] is False and entry["core_pass"] is True
    assert entry["complete_strict"] is False
    core = report["tiers"]["core"]
    assert core["pass"] == 3 and core["complete_strict"] == 3
    _assert_label_invariants(report)

    # Core needs no second case: the thresholds law pins the complete band
    # at rate 1.0, so a core issuer in that band has no failed metric field
    # and core strictness already equals core pass on every fixture.


def test_v1a_s1_policy_maps_never_carry_a_zero_count() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["$defs"]["policy_count_map"]["additionalProperties"]["minimum"] == 1
    for tier in ("core_tier", "deep_tier"):
        for key in ("qualifier_policies", "derivation_policies"):
            block = contract["$defs"][tier]["properties"][key]
            assert block == {"$ref": "#/$defs/policy_count_map"}
