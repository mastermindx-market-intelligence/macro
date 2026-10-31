"""Qualified-or-abstain cross-market dislocation detection contract (IM15).

Consumes IM12 observations and emits typed, basis-explicit, four-clock
evidence for three dislocation families — index return, FX leg and 1m-block
volatility — under two always-disclosed comparison modes: ``own_history``
(this market against its own earlier non-overlapping windows) and
``cross_section_today`` (this market against peer markets in the same
window). The statistic is the MAD-scaled modified z with the published 3.5
attention rule; every threshold is a declared constant whose rationale is
pinned by a test. Research attention only: nothing here is a trading signal,
a valuation or a recommendation.

This module is a pure contract: no collector, no network, no UI, no pandas
or numpy, and no read of the frozen contagion links graph or the 14-ETF VAR.
IM12 stays the qualification authority — an abstained subject never carries
an attention label, and missing or withheld reference data is counted, never
silently smoothed away.
"""
import hashlib
import json
import math
import statistics
from copy import deepcopy
from datetime import date, datetime, timezone

from engine.intl_global_observation import (
    ABSTAIN_REASONS as OBSERVATION_ABSTAIN_REASONS,
    ObservationError,
    assert_single_basis,
    check_clocks,
)
from engine.intl_global_universe import load_universe

CONTRACT_VERSION = "intl-global-dislocation-v1"

KINDS = ("own_history_return", "own_history_fx", "own_history_volatility",
         "peer_divergence_return", "peer_divergence_fx")
DECLARED_NOT_IMPLEMENTED = ("factor_residual", "cross_asset", "instrument",
                            "peer_divergence_volatility")
COMPARISON_MODES = ("own_history", "cross_section_today")
PEER_RULES = ("same_universe_region", "all_qualified")
STATES = ("qualified", "abstain")
ATTENTION_LABELS = ("outside_reference_range", "within_reference_range")
DIRECTIONS = ("above", "below", "at_center")

MODIFIED_Z_CONSTANT = 0.6745
ATTENTION_MODIFIED_Z = 3.5
MIN_REFERENCE_OBSERVATIONS = 20
MIN_PEERS = 3
VOL_HORIZON = "1m"
VOL_BLOCK_WINDOWS = 3

THRESHOLD_RATIONALE = {
    "modified_z_constant": "0.6745 is the standard-normal 0.75 quantile, so a "
                           "MAD-scaled modified z is comparable with a standard z "
                           "under normality (Iglewicz and Hoaglin 1993)",
    "attention_modified_z": "|modified z| > 3.5 is the published potential-outlier "
                            "rule (Iglewicz and Hoaglin 1993; NIST/SEMATECH "
                            "e-Handbook of Statistical Methods, section 1.3.5.17)",
    "min_reference_observations": "smallest reference count n whose rank resolution "
                                  "1/(n+1) is below 0.05",
    "min_peers": "smallest peer count whose median stays inside the clean peers' "
                 "range when one peer is arbitrarily corrupted",
    "vol_block_windows": "horizons_d['3m'] // horizons_d['1m'] of the incumbent "
                         "performance config: one quarter of contiguous 1m windows",
}

INTERPRETATION_LIMITS = (
    "Research attention only: not a trading signal, a valuation, a reversal "
    "probability or a recommendation.",
    "own_history compares a market with its own earlier windows; "
    "cross_section_today compares it with other markets in the same window. "
    "They answer different questions.",
    "Distance from the reference centre is descriptive; it says nothing about "
    "cause, persistence or the next move.",
    "Missing or withheld data is never evidence of calm: an abstained subject "
    "carries no attention label.",
)

EXCLUSION_REASONS = ("not_qualified", "market_mismatch", "subject_market",
                     "horizon_mismatch", "window_end_mismatch", "not_point_in_time",
                     "fx_leg_unavailable", "outside_peer_group", "window_overlap",
                     "duplicate_window", "block_not_contiguous")

DISLOCATION_ABSTAIN_REASONS = frozenset({
    "subject_not_qualified", "subject_fx_leg_unavailable",
    "insufficient_reference_history", "insufficient_peers",
    "dispersion_degenerate", "subject_block_incomplete", "peer_group_unresolved",
    "clock_missing", "clock_order_violation"})


