"""Verify the Energy master Fable handoff packet; does not dispatch or start execution."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "agentos/handoffs/GMI-ENERGY-MASTER-FABLE-CEO-HANDOFF-2026-09-23.md"
CHECKPOINT = ROOT / "agentos/handoffs/GMI-ENERGY-RESEARCH-2026-09-23.md"
SPEC = ROOT / "docs/superpowers/specs/2026-09-23-energy-economic-change-dossier-design.md"
PLAN = ROOT / "docs/superpowers/plans/2026-09-23-energy-economic-change-first-vertical-implementation.md"
OUT = ROOT / "research/energy/ENERGY_FABLE_HANDOFF_VERIFICATION_2026-09-23.json"

EXPECTED_HANDOFF_BLOB = "f628167227613175cc3ede088f40423add7252fb"
EXPECTED_CHECKPOINT_BLOB = "6696e76eff9f93a7822a5dc50afb4d340c6aa075"
EXPECTED_SPEC_BLOB = "d6dac80bead5a028da8d757b419c896b1b8437ed"
EXPECTED_PLAN_BLOB = "f7dc93621532b06e2478f90ef3876d6c31236242"

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def ck(rows: list[dict], name: str, ok: bool, detail: object = "") -> None:
    rows.append({"name": name, "pass": bool(ok), "detail": detail})

hb, cb, sb, pb = HANDOFF.read_bytes(), CHECKPOINT.read_bytes(), SPEC.read_bytes(), PLAN.read_bytes()
h, c, s, p = hb.decode(), cb.decode(), sb.decode(), pb.decode()
checks: list[dict] = []

ck(checks, "handoff_blob_identity", git_blob(hb) == EXPECTED_HANDOFF_BLOB, git_blob(hb))
ck(checks, "checkpoint_blob_identity", git_blob(cb) == EXPECTED_CHECKPOINT_BLOB, git_blob(cb))
ck(checks, "spec_blob_identity", git_blob(sb) == EXPECTED_SPEC_BLOB, git_blob(sb))
ck(checks, "plan_blob_identity", git_blob(pb) == EXPECTED_PLAN_BLOB, git_blob(pb))

for token in [
    "operation_key: gmi-energy-fable-ceo-e2e-20260923-chairman-001",
    "parent_operation: gmi-energy-sector-research-20260923-sol-001",
    "preferred_avenue: Fable",
    "receiver_mode: OPEN_PICKUP",
    "receiver_binding_mode: CAPACITY_SELECTABLE",
    "placement_state: WAITING_CAPACITY",
    "needs_placement: true",
    "mission_complete: false",
]:
    ck(checks, "metadata_" + re.sub(r"[^a-z0-9]+", "_", token.lower()).strip("_")[:70], token in h, token)

ck(checks, "live_delivery_is_assignment", "that live delivery is the receiver assignment" in h)
ck(checks, "no_second_claim", "Do not ask the Chairman to “claim” this operation again" in h)
ck(checks, "pickup_start_distinct", "PICKUP_ACK gmi-energy-fable-ceo-e2e-20260923-chairman-001" in h and "START gmi-energy-fable-ceo-e2e-20260923-chairman-001" in h)
ck(checks, "no_current_receiver_claim", "Fable concrete receiver: **not assigned**" in h)
ck(checks, "no_current_ack_claim", "Fable PICKUP_ACK: **absent**" in h)
ck(checks, "no_current_start_claim", "Fable START: **absent**" in h)
ck(checks, "no_exec_job_claim", "Executive Job/Attempt: **not created by this packet**" in h)

for token in [
    "a7d2b3049e5cdc523e91e61a6e9d70a1cb911157",
    "b9c794cab7c5a1d81f033fd27622aee4232f307d",
    EXPECTED_CHECKPOINT_BLOB,
    "33774cd8fb89ddcf156469dec60e90bfb0b2ef82",
    EXPECTED_SPEC_BLOB,
    "0166518d5b4a7ac4d9278b689225c5d193dbda0f",
    EXPECTED_PLAN_BLOB,
    "715eb2ff74a424ef016025de6315bbd36ff38486",
    "b7fa282e71650496ec6a5751499f7927268ff63b",
    "07b0eeb44317b5bb104da46abef5f233cbe77703",
]:
    ck(checks, "source_ref_" + token[:12], token in h, token)

for pr in ["#7462", "#7664", "#7669", "#7777", "#7773", "#7793", "#7788"]:
    ck(checks, "collision_" + pr[1:], pr in h, pr)

ck(checks, "nuclear_first_vertical", "Nuclear Value Capture" in h and "theme:nuclear_power" in h)
ck(checks, "primary_supplemental", "primary basket:" in h and "supplemental basket:" in h and "nuclear_power" in h and "uranium_miners" in h)
ck(checks, "power_next_expansion", "Power-Demand Value Capture" in h)
ck(checks, "why_fable", "**WHY FABLE:**" in h and "WHY NOT FABLE for routine work" in h)
ck(checks, "do_not_redo", "WHAT MUST NOT BE REDONE" in h and all(x in h for x in ["R1 taxonomy", "R2 hydrocarbon", "R3 power-demand", "R4 nuclear", "R5 consensus", "R6 product thesis"]))
ck(checks, "research_pr_not_product_branch", "Product implementation begins from fresh then-current" in h)
ck(checks, "no_second_owner_planes", all(x in h for x in ["No second Theme Graph", "No Energy database", "No new identity plane", "No new correction/supersession plane"]))
ck(checks, "privacy_completion", "full-fidelity current research is unavailable to anonymous/free/public mirrors" in h and "private/no-store/noindex/noarchive" in h)
ck(checks, "non_regression_completion", "legacy basket/theme/Prophet/entry results remain unchanged" in h)
ck(checks, "real_update_liveness", "subsequent real source update or rights-approved retained correction proves update liveness" in h)
ck(checks, "r5_grammar", "PRE_EVENT_TIMESTAMPED_VALUE" in h and "Forecast-year rollover is not a revision" in h)
ck(checks, "no_placeholders", not re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", h))
ck(checks, "research_hold", "DRAFT / HOLD / DO NOT MERGE AUTOMATICALLY" in h)
ck(checks, "packet_ready_not_delivered", "ready for deliberate delivery/placement" in h and "Repository existence alone is not receiver assignment" in h)
ck(checks, "ene_requirements_source_intact", len(re.findall(r"\*\*(ENE-(\d{2}))\*\*", s)) == 78)
ck(checks, "plan_tasks_intact", len(re.findall(r"^## \d+\. Task \d+ —", p, re.M)) == 11)
ck(checks, "checkpoint_next_action_packet", "Create the durable Fable CEO master execution packet" in c)

failures = [x for x in checks if not x["pass"]]
result = {
    "artifact_type": "energy_fable_handoff_integrity_receipt",
    "operation_key": "gmi-energy-fable-ceo-e2e-20260923-chairman-001",
    "handoff_file": str(HANDOFF.relative_to(ROOT)),
    "handoff_git_blob": git_blob(hb),
    "handoff_sha256": hashlib.sha256(hb).hexdigest(),
    "checkpoint_git_blob": git_blob(cb),
    "spec_git_blob": git_blob(sb),
    "plan_git_blob": git_blob(pb),
    "passed": len(checks) - len(failures),
    "failed": len(failures),
    "receiver_assigned": False,
    "pickup_ack_observed": False,
    "start_observed": False,
    "implementation_started": False,
    "application_tests_run": 0,
    "claim_limit": "Packet/source/receiver-semantics integrity only. This receipt does not assign Fable, create runtime work, establish shared-interface acceptance, start implementation, prove source rights, deploy product code or satisfy browser/production acceptance.",
    "checks": checks,
}
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k:v for k,v in result.items() if k != "checks"}, indent=2))
if failures:
    print(json.dumps(failures, indent=2))
    raise SystemExit(1)
