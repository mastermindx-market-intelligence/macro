"""Explain differences between two existing GMI neighborhood documents.

Pure input comparison: no graph reads/writes, discovery, curation or state authority.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import html
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "gmi.theme_ontology_changes/v1"
LIMITATIONS = [
    "descriptive input comparison; not capital flows, ThemeState, forecasts or trade signals",
    "knowledge revisions do not establish changes occurring on the effective comparison date",
    "both clocks changed: effective-time and knowledge effects are not separately attributed",
    "missing baseline or target is not an empty membership set",
    "digests identify input documents, not independent source authenticity or complete coverage",
    "identical clocks with changed inputs do not establish a market event",
]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads((ROOT / "contracts/theme_graph/ontology_neighborhood.v1.schema.json").read_text())
    return jsonschema.Draft202012Validator(schema)


def _validate(document: Mapping[str, Any]) -> None:
    try:
        _validator().validate(document)
        for field in ("asof", "knowledge_cutoff"):
            dt.date.fromisoformat(document[field])
        subject = document["subject"]
        if (subject is not None) != (document["availability"]["state"] == "OK"):
            raise ValueError("availability disagrees with subject")
        if subject is not None and subject["node_id"] != document["node_id"]:
            raise ValueError("subject identity disagrees with envelope")
        _canonical(document)
    except (jsonschema.ValidationError, TypeError, KeyError) as exc:
        raise ValueError("invalid neighborhood input") from exc


def _group(rows, fields):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in fields)].append(row)
    return {key: sorted(value, key=_canonical) for key, value in grouped.items()}


def _differences(before, after, fields):
    left, right = _group(before, fields), _group(after, fields)
    changes = []
    for key in sorted(set(left) | set(right)):
        old, new = left.get(key, []), right.get(key, [])
        if old == new:
            continue
        columns = sorted(set().union(*(row.keys() for row in old + new)))
        changed = [field for field in columns
                   if sorted(_canonical(row.get(field)) for row in old)
                   != sorted(_canonical(row.get(field)) for row in new)]
        changes.append(dict(zip(fields, key), change="ADDED" if not old else "REMOVED" if not new else "UPDATED",
                            before=old, after=new, changed_fields=changed))
    return changes


def build_change_report(baseline: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    """Keep membership deltas, evidence revisions and proposal decisions distinct."""
    _validate(baseline); _validate(target)
    if baseline["node_id"] != target["node_id"]:
        raise ValueError("baseline and target must identify the same exact node")
    before, after = copy.deepcopy(dict(baseline)), copy.deepcopy(dict(target))
    same_date = before["asof"] == after["asof"]
    same_cutoff = before["knowledge_cutoff"] == after["knowledge_cutoff"]
    basis = ("IDENTICAL_CLOCKS" if same_date and same_cutoff else
             "KNOWLEDGE_REVISION" if same_date else
             "EFFECTIVE_DATE_CHANGE" if same_cutoff else "BOTH_CLOCKS_CHANGED")
    old_ok = before["availability"]["state"] == "OK"
    new_ok = after["availability"]["state"] == "OK"
    state = ("OK" if old_ok and new_ok else "BOTH_UNAVAILABLE" if not old_ok and not new_ok
             else "BASELINE_UNAVAILABLE" if not old_ok else "TARGET_UNAVAILABLE")
    result = dict(schema=SCHEMA, authority_ceiling="research_internal_only", node_id=before["node_id"],
        comparison_basis=basis, availability={"state": state, "reason": None if state == "OK" else "comparison unavailable; missing is not zero"},
        baseline=before, target=after, relation_changes=[], proposal_changes=[],
        subject_changed_fields=[], mapping_changed=None, curation_changed=None, summary=None,
        input_digests={name: hashlib.sha256(_canonical(doc).encode("utf-8")).hexdigest()
                       for name, doc in (("baseline", before), ("target", after))},
        limitations=list(LIMITATIONS))
    if state != "OK":
        return result
    relations = _differences(before["relations"], after["relations"], ("type", "direction", "peer_node_id"))
    proposals = _differences(before["proposals"], after["proposals"], ("proposal_id",))
    result.update(relation_changes=relations, proposal_changes=proposals,
        subject_changed_fields=sorted(key for key in set(before["subject"]) | set(after["subject"])
                                      if before["subject"].get(key) != after["subject"].get(key)),
        mapping_changed=before["canonical_mapping"] != after["canonical_mapping"],
        curation_changed=before["curation"] != after["curation"])
    result["summary"] = {f"{kind}_{action.lower()}": sum(row["change"] == action for row in rows)
        for kind, rows in (("relations", relations), ("proposals", proposals))
        for action in ("ADDED", "REMOVED", "UPDATED")}
    result["summary"].update({f"memberships_{action.lower()}": sum(row["type"] == "MEMBER_OF"
        and row["change"] == action for row in relations) for action in ("ADDED", "REMOVED")})
    return result


def _display(value: Any) -> str:
    text = html.escape(" ".join(str(value or "").split()), quote=False)
    for char in ("\\", "`", "|", "[", "]", "*"):
        text = text.replace(char, "\\" + char)
    return text


def render_markdown(report: Mapping[str, Any]) -> str:
    """Human brief; full old/new rows remain in the JSON report, never inferred."""
    subject = report["target"]["subject"] or report["baseline"]["subject"] or {}
    title = subject.get("name_en") or subject.get("name_zh") or report["node_id"]
    lines = [f"# GMI change report: {_display(title)}", "",
             f"Exact subject: {_display(report['node_id'])}",
             f"Comparison: {_display(report['comparison_basis'])}", ""]
    for label, doc in (("Baseline", report["baseline"]), ("Target", report["target"])):
        lines.append(f"{label}: effective {doc['asof']}; knowledge cutoff {doc['knowledge_cutoff']}.")
    lines += ["", "Research context only: not capital flows, forecasts, rankings or trade signals.", ""]
    if report["summary"] is None:
        return "\n".join(lines + ["Comparison unavailable. Missing data is not an empty membership set.", ""])
    summary = report["summary"]
    lines += [f"Membership relations: +{summary['memberships_added']} / -{summary['memberships_removed']}.",
              f"Other relationship/evidence updates: {summary['relations_updated']}.",
              f"Canonical mapping changed: {report['mapping_changed']}; curation changed: {report['curation_changed']}.",
              "", "## Relationship changes", "", "| Change | Type / direction | Exact peer | Label | Evidence before → after |",
              "| --- | --- | --- | --- | --- |"]
    for row in report["relation_changes"][:100]:
        peer = next((x["peer"] for x in row["after"] + row["before"] if x.get("peer")), {})
        label = peer.get("name_en") or peer.get("name_zh") or "unavailable"
        evidence = [", ".join(sorted({str(ref) for x in row[side] for ref in x["evidence_refs"]})) or "none"
                    for side in ("before", "after")]
        cells = [row["change"], row["type"] + " / " + row["direction"], row["peer_node_id"], label,
                 evidence[0] + " → " + evidence[1]]
        lines.append("| " + " | ".join(_display(x) for x in cells) + " |")
    if not report["relation_changes"]:
        lines.append("No relationship changes in these inputs.")
    if len(report["relation_changes"]) > 100:
        lines.append(f"Showing 100 of {len(report['relation_changes'])} relationship changes; JSON contains all rows.")
    lines += ["", "## Proposal changes", ""]
    for row in report["proposal_changes"][:100]:
        status = [", ".join(x["status"] for x in row[side]) or "unavailable" for side in ("before", "after")]
        lines.append(f"{_display(row['proposal_id'])}: {_display(status[0])} → {_display(status[1])}; proposal only.")
    if not report["proposal_changes"]:
        lines.append("No proposal changes in these inputs.")
    if len(report["proposal_changes"]) > 100:
        lines.append(f"Showing 100 of {len(report['proposal_changes'])} proposal changes; JSON contains all rows.")
    lines += ["", "## Subject and mapping updates", ""]
    for field in report["subject_changed_fields"]:
        old_value = report["baseline"]["subject"].get(field)
        new_value = report["target"]["subject"].get(field)
        lines.append(f"{_display(field)}: {_display(old_value if old_value is not None else 'null')} → {_display(new_value if new_value is not None else 'null')}")
    if not report["subject_changed_fields"]:
        lines.append("No subject metadata changes.")
    if report["mapping_changed"]:
        for label, document in (("Before", report["baseline"]), ("After", report["target"])):
            mapping = document["canonical_mapping"]
            lines.append(f"{label} mapping: {_display(mapping['state'])}; exact themes: {_display(', '.join(mapping['theme_node_ids']) or 'none')}.")
    lines += ["", "## Interpretation limits", ""] + list(report["limitations"])
    lines += ["", "Input document digests: " + report["input_digests"]["baseline"] + " / " + report["input_digests"]["target"], ""]
    return "\n".join(lines)