class DislocationError(ValueError):
    """Malformed dislocation request. The contract never guesses a threshold."""


# --------------------------------------------------------------------------
# Dates and instants (ISO-8601 strings in, comparable values out)
# --------------------------------------------------------------------------

def _as_date(text) -> date | None:
    """Calendar date of an ISO-8601 string; None when unusable."""
    try:
        return date.fromisoformat(str(text).strip()[:10])
    except (TypeError, ValueError):
        return None


def _as_instant(text) -> datetime | None:
    """UTC instant of an ISO-8601 string; a naive value is UTC; None if unusable."""
    try:
        moment = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


# --------------------------------------------------------------------------
# Public helpers
# --------------------------------------------------------------------------

def robust_location(values: list[float]) -> "tuple[float, float]":
    """(median, median absolute deviation) of a non-empty sample."""
    if not values:
        raise DislocationError("robust_location_requires_values")
    center = statistics.median(values)
    return center, statistics.median([abs(value - center) for value in values])


def modified_z(value: float, center: float, mad: float) -> float:
    """MAD-scaled modified z; a non-positive MAD is not a scale."""
    if mad <= 0:
        raise DislocationError("modified_z_requires_dispersion")
    return MODIFIED_Z_CONSTANT * (value - center) / mad


def rank_counts(value: float, values: list[float]) -> dict:
    """Integer counts of references strictly below, equal to and above value."""
    return {
        "below": sum(1 for item in values if item < value),
        "equal": sum(1 for item in values if item == value),
        "above": sum(1 for item in values if item > value),
        "n": len(values),
    }


def subject_value(observation: dict, kind: str) -> "float | None":
    """The leg a kind reads: value.pct for return/volatility, fx_pct for FX."""
    if kind.endswith("_fx"):
        decomposition = observation.get("decomposition")
        return decomposition.get("fx_pct") if isinstance(decomposition, dict) else None
    value = observation.get("value")
    return value.get("pct") if isinstance(value, dict) else None


def region_of(universe_id, universe: dict) -> "str | None":
    """Region of a jurisdiction id, or of an aggregate's members; else None."""
    if not isinstance(universe_id, str) or not isinstance(universe, dict):
        return None
    jurisdictions = universe.get("jurisdictions") or {}
    jurisdiction = jurisdictions.get(universe_id)
    if isinstance(jurisdiction, dict):
        return jurisdiction.get("region")
    aggregate = (universe.get("aggregates") or {}).get(universe_id)
    if not isinstance(aggregate, dict):
        return None
    regions = {jurisdictions[member].get("region") for member in
               aggregate.get("members") or [] if member in jurisdictions}
    return next(iter(regions)) if len(regions) == 1 else None


# --------------------------------------------------------------------------
# Observation accessors
# --------------------------------------------------------------------------

def _identity_of(observation: dict) -> dict:
    identity = observation.get("identity") if isinstance(observation, dict) else None
    return identity if isinstance(identity, dict) else {}


def _window_dates(observation: dict) -> "tuple[date | None, date | None]":
    identity = _identity_of(observation)
    return _as_date(identity.get("window_start")), _as_date(identity.get("window_end"))


def _is_fx_kind(kind: str) -> bool:
    return kind.endswith("_fx")


def _fx_leg_available(observation: dict) -> bool:
    decomposition = observation.get("decomposition")
    return isinstance(decomposition, dict) and decomposition.get("fx_pct") is not None


def _carried_reasons(subject: dict) -> list[str]:
    """The subject's IM12 abstain reasons, carried verbatim (sorted)."""
    reasons = sorted(subject.get("abstain_reasons") or [])
    assert all(reason in OBSERVATION_ABSTAIN_REASONS for reason in reasons), \
        "subject abstain_reasons escape the IM12 closed vocabulary"
    return reasons


def _require_kind(kind, family: str) -> None:
    if kind in DECLARED_NOT_IMPLEMENTED:
        raise DislocationError(f"kind_not_implemented:{kind}")
    if kind not in KINDS:
        raise DislocationError(f"unknown_kind:{kind}")
    if not kind.startswith(family):
        raise DislocationError(f"kind_function_mismatch:{kind}")


