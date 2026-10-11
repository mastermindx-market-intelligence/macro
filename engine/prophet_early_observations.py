"""Lossless, read-only B03 projection of the existing private Turn Watch sidecar.

This is an observation population, not the qualified candidate pool, B1 episode
writer or an entry decision. Consumers must enforce entitlement before reading it.
The source's logical session close is never substituted for a capture/publication
clock. Identity resolution uses the current canonical reference and makes no claim
that today's aliases were available at a historical decision.
"""
from __future__ import annotations

import json
import re
from datetime import date
from hashlib import sha256
from pathlib import Path

from engine.us_candidate_episode import (
    EpisodeContractError,
    canonical_json,
    load_candidate_episode_store_snapshot,
)
from engine.us_candidate_episode_intake import IdentitySpine, TURN_WATCH_SCHEMA, _source_id

SCHEMA = "prophet.early_observations/v1"
AUTHORITY = {"buy": False, "alert": False, "entry_open": False,
             "rank": False, "size": False, "episode_write": False}
_SECURITY = re.compile(r"SEC:[A-Za-z0-9][A-Za-z0-9_.:-]{0,126}\Z")
_TICKER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,31}\Z")


class ObservationQueryError(ValueError):
    """An exact query, page boundary or retained snapshot is invalid."""


def _relation(state, reason, *, episode_id=None, generation_id=None):
    return {"state": state, "reason": reason, "episode_id": episode_id,
            "generation_id": generation_id}


def _episode_relation(event_id, receipt, security, snapshot):
    if security is None:
        return _relation("IDENTITY_UNRESOLVED", "CANONICAL_IDENTITY_UNAVAILABLE")
    if snapshot is None:
        return _relation("EPISODE_JOIN_UNAVAILABLE", "B1_SNAPSHOT_UNAVAILABLE")
    generation = snapshot.generation
    gid = snapshot.generation_id
    # Match the immutable source key AND receipt. A same-security episode or a
    # later correction cannot silently stand in for this observation's relation.
    def matches(row):
        return (row.get("source_system") == "turn_watch"
                and row.get("source_schema") == TURN_WATCH_SCHEMA
                and row.get("source_event_id") == event_id
                and row.get("source_receipt") == receipt)
    events = [row for row in generation.events if matches(row)]
    suppressions = [row for row in generation.suppressions if matches(row)]
    if len(events) == 1 and not suppressions:
        episode = next((r for r in generation.episodes
                        if r["episode_id"] == events[0]["episode_id"]), None)
        if episode is not None and episode["security_id"] == security:
            return _relation("EXACT_EPISODE", "EXACT_B1_SOURCE_RECEIPT",
                             episode_id=episode["episode_id"], generation_id=gid)
    # An early intake refusal can precede identity binding. Its exact immutable
    # source key/receipt still establishes a source refusal, never an episode.
    if (len(suppressions) == 1 and not events
            and suppressions[0].get("security_id") in (None, security)):
        reason = suppressions[0]["reason"]
        state = {"ACTIVE_EPISODE_DIFFERENT_ANCHOR": "BLOCKED_BY_ACTIVE_EPISODE",
                 "MISSING_STRUCTURAL_ANCHOR": "NOT_YET_ANCHORED"}.get(reason, "SOURCE_SUPPRESSED")
        return _relation(state, reason, generation_id=gid)
    return _relation("EPISODE_JOIN_UNAVAILABLE", "NO_EXACT_B1_SOURCE_RECEIPT", generation_id=gid)


def unavailable_observations(reason: str) -> dict:
    """Typed failed read; never a successful empty population."""
    return {"schema": SCHEMA, "status": "UNAVAILABLE", "reason": reason,
           "source_receipt": None, "snapshot_id": None, "rows": [],
           "clocks": {"source_session": None, "logical_known_at": None,
                      "first_available_at": None, "source_available_at": None,
                      "observed_at": None, "published_at": None,
                      "actual_clock_state": "NOT_RECORDED"},
           "authority": dict(AUTHORITY)}


