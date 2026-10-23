"""Exact current-published Data OS references into existing GMI neighborhoods.

No identity resolution, allocation, ticker matching, new store or historical-identity claim.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jsonschema
from engine.theme_graph.ontology import (
    _clean, _default_rights_resolver, _parse_date, _records, compose_neighborhood,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "gmi.theme_security_neighborhoods/v1"
LIMITATIONS = [
    "Identity bindings are the latest published owner snapshot, not historical as-known-at identity.",
    "Requested effective/knowledge clocks apply only to the graph neighborhoods.",
    "Owner resolution and master clocks are retained; this reader makes no freshness guarantee.",
    "Aliases, topology epochs and share classes remain distinct; memberships are not merged.",
    "No binding is not proof that the security is unknown or has no themes.",
    "No new identity, public-display permission, classification, ranking or trading authority.",
]


@lru_cache(maxsize=1)
def _binding_validator():
    schema = json.loads((ROOT / "contracts/theme_graph/identity_resolution.v1.schema.json").read_text())
    return jsonschema.Draft202012Validator(schema)


def compose_security_neighborhoods(store_view, identity_rows, *, identity_kind: str,
        identity_id: str, asof, knowledge_cutoff=None, rights_resolver=None) -> dict[str, Any]:
    """Traverse exact published owner references; never re-resolve a symbol or issuer."""
    prefix = {"security": "SEC:", "issuer": "ISS:"}.get(identity_kind)
    if (prefix is None or not isinstance(identity_id, str) or not identity_id.startswith(prefix)
            or len(identity_id) <= len(prefix) or len(identity_id) > 512
            or any(c.isspace() or ord(c) < 32 for c in identity_id)):
        raise ValueError("identity_id must be an exact ID of the declared identity_kind")
    effective = _parse_date(asof, "asof")
    cutoff = _parse_date(knowledge_cutoff, "knowledge_cutoff") if knowledge_cutoff is not None else effective
    rows = _clean(_records(identity_rows))
    result = dict(schema=SCHEMA, authority_ceiling="research_internal_only",
        query={"kind": identity_kind, "id": identity_id}, asof=effective.isoformat(),
        knowledge_cutoff=cutoff.isoformat(), identity_basis="LATEST_PUBLISHED_OWNER_REFERENCE",
        identity_owner="gmi.identity_resolution/v1", historical_identity_claim=False,
        knowledge_cutoff_applies_to="GRAPH_NEIGHBORHOODS_ONLY", bindings=[], counts=None,
        availability={"state": "IDENTITY_OWNER_UNAVAILABLE", "reason": "no published identity rows available"},
        limitations=list(LIMITATIONS))
    if not rows:
        return result
    matches = [row for row in rows if row.get(identity_kind + "_id") == identity_id]
    if not matches:
        result["availability"] = {"state": "NO_GRAPH_BINDING", "reason": "no exact published owner binding"}
        return result
    node_counts = Counter(row.get("node_id") for row in rows)
    for row in matches:
        try:
            _binding_validator().validate(row)
            dt.date.fromisoformat(row["resolution_asof"])
            dt.datetime.fromisoformat(row["computed_at"].replace("Z", "+00:00"))
        except (jsonschema.ValidationError, TypeError, KeyError, ValueError) as exc:
            raise ValueError("invalid published identity binding") from exc
        if (row["resolution_state"] != "RESOLVED" or not row["security_id"]
                or not row["listing_key"] or row["join_method"] == "refused"
                or row["refusal_reason"] is not None or not row["node_id"].startswith("co:")):
            raise ValueError("inconsistent resolved identity binding")
        if node_counts[row["node_id"]] != 1:
            raise ValueError("duplicate current identity binding for graph node")
    nodes, edges = _records(store_view.read_nodes()), _records(store_view.read_edges())
    proposals = _records(store_view.read_proposals())
    lifecycle_reader = getattr(store_view, "read_node_lifecycle", None)
    lifecycle = _records(lifecycle_reader()) if callable(lifecycle_reader) else []
    snapshot = SimpleNamespace(read_nodes=lambda: nodes, read_edges=lambda: edges,
        read_proposals=lambda: proposals, read_node_lifecycle=lambda: lifecycle)
    resolver = _default_rights_resolver if rights_resolver is None else rights_resolver
    for row in sorted(matches, key=lambda item: item["node_id"]):
        neighborhood = compose_neighborhood(snapshot, node_id=row["node_id"], asof=effective,
            knowledge_cutoff=cutoff, rights_resolver=resolver)
        if neighborhood["subject"] is not None and neighborhood["subject"]["kind"] != "company":
            raise ValueError("identity binding conflicts with the graph subject kind")
        result["bindings"].append(dict(node_id=row["node_id"], resolution=copy.deepcopy(row),
                                        neighborhood=neighborhood))
    matched = len(result["bindings"])
    available = sum(item["neighborhood"]["availability"]["state"] == "OK" for item in result["bindings"])
    result["counts"] = dict(matched_nodes=matched, available_nodes=available, unavailable_nodes=matched - available)
    state = "OK" if available == matched else "PARTIAL_GRAPH_VISIBILITY" if available else "GRAPH_SUBJECTS_UNAVAILABLE"
    result["availability"] = {"state": state, "reason": None if state == "OK" else "published identity and historical graph visibility differ"}
    return result