def _subject_abstain_reasons(subject: dict, kind: str) -> list[str]:
    reasons = []
    if subject.get("state") != "qualified":
        reasons.append("subject_not_qualified")
    if _is_fx_kind(kind) and not _fx_leg_available(subject):
        reasons.append("subject_fx_leg_unavailable")
    return reasons


# --------------------------------------------------------------------------
# Own-history candidate filtering
# --------------------------------------------------------------------------

def _own_history_exclusion(candidate: dict, subject: dict, kind: str,
                           computed: "datetime | None") -> "str | None":
    identity = _identity_of(candidate)
    start, end = _window_dates(candidate)
    if candidate.get("state") != "qualified" or start is None or end is None:
        return "not_qualified"
    if identity.get("universe_id") != _identity_of(subject).get("universe_id"):
        return "market_mismatch"
    if identity.get("horizon") != _identity_of(subject).get("horizon"):
        return "horizon_mismatch"
    ingestion = (candidate.get("clocks") or {}).get("ingestion")
    ingested = _as_instant(ingestion.get("at")) if isinstance(ingestion, dict) else None
    if ingested is None or (computed is not None and ingested > computed):
        return "not_point_in_time"
    if _is_fx_kind(kind) and not _fx_leg_available(candidate):
        return "fx_leg_unavailable"
    return None


def _sort_key_newest(observation: dict) -> tuple:
    end, observation_id = _window_dates(observation)[1], observation.get(
        "observation_id") or ""
    return (end if end is not None else date.min, observation_id)


def _subject_block(subject: dict, pool: list[dict], size: int):
    """Subject plus contiguous predecessors, oldest last; removes them from the pool."""
    block, predecessors = [subject], []
    remaining = list(pool)
    current = _window_dates(subject)[0]
    while len(block) < size and remaining:
        matches = [obs for obs in remaining if _window_dates(obs)[1] == current]
        if not matches:
            break
        pick = min(matches, key=lambda obs: obs.get("observation_id") or "")
        block.append(pick)
        predecessors.append(pick)
        remaining.remove(pick)
        current = _window_dates(pick)[0]
    return block, predecessors, remaining


def _window_filter(pool: list[dict], boundary: "date | None", protected: set):
    """Newest-first non-overlap filter; returns (keepers, per-reason counts)."""
    counts = {"duplicate_window": 0, "window_overlap": 0}
    seen = set(protected)
    kept = []
    for candidate in sorted(pool, key=_sort_key_newest, reverse=True):
        identity = _identity_of(candidate)
        pair = (identity.get("window_start"), identity.get("window_end"))
        end = _window_dates(candidate)[1]
        if pair in seen:
            counts["duplicate_window"] += 1
        elif boundary is not None and end is not None and end > boundary:
            counts["window_overlap"] += 1
        else:
            kept.append(candidate)
            seen.add(pair)
            boundary = _window_dates(candidate)[0]
    return kept, counts


def _reference_blocks(keepers: list[dict], size: int):
    """Contiguous blocks of `size` from newest-to-oldest keepers; broken windows."""
    blocks, broken, current = [], [], []
    earliest = None
    for keeper in keepers:
        if not current:
            current, earliest = [keeper], _window_dates(keeper)[0]
        elif _window_dates(keeper)[1] == earliest:
            current.append(keeper)
            earliest = _window_dates(keeper)[0]
        else:
            broken.extend(current)
            current, earliest = [keeper], _window_dates(keeper)[0]
        if len(current) == size:
            blocks.append(current)
            current = []
    broken.extend(current)
    return blocks, broken


def _block_value(block: list[dict]) -> float:
    """Uncentred RMS of a block's value.pct."""
    squares = []
    for observation in block:
        pct = (observation.get("value") or {}).get("pct")
        squares.append(pct * pct)
    return math.sqrt(sum(squares) / len(squares))


# --------------------------------------------------------------------------
# Peer candidate filtering
# --------------------------------------------------------------------------