def _source_coverage(doc, public_path):
    """Join only the exact producer-published partition; never assume a cap."""
    coverage = {"state": "UNAVAILABLE", "reason": "SOURCE_ARTIFACT_UNAVAILABLE",
                "total": len(doc["rows"]), "featured": None, "beyond_cap": None,
                "source_artifact_receipt": doc.get("source_artifact_sha256")}
    if public_path is None:
        return coverage, set()
    def require(condition):
        if not condition:
            raise ValueError("source partition")
    try:
        raw = Path(public_path).read_bytes()
        if "sha256:" + sha256(raw).hexdigest() != doc.get("source_artifact_sha256"):
            coverage["reason"] = "SOURCE_ARTIFACT_RECEIPT_MISMATCH"
            return coverage, set()
        public = json.loads(raw)
        require(public["schema"] == "us_turn_watch.v1" and public["data_session"] == doc["data_session"])
        deck, beyond = public["deck"], public["beyond_cap"]
        require(isinstance(deck, list) and isinstance(beyond, list))
        names = [r["ticker"] for r in deck + beyond]
        original = [r["ticker"] for r in doc["rows"]]
        require(len(set(names)) == len(names) == len(original) and set(names) == set(original))
        for key, value in (("triggered", len(original)), ("deck", len(deck)), ("beyond_cap", len(beyond))):
            require(type(public["coverage"][key]) is int and public["coverage"][key] == value)
    except (OSError, ValueError, TypeError, KeyError):
        coverage["reason"] = "SOURCE_ARTIFACT_PARTITION_UNAVAILABLE"
        return coverage, set()
    coverage.update(state="VERIFIED_SOURCE_PARTITION", reason=None, featured=len(deck), beyond_cap=len(beyond))
    return coverage, {r["ticker"] for r in deck}


