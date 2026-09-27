"""``semiconductor_theme_research.v1`` — the pure F04 composition module.

T07+T08 of operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001
(carrier PR #7870). This module is PURE IN-MEMORY COMPOSITION over
caller-supplied native objects: no I/O, no network, no store, no LLM call, no
scoring, no ranking by magnitude. Every emitted value is either an echo of an
input the caller passed in or a fiat classification over those inputs.

What that means concretely:

* configurations are never merged and stages are never inherited — a 12H
  reported shipment and a 16H sample stay two rows forever;
* mixed units (200mm vs 300mm, wafers vs area) are copied verbatim and NEVER
  converted — there is no formula anywhere in this file;
* a native output-based utilization is echoed and any shipment/capacity
  quotient is marked ``not_computed``;
* an integrated-assembly purchase total with contained configuration objects
  is refused (``purchase_total`` null, reason ``purchase_boundary``) — the
  same double-count law the assertion module enforces at mint time;
* one facility is counted once physically (capacity rows dedupe on
  (selector, stage)) while parent/NCI and captive/external economics stay
  separate rows;
* ordering is deterministic over source identities — (selector) /
  (source_business_label, company_node_id) / (curation_revision) — NEVER over
  any value or magnitude;
* source text inside assertions is DATA: instruction-like wording is copied
  verbatim as a string and authority stays structurally all-false;
* ``generation`` is a CONTENT fingerprint (sha256 over definition_version,
  rights_revision, the sorted revision tuple and the time-scoping query
  fields), not an access token and not a simultaneity claim; offset/limit are
  excluded so pagination never perturbs it.

The module never sees denied relationships: the caller filters by
authorization before building the :class:`OwnerBundle` and re-checks rights
immediately before emission (T09). Out-of-scope inputs are ignored, not
counted, and do not perturb the fingerprint.

Error protocol: :class:`ResearchRefusal` (a ``ValueError`` whose message is
exactly its snake_case ``.code``) for QUERY/GENERATION contract violations
only. Data availability NEVER raises — an invalid assertion is dropped into
``limitations`` as ``assertion_invalid:<index>``.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from engine.company_intelligence.guidance_history import (
    GuidanceHistoryError,
    assess_management_sequence,
)
from engine.theme_graph.curation_assertion import (
    CurationAssertionError,
    source_ref_for,
    validate_assertion,
)

#: Frozen response schema id.
SCHEMA_ID = "semiconductor_theme_research.v1"

#: Bump on any composition-definition change; participates in the generation fingerprint.
DEFINITION_VERSION = "2026-09-24.1"

#: Authority is structurally absent — the composition informs, it never
#: ranks/gates/sizes/originates/opens. Echoed verbatim into every response.
AUTHORITY: dict[str, bool] = {
    "can_rank": False,
    "can_gate": False,
    "can_size": False,
    "can_originate": False,
    "can_open_entry": False,
}

#: The five industrial views, always all present in a response.
VIEW_KEYS: tuple[str, ...] = (
    "composition", "manufacturing", "commercial", "capacity", "economics",
)

_EVIDENCE_SCHEMA_ID = "semiconductor_theme_research.evidence.v1"

#: Graph presentation caps (nodes/edges); capping mints ``graph_truncated``.
_MAX_GRAPH_NODES = 40
_MAX_GRAPH_EDGES = 80

#: Page bounds for the two paginated tables.
_MIN_LIMIT, _MAX_LIMIT = 1, 100

_STALE_PREFIX = "[stale interpretation] "


@dataclass(frozen=True)
class ResearchQuery:
    anchor_theme_id: str
    slice_key: Literal['hbm_packaging', 'sic_gan_specialty']
    view: Literal['composition', 'manufacturing', 'commercial', 'capacity', 'economics']
    time_mode: Literal['latest', 'source_history', 'system_replay']
    source_cutoff: str | None
    recorded_cutoff: str | None
    offset: int = 0
    limit: int = 50
    expected_generation: str | None = None


@dataclass(frozen=True)
class OwnerBundle:
    revision_tuple: tuple[tuple[str, str], ...]
    rights_revision: str
    assertions: tuple[Mapping[str, Any], ...]
    identity_results: tuple[Mapping[str, Any], ...]
    event_workspaces: tuple[Mapping[str, Any], ...]
    financial_packets: tuple[Mapping[str, Any], ...]
    interpretation_blocks: tuple[Mapping[str, Any], ...]
    native_refs: tuple[Mapping[str, Any], ...]
    omissions: tuple[str, ...]


class ResearchRefusal(ValueError):
    """A query/generation contract violation. ``str(exc)`` is exactly ``.code``."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------------------
# Canonical JSON / time parsing
# ---------------------------------------------------------------------------