def _peer_exclusion(candidate: dict, subject: dict, kind: str,
                    computed: "datetime | None", peer_rule: str,
                    universe: dict, kept_universe_ids: set) -> "str | None":
    identity = _identity_of(candidate)
    if candidate.get("state") != "qualified":
        return "not_qualified"
    if identity.get("universe_id") == _identity_of(subject).get("universe_id"):
        return "subject_market"
    if identity.get("horizon") != _identity_of(subject).get("horizon"):
        return "horizon_mismatch"
    candidate_end = _window_dates(candidate)[1]
    subject_end = _window_dates(subject)[1]
    if candidate_end is None or subject_end is None or candidate_end != subject_end:
        return "window_end_mismatch"
    ingestion = (candidate.get("clocks") or {}).get("ingestion")
    ingested = _as_instant(ingestion.get("at")) if isinstance(ingestion, dict) else None
    if ingested is None or (computed is not None and ingested > computed):
        return "not_point_in_time"
    if _is_fx_kind(kind) and not _fx_leg_available(candidate):
        return "fx_leg_unavailable"
    if peer_rule == "same_universe_region" and region_of(
            identity.get("universe_id"), universe) != region_of(
            _identity_of(subject).get("universe_id"), universe):
        return "outside_peer_group"
    if identity.get("universe_id") in kept_universe_ids:
        return "duplicate_window"
    return None


# --------------------------------------------------------------------------
# Receipt assembly (shared)
# --------------------------------------------------------------------------

def _receipt_clocks(subject: dict, used: list[dict], computed_at: str) -> dict:
    subject_clocks = subject.get("clocks") or {}
    clocks = {
        "observation": deepcopy(subject_clocks.get("observation")),
        "source_publication": deepcopy(subject_clocks.get("source_publication")),
    }
    ingestion = subject_clocks.get("ingestion")
    best = deepcopy(ingestion)
    best_at = _as_instant(ingestion.get("at")) if isinstance(ingestion, dict) else None
    for observation in used:
        clock = (observation.get("clocks") or {}).get("ingestion")
        at = _as_instant(clock.get("at")) if isinstance(clock, dict) else None
        if at is not None and (best_at is None or at > best_at):
            best, best_at = deepcopy(clock), at
    clocks["ingestion"] = best
    clocks["computation"] = {"at": computed_at, "precision": "exact"}
    return clocks


def _dislocation_id(kind: str, comparison_mode: str, peer_rule, subject_id, used_ids) -> str:
    payload = json.dumps({
        "contract_version": CONTRACT_VERSION, "kind": kind,
        "comparison_mode": comparison_mode, "peer_rule": peer_rule,
        "subject": subject_id, "references": sorted(used_ids),
    }, sort_keys=True, separators=(",", ":"))
    return "disl:sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _direction(value: float, center: float) -> str:
    if value > center:
        return "above"
    if value < center:
        return "below"
    return "at_center"


def _evidence(value, reference_values: list[float]) -> dict:
    center, mad = robust_location(reference_values)
    score = modified_z(value, center, mad)
    attention = ("outside_reference_range" if abs(score) > ATTENTION_MODIFIED_Z
                 else "within_reference_range")
    return {
        "statistic": "modified_z",
        "subject_value": value,
        "center": center,
        "mad": mad,
        "modified_z": score,
        "attention": attention,
        "direction": _direction(value, center),
        "rank": rank_counts(value, reference_values),
    }


def _blank_evidence() -> dict:
    return {"statistic": "modified_z", "subject_value": None, "center": None,
            "mad": None, "modified_z": None, "attention": None, "direction": None,
            "rank": None}


