"""ROR-1 offline audit of *published* artifact differences, not a new risk authority.

No I/O in audit(). Reads/prints only when invoked as a standalone research CLI.
Each reported inconsistency is qualified as artifact-local or cross-version:
neither the existing slow score nor source-native risk is recomputed.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping


class AuditError(ValueError):
    """Malformed compared observation. No inference from untrusted input."""


_NATIVE_OBSERVED_DAMAGE = frozenset({"CRACKING", "STRAINED", "CRACKED", "BROKEN"})
_REQUIRED_DOCS = (
    "site_envelope", "data_envelope", "market_state", "leadership", "market_plane"
)


def _day(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise AuditError(f"{field}: session must be dated text")
    try:
        actual = date.fromisoformat(value)
    except ValueError as e:
        raise AuditError(f"{field}: invalid date") from e
    if actual.isoformat() != value:
        raise AuditError(f"{field}: non-canonical ISO date")
    return value


def _score(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise AuditError(f"{field}: invalid score")
    if value < 0 or value > 100:
        raise AuditError(f"{field}: score out of range")
    return float(value)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def audit(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Contrast five independently published artifacts.

    This function does NOT fetch, publish, rank, gate, execute, or synthesize a
    severity. It does NOT assert which variant was served to an authenticated
    user or that differences caused October 14 losses.
    """
    if not isinstance(documents, Mapping):
        raise AuditError("documents must be a mapping")
    doc = {k: _mapping(documents.get(k)) for k in _REQUIRED_DOCS}
    findings: list[dict[str, Any]] = []
    incomplete = False
    for k in _REQUIRED_DOCS:
        if not doc[k]:
            incomplete = True
            findings.append({
                "code": k.upper() + "_MISSING",
                "classification": "unavailable_not_calm",
            })

    se = doc["site_envelope"]
    de = doc["data_envelope"]
    ms = doc["market_state"]
    lc = doc["leadership"]
    plane = doc["market_plane"]

    for k, key in (("site_envelope", "source_session"),
                   ("data_envelope", "source_session"), ("market_state", "asof"),
                   ("leadership", "asof"), ("market_plane", "asof")):
        if doc[k] and key in doc[k]:
            _day(doc[k][key], f"{k}.{key}")

    if ms:
        _score(ms.get("score"), "market_state.score")
    if plane:
        _score(_mapping(plane.get("verdict")).get("score"), "market_plane.verdict.score")

    if se:
        hazard = _mapping(se.get("hazard_summary"))
        unseen = hazard.get("unmapped_required_sources")
        if not isinstance(unseen, list):
            unseen = []
        sources = _mapping(se.get("provenance")).get("sources")
        if not isinstance(sources, list):
            sources = []
        for source in sources:
            if not isinstance(source, Mapping):
                continue
            sid = source.get("source_id")
            state = source.get("state")
            if (hazard.get("stage") is None
                    and hazard.get("stage_reason") == "required_source_state_unmapped"
                    and sid in unseen
                    and state in _NATIVE_OBSERVED_DAMAGE
                    and source.get("coverage") == "FRESH"
                    and source.get("as_of") == se.get("source_session")):
                findings.append({
                    "code": "UNMAPPED_FRESH_REQUIRED_HAZARD",
                    "classification": "confirmed_in_published_artifact",
                    "source_session": se["source_session"],
                    "source_id": sid,
                    "source_state": state,
                    "source_stage_ceiling": source.get("stage_ceiling"),
                    "asserts_contagion": False,
                    "note": (
                        "Fresh required native damage was marked unmapped; "
                        "aggregate hazard is unavailable, not calm. "
                        "This source cannot by itself claim spread or breakdown."
                    ),
                })
    if se and de and se.get("source_session") != de.get("source_session"):
        findings.append({
            "code": "ENVELOPE_SESSION_DIVERGENCE",
            "classification": "publication_variants_need_consumer_binding",
            "site_session": se.get("source_session"),
            "data_session": de.get("source_session"),
            "note": (
                "Both snapshots may be valid for their independent build times. "
                "Determine the actual serving path before asserting staleness or release failure."
            ),
        })
    if se and lc:
        sources = _mapping(se.get("provenance")).get("sources")
        if isinstance(sources, list):
            source = next((x for x in sources
                           if isinstance(x, Mapping)
                           and x.get("source_id") == "leadership-crack-latest"), {})
            if source and source.get("as_of") != lc.get("asof"):
                findings.append({
                    "code": "LEADERSHIP_SESSION_DIVERGENCE",
                    "classification": "publication_variants_need_source_binding",
                    "site_leadership_asof": source.get("as_of"),
                    "persisted_leadership_asof": lc.get("asof"),
                    "site_leadership_state": source.get("state"),
                    "persisted_leadership_state": lc.get("state"),
                    "note": (
                        "The site-facing producer may hold non-persisted or later data. "
                        "Do not promote the old data pointer or overwrite the fresh site observation."
                    ),
                })
    if plane and ms and plane.get("asof") == ms.get("asof"):
        a = _score(_mapping(plane.get("verdict")).get("score"), "market_plane.verdict.score")
        b = _score(ms.get("score"), "market_state.score")
        if a is not None and b is not None and a != b:
            findings.append({
                "code": "MARKET_PLANE_SCORE_DIVERGENCE",
                "classification": "different_generation_clocks_no_issue_time_inference",
                "source_session": plane["asof"],
                "context_plane_score": a,
                "measured_score": b,
                "plane_produced_at": plane.get("produced_at"),
                "plane_stale_flag": plane.get("stale"),
                "note": (
                    "A context-only plane and a later measured snapshot disagree "
                    "under the same displayed session label. Without common build "
                    "cutoff and consumer receipt, this is not a historical forecast error."
                ),
            })
    # Optional sixth pinned source: the native verdict's observation clock
    # may differ from a market-plane date derived from its build/processing day.
    # Matching scores prove origin; no claim that a pre-close snapshot was stale.
    world = _mapping(documents.get("world_state"))
    if world and plane:
        native = _mapping(world.get("verdict"))
        plane_verdict = _mapping(plane.get("verdict"))
        native_day = native.get("asof")
        plane_day = plane.get("asof")
        if native_day is not None:
            native_day = _day(native_day, "world_state.verdict.asof")
        src_score = _score(native.get("score"), "world_state.verdict.score")
        projected_score = _score(plane_verdict.get("score"), "market_plane.verdict.score")
        surviving_date = plane_verdict.get("source_session") or plane_verdict.get("asof")
        if (native_day and plane_day and native_day != plane_day
                and src_score is not None and projected_score == src_score
                and surviving_date != native_day):
            findings.append({
                "code": "VERDICT_SOURCE_SESSION_LOST",
                "classification": "confirmed_source_date_not_projected",
                "native_verdict_session": native_day,
                "plane_label_session": plane_day,
                "world_produced_at": world.get("produced_at"),
                "projected_verdict_score": projected_score,
                "asserts_stale_at_production": False,
                "note": (
                    "The world-state verdict carried a distinct native session, "
                    "but the market-plane verdict copy does not preserve it. "
                    "The plane label may be the processing day; legal expected "
                    "last-session and actual consumer clocks remain unverified."
                ),
            })

    freshness = _mapping(ms.get("freshness"))
    if freshness.get("any_input_stale") is True:
        ins = freshness.get("stale_inputs")
        findings.append({
            "code": "MARKET_STATE_INPUTS_STALE",
            "classification": "observed_quality_qualification",
            "source_session": ms.get("asof"),
            "stale_inputs": ins if isinstance(ins, list) else [],
            "note": "Stale constituent inputs are not proof of fresh underlying market coverage.",
        })

    return {
        "schema": "ror1.offline_artifact_consistency.v1",
        "scope": "read_only_cross_artifact_evidence",
        "status": "INCOMPLETE" if incomplete else "ARTIFACT_COMPARISON_ONLY",
        "findings": findings,
        "warning": (
            "Not a production freshness sentinel, market score, risk detector, "
            "forecast, episode lifecycle, notification receipt or trading policy."
        ),
    }


