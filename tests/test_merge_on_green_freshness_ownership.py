"""Native entrypoint removal must not remove the admitted proof's ownership."""
from pathlib import Path

import pytest
import yaml

from scripts import merge_on_green as mog


ROOT = Path(__file__).resolve().parents[1]
PATHS = ["**", "engine/**", "worker/**", "templates/**", "config.yml"]


def write_workflows(tmp_path, paths=PATHS, *, native=True, metadata=True):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    events = {"workflow_dispatch": {"inputs": {"proof_role": {"type": "string"},
                                               "admission_generation": {"type": "string"}}}}
    if native:
        events["pull_request"] = {"paths": paths}
    (workflows / "ci.yml").write_text(yaml.safe_dump({"on": events, "jobs": {}}))
    # Other PR gates cannot mask loss of the CI surface.
    (workflows / "other.yml").write_text("on:\n  pull_request:\n    paths: [docs/**]\njobs: {}\n")
    if metadata:
        manifest = workflows.parent / "ci" / "legacy-jobs.yml"
        manifest.parent.mkdir()
        manifest.write_text(yaml.safe_dump({"proof_paths": paths, "jobs": {}}))
    return workflows


def test_native_and_admitted_only_paths_are_identical(tmp_path):
    native = mog.load_pr_gates(write_workflows(tmp_path / "native"))
    admitted = mog.load_pr_gates(write_workflows(tmp_path / "admitted", native=False))
    assert native == admitted
    assert next(g for g in admitted if g["workflow"] == "ci.yml")["patterns"] == PATHS[1:]


@pytest.mark.parametrize("changed", ["engine/example.py", "worker/example.py", "templates/example.j2", "config.yml"])
def test_cutover_rejects_stale_affected_input(tmp_path, changed):
    gates = mog.load_pr_gates(write_workflows(tmp_path, native=False))
    freshness = mog.ProofFreshness("acme/widgets", "read", gates,
        [{"sha": "4" * 40, "message": "product change"}, {"sha": "2" * 40, "message": "old base"}])
    freshness.exact_proof_base = lambda *_: ("2" * 40, "authenticated admitted tested base")
    freshness.files_of = lambda _: ([changed], False)
    freshness.pull_files = lambda _: [changed]
    assert freshness.stale_for({"number": 7}, [])[0] is True


@pytest.mark.parametrize("native", [False, True])
def test_admission_capability_requires_canonical_ownership(tmp_path, native):
    with pytest.raises(RuntimeError, match="canonical CI proof ownership"):
        mog.load_pr_gates(write_workflows(tmp_path, native=native, metadata=False))


def test_foundation_rejects_drift_between_native_and_canonical_paths(tmp_path):
    workflows = write_workflows(tmp_path)
    manifest = workflows.parent / "ci" / "legacy-jobs.yml"
    manifest.write_text(yaml.safe_dump({"proof_paths": ["different/**"], "jobs": {}}))
    with pytest.raises(RuntimeError, match="differs from canonical"):
        mog.load_pr_gates(workflows)


@pytest.mark.parametrize("paths", [[], ["**"], ["engine/**", "!engine/old/**"], [None], "engine/**"])
def test_invalid_canonical_ownership_cannot_fall_back_to_other_gate(tmp_path, paths):
    with pytest.raises(RuntimeError, match="canonical CI proof ownership"):
        mog.load_pr_gates(write_workflows(tmp_path, paths, native=False))


def test_existing_native_only_workflow_needs_no_new_metadata(tmp_path):
    (tmp_path / "ci.yml").write_text("on:\n  pull_request:\n    paths: [engine/**]\njobs: {}\n")
    assert mog.load_pr_gates(tmp_path) == [dict(workflow="ci.yml", patterns=["engine/**"], start_only_patterns=[])]


def test_real_foundation_metadata_is_exact_native_provenance(tmp_path):
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    manifest = yaml.safe_load((ROOT / ".github/ci/legacy-jobs.yml").read_text())
    events = workflow.get("on", workflow.get(True))
    from scripts.audit_unrun_tests import ci_proof_paths
    # The reader enforces native parity while present; below both delivery
    # shapes exercise the exact real inventory as explicit fixtures.
    assert manifest["proof_paths"] == ci_proof_paths()
    # Metadata is orthogonal to the incumbent executable jobs mapping.
    assert isinstance(manifest["jobs"], dict) and manifest["jobs"]
    # Exercise every real path, retaining order, duplicates and start-only globs.
    before = mog.load_pr_gates(write_workflows(tmp_path / "before", manifest["proof_paths"]))
    after = mog.load_pr_gates(write_workflows(tmp_path / "after", manifest["proof_paths"], native=False))
    assert before == after


@pytest.mark.parametrize("changed", [".github/workflows/ci.yml", ".github/ci/legacy-jobs.yml"])
def test_cutover_keeps_workflow_and_ownership_definition_invalidators(tmp_path, changed):
    gates = mog.load_pr_gates(write_workflows(tmp_path, native=False))
    freshness = mog.ProofFreshness("acme/widgets", "read", gates,
        [{"sha": "4" * 40, "message": "definition change"}, {"sha": "2" * 40, "message": "old base"}])
    freshness.exact_proof_base = lambda *_: ("2" * 40, "authenticated admitted tested base")
    freshness.files_of = lambda _: ([changed], False)
    freshness.pull_files = lambda _: ["engine/example.py"]
    stale, reason = freshness.stale_for({"number": 7}, [])
    assert stale is True and "check definitions" in reason
