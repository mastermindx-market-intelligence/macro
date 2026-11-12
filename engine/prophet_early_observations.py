"""Lossless, read-only B03 projection of the existing private Turn Watch sidecar.

This is an observation population, not the qualified candidate pool, B1 episode
writer or an entry decision. Consumers must enforce entitlement before reading it.
The source's logical session close is never substituted for a capture/publication
clock. Identity resolution uses the current canonical reference and makes no claim
that today's aliases were available at a historical decision.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections.abc import Mapping
from typing import Any
from datetime import date
from hashlib import sha256
from pathlib import Path
from threading import Lock
from types import MappingProxyType

from engine.us_candidate_episode import (
    EpisodeContractError,
    attest_candidate_episode_store_bytes,
    canonical_json,
    load_candidate_episode_store_snapshot,
)
from engine.us_candidate_episode_intake import IdentitySpine, TURN_WATCH_SCHEMA, _source_id

SCHEMA = "prophet.early_observations/v1"
AUTHORITY = {"buy": False, "alert": False, "entry_open": False,
             "rank": False, "size": False, "episode_write": False}
#: Typed source-bound coverage slots — every per-query result resolves to exactly one
#: of these four literals.  An absent row alone NEVER means "evaluated": a ticker
#: that is in the active universe but absent from the current observation set is
#: :data:`SOURCE_COVERAGE_IN_UNIVERSE_NO_RECORDED_TRIGGER`, not a fabricated verdict.
SOURCE_COVERAGE_NOT_IN_UNIVERSE = "NOT_IN_UNIVERSE"
SOURCE_COVERAGE_IN_UNIVERSE_NO_RECORDED_TRIGGER = "IN_UNIVERSE_NO_RECORDED_TRIGGER"
SOURCE_COVERAGE_UNAVAILABLE = "UNAVAILABLE"
SOURCE_COVERAGE_VERIFIED = "VERIFIED_SOURCE_PARTITION"
_SECURITY = re.compile(r"SEC:[A-Za-z0-9][A-Za-z0-9_.:-]{0,126}\Z")
_TICKER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,31}\Z")


class ObservationQueryError(ValueError):
    """An exact query, page boundary or retained snapshot is invalid."""


def _relation(state, reason, *, episode_id=None, generation_id=None):
    return {"state": state, "reason": reason, "episode_id": episode_id,
            "generation_id": generation_id}


def _index_episode_snapshot(snapshot, source_receipt=None):
    """Copy minimal immutable relations from a fully validated B1 snapshot.

    Retain cardinality and first episode match, but never event payloads or the
    large generation object. A receipt filter cannot substitute another source.
    """
    if snapshot is None:
        return None
    events, suppressions, episodes = {}, {}, {}
    for rows, index in ((snapshot.generation.events, events),
                        (snapshot.generation.suppressions, suppressions)):
        for row in rows:
            if (row.get("source_system") == "turn_watch"
                    and row.get("source_schema") == TURN_WATCH_SCHEMA
                    and (source_receipt is None or row.get("source_receipt") == source_receipt)):
                key = (row.get("source_event_id"), row.get("source_receipt"))
                fields = ("episode_id",) if index is events else ("security_id", "reason")
                index.setdefault(key, []).append(MappingProxyType({k: row.get(k) for k in fields}))
    wanted = {row["episode_id"] for matches in events.values() for row in matches}
    for row in snapshot.generation.episodes:
        # Preserve the prior first matching episode lookup, without another scan.
        if row["episode_id"] in wanted:
            episodes.setdefault(row["episode_id"], MappingProxyType({
                "episode_id": row["episode_id"], "security_id": row["security_id"],
            }))
    return (snapshot.generation_id,
            MappingProxyType({key: tuple(values) for key, values in events.items()}),
            MappingProxyType({key: tuple(values) for key, values in suppressions.items()}),
            MappingProxyType(episodes))


def _relation_index_bytes(value):
    """Conservative retained-size bound, counting shared strings more than once."""
    if isinstance(value, Mapping):
        return sys.getsizeof(value) + sys.getsizeof(dict(value)) + sum(
            _relation_index_bytes(k) + _relation_index_bytes(v) for k, v in value.items())
    if isinstance(value, tuple):
        return sys.getsizeof(value) + sum(_relation_index_bytes(v) for v in value)
    return sys.getsizeof(value)


class _AttestedRelationCache:
    """One compact entry; every reuse re-reads all B1 bytes through its owner.

    Cold reads still perform full semantic validation. No stale entry survives a
    failed read, and concurrent requests cannot publish a partially built index.
    """
    max_bytes = 4 * 1024 * 1024

    def __init__(self):
        self._lock = Lock()
        self._entry = None

    def read(self, root, source_receipt):
        with self._lock:
            try:
                token = attest_candidate_episode_store_bytes(root)
                key = (str(Path(root).resolve()), token, source_receipt)
                if self._entry is not None and self._entry[0] == key:
                    return self._entry[1]
                self._entry = None
                snapshot = load_candidate_episode_store_snapshot(root)
                index = _index_episode_snapshot(snapshot, source_receipt)
                # A concurrent publication or corruption during the cold read
                # must not bind its derived relations to the earlier byte token.
                if (snapshot.generation_id != token.generation_id
                        or attest_candidate_episode_store_bytes(root) != token):
                    raise EpisodeContractError("B1 generation changed during relation read")
                if _relation_index_bytes(index) <= self.max_bytes:
                    self._entry = (key, index)
                return index
            except Exception:
                self._entry = None
                raise


_RELATION_CACHE = _AttestedRelationCache()


def _episode_relation(event_id, receipt, security, index):
    if security is None:
        return _relation("IDENTITY_UNRESOLVED", "CANONICAL_IDENTITY_UNAVAILABLE")
    if index is None:
        return _relation("EPISODE_JOIN_UNAVAILABLE", "B1_SNAPSHOT_UNAVAILABLE")
    gid, event_index, suppression_index, episode_index = index
    # Match the immutable source key AND receipt. A same-security episode or a
    # later correction cannot silently stand in for this observation's relation.
    events = event_index.get((event_id, receipt), ())
    suppressions = suppression_index.get((event_id, receipt), ())
    if len(events) == 1 and not suppressions:
        episode = episode_index.get(events[0]["episode_id"])
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
           "universe_coverage": {"state": SOURCE_COVERAGE_UNAVAILABLE,
                                 "reason": "ACTIVE_UNIVERSE_UNAVAILABLE",
                                 "selection_era": None,
                                 "tickers_sha256": None,
                                 "published_proof_sha256": None, "source_session": None},
           "_universe_tickers": None,
           "authority": dict(AUTHORITY)}


def _universe_coverage(active_universe, *, doc, coverage, public_contract):
    """Verify membership against the same producer bytes as the source partition."""
    out = {"state": SOURCE_COVERAGE_UNAVAILABLE,
           "reason": "ACTIVE_UNIVERSE_UNAVAILABLE", "selection_era": None,
           "tickers_sha256": None, "published_proof_sha256": None,
           "source_session": doc["data_session"]}
    if not isinstance(active_universe, dict):
        return out, None
    tickers = active_universe.get("tickers")
    digest = active_universe.get("tickers_sha256")
    era = active_universe.get("selection_era")
    if (not isinstance(tickers, list) or not tickers
            or any(not isinstance(t, str) or not _TICKER.fullmatch(t) for t in tickers)
            or tickers != sorted(set(tickers)) or not isinstance(digest, str)
            or not isinstance(era, str)
            or type(active_universe.get("population_count")) is not int
            or active_universe["population_count"] != len(tickers)):
        out["reason"] = "ACTIVE_UNIVERSE_SHAPE_INVALID"
        return out, None
    out.update(selection_era=era, tickers_sha256=digest)
    recomputed = sha256(("\n".join(tickers) + "\n").encode()).hexdigest()
    if recomputed != digest:
        out["reason"] = "ACTIVE_UNIVERSE_DIGEST_MISMATCH"
        return out, None
    from engine.us_turn_watch import selection_era_for_session
    if (doc.get("selection_era") != era
            or selection_era_for_session(doc["data_session"]) != era):
        out["reason"] = "SOURCE_UNIVERSE_ERA_MISMATCH"
        return out, None
    if coverage["state"] != SOURCE_COVERAGE_VERIFIED or not isinstance(public_contract, dict):
        out["reason"] = "SOURCE_UNIVERSE_PROOF_UNAVAILABLE"
        return out, None
    if (public_contract.get("schema") != "us_turn_watch.source_contract.v1"
            or public_contract.get("pass") is not True
            or any(public_contract.get(key) != active_universe.get(key) for key in
                   ("universe_id", "selection_era", "population_count", "tickers_sha256"))
            or active_universe.get("universe_id") != f"us-turn-watch:{era}:{digest[:12]}"
            or type(public_contract.get("selected_count")) is not int
            or public_contract["selected_count"] != len(tickers)
            or public_contract.get("universe_limit") is not None
            or type(public_contract.get("missing_store_count")) is not int
            or public_contract["missing_store_count"] != 0
            or public_contract.get("modal_session") != doc["data_session"]
            or public_contract.get("freshness_ok") is not True
            or any(row.get("ticker") not in tickers for row in doc["rows"])):
        out["reason"] = "SOURCE_UNIVERSE_PROOF_MISMATCH"
        return out, None
    out.update(state=SOURCE_COVERAGE_VERIFIED, reason=None,
               published_proof_sha256=coverage["source_artifact_receipt"].removeprefix("sha256:"))
    return out, set(tickers)


def _finite_number(value, *, positive=False, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        return None
    if (positive and value <= 0) or (nonnegative and value < 0):
        return None
    return value


def _source_date(value, latest):
    if not isinstance(value, str):
        return None
    try:
        if date.fromisoformat(value).isoformat() == value and value <= latest:
            return value
    except ValueError:
        pass
    return None


def _source_timing(row, session: str) -> dict[str, Any]:
    """Preserve actual per-stock clocks and finite native facts; missing stays unknown."""
    out = {"asof": None, "close": None, "reset_low": None, "reset_low_date": None,
           "off_reset_low_pct": None, "slow_tier_eligible": None, "slow_tier_tier": None,
           "slow_tier_bars_to_cross_3d": None, "slow_tier_blocking": None,
           "slow_tier_evaluated": None, "slow_tier_above_200dma": None}
    if not isinstance(row, dict):
        return out
    out["asof"] = _source_date(row.get("asof"), session)
    out["close"] = _finite_number(row.get("close"), positive=True)
    reset = row.get("reset")
    if isinstance(reset, dict):
        out["reset_low"] = _finite_number(reset.get("reset_low"), positive=True)
        out["reset_low_date"] = _source_date(reset.get("reset_low_date"), out["asof"] or session)
        out["off_reset_low_pct"] = _finite_number(reset.get("off_reset_low_pct"))
    slow = row.get("slow_tier")
    if isinstance(slow, dict):
        for key in ("eligible", "evaluated", "above_200dma"):
            out["slow_tier_" + key] = slow.get(key) if type(slow.get(key)) is bool else None
        tier = slow.get("tier")
        out["slow_tier_tier"] = tier if isinstance(tier, str) and len(tier) <= 32 else None
        out["slow_tier_bars_to_cross_3d"] = _finite_number(slow.get("bars_to_cross_3d"), nonnegative=True)
        blockers = slow.get("blocking")
        out["slow_tier_blocking"] = list(blockers) if (
            isinstance(blockers, list) and len(blockers) <= 100
            and all(isinstance(v, str) and len(v) <= 200 for v in blockers)) else None
    return out


def _source_coverage(doc, public_path):
    """Join only the exact producer-published partition; never assume a cap."""
    coverage = {"state": "UNAVAILABLE", "reason": "SOURCE_ARTIFACT_UNAVAILABLE",
                "total": len(doc["rows"]), "featured": None, "beyond_cap": None,
                "source_artifact_receipt": doc.get("source_artifact_sha256")}
    if public_path is None:
        return coverage, set(), None
    def require(condition):
        if not condition:
            raise ValueError("source partition")
    try:
        raw = Path(public_path).read_bytes()
        if "sha256:" + sha256(raw).hexdigest() != doc.get("source_artifact_sha256"):
            coverage["reason"] = "SOURCE_ARTIFACT_RECEIPT_MISMATCH"
            return coverage, set(), None
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
        return coverage, set(), None
    coverage.update(state="VERIFIED_SOURCE_PARTITION", reason=None, featured=len(deck), beyond_cap=len(beyond))
    return coverage, {r["ticker"] for r in deck}, public["coverage"].get("source_contract")


def load_observations(source_path: Path, *, spine: IdentitySpine | None,
                      reference_session: str, episode_root: Path | None = None,
                      public_artifact_path: Path | None = None,
                      active_universe: dict | None = None,
                      universe_proof_artifact_path: Path | None = None) -> dict:
    """Read one source byte snapshot and, optionally, one validated atomic B1 HEAD.

    A broken B1/identity read degrades only its relationships, never the observation
    population. Invalid source bytes invalidate the population rather than fabricate
    a successful zero. This function never modifies any producer or episode file.

    ``active_universe`` must describe the source session. Membership is verified
    only against the existing source contract in the exact public artifact.
    The optional legacy proof-path argument may name that same artifact.
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
    coverage, featured, public_contract = _source_coverage(doc, public_artifact_path)
    if (universe_proof_artifact_path is not None
            and universe_proof_artifact_path != public_artifact_path):
        public_contract = None
    universe_coverage, universe_tickers = _universe_coverage(
        active_universe, doc=doc, coverage=coverage, public_contract=public_contract)
    relation_index = None
    if episode_root is not None:
        try:
            relation_index = _RELATION_CACHE.read(episode_root, receipt)
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
                          "source_timing": _source_timing(row, session),
                          "lineage": {"state": "CURRENT_RECEIPT_ONLY", "current_receipt": receipt,
                              "source_event_id": event_id, "source_artifact_receipt": doc.get("source_artifact_sha256"),
                              "selection_era": doc.get("selection_era"), "anchor_era": doc.get("anchor_era"),
                              "prior_receipt": None, "correction_available_at": None},
                          "episode_relation": _episode_relation(event_id, receipt, security, relation_index),
                          "authority": dict(AUTHORITY)})
    out.update(status="CURRENT_SESSION" if session == reference_session else "RETAINED_PREVIOUS_SESSION",
               reason=None, source_receipt=receipt, rows=projected, coverage=coverage,
               universe_coverage=universe_coverage,
               _universe_tickers=universe_tickers)
    out["clocks"].update(source_session=session, logical_known_at=doc.get("known_at"))
    # Bind pagination to source, B1 generation and the actual current identity
    # projection. A changed receipt, alias resolution or B1 return invalidates it.
    material = {"source_receipt": receipt, "rows": projected, "coverage": coverage,
                "universe_coverage": universe_coverage,
                "universe_tickers": sorted(universe_tickers) if universe_tickers else None,
                "generation_id": relation_index[0] if relation_index else None,
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
    unavailable = projection["status"] == "UNAVAILABLE"
    universe_coverage = projection.get("universe_coverage") or {
        "state": SOURCE_COVERAGE_UNAVAILABLE, "reason": "ACTIVE_UNIVERSE_UNAVAILABLE"}
    universe_state = universe_coverage.get("state")
    universe_tickers = projection.get("_universe_tickers")
    universe_tickers = universe_tickers if isinstance(universe_tickers, set) else None
    subject = None
    if ticker is not None:
        subject = {"ticker": ticker.upper(), "state": SOURCE_COVERAGE_UNAVAILABLE,
                   "reason": universe_coverage.get("reason") or "SOURCE_UNAVAILABLE"}
        if not unavailable and universe_state == SOURCE_COVERAGE_VERIFIED and universe_tickers is not None:
            member = ticker.upper() in universe_tickers
            recorded = any(row["ticker"].casefold() == ticker.casefold() for row in rows)
            state = (SOURCE_COVERAGE_NOT_IN_UNIVERSE if not member else
                     SOURCE_COVERAGE_VERIFIED if recorded else
                     SOURCE_COVERAGE_IN_UNIVERSE_NO_RECORDED_TRIGGER)
            subject.update(state=state, reason=None)
    page = [_annotate_universe_coverage(row, universe_state, universe_tickers)
            for row in matched[offset:offset + limit]]
    public_keys = ("schema", "status", "reason", "source_receipt", "snapshot_id",
                   "clocks", "authority", "coverage", "universe_coverage", "market", "reference_session")
    return {**{key: projection[key] for key in public_keys if key in projection},
            "subject_coverage": subject, "rows": page,
            "counts": {"source": None if unavailable else len(rows),
                       "matched": None if unavailable else len(matched), "returned": len(page)},
            "page": {"offset": offset, "limit": limit,
                     "next_offset": offset + limit if offset + limit < len(matched) else None}}


def _annotate_universe_coverage(row: dict, universe_state, universe_tickers) -> dict:
    """Annotate only real observations; membership never creates an event."""
    verified = (universe_state == SOURCE_COVERAGE_VERIFIED and universe_tickers is not None
                and row["ticker"] in universe_tickers)
    return {**row, "source_coverage_state": SOURCE_COVERAGE_VERIFIED if verified else SOURCE_COVERAGE_UNAVAILABLE,
            "source_coverage_reason": None if verified else "SOURCE_UNIVERSE_PROOF_UNAVAILABLE"}
