#!/usr/bin/env python3
"""Fail-closed validation for TOI W1 residual-family dispositions.

Records-only. This validates family ownership / kill / W3-exclusion metadata and
never reads market outcomes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESIDUALS = ROOT / "research/technical_opportunity/w1_residual_family_dispositions.json"

TOP_KEYS = {
    "schema_version", "as_of", "authority", "parent_operation", "rule",
    "families", "family_counts", "w3_trial_family_effect", "outcomes_read",
}
REQUIRED_FAMILY_KEYS = {
    "family_id", "representative_methods", "research_priority",
    "owner_disposition", "local_state", "evidence_paths", "dnr_keys",
    "w3_first_vertical", "reason",
}
OPTIONAL_FAMILY_KEYS = {
    "local_signal_ids", "dnr_interpretation", "horizon_owner_boundary",
    "known_at_boundary", "canonical_owner", "aggregation_scope",
}
ALLOWED_PRIORITIES = {"P2", "archive", "blocked"}
ALLOWED_W3 = {"hold", "exclude", "comparator_or_context_only", "blocked"}


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != TOP_KEYS:
        raise ValueError("residual top-level schema mismatch")
    if payload.get("schema_version") != "toi.w1_residual_family_dispositions.v1":
        raise ValueError("wrong residual schema")
    if payload.get("parent_operation") != "TOI-W1-EVIDENCE-CENSUS-V1":
        raise ValueError("wrong residual parent operation")
    if payload.get("outcomes_read") is not False:
        raise ValueError("residual census must remain outcome-blind")
    if not isinstance(payload.get("authority"), str) or not payload["authority"]:
        raise ValueError("residual authority boundary missing")
    if not isinstance(payload.get("rule"), str) or not payload["rule"]:
        raise ValueError("residual rule missing")
    if not isinstance(payload.get("w3_trial_family_effect"), str) or not payload["w3_trial_family_effect"]:
        raise ValueError("residual W3 effect boundary missing")

    families = payload.get("families")
    if not isinstance(families, list) or len(families) != 10:
        raise ValueError("residual census must contain exactly 10 families")

    seen: set[str] = set()
    counts = {"P2": 0, "archive": 0, "blocked": 0}
    for row in families:
        if not isinstance(row, dict):
            raise ValueError("residual family must be an object")
        keys = set(row)
        if not REQUIRED_FAMILY_KEYS <= keys or keys - (REQUIRED_FAMILY_KEYS | OPTIONAL_FAMILY_KEYS):
            raise ValueError(f"{row.get('family_id')}: residual family schema mismatch")
        fid = row.get("family_id")
        if not isinstance(fid, str) or not fid or fid in seen:
            raise ValueError(f"invalid/duplicate residual family_id {fid!r}")
        seen.add(fid)
        priority = row.get("research_priority")
        if priority not in ALLOWED_PRIORITIES:
            raise ValueError(f"{fid}: invalid residual priority")
        counts[priority] += 1
        if not isinstance(row.get("representative_methods"), list) or not row["representative_methods"]:
            raise ValueError(f"{fid}: representative_methods missing")
        if not isinstance(row.get("evidence_paths"), list) or not row["evidence_paths"]:
            raise ValueError(f"{fid}: evidence_paths missing")
        if not isinstance(row.get("owner_disposition"), str) or not row["owner_disposition"]:
            raise ValueError(f"{fid}: owner disposition missing")
        if not isinstance(row.get("local_state"), str) or not row["local_state"]:
            raise ValueError(f"{fid}: local state missing")
        if row.get("w3_first_vertical") not in ALLOWED_W3:
            raise ValueError(f"{fid}: invalid W3 first-vertical disposition")
        dnr = row.get("dnr_keys")
        if not isinstance(dnr, list) or any(not isinstance(k, str) or not k.startswith("DNR:") for k in dnr):
            raise ValueError(f"{fid}: invalid DNR key")
        if priority == "blocked":
            if row.get("owner_disposition") != "blocked" or row.get("w3_first_vertical") != "blocked":
                raise ValueError(f"{fid}: blocked family must fail closed")
        elif row.get("w3_first_vertical") == "blocked":
            raise ValueError(f"{fid}: only blocked priority may use blocked W3 disposition")

    expected = {**counts, "total": len(families)}
    if payload.get("family_counts") != expected:
        raise ValueError(f"residual family_counts mismatch expected={expected}")
    return {"status": "valid", "family_count": len(families), "family_counts": expected}


def main() -> int:
    payload = json.loads(RESIDUALS.read_text(encoding="utf-8"))
    print(json.dumps(validate(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
