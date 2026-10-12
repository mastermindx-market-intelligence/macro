"""Read-only local-concept discovery through the existing GMI ontology reader.

The inventory is a disposable projection, not a queue, mapping or identity owner.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from types import SimpleNamespace
from engine.theme_graph import probation, rights
from engine.theme_graph.change_report import _canonical, _display
from engine.theme_graph.ontology import (
    _default_rights_resolver, _nodes_as_known, _parse_date, _records,
    _contains_exact, compose_neighborhood,
)

SCHEMA = "gmi.theme_ontology_inventory/v1"
MAPPINGS = frozenset({"all", "mapped", "unmapped"})
CURATIONS = frozenset({"all", "with_proposals", "without_proposals", "proposed", "ratified", "rejected"})
LIMITATIONS = [
    "Read-only local-concept projection; not a new queue or taxonomy.",
    "Unmapped concepts remain useful; no label match or proposal creates a mapping.",
    "Mapping counts describe graph relationships, not approved proposals.",
    "All visible lifecycle states are included and reported, including retired nodes.",
    "Exact-ID order is navigation, never research or investment priority.",
    "The digest binds this projection and evidence, not authenticity or freshness.",
    "Research-internal only; no new rights, public display, ranking, sizing or trading authority.",
]


def compose_inventory(store_view, *, asof, knowledge_cutoff=None, source_family=None,
        mapping="all", curation="all", offset=0, limit=25, expected_snapshot=None,
        rights_resolver=_default_rights_resolver):
    """Enumerate concepts; delegate semantic interpretation to the existing owner."""
    effective = _parse_date(asof, "asof")
    cutoff = _parse_date(knowledge_cutoff, "knowledge_cutoff") if knowledge_cutoff is not None else effective
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("limit must be 1..100 and offset a nonnegative integer")
    if mapping not in MAPPINGS or curation not in CURATIONS:
        raise ValueError("unknown mapping or curation filter")
    if source_family is not None and (not isinstance(source_family, str) or not source_family
            or len(source_family) > 128 or any(c.isspace() or ord(c) < 32 for c in source_family)):
        raise ValueError("source_family must be an exact owner-family identifier")
    if expected_snapshot is not None and (not isinstance(expected_snapshot, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_snapshot) is None):
        raise ValueError("invalid expected snapshot")
    if offset and expected_snapshot is None:
        raise ValueError("continued pages require the first page snapshot")
    nodes = _records(store_view.read_nodes())
    edges = _records(store_view.read_edges())
    proposals = _records(store_view.read_proposals())
    lifecycle_reader = getattr(store_view, "read_node_lifecycle", None)
    lifecycle = _records(lifecycle_reader()) if callable(lifecycle_reader) else []
    probation.require_valid_rows(proposals)
    by_node = {}
    for row in nodes:
        node_id = row.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("graph node is missing exact node_id")
        if node_id in by_node:
            raise ValueError("duplicate graph node identity")
        if row.get("kind") == "local_theme" and not node_id.startswith("ltheme:"):
            raise ValueError("local concept has an invalid exact identity")
        by_node[node_id] = row
    visible = _nodes_as_known(nodes, lifecycle, asof=effective, knowledge_cutoff=cutoff)
    local_ids = sorted(key for key, row in visible.items() if row.get("kind") == "local_theme")
    edge_index, lifecycle_index = defaultdict(list), defaultdict(list)
    for row in edges:
        for node_id in {row.get("src"), row.get("dst")}:
            edge_index[node_id].append(row)
    for row in lifecycle:
        lifecycle_index[row.get("node_id")].append(row)
    rights_cache = {}
    def resolve(node_id):
        if node_id not in rights_cache:
            rights_cache[node_id] = rights_resolver(node_id)
        return rights_cache[node_id]
    items = []
    for node_id in local_ids:
        incident = edge_index[node_id]
        peer_ids = {node_id}
        for edge in incident:
            peer_ids.update((edge.get("src"), edge.get("dst")))
        selected_nodes = [row for key, row in by_node.items() if key in peer_ids]
        selected_lifecycle = [row for key in sorted(x for x in peer_ids if isinstance(x, str))
                              for row in lifecycle_index[key]]
        selected_proposals = [row for row in proposals if _contains_exact(row.get("subject"), node_id)]
        view = SimpleNamespace(read_nodes=lambda: selected_nodes, read_edges=lambda: incident,
            read_proposals=lambda: selected_proposals, read_node_lifecycle=lambda: selected_lifecycle)
        document = compose_neighborhood(view, node_id=node_id, asof=effective,
            knowledge_cutoff=cutoff, rights_resolver=resolve)
        items.append(dict(node=document["subject"], source_family=rights.family_for_node_id(node_id),
            rights=resolve(node_id), canonical_mapping=document["canonical_mapping"],
            curation=document["curation"], neighborhood_counts=document["counts"],
            neighborhood_query=dict(node_id=node_id, asof=effective.isoformat(), knowledge_cutoff=cutoff.isoformat()),
            neighborhood_sha256=hashlib.sha256(_canonical(document).encode("utf-8")).hexdigest()))
    filters = dict(source_family=source_family, mapping=mapping, curation=curation)
    def matches(item):
        if source_family is not None and item["source_family"] != source_family:
            return False
        if mapping != "all" and item["canonical_mapping"]["state"].lower() != mapping:
            return False
        if curation == "with_proposals": return bool(item["curation"]["proposal_ids"])
        if curation == "without_proposals": return not item["curation"]["proposal_ids"]
        return curation == "all" or item["curation"]["counts"].get(curation, 0) > 0
    selected = [item for item in items if matches(item)]
    facets = {key: dict(sorted(Counter(values).items())) for key, values in {
        "source_family": [item["source_family"] or "UNKNOWN" for item in items],
        "mapping_state": [item["canonical_mapping"]["state"] for item in items],
        "curation_state": [item["curation"]["state"] for item in items],
        "node_status": [item["node"]["status"] for item in items],
    }.items()}
    stamp = dict(schema=SCHEMA, asof=effective.isoformat(), knowledge_cutoff=cutoff.isoformat(),
                 graph_available=bool(nodes), filters=filters, items=items)
    digest = hashlib.sha256(_canonical(stamp).encode("utf-8")).hexdigest()
    if expected_snapshot is not None and digest != expected_snapshot:
        raise ValueError("ontology inventory snapshot changed; restart from the first page")
    page = selected[offset:offset + limit]
    state = "GRAPH_UNAVAILABLE" if not nodes else "EMPTY" if not items else "NO_MATCH" if not selected else "OK"
    reasons = {"GRAPH_UNAVAILABLE": "no graph node records available", "EMPTY": "no visible local concepts",
               "NO_MATCH": "no local concepts match the exact filters", "OK": None}
    mapped = sum(item["canonical_mapping"]["state"] == "MAPPED" for item in items)
    with_proposals = sum(bool(item["curation"]["proposal_ids"]) for item in items)
    counts = dict(visible=len(items), matching=len(selected), returned=len(page), mapped=mapped,
        unmapped=len(items)-mapped, with_proposals=with_proposals, without_proposals=len(items)-with_proposals) if nodes else None
    return dict(schema=SCHEMA, authority_ceiling="research_internal_only", asof=effective.isoformat(),
        knowledge_cutoff=cutoff.isoformat(), filters=filters, ordering="EXACT_NODE_ID",
        availability=dict(state=state, reason=reasons[state]), counts=counts, facets=facets,
        snapshot_sha256=digest, page=dict(offset=offset, limit=limit,
            next_offset=offset+len(page) if offset+len(page)<len(selected) else None),
        items=page, limitations=list(LIMITATIONS))


def render_markdown(inventory):
    """Render a bounded research page with existing exact-owner drilldown arguments."""
    lines = ["# GMI local-concept inventory", "", "Research-internal, read-only; not an approval or ranking.",
        f"Effective date: {inventory['asof']}; knowledge cutoff: {inventory['knowledge_cutoff']}."]
    counts = inventory["counts"]
    if counts is None:
        lines += ["", "GRAPH_UNAVAILABLE — no graph node records available."]
    else:
        lines += [f"Visible: {counts['visible']}; mapped: {counts['mapped']}; unmapped: {counts['unmapped']}.",
            f"Matching: {counts['matching']}; this page: {counts['returned']}.",
            "", "| Exact local ID | Source label | Lifecycle | Canonical mapping | Proposal state |",
            "| --- | --- | --- | --- | --- |"]
        for item in inventory["items"]:
            node, mapping = item["node"], item["canonical_mapping"]
            values = [node["node_id"], node["name_en"] or node["name_zh"] or "", node["status"],
                      mapping["state"] + ": " + ", ".join(mapping["theme_node_ids"]), item["curation"]["state"]]
            lines.append("| " + " | ".join(_display(v) for v in values) + " |")
    lines += ["", "## Exact evidence drilldown", "",
        "Pass an item's neighborhood_query to scripts/query_theme_ontology.py; JSON retains exact arguments.",
        "Then inspect its existing proposal IDs; an inventory row does not create or approve a proposal.",
        "", "Snapshot: " + inventory["snapshot_sha256"]]
    if inventory["page"]["next_offset"] is not None:
        lines.append(f"Next page: --offset {inventory['page']['next_offset']} --snapshot {inventory['snapshot_sha256']} (same filters and clocks).")
    lines += ["", "## Limits", "", *inventory["limitations"], ""]
    return "\n".join(lines)
