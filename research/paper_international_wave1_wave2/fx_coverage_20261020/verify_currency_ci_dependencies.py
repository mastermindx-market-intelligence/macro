#!/usr/bin/env python3
"""Record the existing CI owner's current-working-tree dependency verdict."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.run_ci_pack import curated_exclusive_closure_findings, load_legacy_jobs
from scripts.audit_unrun_tests import gated_unrun_suites

HERE = Path(__file__).resolve().parent
MANIFEST = ROOT / ".github/ci/legacy-jobs.yml"
def stamp():
    return datetime.now(timezone.utc).isoformat()
def fp(rel):
    data = (ROOT / rel).read_bytes()
    return {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

paths = [".github/ci/legacy-jobs.yml", "lib/intl_currency_observation.py",
         "engine/intl_run.py", "tests/test_intl_currency_observation.py",
         "tests/fixtures/intl_currency_observations_20261020.json",
         "scripts/run_ci_pack.py", "scripts/ci_scope_dependencies.py",
         "scripts/audit_unrun_tests.py"]
before = [fp(p) for p in paths]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
assert head == "11c83bb5dfb0c8199a0fb0cb2c6e70452c724984", head
result = {"schema": "mastermind.intl_currency_ci_dependency_coverage.v1",
          "started_at": stamp(), "workspace_head": head,
          "scope": "Canonical shared primitives against the materialized working tree, including held uncommitted source; not hosted PR-versus-base contract-delta.",
          "owners": ["scripts.run_ci_pack.curated_exclusive_closure_findings",
                     "scripts.audit_unrun_tests.gated_unrun_suites"],
          "inputs": before}
print(json.dumps({"phase": "canonical_dependency_inference_started", "at": result["started_at"]}), flush=True)
jobs = load_legacy_jobs(MANIFEST)
engine_jobs = [j for j in jobs if "engine/intl_run.py" in j.paths]
result["engine_job_coverage"] = [
    {"job": j.job_id, "currency_helper_explicit": "lib/intl_currency_observation.py" in j.paths,
     "exclusive": j.exclusive} for j in engine_jobs]
assert len(engine_jobs) == 7
assert all(j["currency_helper_explicit"] for j in result["engine_job_coverage"])
foundation = next(j for j in jobs if j.job_id == "international-workspace-foundation")
test = "tests/test_intl_currency_observation.py"
fixture = "tests/fixtures/intl_currency_observations_20261020.json"
commands = "\n".join(str(s.get("run", "")) for s in foundation.definition.get("steps", []) if isinstance(s, dict))
result["currency_suite_enrollment"] = {"job": foundation.job_id,
    "test_explicit_path": test in foundation.paths,
    "fixture_explicit_path": fixture in foundation.paths,
    "test_named_in_execution": test in commands}
assert all(v for k, v in result["currency_suite_enrollment"].items() if k != "job")
result["import_closure_findings"] = {k: list(v) for k, v in curated_exclusive_closure_findings(MANIFEST).items()}
print(json.dumps({"phase": "canonical_dependency_inference_complete", "uncovered_jobs": len(result["import_closure_findings"]), "at": stamp()}), flush=True)
result["unwired_suites"] = sorted(gated_unrun_suites())
result["input_bytes_unchanged"] = before == [fp(p) for p in paths]
result["finished_at"] = stamp()
result["passed"] = not result["import_closure_findings"] and not result["unwired_suites"] and result["input_bytes_unchanged"]
(HERE / "ci_dependency_coverage.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": result["passed"], "engine_jobs": len(engine_jobs), "uncovered_jobs": len(result["import_closure_findings"]), "unwired_suites": len(result["unwired_suites"]), "finished_at": result["finished_at"]}), flush=True)
raise SystemExit(0 if result["passed"] else 1)