def _canonical_text(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _is_instant(value: str) -> bool:
    return "T" in value


def _parse_clock(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _parse_day(value: str):
    return _parse_clock(value).date() if _is_instant(value) else datetime.strptime(value, "%Y-%m-%d").date()


def _le(value: str, cutoff: str) -> bool:
    """``value <= cutoff`` for date-or-datetime strings, WITHOUT synthesizing a
    time: when either side is date-only the comparison is on calendar days
    (inclusive). Two instants compare as instants."""
    if not _is_instant(value) and not _is_instant(cutoff):
        return _parse_day(value) <= _parse_day(cutoff)
    if not _is_instant(value):          # date vs instant: compare days
        return _parse_day(value) <= _parse_clock(cutoff).date()
    if not _is_instant(cutoff):         # instant vs date: compare days
        return _parse_clock(value).date() <= _parse_day(cutoff)
    return _parse_clock(value) <= _parse_clock(cutoff)


# ---------------------------------------------------------------------------
# Query contract + generation fingerprint
# ---------------------------------------------------------------------------

def _validate_query(query: ResearchQuery) -> None:
    if not isinstance(query.limit, int) or isinstance(query.limit, bool) \
            or not _MIN_LIMIT <= query.limit <= _MAX_LIMIT:
        raise ResearchRefusal("limit_out_of_range")
    if not isinstance(query.offset, int) or isinstance(query.offset, bool) or query.offset < 0:
        raise ResearchRefusal("offset_negative")
    if query.offset > 0 and query.expected_generation is None:
        raise ResearchRefusal("expected_generation_required")
    if query.time_mode == "system_replay" and (
            query.source_cutoff is None or query.recorded_cutoff is None):
        raise ResearchRefusal("replay_cutoffs_required")


def _generation(query: ResearchQuery, bundle: OwnerBundle) -> str:
    payload = {
        "definition_version": DEFINITION_VERSION,
        "rights_revision": bundle.rights_revision,
        "revision_tuple": sorted(list(pair) for pair in bundle.revision_tuple),
        "slice_key": query.slice_key,
        "view": query.view,
        "time_mode": query.time_mode,
        "source_cutoff": query.source_cutoff,
        "recorded_cutoff": query.recorded_cutoff,
        "anchor_theme_id": query.anchor_theme_id,
    }
    digest = hashlib.sha256(_canonical_text(payload).encode("utf-8")).hexdigest()[:32]
    return "gen_" + digest


# ---------------------------------------------------------------------------
# Selection — validate, scope, time-filter
# ---------------------------------------------------------------------------

def _passes_time_mode(assertion: Mapping[str, Any], query: ResearchQuery,
                      limitations: set[str]) -> bool:
    source = assertion["source"]

    if query.time_mode == "latest":
        return True

    if query.time_mode == "source_history":
        if query.source_cutoff is None:
            return True  # no cutoff given: history is the whole selection
        comparable = False
        published = source.get("published_at")
        if published is not None:
            comparable = True
            if _le(published, query.source_cutoff):
                return True
        available = source.get("available_at")
        if isinstance(available, str) and available != "unknown":
            comparable = True
            if _le(available, query.source_cutoff):
                return True
        if not comparable:
            limitations.add("undatable_excluded")
        return False

    # system_replay: known availability AND system recording, both inside cutoffs
    available = source.get("available_at")
    if not isinstance(available, str) or available == "unknown":
        limitations.add("availability_unknown_excluded")
        return False
    if not _le(available, query.source_cutoff):
        return False
    if not _le(source["retained_at"], query.recorded_cutoff):
        return False
    published = source.get("published_at")
    if published is not None:
        grain = source.get("published_at_grain")
        if grain == "date":
            # never synthesize midnight: a date-only publication on the cutoff
            # day cannot be placed before or after the cutoff instant
            if _is_instant(query.source_cutoff) \
                    and _parse_day(published) == _parse_clock(query.source_cutoff).date():
                limitations.add("same_day_grain_ambiguous")
                return False
        if not _le(published, query.source_cutoff):
            return False
    return True


def _is_retrospective(assertion: Mapping[str, Any], query: ResearchQuery) -> bool:
    """source_history only: an archival source recorded later than its
    publication is allowed there and is labelled retrospective."""
    if query.time_mode != "source_history":
        return False
    source = assertion["source"]
    published = source.get("published_at")
    if published is None:
        return False
    return _parse_day(source["retained_at"]) > _parse_day(published)


class _Selection:
    """The authorized, time-scoped, validated selection + its caveats."""

    def __init__(self, query: ResearchQuery, bundle: OwnerBundle):
        self.query = query
        self.bundle = bundle
        self.generation = _generation(query, bundle)
        self.limitations: set[str] = set()
        self.assertions: list[dict[str, Any]] = []
        for index, item in enumerate(bundle.assertions):
            try:
                assertion = validate_assertion(item)
            except CurationAssertionError:
                self.limitations.add(f"assertion_invalid:{index}")
                continue
            if assertion.get("scope", {}).get("canonical_theme_id") != query.anchor_theme_id:
                continue  # out of scope: ignored, not counted, never fingerprint-relevant
            if not _passes_time_mode(assertion, query, self.limitations):
                continue
            self.assertions.append(assertion)
        self.assertions.sort(key=lambda a: a["curation_revision"])
        for name in bundle.omissions:
            self.limitations.add(f"omitted:{name}")

    # -- replay-scoped native inputs (events, packets, interpretations) ------

    def event_workspaces(self) -> list[dict[str, Any]]:
        chosen = []
        for workspace in self.bundle.event_workspaces:
            lifecycle = workspace.get("lifecycle") or {}
            if self.query.time_mode == "system_replay":
                available = lifecycle.get("source_available_at")
                if not isinstance(available, str) or available == "unknown":
                    self.limitations.add("availability_unknown_excluded")
                    continue
                if not _le(available, self.query.source_cutoff):
                    continue
                recorded = lifecycle.get("recorded_at")
                if not isinstance(recorded, str) or not _le(recorded, self.query.recorded_cutoff):
                    continue
            chosen.append(dict(workspace))
        chosen.sort(key=lambda w: w.get("event_id", ""))
        return chosen

    def financial_packets(self) -> list[dict[str, Any]]:
        chosen = []
        for packet in self.bundle.financial_packets:
            if self.query.time_mode == "system_replay":
                recorded = packet.get("recorded_at")
                if not isinstance(recorded, str) or not _le(recorded, self.query.recorded_cutoff):
                    continue
            chosen.append(dict(packet))
        chosen.sort(key=lambda p: (p.get("recorded_at") or "", str(p.get("entity") or "")))
        return chosen

    def interpretation_blocks(self) -> list[dict[str, Any]]:
        chosen = []
        for block in self.bundle.interpretation_blocks:
            if self.query.time_mode == "system_replay":
                reviewed = block.get("reviewed_at")
                if not isinstance(reviewed, str) or not _le(reviewed, self.query.recorded_cutoff):
                    continue
            chosen.append(dict(block))
        chosen.sort(key=lambda b: b.get("interpretation_id", ""))
        return chosen

    # -- identity ------------------------------------------------------------

    def identity_index(self) -> dict[str, dict[str, Any]]:
        """source_business_label -> state row. A mapping learned after the
        replay's recorded_cutoff never resolves retroactively; the 1970-01-01
        listing epoch is never consulted as listing evidence — the mapping
        timestamp is the only gate."""
        index: dict[str, dict[str, Any]] = {}
        for result in self.bundle.identity_results:
            label = result.get("source_business_label")
            if not isinstance(label, str) or not label:
                continue
            node_id = result.get("company_node_id")
            learned = result.get("mapping_learned_at")
            not_yet = (
                self.query.time_mode == "system_replay"
                and isinstance(learned, str)
                and self.query.recorded_cutoff is not None
                and not _le(learned, self.query.recorded_cutoff)
            )
            if not_yet:
                state = {"company_node_id": None, "reason": "identity_not_yet_learned"}
            elif result.get("resolution") == "RESOLVED" and isinstance(node_id, str) and node_id:
                state = {"company_node_id": node_id, "reason": None}
            else:
                state = {"company_node_id": None, "reason": "identity_unresolved"}
            index[label] = state
        return index

    def node_for(self, identity: dict[str, Any], label: Any) -> str | None:
        if not isinstance(label, str):
            return None
        return identity.get(label, {"company_node_id": None})["company_node_id"]


# ---------------------------------------------------------------------------
# Industrial rows / views
# ---------------------------------------------------------------------------

def _context_of(assertion: Mapping[str, Any]) -> dict[str, Any]:
    context = assertion.get("industrial_context")
    return dict(context) if isinstance(context, Mapping) else {}


def _views_of(assertion: Mapping[str, Any]) -> set[str]:
    predicate = assertion.get("predicate")
    context = _context_of(assertion)
    relation = context.get("relation") or {}
    relation_kind = relation.get("kind") if isinstance(relation, Mapping) else None
    views: set[str] = set()
    if relation_kind in ("contains", "requires_process", "catalog_compatible") \
            or predicate == "DOCUMENTED_PRODUCT_INCLUSION":
        views.add("composition")
    if predicate in ("REPORTED_DEPLOYMENT", "DEPLOYMENT_TARGET"):
        views.add("manufacturing")
    if relation_kind in ("documented_supply", "announced_agreement", "ownership") \
            or predicate == "ANNOUNCED_DEVELOPMENT_AGREEMENT":
        views.add("commercial")
    # financial/ownership measures carry a measure_scope too, but they are
    # economics rows — the physical capacity view must not inherit them
    if (context.get("measure_scope") is not None
            and predicate not in ("REPORTED_FINANCIAL_MEASURE", "OWNERSHIP_EVENT")) \
            or predicate == "REPORTED_OPERATING_MEASURE":
        views.add("capacity")
    if predicate in ("REPORTED_FINANCIAL_MEASURE", "OWNERSHIP_EVENT"):
        views.add("economics")
    return views


def _industrial_row(assertion: Mapping[str, Any], selection: _Selection,
                    identity: dict[str, Any]) -> dict[str, Any]:
    subject = assertion["subject"]
    context = _context_of(assertion)
    objects = context.get("local_objects") or []
    primary = objects[0] if objects else None
    selectors = {o.get("selector") for o in objects if isinstance(o, Mapping)}
    relation = context.get("relation") if isinstance(context.get("relation"), Mapping) else None
    measure_scope = context.get("measure_scope") if isinstance(context.get("measure_scope"), Mapping) else None
    stage = context.get("stage")

    business = subject.get("source_business_label")
    configuration = None
    for candidate in (
        primary.get("configuration") if primary else None,
        subject.get("configuration"),
        assertion["object"].get("configuration"),
    ):
        if candidate is not None:
            configuration = candidate
            break

    # purchase total: refused when an integrated_assembly measure carries
    # contained configuration objects (the double-count shape the assertion
    # module refuses at mint time; here the refusal is on the TOTAL, not the row)
    purchase_total = None
    purchase_total_reason = None
    if measure_scope is not None:
        value_basis = str(measure_scope.get("value_basis") or "")
        if "purchase" in value_basis:
            contained = any(isinstance(o, Mapping) and o.get("kind") == "configuration" for o in objects)
            if measure_scope.get("purchase_boundary") == "integrated_assembly" and contained:
                purchase_total_reason = "purchase_boundary"
            else:
                purchase_total = assertion["observation"].get("value")

    # utilization: the native output-based figure verbatim; a quotient is
    # never computed here — there is no formula in this module
    native_utilization, native_unit = None, None
    if measure_scope is not None and "utilization" in str(measure_scope.get("value_basis") or ""):
        native_utilization = assertion["observation"].get("value")
        native_unit = assertion["observation"].get("unit")

    return {
        "assertion_ref": source_ref_for(assertion),
        "curation_revision": assertion["curation_revision"],
        "source_business_label": business,
        "source_product_label": subject.get("source_product_label"),
        "selector": primary.get("selector") if primary else None,
        "object_selector": relation.get("dst_selector")
        if relation and relation.get("dst_selector") in selectors else None,
        "kind": primary.get("kind") if primary else None,
        "model": primary.get("model") if primary else None,
        "configuration": configuration,
        "stage": stage,
        "stage_source_language": context.get("stage_source_language"),
        "relation_kind": relation.get("kind") if relation else None,
        "predicate": assertion["predicate"],
        "statement_mode": assertion["statement_mode"],
        "retrospective": _is_retrospective(assertion, selection.query),
        "observation": dict(assertion["observation"]),
        "measure_scope": dict(measure_scope) if measure_scope is not None else None,
        "purchase_total": purchase_total,
        "purchase_total_reason": purchase_total_reason,
        "utilization": {
            "native_value": native_utilization,
            "native_unit": native_unit,
            "quotient_value": None,
            "quotient_reason": "not_computed",
        },
        "company_node_id": selection.node_for(identity, business),
    }


_ROW_ORDER = ("selector", "source_business_label", "configuration", "stage", "curation_revision")


def _row_sort_key(row: dict[str, Any]) -> tuple:
    return tuple((row.get(key) or "") if isinstance(row.get(key), str) else "" for key in _ROW_ORDER)


# Row fields that say WHO asserted a capacity measurement (and how that owner
# phrased it) rather than WHAT was measured. Two rows equal in every other
# field are one physical measurement restated by two owners (the JV shape);
# a difference anywhere else — configuration, model, kind, product label,
# predicate, statement mode, observation, measure scope, relation, the
# normalized stage, a refusal — is a second measurement and is never
# collapsed. `stage_source_language` is the owner's verbatim phrasing of the
# stage; the normalized `stage` stays in the fingerprint.
_CAPACITY_OWNER_FIELDS = frozenset({
    "assertion_ref", "curation_revision", "source_business_label", "company_node_id",
    "retrospective", "stage_source_language",
})


def _physical_fingerprint(row: Mapping[str, Any]) -> str:
    return json.dumps({k: v for k, v in row.items() if k not in _CAPACITY_OWNER_FIELDS},
                      sort_keys=True, default=str)


def _view_graph(assertions: list[Mapping[str, Any]]) -> tuple[dict[str, Any], bool]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for assertion in assertions:  # already sorted by curation_revision
        for obj in _context_of(assertion).get("local_objects") or []:
            if isinstance(obj, Mapping) and obj.get("selector"):
                nodes.setdefault(obj["selector"], {
                    "id": obj["selector"],
                    "label": obj.get("source_label") or obj["selector"],
                    "kind": obj.get("kind") or "object",
                })
    for assertion in assertions:
        relation = _context_of(assertion).get("relation")
        if not isinstance(relation, Mapping):
            continue
        src, dst = relation.get("src_selector"), relation.get("dst_selector")
        if src in nodes and dst in nodes:
            edges[(src, dst, relation.get("kind"))] = {
                "src": src, "dst": dst, "kind": relation.get("kind"), "width": None,
            }
    ordered_nodes = [nodes[key] for key in sorted(nodes)]
    ordered_edges = [edges[key] for key in sorted(edges)]
    truncated = False
    if len(ordered_nodes) > _MAX_GRAPH_NODES:
        ordered_nodes = ordered_nodes[:_MAX_GRAPH_NODES]
        truncated = True
    allowed = {node["id"] for node in ordered_nodes}
    ordered_edges = [e for e in ordered_edges if e["src"] in allowed and e["dst"] in allowed]
    if len(ordered_edges) > _MAX_GRAPH_EDGES:
        ordered_edges = ordered_edges[:_MAX_GRAPH_EDGES]
        truncated = True
    return {"nodes": ordered_nodes, "edges": ordered_edges}, truncated


def _build_views(selection: _Selection, identity: dict[str, Any]) -> dict[str, Any]:
    views: dict[str, Any] = {}
    selected_revisions = [a["curation_revision"] for a in selection.assertions]
    for key in VIEW_KEYS:
        members = [a for a in selection.assertions if key in _views_of(a)]
        rows = sorted((_industrial_row(a, selection, identity) for a in members), key=_row_sort_key)
        view_limitations: list[str] = []
        members_refs = sorted(a["curation_revision"] for a in members)

        if key == "capacity" and rows:
            # One facility counted once PHYSICALLY: a second assertion that
            # restates the SAME physical measurement of the same facility+stage
            # — equal in every row field except who asserts it (the JV /
            # multi-owner shape) — is counted once. A row that differs in WHAT
            # is measured or how (12H vs 16H, another model, unit, basis or a
            # conflicting figure) is NEVER deleted or chosen by hash: two
            # measures are two rows, and the view says so with
            # `multiple_measures_same_facility`.
            seen: dict[tuple, set[str]] = {}
            deduped: list[dict[str, Any]] = []
            for row in rows:  # revision-sorted, so the order is deterministic
                selector = row.get("selector")
                if selector is None:
                    deduped.append(row)
                    continue
                dedupe_key = (selector, row.get("stage"))
                fingerprint = _physical_fingerprint(row)
                fingerprints = seen.setdefault(dedupe_key, set())
                if not fingerprints:
                    fingerprints.add(fingerprint)
                    deduped.append(row)
                    continue
                if fingerprint in fingerprints:
                    view_limitations.append("facility_counted_once_multi_owner")
                    continue
                fingerprints.add(fingerprint)
                view_limitations.append("multiple_measures_same_facility")
                deduped.append(row)
            rows = deduped

        if not selected_revisions:
            status, reason = "unavailable", "no_selected_assertions"
        elif not rows:
            status, reason = "unavailable", "no_rows_for_view"
        else:
            status, reason = ("degraded", sorted(view_limitations)[0]) if view_limitations else ("ready", None)

        graph, truncated = _view_graph(members)
        view: dict[str, Any] = {
            "status": status,
            "input_refs": members_refs,
            "rows": rows,
            "graph": graph,
            "limitations": sorted(set(view_limitations)),
        }
        if reason:
            view["reason"] = reason

        if key == "capacity":
            # a summed capacity total is NEVER minted; scoped constructions
            # (CoWoS-S/R/L, 12H/16H…) make any total a mixed-scope hazard
            distinct = {row.get("configuration") for row in rows}
            view["total"] = {
                "value": None,
                "reason": "mixed_construction_scope" if len(distinct) > 1 else None,
            }
            if len(distinct) > 1:
                view["limitations"] = sorted(set(view["limitations"]) | {"mixed_construction_scope"})
                if view["status"] == "ready":
                    view["status"], view["reason"] = "degraded", "mixed_construction_scope"

        if truncated:
            view["limitations"] = sorted(set(view["limitations"]) | {"graph_truncated"})
            selection.limitations.add("graph_truncated")
            if view["status"] == "ready":
                view["status"], view["reason"] = "degraded", "graph_truncated"

        views[key] = view
    return views


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

def _role_for(assertion: Mapping[str, Any], business: str) -> str:
    objects = _context_of(assertion).get("local_objects") or []
    for obj in objects:
        if isinstance(obj, Mapping) and business in (obj.get("manufacturer"), obj.get("source_label")):
            return obj.get("kind") or "object"
    return "subject" if assertion["subject"].get("source_business_label") == business else "mentioned"


def _build_companies(selection: _Selection, identity: dict[str, Any]) -> dict[str, Any]:
    roles: dict[str, list[dict[str, Any]]] = {}
    for assertion in selection.assertions:  # revision-sorted
        subject = assertion["subject"]
        businesses = {subject.get("source_business_label")}
        for obj in _context_of(assertion).get("local_objects") or []:
            if isinstance(obj, Mapping) and obj.get("manufacturer"):
                businesses.add(obj.get("manufacturer"))
        for business in sorted(b for b in businesses if isinstance(b, str) and b):
            roles.setdefault(business, []).append({
                "role": _role_for(assertion, business),
                "relation_kind": (lambda r: r.get("kind") if isinstance(r, Mapping) else None)(
                    _context_of(assertion).get("relation")),
                "stage": _context_of(assertion).get("stage"),
                "assertion_ref": source_ref_for(assertion),
            })
    rows = []
    for business in sorted(roles):
        state = identity.get(business, {"company_node_id": None, "reason": "identity_unresolved"})
        rows.append({
            "source_business_label": business,
            "company_node_id": state["company_node_id"],
            "navigation": {
                "status": "ready" if state["company_node_id"] is not None else "unavailable",
                "href": None,  # T10 owns hrefs; the composition emits only the native id
                "reason": state["reason"] if state["company_node_id"] is None else None,
            },
            "roles": sorted(roles[business], key=lambda r: (
                r["role"], r["relation_kind"] or "", r["stage"] or "", r["assertion_ref"])),
        })
    rows.sort(key=lambda r: (r["source_business_label"], r["company_node_id"] or ""))
    if not rows:
        section = {"status": "unavailable", "reason": "no_companies", "input_refs": [], "rows": []}
    elif any(row["navigation"]["status"] != "ready" for row in rows):
        section = {"status": "degraded", "reason": "identity_incomplete",
                   "input_refs": sorted(a["curation_revision"] for a in selection.assertions),
                   "rows": rows}
    else:
        section = {"status": "ready",
                   "input_refs": sorted(a["curation_revision"] for a in selection.assertions),
                   "rows": rows}
    return section


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _fact_text(assertion: Mapping[str, Any]) -> str:
    subject = assertion["subject"]
    context = _context_of(assertion)
    parts = [
        subject.get("source_business_label"),
        subject.get("source_product_label") or assertion["object"].get("source_product_label"),
        context.get("stage") or assertion.get("predicate"),
    ]
    return " — ".join(part for part in parts if part)


def _interpretation_items(blocks: list[dict[str, Any]], selected_revisions: set[str],
                          field: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in blocks:
        text = block.get(field)
        if not text:
            continue
        inputs = list(block.get("input_revisions") or [])
        stale = block.get("freshness") != "current" or any(rev not in selected_revisions for rev in inputs)
        item = {
            "text": (_STALE_PREFIX + text) if stale else str(text),
            "label": "interpretation",
            "input_refs": sorted(inputs),
        }
        if stale:
            item["stale"] = True
        items.append(item)
    items.sort(key=lambda i: (tuple(i["input_refs"]), i["text"]))
    return items


def _build_summary(selection: _Selection) -> tuple[dict[str, Any], bool]:
    selected_revisions = {a["curation_revision"] for a in selection.assertions}
    what_changed, next_evidence = [], []
    for assertion in selection.assertions:  # revision-sorted
        mode = assertion.get("statement_mode")
        if mode == "REPORTED_FACT":
            what_changed.append({
                "text": _fact_text(assertion),
                "label": "fact",
                "input_refs": [assertion["curation_revision"]],
            })
        elif mode == "FORWARD_TARGET" or assertion.get("predicate") == "DEPLOYMENT_TARGET":
            next_evidence.append({
                "text": _fact_text(assertion),
                "label": "target",
                "input_refs": [assertion["curation_revision"]],
            })
    blocks = selection.interpretation_blocks()
    why_it_matters = _interpretation_items(blocks, selected_revisions, "mechanism")
    offsets = _interpretation_items(blocks, selected_revisions, "offset")
    watchers = _interpretation_items(blocks, selected_revisions, "missing_measurement")
    if not watchers:
        watchers = _interpretation_items(blocks, selected_revisions, "falsifier")
    next_evidence.extend(watchers)
    next_evidence.sort(key=lambda i: (i["label"], tuple(i["input_refs"]), i["text"]))
    what_changed.sort(key=lambda i: (tuple(i["input_refs"]), i["text"]))

    stale_present = any(item.get("stale") for item in why_it_matters)
    if stale_present:
        selection.limitations.add("interpretation_stale")
    dropped = any(limitation.startswith("assertion_invalid:") for limitation in selection.limitations) \
        or any(limitation.startswith("omitted:") for limitation in selection.limitations)
    if not selection.assertions:
        status, reason = "unavailable", "no_selected_assertions"
    elif dropped:
        status, reason = "degraded", "inputs_dropped"
    elif stale_present:
        status, reason = "degraded", "interpretation_stale"
    else:
        status, reason = "ready", None
    summary = {
        "status": status,
        "input_refs": sorted(selected_revisions),
        "what_changed": what_changed,
        "why_it_matters": why_it_matters,
        "offset": offsets,
        "next_evidence": next_evidence,
    }
    if reason:
        summary["reason"] = reason
    return summary, stale_present


# ---------------------------------------------------------------------------
# Economics — the management sequence triple
# ---------------------------------------------------------------------------

def _fiscal_key(period: Any) -> tuple[int, int]:
    text = str(period or "")
    year, _, quarter = text.partition("Q")
    try:
        return (int(year), int(quarter))
    except ValueError:
        return (0, 0)


def _company_key(workspace: Mapping[str, Any]) -> str:
    return str(workspace.get("company_node_id") or f"cik:{(workspace.get('cik') or '')}")


def _receipts_bound_to(derivations: Mapping[str, Any], consumed: set[str]) -> bool:
    """True when every derivation receipt names only inputs among *consumed*
    (the event ids of the triple being explained). A receipt without inputs,
    or one that cites another period's event, does not bind to this triple."""
    for derivation in derivations.values():
        if not isinstance(derivation, Mapping):
            return False
        inputs = derivation.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            return False
        if not set(str(i) for i in inputs) <= consumed:
            return False
    return True


def _build_economics(selection: _Selection) -> dict[str, Any]:
    workspaces = selection.event_workspaces()
    packets = selection.financial_packets()
    by_company: dict[str, list[dict[str, Any]]] = {}
    for workspace in workspaces:
        by_company.setdefault(_company_key(workspace), []).append(workspace)

    best: tuple[tuple[int, int], str, dict[str, Any], dict[str, Any], dict[str, Any],
                list[str], Mapping[str, Any] | None, bool] | None = None
    for company in sorted(by_company):
        ordered = sorted(by_company[company], key=lambda w: _fiscal_key(
            f"{(w.get('fiscal_period') or {}).get('year')}Q{(w.get('fiscal_period') or {}).get('quarter')}"))
        for index, workspace in enumerate(ordered):
            for reported in workspace.get("reported") or []:
                actual_key = _fiscal_key(reported.get("fiscal_period"))
                if actual_key == (0, 0):
                    continue
                prior = None
                for earlier in ordered[:index]:
                    for guidance in earlier.get("guidance") or []:
                        if _fiscal_key(guidance.get("horizon")) == actual_key:
                            prior = guidance  # the most recent earlier release wins
                if prior is None:
                    continue
                new_outlook = None
                for guidance in workspace.get("guidance") or []:
                    if _fiscal_key(guidance.get("horizon")) > actual_key:
                        new_outlook = guidance
                if new_outlook is None:
                    continue
                actual = {
                    "metric": reported.get("metric"),
                    "value": reported.get("value"),
                    "unit": reported.get("unit"),
                    "fiscal_period": reported.get("fiscal_period"),
                    "source_span": {"event_id": workspace.get("event_id")},
                }
                for optional in ("basis", "currency", "perimeter", "definition"):
                    if optional in reported:
                        actual[optional] = reported[optional]
                consumed = sorted({w.get("event_id", "") for w in ordered})
                # A financial packet is attached ONLY when it is `ready`, is
                # for this company, and every derivation receipt's inputs are
                # among the event ids this triple consumed — a stale,
                # unavailable or foreign-period packet is not evidence about
                # this triple, and its figure must never be displayed as one.
                # Two DIFFERENT bound packets are a conflict: neither is
                # attached (no figure is ever chosen by list order) and the
                # response says `competing_financial_packets`; byte-identical
                # restatements of one packet are one packet.
                bound: dict[str, Mapping[str, Any]] = {}
                for packet in packets:
                    entity = packet.get("entity") or {}
                    if entity.get("cik") != workspace.get("cik"):
                        continue
                    if str(packet.get("status") or "") != "ready":
                        continue
                    candidate_derivations = packet.get("derivations")
                    if not (isinstance(candidate_derivations, Mapping) and candidate_derivations):
                        continue
                    if not _receipts_bound_to(candidate_derivations, set(consumed)):
                        continue
                    bound.setdefault(json.dumps(candidate_derivations, sort_keys=True, default=str),
                                     candidate_derivations)
                derivations = next(iter(bound.values())) if len(bound) == 1 else None
                candidate = (actual_key, company, prior, actual, new_outlook, consumed, derivations,
                             len(bound) > 1)
                if best is None or candidate[0] > best[0]:
                    best = candidate

    if best is None:
        selection.limitations.add("witness_economics_missing")
        return {
            "status": "unavailable",
            "reason": "management_sequence_missing",
            "input_refs": [],
            "management": None,
            "witness_gate": "missing",
        }

    _, _, prior, actual, new_outlook, consumed, derivations, competing = best
    if competing:
        selection.limitations.add("competing_financial_packets")
    try:
        management = assess_management_sequence(
            prior, actual, new_outlook,
            native_derivations=derivations if derivations else None,
        )
    except GuidanceHistoryError:
        selection.limitations.add("witness_economics_missing")
        return {
            "status": "unavailable",
            "reason": "management_sequence_invalid",
            "input_refs": consumed,
            "management": None,
            "witness_gate": "missing",
        }
    return {
        "status": "ready",
        "input_refs": consumed,
        "management": management,
        "witness_gate": "positive",
    }


def _build_expectations(economics: dict[str, Any]) -> dict[str, Any]:
    if economics["management"] is not None:
        management = {
            "status": "ready",
            "input_refs": list(economics["input_refs"]),
            "roles": economics["management"]["roles"],
        }
    else:
        management = {
            "status": "unavailable",
            "reason": "management_sequence_missing",
            "input_refs": [],
            "roles": None,
        }
    return {
        "management": management,
        "external_consensus": {"status": "unavailable", "reason": "no_external_consensus"},
        "house_forecast": {"status": "unavailable", "reason": "not_authorized"},
        "market_incorporation": {"status": "unavailable", "reason": "not_authorized"},
    }


# ---------------------------------------------------------------------------
# Native subjects / evidence refs
# ---------------------------------------------------------------------------

def _build_native_subjects(selection: _Selection, identity: dict[str, Any]) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for assertion in selection.assertions:
        for obj in _context_of(assertion).get("local_objects") or []:
            if not (isinstance(obj, Mapping) and obj.get("selector")):
                continue
            key = (obj["selector"], obj.get("kind") or "", obj.get("source_label") or "")
            if key in rows:
                continue
            rows[key] = {
                "selector": obj["selector"],
                "kind": obj.get("kind") or "object",
                "source_label": obj.get("source_label") or obj["selector"],
                "company_node_id": selection.node_for(identity, obj.get("manufacturer")),
            }
    return [rows[key] for key in sorted(rows)]


def _build_evidence_refs(selection: _Selection) -> list[dict[str, Any]]:
    refs = [
        {
            "assertion_ref": source_ref_for(assertion),
            "curation_revision": assertion["curation_revision"],
            "kind": "assertion",
        }
        for assertion in selection.assertions
    ]
    refs.extend(
        {
            "owner_store": native.get("owner_store"),
            "native_identity": copy.deepcopy(native.get("native_identity")),
            "reference_id": native.get("reference_id"),
            "kind": "native",
        }
        for native in sorted(selection.bundle.native_refs,
                             key=lambda n: str(n.get("reference_id") or ""))
    )
    return refs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _compose(query: ResearchQuery, bundle: OwnerBundle) -> dict[str, Any]:
    _validate_query(query)
    generation = _generation(query, bundle)
    if query.expected_generation is not None and query.expected_generation != generation:
        raise ResearchRefusal("generation_changed")

    selection = _Selection(query, bundle)
    identity = selection.identity_index()
    views = _build_views(selection, identity)
    economics = _build_economics(selection)
    summary, _ = _build_summary(selection)

    start, end = query.offset, query.offset + query.limit
    companies = _build_companies(selection, identity)
    companies["rows"] = companies["rows"][start:end]
    for view in views.values():
        view["rows"] = view["rows"][start:end]

    return {
        "schema": SCHEMA_ID,
        "definition_version": DEFINITION_VERSION,
        "generation": generation,
        "request": {
            "anchor_theme_id": query.anchor_theme_id,
            "slice_key": query.slice_key,
            "view": query.view,
            "time_mode": query.time_mode,
            "source_cutoff": query.source_cutoff,
            "recorded_cutoff": query.recorded_cutoff,
            "offset": query.offset,
            "limit": query.limit,
            "expected_generation": query.expected_generation,
        },
        "native_subjects": _build_native_subjects(selection, identity),
        "summary": summary,
        "companies": companies,
        "industrial_views": views,
        "economics": economics,
        "expectations": _build_expectations(economics),
        "evidence_refs": _build_evidence_refs(selection),
        "authorized_coverage": {
            "status": "ready" if selection.assertions else "unavailable",
            "input_refs": sorted(a["curation_revision"] for a in selection.assertions),
            "selected": len(selection.assertions),
            "industry_total": None,
            "note": "counts only what this principal may know exists",
        },
        "limitations": sorted(selection.limitations),
        "authority": dict(AUTHORITY),
    }


def compose_semiconductor_research(query: ResearchQuery, bundle: OwnerBundle) -> dict[str, Any]:
    """Compose the closed bounded snapshot (T08). Pure; raises
    :class:`ResearchRefusal` only for query/generation contract violations."""
    return _compose(query, bundle)


def select_industrial_sections(query: ResearchQuery, bundle: OwnerBundle) -> dict[str, Any]:
    """The industrial projection (T07): native subjects, the five industrial
    views, and the caveats — everything in the snapshot except the economics
    pane, the companies pane and the expectations pane."""
    response = _compose(query, bundle)
    return {
        "schema": response["schema"],
        "definition_version": response["definition_version"],
        "generation": response["generation"],
        "request": response["request"],
        "native_subjects": response["native_subjects"],
        "industrial_views": response["industrial_views"],
        "limitations": response["limitations"],
        "authority": response["authority"],
    }


def select_authorized_evidence(query: ResearchQuery, bundle: OwnerBundle,
                               assertion_ref: str) -> dict[str, Any]:
    """Return one authorized assertion as its own evidence object. Unknown and
    not-selected refs share the single code ``not_available`` — no existence
    disclosure."""
    _validate_query(query)
    generation = _generation(query, bundle)
    if query.expected_generation != generation:
        raise ResearchRefusal("generation_changed")
    selection = _Selection(query, bundle)
    for assertion in selection.assertions:
        if source_ref_for(assertion) == assertion_ref:
            source = assertion["source"]
            return {
                "schema": _EVIDENCE_SCHEMA_ID,
                "generation": generation,
                "assertion_ref": assertion_ref,
                "assertion": copy.deepcopy(assertion),
                "source": {
                    "publisher": source.get("publisher"),
                    "source_uri": source.get("source_uri"),
                    "locator": source.get("locator"),
                    "published_at": source.get("published_at"),
                    "published_at_grain": source.get("published_at_grain"),
                    "available_at": source.get("available_at"),
                },
                "lineage": copy.deepcopy(_context_of(assertion).get("lineage_refs") or []),
                "limitations": sorted(selection.limitations),
                "authority": dict(AUTHORITY),
            }
    raise ResearchRefusal("not_available")
