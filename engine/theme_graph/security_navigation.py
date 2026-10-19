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


def _published_bindings(identity_rows, identity_kind: str, identity_id: str):
    """Validate exact published owner matches; shared by internal/display readers."""
    prefix = {"security": "SEC:", "issuer": "ISS:"}.get(identity_kind)
    if (prefix is None or not isinstance(identity_id, str) or not identity_id.startswith(prefix)
            or len(identity_id) <= len(prefix) or len(identity_id) > 512
            or any(c.isspace() or ord(c) < 32 for c in identity_id)):
        raise ValueError("identity_id must be an exact ID of the declared identity_kind")
    rows = _clean(_records(identity_rows))
    matches = [row for row in rows if row.get(identity_kind + "_id") == identity_id]
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
    return rows, matches


def compose_security_neighborhoods(store_view, identity_rows, *, identity_kind: str,
        identity_id: str, asof, knowledge_cutoff=None, rights_resolver=None) -> dict[str, Any]:
    """Traverse exact published owner references; never re-resolve a symbol or issuer."""
    rows, matches = _published_bindings(identity_rows, identity_kind, identity_id)
    effective = _parse_date(asof, "asof")
    cutoff = _parse_date(knowledge_cutoff, "knowledge_cutoff") if knowledge_cutoff is not None else effective
    result = dict(schema=SCHEMA, authority_ceiling="research_internal_only",
        query={"kind": identity_kind, "id": identity_id}, asof=effective.isoformat(),
        knowledge_cutoff=cutoff.isoformat(), identity_basis="LATEST_PUBLISHED_OWNER_REFERENCE",
        identity_owner="gmi.identity_resolution/v1", historical_identity_claim=False,
        knowledge_cutoff_applies_to="GRAPH_NEIGHBORHOODS_ONLY", bindings=[], counts=None,
        availability={"state": "IDENTITY_OWNER_UNAVAILABLE", "reason": "no published identity rows available"},
        limitations=list(LIMITATIONS))
    if not rows:
        return result
    if not matches:
        result["availability"] = {"state": "NO_GRAPH_BINDING", "reason": "no exact published owner binding"}
        return result
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


DISPLAY_SCHEMA = "gmi.theme_security_hierarchy_display/v1"
_RESOLUTION_DISPLAY_FIELDS = (
    "node_id", "security_id", "issuer_id", "listing_key", "graph_identity_epoch",
    "resolution_asof", "computed_at", "master_generated_at", "master_code_version",
)


def compose_security_hierarchy(store_view, identity_rows, *, identity_kind: str,
                               identity_id: str, asof, knowledge_cutoff=None) -> dict:
    """Exact owner identity → existing house display paths; never raw neighborhoods.

    Rights remain the incumbent default resolver. No injected permissive resolver,
    source-native symbols, owner source_receipts, vendor relations or graph bodies.
    Empty qualified paths are not evidence that a company has no themes.
    """
    from engine.theme_graph.ontology import _clock_instant, _has_time_grain, _nodes_as_known
    from engine.theme_graph.store import RETIRED_LIKE_STATUSES
    from engine.theme_graph import rights
    from engine.theme_graph.ontology import _collapse_relevant_edges, _string_list
    from engine.theme_graph.structural_navigation import hierarchy_paths

    rows, matches = _published_bindings(identity_rows, identity_kind, identity_id)
    effective = _parse_date(asof, "asof")
    raw_cutoff = effective if knowledge_cutoff is None else knowledge_cutoff
    cutoff = (_clock_instant(raw_cutoff, "knowledge_cutoff") if _has_time_grain(raw_cutoff)
              else _parse_date(raw_cutoff, "knowledge_cutoff"))
    result = dict(schema=DISPLAY_SCHEMA, authority_ceiling="display_only",
        query={"kind": identity_kind, "id": identity_id}, asof=effective.isoformat(),
        knowledge_cutoff=cutoff.isoformat(), identity_basis="LATEST_PUBLISHED_OWNER_REFERENCE",
        identity_owner="gmi.identity_resolution/v1", historical_identity_claim=False,
        knowledge_cutoff_applies_to="GRAPH_PATHS_ONLY", bindings=[],
        availability={"state": "IDENTITY_OWNER_UNAVAILABLE" if not rows else "NO_GRAPH_BINDING"},
        etf_tracking={"status": "unavailable", "reason": "ETF_DISPLAY_BINDING_NOT_COMPOSED"},
        limitations=list(LIMITATIONS))
    nodes = _records(store_view.read_nodes())
    edges = _records(store_view.read_edges())
    lifecycle = _records(store_view.read_node_lifecycle())
    view = SimpleNamespace(read_nodes=lambda: nodes, read_edges=lambda: edges,
                           read_node_lifecycle=lambda: lifecycle)
    kinds = {row.get("node_id"): row.get("kind") for row in nodes}
    evidence = _records(store_view.read_evidence())
    evidence_by_id = {}
    for receipt in evidence:
        eid = receipt.get("evidence_id")
        if eid in evidence_by_id:
            raise ValueError("duplicate graph evidence")
        evidence_by_id[eid] = receipt
    live_by_id = {}

    def house_evidence(edge_id):
        if edge_id not in live_by_id:
            candidates = [e for e in edges if e.get("edge_id") == edge_id]
            if not candidates:
                return False
            live, _ = _collapse_relevant_edges(edges, node_id=candidates[0]["src"],
                asof=effective, knowledge_cutoff=cutoff)
            live_by_id.update({e["edge_id"]: e for e in live})
        edge = live_by_id.get(edge_id)
        if not edge:
            return False
        refs = _string_list(edge.get("evidence_refs"))
        if not refs:
            return False
        for eid in refs:
            receipt = evidence_by_id.get(eid)
            if (not receipt or receipt.get("licensing_display_ok") is not True
                    or rights.family_for_source_ref(receipt.get("source_ref")) != "mastermind_curated"
                    or not rights.emission_allowed("mastermind_curated")):
                return False
        return True
    visible = _nodes_as_known(nodes, lifecycle, asof=effective, knowledge_cutoff=cutoff)
    for row in sorted(matches, key=lambda r: r["node_id"]):
        if row["node_id"] in kinds and kinds[row["node_id"]] != "company":
            raise ValueError("identity binding conflicts with the graph subject kind")
        subject = visible.get(row["node_id"])
        paths = (hierarchy_paths(view, row["node_id"], effective, knowledge_cutoff=cutoff)
                 if subject and subject.get("status") not in RETIRED_LIKE_STATUSES else [])
        # The existing display reader allows any currently qualified family;
        # this continuation deliberately admits house curation only.
        paths = [path for path in paths if all(
            element.get("rights", {}).get("family") == "mastermind_curated"
            and element["rights"].get("public_display_allowed") is True
            for element in path["path"] + [hop["node"] for hop in path["via"]])
            and all(house_evidence(eid) for eid in path["parent_of_edge_ids"]
                    + [hop["edge_id"] for hop in path["via"]])]
        result["bindings"].append({
            "resolution": {k: copy.deepcopy(row[k]) for k in _RESOLUTION_DISPLAY_FIELDS},
            "paths": paths,
            "status": "available" if paths else "unavailable",
            "reason": None if paths else "NO_QUALIFIED_HOUSE_PATH",
        })
    if matches:
        available = sum(bool(b["paths"]) for b in result["bindings"])
        result["availability"] = {"state": "AVAILABLE" if available == len(matches)
            else "PARTIAL" if available else "NO_QUALIFIED_HOUSE_PATH"}
    return result
