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

# Research-only microtheme member/activity review; no graph or proposal writes.
MICRO_RESEARCH_SCHEMA = "gmi.microtheme_membership_research/v1"
MICRO_REVIEW_SCHEMA = "gmi.microtheme_membership_review/v1"
MICRO_STAGES = frozenset({
    "CAPABILITY_EVIDENCE", "COMMERCIAL_EVIDENCE", "CONTRACT_EVIDENCE",
    "DEVELOPMENT_EVIDENCE", "OFFERED_PRODUCT", "SCOPE_REVIEW",
})
MICRO_AUTHORITY = frozenset({
    "canonical_membership", "taxonomy_mutation", "ranking", "gating",
    "sizing", "trading", "candidate_insertion", "production_publication",
})


def _micro_refuse(reason: str) -> None:
    raise ValueError("microtheme research refused: " + reason)


def _micro_string(value, what):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        _micro_refuse("invalid " + what)
    return value


def _micro_exact_fields(row, allowed, family):
    if not isinstance(row, Mapping) or set(row) != set(allowed.split()):
        _micro_refuse(f"unexpected or missing {family} fields")


def build_microtheme_research_evidence(
    document: Mapping[str, Any], *, crosswalk_path: Path | None = None
) -> dict[str, Any]:
    """Structural review of existing micro IDs and unadmitted research roles.

    This reads a single pinned crosswalk file for identity equality; it never
    opens graph/market data, fetches URLs, appends proposals or issues signals.
    """
    import datetime as dt
    import ipaddress
    import re
    from urllib.parse import urlsplit
    import yaml

    if not isinstance(document, Mapping) or document.get("schema") != MICRO_RESEARCH_SCHEMA:
        _micro_refuse("unsupported research document")
    if document.get("artifact_role") != "IMMUTABLE_RESEARCH_DOCUMENT_NOT_RUNTIME_REGISTRY" or document.get("owner") != "WS:GMI-THEME-GRAPH":
        _micro_refuse("document role or owner mismatch")
    _micro_exact_fields(document, "schema artifact_role owner operation commission_date compiled_at authority source_pin population sources microthemes subthemes candidates negative_cases cpu_scope_review limitations", "root research")
    authority = document.get("authority")
    if not isinstance(authority, Mapping) or set(authority) != MICRO_AUTHORITY or any(x is not False for x in authority.values()):
        _micro_refuse("document claims or alters authority")
    try:
        compiled = dt.datetime.fromisoformat(document["compiled_at"].replace("Z", "+00:00"))
        if compiled.utcoffset() is None:
            raise ValueError()
        commission = dt.date.fromisoformat(document["commission_date"])
        if commission.isoformat() != document["commission_date"]:
            raise ValueError()
    except (ValueError, TypeError, KeyError, AttributeError):
        _micro_refuse("invalid research or commission timestamp")
    if compiled.astimezone(dt.timezone.utc) > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
        _micro_refuse("research compilation is future dated")
    if commission > compiled.date():
        _micro_refuse("commission date follows compilation")
    _micro_string(document.get("operation"), "operation")
    limits = document.get("limitations")
    if not isinstance(limits, list) or not limits:
        _micro_refuse("missing source limitations")
    for limit in limits:
        _micro_string(limit, "source limitation")

    pin = document.get("source_pin")
    if not isinstance(pin, Mapping) or pin.get("repository") != "mastermindx-market-intelligence/macro" or pin.get("crosswalk_path") != "config/theme_crosswalk.yml":
        _micro_refuse("unbound incumbent source")
    _micro_exact_fields(pin, "repository commit crosswalk_path crosswalk_blob initial_research_snapshot crosswalk_sha256 protected_procedure_commit", "source pin")
    # SHA-shaped declarations are not commit-authenticity proof; the
    # independently verified crosswalk bytes are the local source fence.
    for key in ("commit", "crosswalk_blob", "protected_procedure_commit", "initial_research_snapshot"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(pin.get(key, ""))):
            _micro_refuse("malformed source pin")
    if not re.fullmatch(r"[0-9a-f]{64}", str(pin.get("crosswalk_sha256", ""))):
        _micro_refuse("malformed source digest")
    path = Path(crosswalk_path) if crosswalk_path is not None else ROOT / "config/theme_crosswalk.yml"
    try:
        raw = path.read_bytes()
        hierarchy = yaml.safe_load(raw)["hierarchy"]
        micro_rows, sub_rows, edges = (hierarchy["micro_themes"], hierarchy["sub_themes"], hierarchy["parents"])
    except (OSError, KeyError, ValueError, TypeError, yaml.YAMLError):
        _micro_refuse("pinned house hierarchy unavailable")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if pin["crosswalk_sha256"] != hashlib.sha256(raw).hexdigest() or pin["crosswalk_blob"] != blob:
        _micro_refuse("crosswalk bytes differ from research pin")
    micro_ids = {x["id"] for x in micro_rows}
    sub_ids = {x["id"] for x in sub_rows}
    if len(micro_ids) != len(micro_rows) or len(sub_ids) != len(sub_rows):
        _micro_refuse("ambiguous incumbent taxonomy")
    definitions, subthemes, candidates = (
        document.get("microthemes"), document.get("subthemes"), document.get("candidates")
    )
    if not isinstance(definitions, list) or len(definitions) != len(micro_ids):
        _micro_refuse("incomplete micro definitions")
    if not isinstance(subthemes, list) or len(subthemes) != len(sub_ids):
        _micro_refuse("intermediate subtheme tier not reconciled")
    if not isinstance(candidates, list):
        _micro_refuse("candidate list unavailable")
    seen = set()
    for row in definitions:
        if not isinstance(row, Mapping):
            _micro_refuse("nonobject definition")
        _micro_exact_fields(row, "micro_id name parent_theme_ids parent_subtheme_ids activity_facets inclusion_predicate exclusion_predicate next_evidence_gate predicate_authority canonical_definition_modified membership_population_complete", "micro definition")
        micro = row.get("micro_id")
        if micro not in micro_ids or micro in seen:
            _micro_refuse("invented or duplicate micro ID")
        seen.add(micro)
        parents = sorted(e["parent"] for e in edges if e["child"] == micro)
        theme_paths, sub_paths = row.get("parent_theme_ids"), row.get("parent_subtheme_ids")
        if not isinstance(theme_paths, list) or not isinstance(sub_paths, list):
            _micro_refuse("micro parent paths must be lists")
        if any(not isinstance(x, str) for x in theme_paths + sub_paths):
            _micro_refuse("micro parent IDs must be strings")
        supplied = sorted(theme_paths + sub_paths)
        facets = row.get("activity_facets")
        if not isinstance(facets, list) or not facets:
            _micro_refuse("activity facets missing")
        for facet in facets:
            _micro_string(facet, "activity facet")
        if parents != supplied:
            _micro_refuse("micro parent relations conflict with incumbent crosswalk")
        if row.get("canonical_definition_modified") is not False or row.get("membership_population_complete") is not False or row.get("predicate_authority") != "MODEL_PROPOSED_REVIEW_CRITERIA":
            _micro_refuse("micro definition overclaims admission")
        for key in ("name", "inclusion_predicate", "exclusion_predicate", "next_evidence_gate"):
            _micro_string(row.get(key), "micro " + key)
    seen.clear()
    for row in subthemes:
        if not isinstance(row, Mapping) or row.get("node_id") not in sub_ids or row["node_id"] in seen:
            _micro_refuse("invented or duplicate intermediate subtheme")
        _micro_exact_fields(row, "node_id name value_chain_position children", "subtheme")
        seen.add(row["node_id"])
        _micro_string(row.get("name"), "subtheme name")
        if not isinstance(row.get("children"), list) or any(not isinstance(x, str) for x in row["children"]):
            _micro_refuse("subtheme children must be string IDs")
        own = next(x for x in sub_rows if x["id"] == row["node_id"])
        children = sorted(e["child"] for e in edges if e["parent"] == row["node_id"])
        if children != row.get("children") or own.get("value_chain_position") != row.get("value_chain_position"):
            _micro_refuse("intermediate subtheme content diverges from crosswalk")

    sources = document.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        _micro_refuse("source register unavailable")
    for sid, source in sources.items():
        if not isinstance(sid, str) or not re.fullmatch(r"S[0-9]{3,6}", sid) or not isinstance(source, Mapping):
            _micro_refuse("malformed source entry")
        _micro_exact_fields(source, "publisher url published_on publication_precision supported_observation evidence_basis retrieval_scope full_document_archived body_sha256 first_observed_at catalogued_at rights_use_qualification limitation", "source")
        if source.get("evidence_basis") != "PRIMARY_SOURCE_RESEARCH_REFERENCE" or source.get("retrieval_scope") != "SEARCH_EXTRACT_OR_SELECTED_PAGE_READ" or source.get("first_observed_at") is not None:
            _micro_refuse("source falsely upgrades observation proof")
        url = _micro_string(source.get("url"), "source URL")
        try:
            parts = urlsplit(url)
            host = (parts.hostname or "").lower()
            if parts.scheme != "https" or parts.username or parts.password or parts.port not in (None, 443):
                _micro_refuse("source URL is not public HTTPS")
        except ValueError:
            _micro_refuse("malformed source URL")
        if not host or host in ("localhost",) or host.endswith((".local", ".internal", ".localhost")):
            _micro_refuse("private source hostname")
        try:
            addr = ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not addr.is_global:
                _micro_refuse("nonpublic source address")
        if any(x.isspace() for x in url) or any(x in url for x in "<>\\"):
            _micro_refuse("unsafe source URL")
        _micro_string(source.get("supported_observation"), "source observation")
        _micro_string(source.get("publisher"), "source publisher")
        _micro_string(source.get("limitation"), "source limitation")
        try:
            catalogued = dt.datetime.fromisoformat(source["catalogued_at"].replace("Z", "+00:00"))
            if catalogued.utcoffset() is None:
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError):
            _micro_refuse("invalid source cataloguing clock")
        if catalogued > compiled:
            _micro_refuse("source catalogue postdates compilation")
        if source.get("rights_use_qualification") != "NOT_PERFORMED" or source.get("full_document_archived") is not False or source.get("body_sha256") is not None:
            _micro_refuse("unsupported source authenticity or rights claim")
        published, precision = source.get("published_on"), source.get("publication_precision")
        if precision == "UNKNOWN":
            if published is not None:
                _micro_refuse("unknown publication precision falsely dated")
        elif precision == "YEAR":
            if not isinstance(published, str) or not re.fullmatch(r"[12][0-9]{3}", published) or int(published) > min(compiled.year, catalogued.year):
                _micro_refuse("invalid source publication year")
        elif precision == "DAY":
            try:
                date = dt.date.fromisoformat(published)
            except (ValueError, TypeError):
                _micro_refuse("invalid publication day")
            if date.isoformat() != published or date > min(compiled.date(), catalogued.date()):
                _micro_refuse("future-dated source")
        else:
            _micro_refuse("invalid source precision")

    stage_counts, seen = defaultdict(int), set()
    for row in candidates:
        if not isinstance(row, Mapping):
            _micro_refuse("nonobject candidate")
        _micro_exact_fields(row, "record_id micro_id entity_name issuer_name_hint product_or_activity role stage source_ids qualification_note proposed_by admission_status canonical_entity_id canonical_security_id identity_status valid_from valid_to admitted_at current_operation_asserted economic_share measurement_eligible", "candidate")
        rid = row.get("record_id")
        if not isinstance(rid, str) or not re.fullmatch(r"M[0-9]{3,6}", rid) or rid in seen:
            _micro_refuse("duplicate or malformed candidate record ID")
        seen.add(rid)
        if row.get("micro_id") not in micro_ids or row.get("stage") not in MICRO_STAGES:
            _micro_refuse("unadmitted micro ID or evidence stage")
        if row.get("proposed_by") != "llm_proposed" or row.get("admission_status") != "UNADMITTED_RESEARCH" or row.get("identity_status") != "NOT_QUALIFIED":
            _micro_refuse("research candidate claims owner identity or admission")
        if any(row.get(key) is not None for key in (
            "canonical_entity_id", "canonical_security_id", "valid_from", "valid_to", "admitted_at", "economic_share"
        )):
            _micro_refuse("candidate contains unadmitted identity, time or economic claims")
        if row.get("measurement_eligible") is not False or row.get("current_operation_asserted") is not False:
            _micro_refuse("candidate asserts measurement or operational authority")
        for key in ("entity_name", "product_or_activity", "role", "qualification_note"):
            _micro_string(row.get(key), "candidate " + key)
        if row.get("issuer_name_hint") is not None:
            _micro_string(row.get("issuer_name_hint"), "issuer hint")
        refs = row.get("source_ids")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs) or len(set(refs)) != len(refs) or any(ref not in sources for ref in refs):
            _micro_refuse("candidate source references incomplete or duplicate")
        stage_counts[row["stage"]] += 1
    for key in ("negative_cases", "cpu_scope_review"):
        group = document.get(key)
        if not isinstance(group, list) or not group:
            _micro_refuse(key + " absent")
        seen_ids = set()
        for row in group:
            if not isinstance(row, Mapping):
                _micro_refuse("nonobject " + key)
            _micro_exact_fields(row, ("case_id micro_id unsupported_inference research_disposition source_ids adjudication" if key == "negative_cases" else "label entity_name activity source_ids note canonical_micro_id admission_status measurement_eligible"), key)
            refs = row.get("source_ids")
            if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs) or any(ref not in sources for ref in refs):
                _micro_refuse("unlinked negative or scope reference")
            if key == "negative_cases":
                case_id = row.get("case_id")
                if not isinstance(case_id, str) or not re.fullmatch(r"N[0-9]{2,6}", case_id):
                    _micro_refuse("malformed negative case ID")
                for field in ("unsupported_inference", "research_disposition"):
                    _micro_string(row.get(field), "negative " + field)
                if case_id in seen_ids or row.get("micro_id") not in micro_ids or row.get("adjudication") != "MODEL_AUTHORED_REVIEW_CASE_NOT_HUMAN_GOLD_LABEL":
                    _micro_refuse("negative case overclaims adjudication")
                seen_ids.add(case_id)
            else:
                for field in ("label", "entity_name", "activity", "note"):
                    _micro_string(row.get(field), "CPU scope " + field)
                if row.get("canonical_micro_id") is not None or row.get("admission_status") != "SCOPE_REVIEW_ONLY" or row.get("measurement_eligible") is not False:
                    _micro_refuse("CPU scope item overclaims admission")
    population = document.get("population")
    if not isinstance(population, Mapping) or population.get("complete_global_membership") is not False:
        _micro_refuse("unverified population completeness")
    _micro_exact_fields(population, "definition micro_definitions subtheme_definitions parent_relationships candidate_activity_records source_references source_stage_counts complete_global_membership canonical_memberships_admitted dataos_identities_qualified measurement_cohorts_admitted", "population")
    _micro_string(population.get("definition"), "population definition")
    numeric = {
        "micro_definitions": len(definitions), "subtheme_definitions": len(subthemes),
        "parent_relationships": len(edges), "candidate_activity_records": len(candidates),
        "source_references": len(sources), "canonical_memberships_admitted": 0,
        "dataos_identities_qualified": 0, "measurement_cohorts_admitted": 0,
    }
    if any(type(population.get(k)) is not int or population[k] != v for k, v in numeric.items()) or population.get("source_stage_counts") != dict(sorted(stage_counts.items())):
        _micro_refuse("population denominators or admission state conflict with source records")
    try:
        encoded = json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError):
        _micro_refuse("nonfinite research JSON")
    return dict(
        schema=MICRO_REVIEW_SCHEMA, operation=document["operation"],
        availability={"state": "STRUCTURALLY_REVIEWABLE_NOT_ADMITTED",
                      "reason": "Source authentication, Data OS identities and curation admission not established"},
        authority_ceiling="research_internal_only", authority=dict(authority),
        source_pin=dict(pin), counts=dict(numeric, source_stage_counts=dict(sorted(stage_counts.items())),
                                          negative_cases=len(document["negative_cases"]),
                                          cpu_scope_reviews=len(document["cpu_scope_review"])),
        source_digest=hashlib.sha256(encoded.encode()).hexdigest(),
        sources=copy.deepcopy(dict(sources)), microthemes=copy.deepcopy(definitions),
        subthemes=copy.deepcopy(subthemes), candidates=copy.deepcopy(candidates),
        negative_cases=copy.deepcopy(document["negative_cases"]),
        cpu_scope_review=copy.deepcopy(document["cpu_scope_review"]),
        limitations=[
            "Model-authored company/product roles are research, not independently adjudicated membership.",
            "Source links are not fetched, authenticated or rights-certified by this parser.",
            "An operating-business hint does not resolve a legal issuer, listing or corporate event.",
            "Parent paths are context, not multiple issuers, weights, forecasts or trading signals.",
            "No graph, membership, probation, score, identity, state or production write occurs.",
            "Source commits are unverified declarations; local byte checks bind only the crosswalk.",
        ]
    )


