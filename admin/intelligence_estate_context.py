"""Bounded, invocation-local estate evidence for the private operator Brain.

Intelligence OS retains derivation, consistency, execution limits and authority.
This module projects one owner observation; it never persists or refreshes it.
"""
from __future__ import annotations

from contextvars import ContextVar
from functools import wraps
import hashlib
import json
from pathlib import Path

from . import intelligence_execution

MAX_CONTEXT_BYTES = 32 * 1024
MAX_ENGINES = 12
MAX_FINDINGS = 3
SCHEMA = "mastermind.admin_estate_context.v1"

_INVOCATION: ContextVar[dict | None] = ContextVar("admin_estate_observation", default=None)
_OWNER_ERRORS = frozenset({
    "changed_during_read", "evidence_estate_unavailable", "evidence_derivation_busy",
    "evidence_deadline_exceeded", "evidence_execution_unavailable",
    "evidence_cleanup_unconfirmed", "evidence_limits_unavailable",
    "evidence_binding_not_transferable", "evidence_request_invalid",
})
_ENGINE_FIELDS = (
    "engine_id", "canonical_t1", "owner_program", "producer", "output_class",
    "authority", "n_artifacts", "worst_state", "state_counts", "n_blind",
    "evidence_status", "evidence_reason_codes", "evidence_refs",
    "evidence_owner_scope", "evidence_ruler", "evidence_basis",
    "evidence_maturity", "evidence_coverage", "evidence_measurement",
)
_CENSUS_FIELDS = (
    "engines", "canonical_engines", "noncanonical_output_groups", "artifacts",
    "outputs_assessed", "by_state", "by_assessment_status", "by_output_class",
    "by_evidence_status", "by_authority", "by_storage", "by_dependency_bound",
    "top_reason_codes",
)
_FINDING_FIELDS = (
    "status", "reason", "display_only", "affects_evidence_status",
    "current_source_qualification", "source", "numeric_attribution",
    "rejected_records", "unbound_records",
)


