"""T03 (lane B1): pin the v2 global-liquidity source qualification manifest.

``config/global_liquidity_sources_v2.yml`` is a NEW namespace — a measured-truth,
display-tier (``validated: false``) source matrix that cites data, never copies it.
These tests hold the load-bearing law of that document: the C06 null scalars, the
forbidden private-credit pool, one known concept per source (C05), verdict
completeness per use, absent-store exclusions, namespace separation from the
untouched v1 producer manifest, and that every cited store is really tracked.

stdlib + yaml only. No data values are read — this file tests the manifest.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_PATH = REPO_ROOT / "config" / "global_liquidity_sources_v2.yml"
V1_PATH = REPO_ROOT / "config" / "global_liquidity_transmission_v1.yml"

USES = (
    "display",
    "reconstructed_research",
    "vintage_qualified_research",
    "prospective_eligibility",
)


def _load_v2() -> dict:
    with open(V2_PATH, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    assert isinstance(doc, dict), "v2 manifest must be a mapping at top level"
    return doc


def test_v2_config_loads_and_is_display_tier():
    d = _load_v2()
    assert d["validated"] is False
    assert d["schema_version"] == 2
    assert d["claim_level"] == "source_qualification_display_tier"


def test_credit_impulse_global_is_null_with_reason():
    """C06: the global credit and broad-money scalars stay null, with reasons."""
    d = _load_v2()
    scalars = d["global_scalars"]
    for key in ("credit_impulse_global", "broad_money_global"):
        entry = scalars[key]
        assert entry["value"] is None, f"{key} must be null, not zero/neutral"
        assert entry["status"] == "insufficient_comparable_pit_coverage"
        assert len(entry["reason"]) > 40, f"{key} needs a substantive reason"


def test_forbidden_pool_names_tsf_ci_and_bis():
    """china_tsf, us_ci_loans, bis_gli_external_credit may never be pooled."""
    d = _load_v2()
    pools = d["pooling"]["forbidden_pools"]
    assert len(pools) >= 1
    global_credit = [p for p in pools if p["id"] == "global_private_credit"]
    assert len(global_credit) == 1
    members = set(global_credit[0]["members"])
    assert members == {"china_tsf", "us_ci_loans", "bis_gli_external_credit"}
    ids = {s["id"] for s in d["sources"]}
    for member in members:
        assert member in ids, f"forbidden-pool member {member} is not a declared source"


def test_every_source_has_one_known_concept_and_valid_verdicts():
    """C05: one known concept per source; all four uses carry valid verdicts."""
    d = _load_v2()
    concepts = set(d["concepts"])
    verdict_values = set(d["verdict_values"])
    assert d["sources"], "sources list must not be empty"
    for s in d["sources"]:
        assert s["concept"] in concepts, f"{s['id']}: unknown concept {s['concept']!r}"
        verdicts = s["verdicts"]
        assert set(verdicts.keys()) == set(USES), f"{s['id']}: uses must be exactly {USES}"
        for use in USES:
            entry = verdicts[use]
            assert entry["verdict"] in verdict_values, f"{s['id']}/{use}: bad verdict"
            if entry["verdict"] != "eligible":
                assert entry.get("reason"), f"{s['id']}/{use}: non-eligible needs a reason"


def test_absent_sources_are_excluded_everywhere():
    """repo_path == 'absent' => every use (display included) excluded, with a reason.

    B4 finding 2: iterating only the research uses let a mutant that marks an
    absent store display-eligible survive.
    """
    d = _load_v2()
    for s in d["sources"]:
        if s["repo_path"] == "absent":
            for use in USES:
                assert s["verdicts"][use]["verdict"] == "excluded", f"{s['id']}/{use}"
            assert s.get("exclusion_reason"), f"{s['id']}: exclusion_reason required"


def test_v1_config_untouched_namespace():
    """v2 is a new namespace; the v1 producer manifest still loads untouched."""
    d = _load_v2()
    assert d["namespace"] == "global_liquidity_sources_v2"
    with open(V1_PATH, encoding="utf-8") as fh:
        v1 = yaml.safe_load(fh)
    assert isinstance(v1, dict) and v1, "v1 producer config must still load"
    assert "schema" in v1  # v1's own top-level identity key
    assert "schema" not in d  # v2 must not reuse v1's top-level key shape


def test_repo_paths_are_tracked():
    """Every cited store is really a tracked file (sparse tree: ls-files, not ls)."""
    d = _load_v2()
    cited = [
        s["repo_path"].split("::", 1)[0]
        for s in d["sources"]
        if s.get("repo_path") and s["repo_path"] != "absent"
    ]
    assert cited, "expected at least one tracked repo_path"
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"git ls-files unavailable: {exc}")
    tracked = set(proc.stdout.split())
    for path in cited:
        assert path in tracked, f"{path} is not tracked at {REPO_ROOT}"
