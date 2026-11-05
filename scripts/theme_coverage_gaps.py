"""Coverage-gap diagnostic over the theme graph — mechanical, LLM-free (W3A §4, §9.9).

THE QUESTION IT ASKS. Given a set of instruments somebody cares about, which of them does
the concept vocabulary fail to explain? The motivating exemplar is the lithium one: three
names move together, each of them HAS local-theme memberships, and yet no single concept
contains more than one of them — a coverage gap that a per-name "is it in any theme?"
check cannot see, because every name individually looks covered.

So case A is a CO-OCCURRENCE report, not a zero-membership report:

  * pairwise shared-concept counts across the supplied ids;
  * the ids that share NO concept with any other supplied id — the gap signal;
  * ids with zero live memberships at all, reported as a sub-case (they are a different
    failure: no vocabulary rather than no SHARED vocabulary).

Case D is a BREADTH signal: ids whose only memberships are concepts above a reporting
floor. A 200-member concept explains "this is a US equity" more than it explains why
these three names moved. The floor is a REPORT PARAMETER — printed with the breadth
distribution beside it, never a truth claim about where "too broad" begins.

Cases B and C (theme_discovery clusters, co-movement) are documented in the plan and
deferred to W3B, where those inputs have state.

READ-ONLY over the store. The optional ``--propose`` writes probation rows, which are
suggestions in a queue nothing reads without a curated ratification — never edges.

Run: python -m scripts.theme_coverage_gaps --ids-file ids.txt [--out report.json]
                                          [--breadth-floor N] [--propose]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.theme_graph import probation, store  # noqa: E402

log = logging.getLogger("theme_coverage_gaps")
DEFAULT_BREADTH_FLOOR = 25
PAIR_DISPLAY_LIMIT = 200
SELECTION_BASIS = "CURRENT_NODES_LATEST_BELIEF_EDGES_NO_HISTORICAL_RECONSTRUCTION"


def _is_null(v: object) -> bool:
    return v is None or (isinstance(v, float) and v != v) or str(v).strip() in ("", "None", "NaT", "<NA>")


def _stamp(value: object) -> datetime:
    text = str(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp requires a timezone")
    return stamp.astimezone(timezone.utc)


def _live(row: dict, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    start = _stamp(row["valid_from"])
    end = None if _is_null(row.get("valid_to")) else _stamp(row["valid_to"])
    return start <= now and (end is None or now < end)


def read_ids(source: str | None) -> list[str]:
    text = Path(source).read_text(encoding="utf-8") if source and source != "-" else sys.stdin.read()
    # Preserve the actual parsed input list, including duplicates, in the digest.
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def resolve_ids(ids: list[str], nodes) -> tuple[dict[str, str], dict[str, str]]:
    """Exact active graph company or unambiguous symbol; never security qualification.

    Share-class/epoch suffixes remain distinct. A symbol cannot drop a '#' suffix.
    """
    rows = nodes.to_dict("records")
    all_nodes = {str(row.get("node_id")): row for row in rows}
    companies = {nid for nid, row in all_nodes.items() if re.fullmatch(r"co:[a-z]+:[^\s:]+", nid)
                 and row.get("kind") == "company"
                 and row.get("status") in {"candidate", "canonical"}}
    by_symbol: dict[str, list[str]] = {}
    for nid in sorted(companies):
        parts = nid.split(":", 2)
        if len(parts) == 3:
            by_symbol.setdefault(parts[2].upper(), []).append(nid)
    resolved, unresolved = {}, {}
    for item in dict.fromkeys(ids):
        if item in companies:
            resolved[item] = item
        elif item in all_nodes:
            unresolved[item] = "node is retired/merged or is not a company"
        else:
            hits = by_symbol.get(item.upper(), []) if ":" not in item else []
            if len(hits) == 1:
                resolved[item] = hits[0]
            elif len(hits) > 1:
                unresolved[item] = f"ambiguous across markets or share classes: {sorted(hits)}"
            else:
                unresolved[item] = "no company node with this id or symbol"
    # Two aliases of the same graph company must not become a spurious pair.
    seen = set()
    for item, nid in list(resolved.items()):
        if nid in seen:
            unresolved[item] = "duplicate reference to an already supplied graph company"
            del resolved[item]
        seen.add(nid)
    return resolved, unresolved


def membership_index(edges: list[dict], *, now: datetime | None = None,
                     eligible_nodes: set[str] | None = None,
                     active_endpoints: set[str] | None = None,
                     node_kinds: dict[str, str] | None = None) -> tuple[dict[str, set[str]], dict[str, int]]:
    basket_ltheme: dict[str, set[str]] = {}
    for e in edges:
        if active_endpoints is not None and (e.get("src") not in active_endpoints or e.get("dst") not in active_endpoints):
            continue
        if node_kinds is not None and (node_kinds.get(e.get("src")) != "basket" or node_kinds.get(e.get("dst")) != "local_theme"):
            continue
        if (e.get("type") == "EXPRESSES" and _live(e, now)
                and re.fullmatch(r"basket:[^\s:]+:[^\s:]+", str(e.get("src", "")))
                and re.fullmatch(r"ltheme:[^\s:]+:[^\s:]+", str(e.get("dst", "")))):
            basket_ltheme.setdefault(str(e["src"]), set()).add(str(e["dst"]))
    per_company: dict[str, set[str]] = {}
    for e in edges:
        if active_endpoints is not None and (e.get("src") not in active_endpoints or e.get("dst") not in active_endpoints):
            continue
        if e.get("type") != "MEMBER_OF" or not _live(e, now):
            continue
        src, dst = str(e.get("src", "")), str(e.get("dst", ""))
        if not re.fullmatch(r"co:[a-z]+:[^\s:]+", src) or (eligible_nodes is not None and src not in eligible_nodes):
            continue
        if node_kinds is not None and node_kinds.get(src) != "company":
            continue
        if re.fullmatch(r"ltheme:[^\s:]+:[^\s:]+", dst) and (node_kinds is None or node_kinds.get(dst) == "local_theme"):
            per_company.setdefault(src, set()).add(dst)
        elif re.fullmatch(r"basket:[^\s:]+:[^\s:]+", dst) and (node_kinds is None or node_kinds.get(dst) == "basket"):
            per_company.setdefault(src, set()).update(basket_ltheme.get(dst, ()))
    breadth: dict[str, int] = {}
    for themes in per_company.values():
        for lt in themes:
            breadth[lt] = breadth.get(lt, 0) + 1
    return per_company, breadth


def _clock_issues(nodes, edges, lifecycle, now):
    issues = []
    for owner, rows, fields in (
        ("nodes", nodes.to_dict("records"), ("computed_at",)),
        ("latest_edges", edges, ("valid_from", "belief_time", "computed_at")),
        ("latest_lifecycle", lifecycle, ("computed_at",))):
        for row in rows:
            ref = str(row.get("edge_id") or row.get("node_id") or "unknown")
            for field in fields:
                value = row.get(field)
                try:
                    if _is_null(value):
                        raise ValueError("missing clock")
                    if _stamp(value) > now:
                        raise ValueError("future clock in already-selected current snapshot")
                except (ValueError, TypeError) as exc:
                    issues.append(f"{owner}:{ref}:{field}: {exc}")
            for field in ("valid_to", "retire_date", "birth_date", "source_effective_at", "source_published_at", "house_admitted_at", "evidence_time"):
                if not _is_null(row.get(field)):
                    try:
                        end = _stamp(row[field])
                        if end > now:
                            raise ValueError("future optional clock in current snapshot")
                        if field == "valid_to" and end < _stamp(row["valid_from"]):
                            raise ValueError("interval closes before it opens")
                    except (ValueError, KeyError, TypeError) as exc:
                        issues.append(f"{owner}:{ref}:{field}: {exc}")
    return issues


def _observation(ids, report, nodes, edges, lifecycle, *, now, source_artifact, source_asof, input_available):
    companies = set(report["resolved_graph_nodes"].values())
    endpoints = {str(row.get("node_id")): row for row in nodes.to_dict("records")}
    def eligible(row):
        src, dst = endpoints.get(row.get("src"), {}), endpoints.get(row.get("dst"), {})
        if src.get("status") not in {"candidate", "canonical"} or dst.get("status") not in {"candidate", "canonical"}:
            return False
        if row.get("type") == "MEMBER_OF":
            kinds = ("company", "local_theme") if str(row.get("dst")).startswith("ltheme:") else ("company", "basket")
        elif row.get("type") == "EXPRESSES":
            kinds = ("basket", "local_theme")
        else:
            return False
        return (src.get("kind"), dst.get("kind")) == kinds and _live(row, now)
    # An indeterminate snapshot carries no eligible-path assertions.
    selected = [row for row in edges if eligible(row)] if report["availability"]["state"] == "OK" else []
    memberships = [row for row in selected if row.get("type") == "MEMBER_OF" and row.get("src") in companies
                   and re.fullmatch(r"(?:basket|ltheme):[^\s:]+:[^\s:]+", str(row.get("dst")))]
    baskets = {row.get("dst") for row in memberships if str(row.get("dst")).startswith("basket:")}
    relevant = memberships + [row for row in selected if row.get("type") == "EXPRESSES" and row.get("src") in baskets
                              and re.fullmatch(r"ltheme:[^\s:]+:[^\s:]+", str(row.get("dst")))]
    refs = sorted({str(ref) for row in relevant for ref in _refs(row.get("evidence_refs"))})
    complete_snapshot = report["availability"]["state"] == "OK"
    snapshot = {"node_rows": len(nodes) if complete_snapshot else None,
        "edge_rows": len(edges) if complete_snapshot else None,
        "lifecycle_rows": len(lifecycle) if complete_snapshot else None,
        "sha256": hashlib.sha256(json.dumps(_normalized({"nodes": nodes.to_dict("records"), "edges": edges,
            "lifecycle": lifecycle}), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest() if complete_snapshot else None,
        "basis": "digest of the actual selected current reader rows; not a source-capture or authenticity receipt"}
    raw_clocks = []
    for row in relevant:
        raw_clocks.append({"edge_id": "unknown" if _is_null(row.get("edge_id")) else str(row["edge_id"]),
            "src": row["src"], "dst": row["dst"], "type": row["type"],
            "endpoint_eligibility": {"src_kind": endpoints[row["src"]]["kind"], "src_status": endpoints[row["src"]]["status"],
                "dst_kind": endpoints[row["dst"]]["kind"], "dst_status": endpoints[row["dst"]]["status"]},
            "values": {key: None if _is_null(row.get(key)) else str(row[key]) for key in
                       ("valid_from", "valid_to", "evidence_time", "belief_time", "computed_at",
                        "source_effective_at", "source_published_at", "house_admitted_at")},
            "missing_clock_reason": "null values were not supplied by the stored owner row"})
    analysis = ("PARTIAL" if report["unresolved"] else "COMPLETE") if report["availability"]["state"] == "OK" else "INDETERMINATE"
    return {"schema": "gmi.coverage_observation/v1", "input_list": list(ids) if input_available else None,
        "input_state": "READ" if input_available else "UNAVAILABLE",
        "input_digest_reason": None if input_available else "input list could not be read; no population/digest witness",
        "input_list_sha256": hashlib.sha256(json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() if input_available else None,
        "graph_snapshot": snapshot,
        "source_artifact": {"reference": source_artifact, "verification": "CALLER_DECLARED" if source_artifact else "NOT_SUPPLIED",
            "revision": None, "sha256": None, "reason": "caller declaration is not an artifact verification receipt"},
        "clocks": {"observed_at": now.isoformat().replace("+00:00", "Z"),
            "selection_basis": SELECTION_BASIS, "historical_claim": False,
            "source_asof_declared": source_asof, "edge_observations": raw_clocks,
            "issues": report["availability"]["issues"]},
        "population": {"definition": "unique active graph company nodes resolved from the supplied input; source-local MEMBER_OF directly or via basket EXPRESSES local theme",
            "supplied": len(ids) if input_available else None, "distinct_supplied": len(set(ids)) if input_available else None, "eligible": report["resolved"],
            "resolved_graph_nodes": report["resolved_graph_nodes"], "excluded": report["unresolved"]},
        "identity": {"state": "UNQUALIFIED_GRAPH_COMPANY", "security_qualification": "NOT_EVALUATED",
            "owner": "engine.theme_graph.security_navigation", "reason": "graph company resolution does not verify Data OS security/listing identity"},
        "evaluated_dimensions": {"source_local_concept_cooccurrence": analysis,
            "canonical_theme": "NOT_EVALUATED", "micro_theme": "NOT_EVALUATED", "sector": "NOT_EVALUATED",
            "industry": "NOT_EVALUATED", "measurement": "NOT_EVALUATED"},
        "source_local_memberships": report["membership_detail"],
        "pair_display": {"total": report["case_a_cooccurrence"]["total_pairs_sharing_a_concept"],
            "displayed": report["case_a_cooccurrence"]["displayed_pairs"], "limit": PAIR_DISPLAY_LIMIT,
            "truncated": report["case_a_cooccurrence"]["truncated"]},
        "evidence_refs": refs, "counterevidence": {"state": "NOT_EVALUATED", "refs": []},
        "completeness": {"analysis": analysis,
            "display": "TRUNCATED" if report["case_a_cooccurrence"]["truncated"] else analysis,
            "identity": "NOT_EVALUATED", "reason": "analysis covers this current graph snapshot only; display may be bounded; security identity is unexamined"},
        "rights": {"authority_ceiling": "research_internal_only", "use_verdict": "NOT_EVALUATED",
            "new_grant": False, "public_display_allowed": False},
        "next_action": {"reason": "review source-local evidence and qualification; no missing canonical/sector/measurement claim follows",
            "owner": "engine.theme_graph.proposal_worklist", "code": "REVIEW_CURRENT_SOURCE_LOCAL_OBSERVATION",
            "query": "python -m scripts.query_theme_ontology --proposal-id <existing-proposal-id> --asof <current-date>"}}


def _normalized(value):
    if isinstance(value, dict):
        return {str(k): _normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalized(v) for v in value]
    if _is_null(value):
        return None
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def _refs(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return [value] if value.strip() else []
    return [v for v in value if isinstance(v, str) and v] if isinstance(value, list) else []


def analyse(ids: list[str], nodes, edges: list[dict], *, breadth_floor: int = DEFAULT_BREADTH_FLOOR,
            now: datetime | None = None, lifecycle: list[dict] | None = None,
            source_artifact: str | None = None, source_asof: str | None = None,
            input_issue: str | None = None, input_available: bool = True) -> dict:
    now = now or datetime.now(timezone.utc)
    source_artifact = source_artifact or None
    issues = [input_issue] if input_issue else []
    resolved, unresolved = {}, {}
    try:
        if not ids:
            issues.append("EMPTY_INPUT_POPULATION")
        if nodes.empty or not edges:
            issues.append("EMPTY_GRAPH_INPUT")
        if breadth_floor < 1:
            issues.append("INVALID_BREADTH_REPORT_PARAMETER")
        if not nodes.empty:
            if not {"node_id", "kind", "status", "computed_at", "birth_date"}.issubset(nodes.columns):
                raise ValueError("missing node identity/clock columns")
            if nodes["node_id"].duplicated().any():
                raise ValueError("duplicate graph node identity")
            if not nodes["status"].isin({"candidate", "canonical", "retired", "merged"}).all():
                raise ValueError("unsupported node lifecycle status")
            resolved, unresolved = resolve_ids(ids, nodes)
        known = set(str(n) for n in nodes.get("node_id", []))
        seen_edges = {}
        for edge in edges:
            if not all(isinstance(edge.get(key), str) and edge[key].strip()
                       for key in ("edge_id", "src", "dst", "type")):
                issues.append("MALFORMED_EDGE_IDENTITY")
            edge_key = str(edge.get("edge_id"))
            payload = json.dumps(_normalized(edge), sort_keys=True, separators=(",", ":"), allow_nan=False)
            if edge_key in seen_edges and seen_edges[edge_key] != payload:
                issues.append("CONFLICTING_DUPLICATE_EDGE_ID:" + edge_key)
            seen_edges[edge_key] = payload
            if edge.get("src") not in known or edge.get("dst") not in known:
                issues.append("EDGE_ENDPOINT_NOT_IN_CURRENT_NODE_SNAPSHOT:" + str(edge.get("edge_id")))
        issues.extend(_clock_issues(nodes, edges, lifecycle or [], now))
    except (ValueError, KeyError, TypeError) as exc:
        issues.append("INCONSISTENT_GRAPH_INPUT: " + str(exc))
    pairs, isolated, zero, broad, memberships = [], None, None, None, None
    distribution = dict.fromkeys(("concepts_with_live_members", "median_members", "p90_members", "max_members"))
    if not issues:
        eligible = {str(row["node_id"]) for row in nodes.to_dict("records")
                    if row.get("kind") == "company" and row.get("status") not in store.RETIRED_LIKE_STATUSES}
        active = {str(row["node_id"]) for row in nodes.to_dict("records")
                  if row.get("status") not in store.RETIRED_LIKE_STATUSES}
        kinds = {str(row["node_id"]): row["kind"] for row in nodes.to_dict("records")}
        per_company, breadth = membership_index(edges, now=now, eligible_nodes=eligible, active_endpoints=active, node_kinds=kinds)
        memberships = {sup: per_company.get(node, set()) for sup, node in resolved.items()}
        supplied = sorted(memberships)
        for i, a in enumerate(supplied):
            for b in supplied[i + 1:]:
                shared = memberships[a] & memberships[b]
                if shared:
                    pairs.append(dict(a=a, b=b, shared=len(shared), concepts=sorted(shared)))
        pairs.sort(key=lambda p: (-p["shared"], p["a"], p["b"]))
        has_partner = {name for pair in pairs for name in (pair["a"], pair["b"])}
        zero = sorted(s for s in supplied if not memberships[s])
        isolated = sorted(s for s in supplied if s not in has_partner and memberships[s])
        broad = sorted(s for s in supplied if memberships[s] and all(breadth[lt] >= breadth_floor for lt in memberships[s]))
        sizes = sorted(breadth.values())
        distribution = dict(concepts_with_live_members=len(sizes), median_members=sizes[len(sizes)//2] if sizes else 0,
                            p90_members=sizes[int(len(sizes)*.9)] if sizes else 0, max_members=sizes[-1] if sizes else 0)
    total = len(pairs) if not issues else None
    report = {"generated_at": now.isoformat().replace("+00:00", "Z"),
        "rule": "coverage_gaps.v1 (mechanical source-local concept co-occurrence; breadth is a report parameter)",
        "authority_ceiling": "research_internal_only", "selection_basis": SELECTION_BASIS,
        "availability": {"state": "INDETERMINATE" if issues else "OK", "issues": issues},
        "supplied": len(ids) if input_available else None, "resolved": len(resolved) if not issues else None,
        "resolved_graph_nodes": resolved if not issues else {}, "unresolved": unresolved,
        "case_a_cooccurrence": {"pairs_sharing_a_concept": pairs[:PAIR_DISPLAY_LIMIT] if not issues else None,
            "total_pairs_sharing_a_concept": total, "displayed_pairs": min(total, PAIR_DISPLAY_LIMIT) if total is not None else None,
            "display_limit": PAIR_DISPLAY_LIMIT, "truncated": total > PAIR_DISPLAY_LIMIT if total is not None else None,
            "isolated_ids": isolated, "zero_membership_ids": zero,
            "isolated_note": "source-local memberships share no concept with another eligible supplied graph company",
            "zero_membership_note": "zero in this current source-local graph snapshot only; canonical/micro/sector/measurement dimensions NOT_EVALUATED"},
        "case_d_breadth": {"reporting_floor_members": breadth_floor,
            "floor_note": "a REPORT PARAMETER, not a truth claim about where too broad begins",
            "breadth_distribution": distribution, "broad_only_ids": broad},
        "membership_detail": {s: sorted(m) for s, m in sorted(memberships.items())} if memberships is not None else None}
    report["observation_profile"] = _observation(ids, report, nodes, edges, lifecycle or [], now=now, source_artifact=source_artifact, source_asof=source_asof, input_available=input_available)
    probation.require_valid_observation_profile(report["observation_profile"])
    return report


def proposals_from(report: dict) -> list[dict]:
    if report["availability"]["state"] != "OK":
        return []
    isolated = report["case_a_cooccurrence"]["isolated_ids"]
    if len(isolated) < 2:
        return []
    profile = report["observation_profile"]
    return [probation.make_proposal(kind="new_theme", subject={"instrument_ids": sorted(isolated)},
        evidence={"rule": report["rule"], "breadth_floor": report["case_d_breadth"]["reporting_floor_members"],
                  "supplied": report["supplied"], "resolved": report["resolved"], "observation_profile": profile},
        evidence_refs=profile["evidence_refs"], proposed_by="coverage_gap",
        note="source-local candidate vocabulary gap only; unexamined classifications and security identity are NOT_EVALUATED. Ratification is curated.")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids-file", default="-")
    ap.add_argument("--out")
    ap.add_argument("--breadth-floor", type=int, default=DEFAULT_BREADTH_FLOOR)
    ap.add_argument("--propose", action="store_true")
    ap.add_argument("--source-artifact", default=None)
    ap.add_argument("--source-asof", default=None)
    a = ap.parse_args(argv)
    import pandas as pd
    ids, nodes, edges, lifecycle, issue = [], pd.DataFrame(), [], [], None
    input_available = False
    try:
        ids = read_ids(a.ids_file)
        input_available = True
        # Frozen D2B3 current-only consumer decision: never reconstruct past beliefs.
        nodes = store.read_nodes(current=True, strict=True)
        lifecycle = store.read_node_lifecycle(latest=True, strict=True).to_dict("records")
        edges = store.read_edges(latest_belief=True, strict=True).to_dict("records")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        issue = f"UNAVAILABLE_INPUT:{type(exc).__name__}: {exc}"
    report = analyse(ids, nodes, edges, breadth_floor=a.breadth_floor, lifecycle=lifecycle,
                     source_artifact=a.source_artifact, source_asof=a.source_asof, input_issue=issue, input_available=input_available)
    report["input"] = dict(ids_file=a.ids_file, n_supplied=len(ids) if input_available else None, source_artifact=a.source_artifact, source_asof=a.source_asof)
    if a.propose:
        rows = proposals_from(report)
        try:
            added, skipped = probation.append_proposals(rows, store.probation_path()) if rows else (0, 0)
            report["probation"] = dict(written=added, already_present=skipped,
                observation_retention="keep-first: existing proposals, including rejected rows, retain their original observation")
        except (OSError, ValueError) as exc:
            report["probation"] = dict(state="WRITE_REFUSED", reason=str(exc))
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 2 if report["availability"]["state"] != "OK" or report.get("probation", {}).get("state") == "WRITE_REFUSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
