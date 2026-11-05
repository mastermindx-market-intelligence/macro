"""Cutoff-correct worklist over the existing probation owner, with no queue writes.

Pages are stateless projections; their content digest is not an acceptance receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import jsonschema
from engine.theme_graph import probation
from engine.theme_graph.change_report import _canonical, _display
from engine.theme_graph.ontology import _parse_date, _proposal_as_known, _proposal_projection

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "gmi.theme_proposal_worklist/v1"
LIMITATIONS = [
    "Read-only view of the existing probation owner; no new queue or adjudication.",
    "Proposals are not graph facts, recommendations, rankings or trade signals.",
    "Oldest creation first is browsing order, not research or investment priority.",
    "Effective date is carried to drilldown; only the cutoff selects proposal knowledge.",
    "A snapshot digest binds this visible worklist, not source authenticity or rights.",
]


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads((ROOT / "contracts/theme_graph/probation_proposal.v1.schema.json").read_text())
    return jsonschema.Draft202012Validator(schema)


def compose_worklist(rows, *, asof, knowledge_cutoff=None, status="proposed", kind=None,
        proposed_by=None, subject_id=None, offset=0, limit=25, expected_snapshot=None):
    """Select exact existing proposals; stable pages retain the original evidence."""
    effective = _parse_date(asof, "asof")
    cutoff = _parse_date(knowledge_cutoff, "knowledge_cutoff") if knowledge_cutoff is not None else effective
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("limit must be 1..100 and offset a nonnegative integer")
    if status not in probation.STATUSES | {"all"}:
        raise ValueError("unknown proposal status")
    if kind is not None and kind not in probation.PROPOSAL_KINDS:
        raise ValueError("unknown proposal kind")
    if proposed_by is not None and proposed_by not in probation.PROPOSED_BY:
        raise ValueError("unknown proposer")
    if subject_id is not None and (not isinstance(subject_id, str) or ":" not in subject_id
            or len(subject_id) > 512 or any(c.isspace() or ord(c) < 32 for c in subject_id)):
        raise ValueError("subject_id must be an exact identifier, not a label")
    if expected_snapshot is not None and (not isinstance(expected_snapshot, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_snapshot) is None):
        raise ValueError("invalid expected snapshot")
    if offset and expected_snapshot is None:
        raise ValueError("continued pages require the first page snapshot")
    probation.require_valid_rows(rows)
    visible, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid proposal row")
        known = _proposal_as_known(row, cutoff)
        if known is None:
            continue
        try:
            _validator().validate(row)
        except jsonschema.ValidationError as exc:
            raise ValueError("invalid proposal row") from exc
        errors = probation.validate(row)
        if errors:
            raise ValueError(f"invalid proposal: {errors}")
        if row["proposal_id"] in seen:
            raise ValueError("duplicate visible proposal identity")
        seen.add(row["proposal_id"])
        visible.append(_proposal_projection(known))
    visible.sort(key=lambda row: (probation._parse_stamp(row["created"], "created"), row["proposal_id"]))
    filters = dict(status=status, kind=kind, proposed_by=proposed_by, subject_id=subject_id)
    facets = {key: dict(sorted(Counter(row[key] for row in visible).items()))
              for key in ("status", "kind", "proposed_by")}
    facets["status"] = {key: facets["status"].get(key, 0) for key in sorted(probation.STATUSES)}
    selected = [row for row in visible if (status == "all" or row["status"] == status)
        and (kind is None or row["kind"] == kind)
        and (proposed_by is None or row["proposed_by"] == proposed_by)
        and (subject_id is None or any(value == subject_id for value in row["subject"].values()))]
    stamp = dict(schema=SCHEMA, asof=effective.isoformat(), knowledge_cutoff=cutoff.isoformat(),
                 filters=filters, proposals=visible)
    digest = hashlib.sha256(_canonical(stamp).encode("utf-8")).hexdigest()
    if expected_snapshot is not None and expected_snapshot != digest:
        raise ValueError("worklist snapshot changed; restart from the first page")
    page = selected[offset:offset + limit]
    state = "EMPTY" if not visible else "NO_MATCH" if not selected else "OK"
    return dict(schema=SCHEMA, authority_ceiling="research_internal_only", asof=effective.isoformat(),
        knowledge_cutoff=cutoff.isoformat(), filters=filters, ordering="CREATED_UTC_THEN_PROPOSAL_ID",
        availability={"state": state, "reason": None if state == "OK" else "no visible proposals" if state == "EMPTY" else "no proposals match the exact filters"},
        counts=dict(visible=len(visible), matching=len(selected), returned=len(page)), facets=facets,
        snapshot_sha256=digest, page=dict(offset=offset, limit=limit,
            next_offset=offset + len(page) if offset + len(page) < len(selected) else None),
        items=[dict(proposal=row, review_query=dict(proposal_id=row["proposal_id"],
            asof=effective.isoformat(), knowledge_cutoff=cutoff.isoformat())) for row in page],
        limitations=list(LIMITATIONS))


def render_markdown(worklist):
    """Present a bounded page, with exact IDs for the existing review consumer."""
    c, p = worklist["counts"], worklist["page"]
    lines = ["# GMI proposal worklist", "", "PROPOSAL_ONLY — research-internal, read-only.",
        f"Effective date for drilldown: {worklist['asof']}; knowledge cutoff: {worklist['knowledge_cutoff']}.",
        f"Visible proposals: {c['visible']}; matching: {c['matching']}; this page: {c['returned']}.",
        "Filters: " + _display(_canonical(worklist["filters"])),
        "Order: creation time in UTC, then exact proposal ID; not priority.", "",
        "| Proposal | Status | Kind | Proposer | Created | Exact subjects |",
        "| --- | --- | --- | --- | --- | --- |"]
    for item in worklist["items"]:
        row = item["proposal"]
        cells = (row["proposal_id"], row["status"], row["kind"], row["proposed_by"],
                 row["created"], _canonical(row["subject"]))
        lines.append("| " + " | ".join(_display(value) for value in cells) + " |")
    if not worklist["items"]:
        lines.append("No rows on this page. " + _display(worklist["availability"]["reason"] or ""))
    lines += ["", "## Evidence drilldown", "",
        "Use an item's exact review_query with scripts/query_theme_ontology.py. No mapping is approved by appearing here.",
        "The JSON output retains proposal evidence, notes, source references and exact query arguments.",
        "", "Snapshot: " + worklist["snapshot_sha256"]]
    if p["next_offset"] is not None:
        lines.append(f"Next page: --offset {p['next_offset']} --snapshot {worklist['snapshot_sha256']} (retain the same filters and clocks).")
    lines += ["", "## Limits", "", *worklist["limitations"], ""]
    return "\n".join(lines)
