#!/usr/bin/env python3
"""Fail-closed, zero-network Agent OS -> Linear P1 project dry-run.

The accepted MAS-65 P0 plan owns the *desired* workstream representation.
An explicit, separately reviewed immutable WS->project ID mapping owns bindings.
A read-only, time-bound Linear snapshot is witness evidence, not source truth.

This module intentionally cannot apply updates, create projects or authenticate.
MAS-64 app-actor enrollment and MAS-66 real-path canaries remain independent gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# File-path entry execution must resolve this checkout before foreign packages.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from scripts.linear_portfolio_plan import PLAN_SCHEMA, canonical_bytes

SCHEMA = "linear_projector_p1_offline_diff.v1"
SNAPSHOT_SCHEMA = "linear_projector_p1_snapshot.v1"
BEGIN = "[MMX-PROJECTOR:BEGIN linear_portfolio_plan.v1]"
END = "[MMX-PROJECTOR:END linear_portfolio_plan.v1]"
P0_BEGIN = "<!-- mastermind-portfolio-projector:managed:v1 -->"
P0_END = "<!-- /mastermind-portfolio-projector:managed:v1 -->"
_WS = re.compile(r"WS:[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_MANAGED_FIELDS = ("name", "summary", "description")


def _string(value: object) -> bool:
    return type(value) is str and bool(value)


def _ws_key(value: object) -> bool:
    return type(value) is str and _WS.fullmatch(value) is not None


def _timestamp(value: object) -> bool:
    """Only timezone-aware ISO timestamps qualify as observation versions."""
    if not _string(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _refuse(reason: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "status": "refused", "reason": reason, "effects": 0}


def canonical_plan(plan: object) -> bool:
    if not isinstance(plan, Mapping) or plan.get("schema") != PLAN_SCHEMA:
        return False
    actual_hash = plan.get("semantic_hash")
    if type(actual_hash) is not str or not _HASH.fullmatch(actual_hash):
        return False
    try:
        return digest({key: val for key, val in plan.items() if key != "semantic_hash"}) == actual_hash
    except (TypeError, ValueError, OverflowError):
        return False


def normalized_managed(block: object) -> str:
    """Wrap a correctly delimited P0 block in the P1 marker contract.

    This intentionally does not 'repair' an invalid or partially-adopted block.
    """
    if (
        type(block) is not str
        or block.count(P0_BEGIN) != 1
        or block.count(P0_END) != 1
        or not block.startswith(P0_BEGIN)
        or not block.endswith(P0_END)
    ):
        raise ValueError("managed_block_invalid")
    inner = block[len(P0_BEGIN):-len(P0_END)].strip("\n")
    if not inner or BEGIN in inner or END in inner:
        raise ValueError("managed_block_invalid")
    return BEGIN + "\n" + inner + "\n" + END


def replace_managed(description: object, new_managed: object) -> str:
    """Only replace one valid managed span; preserve every external byte."""
    if (
        type(description) is not str
        or type(new_managed) is not str
        or new_managed.count(BEGIN) != 1
        or new_managed.count(END) != 1
        or not new_managed.startswith(BEGIN)
        or not new_managed.endswith(END)
        or description.count(BEGIN) != 1
        or description.count(END) != 1
    ):
        raise ValueError("managed_block_invalid")
    start = description.index(BEGIN)
    stop = description.index(END) + len(END)
    if stop <= start or END in description[:start] or BEGIN in description[stop:]:
        raise ValueError("managed_block_invalid")
    inside = description[start:stop]
    if inside.count(BEGIN) != 1 or inside.count(END) != 1:
        raise ValueError("managed_block_invalid")
    return description[:start] + new_managed + description[stop:]


def _valid_plan_rows(plan: Mapping[str, Any]) -> bool:
    groups = ("active_projects", "review_candidates", "excluded_projects")
    keys: set[str] = set()
    for group in groups:
        rows = plan.get(group)
        if type(rows) is not list:
            return False
        for row in rows:
            if not isinstance(row, Mapping) or not _ws_key(row.get("workstream_key")):
                return False
            key = row["workstream_key"]
            if key in keys:
                return False
            keys.add(key)
            if group == "active_projects":
                if (
                    not all(_string(row.get(f)) for f in
                            ("desired_project_name", "desired_project_summary",
                             "desired_project_status_class", "managed_description_block"))
                    or not row["desired_project_name"].startswith(key + " — ")
                ):
                    return False
            elif group == "excluded_projects":
                if not all(_string(row.get(f)) for f in
                           ("canonical_status", "desired_project_status_class", "reason")):
                    return False
    return True


def plan_offline(
    plan: object,
    bindings: object,
    projects: object,
    *,
    expected_workspace_id: str,
    expected_team_id: str,
    expected_semantic_hash: str,
) -> dict[str, Any]:
    """Return a *read-only* deterministic plan, with zero external effects.

    The immutable project binding is an explicit input; titles never assign it.
    The caller must separately verify snapshot provenance/observation freshness.
    """
    if not canonical_plan(plan):
        return _refuse("plan_hash_mismatch_or_schema_invalid")
    assert isinstance(plan, Mapping)
    if plan["semantic_hash"] != expected_semantic_hash:
        return _refuse("plan_identity_mismatch")
    if not _valid_plan_rows(plan):
        return _refuse("plan_rows_invalid_or_duplicate_ws_key")
    if not _string(expected_workspace_id) or not _string(expected_team_id):
        return _refuse("scope_unverified")
    if not isinstance(bindings, Mapping) or type(projects) is not list:
        return _refuse("snapshot_or_binding_schema_invalid")
    # Excluded projects can carry a reviewed immutable binding, but they are
    # NEVER eligible for a mutation in the first P1 production vertical.
    desired_keys = {
        row["workstream_key"]
        for category in ("active_projects", "excluded_projects")
        for row in plan[category]
    }
    binding_values: list[str] = []
    for key, pid in bindings.items():
        if not _ws_key(key) or key not in desired_keys or not _string(pid):
            return _refuse("binding_invalid_or_unknown_workstream")
        binding_values.append(pid)
    if len(set(binding_values)) != len(binding_values):
        return _refuse("project_identity_ambiguous")

    by_id: dict[str, Mapping[str, Any]] = {}
    by_ws: dict[str, str] = {}
    for p in projects:
        if not isinstance(p, Mapping) or not _string(p.get("id")):
            return _refuse("snapshot_project_invalid")
        pid = p["id"]
        if pid in by_id:
            return _refuse("project_identity_ambiguous")
        by_id[pid] = p
        key = p.get("workstream_key")
        if key is not None:
            if not _ws_key(key):
                return _refuse("snapshot_workstream_binding_invalid")
            if key in by_ws:
                return _refuse("project_identity_ambiguous")
            by_ws[key] = pid

    results: list[dict[str, Any]] = []
    for row in sorted(plan["active_projects"], key=lambda r: r["workstream_key"]):
        key = row["workstream_key"]
        pid = bindings.get(key)
        if pid is None:
            # An omitted binding says *nothing* about whether a project exists.
            # A caller-provided WS hint can suggest a human review candidate,
            # but must never become an automatic binding or would-create verdict.
            candidate_id = by_ws.get(key)
            if candidate_id is None:
                results.append({
                    "workstream_key": key,
                    "outcome": "unbound_requires_reconciliation",
                })
            else:
                results.append({
                    "workstream_key": key,
                    "outcome": "unverified_identity_candidate",
                    "candidate_project_id": candidate_id,
                    "candidate_basis": "untrusted_snapshot_workstream_key",
                })
            continue
        p = by_id.get(pid)
        if p is None:
            # A partial snapshot cannot prove the remote project was deleted.
            results.append({
                "workstream_key": key,
                "project_id": pid,
                "outcome": "bound_project_not_observed",
            })
            continue
        result: dict[str, Any] = {"workstream_key": key, "project_id": pid}
        if p.get("trashed") or p.get("archivedAt"):
            result["outcome"] = "binding_inactive"
        elif p.get("workstream_key") != key:
            result["outcome"] = "binding_mismatch"
        elif p.get("workspace_id") != expected_workspace_id:
            result["outcome"] = "workspace_mismatch"
        elif p.get("team_id") != expected_team_id:
            result["outcome"] = "team_access_refused"
        elif not _timestamp(p.get("updatedAt")):
            result["outcome"] = "preimage_unavailable"
        elif any(type(p.get(field)) is not str for field in _MANAGED_FIELDS):
            result["outcome"] = "preimage_unavailable"
        else:
            try:
                desired_block = normalized_managed(row["managed_description_block"])
                updated_description = replace_managed(p["description"], desired_block)
            except ValueError:
                result["outcome"] = "managed_block_invalid"
            else:
                desired = {
                    "name": row["desired_project_name"],
                    "summary": row["desired_project_summary"],
                    "description": updated_description,
                }
                observed = {field: p[field] for field in _MANAGED_FIELDS}
                changes = sorted(field for field in _MANAGED_FIELDS if observed[field] != desired[field])
                current_class = p.get("status_class")
                desired_class = row["desired_project_status_class"]
                status_drift = (
                    current_class != desired_class
                    if isinstance(current_class, str)
                    else None
                )
                try:
                    preimage_hash = digest({
                        "project_id": pid,
                        "workstream_key": key,
                        "workspace_id": p["workspace_id"],
                        "team_id": p["team_id"],
                        "updatedAt": p["updatedAt"],
                        "status_class": current_class if isinstance(current_class, str) else None,
                        **observed,
                    })
                    desired_hash = digest({"project_id": pid, **desired})
                except (TypeError, ValueError, OverflowError):
                    result["outcome"] = "preimage_unavailable"
                else:
                    result.update({
                        "outcome": "would_update" if changes else "dry_run_noop",
                        "updatedAt": p["updatedAt"],
                        "preimage_hash": preimage_hash,
                        "desired_hash": desired_hash,
                        "changed_fields": changes,
                        "status_class_observed": current_class if isinstance(current_class, str) else None,
                        "status_class_desired": desired_class,
                        "status_drift": status_drift,
                        "status_change_authorized": False,
                    })
        results.append(result)

    # Existing projects for canonical done/parked workstreams are visible to
    # reviewers, but destructive archive/deactivation is NEVER in this adapter's
    # permitted field set. A partial snapshot cannot prove nonexistence.
    excluded_review: list[dict[str, Any]] = []
    for row in sorted(plan["excluded_projects"], key=lambda r: r["workstream_key"]):
        key = row["workstream_key"]
        pid = bindings.get(key)
        item: dict[str, Any] = {
            "workstream_key": key,
            "canonical_status": row["canonical_status"],
            "desired_status_class": row["desired_project_status_class"],
            "action_authorized": False,
        }
        if pid is None:
            candidate = by_ws.get(key)
            item["outcome"] = "excluded_binding_requires_review"
            if candidate is not None:
                item["candidate_project_id"] = candidate
                item["candidate_basis"] = "untrusted_snapshot_workstream_key"
        else:
            item["project_id"] = pid
            remote = by_id.get(pid)
            if remote is None:
                item["outcome"] = "excluded_bound_project_not_observed"
            elif remote.get("workstream_key") != key:
                item["outcome"] = "excluded_binding_mismatch"
            elif remote.get("workspace_id") != expected_workspace_id:
                item["outcome"] = "workspace_mismatch"
            elif remote.get("team_id") != expected_team_id:
                item["outcome"] = "team_access_refused"
            elif remote.get("trashed") or remote.get("archivedAt"):
                item["outcome"] = "excluded_inactive_observed"
            elif not _timestamp(remote.get("updatedAt")):
                item["outcome"] = "preimage_unavailable"
            else:
                current = remote.get("status_class")
                if not _string(current):
                    item["outcome"] = "excluded_status_unknown"
                else:
                    item["observed_status_class"] = current
                    item["outcome"] = (
                        "excluded_status_already_aligned"
                        if current == row["desired_project_status_class"]
                        else "would_deactivate_or_archive"
                    )
        excluded_review.append(item)

    # P0 proposal rows are never an instruction to create. A real actor must
    # first reconcile their separate admission and project-identity boundary.
    proposal_review = [
        {"workstream_key": row["workstream_key"],
         "outcome": "proposed_requires_review",
         "action_authorized": False}
        for row in sorted(plan["review_candidates"], key=lambda r: r["workstream_key"])
    ]

    actionable = {"would_update", "dry_run_noop"}
    bound_ready = sum(row["outcome"] in actionable for row in results)
    return {
        "schema": SCHEMA,
        "status": "dry_run",
        "effects": 0,
        "source_semantic_hash": plan["semantic_hash"],
        "workspace_id": expected_workspace_id,
        "team_id": expected_team_id,
        # Snapshot identity and authorized bindings are not proven by this
        # offline code; no success-shaped output may arm a remote mutation.
        "live_apply_authorized": False,
        "summary": {
            "desired_active_workstreams": len(results),
            "bound_ready_for_review": bound_ready,
            "review_required": len(results) - bound_ready,
            "unverified_identity_candidates": sum(
                row["outcome"] == "unverified_identity_candidate" for row in results
            ),
            "unbound_workstreams": sum(
                row["outcome"] == "unbound_requires_reconciliation" for row in results
            ),
            "bound_projects_not_observed": sum(
                row["outcome"] == "bound_project_not_observed" for row in results
            ),
            "snapshot_completeness_verified": False,
            "excluded_workstreams": len(excluded_review),
            "excluded_lifecycle_review_candidates": sum(
                row["outcome"] == "would_deactivate_or_archive"
                for row in excluded_review
            ),
            "proposed_workstreams_for_review": len(proposal_review),
        },
        "results": results,
        "excluded_review": excluded_review,
        "proposal_review": proposal_review,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--bindings", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--expected-semantic-hash", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--team-id", required=True)
    args = parser.parse_args(argv)
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        if not isinstance(snapshot, Mapping) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
            outcome = _refuse("snapshot_schema_invalid")
        elif (snapshot.get("workspace_id") != args.workspace_id or
              snapshot.get("team_id") != args.team_id or
              not _timestamp(snapshot.get("observed_at"))):
            outcome = _refuse("snapshot_scope_or_observation_unverified")
        else:
            outcome = plan_offline(
                plan, bindings, snapshot.get("projects"),
                expected_workspace_id=args.workspace_id,
                expected_team_id=args.team_id,
                expected_semantic_hash=args.expected_semantic_hash,
            )
    except (OSError, json.JSONDecodeError, UnicodeError, RecursionError):
        outcome = _refuse("input_unavailable_or_invalid")
    print(json.dumps(outcome, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return 0 if outcome["status"] == "dry_run" else 2


if __name__ == "__main__":
    raise SystemExit(main())
