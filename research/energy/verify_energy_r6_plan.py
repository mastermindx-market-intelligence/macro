"""Energy R6 design/plan integrity checks; not product or implementation validation."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/superpowers/specs/2026-09-23-energy-economic-change-dossier-design.md"
PLAN = ROOT / "docs/superpowers/plans/2026-09-23-energy-economic-change-first-vertical-implementation.md"
OUT = ROOT / "research/energy/ENERGY_R6_PLANNING_VERIFICATION_2026-09-23.json"

EXPECTED_SPEC_BLOB = "d6dac80bead5a028da8d757b419c896b1b8437ed"
EXPECTED_PLAN_BLOB = "f7dc93621532b06e2478f90ef3876d6c31236242"
EXPECTED_DESIGN_COMMIT = "33774cd8fb89ddcf156469dec60e90bfb0b2ef82"
EXPECTED_PLAN_COMMIT = "0166518d5b4a7ac4d9278b689225c5d193dbda0f"

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def check(rows: list[dict], name: str, ok: bool, detail: object = "") -> None:
    rows.append({"name": name, "pass": bool(ok), "detail": detail})

spec_b = SPEC.read_bytes()
plan_b = PLAN.read_bytes()
spec = spec_b.decode()
plan = plan_b.decode()
checks: list[dict] = []

check(checks, "spec_blob_identity", git_blob(spec_b) == EXPECTED_SPEC_BLOB, git_blob(spec_b))
check(checks, "plan_blob_identity", git_blob(plan_b) == EXPECTED_PLAN_BLOB, git_blob(plan_b))

requirements = re.findall(r"\*\*(ENE-(\d{2}))\*\*", spec)
actual_req_ids = [name for name, _ in requirements]
expected_req_ids = [f"ENE-{i:02d}" for i in range(1, 79)]
check(checks, "requirements_exact_01_78", actual_req_ids == expected_req_ids, {"count": len(actual_req_ids), "first": actual_req_ids[:2], "last": actual_req_ids[-2:]})

task_headers = re.findall(r"^## \d+\. Task (\d+) —", plan, re.M)
check(checks, "eleven_ordered_tasks", task_headers == [str(i) for i in range(1, 12)], task_headers)

bands = [
    "ENE-01–07", "ENE-08–26", "ENE-27–38", "ENE-39–45",
    "ENE-46–51", "ENE-52–55", "ENE-56–63", "ENE-64–66",
    "ENE-67–71", "ENE-72–75", "ENE-76–78",
]
check(checks, "all_requirement_bands_mapped", all(b in plan for b in bands), [b for b in bands if b not in plan])

for token in ["#7462", "#7669", "#7664", "#7777"]:
    check(checks, f"collision_{token[1:]}", token in plan, token)

check(checks, "design_identity_in_plan", EXPECTED_DESIGN_COMMIT in plan and EXPECTED_SPEC_BLOB in plan)
check(checks, "nuclear_first_vertical", "Nuclear Value Capture" in spec and "Nuclear Value Capture" in plan)
check(checks, "existing_nuclear_theme_identity", "theme:nuclear_power" in spec and "theme:nuclear_power" in plan)
check(checks, "primary_supplemental_distinction", all(x in spec and x in plan for x in ["nuclear_power", "uranium_miners", "primary", "supplemental"]))
check(checks, "shared_dossier_not_energy_clone", "economic_change_dossier.v1" in spec and "economic_change_dossier.v1" in plan and "energy_economic_change_dossier.v1" not in plan)
check(checks, "no_energy_database", "No Energy database" in plan)
check(checks, "fresh_implementation_carrier", "fresh product carrier" in plan and "then-current main" in plan)
check(checks, "research_pr_not_product_carrier", "Product code must use a fresh implementation carrier" in plan)
check(checks, "why_fable_present", "**WHY FABLE:**" in plan and "**WHY NOT FABLE for routine work:**" in plan)
check(checks, "real_path_acceptance", "Real source-to-browser Nuclear proof" in plan)
check(checks, "privacy_negative_proof", "anonymous/free/public mirrors" in plan.lower() and "cache-control: private, no-store" in plan.lower())
check(checks, "decision_non_regression", "non-regression" in plan.lower() and "Prophet" in plan and "entry" in plan)
check(checks, "r5_grammar_preserved", "R5" in plan and "evidence-grade" in plan and "forecast-year rollover" in spec.lower())
check(checks, "power_second_vertical_foundation", "Power-Demand Value Capture" in spec)
check(checks, "no_placeholders", not re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", spec + "\n" + plan))
check(checks, "no_completion_claim", "IMPLEMENTATION_STARTED: false" in spec and "implementation blueprint" in plan.lower())
check(checks, "public_builder_not_private_plane", "public builder as paid research data plane" in plan)
check(checks, "unknown_expectations_allowed", "expectations.status=UNAVAILABLE" in plan)
check(checks, "shared_assertion_dependency", "shared curation assertion" in plan.lower() and "do not clone it" in plan)
check(checks, "shared_private_owner_dependency", "existing private owner" in plan.lower() and "second Energy private publisher" in plan)
check(checks, "bounded_first_unit", "max 5 selected companies" in plan and "no pagination in v1" in plan)
check(checks, "source_instruction_inert_requirement", "**ENE-65**" in spec)
check(checks, "all_authority_false_semantics", "all decision authority false" in spec.lower() and "all authority bits false" in plan)
check(checks, "research_do_not_redo", "R1–R5 Energy research is DO_NOT_REDO" in plan)

failures = [r for r in checks if not r["pass"]]
result = {
    "artifact_type": "energy_r6_planning_integrity_receipt",
    "operation_key": "gmi-energy-sector-research-20260923-sol-001",
    "spec_file": str(SPEC.relative_to(ROOT)),
    "plan_file": str(PLAN.relative_to(ROOT)),
    "spec_sha256": hashlib.sha256(spec_b).hexdigest(),
    "plan_sha256": hashlib.sha256(plan_b).hexdigest(),
    "spec_git_blob": git_blob(spec_b),
    "plan_git_blob": git_blob(plan_b),
    "expected_spec_commit": EXPECTED_DESIGN_COMMIT,
    "expected_plan_commit": EXPECTED_PLAN_COMMIT,
    "requirements": len(actual_req_ids),
    "tasks": len(task_headers),
    "passed": len(checks) - len(failures),
    "failed": len(failures),
    "application_tests_run": 0,
    "implementation_started": False,
    "fable_handoff_issued": False,
    "claim_limit": "Planning/spec integrity only. Does not prove shared-interface acceptance, source rights/admission, product implementation, tests, deployment, browser behavior, predictive validity or Fable receipt.",
    "check_corrections": [
        "Initial privacy check expected private/no-store but the plan correctly specifies Cache-Control: private, no-store; check grammar corrected only.",
        "Initial R5 check used a case-sensitive Forecast-year match; corrected to case-insensitive without changing the requirement.",
        "Initial authority check expected all-false authority while the spec says all decision authority false; corrected to the exact equivalent semantics.",
    ],
    "checks": checks,
}
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "checks"}, indent=2))
if failures:
    print(json.dumps(failures, indent=2))
    raise SystemExit(1)
