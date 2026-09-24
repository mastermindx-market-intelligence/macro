"""engine/market_ontology/robotics_theme_research.py — the pure Robotics
theme-research response composer (R2).

Operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001, carrier #7908.
Consumes the shared assertion contract and composition types from #7870
(c6c67c87) and answers on the SAME envelope as
``semiconductor_theme_research.v1`` so one generic route and client serve both
verticals.

Laws this module is bound to (RBV-01..RBV-27 acceptance cases):

- PURE composition. No I/O, no network, no store, no LLM. Everything is
  computed in memory from the caller-supplied decoded assertions.
- The composer never ranks, scores, gates, sizes, originates or opens
  entries; ``AUTHORITY`` is structurally all-false and no row carries a
  magnitude-ordered position.
- Echo, never derive: predicate, statement mode, configuration scope,
  quantity basis, clocks, review state, correction lineage and limitations
  are carried verbatim. A catalog capability never becomes a supply
  contract; a target is never a deployment; an attributed interpretation is
  never an operating row; an undisclosed value stays null, never zero.
- No formula exists here. Financial rows are never summed; per-hand
  quantities are never converted; totals are structurally null.
- ``generation`` is a CONTENT fingerprint (sha256 over the definition
  version, rights revision, sorted revision tuple and the time-scoping query
  fields). It is never an access token and never a simultaneity claim.

Private names (``_canonical_text``, ``_validate_query``, ``_passes_time_mode``,
``_le``, ``_is_retrospective``) are imported from the shared owner rather
than re-implemented; a public export has been requested of that seat and is
pending. A local frozen mirror of the shared types keeps this module
importable (and its tests green) on a base without #7870.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from engine.theme_graph.curation_assertion import (
    CurationAssertionError,
    source_ref_for,
    validate_assertion,
)

# ---------------------------------------------------------------------------
# Frozen interface
# ---------------------------------------------------------------------------

SCHEMA_ID = "robotics_theme_research.v1"
EVIDENCE_SCHEMA_ID = "robotics_theme_research.evidence.v1"
DEFINITION_VERSION = "2026-09-24.1"
ANCHOR_THEME_ID = "robotics_automation"


def _canonical_theme_id(slug: str) -> tuple[str, bool]:
    """The assertion-side theme id for a mount/API slug, minted by the identity
    owner (``engine.theme_graph.identity.theme_node_id``; shared-owner ruling
    #7870 5812295091). Returns ``(canonical_id, owner_fallback_used)``: the
    local ``theme:<slug>`` fallback exists only so a base without the identity
    owner still composes, and it is always declared in limitations."""
    try:
        from engine.theme_graph.identity import theme_node_id
    except ImportError:  # pragma: no cover - base without the identity owner
        return f"theme:{slug}", True
    return theme_node_id(slug), False
SLICES = ("precision_motion", "perception")
VIEWS = ("composition", "manufacturing", "commercial", "capacity", "economics")
AUTHORITY = {
    "can_rank": False,
    "can_gate": False,
    "can_size": False,
    "can_originate": False,
    "can_open_entry": False,
}

# The shared observation quantity-basis enum (theme_graph.curation_assertion.v1).
QUANTITY_BASES = (
    "per_robot", "per_joint", "per_hand", "per_cell", "per_installation",
    "per_unit", "per_wafer", "per_package", "per_device", "per_period",
    "absolute",
)
COST_BOUNDARIES = ("integrated_assembly", "contained_component", "standalone")

# predicate -> the one textual relation this composer exposes
_RELATION_KINDS = {
    "PRODUCT_CAPABILITY": "catalog_capability",
    "DOCUMENTED_PRODUCT_INCLUSION": "documented_inclusion",
    "ANNOUNCED_DEVELOPMENT_AGREEMENT": "announced_development",
    "DEPLOYMENT_TARGET": "deployment_target",
    "REPORTED_DEPLOYMENT": "reported_deployment",
    "OWNERSHIP_EVENT": "ownership_event",
    "REPORTED_OPERATING_MEASURE": "operating_observation",
    "REPORTED_FINANCIAL_MEASURE": "financial_observation",
}

# predicate -> the views it feeds. A statement whose mode is
# ATTRIBUTED_INTERPRETATION never becomes a row in ANY view; it survives as
# a summary interpretation item and as authorized evidence only.
_VIEW_PREDICATES = {
    "composition": {"DOCUMENTED_PRODUCT_INCLUSION", "PRODUCT_CAPABILITY"},
    "manufacturing": set(),
    "commercial": {"ANNOUNCED_DEVELOPMENT_AGREEMENT", "DEPLOYMENT_TARGET",
                   "REPORTED_DEPLOYMENT", "OWNERSHIP_EVENT"},
    "capacity": {"REPORTED_OPERATING_MEASURE"},
    "economics": {"REPORTED_FINANCIAL_MEASURE"},
}

_GRAPH_NODE_CAP = 40
_GRAPH_EDGE_CAP = 80

# ---------------------------------------------------------------------------
# Shared types — imported when the shared owner is on this base, mirrored
# locally (frozen, same field order) when it is not.
# ---------------------------------------------------------------------------

try:  # pinned to #7870 c6c67c87
    from engine.market_ontology.semiconductor_theme_research import (
        OwnerBundle,
        ResearchQuery,
        ResearchRefusal,
        _canonical_text,
        _is_instant,
        _is_retrospective,
        _le,
        _parse_clock,
        _parse_day,
        _passes_time_mode,
        _validate_query,
    )

    SHARED_TYPES = True
except ImportError:  # pragma: no cover - carrier base fallback
    SHARED_TYPES = False

    _MIN_LIMIT = 1
    _MAX_LIMIT = 100

    @dataclass(frozen=True)
    class ResearchQuery:  # type: ignore[no-redef]
        anchor_theme_id: str
        slice_key: str
        view: str
        time_mode: str
        source_cutoff: str | None = None
        recorded_cutoff: str | None = None
        offset: int = 0
        limit: int = 50
        expected_generation: str | None = None

    @dataclass(frozen=True)
    class OwnerBundle:  # type: ignore[no-redef]
        revision_tuple: tuple
        rights_revision: str
        assertions: tuple
        identity_results: tuple
        event_workspaces: tuple
        financial_packets: tuple
        interpretation_blocks: tuple
        native_refs: tuple
        omissions: tuple

    class ResearchRefusal(ValueError):  # type: ignore[no-redef]
        """A query/generation contract violation. ``str(exc)`` is ``.code``."""

        def __init__(self, code: str):
            super().__init__(code)
            self.code = code

    def _canonical_text(payload: Mapping[str, Any]) -> str:  # type: ignore[misc]
        return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)

    def _is_instant(value: str) -> bool:  # type: ignore[misc]
        return "T" in value

    def _parse_clock(value: str) -> datetime:  # type: ignore[misc]
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        moment = datetime.fromisoformat(text)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment

    def _parse_day(value: str):  # type: ignore[misc]
        return _parse_clock(value).date() if _is_instant(value) \
            else datetime.strptime(value, "%Y-%m-%d").date()

    def _le(value: str, cutoff: str) -> bool:  # type: ignore[misc]
        """date-vs-instant comparison without synthesizing a time."""
        if not _is_instant(value) and not _is_instant(cutoff):
            return _parse_day(value) <= _parse_day(cutoff)
        if not _is_instant(value):
            return _parse_day(value) <= _parse_clock(cutoff).date()
        if not _is_instant(cutoff):
            return _parse_clock(value).date() <= _parse_day(cutoff)
        return _parse_clock(value) <= _parse_clock(cutoff)

    def _validate_query(query: ResearchQuery) -> None:  # type: ignore[misc]
        if not isinstance(query.limit, int) or isinstance(query.limit, bool) \
                or not _MIN_LIMIT <= query.limit <= _MAX_LIMIT:
            raise ResearchRefusal("limit_out_of_range")
        if not isinstance(query.offset, int) or isinstance(query.offset, bool) \
                or query.offset < 0:
            raise ResearchRefusal("offset_negative")
        if query.offset > 0 and query.expected_generation is None:
            raise ResearchRefusal("expected_generation_required")
        if query.time_mode == "system_replay" and (
                query.source_cutoff is None or query.recorded_cutoff is None):
            raise ResearchRefusal("replay_cutoffs_required")

    def _passes_time_mode(assertion: Mapping[str, Any],
                          query: ResearchQuery,
                          limitations: set[str]) -> bool:  # type: ignore[misc]
        source = assertion["source"]
        if query.time_mode == "latest":
            return True
        if query.time_mode == "source_history":
            if query.source_cutoff is None:
                return True
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
                if _is_instant(query.source_cutoff) \
                        and _parse_day(published) \
                        == _parse_clock(query.source_cutoff).date():
                    limitations.add("same_day_grain_ambiguous")
                    return False
            if not _le(published, query.source_cutoff):
                return False
        return True

    def _is_retrospective(assertion: Mapping[str, Any],
                          query: ResearchQuery) -> bool:  # type: ignore[misc]
        if query.time_mode != "source_history":
            return False
        published = assertion["source"].get("published_at")
        if published is None:
            return False
        return _parse_day(assertion["source"]["retained_at"]) \
            > _parse_day(published)


# ---------------------------------------------------------------------------
# Selectors — source-scoped, never global
# ---------------------------------------------------------------------------

def _biz_selector(label: str) -> str:
    return f"biz:{label}"


def _prd_selector(business: str, product: str) -> str:
    return f"prd:{business}/{product}"


def _plt_selector(business: str, platform: str) -> str:
    return f"plt:{business}/{platform}"


def _obj_selector(publisher: str, label: str) -> str:
    return f"obj:{publisher}/{label}"


def _subject_selector(assertion: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """(selector, kind) for the subject side; (None, None) when unlabelled."""
    subject = assertion.get("subject") or {}
    business = subject.get("source_business_label")
    product = subject.get("source_product_label")
    platform = subject.get("source_platform_label")
    if isinstance(platform, str) and platform and isinstance(business, str):
        return _plt_selector(business, platform), "platform"
    if isinstance(product, str) and product and isinstance(business, str):
        return _prd_selector(business, product), "product"
    if isinstance(business, str) and business:
        return _biz_selector(business), "business"
    return None, None


def _object_selector(assertion: Mapping[str, Any]) -> str | None:
    obj = assertion.get("object") or {}
    publisher = (assertion.get("source") or {}).get("publisher")
    label = obj.get("source_product_label")
    if isinstance(label, str) and label and isinstance(publisher, str) and publisher:
        return _obj_selector(publisher, label)
    return None


def _adapt_source(assertion: Mapping[str, Any]) -> dict[str, Any]:
    """The shared time filter reads ``source.available_at``; a Robotics
    assertion carries no such field, so availability is the OBSERVATION
    clock. The adaptation is a copy — the caller's payload is never
    mutated and the composed rows echo the true Robotics source fields."""
    source = assertion.get("source") or {}
    if isinstance(source.get("available_at"), str) or "available_at" in source:
        return dict(assertion)
    adapted = dict(assertion)
    observed = source.get("observed_at")
    if isinstance(observed, str) and observed:
        adapted["source"] = {**source, "available_at": observed}
    return adapted


# ---------------------------------------------------------------------------
# Generation — content fingerprint, pagination excluded
# ---------------------------------------------------------------------------

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
    digest = hashlib.sha256(
        _canonical_text(payload).encode("utf-8")).hexdigest()[:32]
    return "gen_" + digest


# ---------------------------------------------------------------------------
# Selection — validate, scope, time-filter, then gate review/supersession
# ---------------------------------------------------------------------------

class _Selection:
    """The authorized, time-scoped selection plus its caveats and gates."""

    def __init__(self, query: ResearchQuery, bundle: OwnerBundle):
        self.query = query
        self.bundle = bundle
        self.generation = _generation(query, bundle)
        self.limitations: set[str] = set()
        # Sol #7780 5813801605 / disposition "Slice scope": the Robotics corpus
        # is a declared witness cohort, never slice membership; every response
        # and every evidence object says so.
        self.limitations.add("slice_scope_unowned")
        self.assertions: list[dict[str, Any]] = []
        canonical_theme, owner_fallback = _canonical_theme_id(query.anchor_theme_id)
        if owner_fallback:
            self.limitations.add("identity_owner_fallback")
        slug_keyed = 0
        for index, item in enumerate(bundle.assertions):
            try:
                assertion = validate_assertion(item)
            except CurationAssertionError:
                self.limitations.add(f"assertion_invalid:{index}")
                continue
            scope = assertion.get("scope") or {}
            # scope gate: theme AND facet. The theme is matched on the
            # CANONICAL id only (theme:<slug>); a bare-slug scope is the
            # pre-ruling defect and is dropped but counted, never healed.
            theme = scope.get("canonical_theme_id")
            if theme == query.anchor_theme_id:
                slug_keyed += 1
                continue
            if theme != canonical_theme:
                continue
            if scope.get("technology_facet") != query.slice_key:
                continue
            if not _passes_time_mode(_adapt_source(assertion), query,
                                     self.limitations):
                continue
            self.assertions.append(assertion)
        self.assertions.sort(key=lambda a: a["curation_revision"])
        if slug_keyed:
            self.limitations.add(f"scope_slug_keyed:{slug_keyed}")
        # RBV-27: partial rights show a partial state and NEVER name the
        # withheld families (deliberate divergence from the shared owner's
        # ``omitted:<name>`` limitation).
        if bundle.omissions:
            self.limitations.add("rights_partial")

        self._apply_review_gate()
        self._apply_supersession()
        self._apply_syndication()

    # -- review gate (RBV-18) ----------------------------------------------
    #
    # "now of the query" is the replay cutoff when present, else the newest
    # review stamp inside the selection — never the wall clock, so a
    # composition is reproducible.

    def _now_of_query(self) -> str | None:
        if self.query.recorded_cutoff is not None:
            return self.query.recorded_cutoff
        stamps = [a.get("review", {}).get("reviewed_at") for a in self.assertions]
        stamps = [s for s in stamps if isinstance(s, str) and s]
        return max(stamps) if stamps else None

    def _review_excluded(self, assertion: Mapping[str, Any]) -> bool:
        review = assertion.get("review") or {}
        disposition = review.get("disposition")
        if disposition in ("held", "rejected"):
            self.limitations.add(
                "held_present" if disposition == "held" else "rejected_present")
            return True
        due = review.get("review_due_at")
        now = self._now_of_query()
        if isinstance(due, str) and due and now is not None and _le(due, now):
            self.limitations.add("review_expired_present")
            return True
        return False

    def _apply_review_gate(self) -> None:
        self.review_ok = [a for a in self.assertions
                          if not self._review_excluded(a)]

    # -- supersession (RBV-17) ----------------------------------------------
    #
    # A correction inside the selection supersedes its predecessor for
    # CURRENT applicability; both stay rows (the predecessor flagged) and
    # both stay authorized evidence.

    def _apply_supersession(self) -> None:
        revisions = {a["curation_revision"] for a in self.review_ok}
        self.superseded: set[str] = set()
        for a in self.review_ok:
            prior = (a.get("correction") or {}).get("predecessor_revision")
            if isinstance(prior, str) and prior and prior in revisions:
                self.superseded.add(prior)
        if self.superseded:
            self.limitations.add("superseded_present")
        self.current = list(self.review_ok)

    def superseded_revisions(self) -> set[str]:
        return set(self.superseded)

    # -- syndication (RBV-26) ------------------------------------------------
    #
    # A syndicated copy corroborates its original; it never counts as an
    # independent source and never appears as its own row. The collapse only
    # happens when exactly one selected original matches the named upstream
    # publisher — an ambiguous match keeps both rows rather than guessing.

    def _apply_syndication(self) -> None:
        self.corroboration: dict[str, list[str]] = {}
        by_revision = {a["curation_revision"]: a for a in self.current}
        survivors = []
        for assertion in self.current:
            dependence = (assertion.get("limitations") or {}).get(
                "source_dependence") or ""
            if not dependence.startswith("syndicated_copy_of:"):
                survivors.append(assertion)
                continue
            upstream = dependence[len("syndicated_copy_of:"):]
            originals = [
                a for a in self.current
                if (a.get("source") or {}).get("publisher") == upstream
                and not ((a.get("limitations") or {}).get("source_dependence")
                         or "").startswith("syndicated_copy_of:")
                and a.get("predicate") == assertion.get("predicate")
            ]
            if len(originals) == 1:
                original = originals[0]
                self.corroboration.setdefault(
                    original["curation_revision"], []).append(
                    source_ref_for(assertion))
                self.limitations.add("syndicated_collapsed")
            else:
                survivors.append(assertion)
        self.current = survivors
        # row_assertions: current, row-eligible (an attributed interpretation
        # is never a row in ANY view — RBV-23); superseded predecessors STAY
        # rows, flagged ``review.current == False`` (RBV-17).
        self.row_assertions = [a for a in self.current
                               if a.get("statement_mode") != "ATTRIBUTED_INTERPRETATION"]
        # live: the non-superseded projection — the only thing that feeds
        # companies roles, native subjects, the graph and summary items.
        self.live = [a for a in self.row_assertions
                     if a["curation_revision"] not in self.superseded]

    # -- replay-scoped interpretation blocks ---------------------------------

    def interpretation_blocks(self) -> list[dict[str, Any]]:
        chosen = []
        for block in self.bundle.interpretation_blocks:
            if self.query.time_mode == "system_replay":
                reviewed = block.get("reviewed_at")
                if not isinstance(reviewed, str) \
                        or not _le(reviewed, self.query.recorded_cutoff):
                    continue
            chosen.append(dict(block))
        chosen.sort(key=lambda b: b.get("interpretation_id", ""))
        return chosen

    # -- identity ------------------------------------------------------------

    def identity_state(self, label: Any) -> dict[str, Any]:
        """Shared-owner identity law, with the R1 echo extension: an
        unresolved identity row still echoes its GMI node id (the subject's
        own company_node_id), while the SECURITY join stays closed."""
        if not isinstance(label, str) or not label:
            return {"company_node_id": None, "reason": "identity_unresolved",
                    "security": None}
        for result in self.bundle.identity_results:
            if result.get("source_business_label") != label:
                continue
            learned = result.get("mapping_learned_at")
            if self.query.time_mode == "system_replay" \
                    and isinstance(learned, str) and learned \
                    and not _le(learned, self.query.recorded_cutoff):
                return {"company_node_id": None,
                        "reason": "identity_not_yet_learned", "security": None}
            node = result.get("company_node_id")
            security = None
            if result.get("resolution") == "RESOLVED" \
                    and isinstance(result.get("security_id"), str) \
                    and result["security_id"]:
                security = {
                    "security_id": result["security_id"],
                    "listing_valid_from": result.get("listing_valid_from"),
                    "listing_valid_to": result.get("listing_valid_to"),
                }
            return {
                "company_node_id": node if isinstance(node, str) and node else None,
                "reason": None if security is not None else "identity_unresolved",
                "security": security,
            }
        # no identity row: echo the node id the subject itself carries
        for assertion in self.row_assertions:
            subject = assertion.get("subject") or {}
            if subject.get("source_business_label") == label:
                node = subject.get("company_node_id")
                return {"company_node_id": node if isinstance(node, str) and node
                        and node.startswith("co:") else None,
                        "reason": "identity_unresolved", "security": None}
        return {"company_node_id": None, "reason": "identity_unresolved",
                "security": None}


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------

_ROW_ORDER = ("selector", "object_selector", "curation_revision")


def _industrial_row(assertion: Mapping[str, Any], selection: _Selection) -> dict[str, Any]:
    subject = assertion.get("subject") or {}
    obj = assertion.get("object") or {}
    scope = assertion.get("scope") or {}
    source = assertion.get("source") or {}
    limits = assertion.get("limitations") or {}
    temporal = assertion.get("temporal") or {}
    selector, kind = _subject_selector(assertion)
    business = subject.get("source_business_label")

    configuration = None
    for candidate in (subject.get("configuration"), obj.get("configuration")):
        if candidate is not None:
            configuration = candidate
            break

    superseded = assertion["curation_revision"] in selection.superseded_revisions()
    corroboration = selection.corroboration.get(assertion["curation_revision"], [])

    return {
        "assertion_ref": source_ref_for(assertion),
        "curation_revision": assertion["curation_revision"],
        "source_business_label": business,
        "source_product_label": subject.get("source_product_label"),
        "selector": selector,
        "object_selector": _object_selector(assertion),
        "kind": kind,
        "model": None,
        "configuration": configuration,
        "stage": None,
        "stage_source_language": None,
        "relation_kind": _RELATION_KINDS[assertion["predicate"]],
        "predicate": assertion["predicate"],
        "statement_mode": assertion["statement_mode"],
        "retrospective": _is_retrospective(assertion, selection.query),
        "observation": dict(assertion["observation"]),
        "measure_scope": None,
        "purchase_total": None,
        "purchase_total_reason": None,
        "object_product_label": obj.get("source_product_label"),
        "object_configuration": obj.get("configuration"),
        "application": scope.get("application"),
        "technology_facet": scope.get("technology_facet"),
        "region": scope.get("region"),
        "period": scope.get("period"),
        "denominator": scope.get("denominator"),
        "source_clocks": {
            "published_at": source.get("published_at"),
            "published_at_grain": source.get("published_at_grain"),
            "observed_at": source.get("observed_at"),
            "retained_at": source.get("retained_at"),
            "business_valid_from": temporal.get("business_valid_from"),
            "business_valid_to": temporal.get("business_valid_to"),
        },
        "review": {
            "disposition": (assertion.get("review") or {}).get("disposition"),
            "reviewed_at": (assertion.get("review") or {}).get("reviewed_at"),
            "review_due_at": (assertion.get("review") or {}).get("review_due_at"),
            "current": not superseded,
        },
        "independent_source_count": 1,
        "corroboration_refs": sorted(corroboration),
        "correction": {
            "predecessor_revision": (assertion.get("correction") or {})
            .get("predecessor_revision"),
            "reason": (assertion.get("correction") or {}).get("reason"),
        },
        "establishes": list(limits.get("establishes") or []),
        "does_not_establish": list(limits.get("does_not_establish") or []),
        "coverage": limits.get("coverage") or "",
        "source_dependence": limits.get("source_dependence") or "",
    }


def _row_sort_key(row: Mapping[str, Any]) -> tuple:
    return tuple((row.get(key) or "") if isinstance(row.get(key), str)
                 else "" for key in _ROW_ORDER)


# ---------------------------------------------------------------------------
# Graph — directed, never cycle-pruned, capped
# ---------------------------------------------------------------------------

def _node_of(selector_id: str, selection: _Selection,
             business_of_row: Mapping[str, Any]) -> dict[str, Any] | None:
    kind, label, company = None, None, None
    if selector_id.startswith("prd:") or selector_id.startswith("obj:"):
        kind, label = "product", selector_id.split("/", 1)[1]
    elif selector_id.startswith("plt:"):
        kind, label = "platform", selector_id.split("/", 1)[1]
    elif selector_id.startswith("biz:"):
        kind, label = "business", selector_id[len("biz:"):]
        company = selection.identity_state(label)["company_node_id"]
    elif selector_id.startswith("app:"):
        kind, label = "application", selector_id[len("app:"):]
    elif selector_id.startswith("facet:"):
        kind, label = "facet", selector_id[len("facet:"):]
    else:
        return None
    return {"id": selector_id, "kind": kind, "label": label,
            "company_node_id": company}


def _graph(rows: list[dict[str, Any]], selection: _Selection) -> tuple[dict, bool]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple, dict[str, Any]] = {}
    truncated = False
    for row in rows:
        src, dst = row.get("selector"), row.get("object_selector")
        if not src or not dst:
            continue
        for selector_id in (src, dst):
            if selector_id not in nodes:
                node = _node_of(selector_id, selection, row)
                if node is not None:
                    nodes[selector_id] = node
        edge = {
            "src": src, "dst": dst,
            "relation_kind": row["relation_kind"],
            "assertion_ref": row["assertion_ref"],
            "statement_mode": row["statement_mode"],
        }
        edges[(src, dst, row["relation_kind"], row["assertion_ref"])] = edge
    ordered_nodes = [nodes[k] for k in sorted(nodes)]
    ordered_edges = [edges[k] for k in sorted(edges)]
    if len(ordered_nodes) > _GRAPH_NODE_CAP:
        ordered_nodes = ordered_nodes[:_GRAPH_NODE_CAP]
        truncated = True
    if len(ordered_edges) > _GRAPH_EDGE_CAP:
        ordered_edges = ordered_edges[:_GRAPH_EDGE_CAP]
        truncated = True
    return {"nodes": ordered_nodes, "edges": ordered_edges}, truncated


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

_ACQUIRER_MARKERS = ("acquires", "acquired", "acquisition")
_SELLER_MARKERS = ("sale to", "divest", "transferring", "transfer of",
                   "change of")


def _ownership_role(assertion: Mapping[str, Any]) -> str:
    if assertion.get("predicate") != "OWNERSHIP_EVENT":
        return "subject"
    mode = assertion.get("statement_mode")
    if mode == "REPORTED_FACT":
        valid_from = (assertion.get("temporal") or {}).get("business_valid_from")
        if isinstance(valid_from, str) and valid_from:
            return f"owner_from:{valid_from}"
        return "owner_reported_effective_date_unknown"
    if mode == "ANNOUNCED_ARRANGEMENT":
        limits = assertion.get("limitations") or {}
        # The side is read ONLY from what the assertion ESTABLISHES about its
        # own subject. ``does_not_establish`` is a list of denials and
        # ``coverage`` may carry the counterparty's verb, so neither may
        # decide a side (R2 review nit 1). Both verbs present = ambiguous,
        # and an ambiguous side is never guessed.
        scanned = " ".join(
            piece for piece in (limits.get("establishes") or [])
            if isinstance(piece, str)
        ).lower()
        acquirer = any(marker in scanned for marker in _ACQUIRER_MARKERS)
        seller = any(marker in scanned for marker in _SELLER_MARKERS)
        if acquirer and not seller:
            return "announced_acquirer"
        if seller and not acquirer:
            return "announced_seller"
        return "announced_party"
    return "subject"


def _companies(selection: _Selection) -> dict[str, Any]:
    by_label: dict[str, list[dict[str, Any]]] = {}
    for assertion in selection.live:
        label = (assertion.get("subject") or {}).get("source_business_label")
        if not isinstance(label, str) or not label:
            continue
        by_label.setdefault(label, []).append(assertion)
    rows = []
    for label in sorted(by_label):
        state = selection.identity_state(label)
        navigation = {"status": "ready", "href": None, "reason": None}
        if state["security"] is None:
            navigation = {"status": "unavailable", "href": None,
                          "reason": state["reason"]}
        roles = sorted(
            ({
                "role": _ownership_role(a),
                "predicate": a["predicate"],
                "statement_mode": a["statement_mode"],
                "assertion_ref": source_ref_for(a),
            } for a in by_label[label]),
            key=lambda r: (r["assertion_ref"], r["role"]),
        )
        rows.append({
            "source_business_label": label,
            "company_node_id": state["company_node_id"],
            "navigation": navigation,
            "roles": roles,
            "security": state["security"],
        })
    rows.sort(key=lambda r: (r["source_business_label"],
                             r["company_node_id"] or ""))
    section: dict[str, Any] = {"input_refs": sorted({
        a["curation_revision"] for group in by_label.values() for a in group})}
    if not rows:
        section.update({"status": "unavailable", "reason": "no_companies",
                        "rows": []})
        return section
    status = "degraded" if any(r["navigation"]["status"] != "ready"
                               for r in rows) else "ready"
    section["status"] = status
    if status == "degraded":
        section["reason"] = "identity_incomplete"
    section["rows"] = rows
    return section


# ---------------------------------------------------------------------------
# Native subjects — source-scoped, never merged across sources
# ---------------------------------------------------------------------------

def _native_subjects(selection: _Selection) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for assertion in selection.live:
        subject = assertion.get("subject") or {}
        scope = assertion.get("scope") or {}
        business = subject.get("source_business_label")
        selector, kind = _subject_selector(assertion)
        if selector and selector not in seen:
            company = None
            if isinstance(business, str) and business:
                company = selection.identity_state(business)["company_node_id"]
            seen[selector] = {"selector": selector, "kind": kind,
                              "source_label": selector.split("/", 1)[-1]
                              if "/" in selector else selector.split(":", 1)[1],
                              "company_node_id": company}
        application = scope.get("application")
        if isinstance(application, str) and application:
            key = f"app:{application}"
            seen.setdefault(key, {"selector": key, "kind": "application",
                                  "source_label": application,
                                  "company_node_id": None})
        facet = scope.get("technology_facet")
        if isinstance(facet, str) and facet:
            key = f"facet:{facet}"
            seen.setdefault(key, {"selector": key, "kind": "facet",
                                  "source_label": facet,
                                  "company_node_id": None})
    return [seen[k] for k in sorted(seen)]


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _text_of(assertion: Mapping[str, Any]) -> str:
    limits = assertion.get("limitations") or {}
    establishes = limits.get("establishes") or []
    if establishes and isinstance(establishes[0], str) and establishes[0]:
        return establishes[0]
    return limits.get("coverage") or ""


def _summary(selection: _Selection, response_limitations: set[str]) -> dict[str, Any]:
    query = selection.query
    selected_revisions = {a["curation_revision"] for a in selection.assertions}
    current_revisions = {a["curation_revision"] for a in selection.current}
    blocks = selection.interpretation_blocks()

    stale_blocks: list[dict[str, Any]] = []
    for block in blocks:
        supported = block.get("freshness") == "current" and all(
            ref in selected_revisions for ref in (block.get("input_revisions") or []))
        if not supported:
            stale_blocks.append(block)

    what_changed = sorted(
        ({"text": _text_of(a), "label": "fact",
          "input_refs": [a["curation_revision"]]}
         for a in selection.live
         if a["statement_mode"] in ("REPORTED_FACT", "CATALOG_DESCRIPTION")),
        key=lambda i: (i["text"], i["input_refs"]))
    next_evidence = sorted(
        ({"text": _text_of(a), "label": "target",
          "input_refs": [a["curation_revision"]]}
         for a in selection.live
         if a["statement_mode"] in ("FORWARD_TARGET", "ANNOUNCED_ARRANGEMENT")
         or a["predicate"] == "DEPLOYMENT_TARGET"),
        key=lambda i: (i["text"], i["input_refs"]))
    for block in blocks:
        watcher = block.get("falsifier") or block.get("missing_measurement") or ""
        if watcher:
            next_evidence.append({"text": watcher, "label": "interpretation",
                                  "input_refs": list(
                                      block.get("input_revisions") or [])})
    next_evidence.sort(key=lambda i: (i["text"], i["input_refs"]))

    why_it_matters: list[dict[str, Any]] = []
    for block in blocks:
        item = {"text": block.get("mechanism") or "", "label": "interpretation",
                "input_refs": list(block.get("input_revisions") or [])}
        if item["text"]:
            why_it_matters.append(item)
    for assertion in selection.current:
        if assertion["statement_mode"] == "ATTRIBUTED_INTERPRETATION" \
                and assertion["curation_revision"] not in selection.superseded:
            why_it_matters.append({
                "text": _text_of(assertion), "label": "interpretation",
                "input_refs": [assertion["curation_revision"]]})
    why_it_matters.sort(key=lambda i: (i["text"], i["input_refs"]))

    offsets = sorted(
        ({"text": block.get("offset") or "", "label": "interpretation",
          "input_refs": list(block.get("input_revisions") or [])}
         for block in blocks if block.get("offset")),
        key=lambda i: (i["text"], i["input_refs"]))

    stale_ids = {id(b) for b in stale_blocks}
    for item in why_it_matters + offsets:
        source_block = next((b for b in blocks
                             if item["input_refs"] == list(
                                 b.get("input_revisions") or [])), None)
        if source_block is not None and id(source_block) in stale_ids:
            item["stale"] = True
            item["text"] = "[stale interpretation] " + item["text"]
    if stale_blocks:
        response_limitations.add("interpretation_stale")

    summary: dict[str, Any] = {
        "input_refs": sorted(current_revisions),
        "what_changed": what_changed,
        "why_it_matters": why_it_matters,
        "offset": offsets,
        "next_evidence": next_evidence,
    }
    if not selection.assertions:
        summary.update({"status": "unavailable",
                        "reason": "no_selected_assertions"})
    elif stale_blocks:
        summary.update({"status": "degraded", "reason": "interpretation_stale"})
    else:
        summary["status"] = "ready"
    return summary


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _views(selection: _Selection, response_limitations: set[str]) -> dict[str, Any]:
    built: dict[str, dict[str, Any]] = {}
    for view in VIEWS:
        predicates = _VIEW_PREDICATES[view]
        rows = [_industrial_row(a, selection) for a in selection.row_assertions
                if a["predicate"] in predicates]
        rows.sort(key=_row_sort_key)
        live_rows = [r for r in rows if r["review"]["current"]]
        section: dict[str, Any] = {"input_refs": sorted(
            r["curation_revision"] for r in rows)}
        section["rows"] = rows
        if rows:
            section["status"] = "ready"
            section["total"] = {"value": None, "reason": "totals_not_computed"}
        else:
            section["status"] = "unavailable"
            # closed reason set: the shared owner's ``no_selected_assertions``
            # plus the packet-mandated ``no_manufacturing_evidence`` only
            section["reason"] = ("no_manufacturing_evidence"
                                 if view == "manufacturing" and selection.assertions
                                 else "no_selected_assertions")
            section["total"] = {"value": None, "reason": None}
        graph, truncated = _graph(live_rows, selection)
        section["graph"] = graph
        section["limitations"] = ["graph_truncated"] if truncated else []
        if truncated:
            response_limitations.add("graph_truncated")
            section["status"] = "degraded"
        built[view] = section

    # pagination slices the companies rows and every view's rows alike; the
    # population behind the metrics never changes with the page
    start = selection.query.offset
    stop = start + selection.query.limit
    for view in VIEWS:
        built[view]["rows"] = built[view]["rows"][start:stop]
        built[view]["input_refs"] = sorted(
            r["curation_revision"] for r in built[view]["rows"])
    return built


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def safe_quantity(value: object, basis: object) -> tuple[float, str] | None:
    """Accept a decoded BOM quantity EXACTLY as the source stated it.

    Refuses (returns ``None``) for booleans, non-numbers, non-finite floats,
    negatives, missing values, the strict-JSON sentinels and any basis
    outside the shared enum. A accepted value is NEVER converted between
    bases: a per-hand count stays per-hand because the missing per-hand
    multiplicity is evidence, not arithmetic (RBV-22).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value < 0:
        return None
    if not isinstance(basis, str) or basis not in QUANTITY_BASES:
        return None
    return (float(value), basis)


def compatible_financial_basis(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Two financial observations share a basis only when entity period,
    denominator, unit and gross/net basis are ALL equal. Fail-closed: a
    missing field on one side never matches a present field on the other
    (RBV-09 — ratios across incompatible bases are refused)."""

    def _basis(mapping: Mapping[str, Any]) -> tuple:
        scope = mapping.get("scope") or {}
        observation = mapping.get("observation") or {}
        return (scope.get("period"), scope.get("denominator"),
                observation.get("unit"), observation.get("gross_net_basis"))

    return _basis(a) == _basis(b)


def non_overlapping_cost_items(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate a caller's cost-selection and refuse the parent/child
    double-count shape (RBV-21): an ``integrated_assembly`` item selected
    together with an item contained in it refuses with
    ``purchase_boundary_double_count``. Malformed items refuse with
    ``cost_item_invalid``. The composer itself never builds a cost total."""
    cleaned: list[dict[str, Any]] = []
    if not isinstance(items, (list, tuple)):
        raise ResearchRefusal("cost_item_invalid")
    for item in items:
        if not isinstance(item, Mapping):
            raise ResearchRefusal("cost_item_invalid")
        ref = item.get("assertion_ref")
        boundary = item.get("boundary")
        contained_in = item.get("contained_in")
        if not isinstance(ref, str) or not ref:
            raise ResearchRefusal("cost_item_invalid")
        if boundary not in COST_BOUNDARIES:
            raise ResearchRefusal("cost_item_invalid")
        if contained_in is not None and not isinstance(contained_in, str):
            raise ResearchRefusal("cost_item_invalid")
        cleaned.append({"assertion_ref": ref, "boundary": boundary,
                        "contained_in": contained_in})
    assembly_refs = {c["assertion_ref"] for c in cleaned
                     if c["boundary"] == "integrated_assembly"}
    for item in cleaned:
        if item["contained_in"] in assembly_refs:
            raise ResearchRefusal("purchase_boundary_double_count")
    return cleaned


# ---------------------------------------------------------------------------
# Composition entry point
# ---------------------------------------------------------------------------

_ECONOMICS_REASON = "no_management_sequence_in_robotics_v1"


def _refuse_unsupported_identity_vintage(selection: "_Selection") -> None:
    """Sol #7780 5813801605 (historical identity): a ``system_replay`` may not
    be served on an identity whose as-known vintage is unsupported. An identity
    row for an in-scope subject without a non-empty string
    ``mapping_learned_at`` is exactly that; the shared route-level token is
    ``identity_vintage_unsupported`` (#7870 5813976021). ``latest`` and
    ``source_history`` never take this path; a subject with NO identity row
    claims no belief and is not affected; a mapping learned after the cutoff
    stays the row-level ``identity_not_yet_learned`` (the system knows it did
    not know yet). No rebuild or wall-clock time is ever used as a vintage."""
    if selection.query.time_mode != "system_replay":
        return
    labels = {
        (a.get("subject") or {}).get("source_business_label")
        for a in selection.assertions
    }
    for result in selection.bundle.identity_results:
        if result.get("source_business_label") not in labels:
            continue
        learned = result.get("mapping_learned_at")
        if not (isinstance(learned, str) and learned):
            raise ResearchRefusal("identity_vintage_unsupported")


def compose_robotics_research(query: ResearchQuery,
                              bundle: OwnerBundle) -> dict[str, Any]:
    """Compose the closed Robotics research response. Pure: the bundle is
    read, never mutated; nothing outside the arguments is consulted."""
    if query.anchor_theme_id != ANCHOR_THEME_ID:
        raise ResearchRefusal("not_available")
    if query.slice_key not in SLICES:
        raise ResearchRefusal("slice_not_supported")
    if query.view not in VIEWS:
        raise ResearchRefusal("view_not_supported")
    _validate_query(query)
    selection = _Selection(query, bundle)
    generation = selection.generation
    # None is "no expectation" (a first fetch); a SET value must match exactly
    if query.expected_generation is not None \
            and query.expected_generation != generation:
        raise ResearchRefusal("generation_changed")
    _refuse_unsupported_identity_vintage(selection)

    response_limitations: set[str] = set(selection.limitations)
    summary = _summary(selection, response_limitations)
    views = _views(selection, response_limitations)
    companies = _companies(selection)
    companies["rows"] = companies["rows"][query.offset:query.offset + query.limit]

    evidence_refs: list[dict[str, Any]] = [
        {"assertion_ref": source_ref_for(a),
         "curation_revision": a["curation_revision"],
         "kind": "assertion"}
        for a in selection.assertions
    ]
    evidence_refs.extend(
        {"owner_store": ref.get("owner_store"),
         "native_identity": copy.deepcopy(ref.get("native_identity")),
         "reference_id": ref.get("reference_id"),
         "kind": "native"}
        for ref in bundle.native_refs)

    coverage_status = "unavailable"
    if bundle.omissions:
        coverage_status = "degraded"
    elif selection.assertions:
        coverage_status = "ready"

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
        "native_subjects": _native_subjects(selection),
        "summary": summary,
        "companies": companies,
        "industrial_views": views,
        "economics": {
            "status": "unavailable",
            "reason": _ECONOMICS_REASON,
            "input_refs": [],
            "management": None,
            "witness_gate": "missing",
        },
        "expectations": {
            "management": {
                "status": "unavailable",
                "reason": _ECONOMICS_REASON,
                "input_refs": [],
                "roles": None,
            },
            "external_consensus": {"status": "unavailable",
                                   "reason": "no_external_consensus"},
            "house_forecast": {"status": "unavailable",
                               "reason": "not_authorized"},
            "market_incorporation": {"status": "unavailable",
                                     "reason": "not_authorized"},
        },
        "evidence_refs": evidence_refs,
        "authorized_coverage": {
            "status": coverage_status,
            "input_refs": sorted(a["curation_revision"]
                                 for a in selection.assertions),
            "selected": len(selection.assertions),
            "industry_total": None,
            "note": "counts only what this principal may know exists",
        },
        "limitations": sorted(response_limitations),
        "authority": dict(AUTHORITY),
    }


# ---------------------------------------------------------------------------
# Authorized evidence selection
# ---------------------------------------------------------------------------

def select_authorized_evidence(query: ResearchQuery, bundle: OwnerBundle,
                               assertion_ref: str) -> dict[str, Any]:
    """Return one authorized assertion as its own evidence object. Unknown
    and not-selected refs share the single code ``not_available`` — no
    existence disclosure."""
    if query.anchor_theme_id != ANCHOR_THEME_ID:
        raise ResearchRefusal("not_available")
    if query.slice_key not in SLICES:
        raise ResearchRefusal("slice_not_supported")
    if query.view not in VIEWS:
        raise ResearchRefusal("view_not_supported")
    _validate_query(query)
    generation = _generation(query, bundle)
    if query.expected_generation is not None \
            and query.expected_generation != generation:
        raise ResearchRefusal("generation_changed")
    selection = _Selection(query, bundle)
    _refuse_unsupported_identity_vintage(selection)
    for assertion in selection.assertions:
        if source_ref_for(assertion) == assertion_ref:
            source = assertion["source"]
            return {
                "schema": EVIDENCE_SCHEMA_ID,
                "generation": generation,
                "assertion_ref": assertion_ref,
                "assertion": copy.deepcopy(assertion),
                "source": {
                    "publisher": source.get("publisher"),
                    "source_uri": source.get("source_uri"),
                    "locator": source.get("locator"),
                    "published_at": source.get("published_at"),
                    "published_at_grain": source.get("published_at_grain"),
                    "observed_at": source.get("observed_at"),
                    "retained_at": source.get("retained_at"),
                },
                "lineage": _correction_lineage(assertion, bundle),
                "limitations": sorted(selection.limitations),
                "authority": dict(AUTHORITY),
            }
    raise ResearchRefusal("not_available")


def _correction_lineage(assertion: Mapping[str, Any],
                        bundle: OwnerBundle) -> list[str]:
    """The immutable predecessor chain behind a corrected assertion, as
    native curation refs, cycle-guarded. The immediate predecessor comes
    first; an uncorrected assertion has an empty lineage."""
    by_revision = {a.get("curation_revision"): a for a in bundle.assertions
                   if isinstance(a, Mapping)}
    lineage: list[str] = []
    seen = {assertion.get("curation_revision")}
    current = assertion
    while True:
        prior = (current.get("correction") or {}).get("predecessor_revision")
        if not isinstance(prior, str) or not prior or prior in seen:
            break
        predecessor = by_revision.get(prior)
        if predecessor is None:
            # the predecessor is not in the bundle: its ref lives in the same
            # theme segment the shared resolver minted for the current
            # assertion — never a locally fabricated theme id
            prefix = source_ref_for(current).rsplit("/", 1)[0]
            lineage.append(f"{prefix}/{prior}")
            break
        seen.add(prior)
        lineage.append(source_ref_for(predecessor))
        current = predecessor
    return lineage
