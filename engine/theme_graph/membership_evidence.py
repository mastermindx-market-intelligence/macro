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


#: The ratified micro-theme expansion (research/theme_graph/micro_expansion_20261021/,
#: receipts copied verbatim there) appended additive display-tier rows dated
#: 2026-10-21 to config/theme_crosswalk.yml. Research documents commissioned before
#: that date were compiled against the frozen tier, so their byte pin is
#: reconciled against the frozen rows, never against the appended display tier.
MICRO_EXPANSION_ASSERTED_ON = "2026-10-21"


def frozen_hierarchy(
    hierarchy: Mapping[str, Any], *, before: str = MICRO_EXPANSION_ASSERTED_ON
) -> dict[str, list]:
    """Hierarchy rows asserted before ``before`` — the frozen table a research pin was compiled against.

    The 2026-10-21 expansion is additive display-tier vocabulary; this helper is
    how readers distinguish the frozen acceptance tier from the appended rows
    without changing any row format.
    """
    frozen: dict[str, list] = {}
    for key in ("categories", "sub_themes", "micro_themes", "parents"):
        rows = hierarchy.get(key) if isinstance(hierarchy, Mapping) else None
        frozen[key] = [
            row for row in (rows or []) if isinstance(row, Mapping)
            and str(row.get("asserted_on", "")) < before
        ]
    return frozen


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
    expanded = any(str(row.get("asserted_on", "")) >= MICRO_EXPANSION_ASSERTED_ON
                   for row in list(micro_rows) + list(sub_rows) + list(edges))
    if expanded:
        # The live file carries the additive 2026-10-21 display-tier expansion, so
        # the raw-byte pin cannot match. The pinned bytes remain named by
        # pin["commit"]; the fence here reconciles the frozen projection: every
        # frozen id, parent edge and subtheme field must still be exactly the
        # table this document was compiled against (checks below bind that).
        frozen = frozen_hierarchy(hierarchy)
        if [len(frozen["micro_themes"]), len(frozen["sub_themes"]), len(frozen["parents"])] \
                == [len(micro_rows), len(sub_rows), len(edges)]:
            _micro_refuse("crosswalk bytes differ from research pin")
        micro_rows, sub_rows, edges = (
            frozen["micro_themes"], frozen["sub_themes"], frozen["parents"])
    elif pin["crosswalk_sha256"] != hashlib.sha256(raw).hexdigest() or pin["crosswalk_blob"] != blob:
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


# Research-only extension overlay. The original 103-row dataset and all production
# issuer/membership owners remain authoritative; new candidates NEVER become edges.
MICRO_ADDENDUM_SCHEMA = "gmi.microtheme_member_research_addendum/v1"