def _output(*, kind, comparison_mode, peer_rule, subject, clocks,
            abstain_reasons, used_observations, used_count, used_windows, offered,
            subject_block_ids, excluded, thresholds) -> dict:
    identity = _identity_of(subject)
    reasons = sorted(abstain_reasons)
    assert all(reason in DISLOCATION_ABSTAIN_REASONS for reason in reasons)
    used_ids = [observation.get("observation_id")
                for observation in used_observations]
    assert offered == used_windows + len(subject_block_ids) + sum(excluded.values()), \
        "offered must equal used windows plus subject block plus exclusions"
    state = "qualified" if not reasons else "abstain"
    return {
        "contract_version": CONTRACT_VERSION,
        "dislocation_id": _dislocation_id(
            kind, comparison_mode, peer_rule,
            subject.get("observation_id"), used_ids),
        "kind": kind,
        "comparison_mode": comparison_mode,
        "peer_rule": peer_rule,
        "subject": {
            "observation_id": subject.get("observation_id"),
            "universe_id": identity.get("universe_id"),
            "market_id": identity.get("market_id"),
            "horizon": identity.get("horizon"),
            "currency_basis": identity.get("currency_basis"),
            "return_basis": identity.get("return_basis"),
            "window_start": identity.get("window_start"),
            "window_end": identity.get("window_end"),
            "state": subject.get("state"),
            "abstain_reasons": _carried_reasons(subject),
            "decomposition": deepcopy(subject.get("decomposition")),
        },
        "clocks": clocks,
        "state": state,
        "abstain_reasons": reasons,
        "evidence": None,  # replaced by the caller
        "references": {
            "offered": offered,
            "used": used_count,
            "used_windows": used_windows,
            "used_observation_ids": sorted(used_ids),
            "subject_block_ids": sorted(subject_block_ids),
            "excluded_by_reason": dict(excluded),
        },
        "thresholds": thresholds,
        "threshold_rationale": deepcopy(THRESHOLD_RATIONALE),
        "interpretation_limits": list(INTERPRETATION_LIMITS),
        "rights": deepcopy(subject.get("rights")),
    }


# --------------------------------------------------------------------------
# Public contracts
# --------------------------------------------------------------------------

def dislocation_own_history(subject: dict, history: list[dict], *, kind: str,
                            computed_at: str) -> dict:
    """Compare one qualified subject with its own earlier non-overlapping windows."""
    _require_kind(kind, "own_history")
    entries = list(history)
    if kind == "own_history_volatility" and _identity_of(
            subject).get("horizon") != VOL_HORIZON:
        raise DislocationError("volatility_horizon")
    assert_single_basis([subject] + entries)
    computed = _as_instant(computed_at)
    volatility = kind == "own_history_volatility"

    reasons = set(_subject_abstain_reasons(subject, kind))
    subject_id = subject.get("observation_id")
    candidates = [entry for entry in entries
                  if not (isinstance(entry, dict)
                          and entry.get("observation_id") == subject_id)]
    offered = len(candidates)
    excluded = {reason: 0 for reason in EXCLUSION_REASONS}
    pool = []
    for candidate in candidates:
        reason = _own_history_exclusion(candidate, subject, kind, computed)
        if reason is None:
            pool.append(candidate)
        else:
            excluded[reason] += 1

    subject_block_ids = []
    if volatility:
        block, predecessors, pool = _subject_block(
            subject, pool, VOL_BLOCK_WINDOWS)
        subject_block_ids = [obs.get("observation_id") for obs in predecessors]
        if len(block) < VOL_BLOCK_WINDOWS:
            reasons.add("subject_block_incomplete")
        starts = [start for start, _ in (_window_dates(obs) for obs in block)
                  if start is not None]
        boundary = min(starts) if starts else None
        protected = {(_identity_of(obs).get("window_start"),
                      _identity_of(obs).get("window_end")) for obs in block}
    else:
        boundary = _window_dates(subject)[0]
        protected = {(_identity_of(subject).get("window_start"),
                      _identity_of(subject).get("window_end"))}

    keepers, window_counts = _window_filter(pool, boundary, protected)
    excluded.update(window_counts)

    if volatility:
        blocks, broken = _reference_blocks(keepers, VOL_BLOCK_WINDOWS)
        excluded["block_not_contiguous"] += len(broken)
        used_observations = [observation for block in blocks
                             for observation in block]
        reference_values = [_block_value(block) for block in blocks]
        used_windows = len(used_observations)
        used_count = len(blocks)
        value = _block_value(block)
        count_gate = used_count < MIN_REFERENCE_OBSERVATIONS
    else:
        used_observations = keepers
        reference_values = [subject_value(observation, kind)
                            for observation in used_observations]
        used_windows = len(used_observations)
        used_count = used_windows
        value = subject_value(subject, kind)
        count_gate = used_count < MIN_REFERENCE_OBSERVATIONS
    if count_gate:
        reasons.add("insufficient_reference_history")

    if reference_values:
        _, mad = robust_location(reference_values)
        if mad == 0:
            reasons.add("dispersion_degenerate")

    clocks = _receipt_clocks(subject, used_observations, computed_at)
    clock_reason = check_clocks(clocks)
    if clock_reason is not None:
        reasons.add(clock_reason)

    evidence = (_evidence(value, reference_values)
                if not reasons and value is not None else _blank_evidence())
    receipt = _output(kind=kind, comparison_mode="own_history", peer_rule=None,
                      subject=subject, clocks=clocks, abstain_reasons=reasons,
                      used_observations=used_observations, used_count=used_count,
                      used_windows=used_windows, offered=offered,
                      subject_block_ids=subject_block_ids, excluded=excluded,
                      thresholds={
                          "modified_z_constant": MODIFIED_Z_CONSTANT,
                          "attention_modified_z": ATTENTION_MODIFIED_Z,
                          "min_reference_observations": MIN_REFERENCE_OBSERVATIONS,
                          "min_peers": None,
                          "vol_block_windows": (VOL_BLOCK_WINDOWS
                                                if volatility else None)})
    receipt["evidence"] = evidence
    return receipt


