"""Attribute the CI registration using HEAD/candidate manifests on one source tree."""
from __future__ import annotations
import ast
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts.run_ci_pack import PACK_TARGET_SECONDS, infer_job_scopes, load_legacy_jobs, select_jobs

manifest = ROOT / ".github/ci/legacy-jobs.yml"
base = subprocess.run(["git", "show", "HEAD:.github/ci/legacy-jobs.yml"], cwd=ROOT,
                      capture_output=True, text=True, check=True).stdout
tree = ast.parse((ROOT / "tests/test_ci_pack.py").read_text())
constants = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {"PACKING_PROBES", "PACKING_PROBE_MAX_PACKS"}:
                constants[target.id] = ast.literal_eval(node.value)
def rows(jobs):
    result = []
    for probe, limit_jobs, limit_weight in constants["PACKING_PROBES"]:
        selected, reason = select_jobs(jobs, [probe])
        weight = sum(job.weight for job in selected)
        result.append({"probe": probe, "jobs": len(selected), "weight": weight,
                       "packs": max(1, min(12, -(-weight // PACK_TARGET_SECONDS))),
                       "max_jobs": limit_jobs, "max_weight": limit_weight,
                       "max_packs": constants["PACKING_PROBE_MAX_PACKS"],
                       "job_ids": sorted(job.job_id for job in selected), "reason": reason})
    return result
with tempfile.TemporaryDirectory(prefix="ci-registration-baseline-", dir=OUT) as temp:
    baseline_path = Path(temp) / "legacy-jobs.yml"
    baseline_path.write_text(base)
    baseline_jobs, baseline_note = infer_job_scopes(load_legacy_jobs(baseline_path))
    print("HEAD-manifest inference completed on candidate source tree.", flush=True)
    candidate_jobs, candidate_note = infer_job_scopes(load_legacy_jobs(manifest))
    print("Candidate-manifest inference completed on the same source tree.", flush=True)
    before, after = rows(baseline_jobs), rows(candidate_jobs)
base_by_id = {job.job_id: job for job in baseline_jobs}
candidate_by_id = {job.job_id: job for job in candidate_jobs}
assert set(base_by_id) == set(candidate_by_id)
deltas = [{"job": key, "before": base_by_id[key].weight, "after": job.weight,
           "delta": job.weight - base_by_id[key].weight}
          for key, job in candidate_by_id.items() if job.weight != base_by_id[key].weight]
assert len(deltas) == 1 and deltas[0]["job"] == "public-render-fastlane" and deltas[0]["delta"] == 6, deltas
for old, new in zip(before, after):
    assert old["job_ids"] == new["job_ids"], new["probe"]
    assert new["weight"] - old["weight"] == 6, new["probe"]
    assert old["packs"] == new["packs"] <= constants["PACKING_PROBE_MAX_PACKS"]
representative = {}
for path in ("templates/sector_central.html.j2", "templates/si_workspace.js",
             "templates/_sector_central_coverage.js.j2", "templates/_sector_prophet_context.js.j2",
             "templates/dashboard.html.j2", "tests/test_sector_central_paper.py",
             "tests/test_sector_central_data_is_sync.py"):
    selected, reason = select_jobs(candidate_jobs, [path])
    ids = sorted(job.job_id for job in selected)
    assert "public-render-fastlane" in ids, path
    representative[path] = {"executing_owner_selected": True, "reason": reason}
countercase = candidate_by_id["leadership-rotation-countercases"]
assert "templates/_sector_prophet_context.js.j2" in countercase.paths
assert countercase.weight == base_by_id[countercase.job_id].weight
receipt = {
    "scope": "Planning attribution only; identical candidate source tree for both manifests",
    "base_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
    "candidate_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    "weight_deltas": deltas, "all_probe_job_ids_equal": True,
    "baseline": before, "candidate": after, "representative_selection": representative,
    "countercase_shared_dependency_declared": True,
    "selectors_or_suite_execution_narrowed": False,
    "estimator_units_are_runtime_measurement": False,
}
(OUT / "ci-registration-attribution.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"weight_deltas": deltas, "probes": [
    {"path": a["probe"], "jobs": a["jobs"], "before": b["weight"], "after": a["weight"], "packs": a["packs"]}
    for b, a in zip(before, after)], "all_probe_job_ids_equal": True,
    "representative_selection_passed": True}, indent=2))