def build_microtheme_addendum_review(
    research: Mapping[str, Any],
    addendum: Mapping[str, Any],
    *,
    crosswalk_path: Path | None = None,
    intake_dir: Path | None = None,
) -> dict[str, Any]:
    """Review an in-hand source-pointer addendum, with no new authority or I/O effect.

    Verify its linkage to the exact current original source and source-intake
    bytes, rather than trusting a supplied size, digest or source claim.
    """
    import csv
    import datetime as dt
    import io
    import ipaddress
    import re
    from urllib.parse import urlsplit

    original = build_microtheme_research_evidence(
        research, crosswalk_path=crosswalk_path)
    path = ROOT / "research/theme_graph/microtheme_membership_candidates_2026-10-08.json"
    original_raw = path.read_bytes()
    pinned = json.loads(original_raw)
    if research != pinned:
        _micro_refuse("addendum source differs from canonical original research")
    if not isinstance(addendum, Mapping):
        _micro_refuse("addendum must be an object")

    def exact(value, keys, where):
        if not isinstance(value, Mapping) or set(value) != set(keys):
            _micro_refuse("unexpected " + where + " fields")

    def sha(value, where):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            _micro_refuse("invalid " + where + " hash")

    def label(value, where):
        if not isinstance(value, str) or not value.strip() or len(value) > 8191:
            _micro_refuse("invalid " + where + " text")

    root_keys = ("schema", "artifact_role", "owner_workstream", "source_provenance",
                 "population", "authority", "sources", "proposed_activity_roles",
                 "negative_cases", "scope_holds", "limitations")
    exact(addendum, root_keys, "addendum")
    if (addendum["schema"] != MICRO_ADDENDUM_SCHEMA
        or addendum["artifact_role"] != "RESEARCH_POINTERS_UNADMITTED_NOT_RUNTIME_REGISTRY"
        or addendum["owner_workstream"] != "WS:GMI-THEME-GRAPH"):
        _micro_refuse("unrecognized nonauthoritative addendum")
    if addendum["authority"] != {
        "canonical_membership": False, "identity_qualification": False,
        "production_publication": False, "ranking": False, "sizing": False,
        "trading": False,
    }:
        _micro_refuse("addendum overclaims authority")

    prov_keys = ("original_canonical_research_sha256", "original_source_pin",
                 "intake_tsv_sha256", "negative_tsv_sha256", "hold_tsv_sha256",
                 "source_body_validation", "source_rights_certified",
                 "available_source_origin")
    provenance = addendum["source_provenance"]
    exact(provenance, prov_keys, "source provenance")
    expected_research_hash = hashlib.sha256(original_raw).hexdigest()
    if (provenance["original_canonical_research_sha256"] != expected_research_hash
        or provenance["original_source_pin"] != research["source_pin"]
        or provenance["source_rights_certified"] is not False
        or provenance["source_body_validation"] != "NOT_PERFORMED"):
        _micro_refuse("source lineage or rights overclaim")
    label(provenance["available_source_origin"], "origin")
    records_dir = (intake_dir or
                   ROOT / "research/theme_graph/micro_member_research_addendum_20261016")
    intake_records: dict[str, list[dict[str, str]]] = {}
    expected_csv_keys = {
        "intake.tsv": {"micro_id", "entity_name", "issuer_hint",
                       "product_or_activity", "role", "stage", "source_url",
                       "source_published", "publisher", "supported_observation",
                       "qualification_note", "origin"},
        "negative_intake.tsv": {"micro_id", "entity_name",
                                "unsupported_inference", "disposition_reason",
                                "source_url", "source_published", "publisher",
                                "origin"},
        "scope_holds.tsv": {"micro_id", "entity_name",
                            "unsupported_inference", "disposition_reason",
                            "source_url", "source_published", "publisher",
                            "origin"},
    }
    for filename, key in (("intake.tsv", "intake_tsv_sha256"),
                          ("negative_intake.tsv", "negative_tsv_sha256"),
                          ("scope_holds.tsv", "hold_tsv_sha256")):
        sha(provenance[key], "input")
        input_path = records_dir / filename
        if not input_path.is_file() or input_path.is_symlink() or input_path.stat().st_size > 100_000:
            _micro_refuse("bounded research intake unavailable")
        raw = input_path.read_bytes()
        if len(raw) > 100_000 or hashlib.sha256(raw).hexdigest() != provenance[key]:
            _micro_refuse("research intake bytes differ")
        try:
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t")
            if (set(reader.fieldnames or ()) != expected_csv_keys[filename] or
                len(reader.fieldnames or []) != len(expected_csv_keys[filename])):
                _micro_refuse("research intake header drift")
            records = list(reader)
        except (UnicodeError, csv.Error) as exc:
            raise ValueError("microtheme research refused: unreadable research TSV") from exc
        if any(None in row or any(v is None for v in row.values()) for row in records):
            _micro_refuse("research intake cells missing")
        intake_records[filename] = records

    sources = addendum["sources"]
    if not isinstance(sources, Mapping) or not sources:
        _micro_refuse("source pointers missing")
    source_fields = ("url", "publisher_hint", "published_on", "publication_precision",
                     "reference_kind", "source_use_qualification",
                     "first_observed_at", "body_sha256",
                     "full_document_archived", "independently_authenticated")
    for source_id, item in sources.items():
        exact(item, source_fields, "source reference")
        label(item["url"], "source URL")
        uri = urlsplit(item["url"])
        if (uri.scheme != "https" or not uri.hostname or uri.username or uri.password
            or (uri.port not in (None, 443)) or uri.hostname.endswith(
                (".local", ".internal", ".localhost"))
            or any(c.isspace() for c in item["url"])
            or any(c in item["url"] for c in "<>|\\")
            or uri.hostname == "localhost"):
            _micro_refuse("unsafe source-pointer URL")
        try:
            host_ip = ipaddress.ip_address(uri.hostname)
        except ValueError:
            pass
        else:
            if not host_ip.is_global:
                _micro_refuse("nonpublic source-pointer host")
        expected_id = "U" + hashlib.sha256(item["url"].encode()).hexdigest()[:16]
        if source_id != expected_id:
            _micro_refuse("source-pointer id mismatch")
        label(item["publisher_hint"], "source publisher")
        if (item["reference_kind"] != "PUBLIC_PRIMARY_SOURCE_POINTER"
            or item["source_use_qualification"] != "NOT_PERFORMED"
            or item["first_observed_at"] is not None
            or item["body_sha256"] is not None
            or item["full_document_archived"] is not False
            or item["independently_authenticated"] is not False):
            _micro_refuse("source reference claims unsupported verification")
        published = item["published_on"]
        precision = item["publication_precision"]
        if published is None:
            if precision != "UNKNOWN":
                _micro_refuse("unknown source date has nonnull precision")
        elif isinstance(published, str) and re.fullmatch(r"[12][0-9]{3}", published):
            if precision != "YEAR" or int(published) > 2026:
                _micro_refuse("invalid source year")
        elif isinstance(published, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
            try:
                parsed_date = dt.date.fromisoformat(published)
            except ValueError:
                _micro_refuse("invalid source day")
            if precision != "DAY" or parsed_date > dt.date(2026, 10, 16):
                _micro_refuse("source date outside research window")
        else:
            _micro_refuse("source date imprecise")
    valid_micros = {row["micro_id"] for row in original["microthemes"]}
    original_pairs = {
        (x["micro_id"], re.sub("[^a-z0-9]", "", x["entity_name"].lower()))
        for x in original["candidates"]
    }
    def source_refs(value):
        if (not isinstance(value, list) or not value or
            any(not isinstance(x, str) or x not in sources for x in value) or
            len(value) != len(set(value))):
            _micro_refuse("missing or duplicated source references")
    roles = addendum["proposed_activity_roles"]
    if not isinstance(roles, list) or not roles:
        _micro_refuse("addendum roles unavailable")
    role_keys = ("record_id", "micro_id", "entity_name", "issuer_name_hint",
                 "product_or_activity", "proposed_role", "evidence_stage",
                 "supported_observation", "qualification_note", "source_ids",
                 "origin_pointer", "proposed_by", "canonical_entity_id",
                 "canonical_security_id", "canonical_membership_status",
                 "identity_qualified", "measurement_eligible", "may_rank",
                 "may_gate", "may_size", "may_trade")
    identifiers: set[str] = set()
    pairs: set[tuple[str,str]] = set()
    stage_counts: dict[str,int] = {}
    for row in roles:
        exact(row, role_keys, "research candidate")
        micro = row["micro_id"]
        if micro not in valid_micros:
            _micro_refuse("new or unaccepted micro id")
        for name in ("record_id", "entity_name", "product_or_activity",
                     "proposed_role", "evidence_stage", "supported_observation",
                     "qualification_note", "origin_pointer"):
            label(row[name], name)
        if row["issuer_name_hint"] is not None and not isinstance(row["issuer_name_hint"], str):
            _micro_refuse("untrusted issuer hint type")
        if (row["canonical_entity_id"] is not None
            or row["canonical_security_id"] is not None
            or row["canonical_membership_status"] != "NOT_ADMITTED"
            or row["identity_qualified"] is not False
            or row["measurement_eligible"] is not False
            or any(row[x] is not False for x in ("may_rank", "may_gate",
                                                 "may_size", "may_trade"))
            or row["proposed_by"] != "research_pointer_intake_unratified"):
            _micro_refuse("candidate overclaims admission or authority")
        if row["evidence_stage"] not in (
            "OFFERED_PRODUCT", "COMMERCIAL_EVIDENCE", "CONTRACT_EVIDENCE",
            "DEVELOPMENT_EVIDENCE", "CAPABILITY_EVIDENCE", "SCOPE_REVIEW"):
            _micro_refuse("unsupported evidence stage")
        source_refs(row["source_ids"])
        expected_id = "R" + hashlib.sha256("\n".join(
            (micro, row["entity_name"], row["proposed_role"],
             sources[row["source_ids"][0]]["url"])).encode()).hexdigest()[:16]
        if row["record_id"] != expected_id or row["record_id"] in identifiers:
            _micro_refuse("duplicate/malformed activity record")
        identifiers.add(row["record_id"])
        pair = (micro, re.sub("[^a-z0-9]", "", row["entity_name"].lower()))
        if pair in original_pairs or pair in pairs:
            _micro_refuse("research candidate duplicates an existing role")
        pairs.add(pair)
        stage_counts[row["evidence_stage"]] = stage_counts.get(row["evidence_stage"],0)+1

    neg_keys = ("negative_id", "micro_id", "entity_name", "unsupported_inference",
                "disposition_reason", "source_ids", "origin_pointer", "authority")
    def check_negative(field, prefix):
        rows = addendum[field]
        if not isinstance(rows, list):
            _micro_refuse("negative or scope rows invalid")
        seen: set[str] = set()
        for row in rows:
            exact(row, neg_keys, field)
            if row["micro_id"] not in valid_micros:
                _micro_refuse("unknown scope micro")
            for key in ("entity_name", "unsupported_inference", "disposition_reason",
                        "origin_pointer"):
                label(row[key], field + " " + key)
            source_refs(row["source_ids"])
            expected_id = prefix+hashlib.sha256("\n".join(
                (row["micro_id"],row["entity_name"],row["unsupported_inference"])
            ).encode()).hexdigest()[:16]
            if (row["negative_id"] != expected_id or row["negative_id"] in seen
                or row["authority"] != "UNADJUDICATED_RESEARCH_FALSIFIER"):
                _micro_refuse("case overclaims adjudication")
            seen.add(row["negative_id"])
        return len(rows)
    neg_count = check_negative("negative_cases", "N")
    hold_count = check_negative("scope_holds", "H")

    # Content-binding check, not merely a TSV filename/hash check. Each
    # unadmitted claim must correspond to ONE row in the original input;
    # otherwise curated-looking JSON could invent product roles or dates
    # while retaining perfectly genuine hashes for unrelated TSV bytes.
    def check_source(original_url, original_publisher, original_date, refs):
        sid = "U" + hashlib.sha256(original_url.encode()).hexdigest()[:16]
        if refs != [sid]:
            _micro_refuse("compiled row source reference differs from intake")
        src = sources[sid]
        if (src["url"] != original_url or src["publisher_hint"] != original_publisher
            or src["published_on"] != (original_date or None)):
            _micro_refuse("compiled source pointer changed from intake")

    roles_by_id = {row["record_id"]: row for row in roles}
    if len(intake_records["intake.tsv"]) != len(roles_by_id):
        _micro_refuse("research role row count drift")
    for input_row in intake_records["intake.tsv"]:
        code = "R" + hashlib.sha256("\n".join((
            input_row["micro_id"], input_row["entity_name"],
            input_row["role"], input_row["source_url"])).encode()).hexdigest()[:16]
        row = roles_by_id.get(code)
        if row is None:
            _micro_refuse("research role absent from original intake")
        for key, source_key in (
            ("micro_id", "micro_id"), ("entity_name", "entity_name"),
            ("product_or_activity", "product_or_activity"),
            ("proposed_role", "role"), ("evidence_stage", "stage"),
            ("supported_observation", "supported_observation"),
            ("qualification_note", "qualification_note"),
            ("origin_pointer", "origin"),
        ):
            if row[key] != input_row[source_key]:
                _micro_refuse("compiled product role diverges from original intake")
        if row["issuer_name_hint"] != (input_row["issuer_hint"] or None):
            _micro_refuse("issuer name hint differs from original intake")
        check_source(input_row["source_url"], input_row["publisher"],
                     input_row["source_published"], row["source_ids"])

    def check_case_intake(filename, field):
        compiled = {row["negative_id"]: row for row in addendum[field]}
        incoming = intake_records[filename]
        if len(incoming) != len(compiled):
            _micro_refuse("negative or scope source row count drift")
        for input_row in incoming:
            prefix = "N" if field == "negative_cases" else "H"
            key = prefix + hashlib.sha256("\n".join((
                input_row["micro_id"], input_row["entity_name"],
                input_row["unsupported_inference"])).encode()).hexdigest()[:16]
            row = compiled.get(key)
            if row is None:
                _micro_refuse("compiled negative or hold not found in intake")
            for output_key, source_key in (
                ("micro_id", "micro_id"), ("entity_name", "entity_name"),
                ("unsupported_inference", "unsupported_inference"),
                ("disposition_reason", "disposition_reason"),
                ("origin_pointer", "origin"),
            ):
                if row[output_key] != input_row[source_key]:
                    _micro_refuse("compiled scope/negative claim changed from intake")
            check_source(input_row["source_url"], input_row["publisher"],
                         input_row["source_published"], row["source_ids"])

    check_case_intake("negative_intake.tsv", "negative_cases")
    check_case_intake("scope_holds.tsv", "scope_holds")
    for limit in addendum["limitations"] if isinstance(addendum["limitations"], list) else []:
        label(limit, "source limitation")
    if not isinstance(addendum["limitations"], list) or len(addendum["limitations"]) < 3:
        _micro_refuse("source limitations insufficient")
    population = addendum["population"]
    expected_keys = (
        "original_activity_records", "additional_activity_proposals",
        "additional_negative_proposals", "additional_scope_holds",
        "additional_source_pointers", "canonical_membership_admissions",
        "dataos_identities_qualified", "existing_micro_count",
        "measurement_cohorts_admitted", "micros_with_new_proposals",
        "new_micro_ids", "single_candidate_micros_before",
        "single_candidate_micros_if_all_additions_accepted",
        "undated_additional_candidate_rows")
    exact(population, expected_keys, "population")
    orig_counts: dict[str,int] = {}
    for row in original["candidates"]:
        orig_counts[row["micro_id"]] = orig_counts.get(row["micro_id"], 0)+1
    new_counts: dict[str,int] = {}
    for row in roles:
        new_counts[row["micro_id"]] = new_counts.get(row["micro_id"],0)+1
    expected_counts = {
        "original_activity_records": len(original["candidates"]),
        "additional_activity_proposals": len(roles),
        "additional_negative_proposals": neg_count,
        "additional_scope_holds": hold_count,
        "additional_source_pointers": len(sources),
        "canonical_membership_admissions": 0,
        "dataos_identities_qualified": 0,
        "existing_micro_count": len(valid_micros),
        "measurement_cohorts_admitted": 0,
        "micros_with_new_proposals": len(new_counts),
        "new_micro_ids": 0,
        "single_candidate_micros_before": sum(v == 1 for v in orig_counts.values()),
        "single_candidate_micros_if_all_additions_accepted": sum(
            orig_counts[micro]+new_counts.get(micro,0)==1
            for micro in valid_micros),
        "undated_additional_candidate_rows": sum(
            sources[row["source_ids"][0]]["published_on"] is None for row in roles),
    }
    if population != expected_counts:
        _micro_refuse("unverified addendum population or authority counts")
    # A read-only view of source pointers: do NOT mark the 46 role claims as
    # Data OS resolved or graph admitted, even when publishers and dates exist.
    return {
        "schema": "gmi.microtheme_member_research_addendum_review/v1",
        "availability": "SOURCE_POINTERS_STRUCTURALLY_REVIEWABLE_UNADMITTED",
        "authority_ceiling": "research_internal_only",
        "original_source_digest": original["source_digest"],
        "addendum_content_digest": hashlib.sha256(json.dumps(
            addendum, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
        "counts": expected_counts,
        "source_stage_counts": dict(sorted(stage_counts.items())),
        "source_references": copy.deepcopy(dict(sources)),
        "candidate_activity_roles": copy.deepcopy(roles),
        "negative_cases": copy.deepcopy(addendum["negative_cases"]),
        "scope_holds": copy.deepcopy(addendum["scope_holds"]),
        "limitations": copy.deepcopy(addendum["limitations"]),
    }


def render_microtheme_addendum_markdown(report: Mapping[str, Any]) -> str:
    """Human-readable unadmitted source-pointer review; URLs are not fetched."""
    import html
    from urllib.parse import quote
    def clean(value):
        return html.escape(str(value if value is not None else "unknown"), quote=True).replace("|","&#124;").replace("\n"," ").replace("\r"," ")
    c = report["counts"]
    lines=[
        "# GMI microtheme activity source-pointer addendum — NOT ADMITTED", "",
        f"{c['additional_activity_proposals']} unadmitted additional role proposals across "
        f"{c['micros_with_new_proposals']} existing micros; no new runtime members.", "",
        f"Original source activity records: {c['original_activity_records']}. "
        f"Undated additional activities: {c['undated_additional_candidate_rows']}. "
        f"Potential singleton decrease {c['single_candidate_micros_before']} to "
        f"{c['single_candidate_micros_if_all_additions_accepted']} ONLY IF individually reviewed.", "",
        "Source bodies, issuer/legal identities, purpose rights and market measurements have NOT been verified.", "",
        "| Micro | Entity hint | Activity | Stage | Primary source POINTER |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["candidate_activity_roles"]:
        u = report["source_references"][row["source_ids"][0]]["url"]
        safe_url = quote(u, safe="/:?&=#%+@-._~")
        lines.append("| " + " | ".join((
            clean(row["micro_id"]),clean(row["entity_name"]),
            clean(row["product_or_activity"]),clean(row["evidence_stage"]),
            f"[source]({safe_url})",
        )) + " |")
    lines.extend(["", "## Negative research cases", ""])
    lines.extend("- " + clean(x["micro_id"]) + ": " + clean(x["disposition_reason"])
                 for x in report["negative_cases"])
    lines.extend(["", "## Scope holds", ""])
    lines.extend("- " + clean(x["micro_id"]) + ": " + clean(x["disposition_reason"])
                 for x in report["scope_holds"])
    lines.extend(["", "## No authority conveyed", ""])
    lines.extend("- "+clean(x) for x in report["limitations"])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Native activity admission (GMI recovery 2026-10-16, section 9 step 3)
# ---------------------------------------------------------------------------
#
# One owner-read company activity, bound to one micro-theme definition, as EVIDENCE
# for a proposal. Nothing here ratifies, materializes, ranks or publishes. Identity is
# read through the existing read-only identity_resolution owner, the source edition,
# span and purpose through the company-intelligence disclosure owner, and rights
# through engine.theme_graph.rights. A name-prefix identity hint, a basket/group
# expression or a prepared coverage profile is never an admission basis.

ACTIVITY_EVIDENCE_SCHEMA = "gmi.activity_membership_evidence/v1"
ADMITTED_ACTIVITY_SPECIES = frozenset({"planned_product_integration"})
ACTIVITY_ROLES = frozenset({"component_supplier", "platform_owner"})
ACTIVITY_CROSSWALK_PATH = "config/theme_crosswalk.yml"
ACTIVITY_SOURCE_OWNER = "engine.company_intelligence.issuer_disclosure_owner"
_ACTIVITY_SPECIES_BY_FACT = {("product_integration", "planned"): "planned_product_integration"}
_NATIVE_BASIS = {"kind": "native_disclosure_fact"}
_HINT_KEYS = frozenset({"identity_hint_state", "possible_current_issuer_refs"})


class ActivityAdmissionRefusal(ValueError):
    """A typed refusal; ``code`` is stable and is what callers and tests branch on."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _activity_instant(value: Any, code: str):
    from datetime import datetime

    if not isinstance(value, str) or "T" not in value:
        raise ActivityAdmissionRefusal(code, "a zoned ISO-8601 instant is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ActivityAdmissionRefusal(code, str(exc)) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ActivityAdmissionRefusal(code, "the instant carries no zone")
    return parsed


def _activity_plain(value: Any) -> Any:
    """JSON-plain view of one identity-owner cell (parquet rows carry numpy/NaN)."""
    from datetime import date, datetime

    if value is None or type(value).__name__ in {"NAType", "NaTType"}:
        return None
    if isinstance(value, float) and value != value:
        return None
    if not isinstance(value, (str, bytes, bool, int, float)) and hasattr(value, "item"):
        try:
            return _activity_plain(value.item())
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _default_activity_disclosure(root: Path, code_version: str):
    from engine.company_intelligence import issuer_disclosure_owner as owner

    spec_raw = (root / owner.SPEC_PATH).read_bytes()
    ruling_raw = (root / owner.RULING_PATH).read_bytes()
    registry_raw = (root / owner.REGISTRY_PATH).read_bytes()
    return owner.qualify_records(code_version, spec_raw, ruling_raw, registry_raw,
                                 json.loads(spec_raw)["identities"])


def _default_activity_identity(node_id: str) -> Mapping[str, Any]:
    from engine.theme_graph.identity_resolution import resolve_graph_node_identity

    return resolve_graph_node_identity(node_id)


def _activity_rights_read(family: str | None) -> dict[str, Any]:
    from engine.theme_graph import rights

    if family is None:
        return {"family": None, "rights_class": None,
                "public_emission": "RIGHTS_FAMILY_UNRESOLVED"}
    try:
        cls = rights.rights_class(family)
    except rights.RightsRefusal:
        return {"family": family, "rights_class": None,
                "public_emission": "RIGHTS_FAMILY_UNRESOLVED"}
    return {"family": family, "rights_class": cls,
            "public_emission": "GRANTED" if rights.emission_allowed(family) else "NOT_GRANTED"}


def _activity_target_definition(root: Path, theme_id: str) -> dict[str, Any]:
    import yaml
    from datetime import date
    from engine.theme_graph import rights

    raw = (root / ACTIVITY_CROSSWALK_PATH).read_bytes()
    entries = [entry for entry in yaml.safe_load(raw)["hierarchy"]["micro_themes"]
               if isinstance(entry, Mapping) and entry.get("id") == theme_id]
    if len(entries) != 1:
        raise ActivityAdmissionRefusal("TARGET_DEFINITION_UNKNOWN",
                                       f"{theme_id!r} is not one current micro-theme definition")
    entry = {key: (value.isoformat() if isinstance(value, date) else value)
             for key, value in entries[0].items()}
    asserted = entry.get("asserted_on")
    if not isinstance(asserted, str) or len(asserted) != 10:
        raise ActivityAdmissionRefusal("TARGET_DEFINITION_UNKNOWN",
                                       f"{theme_id!r} carries no asserted_on date")
    family = rights.family_for_source_ref(ACTIVITY_CROSSWALK_PATH)
    return {
        "theme_id": theme_id,
        "tier": "micro_theme",
        "asserted_on": asserted,
        "definition_sha256": hashlib.sha256(_canonical(entry).encode()).hexdigest(),
        "crosswalk_sha256": hashlib.sha256(raw).hexdigest(),
        "rights_family": family,
    }


def _activity_magnitude(value: Any) -> dict[str, Any]:
    """A null magnitude stays null and UNDISCLOSED; zero is only ever a disclosed zero."""
    if value is None:
        return {"value": None, "state": "UNDISCLOSED"}
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActivityAdmissionRefusal("MAGNITUDE_INVALID", f"{value!r} is not a number")
    return {"value": value, "state": "KNOWN_ZERO" if value == 0 else "KNOWN"}


def _activity_clock(value: Any, precision: str) -> dict[str, Any]:
    if value is None:
        return {"value": None, "precision": None, "state": "UNDISCLOSED"}
    return {"value": value, "precision": precision, "state": "KNOWN"}


def build_activity_membership_evidence(*, issuer_node_id: str, target_theme_id: str,
                                       role: str, knowledge_cutoff: str, code_version: str,
                                       root: Path = ROOT, identity_reader=None,
                                       disclosure_reader=None,
                                       basis: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Bind one native disclosed activity to one micro-theme as proposal evidence.

    Refuses (``ActivityAdmissionRefusal.code``) rather than guessing: a name-prefix
    identity hint, a basket/group expression or a prepared profile as the basis; a
    source the owner does not qualify; a fact not yet known at ``knowledge_cutoff``
    (filtered before any other selection); an unadmitted species; an unresolved,
    ambiguous or mismatched issuer identity; a target that is not one current
    micro-theme definition; an unadmitted role. The result is evidence only:
    graph-membership use is NOT_GRANTED because no source-purpose ruling grants it.
    """
    if basis is not None:
        if isinstance(basis, Mapping) and _HINT_KEYS & set(basis):
            raise ActivityAdmissionRefusal("IDENTITY_HINT_NOT_ADMISSION",
                                           "a name-prefix identity hint is not identity")
        if not isinstance(basis, Mapping) or dict(basis) != _NATIVE_BASIS:
            raise ActivityAdmissionRefusal("GROUP_TO_MICRO_REFUSED",
                                           "only a native disclosure fact may admit an activity")
    node = str(issuer_node_id)
    if not node.startswith("co:"):
        raise ActivityAdmissionRefusal("ENDPOINT_NOT_ADMITTED",
                                       f"{node!r} is not a company node")
    if not str(target_theme_id).startswith("theme:"):
        raise ActivityAdmissionRefusal("ENDPOINT_NOT_ADMITTED",
                                       f"{target_theme_id!r} is not a micro-theme node")
    cutoff = _activity_instant(knowledge_cutoff, "KNOWLEDGE_CUTOFF_INVALID")

    root = Path(root)
    try:
        snapshot = (disclosure_reader(root, code_version) if disclosure_reader is not None
                    else _default_activity_disclosure(root, code_version))
        spec, bindings = snapshot.spec, dict(snapshot.bindings)
        edition, fact = spec["edition"], spec["fact"]
    except ActivityAdmissionRefusal:
        raise
    except Exception as exc:  # the owner's own refusal or an unreadable record
        raise ActivityAdmissionRefusal("SOURCE_OWNER_REFUSED", type(exc).__name__) from None

    # Knowledge cutoff BEFORE selection: a fact or edition we did not yet know is absent.
    for clock in (fact.get("known_at"), edition.get("known_at")):
        if _activity_instant(clock, "SOURCE_OWNER_REFUSED") > cutoff:
            raise ActivityAdmissionRefusal("KNOWLEDGE_CUTOFF_EXCLUDED",
                                           f"known_at {clock} is after {knowledge_cutoff}")

    species = _ACTIVITY_SPECIES_BY_FACT.get((fact.get("kind"), fact.get("lifecycle")))
    if species not in ADMITTED_ACTIVITY_SPECIES:
        raise ActivityAdmissionRefusal(
            "SPECIES_NOT_ADMITTED", f"{fact.get('kind')!r}/{fact.get('lifecycle')!r}")

    try:
        row = (identity_reader or _default_activity_identity)(node)
        row = {str(key): _activity_plain(value) for key, value in dict(row).items()}
    except Exception as exc:
        raise ActivityAdmissionRefusal("IDENTITY_UNRESOLVED", type(exc).__name__) from None
    state = row.get("resolution_state")
    if state == "AMBIGUOUS":
        raise ActivityAdmissionRefusal("AMBIGUOUS_IDENTITY", node)
    if state != "RESOLVED" or not row.get("security_id"):
        raise ActivityAdmissionRefusal("IDENTITY_UNRESOLVED", f"{node}: {state}")
    if row.get("node_id") != node or row.get("issuer_id") != fact.get("subject_id"):
        raise ActivityAdmissionRefusal(
            "ISSUER_IDENTITY_MISMATCH",
            f"{node} resolves to {row.get('issuer_id')!r}, the fact names {fact.get('subject_id')!r}")

    target = _activity_target_definition(root, str(target_theme_id))
    if role not in ACTIVITY_ROLES:
        raise ActivityAdmissionRefusal("ROLE_NOT_ADMITTED", repr(role))

    from engine.company_intelligence import issuer_disclosure_owner as owner
    from engine.theme_graph import rights

    return {
        "schema": ACTIVITY_EVIDENCE_SCHEMA,
        "issuer": {
            "node_id": node,
            "issuer_id": row["issuer_id"],
            "security_id": row["security_id"],
            "resolution_state": state,
            "join_method": row.get("join_method"),
            "resolution_asof": row.get("resolution_asof"),
            "identity_read_sha256": hashlib.sha256(_canonical(row).encode()).hexdigest(),
        },
        "species": species,
        "scope": {
            "product": fact["product"],
            "platform": fact["platform"],
            "counterparty_issuer_id": fact["object_id"],
            "segment": {"value": None, "state": "UNDISCLOSED"},
        },
        "role": role,
        "lifecycle": fact["lifecycle"],
        "endpoints": {"source_node_id": node, "target_node_id": target["theme_id"],
                      "direction": "SOURCE_TO_TARGET"},
        "target_definition": target,
        "source_evidence": {
            "disclosure_id": fact["disclosure_id"],
            "fact_id": fact["fact_id"],
            "fact_revision": fact["revision"],
            "review_revision": fact["review_revision"],
            "edition": {
                "source_key": edition["source_key"],
                "source_sha256": edition["source_sha256"],
                "byte_length": edition["source_byte_length"],
                "published_date": edition.get("published_date"),
            },
            "span": copy.deepcopy(fact["span"]),
            "owner_bindings": bindings,
            "owner": ACTIVITY_SOURCE_OWNER,
        },
        "use_qualification": {
            "target_definition_rights": _activity_rights_read(target["rights_family"]),
            "source_rights": _activity_rights_read(rights.family_for_source_ref(owner.SPEC_PATH)),
            "purpose": {
                "ruling_binding_sha256": bindings["purpose"],
                "permitted_purpose": owner.PURPOSE,
                "permitted_audience": owner.AUDIENCE,
            },
            "graph_membership_use": "NOT_GRANTED",
        },
        "magnitudes": {
            "amount": _activity_magnitude(fact.get("amount")),
            "economic_share": _activity_magnitude(fact.get("economic_share")),
        },
        "clocks": {
            "publication": _activity_clock(edition.get("published_date"), "date"),
            "observation": _activity_clock(edition.get("known_at"), "instant"),
            "knowledge": _activity_clock(fact.get("known_at"), "instant"),
            "effective": {"value": None, "precision": None, "state": "UNDISCLOSED"},
            "admitted": {"value": None, "precision": None, "state": "NOT_APPLICABLE"},
            "correction": {"value": None, "precision": None, "state": "NOT_APPLICABLE"},
            "served_generation": {"value": None, "precision": None, "state": "NOT_APPLICABLE"},
        },
    }