def dislocation_peer_divergence(subject: dict, cross_section: list[dict], *, kind: str,
                                computed_at: str,
                                peer_rule: str = "same_universe_region",
                                universe: dict | None = None) -> dict:
    """Compare one qualified subject with peer markets in the same window."""
    _require_kind(kind, "peer_divergence")
    if peer_rule not in PEER_RULES:
        raise DislocationError(f"peer_rule:{peer_rule}")
    if universe is None:
        universe = load_universe()
    entries = list(cross_section)
    assert_single_basis([subject] + entries)
    computed = _as_instant(computed_at)

    reasons = set(_subject_abstain_reasons(subject, kind))
    subject_id = subject.get("observation_id")
    candidates = [entry for entry in entries
                  if not (isinstance(entry, dict)
                          and entry.get("observation_id") == subject_id)]
    offered = len(candidates)
    excluded = {reason: 0 for reason in EXCLUSION_REASONS}
    used = []
    kept_universe_ids = set()
    for candidate in sorted(candidates, key=lambda obs: obs.get("observation_id") or ""):
        reason = _peer_exclusion(candidate, subject, kind, computed, peer_rule,
                                 universe, kept_universe_ids)
        if reason is None:
            used.append(candidate)
            kept_universe_ids.add(_identity_of(candidate).get("universe_id"))
        else:
            excluded[reason] += 1

    reference_values = [subject_value(observation, kind) for observation in used]
    if len(used) < MIN_PEERS:
        reasons.add("insufficient_peers")
    if peer_rule == "same_universe_region" and region_of(
            _identity_of(subject).get("universe_id"), universe) is None:
        reasons.add("peer_group_unresolved")
    if reference_values:
        _, mad = robust_location(reference_values)
        if mad == 0:
            reasons.add("dispersion_degenerate")

    clocks = _receipt_clocks(subject, used, computed_at)
    clock_reason = check_clocks(clocks)
    if clock_reason is not None:
        reasons.add(clock_reason)

    value = subject_value(subject, kind)
    evidence = (_evidence(value, reference_values)
                if not reasons and value is not None else _blank_evidence())
    receipt = _output(kind=kind, comparison_mode="cross_section_today",
                      peer_rule=peer_rule, subject=subject, clocks=clocks,
                      abstain_reasons=reasons, used_observations=used,
                      used_count=len(used), used_windows=len(used),
                      offered=offered, subject_block_ids=[], excluded=excluded,
                      thresholds={
                          "modified_z_constant": MODIFIED_Z_CONSTANT,
                          "attention_modified_z": ATTENTION_MODIFIED_Z,
                          "min_reference_observations": None,
                          "min_peers": MIN_PEERS,
                          "vol_block_windows": None})
    receipt["evidence"] = evidence
    return receipt
