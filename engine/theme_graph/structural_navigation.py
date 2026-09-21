"""Read source-owned sector baskets and local parents without a classification master.

Only exact crosswalk-registered sector-context baskets qualify. These references
are not official issuer classifications and do not manufacture graph edges.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from engine.theme_graph.ontology import compose_neighborhood, _default_rights_resolver
from engine.theme_graph import rights
from engine.theme_graph.change_report import _display

CROSSWALK_PATH = Path(__file__).resolve().parents[2] / "config/theme_crosswalk.yml"
SCHEMA = "gmi.theme_structural_context/v1"
LIMITATIONS = [
    "Sector references are recorded memberships in owner-registered context baskets, not complete official company classifications.",
    "The latest stored crosswalk identifies references; graph clocks select memberships, not historical owner classifications.",
    "Source-local parent references retain recorded node metadata; they are not sector, industry or subindustry equivalence.",
    "No industry/subindustry owner is bound here. Missing references do not establish absence of a real classification.",
    "No graph mutation, canonical mapping, curation approval, public-display permission, ranking or trading authority.",
]


class _OwnerLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node):
    result = {}
    for key, value in loader.construct_pairs(node, deep=True):
        if key in result:
            raise ValueError("duplicate structural owner key")
        result[key] = value
    return result


_OwnerLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_structural_owner():
    """Read the incumbent crosswalk once; no alternate CLI-supplied registry."""
    with CROSSWALK_PATH.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("structural owner document exceeds 1 MiB")
    try:
        document = yaml.load(raw, Loader=_OwnerLoader)
    except yaml.YAMLError as exc:
        raise ValueError("unreadable structural owner document") from exc
    return document, hashlib.sha256(raw).hexdigest()


def _owner_index(document):
    if not isinstance(document, dict) or not isinstance(document.get("unmapped_baskets"), list):
        raise ValueError("structural owner requires the existing unmapped_baskets registry")
    index, seen = {}, set()
    for position, row in enumerate(document["unmapped_baskets"]):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("invalid structural owner reference")
        key = row["id"]
        if key in seen:
            raise ValueError("duplicate structural owner reference")
        seen.add(key)
        # The accepted owner census reserves this exact namespace for sector context.
        # A matching display label, sector leg, or unregistered basket is insufficient.
        if key.startswith("us_sector_"):
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                raise ValueError("structural owner reference lacks its declared meaning")
            index[key] = dict(reason=row["reason"], source_pointer=f"/unmapped_baskets/{position}")
    return index


def compose_structure(store_view, *, node_id, asof, knowledge_cutoff=None,
                      owner_document=None, owner_sha256=None, rights_resolver=None):
    if owner_document is None:
        owner_document, owner_sha256 = load_structural_owner()
    if not isinstance(owner_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", owner_sha256) is None:
        raise ValueError("structural owner digest required")
    index = _owner_index(owner_document)
    resolver = _default_rights_resolver if rights_resolver is None else rights_resolver
    neighborhood = compose_neighborhood(store_view, node_id=node_id, asof=asof,
        knowledge_cutoff=knowledge_cutoff, rights_resolver=resolver)
    def query(identity):
        return dict(node_id=identity, asof=neighborhood["asof"],
                    knowledge_cutoff=neighborhood["knowledge_cutoff"])
    def sector_reference(node):
        if not node or node["kind"] != "basket":
            return None
        external = node["external_ids"]
        key = external.get("basket_id")
        if (not isinstance(key, str) or key not in index or external.get("suite") != "baskets"
                or node["node_id"] != "basket:baskets:" + key):
            return None
        return dict(reference_kind="REGISTERED_SECTOR_CONTEXT_BASKET", node_id=node["node_id"],
            basket_id=key, owner_reason=index[key]["reason"], source_pointer=index[key]["source_pointer"],
            neighborhood_query=query(node["node_id"]), membership_evidence=[])
    def parent_reference(node, membership=None):
        if not node or node["kind"] != "local_theme":
            return None
        metadata = node.get("source_meta") or {}
        key = metadata.get("parent_source_key")
        if key is None or key == "":
            return None
        family = metadata.get("source_family")
        if (not isinstance(key, str) or not isinstance(family, str) or not family
                or family != rights.family_for_node_id(node["node_id"])
                or not isinstance(metadata.get("parent_source_label"), (str, type(None)))):
            raise ValueError("invalid source-local parent reference")
        return dict(reference_kind="SOURCE_LOCAL_PARENT_REFERENCE", local_node_id=node["node_id"],
            source_family=family, parent_source_key=key, parent_source_label=metadata.get("parent_source_label"),
            reference_basis="RECORDED_NODE_SOURCE_METADATA", rights=resolver(node["node_id"]),
            neighborhood_query=query(node["node_id"]), membership_evidence=[] if membership is None else [membership])
    subject = neighborhood["subject"]
    subject_reference = sector_reference(subject)
    sectors, parents, members = {}, {}, set()
    parent = parent_reference(subject)
    if parent:
        parents[parent["local_node_id"]] = parent
    for relation in neighborhood["relations"]:
        if relation["type"] != "MEMBER_OF":
            continue
        if relation["direction"] == "OUTGOING":
            sector = sector_reference(relation["peer"])
            if sector:
                record = sectors.setdefault(sector["node_id"], sector)
                record["membership_evidence"].append(relation)
            parent = parent_reference(relation["peer"], relation)
            if parent:
                existing = parents.get(parent["local_node_id"])
                if existing: existing["membership_evidence"].append(relation)
                else: parents[parent["local_node_id"]] = parent
        elif subject_reference and relation["direction"] == "INCOMING":
            peer = relation["peer"]
            if peer and peer["kind"] == "company":
                members.add(peer["node_id"])
    sector_rows = [sectors[key] for key in sorted(sectors)]
    parent_rows = [parents[key] for key in sorted(parents)]
    state = "SUBJECT_UNAVAILABLE" if subject is None else "REFERENCES_FOUND" if sector_rows or subject_reference else "NO_RECORDED_REFERENCE"
    return dict(schema=SCHEMA, authority_ceiling="research_internal_only", neighborhood=neighborhood,
        owner_reference_basis="LATEST_STORED_CROSSWALK", historical_classification_claim=False,
        historical_hierarchy_claim=False,
        owner_reference=dict(source_path="config/theme_crosswalk.yml", sha256=owner_sha256,
                             registered_sector_baskets=len(index)),
        subject_reference=subject_reference, sector_references=sector_rows, source_parent_references=parent_rows,
        member_queries=[query(key) for key in sorted(members)],
        counts=dict(sector_references=len(sector_rows), source_parent_references=len(parent_rows), member_queries=len(members)),
        coverage=dict(sector=dict(state=state, reason="Recorded sector-context references only; no complete classification claim."),
            industry=dict(state="OWNER_NOT_BOUND", reason="No accepted industry identity owner bound to this view."),
            subindustry=dict(state="OWNER_NOT_BOUND", reason="No accepted subindustry identity owner bound to this view.")),
        limitations=list(LIMITATIONS))


def render_markdown(result):
    n = result["neighborhood"]
    lines = ["# GMI structural references", "", _display(n["node_id"]),
        f"Graph effective date: {n['asof']}; knowledge cutoff: {n['knowledge_cutoff']}.",
        "Latest stored owner references; not official or historical company classification.", "",
        "## Recorded sector-context baskets"]
    refs = result["sector_references"] or ([result["subject_reference"]] if result["subject_reference"] else [])
    for row in refs:
        lines.append(_display(row["node_id"]) + " — " + _display(row["owner_reason"]))
    if not refs: lines.append("No recorded sector-context reference in this view.")
    lines += ["", "## Source-local parents"]
    for row in result["source_parent_references"]:
        lines.append(_display(row["local_node_id"]) + " → " + _display(row["source_family"] + ":" + row["parent_source_key"]))
    if not result["source_parent_references"]: lines.append("No recorded source-local parent reference.")
    lines += ["", "Industry: OWNER_NOT_BOUND. Subindustry: OWNER_NOT_BOUND.",
        "Exact neighborhood queries and original membership evidence are retained in JSON.", "", *LIMITATIONS, ""]
    return "\n".join(lines)