def audit_bundle(bundle: Mapping[str, Any], original_bytes: bytes) -> dict[str, Any]:
    """Replay a declared, minimized and commit-pinned fixture.

    This validates shape and exact fixture-byte identity; it does not fetch
    GitHub or independently authenticate the declared source blob hashes.
    """
    if not isinstance(bundle, Mapping) or bundle.get("schema") != "ror1.grounded_artifact_excerpt.v1":
        raise AuditError("invalid_bundle_schema")
    commit = bundle.get("macro_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise AuditError("invalid_macro_commit")
    sources = bundle.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        raise AuditError("missing_source_manifest")
    for key, val in sources.items():
        if (not isinstance(key, str) or not isinstance(val, Mapping)
                or not isinstance(val.get("blob_sha"), str)
                or not re.fullmatch(r"[a-f0-9]{40}", val["blob_sha"])):
            raise AuditError("invalid_declared_source_blob")
    return {
        "macro_commit": commit,
        "sources": dict(sources),
        "inputs_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "audit": audit(bundle.get("observations")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, help="pinned minimal source excerpt JSON")
    for name in _REQUIRED_DOCS:
        parser.add_argument("--" + name.replace("_", "-"), type=Path)
    args = parser.parse_args()
    direct = {k: getattr(args, k) for k in _REQUIRED_DOCS}
    if args.bundle is not None:
        if any(v is not None for v in direct.values()):
            parser.error("--bundle cannot be combined with separate source documents")
        raw = args.bundle.read_bytes()
        result = audit_bundle(json.loads(raw), raw)
    else:
        if any(v is None for v in direct.values()):
            parser.error("supply --bundle or all five --<source> document paths")
        result = audit({k: json.loads(v.read_text()) for k, v in direct.items()})
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