def _digest(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _wire(value: dict) -> str:
    # Match the existing orchestrator's tool-result encoding, including escaped
    # non-ASCII text and separator whitespace, so the COMPLETE result is capped.
    return json.dumps(value, allow_nan=False)


def _fits(value: dict) -> bool:
    candidate = {**value, "snapshot_digest": "0" * 64}
    if "coverage" in value:
        # false is one byte longer than true; reserve it before final coverage.
        candidate["coverage"] = {**value["coverage"], "limited": False}
    return len(_wire(candidate).encode("utf-8")) <= MAX_CONTEXT_BYTES


def _finish(value: dict) -> dict:
    return {**value, "snapshot_digest": _digest(value)}


def unavailable(code: str) -> dict:
    return _finish({"schema": SCHEMA, "available": False, "scope": "operator_private",
                    "read_only": True, "error_code": code, "change_key": None})


def project(panel: dict) -> dict:
    """Preserve owner dispositions and qualifications; bound whole rows, not truth.

    change_key covers all projected engines and recorded findings before sampling.
    snapshot_digest identifies the exact bounded context, excluding only itself.
    Neither digest qualifies freshness or grants action authority.
    """
    if not isinstance(panel, dict) or panel.get("ok") is not True:
        code = panel.get("error_code") if isinstance(panel, dict) else None
        return unavailable(code if isinstance(code, str) and code in _OWNER_ERRORS
                           else "evidence_execution_unavailable")
    if (not isinstance(panel.get("engines"), list)
            or not isinstance(panel.get("census"), dict)
            or not isinstance(panel.get("generated"), dict)):
        return unavailable("estate_context_invalid")
    rows = []
    seen = set()
    for original in panel["engines"]:
        if (not isinstance(original, dict) or not isinstance(original.get("engine_id"), str)
                or not original["engine_id"] or original["engine_id"] in seen
                or not isinstance(original.get("canonical_t1"), bool)):
            return unavailable("estate_context_invalid")
        seen.add(original["engine_id"])
        row = {key: original.get(key) for key in _ENGINE_FIELDS}
        provider = original.get("evidence_provider")
        row["evidence_provider"] = ({key: provider.get(key) for key in
            ("kind", "binding", "family", "read_status", "recorded_snapshot")}
            if isinstance(provider, dict) else None)
        rows.append(row)
    census = {key: panel["census"].get(key) for key in _CENSUS_FIELDS}
    findings = panel.get("typed_findings")
    finding_meta = ({key: findings.get(key) for key in _FINDING_FIELDS}
                    if isinstance(findings, dict) else None)
    records = findings.get("records") if isinstance(findings, dict) else None
    gaps = findings.get("gaps") if isinstance(findings, dict) else None
    if ((records is not None and not isinstance(records, list))
            or (gaps is not None and not isinstance(gaps, list))):
        return unavailable("estate_context_invalid")
    generated = panel["generated"]
    value = {
        "schema": SCHEMA, "available": True, "scope": "operator_private", "read_only": True,
        "source": "admin.intelligence_os.panel",
        "observed_at": generated.get("observed_at"),
        "source_generation": generated.get("source_generation"),
        "root_mode": generated.get("root_mode"),
        "census": census, "engines": [],
        "typed_findings": finding_meta,
        "finding_records": [] if records is not None else None,
        "finding_gaps": [] if gaps is not None else None,
        "coverage": {"engines_total": len(rows), "engines_included": 0,
                     "engines_omitted": len(rows),
                     "finding_records_total": len(records) if records is not None else None,
                     "finding_records_included": 0 if records is not None else None,
                     "finding_records_omitted": len(records) if records is not None else None,
                     "finding_gaps_total": len(gaps) if gaps is not None else None,
                     "finding_gaps_included": 0 if gaps is not None else None,
                     "finding_gaps_omitted": len(gaps) if gaps is not None else None,
                     "limited": bool(rows or records or gaps)},
        "change_key": _digest({"census": census,
            "engines": sorted(rows, key=lambda row: row["engine_id"]),
            "typed_findings": finding_meta, "finding_records": records, "finding_gaps": gaps}),
    }
    if not _fits(value):
        return unavailable("estate_context_budget_exceeded")
    # Keep the owner's order. Oversized rows are omitted intact; every omission
    # remains counted and still contributes to change_key.
    groups = [("engines", rows, MAX_ENGINES), ("finding_records", records, MAX_FINDINGS),
              ("finding_gaps", gaps, MAX_FINDINGS)]
    for key, items, limit in groups:
        for item in items or []:
            if len(value[key]) == limit:
                break
            value[key].append(item)
            value["coverage"][key + "_included"] += 1
            value["coverage"][key + "_omitted"] -= 1
            if not _fits(value):
                value[key].pop()
                value["coverage"][key + "_included"] -= 1
                value["coverage"][key + "_omitted"] += 1
    value["coverage"]["limited"] = any(value["coverage"].get(k + "_omitted")
                                        for k, _, _ in groups)
    return _finish(value)


def within_invocation(function):
    """Share one lazy observation across rounds and provider attempts, then erase it."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        token = _INVOCATION.set({})
        try:
            return function(*args, **kwargs)
        finally:
            _INVOCATION.reset(token)
    return wrapped


def read(root: Path, params: dict) -> dict:
    if not isinstance(params, dict) or params:
        return unavailable("evidence_request_invalid")
    cache = _INVOCATION.get()
    if cache is None:
        return unavailable("estate_invocation_required")
    selected_root = Path(root).resolve()
    if cache and cache["root"] != selected_root:
        return unavailable("evidence_binding_not_transferable")
    if not cache:
        try:
            # Keep failures in the same invocation too. No retries, forced
            # refresh, alternate derivation or escape from cleanup uncertainty.
            result = project(intelligence_execution.response("panel", root=selected_root, force=False))
            encoded = _wire(result)
        except Exception:
            encoded = _wire(unavailable("evidence_execution_unavailable"))
        cache.update(root=selected_root, encoded=encoded)
    # A caller cannot mutate the frozen observation seen by later tool calls.
    return json.loads(cache["encoded"])
