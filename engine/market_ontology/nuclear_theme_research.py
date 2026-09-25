"""Pure Nuclear theme-research response composition."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from typing import Any

from engine.market_ontology.semiconductor_theme_research import (
    AUTHORITY,
    OwnerBundle,
    ResearchQuery,
    ResearchRefusal,
    _canonical_text,
    _parse_day,
    _is_retrospective,
    _le,
    _passes_time_mode,
    _row_sort_key,
    _validate_query,
)
from engine.theme_graph.curation_assertion import (
    CurationAssertionError,
    source_ref_for,
    validate_assertion,
)
from engine.theme_graph.identity import theme_node_id
from engine.theme_graph.rights import family_for_source_ref

ANCHOR_THEME_ID = "nuclear_power"
SCHEMA_ID = "nuclear_theme_research.v1"
EVIDENCE_SCHEMA_ID = "nuclear_theme_research.evidence.v1"
DEFINITION_VERSION = "2026-09-25.1"
SLICES = ("reactor_technology", "nuclear_components", "fuel_cycle")
VIEWS = ("composition", "manufacturing", "commercial", "capacity", "economics")
WITNESS_COHORT = {
    "reactor_technology": ("co:us:SMR", "co:us:OKLO"),
    "nuclear_components": ("co:us:BWXT",),
    "fuel_cycle": ("co:us:CCJ", "co:us:LEU"),
}
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
_VIEW_PREDICATES = {
    "composition": {"DOCUMENTED_PRODUCT_INCLUSION", "PRODUCT_CAPABILITY"},
    "manufacturing": set(),
    "commercial": {
        "ANNOUNCED_DEVELOPMENT_AGREEMENT", "DEPLOYMENT_TARGET",
        "REPORTED_DEPLOYMENT", "OWNERSHIP_EVENT",
    },
    "capacity": {"REPORTED_OPERATING_MEASURE"},
    "economics": {"REPORTED_FINANCIAL_MEASURE"},
}
_GRAPH_NODE_CAP = 40
_GRAPH_EDGE_CAP = 80
_ROW_ORDER = ("selector", "object_selector", "curation_revision")
_ECONOMICS_REASON = "no_management_sequence_in_nuclear_v1"


def _selector(label: str | None, prefix: str) -> str | None:
    return f"{prefix}:{label}" if isinstance(label, str) and label else None


def _subject_selector(assertion: Mapping[str, Any]) -> tuple[str | None, str | None]:
    subject = assertion.get("subject") or {}
    business = subject.get("source_business_label")
    product = subject.get("source_product_label")
    if product:
        return f"prd:{business}/{product}", "product"
    selector = _selector(business, "biz")
    return selector, "business" if selector else None


def _object_selector(assertion: Mapping[str, Any]) -> str | None:
    label = (assertion.get("object") or {}).get("source_product_label")
    publisher = (assertion.get("source") or {}).get("publisher")
    return f"obj:{publisher}/{label}" if label and publisher else None


def _with_observed_availability(assertion: Mapping[str, Any]) -> dict[str, Any]:
    source = assertion.get("source") or {}
    if "available_at" in source:
        return dict(assertion)
    adapted = dict(assertion)
    adapted["source"] = {**source, "available_at": source.get("observed_at")}
    return adapted


def _is_passed_target(assertion: Mapping[str, Any], query: ResearchQuery) -> bool:
    end = (assertion.get("temporal") or {}).get("business_valid_to")
    return (
        assertion.get("predicate") == "DEPLOYMENT_TARGET"
        and assertion.get("statement_mode") == "FORWARD_TARGET"
        and isinstance(end, str) and end
        and isinstance(query.source_cutoff, str)
        and _parse_day(end) <= _parse_day(query.source_cutoff)
    ) or _is_retrospective(assertion, query)


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


class _Selection:
    def __init__(self, query: ResearchQuery, bundle: OwnerBundle):
        self.query = query
        self.bundle = bundle
        self.generation = _generation(query, bundle)
        self.limitations = {"slice_scope_unowned", "milestone_predicate_unavailable"}
        if query.slice_key == "fuel_cycle":
            self.limitations.add("supplemental_basket_witnesses")
        self.assertions: list[dict[str, Any]] = []
        canonical_theme = theme_node_id(query.anchor_theme_id)
        cohort = WITNESS_COHORT[query.slice_key]
        slug_keyed = 0
        for index, item in enumerate(bundle.assertions):
            try:
                assertion = validate_assertion(item)
            except CurationAssertionError:
                self.limitations.add(f"assertion_invalid:{index}")
                continue
            scope = assertion.get("scope") or {}
            theme = scope.get("canonical_theme_id")
            if theme not in (canonical_theme, query.anchor_theme_id):
                continue
            if scope.get("technology_facet") != query.slice_key:
                continue
            if theme == query.anchor_theme_id:
                slug_keyed += 1
                continue
            subject = assertion.get("subject") or {}
            if subject.get("company_node_id") not in cohort:
                self.limitations.add("witness_cohort_excluded:1")
                continue
            if family_for_source_ref((assertion.get("source") or {}).get("source_uri")) is None:
                self.limitations.add("unmapped_rights_source_excluded:1")
                continue
            if not _passes_time_mode(
                    _with_observed_availability(assertion), query, self.limitations):
                continue
            self.assertions.append(assertion)
        self.assertions.sort(key=lambda assertion: assertion["curation_revision"])
        if slug_keyed:
            self.limitations.add(f"scope_slug_keyed:{slug_keyed}")
        self.known_revisions = {
            item.get("curation_revision") for item in bundle.assertions
            if isinstance(item, Mapping)
        }
        absent = sum(
            1 for block in bundle.interpretation_blocks
            if not self._inputs_known(block)
        )
        if absent:
            self.limitations.add(f"interpretation_inputs_absent:{absent}")
        for omission in bundle.omissions:
            name = omission.split(":", 1)[0]
            self.limitations.add(f"omitted:{name}")
        self._apply_review_gate()
        self._apply_supersession()
        self.row_assertions = [
            assertion for assertion in self.current
            if assertion.get("statement_mode") != "ATTRIBUTED_INTERPRETATION"
        ]
        self.live = [
            assertion for assertion in self.row_assertions
            if assertion["curation_revision"] not in self.superseded
        ]

    def _now_of_query(self) -> str | None:
        if self.query.recorded_cutoff is not None:
            return self.query.recorded_cutoff
        stamps = [
            (assertion.get("review") or {}).get("reviewed_at")
            for assertion in self.assertions
        ]
        return max((stamp for stamp in stamps if isinstance(stamp, str) and stamp),
                   default=None)

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
        self.review_ok = [
            assertion for assertion in self.assertions
            if not self._review_excluded(assertion)
        ]

    def _apply_supersession(self) -> None:
        revisions = {assertion["curation_revision"] for assertion in self.review_ok}
        self.superseded = {
            (assertion.get("correction") or {}).get("predecessor_revision")
            for assertion in self.review_ok
            if isinstance(
                (assertion.get("correction") or {}).get("predecessor_revision"), str
            ) and (assertion.get("correction") or {}).get("predecessor_revision") in revisions
        }
        if self.superseded:
            self.limitations.add("superseded_present")
        self.current = list(self.review_ok)

    def superseded_revisions(self) -> set[str]:
        return set(self.superseded)

    def interpretation_blocks(self) -> list[dict[str, Any]]:
        chosen = []
        for block in self.bundle.interpretation_blocks:
            if not self._inputs_known(block):
                continue
            if self.query.time_mode == "system_replay":
                reviewed = block.get("reviewed_at")
                if not isinstance(reviewed, str) or not _le(
                        reviewed, self.query.recorded_cutoff):
                    continue
            chosen.append(dict(block))
        return sorted(chosen, key=lambda block: block.get("interpretation_id", ""))

    def _inputs_known(self, block: Mapping[str, Any]) -> bool:
        refs = block.get("input_revisions") or []
        return all(isinstance(ref, str) and ref in self.known_revisions for ref in refs)

    def identity_state(self, label: Any) -> dict[str, Any]:
        if not isinstance(label, str) or not label:
            return {"company_node_id": None, "reason": "identity_unresolved",
                    "security": None}
        for result in self.bundle.identity_results:
            if result.get("source_business_label") != label:
                continue
            learned = result.get("mapping_learned_at")
            if self.query.time_mode == "system_replay" and learned \
                    and not _le(learned, self.query.recorded_cutoff):
                return {"company_node_id": None,
                        "reason": "identity_not_yet_learned", "security": None}
            node = result.get("company_node_id")
            security = None
            if result.get("resolution") == "RESOLVED" \
                    and isinstance(result.get("security_id"), str) and result["security_id"]:
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
        for assertion in self.row_assertions:
            subject = assertion.get("subject") or {}
            if subject.get("source_business_label") == label:
                node = subject.get("company_node_id")
                return {
                    "company_node_id": node if isinstance(node, str)
                    and node.startswith("co:") else None,
                    "reason": "identity_unresolved", "security": None,
                }
        return {"company_node_id": None, "reason": "identity_unresolved",
                "security": None}


def _row(assertion: Mapping[str, Any], selection: _Selection) -> dict[str, Any]:
    subject = assertion.get("subject") or {}
    obj = assertion.get("object") or {}
    scope = assertion.get("scope") or {}
    source = assertion.get("source") or {}
    limits = assertion.get("limitations") or {}
    temporal = assertion.get("temporal") or {}
    selector, kind = _subject_selector(assertion)
    return {
        "assertion_ref": source_ref_for(assertion),
        "curation_revision": assertion["curation_revision"],
        "source_business_label": subject.get("source_business_label"),
        "source_product_label": subject.get("source_product_label"),
        "selector": selector,
        "object_selector": _object_selector(assertion),
        "kind": kind,
        "model": None,
        "configuration": subject.get("configuration") or obj.get("configuration"),
        "stage": None,
        "stage_source_language": None,
        "relation_kind": _RELATION_KINDS[assertion["predicate"]],
        "predicate": assertion["predicate"],
        "statement_mode": assertion["statement_mode"],
        "retrospective": _is_passed_target(assertion, selection.query),
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
            "current": assertion["curation_revision"] not in selection.superseded,
        },
        "independent_source_count": 1,
        "corroboration_refs": [],
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


def _graph(rows: list[dict[str, Any]], selection: _Selection) -> tuple[dict, bool]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        src, dst = row.get("selector"), row.get("object_selector")
        if not src or not dst:
            continue
        for selector_id in (src, dst):
            if selector_id not in nodes:
                if selector_id.startswith(("prd:", "obj:")):
                    kind, label = "product", selector_id.split("/", 1)[1]
                elif selector_id.startswith("biz:"):
                    kind, label = "business", selector_id[len("biz:"):]
                else:
                    continue
                company = selection.identity_state(label)["company_node_id"] \
                    if kind == "business" else None
                nodes[selector_id] = {"id": selector_id, "kind": kind,
                                      "label": label, "company_node_id": company}
        edges[(src, dst, row["relation_kind"], row["assertion_ref"])] = {
            "src": src, "dst": dst, "relation_kind": row["relation_kind"],
            "assertion_ref": row["assertion_ref"],
            "statement_mode": row["statement_mode"],
        }
    ordered_nodes = [nodes[key] for key in sorted(nodes)]
    ordered_edges = [edges[key] for key in sorted(edges)]
    truncated = False
    if len(ordered_nodes) > _GRAPH_NODE_CAP:
        ordered_nodes, truncated = ordered_nodes[:_GRAPH_NODE_CAP], True
    if len(ordered_edges) > _GRAPH_EDGE_CAP:
        ordered_edges, truncated = ordered_edges[:_GRAPH_EDGE_CAP], True
    return {"nodes": ordered_nodes, "edges": ordered_edges}, truncated


def _companies(selection: _Selection) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for assertion in selection.live:
        label = (assertion.get("subject") or {}).get("source_business_label")
        if isinstance(label, str) and label:
            grouped.setdefault(label, []).append(assertion)
    rows = []
    for label, assertions in sorted(grouped.items()):
        state = selection.identity_state(label)
        rows.append({
            "source_business_label": label,
            "company_node_id": state["company_node_id"],
            "navigation": {
                "status": "ready" if state["security"] else "unavailable",
                "href": None,
                "reason": None if state["security"] else state["reason"],
            },
            "roles": sorted(({
                "role": "subject",
                "predicate": assertion["predicate"],
                "statement_mode": assertion["statement_mode"],
                "assertion_ref": source_ref_for(assertion),
            } for assertion in assertions), key=lambda role: (
                role["assertion_ref"], role["predicate"])),
            "security": state["security"],
        })
    if not rows:
        return {"status": "unavailable", "reason": "no_companies",
                "input_refs": [], "rows": []}
    return {"status": "ready", "input_refs": sorted({
        assertion["curation_revision"] for group in grouped.values()
        for assertion in group}), "rows": rows}


def _native_subjects(selection: _Selection) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for assertion in selection.live:
        subject = assertion.get("subject") or {}
        selector, kind = _subject_selector(assertion)
        if selector and selector not in seen:
            business = subject.get("source_business_label")
            seen[selector] = {
                "selector": selector, "kind": kind,
                "source_label": selector.split("/", 1)[-1],
                "company_node_id": selection.identity_state(
                    business)["company_node_id"] if business else None,
            }
        facet = (assertion.get("scope") or {}).get("technology_facet")
        if isinstance(facet, str) and facet:
            seen.setdefault(f"facet:{facet}", {
                "selector": f"facet:{facet}", "kind": "facet",
                "source_label": facet, "company_node_id": None})
    return [seen[key] for key in sorted(seen)]


def _text_of(assertion: Mapping[str, Any]) -> str:
    limits = assertion.get("limitations") or {}
    establishes = limits.get("establishes") or []
    if establishes and isinstance(establishes[0], str) and establishes[0]:
        return establishes[0]
    return limits.get("coverage") or ""


def _summary(selection: _Selection) -> dict[str, Any]:
    facts = sorted(({
        "text": _text_of(assertion), "label": "fact",
        "input_refs": [assertion["curation_revision"]],
    } for assertion in selection.live if assertion["statement_mode"] in (
        "REPORTED_FACT", "CATALOG_DESCRIPTION")),
        key=lambda item: (item["text"], item["input_refs"]))
    targets = sorted(({
        "text": _text_of(assertion), "label": "target",
        "input_refs": [assertion["curation_revision"]],
    } for assertion in selection.live if assertion["statement_mode"] in (
        "FORWARD_TARGET", "ANNOUNCED_ARRANGEMENT")
        or assertion["predicate"] == "DEPLOYMENT_TARGET"),
        key=lambda item: (item["text"], item["input_refs"]))
    interpretations = sorted(({
        "text": _text_of(assertion), "label": "interpretation",
        "input_refs": [assertion["curation_revision"]],
    } for assertion in selection.current
        if assertion["statement_mode"] == "ATTRIBUTED_INTERPRETATION"),
        key=lambda item: (item["text"], item["input_refs"]))
    return {
        "status": "ready" if selection.current else "unavailable",
        "input_refs": sorted(assertion["curation_revision"]
                             for assertion in selection.current),
        "what_changed": facts,
        "why_it_matters": interpretations,
        "offset": [],
        "next_evidence": targets,
    }


def _views(selection: _Selection, response_limitations: set[str]) -> dict[str, Any]:
    built: dict[str, dict[str, Any]] = {}
    for view in VIEWS:
        rows = sorted((_row(assertion, selection)
                       for assertion in selection.row_assertions
                       if assertion["predicate"] in _VIEW_PREDICATES[view]),
                      key=_row_sort_key)
        section = {"input_refs": sorted(row["curation_revision"] for row in rows)}
        section["rows"] = rows
        if rows:
            section.update(status="ready",
                           total={"value": None, "reason": "totals_not_computed"})
        else:
            section.update(
                status="unavailable",
                reason="no_manufacturing_evidence" if view == "manufacturing"
                else ("no_selected_assertions" if not selection.assertions
                      else "no_rows_for_view"),
                total={"value": None, "reason": None},
            )
        graph, truncated = _graph(
            [row for row in rows if row["review"]["current"]], selection)
        section["graph"] = graph
        section["limitations"] = ["graph_truncated"] if truncated else []
        if truncated:
            section["status"] = "degraded"
            response_limitations.add("graph_truncated")
        built[view] = section
    start, stop = selection.query.offset, selection.query.offset + selection.query.limit
    for view in VIEWS:
        built[view]["rows"] = built[view]["rows"][start:stop]
        built[view]["input_refs"] = sorted(
            row["curation_revision"] for row in built[view]["rows"])
    return built


def _refuse_unsupported_identity_vintage(selection: _Selection) -> None:
    if selection.query.time_mode != "system_replay":
        return
    labels = {(assertion.get("subject") or {}).get("source_business_label")
              for assertion in selection.assertions}
    for result in selection.bundle.identity_results:
        if result.get("source_business_label") not in labels:
            continue
        learned = result.get("mapping_learned_at")
        if not (isinstance(learned, str) and learned):
            raise ResearchRefusal("identity_vintage_unsupported")


def _compose(query: ResearchQuery, bundle: OwnerBundle) -> dict[str, Any]:
    if query.anchor_theme_id != ANCHOR_THEME_ID:
        raise ResearchRefusal("not_available")
    if query.slice_key not in SLICES:
        raise ResearchRefusal("slice_not_supported")
    if query.view not in VIEWS:
        raise ResearchRefusal("view_not_supported")
    _validate_query(query)
    selection = _Selection(query, bundle)
    generation = selection.generation
    if query.expected_generation is not None \
            and query.expected_generation != generation:
        raise ResearchRefusal("generation_changed")
    _refuse_unsupported_identity_vintage(selection)
    response_limitations = set(selection.limitations)
    views = _views(selection, response_limitations)
    companies = _companies(selection)
    companies["rows"] = companies["rows"][query.offset:query.offset + query.limit]
    coverage_status = "unavailable" if not selection.assertions else (
        "degraded" if bundle.omissions else "ready")
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
        "summary": _summary(selection),
        "companies": companies,
        "industrial_views": views,
        "economics": {
            "status": "unavailable", "reason": _ECONOMICS_REASON,
            "input_refs": [], "management": None, "witness_gate": "missing",
        },
        "expectations": {
            "management": {"status": "unavailable", "reason": _ECONOMICS_REASON,
                           "input_refs": [], "roles": None},
            "external_consensus": {"status": "unavailable",
                                   "reason": "no_external_consensus"},
            "house_forecast": {"status": "unavailable",
                               "reason": "not_authorized"},
            "market_incorporation": {"status": "unavailable",
                                     "reason": "not_authorized"},
        },
        "evidence_refs": [
            {"assertion_ref": source_ref_for(assertion),
             "curation_revision": assertion["curation_revision"],
             "kind": "assertion"} for assertion in selection.assertions
        ] + [{"owner_store": ref.get("owner_store"),
              "native_identity": copy.deepcopy(ref.get("native_identity")),
              "reference_id": ref.get("reference_id"), "kind": "native"}
             for ref in bundle.native_refs],
        "authorized_coverage": {
            "status": coverage_status,
            "input_refs": sorted(assertion["curation_revision"]
                                 for assertion in selection.assertions),
            "selected": len(selection.assertions),
            "industry_total": None,
            "note": "counts only what this principal may know exists",
        },
        "limitations": sorted(response_limitations),
        "authority": dict(AUTHORITY),
    }


def compose_nuclear_research(query: ResearchQuery,
                             bundle: OwnerBundle) -> dict[str, Any]:
    return _compose(query, bundle)


def _correction_lineage(assertion: Mapping[str, Any],
                        bundle: OwnerBundle) -> list[str]:
    by_revision = {item.get("curation_revision"): item
                   for item in bundle.assertions if isinstance(item, Mapping)}
    lineage, seen = [], {assertion.get("curation_revision")}
    current = assertion
    while True:
        prior = (current.get("correction") or {}).get("predecessor_revision")
        if not isinstance(prior, str) or not prior or prior in seen:
            break
        predecessor = by_revision.get(prior)
        if predecessor is None:
            prefix = source_ref_for(current).rsplit("/", 1)[0]
            lineage.append(f"{prefix}/{prior}")
            break
        seen.add(prior)
        lineage.append(source_ref_for(predecessor))
        current = predecessor
    return lineage


def select_authorized_evidence(query: ResearchQuery, bundle: OwnerBundle,
                               assertion_ref: str) -> dict[str, Any]:
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
