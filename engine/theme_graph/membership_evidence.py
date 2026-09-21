"""Member-by-member evidence from an existing exact proposal-review export.

Pure document consumer: no graph access, discovery, adjudication or investment authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import jsonschema
from referencing import Registry, Resource
from engine.theme_graph.change_report import _canonical, _display, _validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "gmi.theme_ontology_overlap_evidence/v1"
LIMITATIONS = [
    "Observed exact graph-node memberships only; not proof of semantic expression or an approval recommendation.",
    "No security alias or label merging: different graph node IDs remain distinct even for the same security.",
    "Ratios describe recorded sets, not weights, significance, complete coverage, capital flow or trade signals.",
    "Original proposal evidence has its own creation clock; it is not recomputed historical evidence.",
    "Rights receipts are copied from the input; this internal report does not grant public display permission.",
    "Input digests identify documents, not independent source authenticity or an atomic graph generation.",
]


@lru_cache(maxsize=1)
def _review_validator():
    root = ROOT / "contracts/theme_graph"
    neighborhood = json.loads((root / "ontology_neighborhood.v1.schema.json").read_text())
    schema = json.loads((root / "ontology_proposal_review.v1.schema.json").read_text())
    registry = Registry().with_resource(neighborhood["$id"], Resource.from_contents(neighborhood))
    return jsonschema.Draft202012Validator(schema, registry=registry)


def _members(endpoint):
    grouped, seen = defaultdict(list), {}
    for row in endpoint["relations"]:
        if row["type"] != "MEMBER_OF" or row["direction"] != "INCOMING":
            continue
        node_id, peer = row["peer_node_id"], row["peer"]
        if not node_id.startswith("co:"):
            continue
        if peer is not None and (peer["node_id"] != node_id or peer["kind"] != "company"):
            raise ValueError("membership peer identity is inconsistent")
        encoded = _canonical(row)
        if row["edge_id"] in seen and seen[row["edge_id"]] != encoded:
            raise ValueError("conflicting membership evidence for one edge_id")
        seen[row["edge_id"]] = encoded
        grouped[node_id].append(row)
    return {key: sorted(rows, key=_canonical) for key, rows in grouped.items()}


def build_overlap_evidence(document: Mapping[str, Any]) -> dict[str, Any]:
    """Explain recorded overlap without equating overlap, ratification and graph truth."""
    try:
        _review_validator().validate(document)
        encoded = _canonical(document)
        for endpoint in document["endpoints"]:
            _validate(endpoint)
            if any(endpoint[k] != document[k] for k in ("asof", "knowledge_cutoff")):
                raise ValueError("endpoint clocks disagree with proposal review")
    except (jsonschema.ValidationError, TypeError, KeyError) as exc:
        raise ValueError("invalid proposal-review input") from exc
    source = copy.deepcopy(dict(document))
    proposal, relation = source["proposal"], source["relation"]
    result = dict(schema=SCHEMA, authority_ceiling="research_internal_only",
        proposal_id=source["proposal_id"], asof=source["asof"], knowledge_cutoff=source["knowledge_cutoff"],
        source_node_id=relation["source_node_id"], target_node_id=relation["target_node_id"],
        proposal_status=proposal["status"] if proposal else None,
        reported_created=proposal["created"] if proposal else None,
        reported_evidence=proposal["evidence"] if proposal else None,
        mapping_relation_state=relation["state"],
        availability={"state": "PROPOSAL_UNAVAILABLE", "reason": "proposal unavailable at requested cutoff"},
        counts=None, ratios=None, shared=[], source_only=[], target_only=[], metadata_unavailable_ids=[],
        input_digest=hashlib.sha256(encoded.encode("utf-8")).hexdigest(), limitations=list(LIMITATIONS))
    result["reported_count_comparison"] = _reported_count_comparison(result, source)
    if proposal is None:
        return result
    if proposal["proposal_id"] != source["proposal_id"]:
        raise ValueError("proposal identity disagrees with review")
    subject = proposal["subject"]
    keys = set(subject)
    if proposal["kind"] != "mapping" or keys not in ({"basket", "local_theme"}, {"local_theme", "canonical_theme"}):
        result["availability"] = {"state": "UNSUPPORTED_SUBJECT", "reason": "not an exact supported mapping pair"}
        return result
    pair = ((subject["basket"], subject["local_theme"]) if "basket" in subject
            else (subject["local_theme"], subject["canonical_theme"]))
    if relation["state"] == "UNSUPPORTED_SUBJECT":
        result["availability"] = {"state": "UNSUPPORTED_SUBJECT", "reason": "proposal reader refused subject interpretation"}
        return result
    if pair != (relation["source_node_id"], relation["target_node_id"]) or relation["type"] != "EXPRESSES":
        raise ValueError("mapping endpoint identities disagree")
    endpoints = source["endpoints"]
    if len(endpoints) != 2 or tuple(x["node_id"] for x in endpoints) != pair:
        raise ValueError("review must bind both exact mapping endpoints in order")
    if any(x["availability"]["state"] != "OK" for x in endpoints):
        result["availability"] = {"state": "ENDPOINT_UNAVAILABLE", "reason": "missing endpoint is not an empty set"}
        return result
    left, right = (_members(endpoint) for endpoint in endpoints)
    a, b = set(left), set(right)
    for label, ids in (("shared", a & b), ("source_only", a - b), ("target_only", b - a)):
        result[label] = [dict(node_id=node_id, source_memberships=left.get(node_id, []),
                              target_memberships=right.get(node_id, [])) for node_id in sorted(ids)]
    result["counts"] = dict(source=len(a), target=len(b), shared=len(a & b),
        source_only=len(a - b), target_only=len(b - a), union=len(a | b))
    result["metadata_unavailable_ids"] = sorted({node_id for table in (left, right)
        for node_id, rows in table.items() if any(row["peer"] is None for row in rows)})
    if not a or not b:
        result["availability"] = {"state": "INSUFFICIENT_MEMBERSHIP_EVIDENCE",
                                  "reason": "one endpoint has no recorded company memberships; ratios abstain"}
        return result
    result["availability"] = {"state": "OK", "reason": None}
    result["ratios"] = dict(source_containment=len(a & b) / len(a),
        target_containment=len(a & b) / len(b), jaccard=len(a & b) / len(a | b))
    result["reported_count_comparison"] = _reported_count_comparison(result, source)
    return result


def render_markdown(report: Mapping[str, Any]) -> str:
    """A readable evidence drilldown; JSON retains every full original membership row."""
    lines = ["# GMI proposal membership evidence", "",
        f"Proposal: {_display(report['proposal_id'])}; status: {_display(report['proposal_status'])}.",
        f"Effective date: {report['asof']}; knowledge cutoff: {report['knowledge_cutoff']}.",
        f"Exact mapping relation: {_display(report['mapping_relation_state'])}.", "",
        "Research context only. Overlap is not semantic expression, approval or a trading signal.", "",
        f"Source: {_display(report['source_node_id'])}; target: {_display(report['target_node_id'])}.",
        f"Evidence availability: {_display(report['availability']['state'])}."]
    if report["counts"] is not None:
        c = report["counts"]
        lines += [f"Recorded member IDs: source {c['source']}; target {c['target']}; shared {c['shared']}.",
                  f"Source-only {c['source_only']}; target-only {c['target_only']}; union {c['union']}."]
    if report["ratios"] is not None:
        lines += ["Observed-set ratios (not statistical significance): " +
                  "; ".join(f"{key}={value:.4f}" for key, value in report["ratios"].items()) + "."]
    else:
        lines.append("Ratios unavailable; missing evidence does not prove zero overlap.")
    for field, title in (("shared", "Shared members"), ("source_only", "Source-only members"),
                         ("target_only", "Target-only members")):
        rows = report[field]
        lines += ["", "## " + title, "", "| Exact node | Label | Source evidence | Target evidence |",
                  "| --- | --- | --- | --- |"]
        for member in rows[:100]:
            proofs = member["source_memberships"] + member["target_memberships"]
            peer = next((row["peer"] for row in proofs if row["peer"] is not None), {})
            label = peer.get("name_en") or peer.get("name_zh") or "metadata unavailable"
            refs = [", ".join(sorted({ref for row in member[side] for ref in row["evidence_refs"]})) or "none"
                    for side in ("source_memberships", "target_memberships")]
            lines.append("| " + " | ".join(_display(x) for x in (member["node_id"], label, *refs)) + " |")
        if len(rows) > 100:
            lines.append(f"Showing 100 of {len(rows)} rows; JSON contains all membership evidence.")
        if not rows:
            lines.append("No rows in this group; consult evidence availability before interpreting absence.")
    comparison = report.get("reported_count_comparison")
    if comparison is not None:
        lines += ["", "## Reported counts versus recorded sets", "",
            _display(comparison["state"]),
            "Same-vintage comparability is not established; differences do not identify a cause."]
        for row in comparison["fields"]:
            lines.append(f"{row['field']}: reported {row['reported']}; recorded {row['observed']}; difference {row['delta']}.")
        for key in ("missing_fields", "invalid_fields"):
            if comparison[key]:
                lines.append(_display(key) + ": " + _display(", ".join(comparison[key])))
        if comparison["state"] == "NOT_EVALUATED":
            lines.append("Count comparison unavailable: " + _display(comparison["reason"]))
    lines += ["", "## Original proposal evidence — separate observation", "",
              f"Proposal creation clock: {_display(report['reported_created'])}.",
              _display(_canonical(report["reported_evidence"])), "",
              "This original statistic is not automatically comparable to the current recorded sets.",
              "", "## Interpretation limits", "", *report["limitations"], "",
              "Input document SHA-256: " + report["input_digest"], ""]
    return "\n".join(lines)


def _reported_count_comparison(report, document):
    """Compare cardinality figures only; matching values do not prove matching vintages."""
    comparison = dict(state="NOT_EVALUATED", reason="observed_membership_evidence_unavailable",
        same_vintage_verified=False, fields=[], missing_fields=[], invalid_fields=[])
    if report["availability"]["state"] != "OK":
        return comparison
    proposal = document["proposal"]
    if (proposal["proposed_by"] != "overlap_stats"
        or not str(report["source_node_id"]).startswith("basket:")
        or not str(report["target_node_id"]).startswith("ltheme:")):
        comparison["reason"] = "unsupported_metric_semantics"
        return comparison
    evidence = report["reported_evidence"]
    for field, count_key in (("basket_size", "source"), ("subtheme_size", "target"), ("overlap", "shared")):
        if field not in evidence:
            comparison["missing_fields"].append(field)
            continue
        value = evidence[field]
        if type(value) is not int or value < 0:
            comparison["invalid_fields"].append(field)
            continue
        observed = report["counts"][count_key]
        comparison["fields"].append(dict(field=field, reported=value, observed=observed,
                                         delta=observed - value))
    incomplete = bool(comparison["missing_fields"] or comparison["invalid_fields"])
    differs = any(row["delta"] != 0 for row in comparison["fields"])
    comparison["state"] = ("REPORTED_COUNTS_DIFFER" if differs else
                           "REPORTED_COUNTS_PARTIAL" if incomplete else "REPORTED_COUNTS_EQUAL")
    comparison["reason"] = "reported_counts_incomplete" if incomplete else None
    return comparison
