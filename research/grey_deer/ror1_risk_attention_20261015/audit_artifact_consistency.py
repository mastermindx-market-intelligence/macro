"""ROR-1 offline audit of *published* artifact differences, not a new risk authority.

No I/O in audit(). Reads/prints only when invoked as a standalone research CLI.
Each reported inconsistency is qualified as artifact-local or cross-version:
neither the existing slow score nor source-native risk is recomputed.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import math
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in _REQUIRED_DOCS:
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args()
    inputs = {k: json.loads(getattr(args,k).read_text()) for k in _REQUIRED_DOCS}
    print(json.dumps(audit(inputs), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