def render_microtheme_research_markdown(report: Mapping[str, Any]) -> str:
    """Render escaped human review with source references, never an authority card."""
    import html
    from urllib.parse import quote
    def clean(value):
        return html.escape(str(value if value is not None else "unresolved"), quote=True).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")
    c = report["counts"]
    lines = [
        "# GMI microtheme membership — research review", "",
        "UNADMITTED RESEARCH. Zero new graph memberships or trading authority.", "",
        f"{c['micro_definitions']} microthemes, {c['subtheme_definitions']} intermediate subthemes, "
        f"{c['parent_relationships']} parent relations; {c['candidate_activity_records']} researched activities; "
        f"{c['source_references']} primary-source references.", "",
        "Data OS-qualified issuer identities: 0. Canonical memberships: 0. Admitted measurement cohorts: 0.", "",
        "| Micro | Business | Product/activity | Economic role | Stage | Sources |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["candidates"]:
        refs = ", ".join(
            "[" + clean(sid) + "](" + quote(report["sources"][sid]["url"], safe="/:?&=#%+@-._~") + ")"
            for sid in row["source_ids"]
        )
        lines.append("| " + " | ".join([
            clean(row["micro_id"]), clean(row["entity_name"]), clean(row["product_or_activity"]),
            clean(row["role"]), clean(row["stage"]), refs,
        ]) + " |")
    lines.extend(["", "## Hard-negative research cases", "",
                  "| Micro | Unsupported inference | Exclusion |",
                  "| --- | --- | --- |"])
    for row in report["negative_cases"]:
        lines.append("| " + " | ".join([
            clean(row["micro_id"]), clean(row["unsupported_inference"]),
            clean(row["research_disposition"]),
        ]) + " |")
    lines.extend(["", "## CPU scope — NOT admitted as an existing micro", ""])
    for row in report["cpu_scope_review"]:
        lines.append("- " + clean(row["entity_name"]) + ": " + clean(row["activity"]) + " — " + clean(row["note"]))
    lines.extend(["", "## Reader limitations", ""])
    lines.extend("- " + clean(x) for x in report["limitations"])
    lines.extend(["", "Research document digest: " + report["source_digest"], ""])
    return "\n".join(lines)


# Source-local identity *diagnostic* for the M1 admission worklist.
# The Data OS IssuerMaster remains the sole authority for CURRENT issuer-security
# relationships. A legal-name match here is never an issuer binding, even when unique.
MICRO_IDENTITY_PREFLIGHT_SCHEMA = "gmi.microtheme_identity_preflight/v1"


def build_microtheme_identity_preflight(
    research: Mapping[str, Any],
    *,
    issuer_rows: list[dict],
    security_rows: list[dict],
    issuer_snapshot_sha256: str,
    security_snapshot_sha256: str,
    crosswalk_path: Path | None = None,
) -> dict[str, Any]:
    """Diagnose CURRENT issuer-name hints without minting memberships.

    The caller supplies actual Data OS reference rows, not a second name registry.
    Qualifying real issuer/security/listing identity, clocks and semantic roles
    remains with the original Data OS and GMI owners. No network or file writes.
    """
    import re

    from lib.dataos.identity import IssuerMaster

    base = build_microtheme_research_evidence(research, crosswalk_path=crosswalk_path)
    if any(not isinstance(v, str) or re.fullmatch(r"[0-9a-f]{64}", v) is None
           for v in (issuer_snapshot_sha256, security_snapshot_sha256)):
        _micro_refuse("unbound identity reference digest")
    if not isinstance(issuer_rows, list) or not isinstance(security_rows, list):
        _micro_refuse("identity references must be record lists")
    if not issuer_rows or not security_rows:
        _micro_refuse("identity reference rows unavailable")

    try:
        owner = IssuerMaster.from_records(security_rows)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("microtheme identity preflight: Data OS owner reader refused") from exc

    # Current active-issuer source row is a *search candidate*, not a way to
    # resolve a ticker. Only the incumbent owner determines the existing
    # currently active security roster; duplicate issuer records fail closed.
    index: list[tuple[tuple[str, ...], dict[str, Any]]] = []
    seen_issuers: set[str] = set()
    omitted_active_names = 0
    for row in issuer_rows:
        if not isinstance(row, Mapping):
            _micro_refuse("invalid issuer reference row")
        issuer_id, legal_name = row.get("issuer_id"), row.get("legal_name")
        if not isinstance(issuer_id, str) or not issuer_id.startswith("ISS:") or issuer_id in seen_issuers:
            _micro_refuse("duplicated or malformed current issuer id")
        if legal_name is not None and (not isinstance(legal_name, str) or not legal_name.strip()):
            _micro_refuse("malformed source legal name")
        seen_issuers.add(issuer_id)
        if row.get("status") != "active":
            continue
        if legal_name is None:
            # Real Data OS current issuer reference contains legally unnamed
            # active rows. Exclude from prefix matching, never fabricate a name.
            omitted_active_names += 1
            continue
        security_ids = owner.securities_of_issuer(issuer_id)
        if not security_ids:
            continue
        index.append((
            tuple(re.findall(r"[^\W_]+", legal_name.casefold())),
            {"issuer_id": issuer_id, "legal_name": legal_name,
             "current_security_count": len(security_ids)},
        ))

    if not index:
        _micro_refuse("no current issuers with incumbent eligible securities")
    counts = {
        "POSSIBLE_ONE_CURRENT_ISSUER": 0,
        "NO_NAME_PREFIX_IN_REFERENCE": 0,
        "AMBIGUOUS_NAME_PREFIX": 0,
        "UNUSABLE_NAME_HINT": 0,
    }
    entries: list[dict[str, Any]] = []
    for row in base["candidates"]:
        hint = row.get("issuer_name_hint")
        words = tuple(re.findall(r"[^\W_]+", hint.casefold())) if isinstance(hint, str) else ()
        # Multi-company conjunctions are not legal issuers. No fuzzy fallback:
        # "AMD" must NOT match the letters buried in "Camden".
        usable = (isinstance(hint, str) and bool(words) and len(words[0]) >= 3
                  and "/" not in hint and " and " not in hint.casefold())
        matches = [
            dict(candidate)
            for legal, candidate in index
            if usable and legal[:len(words)] == words
        ]
        matches.sort(key=lambda item: item["issuer_id"])
        state = (
            "UNUSABLE_NAME_HINT" if not usable else
            "POSSIBLE_ONE_CURRENT_ISSUER" if len(matches) == 1 else
            "AMBIGUOUS_NAME_PREFIX" if len(matches) > 1 else
            "NO_NAME_PREFIX_IN_REFERENCE"
        )
        counts[state] += 1
        entries.append({
            "record_id": row["record_id"], "micro_id": row["micro_id"],
            "entity_name": row["entity_name"], "issuer_name_hint": hint,
            "identity_hint_state": state, "possible_current_issuer_refs": matches,
            "legal_entity_qualification": "NOT_PERFORMED",
            "canonical_membership_admitted": False,
            "measurement_eligible": False,
        })
    countries = sorted({
        row.get("country") for row in security_rows
        if isinstance(row, Mapping) and isinstance(row.get("country"), str)
    })
    return {
        "schema": MICRO_IDENTITY_PREFLIGHT_SCHEMA,
        "authority_ceiling": "internal_research_candidate_triage_only",
        "availability": {
            "state": "CURRENT_SOURCE_HINTS_ONLY_NOT_ADMITTED",
            "reason": "Name-prefix hints are not Data OS identity proof or product-role curation.",
        },
        "research_source_digest": base["source_digest"],
        "reference": {
            "issuer_snapshot_sha256": issuer_snapshot_sha256,
            "security_snapshot_sha256": security_snapshot_sha256,
            "basis": "CALLER_SUPPLIED_DATAOS_REFERENCE_BYTES_NOT_INDEPENDENTLY_AUTHENTICATED",
            "point_in_time_issuer_history_available": False,
            "covered_country_codes": countries,
            "current_issuer_rows_without_legal_name": omitted_active_names,
        },
        "counts": {
            "activity_records": len(entries),
            "micro_definitions": base["counts"]["micro_definitions"],
            "identity_hint_states": counts,
            "canonical_memberships_admitted": 0,
            "dataos_identities_qualified_for_micro": 0,
            "measurement_cohorts_admitted": 0,
        },
        "candidate_diagnostics": entries,
        "limitations": [
            "Whole-token legal-name prefixes are discovery cues only, never binding evidence.",
            "Current Data OS reference lacks complete global issuer coverage and historical lineage.",
            "Current identity readers do not qualify source rights, economic activity or product stage.",
            "No graph, company theme edge, basket, membership, signal, weight or trade is emitted.",
        ],
    }


def render_microtheme_identity_preflight_markdown(report: Mapping[str, Any]) -> str:
    """Escaped, deliberately non-actionable owner triage view."""
    import html

    def clean(value):
        return html.escape(str(value if value is not None else "unknown"), quote=True).replace("|", "&#124;").replace("\n", " ")

    counts = report["counts"]
    lines = [
        "# GMI identity reference preflight — NOT ADMITTED",
        "",
        "Current source-local legal-name hints only; qualified identities, memberships and weights: zero.",
        "",
        f"Investigated {counts['activity_records']} candidate activities across {counts['micro_definitions']} micros.",
        "",
        "| Micro | Research candidate | Possible current issuers | Diagnostic |",
        "| --- | --- | --- | --- |",
    ]
    for entry in report["candidate_diagnostics"]:
        issuer_names = ", ".join(x["issuer_id"] for x in entry["possible_current_issuer_refs"])
        lines.append("| " + " | ".join((
            clean(entry["micro_id"]), clean(entry["entity_name"]),
            clean(issuer_names or "none"), clean(entry["identity_hint_state"]),
        )) + " |")
    lines.extend(["", "## Refusal ceiling", ""])
    lines.extend("- " + clean(x) for x in report["limitations"])
    lines.append("")
    return "\n".join(lines)
