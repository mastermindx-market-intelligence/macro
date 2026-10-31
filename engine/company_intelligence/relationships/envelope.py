"""GMI ORCH-REL M2 relationship envelope: the frozen §8.2 measures.

Pure measurement functions over the committed relationship artifacts.  No
network is reachable from this module and no clock call exists in it: every
instant is parsed from the artifacts themselves and ``as_of`` is the package's
own field.  A measure that cannot be computed is returned/printted as OWED or
ABSENT with its reason — never estimated, never filled with a convenient
example.

The predeclared panel (``m2_inputs/envelope_panel_v1.json``) was frozen before
any M2 leaf row existed; its sha256 is pinned below and the CLI refuses to run
against any other bytes.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from engine.company_intelligence.relationships.package_v2 import (
    SPECIES_ROLES,
    path_validity,
)

REPORT_SCHEMA = "gmi_rel_m2.envelope_report/v1"
PANEL_SHA256 = "108866ecea287cfda09ef536a9f0939fa0188ab41697c080f24174436119a3ca"
PANEL_SALT = "gmi-rel-envelope-panel-v1"
EVIDENCE_SALT = "gmi-rel-envelope-evidence-v1"

#: species iteration order used by every per-species print
SPECIES_ORDER = tuple(SPECIES_ROLES.keys())

DOMAINS = ("D1", "D2")

#: E1 raw coverage states -> the §8.2 reading
E1_READING = {
    "assessed": "supported",
    "no_supported_result": "unsupported",
    "unavailable": "unavailable",
    "not_assessed": "pending",
    "pending": "pending",
}
E1_STATES = ("assessed", "no_supported_result", "unavailable", "not_assessed",
             "pending", "other")

#: E2 cell states, in precedence order
E2_STATES = ("known_fresh", "known_stale", "known_anonymous",
             "searched_no_supported_result", "unavailable", "not_assessed")

#: E8 evidence kinds, in print order
EVIDENCE_KINDS = (
    "outgoing_query",
    "incoming_query",
    "quantitative_fact",
    "unknown_magnitude",
    "anonymous_counterparty",
    "contradiction",
    "stale_evidence",
    "correction",
    "next_publication_reassertion",
    "valid_multi_hop",
    "invalid_multi_hop",
)

SEARCHED_CAVEAT = (
    "searched = cue-candidate search of the assessed documents; recall is "
    "OWED (E4); a searched cell is not proof of absence."
)
RECALL_REASON = (
    "requires an independent frozen annotated corpus; none exists — "
    "precision is never used as a recall proxy"
)
PACKAGE_LAG_REASON = (
    "P.computed_at is set to P.as_of by construction (deterministic package "
    "clock)"
)
USEFULNESS_LINE = (
    "usefulness to an investor is judged by people; this is answerability "
    "only — rating OWED."
)

#: M0 dispositions that never enter any count
EXCLUDED_DISPOSITIONS = ("quarantined", "refused")


class EnvelopeError(Exception):
    """A measure cannot be computed honestly (never silently fixed)."""


class PanelDrift(EnvelopeError):
    """The predeclared panel bytes (or its leaves pin) do not match."""


class InputMissing(EnvelopeError):
    """A required input artifact is absent."""


class OutRefused(EnvelopeError):
    """The requested output directory is refused."""


# --- small shared helpers -------------------------------------------------------


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon_bytes(value) -> bytes:
    """Canonical JSON bytes (sorted keys, compact, LF-terminated)."""
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def parse_instant(text):
    """UTC datetime from an artifact instant, or None when absent."""
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def hours_between(published_at, ingested_at):
    """(ingested - published) in hours; None when either instant is absent."""
    published = parse_instant(published_at)
    ingested = parse_instant(ingested_at)
    if published is None or ingested is None:
        return None
    return (ingested - published).total_seconds() / 3600.0


def domain_of_fn(domain_of: dict):
    return lambda issuer_id: domain_of.get(issuer_id)


def name_of(issuer_id: str, resolver_index) -> str:
    """Resolver sec_name for the issuer, else the ticker part of its id."""
    if isinstance(resolver_index, list):
        resolver_index = resolver_index_of(resolver_index)
    name = resolver_index.get(issuer_id)
    if name:
        return name
    return issuer_id.rsplit("-", 1)[-1]


def resolver_index_of(rows: list) -> dict:
    return {row["issuer_id"]: row["sec_name"] for row in rows}


def load_extraction_rows(extraction_dir) -> list:
    """Every extraction row under extraction/**/*.jsonl, sorted by path."""
    rows = []
    for path in sorted(extraction_dir.rglob("*.jsonl")):
        for line in path.read_bytes().decode("utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _empty_species_map():
    return {species: 0 for species in SPECIES_ORDER}


def _blank_counter():
    return {}


def _bump(counter: dict, key):
    counter[key] = counter.get(key, 0) + 1


def verify_panel(panel_bytes: bytes, expected_sha: str, leaves_sha: str) -> None:
    """Refuse any panel whose bytes or leaves pin drifted (raises PanelDrift)."""
    measured = sha256_hex(panel_bytes)
    if measured != expected_sha:
        raise PanelDrift(
            f"panel sha256 {measured} != pinned {expected_sha}"
        )
    panel = json.loads(panel_bytes.decode("utf-8"))
    if panel.get("leaves_sha256") != leaves_sha:
        raise PanelDrift(
            f"panel leaves_sha256 {panel.get('leaves_sha256')} != leaves file "
            f"{leaves_sha}"
        )


def join_observations(package: dict, extraction_rows: list) -> dict:
    """P.observations[] is an INDEX; full rows live in the extraction rows.

    Returns the joined pairs, the index ids with no extraction row (printed,
    never dropped) and the extraction rows no index entry covers.
    """
    by_id = {
        row["observation_id"]: row
        for row in extraction_rows
        if row.get("row_kind") == "observation" and row.get("observation_id")
    }
    joined = []
    join_missing = []
    seen_ids = set()
    for index_row in package.get("observations", []):
        obs_id = index_row.get("observation_id")
        seen_ids.add(obs_id)
        row = by_id.get(obs_id)
        if row is None:
            join_missing.append(obs_id)
        else:
            joined.append((index_row, row))
    extraction_only = sorted(
        row["observation_id"] for row in by_id.values()
        if row["observation_id"] not in seen_ids
    )
    return {
        "joined": joined,
        "join_missing": sorted(join_missing),
        "extraction_only": extraction_only,
        "index_rows": len(package.get("observations", [])),
        "extraction_rows": len(by_id),
    }


# --- M0 -------------------------------------------------------------------------


def m0_counts(package: dict, edges_doc: dict, extraction_rows: list,
              leaves: dict) -> dict:
    """The M2 NOT-DONE line: counts by species/state, per domain and over all."""
    join = join_observations(package, extraction_rows)
    dom = domain_of_fn(domain_map(leaves))

    observations = {d: _empty_species_map() for d in DOMAINS}
    observations["ALL"] = _empty_species_map()
    excluded: dict = {}
    for index_row, row in join["joined"]:
        if index_row.get("disposition") in EXCLUDED_DISPOSITIONS:
            _bump(excluded, index_row.get("disposition"))
            continue
        species = row.get("species")
        if species not in observations["ALL"]:
            observations["ALL"][species] = 0
        observations["ALL"][species] = observations["ALL"].get(species, 0) + 1
        d = dom(row.get("subject", {}).get("issuer_id"))
        if d in observations:
            observations[d][species] = observations[d].get(species, 0) + 1

    edges = {d: _empty_species_map() for d in DOMAINS}
    edges["ALL"] = _empty_species_map()
    for edge in edges_doc.get("edges", []):
        species = edge.get("species")
        edges["ALL"][species] = edges["ALL"].get(species, 0) + 1
        party_domains = {
            dom(edge["direction"][side])
            for side in ("from_issuer_id", "to_issuer_id")
        }
        for d in party_domains:
            if d in edges:
                edges[d][species] = edges[d].get(species, 0) + 1

    non_edges = {d: _empty_species_map() for d in DOMAINS}
    non_edges["ALL"] = _empty_species_map()
    for row in package.get("non_edges", []):
        species = row.get("species")
        non_edges["ALL"][species] = non_edges["ALL"].get(species, 0) + 1
        d = dom(row.get("subject_issuer_id"))
        if d in non_edges:
            non_edges[d][species] = non_edges[d].get(species, 0) + 1

    coverage = {d: _blank_counter() for d in DOMAINS}
    coverage["ALL"] = _blank_counter()
    for row in package.get("coverage", []):
        state = row.get("state")
        coverage["ALL"][state] = coverage["ALL"].get(state, 0) + 1
        d = dom(row.get("issuer_id"))
        if d in coverage:
            coverage[d][state] = coverage[d].get(state, 0) + 1

    return {
        "join": {
            "index_rows": join["index_rows"],
            "extraction_rows": join["extraction_rows"],
            "joined": len(join["joined"]),
            "join_missing": join["join_missing"],
            "extraction_only": len(join["extraction_only"]),
        },
        "observations": observations,
        "excluded_dispositions": dict(sorted(excluded.items())),
        "edges": edges,
        "non_edges": non_edges,
        "coverage": coverage,
    }


# --- E1 ------------------------------------------------------------------------


def domain_map(leaves: dict) -> dict:
    """{issuer_id: D1|D2} from a leaves doc, or from a plain domain->ids map."""
    if "domain_of" in leaves:
        return leaves["domain_of"]
    return {
        issuer_id: domain
        for domain, issuer_ids in leaves.items()
        for issuer_id in issuer_ids
    }


def e1_coverage(package: dict, leaves: dict) -> dict:
    """Issuer relation coverage for every eligible issuer; missing = pending.

    The per-domain state counts must sum to the domain's issuer count — a
    mismatch raises EnvelopeError, it is never silently fixed.
    """
    domain_of = domain_map(leaves)
    by_domain = {d: [] for d in DOMAINS}
    for issuer_id in sorted(domain_of):
        d = domain_of[issuer_id]
        if d in by_domain:
            by_domain[d].append(issuer_id)
    coverage_state = {
        row["issuer_id"]: row.get("state")
        for row in package.get("coverage", [])
    }
    state_by_issuer = {}
    domains = {}
    accounted = 0
    for d, issuers in by_domain.items():
        states = {state: 0 for state in E1_STATES}
        reading = {"supported": 0, "unsupported": 0, "unavailable": 0,
                   "pending": 0, "other": 0}
        for issuer_id in issuers:
            state = coverage_state.get(issuer_id)
            if state is None:
                state = "pending"
            key = state if state in states else "other"
            states[key] += 1
            reading[E1_READING.get(state, "other")] += 1
            state_by_issuer[issuer_id] = state
        total = len(issuers)
        accounted += total
        if sum(states.values()) != total:
            raise EnvelopeError(
                f"E1 {d}: state sum {sum(states.values())} != issuer count "
                f"{total}"
            )
        domains[d] = {"total": total, "states": states, "reading": reading}
    if accounted != len(domain_of):
        raise EnvelopeError(
            f"E1: per-domain sum {accounted} != eligible issuer count "
            f"{len(domain_of)} — an issuer is accounted in no domain"
        )
    return {
        "eligible_total": sum(d["total"] for d in domains.values()),
        "domains": domains,
        "state_by_issuer": dict(sorted(state_by_issuer.items())),
    }


# --- E2 ------------------------------------------------------------------------


def e2_cells(package: dict, edges_doc: dict, extraction_rows: list,
             leaves: dict, e1: dict) -> dict:
    """Issuer x (species, role) coverage cells; precedence is frozen."""
    domain_of = domain_map(leaves)
    dom = domain_of_fn(domain_of)
    state_by_issuer = e1["state_by_issuer"]

    by_issuer_side: dict = {}
    for edge in edges_doc.get("edges", []):
        for side, role_key in (("from_issuer_id", "from_role"),
                               ("to_issuer_id", "to_role")):
            issuer_id = edge["direction"][side]
            role = edge["direction"][role_key]
            by_issuer_side.setdefault((issuer_id, edge["species"], role),
                                      []).append(edge)

    extraction_by_id = {
        row["observation_id"]: row
        for row in extraction_rows
        if row.get("row_kind") == "observation"
    }
    anon_by_issuer: dict = {}
    for row in package.get("non_edges", []):
        if row.get("anonymous_alias") is None:
            continue
        issuer_id = row.get("subject_issuer_id")
        species = row.get("species")
        source = extraction_by_id.get(row.get("observation_id"))
        if source is not None and source.get("subject_role"):
            role = source["subject_role"]
        else:
            role = SPECIES_ROLES.get(species, (None, None, None))[2]
        if role is None:
            continue
        anon_by_issuer.setdefault((issuer_id, species, role), []).append(row)

    def blank_cell():
        return {
            state: {"total": 0, "own_filing": 0, "counterparty_filing": 0}
            for state in E2_STATES
        }

    cells: dict = {}
    for issuer_id in sorted(domain_of):
        d = dom(issuer_id)
        if d not in DOMAINS:
            continue
        issuer_state = state_by_issuer.get(issuer_id)
        for species, roles in SPECIES_ROLES.items():
            for role in (roles[0], roles[1]):
                cell = blank_cell()
                edges = by_issuer_side.get((issuer_id, species, role), [])
                if any(e.get("freshness_state") == "fresh" for e in edges):
                    state = "known_fresh"
                elif edges and all(
                    e.get("freshness_state") == "stale" for e in edges
                ):
                    state = "known_stale"
                elif anon_by_issuer.get((issuer_id, species, role)):
                    state = "known_anonymous"
                elif issuer_state in ("assessed", "no_supported_result"):
                    state = "searched_no_supported_result"
                elif issuer_state == "unavailable":
                    state = "unavailable"
                else:
                    state = "not_assessed"
                block = cell[state]
                block["total"] += 1
                if state in ("known_fresh", "known_stale"):
                    # provenance of the cell: own filing wins when the issuer
                    # asserts any of the edges behind the cell
                    if any(issuer_id in set(e.get("asserting_parties", []))
                           for e in edges):
                        block["own_filing"] += 1
                    else:
                        block["counterparty_filing"] += 1
                elif state == "known_anonymous":
                    sources = anon_by_issuer[(issuer_id, species, role)]
                    own = any(
                        (extraction_by_id.get(src.get("observation_id"), {})
                         .get("asserting_party") == issuer_id)
                        for src in sources
                    )
                    if own or not sources:
                        block["own_filing"] += 1
                    else:
                        block["counterparty_filing"] += 1
                cells.setdefault(d, {})
                per_domain = cells[d]
                key = f"{species}|{role}"
                existing = per_domain.get(key)
                if existing is None:
                    per_domain[key] = cell
                else:
                    for state_name, counts in cell.items():
                        for part, value in counts.items():
                            existing[state_name][part] += value
    per_domain = {}
    for d, keys in cells.items():
        per_domain[d] = {
            species: {
                role: keys[f"{species}|{role}"]
                for role in (SPECIES_ROLES[species][0], SPECIES_ROLES[species][1])
            }
            for species in SPECIES_ORDER
        }
    return {
        "cells_total": sum(
            state_block["total"]
            for domain in per_domain.values()
            for roles in domain.values()
            for states in roles.values()
            for state_block in states.values()
        ),
        "per_domain": per_domain,
        "caveat": SEARCHED_CAVEAT,
    }


# --- E3 ------------------------------------------------------------------------


def read_judging(judging_dirs: list) -> tuple:
    """(ledger_rows, materialize_reports, files_read) across judging dirs."""
    ledger_rows: list = []
    reports: dict = {}
    files_read: list = []
    for directory in judging_dirs:
        ledger_path = directory / "fetch_ledger.jsonl"
        report_path = directory / "materialize_report.json"
        if ledger_path.is_file():
            files_read.append(ledger_path)
            for line in ledger_path.read_bytes().decode("utf-8").splitlines():
                if line.strip():
                    ledger_rows.append(json.loads(line))
        if report_path.is_file():
            files_read.append(report_path)
            reports[str(directory)] = json.loads(
                report_path.read_bytes().decode("utf-8")
            )
    return ledger_rows, reports, files_read


def _parse_outcomes(report: dict):
    """Parse outcomes a materialize_report carries, or None."""
    if not isinstance(report, dict):
        return None
    direct = report.get("parse_outcomes")
    if isinstance(direct, dict):
        return dict(sorted(direct.items()))
    counters = report.get("counters")
    if isinstance(counters, dict):
        picked = {
            key: value
            for key, value in counters.items()
            if "parse" in key or "excerpt" in key
        }
        if picked:
            return dict(sorted(picked.items()))
    return None


def e3_sources(package: dict, leaves: dict, judging_dirs: list,
               inputs_dir=None, ledger_rows=None, materialize_reports=None) -> dict:
    """Source processing per §8.2 vocabulary: collected, parsed, partial,
    rejected, unavailable, pending.  M1-pinned issuers (no ledger row, a
    coverage row with documents) are counted as collected (M1 pinned)."""
    domain_of = domain_map(leaves)
    dom = domain_of_fn(domain_of)
    files_read: list = []
    if ledger_rows is None or materialize_reports is None:
        read_rows, reports, files_read = read_judging(judging_dirs)
        if ledger_rows is None:
            ledger_rows = read_rows
        if materialize_reports is None:
            materialize_reports = reports

    judging_state = "PRESENT" if judging_dirs else "ABSENT"
    coverage_by_issuer = {
        row["issuer_id"]: row for row in package.get("coverage", [])
    }
    ledger_by_issuer: dict = {}
    filings = {d: _blank_counter() for d in DOMAINS}
    filings["OTHER"] = _blank_counter()
    documents = {d: _blank_counter() for d in DOMAINS}
    documents["OTHER"] = _blank_counter()
    for row in ledger_rows:
        d = dom(row.get("issuer_id"))
        bucket = d if d in DOMAINS else "OTHER"
        filings[bucket][row.get("state")] = \
            filings[bucket].get(row.get("state"), 0) + 1
        for document in row.get("documents", []):
            documents[bucket][document.get("state")] = \
                documents[bucket].get(document.get("state"), 0) + 1
        ledger_by_issuer.setdefault(row.get("issuer_id"), []).append(row)

    issuer_states = {
        d: {"collected": 0, "parsed": 0, "partial": 0, "rejected": 0,
            "unavailable": 0, "collected_m1_pinned": 0, "pending": 0}
        for d in DOMAINS
    }
    m1_pinned_documents = {d: 0 for d in DOMAINS}
    for issuer_id in sorted(domain_of):
        d = dom(issuer_id)
        if d not in DOMAINS:
            continue
        rows = ledger_by_issuer.get(issuer_id)
        if rows:
            states = {row.get("state") for row in rows}
            if "collected" in states:
                issuer_states[d]["collected"] += 1
            elif "partial" in states:
                issuer_states[d]["partial"] += 1
            elif "unavailable" in states:
                issuer_states[d]["unavailable"] += 1
            elif states and states <= {"rejected", "pending_documents"}:
                issuer_states[d]["rejected"] += 1
            else:
                issuer_states[d]["collected"] += 1
            continue
        coverage_row = coverage_by_issuer.get(issuer_id)
        if coverage_row and coverage_row.get("documents"):
            issuer_states[d]["collected_m1_pinned"] += 1
            m1_pinned_documents[d] += len(coverage_row["documents"])
        else:
            issuer_states[d]["pending"] += 1

    parse_by_domain = {d: None for d in DOMAINS}
    parse_by_domain["OTHER"] = None
    for directory, report in sorted(materialize_reports.items()):
        outcomes = _parse_outcomes(report)
        if outcomes is None:
            continue
        # attach to the domain of the first ledger issuer seen anywhere; a
        # judging dir is leaf/slice-scoped, so its rows share one domain
        dir_dom = None
        for row in ledger_rows:
            candidate = dom(row.get("issuer_id"))
            if candidate in DOMAINS:
                dir_dom = candidate
                break
        if dir_dom is None:
            dir_dom = "OTHER"
        merged = dict(parse_by_domain[dir_dom] or {})
        for key, value in outcomes.items():
            merged[key] = merged.get(key, 0) + value
        parse_by_domain[dir_dom] = dict(sorted(merged.items()))

    per_domain = {}
    for d in DOMAINS + ("OTHER",):
        failed = documents[d].get("failed", 0)
        skipped = documents[d].get("skipped", 0)
        per_domain[d] = {
            "filings_by_state": dict(sorted(filings[d].items())),
            "documents_by_state": dict(sorted(documents[d].items())),
            "parse_outcomes": parse_by_domain[d],
            "issuers": issuer_states[d] if d in DOMAINS else None,
            "m1_pinned_documents": m1_pinned_documents.get(d, 0),
            "documents_failed": failed,
            "documents_skipped": skipped,
        }
    return {
        "judging_dirs": [
            str(directory) for directory in judging_dirs
        ],
        "judging_state": judging_state,
        "per_domain": per_domain,
        "files_read": files_read,
    }


# --- E4 ------------------------------------------------------------------------


def e4_recall() -> dict:
    """Extraction recall is OWED: no frozen annotated corpus exists."""
    return {"value": None, "state": "OWED", "reason": RECALL_REASON}


# --- E5 ------------------------------------------------------------------------


def e5_precision(precision_dir) -> dict:
    """Positive precision: passthrough of the precision report when scored,
    PREPARED_NOT_REVIEWED from a bare manifest, else OWED."""
    if precision_dir is None or not Path(str(precision_dir)).is_dir():
        return {
            "state": "OWED",
            "reason": "no precision sample directory given (--precision-dir)",
        }
    directory = Path(str(precision_dir))
    report_path = directory / "precision_report.json"
    manifest_path = directory / "manifest.json"
    if report_path.is_file():
        report = json.loads(report_path.read_bytes().decode("utf-8"))
        return {
            "state": "SCORED",
            "overall_unweighted": report.get("overall_unweighted"),
            "overall_weighted": report.get("overall_weighted"),
            "strata": report.get("strata"),
            "decoys": report.get("decoys"),
            "reviewer_reliable": report.get("reviewer_reliable"),
            "files_read": [report_path],
        }
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_bytes().decode("utf-8"))
        n_items = manifest.get("items_total", 0)
        n_decoys = manifest.get("decoys_made", 0)
        return {
            "state": "PREPARED_NOT_REVIEWED",
            "n_items": n_items,
            "n_real": n_items - n_decoys,
            "n_decoys": n_decoys,
            "strata": manifest.get("allocation"),
            "files_read": [manifest_path],
        }
    return {
        "state": "OWED",
        "reason": "no precision_report.json or manifest.json under "
                  "--precision-dir",
    }


# --- E6 ------------------------------------------------------------------------


def _nearest_rank(sorted_values: list, fraction: float):
    if not sorted_values:
        return None
    rank = max(1, math.ceil(fraction * len(sorted_values)))
    return round(sorted_values[rank - 1], 2)


def e6_latency(package: dict, extraction_rows: list, leaves: dict) -> dict:
    """Natural operations latency: (ingested_at - published_at) in hours for
    every joined, non-excluded observation.  Package lag is NOT_MEASURABLE."""
    domain_of = domain_map(leaves)
    dom = domain_of_fn(domain_of)
    join = join_observations(package, extraction_rows)
    lags = {d: [] for d in DOMAINS}
    lags["ALL"] = []
    missing_timestamps = 0
    for index_row, row in join["joined"]:
        if index_row.get("disposition") in EXCLUDED_DISPOSITIONS:
            continue
        hours = hours_between(row.get("published_at"), row.get("ingested_at"))
        if hours is None:
            missing_timestamps += 1
            continue
        lags["ALL"].append(hours)
        d = dom(row.get("subject", {}).get("issuer_id"))
        if d in lags:
            lags[d].append(hours)
    per_domain = {}
    for d in DOMAINS + ("ALL",):
        values = sorted(lags[d])
        per_domain[d] = {
            "n": len(values),
            "p50": _nearest_rank(values, 0.5),
            "p90": _nearest_rank(values, 0.9),
            "max": round(values[-1], 2) if values else None,
            "clock_violations": sum(1 for value in values if value < 0),
        }
    e6 = {
        "per_domain": per_domain,
        "missing_timestamps": missing_timestamps,
        "package_lag": {"state": "NOT_MEASURABLE",
                        "reason": PACKAGE_LAG_REASON},
    }
    return e6


# --- E7 ------------------------------------------------------------------------


def e7_answerability(package: dict, edges_doc: dict, extraction_rows: list,
                     leaves: dict, panel: dict, e1: dict,
                     resolver_index: dict) -> dict:
    """Machine answerability of the predeclared panel (the human usefulness
    rating is OWED).  Every (issuer, question) cell gets a status; Q2 is never
    unanswerable."""
    state_by_issuer = e1["state_by_issuer"]
    extraction_by_id = {
        row["observation_id"]: row
        for row in extraction_rows
        if row.get("row_kind") == "observation"
    }
    edges = edges_doc.get("edges", [])
    edges_by_party: dict = {}
    for edge in edges:
        for side in ("from_issuer_id", "to_issuer_id"):
            edges_by_party.setdefault(edge["direction"][side], []).append(edge)
    revisions_by_key: dict = {}
    for revision in package.get("magnitude_revisions", []):
        revisions_by_key.setdefault(revision.get("relationship_key"),
                                    []).append(revision)

    def edges_of(issuer_id):
        return edges_by_party.get(issuer_id, [])

    def asserted(issuer_id, edge):
        return issuer_id in set(edge.get("asserting_parties", []))

    def edge_cite(issuer_id, edge):
        return edge["relationship_key"]

    def status_for(issuer_id, question):
        kind = question["kind"]
        party_edges = edges_of(issuer_id)
        non_edges = [
            row for row in package.get("non_edges", [])
            if row.get("subject_issuer_id") == issuer_id
        ]
        anonymous = [row for row in non_edges
                     if row.get("anonymous_alias") is not None]
        if kind == "outgoing_customers":
            for edge in party_edges:
                if (edge.get("species") == "supplier_customer"
                        and edge["direction"]["from_issuer_id"] == issuer_id
                        and asserted(issuer_id, edge)):
                    return "ANSWERED_FACT", edge_cite(issuer_id, edge)
            if any(row.get("species") == "supplier_customer"
                   for row in anonymous):
                return "ANSWERED_ANONYMOUS", None
        elif kind == "incoming_mentions":
            for edge in party_edges:
                if not asserted(issuer_id, edge):
                    return "ANSWERED_FACT", edge_cite(issuer_id, edge)
            return "ANSWERED_NONE_FOUND", None
        elif kind == "dependencies":
            for edge in party_edges:
                if (edge.get("species") in ("component_dependency",
                                            "contract_manufacturing")
                        and edge["direction"]["to_issuer_id"] == issuer_id):
                    return "ANSWERED_FACT", edge_cite(issuer_id, edge)
            if any(row.get("species") in ("component_dependency",
                                          "contract_manufacturing")
                   for row in anonymous):
                return "ANSWERED_ANONYMOUS", None
        elif kind == "licensing_distribution":
            for edge in party_edges:
                if edge.get("species") in ("licensing", "distribution"):
                    return "ANSWERED_FACT", edge_cite(issuer_id, edge)
            if any(row.get("species") in ("licensing", "distribution")
                   for row in anonymous):
                return "ANSWERED_ANONYMOUS", None
        elif kind == "freshness":
            coverage_row = next(
                (row for row in package.get("coverage", [])
                 if row.get("issuer_id") == issuer_id),
                None,
            )
            documents = (coverage_row or {}).get("documents") or []
            if documents:
                newest = max(documents)
                cite = newest
                if party_edges:
                    freshness = sorted({
                        edge.get("freshness_state") for edge in party_edges
                    })
                    cite += " (edges: " + ", ".join(freshness) + ")"
                return "ANSWERED_FACT", cite
        elif kind == "revisions":
            revised = False
            for edge in party_edges:
                for revision in revisions_by_key.get(
                    edge["relationship_key"], []
                ):
                    if revision.get("revision_kind") in ("reassertion",
                                                         "restatement"):
                        return "ANSWERED_FACT", revision.get("revision_id")
                if edge.get("conflicts"):
                    revised = True
            if revised:
                return "ANSWERED_FACT", edge_cite(issuer_id, party_edges[0])
            if party_edges:
                return "ANSWERED_NONE_FOUND", None

        # fallthrough (never Q2, which returned above)
        issuer_state = state_by_issuer.get(issuer_id)
        if issuer_state in ("assessed", "no_supported_result"):
            return "ANSWERED_NONE_FOUND", None
        if issuer_state == "unavailable":
            return "UNANSWERABLE_UNAVAILABLE", None
        if issuer_state == "not_assessed":
            return "UNANSWERABLE_NOT_ASSESSED", None
        return "UNANSWERABLE_PENDING", None

    labels = panel.get("status_labels", {})
    cells = []
    per_domain = {}
    for domain in ("D1", "D2"):
        issuers = panel.get("issuers", {}).get(domain, [])
        answered = 0
        for issuer_id in issuers:
            for question in panel.get("questions", []):
                status, cite = status_for(issuer_id, question)
                label = labels.get(status, {})
                cells.append({
                    "issuer": issuer_id,
                    "issuer_name": name_of(issuer_id, resolver_index),
                    "domain": domain,
                    "question": question["id"],
                    "kind": question["kind"],
                    "status": status,
                    "en": label.get("en"),
                    "zh": label.get("zh"),
                    "cite": cite,
                })
                if status in ("ANSWERED_FACT", "ANSWERED_ANONYMOUS",
                              "ANSWERED_NONE_FOUND"):
                    answered += 1
        per_domain[domain] = {
            "answered": answered,
            "of": 6 * len(issuers),
        }
    return {
        "cells": cells,
        "per_domain": per_domain,
        "note": USEFULNESS_LINE,
    }


# --- E8 ------------------------------------------------------------------------


def select_evidence(kind: str, item_ids: list) -> str:
    """Preregistered selection: the hash-min item, never a hand pick."""
    return min(
        item_ids,
        key=lambda item_id: sha256_hex(
            (EVIDENCE_SALT + ":" + kind + ":" + item_id).encode("utf-8")
        ),
    )


def _edge_line(edge: dict, resolver_index: dict) -> str:
    parts = [
        "{} {} -> {}".format(
            edge.get("species"),
            name_of(edge["direction"]["from_issuer_id"], resolver_index),
            name_of(edge["direction"]["to_issuer_id"], resolver_index),
        )
    ]
    magnitudes = [
        m for m in edge.get("current_magnitudes", [])
        if m.get("value") is not None
    ]
    if magnitudes:
        magnitude = magnitudes[0]
        parts.append(
            "magnitude {}={} {} ({})".format(
                magnitude.get("kind"), magnitude.get("value"),
                magnitude.get("unit"), magnitude.get("precision")
            )
        )
    accessions = sorted({
        ref.get("accession") for ref in edge.get("source_refs", [])
        if ref.get("accession")
    })
    if accessions:
        parts.append("accessions " + ",".join(accessions))
    return "; ".join(parts)


def e8_evidence(package: dict, edges_doc: dict, extraction_rows: list,
                leaves: dict, resolver_index: dict) -> dict:
    """Release evidence: authentic examples by preregistered hash-min
    selection.  ABSENT (candidate count 0) is a result, not an error."""
    domain_of = domain_map(leaves)
    dom = domain_of_fn(domain_of)
    edges = edges_doc.get("edges", [])
    edges_by_key = {edge["relationship_key"]: edge for edge in edges}
    revisions_by_kind: dict = {}
    for revision in package.get("magnitude_revisions", []):
        revisions_by_kind.setdefault(revision.get("revision_kind"),
                                     []).append(revision)

    def parties_in_domain(edge, d):
        return [
            edge["direction"][side]
            for side in ("from_issuer_id", "to_issuer_id")
            if dom(edge["direction"][side]) == d
        ]

    candidates = {
        d: {kind: [] for kind in EVIDENCE_KINDS} for d in DOMAINS
    }
    for d in DOMAINS:
        outgoing: list = []
        incoming: list = []
        facts: list = []
        unknown: list = []
        contradiction: list = []
        stale: list = []
        for edge in edges:
            for party in parties_in_domain(edge, d):
                item = edge["relationship_key"] + "@" + party
                if party in set(edge.get("asserting_parties", [])):
                    outgoing.append(item)
                else:
                    incoming.append(item)
            if parties_in_domain(edge, d):
                if edge.get("magnitude_state") == "disclosed":
                    facts.append(edge["relationship_key"])
                elif edge.get("magnitude_state") == "undisclosed":
                    unknown.append(edge["relationship_key"])
                if (edge.get("magnitude_state") == "conflicted"
                        or edge.get("conflicts")):
                    contradiction.append(edge["relationship_key"])
                if edge.get("freshness_state") == "stale":
                    stale.append(edge["relationship_key"])
        corrections = [
            revision["revision_id"]
            for revision in revisions_by_kind.get("restatement", [])
            if revision.get("relationship_key") in edges_by_key
            and parties_in_domain(edges_by_key[revision["relationship_key"]], d)
        ]
        reassertions = [
            revision["revision_id"]
            for revision in revisions_by_kind.get("reassertion", [])
            if revision.get("relationship_key") in edges_by_key
            and parties_in_domain(edges_by_key[revision["relationship_key"]], d)
        ]
        valid_hops: list = []
        invalid_hops: list = []
        for ab in edges:
            if not parties_in_domain(ab, d):
                continue
            for bc in edges:
                if ab is bc:
                    continue
                if (ab["direction"]["to_issuer_id"]
                        != bc["direction"]["from_issuer_id"]):
                    continue
                ok, _reason = path_validity(ab, bc)
                item = ab["relationship_key"] + "|" + bc["relationship_key"]
                (valid_hops if ok else invalid_hops).append(item)
        candidates[d] = {
            "outgoing_query": outgoing,
            "incoming_query": incoming,
            "quantitative_fact": facts,
            "unknown_magnitude": unknown,
            "anonymous_counterparty": [
                row["non_edge_key"]
                for row in package.get("non_edges", [])
                if row.get("anonymous_alias") is not None
                and dom(row.get("subject_issuer_id")) == d
            ],
            "contradiction": contradiction,
            "stale_evidence": stale,
            "correction": corrections,
            "next_publication_reassertion": reassertions,
            "valid_multi_hop": valid_hops,
            "invalid_multi_hop": invalid_hops,
        }

    non_edges_by_key = {
        row["non_edge_key"]: row for row in package.get("non_edges", [])
    }
    revisions_by_id = {
        revision["revision_id"]: revision
        for revision in package.get("magnitude_revisions", [])
    }

    def line_for(kind, d, item_id):
        if kind in ("outgoing_query", "incoming_query"):
            relationship_key, _sep, party = item_id.partition("@")
            edge = edges_by_key[relationship_key]
            own = party in set(edge.get("asserting_parties", []))
            return _edge_line(edge, resolver_index) + "; party {} ({})".format(
                name_of(party, resolver_index),
                "own filing" if own else "counterparty filing",
            )
        if kind in ("quantitative_fact", "unknown_magnitude",
                    "contradiction", "stale_evidence"):
            return _edge_line(edges_by_key[item_id], resolver_index)
        if kind == "anonymous_counterparty":
            row = non_edges_by_key[item_id]
            return "{} {} -> anonymous ({}); accession {}".format(
                row.get("species"),
                name_of(row.get("subject_issuer_id"), resolver_index),
                row.get("non_edge_reason"), row.get("accession"),
            )
        if kind in ("correction", "next_publication_reassertion"):
            revision = revisions_by_id[item_id]
            edge = edges_by_key.get(revision.get("relationship_key"))
            head = "{} {} on {}".format(
                revision.get("revision_kind"), item_id,
                revision.get("relationship_key"),
            )
            if edge is not None:
                head += " ({} {} -> {})".format(
                    edge.get("species"),
                    name_of(edge["direction"]["from_issuer_id"],
                            resolver_index),
                    name_of(edge["direction"]["to_issuer_id"], resolver_index),
                )
            accession = (revision.get("source_ref") or {}).get("accession")
            if accession:
                head += "; accession " + accession
            return head
        if kind in ("valid_multi_hop", "invalid_multi_hop"):
            ab_key, bc_key = item_id.split("|", 1)
            ab, bc = edges_by_key[ab_key], edges_by_key[bc_key]
            text = "{} {} -> {} | {} {} -> {}".format(
                ab.get("species"),
                name_of(ab["direction"]["from_issuer_id"], resolver_index),
                name_of(ab["direction"]["to_issuer_id"], resolver_index),
                bc.get("species"),
                name_of(bc["direction"]["from_issuer_id"], resolver_index),
                name_of(bc["direction"]["to_issuer_id"], resolver_index),
            )
            _ok, reason = path_validity(ab, bc)
            if kind == "invalid_multi_hop":
                text += "; reason " + str(reason)
            return text
        return item_id

    kinds = []
    for d in DOMAINS:
        for kind in EVIDENCE_KINDS:
            unique = sorted(set(candidates[d][kind]))
            if not unique:
                kinds.append({
                    "domain": d,
                    "kind": kind,
                    "state": "ABSENT",
                    "candidates": 0,
                    "selected": None,
                    "line": None,
                })
                continue
            selected = select_evidence(kind, unique)
            kinds.append({
                "domain": d,
                "kind": kind,
                "state": "FOUND",
                "candidates": len(unique),
                "selected": selected,
                "line": line_for(kind, d, selected),
            })
    return {
        "kinds": kinds,
        "selection": (
            "sha256('{}:'+kind+':'+item_id), minimum hex".format(EVIDENCE_SALT)
        ),
    }
