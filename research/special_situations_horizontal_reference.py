"""Research-only reference semantics for Special Situations horizontal integration.

No IO, scoring, ranking, recommendation, publication, or production authority.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Iterable

DIRECT_ROLES = {"target"}
AFFECTED_ROLES = {
    "affected_through_general_partner_control",
    "affected_through_controller",
    "affected_through_parent",
    "affected_through_adviser",
}


def map_transaction_relationships(rows: Iterable[dict]) -> dict:
    """Summarize one canonical transaction without turning affected securities into targets."""
    rows = [deepcopy(r) for r in rows]
    event_refs = {str(r.get("event_ref") or "").strip() for r in rows if r.get("event_ref")}
    if len(event_refs) > 1:
        raise ValueError("rows must describe one canonical transaction")
    direct = sorted({str(r["security"]) for r in rows if r.get("role") in DIRECT_ROLES})
    affected = sorted({str(r["security"]) for r in rows if r.get("role") in AFFECTED_ROLES})
    origins = {str(r.get("source_origin") or "").strip() for r in rows if r.get("source_origin")}
    return {
        "event_ref": next(iter(event_refs), None),
        "direct_targets": direct,
        "affected_securities": affected,
        "independent_source_origins": len(origins),
    }


def transaction_lifecycle(events: Iterable[dict]) -> dict[str, dict]:
    """Build lifecycle state strictly within each transaction_id."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for raw in events:
        e = deepcopy(raw)
        transaction_id = str(e.get("transaction_id") or "").strip()
        if not transaction_id:
            raise ValueError("transaction_id required")
        grouped[transaction_id].append(e)

    out: dict[str, dict] = {}
    for transaction_id, rows in grouped.items():
        rows.sort(key=lambda r: str(r.get("known_at") or ""))
        current = rows[-1].get("stage") if rows else None
        out[transaction_id] = {
            "current_stage": current,
            "history": rows,
            "terminal": current if current in {"closed", "terminated", "withdrawn"} else None,
        }
    return out


def merge_discovery_enrichment(
    discovered: Iterable[dict],
    enrichment: dict[str, dict],
    *,
    special_items: set[str],
) -> list[dict]:
    """Preserve authoritative discovery when enrichment is absent; drop observed negatives."""
    out: list[dict] = []
    for raw in discovered:
        row = deepcopy(raw)
        accession = str(row.get("accession") or "")
        meta = enrichment.get(accession)
        if meta is None:
            row["items"] = []
            row["items_unknown"] = True
            row["enrichment_status"] = "unknown"
            out.append(row)
            continue
        items = [str(x) for x in meta.get("items") or []]
        if not (set(items) & special_items):
            continue
        row["items"] = items
        row["items_unknown"] = False
        row["enrichment_status"] = "observed"
        out.append(row)
    return out


def invalidate_dependent_cases(cases: Iterable[dict], *, changed_dependencies: set[str]) -> dict:
    """Return scoped invalidation; unrelated cases are preserved."""
    invalidated: list[str] = []
    preserved: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id") or "")
        deps = set(case.get("dependencies") or set())
        if deps & changed_dependencies:
            invalidated.append(case_id)
        else:
            preserved.append(case_id)
    return {"invalidated": invalidated, "preserved": preserved}\n\ndef route_registrant_event(\n    *,\n    category: str,\n    registrant_role: str | None,\n    direct_roles: set[str],\n    affected_relation: str | None = None,\n) -> dict:\n    \"\"\"Keep document-event family separate from the registrant's security role.\n\n    direct_roles is supplied by the family-specific semantic adapter; this\n    reference deliberately does not invent one universal role matrix. An\n    incompatible or missing registrant role never becomes a direct security event.\n    If an incumbent owner has separately bound an affected relationship, retain\n    the event as indirect context. Otherwise withhold the security projection\n    until that relationship is resolved.\n    \"\"\"\n    role = str(registrant_role or \"none\").strip().lower() or \"none\"\n    allowed = {str(r).strip().lower() for r in direct_roles if str(r).strip()}\n    if role in allowed:\n        return {\n            \"category\": category,\n            \"projection\": \"direct\",\n            \"security_role\": role,\n            \"direct_event_security\": True,\n            \"direct_target\": role == \"target\",\n            \"reason\": None,\n        }\n    if affected_relation is not None:\n        relation = str(affected_relation).strip()\n        if relation not in AFFECTED_ROLES:\n            raise ValueError(\"affected_relation is not an admitted reference relation\")\n        return {\n            \"category\": category,\n            \"projection\": \"affected\",\n            \"security_role\": relation,\n            \"direct_event_security\": False,\n            \"direct_target\": False,\n            \"reason\": None,\n        }\n    return {\n        \"category\": category,\n        \"projection\": \"withheld\",\n        \"security_role\": role,\n        \"direct_event_security\": False,\n        \"direct_target\": False,\n        \"reason\": \"relationship_unresolved\",\n    }\n