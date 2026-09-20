"""Exact-ID, dual-clock ontology neighborhood reader for GMI D2D.

This module composes existing graph truth with the existing probation queue.  It does
not mint edges, fuzzy-match labels, ratify proposals, rank relations, or create another
ontology/taxonomy owner.  A probation row remains proposal-only even when ratified; an
accepted relationship becomes graph truth only when an existing graph producer emits it.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from engine.theme_graph import probation, rights, store

SCHEMA = "gmi.theme_ontology_neighborhood/v1"
AUTHORITY_CEILING = "research_internal_only"
ORDERING = "type,direction,peer_node_id,edge_id; never score"


class StoreView(Protocol):
    def read_nodes(self) -> Any: ...

    def read_node_lifecycle(self) -> Any: ...

    def read_edges(self) -> Any: ...

    def read_proposals(self) -> Any: ...


class RepositoryStore:
    """Read-only adapter over the canonical Theme Graph owners."""

    def read_nodes(self) -> Any:
        return store.read_nodes(current=False)

    def read_node_lifecycle(self) -> Any:
        return store.read_node_lifecycle(latest=False)

    def read_edges(self) -> Any:
        # Dual-clock selection must see the append-only belief history.
        return store.read_edges(latest_belief=False)

    def read_proposals(self) -> Any:
        return probation.read_proposals(store.probation_path())


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        try:
            return [dict(row) for row in value.to_dict("records")]
        except TypeError:
            pass
    return [dict(row) for row in value]


def _is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _clean(value: Any) -> Any:
    """Convert pandas/NumPy-shaped values into deterministic JSON values."""
    if _is_null(value):
        return None
    item = getattr(value, "item", None)
    if callable(item):
        try:
            value = item()
        except (TypeError, ValueError):
            pass
    to_list = getattr(value, "tolist", None)
    if callable(to_list) and not isinstance(value, (str, bytes, bytearray)):
        try:
            value = to_list()
        except (TypeError, ValueError):
            pass
    if isinstance(value, Mapping):
        return {str(key): _clean(val) for key, val in value.items()}
    if isinstance(value, (set, frozenset)):
        return [_clean(item) for item in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


def _json_object(value: Any) -> dict[str, Any] | None:
    if _is_null(value) or value == "":
        return None
    if isinstance(value, Mapping):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return None
        if isinstance(parsed, Mapping):
            return {str(k): _clean(v) for k, v in parsed.items()}
    return None


def _string_list(value: Any) -> list[str]:
    value = _clean(value)
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return [value] if value else []
        value = parsed
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_string_list(item))
        return out
    text = str(value).strip()
    return [text] if text else []


def _parse_date(value: Any, field: str) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value or "").strip()
    try:
        return dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD, got {text!r}") from exc


def _clock_instant(value: Any, field: str) -> dt.datetime:
    """Compare belief clocks in UTC; keep legacy unzoned/date-only behavior."""
    if isinstance(value, dt.datetime):
        stamp = value
    elif isinstance(value, dt.date):
        stamp = dt.datetime.combine(value, dt.time.min)
    else:
        text = str(value or "").strip()
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            stamp = dt.datetime.fromisoformat(normalized)
        except ValueError:
            stamp = dt.datetime.combine(_parse_date(text, field), dt.time.min)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=dt.timezone.utc)
    return stamp.astimezone(dt.timezone.utc)


def _clock_date(value: Any, field: str) -> dt.date:
    return _clock_instant(value, field).date()


def _node_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "node_id": str(row.get("node_id") or ""),
        "kind": str(row.get("kind") or ""),
        "name_en": None if _is_null(row.get("name_en")) else str(row.get("name_en")),
        "name_zh": None if _is_null(row.get("name_zh")) else str(row.get("name_zh")),
        "market_scope": str(row.get("market_scope") or ""),
        "tier": None if _is_null(row.get("tier")) else str(row.get("tier")),
        "status": str(row.get("status") or ""),
        "merged_into": (
            None if _is_null(row.get("merged_into")) else str(row.get("merged_into"))
        ),
        "external_ids": _json_object(row.get("external_ids")) or {},
        "source_meta": _json_object(row.get("source_meta")),
        "provenance": str(row.get("provenance") or ""),
    }


def _nodes_as_known(
    node_rows: Sequence[Mapping[str, Any]],
    lifecycle_rows: Sequence[Mapping[str, Any]],
    *,
    asof: dt.date,
    knowledge_cutoff: dt.date,
) -> dict[str, dict[str, Any]]:
    visible: dict[str, dict[str, Any]] = {}
    for original in node_rows:
        row = dict(original)
        node_id = str(row.get("node_id") or "")
        if not node_id:
            continue
        computed = row.get("computed_at")
        if not _is_null(computed) and _clock_date(
            computed, "computed_at"
        ) > knowledge_cutoff:
            continue
        birth = row.get("birth_date")
        if not _is_null(birth) and _parse_date(birth, "birth_date") > asof:
            continue
        visible[node_id] = row

    latest: dict[str, tuple[dt.datetime, int, dict[str, Any]]] = {}
    for index, original in enumerate(lifecycle_rows):
        row = dict(original)
        node_id = str(row.get("node_id") or "")
        if node_id not in visible:
            continue
        computed = row.get("computed_at")
        if _is_null(computed):
            continue
        computed_instant = _clock_instant(computed, "computed_at")
        if computed_instant.date() > knowledge_cutoff:
            continue
        candidate = (computed_instant, index, row)
        if node_id not in latest or candidate[:2] > latest[node_id][:2]:
            latest[node_id] = candidate

    for node_id, (_computed, _index, lifecycle) in latest.items():
        retire = lifecycle.get("retire_date")
        effective = (
            _parse_date(retire, "retire_date")
            if not _is_null(retire)
            else _clock_date(lifecycle.get("computed_at"), "computed_at")
        )
        if effective > asof:
            continue
        row = dict(visible[node_id])
        row["status"] = lifecycle.get("status")
        row["retire_date"] = lifecycle.get("retire_date")
        row["merged_into"] = lifecycle.get("merged_into")
        visible[node_id] = row
    return visible


def _contains_exact(value: Any, node_id: str) -> bool:
    value = _clean(value)
    if isinstance(value, Mapping):
        return any(_contains_exact(item, node_id) for item in value.values())
    if isinstance(value, list):
        return any(_contains_exact(item, node_id) for item in value)
    return isinstance(value, str) and value == node_id


def _default_rights_resolver(node_id: str) -> dict[str, Any] | None:
    family = rights.family_for_node_id(node_id)
    if family is None:
        return None
    try:
        current_class = rights.rights_class(family)
        allowed = rights.emission_allowed(family)
    except rights.RightsRefusal:
        return {
            "family": family,
            "rights_class": "REFUSED_UNKNOWN",
            "public_display_allowed": False,
        }
    return {
        "family": family,
        "rights_class": current_class,
        "public_display_allowed": bool(allowed),
    }


def _collapse_relevant_edges(
    rows: Sequence[Mapping[str, Any]],
    *,
    node_id: str,
    asof: dt.date,
    knowledge_cutoff: dt.date,
) -> tuple[list[dict[str, Any]], int]:
    eligible: list[tuple[dt.date, str, int, dict[str, Any]]] = []
    future_beliefs = 0
    for index, original in enumerate(rows):
        row = dict(original)
        src = str(row.get("src") or "")
        dst = str(row.get("dst") or "")
        if node_id not in {src, dst}:
            continue
        edge_id = str(row.get("edge_id") or "")
        type_ = str(row.get("type") or "")
        if not edge_id or not type_ or not src or not dst:
            raise ValueError("relevant edge is missing edge_id/type/src/dst")
        belief = _parse_date(row.get("belief_time"), "belief_time")
        if belief > knowledge_cutoff:
            future_beliefs += 1
            continue
        eligible.append((belief, str(row.get("computed_at") or ""), index, row))

    latest: dict[str, tuple[dt.date, str, int, dict[str, Any]]] = {}
    for candidate in eligible:
        edge_id = str(candidate[3]["edge_id"])
        if edge_id not in latest or candidate[:3] > latest[edge_id][:3]:
            latest[edge_id] = candidate

    live: list[dict[str, Any]] = []
    for _belief, _computed_at, _index, row in latest.values():
        valid_from = _parse_date(row.get("valid_from"), "valid_from")
        raw_valid_to = row.get("valid_to")
        valid_to = None if _is_null(raw_valid_to) or str(raw_valid_to).strip() == "" else _parse_date(
            raw_valid_to, "valid_to"
        )
        if valid_from <= asof and (valid_to is None or asof < valid_to):
            live.append(row)
    return live, future_beliefs


def _rights_for_relation(
    node_ids: Sequence[str],
    resolver: Callable[[str], dict[str, Any] | None],
) -> list[dict[str, Any]]:
    by_family: dict[str, dict[str, Any]] = {}
    for node_id in sorted(set(node_ids)):
        receipt = resolver(node_id)
        if not receipt:
            continue
        family = str(receipt.get("family") or "")
        if not family:
            continue
        normalized = {
            "family": family,
            "rights_class": str(receipt.get("rights_class") or "REFUSED_UNKNOWN"),
            "public_display_allowed": bool(receipt.get("public_display_allowed", False)),
        }
        if family in by_family and by_family[family] != normalized:
            raise ValueError(f"conflicting rights receipts for family {family!r}")
        by_family[family] = normalized
    return [by_family[key] for key in sorted(by_family)]


def _relation_projection(
    row: Mapping[str, Any],
    *,
    node_id: str,
    node_map: Mapping[str, Mapping[str, Any]],
    rights_resolver: Callable[[str], dict[str, Any] | None],
) -> dict[str, Any]:
    src = str(row["src"])
    dst = str(row["dst"])
    if src == node_id and dst == node_id:
        direction = "SELF"
        peer_id = node_id
    elif src == node_id:
        direction = "OUTGOING"
        peer_id = dst
    else:
        direction = "INCOMING"
        peer_id = src
    peer = node_map.get(peer_id)
    return {
        "edge_id": str(row["edge_id"]),
        "type": str(row["type"]),
        "direction": direction,
        "peer_node_id": peer_id,
        "peer": _node_projection(peer) if peer else None,
        "valid_from": str(row["valid_from"]),
        "valid_to": None if _is_null(row.get("valid_to")) else str(row.get("valid_to")),
        "evidence_time": str(row.get("evidence_time") or ""),
        "belief_time": str(row.get("belief_time") or ""),
        "source_class": str(row.get("source_class") or ""),
        "date_provenance": str(row.get("date_provenance") or ""),
        "evidence_refs": _string_list(row.get("evidence_refs")),
        "confidence_basis": str(row.get("confidence_basis") or ""),
        "truth_status": "GRAPH_TRUTH",
        "rights": _rights_for_relation((src, dst), rights_resolver),
    }


def _proposal_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": str(row.get("proposal_id") or ""),
        "kind": str(row.get("kind") or ""),
        "subject": _clean(row.get("subject")) or {},
        "evidence": _clean(row.get("evidence")) or {},
        "evidence_refs": _string_list(row.get("evidence_refs")),
        "proposed_by": str(row.get("proposed_by") or ""),
        "created": str(row.get("created") or ""),
        "status": str(row.get("status") or ""),
        "ratified_by": (
            None if _is_null(row.get("ratified_by")) else str(row.get("ratified_by"))
        ),
        "adjudicated_at": (
            None
            if _is_null(row.get("adjudicated_at"))
            else str(row.get("adjudicated_at"))
        ),
        "note": None if _is_null(row.get("note")) else str(row.get("note")),
        "truth_status": "PROPOSAL_ONLY",
    }


def _proposal_as_known(
    row: Mapping[str, Any], knowledge_cutoff: dt.date
) -> dict[str, Any] | None:
    known = dict(row)
    created = _clock_date(known.get("created"), "created")
    if created > knowledge_cutoff:
        return None
    status = str(known.get("status") or "")
    if status in {"ratified", "rejected"}:
        adjudicated = _clock_date(known.get("adjudicated_at"), "adjudicated_at")
        if adjudicated > knowledge_cutoff:
            known["status"] = "proposed"
            known["ratified_by"] = None
            known["adjudicated_at"] = None
            known["note"] = None
    return known


def _proposal_mapping_edge(
    row: Mapping[str, Any],
) -> tuple[str, str, str] | None:
    if str(row.get("kind") or "") != "mapping":
        return None
    subject = row.get("subject")
    if not isinstance(subject, Mapping):
        return None
    local = str(subject.get("local_theme") or "")
    canonical = str(subject.get("canonical_theme") or "")
    basket = str(subject.get("basket") or "")
    if local and canonical:
        return ("EXPRESSES", local, canonical)
    if basket and local:
        return ("EXPRESSES", basket, local)
    return None


def _curation_summary(
    proposals: Sequence[Mapping[str, Any]],
    *,
    live_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    counts = {"proposed": 0, "ratified": 0, "rejected": 0}
    for row in proposals:
        status = str(row.get("status") or "")
        if status in counts:
            counts[status] += 1
    if counts["ratified"]:
        live_relations = {
            (
                str(row.get("type") or ""),
                str(row.get("src") or ""),
                str(row.get("dst") or ""),
            )
            for row in live_rows
        }
        ratified = [
            row for row in proposals if str(row.get("status")) == "ratified"
        ]
        materialized = sum(
            _proposal_mapping_edge(row) in live_relations for row in ratified
        )
        if materialized == len(ratified):
            state = "RATIFIED_AND_MATERIALIZED"
        elif materialized:
            state = "RATIFIED_PARTIALLY_MATERIALIZED"
        else:
            state = "RATIFIED_NOT_MATERIALIZED"
    elif counts["proposed"] and counts["rejected"]:
        state = "MIXED"
    elif counts["proposed"]:
        state = "PROPOSED"
    elif counts["rejected"]:
        state = "REJECTED"
    else:
        state = "NONE"
    return {
        "state": state,
        "proposal_ids": sorted(
            str(row.get("proposal_id") or "") for row in proposals
        ),
        "counts": counts,
    }


def compose_neighborhood(
    store_view: StoreView,
    *,
    node_id: str,
    asof: dt.date | str,
    knowledge_cutoff: dt.date | str | None = None,
    rights_resolver: Callable[[str], dict[str, Any] | None] = _default_rights_resolver,
) -> dict[str, Any]:
    """Return one exact-ID ontology neighborhood with graph/proposal truth separated."""
    exact_id = str(node_id or "").strip()
    if not exact_id:
        raise ValueError("node_id is required")
    asof_date = _parse_date(asof, "asof")
    cutoff_date = (
        _parse_date(knowledge_cutoff, "knowledge_cutoff")
        if knowledge_cutoff is not None
        else asof_date
    )

    nodes = _records(store_view.read_nodes())
    lifecycle_reader = getattr(store_view, "read_node_lifecycle", None)
    lifecycle = (
        _records(lifecycle_reader()) if callable(lifecycle_reader) else []
    )
    node_map = _nodes_as_known(
        nodes, lifecycle, asof=asof_date, knowledge_cutoff=cutoff_date
    )
    subject_row = node_map.get(exact_id)

    raw_edges = _records(store_view.read_edges())
    live_rows, future_beliefs = _collapse_relevant_edges(
        raw_edges,
        node_id=exact_id,
        asof=asof_date,
        knowledge_cutoff=cutoff_date,
    )
    if subject_row is None:
        live_rows = []
    relations = [
        _relation_projection(
            row,
            node_id=exact_id,
            node_map=node_map,
            rights_resolver=rights_resolver,
        )
        for row in live_rows
    ]
    relations.sort(
        key=lambda row: (
            row["type"],
            row["direction"],
            row["peer_node_id"],
            row["edge_id"],
        )
    )

    raw_proposals = _records(store_view.read_proposals())
    relevant_proposals: list[dict[str, Any]] = []
    for row in raw_proposals:
        if not _contains_exact(row.get("subject"), exact_id):
            continue
        known_row = _proposal_as_known(row, cutoff_date)
        if known_row is None:
            continue
        errors = probation.validate(row)
        if errors:
            raise ValueError(
                f"malformed relevant probation proposal {row.get('proposal_id')!r}: {errors}"
            )
        relevant_proposals.append(known_row)
    proposal_rows = [_proposal_projection(row) for row in relevant_proposals]
    proposal_rows.sort(key=lambda row: (row["created"], row["proposal_id"]))

    subject_kind = str(subject_row.get("kind") or "") if subject_row else ""
    if subject_kind == "theme":
        canonical_state = "SUBJECT_IS_CANONICAL"
        canonical_ids = [exact_id]
    elif subject_kind == "local_theme":
        canonical_ids = sorted(
            {
                str(row.get("dst"))
                for row in live_rows
                if str(row.get("type")) == "EXPRESSES"
                and str(row.get("src")) == exact_id
                and str(row.get("dst") or "").startswith("theme:")
            }
        )
        canonical_state = "MAPPED" if canonical_ids else "UNMAPPED"
    else:
        canonical_state = "NOT_APPLICABLE"
        canonical_ids = []

    canonical_mapping = {
        "state": canonical_state,
        "theme_node_ids": canonical_ids,
    }
    curation = _curation_summary(
        proposal_rows,
        live_rows=live_rows,
    )
    availability = (
        {"state": "OK", "reason": None}
        if subject_row is not None
        else {"state": "SUBJECT_NOT_FOUND", "reason": "exact node_id is absent"}
    )
    return {
        "schema": SCHEMA,
        "authority_ceiling": AUTHORITY_CEILING,
        "availability": availability,
        "node_id": exact_id,
        "asof": asof_date.isoformat(),
        "knowledge_cutoff": cutoff_date.isoformat(),
        "subject": _node_projection(subject_row) if subject_row else None,
        "relations": relations,
        "proposals": proposal_rows,
        "canonical_mapping": canonical_mapping,
        "curation": curation,
        "counts": {
            "relations": len(relations),
            "proposals": len(proposal_rows),
            "future_beliefs_excluded": future_beliefs,
        },
        "ordering": ORDERING,
        "limitations": [
            "exact node_id only; labels are never fuzzy-matched",
            "probation proposals have zero graph authority",
            "internal research projection; public display still requires the cited rights receipts",
            "no ranking, scoring, selection, trade, or ThemeState authority",
        ],
    }


def compose_proposal_review(
    store_view: StoreView,
    *,
    proposal_id: str,
    asof: str | dt.date,
    knowledge_cutoff: str | dt.date | None = None,
    rights_resolver: Callable[[str], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Inspect one existing proposal; never adjudicate it or manufacture an edge."""
    import re
    from types import SimpleNamespace

    if rights_resolver is None:
        rights_resolver = _default_rights_resolver
    if not isinstance(proposal_id, str) or not re.fullmatch(r"prop:[0-9a-f]{16}", proposal_id):
        raise ValueError("proposal_id must be an exact prop: identifier")
    asof_date = _parse_date(asof, "asof")
    cutoff = _parse_date(knowledge_cutoff, "knowledge_cutoff") if knowledge_cutoff is not None else asof_date
    result: dict[str, Any] = {
        "schema": "gmi.theme_ontology_proposal_review/v1",
        "authority_ceiling": AUTHORITY_CEILING,
        "proposal_id": proposal_id,
        "asof": asof_date.isoformat(),
        "knowledge_cutoff": cutoff.isoformat(),
        "availability": {"state": "PROPOSAL_NOT_FOUND", "reason": "exact proposal is unavailable at the cutoff"},
        "proposal": None,
        "relation": {"state": "NOT_EVALUATED", "type": None,
                     "source_node_id": None, "target_node_id": None, "edge_ids": []},
        "endpoints": [],
        "limitations": [
            "read-only evidence review; no adjudication or graph write",
            "proposal status and relation presence are independent facts",
            "overlap evidence is not proof of semantic expression",
            "endpoint rights are current registry receipts, not historical authorization",
            "unsupported subjects remain unresolved; no label inference",
        ],
    }
    proposals = _records(store_view.read_proposals())
    visible = []
    for row in proposals:
        if row.get("proposal_id") != proposal_id:
            continue
        known = _proposal_as_known(row, cutoff)
        if known is not None:
            visible.append((row, known))
    if len(visible) > 1:
        raise ValueError(f"duplicate visible proposal_id {proposal_id!r}")
    if not visible:
        return result
    original, known = visible[0]
    errors = probation.validate(original)
    if errors:
        raise ValueError(f"malformed proposal {proposal_id!r}: {errors}")
    result["availability"] = {"state": "OK", "reason": None}
    result["proposal"] = _proposal_projection(known)
    subject = known.get("subject")
    prefixes = {"basket": "basket:", "local_theme": "ltheme:", "canonical_theme": "theme:"}
    supported = (
        known.get("kind") == "mapping" and isinstance(subject, Mapping)
        and set(subject) in ({"basket", "local_theme"}, {"local_theme", "canonical_theme"})
        and all(isinstance(value, str) and value.startswith(prefixes[key])
                and len(value) > len(prefixes[key]) and not any(c.isspace() for c in value)
                for key, value in subject.items())
    )
    if not supported:
        result["relation"]["state"] = "UNSUPPORTED_SUBJECT"
        return result
    pair = _proposal_mapping_edge(known)
    assert pair is not None  # Exact supported shapes above; never a label resolver.
    relation_type, source_id, target_id = pair
    result["relation"].update(type=relation_type, source_node_id=source_id, target_node_id=target_id)
    # One request-local view of each owner table, not a new store or cache.
    nodes = _records(store_view.read_nodes())
    edges = _records(store_view.read_edges())
    lifecycle_reader = getattr(store_view, "read_node_lifecycle", None)
    lifecycle = _records(lifecycle_reader()) if callable(lifecycle_reader) else []
    snapshot = SimpleNamespace(read_nodes=lambda: nodes, read_edges=lambda: edges,
                              read_node_lifecycle=lambda: lifecycle, read_proposals=lambda: proposals)
    result["endpoints"] = [compose_neighborhood(snapshot, node_id=node_id,
        asof=asof_date, knowledge_cutoff=cutoff, rights_resolver=rights_resolver)
        for node_id in (source_id, target_id)]
    if any(endpoint["availability"]["state"] != "OK" for endpoint in result["endpoints"]):
        result["relation"]["state"] = "ENDPOINT_UNAVAILABLE"
        return result
    matches = sorted({row["edge_id"] for row in result["endpoints"][0]["relations"]
        if row["type"] == relation_type and row["direction"] == "OUTGOING"
        and row["peer_node_id"] == target_id})
    result["relation"]["edge_ids"] = matches
    result["relation"]["state"] = "RELATION_PRESENT" if matches else "RELATION_ABSENT"
    return result