def load_observations(source_path: Path, *, spine: IdentitySpine | None,
                      reference_session: str, episode_root: Path | None = None,
                      public_artifact_path: Path | None = None) -> dict:
    """Read one source byte snapshot and, optionally, one validated atomic B1 HEAD.

    A broken B1/identity read degrades only its relationships, never the observation
    population. Invalid source bytes invalidate the population rather than fabricate
    a successful zero. This function never modifies any producer or episode file.
    """
    date.fromisoformat(reference_session)
    out = unavailable_observations("SOURCE_UNREADABLE")
    try:
        raw = Path(source_path).read_bytes()
    except OSError:
        return out
    try:
        doc = json.loads(raw)
        if not isinstance(doc, dict) or doc.get("schema") != TURN_WATCH_SCHEMA:
            raise ValueError("source envelope")
        rows = doc.get("rows")
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError("source rows")
        session = doc.get("data_session")
        if not isinstance(session, str) or date.fromisoformat(session).isoformat() != session:
            raise ValueError("source session")
        digest = sha256(canonical_json({k: v for k, v in doc.items()
                                       if k != "content_sha256"}).encode()).hexdigest()
        if doc.get("content_sha256") != digest:
            out["reason"] = "SOURCE_RECEIPT_INVALID"
            return out
        if session > reference_session:
            raise ValueError("source session is ahead of requested reference")
    except (ValueError, TypeError, EpisodeContractError):
        out["reason"] = "SOURCE_MALFORMED"
        return out
    receipt = "sha256:" + digest
    coverage, featured = _source_coverage(doc, public_artifact_path)
    snapshot = None
    if episode_root is not None:
        try:
            snapshot = load_candidate_episode_store_snapshot(episode_root)
        except (OSError, ValueError, EpisodeContractError):
            pass
    projected = []
    seen = set()
    for row in rows:
        event_id = _source_id("turn_watch", {"data_session": session, "row": row})
        if event_id in seen:
            out["reason"] = "SOURCE_DUPLICATE_OBSERVATION"
            return out
        seen.add(event_id)
        ticker = row.get("ticker")
        if not isinstance(ticker, str) or _TICKER.fullmatch(ticker) is None:
            out["reason"] = "SOURCE_MALFORMED"
            return out
        security = None
        if spine is not None:
            try:
                security = spine.aliases.resolve("membership", ticker, on=date.fromisoformat(session))
                if security and not spine.issuers.issuer_of_security(security):
                    security = None
            except (ValueError, TypeError):
                security = None
        triggers = row.get("triggers")
        if (not isinstance(triggers, dict)
                or any(not isinstance(t, dict) or type(t.get("fired")) is not bool
                       or type(t.get("evaluated")) is not bool for t in triggers.values())):
            out["reason"] = "SOURCE_MALFORMED"
            return out
        fired = [key for key, trigger in triggers.items()
                 if isinstance(trigger, dict) and trigger.get("fired") is True
                 and trigger.get("evaluated") is True]
        slow = row.get("slow_tier")
        blockers = slow.get("blocking") if isinstance(slow, dict) and slow.get("evaluated") is True else None
        if not isinstance(blockers, list) or any(not isinstance(v, str) for v in blockers):
            blockers = None
        projected.append({"source_event_id": event_id, "source_receipt": receipt,
                          "ticker": ticker, "security_id": security,
                          "identity_basis": "CURRENT_REFERENCE_ONLY" if security else "UNRESOLVED",
                          "source_session": session, "triggers_fired": fired,
                          "source_visibility": ("FEATURED" if ticker in featured else "BEYOND_CAP")
                              if coverage["state"] == "VERIFIED_SOURCE_PARTITION" else "UNAVAILABLE",
                          "source_evidence": {"triggers": triggers, "counterevidence": blockers,
                              "counterevidence_state": "RECORDED" if blockers is not None else "UNAVAILABLE_FIELD"},
                          "lineage": {"state": "CURRENT_RECEIPT_ONLY", "current_receipt": receipt,
                              "source_event_id": event_id, "source_artifact_receipt": doc.get("source_artifact_sha256"),
                              "selection_era": doc.get("selection_era"), "anchor_era": doc.get("anchor_era"),
                              "prior_receipt": None, "correction_available_at": None},
                          "episode_relation": _episode_relation(event_id, receipt, security, snapshot),
                          "authority": dict(AUTHORITY)})
    out.update(status="CURRENT_SESSION" if session == reference_session else "RETAINED_PREVIOUS_SESSION",
               reason=None, source_receipt=receipt, rows=projected, coverage=coverage)
    out["clocks"].update(source_session=session, logical_known_at=doc.get("known_at"))
    # Bind pagination to source, B1 generation and the actual current identity
    # projection. A changed receipt, alias resolution or B1 return invalidates it.
    material = {"source_receipt": receipt, "rows": projected, "coverage": coverage,
                "generation_id": snapshot.generation_id if snapshot else None,
                "identity_receipts": list(spine.source_receipts) if spine else []}
    out["snapshot_id"] = "early:" + sha256(canonical_json(material).encode()).hexdigest()
    return out


def query_observations(projection: dict, *, security_id: str | None = None,
                       ticker: str | None = None, offset: int = 0, limit: int = 50,
                       expected_snapshot: str | None = None) -> dict:
    """Filter the full population on the server, then take a bounded page.

    Exact ticker search also exposes unresolved identity rows; only an exact
    canonical security match can satisfy security_id. No fuzzy joins or cap.
    """
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ObservationQueryError("INVALID_PAGE")
    if security_id is not None and (not isinstance(security_id, str) or not _SECURITY.fullmatch(security_id)):
        raise ObservationQueryError("INVALID_SECURITY_ID")
    if ticker is not None and (not isinstance(ticker, str) or not _TICKER.fullmatch(ticker)):
        raise ObservationQueryError("INVALID_TICKER")
    if expected_snapshot is not None and expected_snapshot != projection["snapshot_id"]:
        raise ObservationQueryError("SNAPSHOT_CHANGED")
    rows = projection["rows"]
    matched = [row for row in rows
               if (security_id is None or row["security_id"] == security_id)
               and (ticker is None or row["ticker"].casefold() == ticker.casefold())]
    page = matched[offset:offset + limit]
    unavailable = projection["status"] == "UNAVAILABLE"
    return {**{key: value for key, value in projection.items() if key != "rows"},
            "rows": page, "counts": {"source": None if unavailable else len(rows),
                                      "matched": None if unavailable else len(matched), "returned": len(page)},
            "page": {"offset": offset, "limit": limit,
                     "next_offset": offset + limit if offset + limit < len(matched) else None}}
