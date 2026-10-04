#!/usr/bin/env python3
"""Fail-closed validator for the Technical Opportunity W1 method passports.

Records-only: validates research metadata and local source identity and never reads
market outcomes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PASSPORTS = ROOT / "research/technical_opportunity/w1_method_passports.jsonl"
SOURCES = ROOT / "research/technical_opportunity/w1_source_receipts.json"

TOP_KEYS = {
    "schema_version", "method_id", "canonical_name", "aliases", "source_refs",
    "rights_class", "rights_ref", "mechanism_family", "dependency_family", "role",
    "direction", "horizon_roles", "aggregation_scope", "formula", "timeframes",
    "local_implementation", "owner_disposition", "equivalence", "mechanism_story",
    "known_failure_modes", "dnd_keys", "candidate_species", "baseline_to_beat",
    "research_priority", "priority_reason",
}
FORMULA_KEYS = {
    "plain_language", "declarative_steps", "parameters", "required_columns",
    "actionable_lag_bars", "repaint_behavior",
}
LOCAL_KEYS = {"status", "paths", "signal_ids"}
EQUIV_KEYS = {"parent_method_id", "equivalence_class", "relationship"}
ALLOWED = {
    "rights_class": {"public_formula", "open_source_parity_only", "licensed", "opaque", "blocked"},
    "role": {"setup", "trigger", "participation", "context", "risk"},
    "direction": {"bullish", "bearish", "symmetric", "non_directional"},
    "aggregation_scope": {"single_security", "cross_sectional", "breadth", "sector_theme_basket", "tactical_intraday"},
    "repaint_behavior": {"none", "confirmation_lag", "provisional_only", "unknown"},
    "local_status": {"exact", "partial", "duplicate", "missing", "blocked"},
    "owner_disposition": {"toi_w3_candidate", "toi_later_context", "live_entry_radar", "terminal_display", "existing_species", "blocked"},
    "relationship": {"first_class", "parameter_variant", "alias", "algebraic_duplicate", "behavioral_duplicate", "subtype"},
    "research_priority": {"P0", "P1", "P2", "archive", "blocked"},
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        except Exception as exc:
            raise ValueError(f"{path}:{n}: invalid strict JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{n}: passport must be an object")
        rows.append(obj)
    if not rows:
        raise ValueError("passport file is empty")
    return rows


def _source_ids(path: Path = SOURCES) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    receipts = payload.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("source receipts must contain a receipts list")
    ids = [r.get("source_ref") for r in receipts if isinstance(r, dict)]
    if any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("every source receipt needs a non-empty source_ref")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source_ref")
    return set(ids)


def _validate_exact_local_identity(mid: str, local: dict[str, Any]) -> None:
    """Prove an `exact` passport names real source paths and real signal identifiers.

    This is intentionally source-text identity, not formula equivalence. It closes the
    weaker failure mode where a passport could claim an exact local implementation by
    naming a stale/nonexistent path or a signal id that is not present in the cited
    source. Formula/source reproduction remains a separate W1 review gate.
    """
    paths = local["paths"]
    signal_ids = local["signal_ids"]
    if any(not isinstance(p, str) or not p for p in paths):
        raise ValueError(f"{mid}: exact local paths must be non-empty strings")
    if any(not isinstance(sid, str) or not sid for sid in signal_ids):
        raise ValueError(f"{mid}: exact local signal_ids must be non-empty strings")
    texts: list[tuple[str, str]] = []
    for rel in paths:
        candidate = ROOT / rel
        if not candidate.is_file():
            raise ValueError(f"{mid}: exact local path missing: {rel}")
        texts.append((rel, candidate.read_text(encoding="utf-8")))
    for sid in signal_ids:
        if not any(sid in text for _, text in texts):
            raise ValueError(f"{mid}: signal_id {sid!r} not found in cited local paths")


def validate_rows(rows: list[dict[str, Any]], source_ids: set[str]) -> dict[str, Any]:
    seen: set[str] = set()
    priorities: dict[str, int] = {}
    owners: dict[str, int] = {}
    exact_local = 0
    for row in rows:
        mid = row.get("method_id", "<missing>")
        if set(row) != TOP_KEYS:
            missing = sorted(TOP_KEYS - set(row))
            extra = sorted(set(row) - TOP_KEYS)
            raise ValueError(f"{mid}: top-level schema mismatch missing={missing} extra={extra}")
        if row["schema_version"] != "toi.method_passport.v1":
            raise ValueError(f"{mid}: wrong schema_version")
        if not isinstance(mid, str) or not mid.startswith("toi.") or mid in seen:
            raise ValueError(f"invalid or duplicate method_id: {mid!r}")
        seen.add(mid)
        for field in ("canonical_name", "mechanism_family", "dependency_family", "mechanism_story", "baseline_to_beat", "priority_reason"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f"{mid}: {field} must be non-empty text")
        for field in ("aliases", "source_refs", "horizon_roles", "timeframes", "known_failure_modes", "dnd_keys", "candidate_species"):
            if not isinstance(row[field], list):
                raise ValueError(f"{mid}: {field} must be a list")
        if row["rights_class"] not in ALLOWED["rights_class"]:
            raise ValueError(f"{mid}: invalid rights_class")
        if row["role"] not in ALLOWED["role"] or row["direction"] not in ALLOWED["direction"]:
            raise ValueError(f"{mid}: invalid role/direction")
        if row["aggregation_scope"] not in ALLOWED["aggregation_scope"]:
            raise ValueError(f"{mid}: invalid aggregation_scope")
        if row["owner_disposition"] not in ALLOWED["owner_disposition"]:
            raise ValueError(f"{mid}: invalid owner_disposition")
        if row["research_priority"] not in ALLOWED["research_priority"]:
            raise ValueError(f"{mid}: invalid research_priority")
        if row["rights_class"] in {"licensed", "open_source_parity_only"} and not row["rights_ref"]:
            raise ValueError(f"{mid}: rights class requires rights_ref")
        if row["rights_class"] in {"opaque", "blocked"} and row["owner_disposition"] != "blocked":
            raise ValueError(f"{mid}: opaque/blocked source cannot receive active owner disposition")
        if row["research_priority"] in {"P0", "P1"}:
            refs = row["source_refs"]
            if not refs or not any(ref in source_ids for ref in refs):
                raise ValueError(f"{mid}: P0/P1 requires a receipted source")
        formula = row["formula"]
        if not isinstance(formula, dict) or set(formula) != FORMULA_KEYS:
            raise ValueError(f"{mid}: formula schema mismatch")
        if formula["repaint_behavior"] not in ALLOWED["repaint_behavior"]:
            raise ValueError(f"{mid}: invalid repaint_behavior")
        if not isinstance(formula["actionable_lag_bars"], int) or formula["actionable_lag_bars"] < 0:
            raise ValueError(f"{mid}: actionable_lag_bars must be a non-negative integer")
        if not isinstance(formula["parameters"], dict) or not isinstance(formula["required_columns"], list):
            raise ValueError(f"{mid}: malformed formula parameters/columns")
        local = row["local_implementation"]
        if not isinstance(local, dict) or set(local) != LOCAL_KEYS or local["status"] not in ALLOWED["local_status"]:
            raise ValueError(f"{mid}: local implementation schema/status invalid")
        if local["status"] == "exact":
            if not local["paths"] or not local["signal_ids"]:
                raise ValueError(f"{mid}: exact local implementation requires paths and signal_ids")
            _validate_exact_local_identity(mid, local)
            exact_local += 1
        equiv = row["equivalence"]
        if not isinstance(equiv, dict) or set(equiv) != EQUIV_KEYS or equiv["relationship"] not in ALLOWED["relationship"]:
            raise ValueError(f"{mid}: equivalence schema invalid")
        if any(not isinstance(k, str) or not k.startswith("DNR:") for k in row["dnd_keys"]):
            raise ValueError(f"{mid}: dnd_keys must use stable DNR:<KEY> identifiers")
        priorities[row["research_priority"]] = priorities.get(row["research_priority"], 0) + 1
        owners[row["owner_disposition"]] = owners.get(row["owner_disposition"], 0) + 1
    return {"status": "valid", "count": len(rows), "exact_local_count": exact_local, "priority_counts": priorities, "owner_counts": owners}


def main() -> int:
    result = validate_rows(_load_jsonl(PASSPORTS), _source_ids())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
