"""Point-in-time replay builder over the observation/dislocation chains (IM18).

The archive is an append-only list of IM12 observations. A step asks one
question: what did the archive hold at that instant? The answer is the
as-known-at view — the records whose ingestion clock had already admitted them,
one version per slot (two versions of a slot are a correction, the loser is
superseded) — fed to the IM15 dislocation engine with the step's own instant as
the computation clock. Nothing a step can see may depend on a later record: no
ids, no counts, no reasons, not even the fact that one exists. Replay runs a
rail of such steps and compares each against the view at now.

Clock rules are the single source inside this module (the E2 lane duplicates
them; unification is a flagged follow-on). Every output instant is normalised
to ``YYYY-MM-DDTHH:MM:SSZ``. Visibility uses the ingestion clock only:
``exact``/``upper_bound`` are visible from their instant, ``session_date`` from
the next day's midnight, anything else never. Recomputing already-ingested data
is deterministic, so computation is not a visibility clock.

Research contract only: no invented signal, no causal verb, no score, no sizing
and no ranking cross this module. An unavailable input withholds with a closed
reason; the peer universe must be the one in force at the step instant, and the
current universe is never a fallback (loading it would be look-ahead).
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from engine.intl_global_dislocation import (
    KINDS as DISLOCATION_KINDS,
    dislocation_own_history,
    dislocation_peer_divergence,
)
from engine.intl_global_observation import IDENTITY_FIELDS

CONTRACT_VERSION = "intl-global-replay-v1"

#: The subject identity field excluded from the slot hash: two records equal on
#: everything else are two versions of one slot, whatever their source content.
SLOT_EXCLUDED_FIELD = "source_content_sha256"

MAX_RAIL_STEPS = 60
WITHHELD_REASONS = ("subject_not_visible", "universe_unavailable")
LAG_WITHHELD_REASONS = (None, "clock_imprecise", "clock_missing",
                        "subject_not_visible")
QUESTIONS = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")

LIMITATIONS = ("source_vintage_unavailable:dollar_credit",)

INTERPRETATION_LIMITS = (
    "Each step shows what the archive held at that instant.",
    "A row withheld at a step stays withheld; replay never fills it from later data.",
    "Future revisions, late-acquired observations and later classifications cannot change an earlier step.",
    "The lag figure appears only when both the source-publication and ingestion clocks carry exact precision.",
)

_FIXED_LATE_ROWS = {
    "Q3": "credit_funding_unadmitted",
    "Q4": "transmission_unadmitted",
    "Q5": "us_corroboration_unadmitted",
    "Q6": "thesis_unadmitted",
}


class ReplayError(ValueError):
    """Malformed replay request or archive. The contract never guesses a clock."""


# ---------------------------------------------------------------------------
# Instants
# ---------------------------------------------------------------------------

def _parse_instant(text) -> "datetime | None":
    """UTC instant of an ISO-8601 string; a naive value is UTC; None if unusable."""
    try:
        moment = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _as_moment(value) -> "datetime | None":
    """A caller-supplied instant as an aware UTC datetime (str or datetime)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return _parse_instant(value)


def normalise_instant(text) -> "str | None":
    """An ISO-8601 instant in ``YYYY-MM-DDTHH:MM:SSZ`` form, or None."""
    moment = _as_moment(text)
    return None if moment is None else moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(prefix: str, payload) -> str:
    return prefix + hashlib.sha256(
        _canonical(payload).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Visibility and slots
# ---------------------------------------------------------------------------

def _ingestion_clock(observation) -> "dict | None":
    clocks = observation.get("clocks") if isinstance(observation, dict) else None
    ingestion = clocks.get("ingestion") if isinstance(clocks, dict) else None
    return ingestion if isinstance(ingestion, dict) else None


def _visible_from(observation) -> "datetime | None":
    """The instant this record became knowable, or None when it never does.

    This is also the ordering key between versions of one slot.
    """
    ingestion = _ingestion_clock(observation)
    if ingestion is None:
        return None
    at = _parse_instant(ingestion.get("at"))
    if at is None:
        return None
    precision = ingestion.get("precision")
    if precision in ("exact", "upper_bound"):
        return at
    if precision == "session_date":
        day = at.date() + timedelta(days=1)
        return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return None


def visible_at(observation, instant) -> bool:
    """True when the ingestion clock alone admits `observation` at `instant`.

    ``exact`` and ``upper_bound`` are visible from their own instant (at ==
    instant is visible); a ``session_date`` clock is visible from the next
    day's 00:00Z; a missing, unparseable or unknown clock is never visible.
    """
    moment = _as_moment(instant)
    visible = _visible_from(observation)
    return moment is not None and visible is not None and visible <= moment


def slot_key(observation) -> str:
    """``slot:sha256:<hex>`` over the identity minus the source content hash."""
    identity = observation.get("identity") if isinstance(observation, dict) else None
    identity = identity if isinstance(identity, dict) else {}
    trimmed = {field: identity[field] for field in sorted(identity)
               if field != SLOT_EXCLUDED_FIELD}
    assert set(trimmed) <= set(IDENTITY_FIELDS) - {SLOT_EXCLUDED_FIELD}
    return _digest("slot:sha256:", trimmed)


# ---------------------------------------------------------------------------
# The as-known-at view
# ---------------------------------------------------------------------------

def _records(archive):
    for record in archive if isinstance(archive, (list, tuple)) else ():
        if isinstance(record, dict):
            yield record


def archive_diagnostics(archive) -> dict:
    """Whole-archive bookkeeping: how many records, which ones can never appear."""
    count = 0
    clock_missing = []
    for record in _records(archive):
        count += 1
        if _visible_from(record) is None:
            observation_id = record.get("observation_id")
            if observation_id is not None:
                clock_missing.append(observation_id)
    return {"observation_count": count, "clock_missing": sorted(clock_missing)}


def as_known_at(archive, instant) -> dict:
    """The archive as a step at `instant` may know it.

    Duplicate observation ids with identical content collapse to one; with
    different content the archive itself is malformed and the call raises.
    Records whose ingestion clock had not yet admitted them are simply absent:
    nothing about them — ids, counts, reasons — enters the view.
    """
    moment = _as_moment(instant)
    if moment is None:
        raise ReplayError("instant")
    by_id = {}
    for record in _records(archive):
        observation_id = record.get("observation_id")
        if observation_id in by_id:
            if _canonical(by_id[observation_id]) != _canonical(record):
                raise ReplayError("observation_id_conflict")
        else:
            by_id[observation_id] = record
    slots = {}
    for record in by_id.values():
        if not visible_at(record, moment):     # the one visibility decision
            continue
        slots.setdefault(slot_key(record), []).append(record)
    winners, superseded = {}, []
    for slot, versions in slots.items():
        # Latest visible_from wins; an exact tie goes to the ascending
        # observation_id, so the winner never depends on archive order.
        winner = versions[0]
        for record in versions[1:]:
            record_visible, winner_visible = _visible_from(record), _visible_from(winner)
            if record_visible > winner_visible or (
                    record_visible == winner_visible
                    and (record.get("observation_id") or "")
                    < (winner.get("observation_id") or "")):
                winner = record
        winners[slot] = winner
        superseded.extend(
            {"observation_id": record.get("observation_id"),
             "superseded_by": winner.get("observation_id")}
            for record in versions if record is not winner)
    visible = sorted(
        (deepcopy(winner) for winner in winners.values()),
        key=lambda record: (slot_key(record), record.get("observation_id") or ""))
    superseded.sort(key=lambda entry: entry["observation_id"] or "")
    return {"instant": normalise_instant(moment), "visible": visible,
            "superseded": superseded}


# ---------------------------------------------------------------------------
# The step-time universe
# ---------------------------------------------------------------------------

def universe_at(universe_versions, instant) -> "dict | None":
    """The universe version in force at `instant`, or None when none is.

    A date-only effective_from means 00:00Z. There is never a fallback to the
    current universe: a step with no version in force withholds instead.
    """
    moment = _as_moment(instant)
    if moment is None:
        raise ReplayError("instant")
    in_force = {}
    for entry in (universe_versions or []):
        if not isinstance(entry, dict):
            continue
        effective = _parse_instant(entry.get("effective_from"))
        universe = entry.get("universe")
        if effective is None or not isinstance(universe, dict):
            continue
        if effective in in_force:
            raise ReplayError("universe_versions")
        in_force[effective] = universe
    best = None
    for effective in sorted(in_force):
        if effective > moment:
            break
        best = in_force[effective]
    return deepcopy(best) if best is not None else None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def _lag(subject, visible: bool) -> dict:
    """Ingestion minus source-publication, only when both clocks are exact."""
    if not visible:
        return {"source_to_ingestion_seconds": None,
                "lag_withheld_reason": "subject_not_visible"}
    ingestion = _ingestion_clock(subject)
    clocks = subject.get("clocks") or {}
    publication = clocks.get("source_publication")
    publication = publication if isinstance(publication, dict) else None
    ingested_at = _parse_instant(ingestion.get("at")) if ingestion else None
    published_at = _parse_instant(publication.get("at")) if publication else None
    if ingested_at is None or published_at is None:
        return {"source_to_ingestion_seconds": None,
                "lag_withheld_reason": "clock_missing"}
    ingested_precision = ingestion.get("precision")
    published_precision = publication.get("precision")
    if ingested_precision != "exact" or published_precision != "exact":
        return {"source_to_ingestion_seconds": None,
                "lag_withheld_reason": "clock_imprecise"}
    seconds = int((ingested_at - published_at).total_seconds())
    return {"source_to_ingestion_seconds": seconds, "lag_withheld_reason": None}


def replay_step(archive, *, step_at, subject_slot, kind,
                universe_versions=None) -> dict:
    """One dislocation computed exactly as the archive held it at `step_at`.

    A step is a pure function of the visible set: the same visible set yields a
    byte-identical step under canonical JSON.
    """
    if kind not in DISLOCATION_KINDS:
        raise ReplayError("kind")
    moment = _as_moment(step_at)
    if moment is None:
        raise ReplayError("step_at")
    step_instant = normalise_instant(moment)
    known = as_known_at(archive, moment)
    visible = known["visible"]
    roster_digest = _digest("roster:sha256:", sorted(
        record.get("observation_id") for record in visible))

    subject = None
    for record in visible:
        if slot_key(record) == subject_slot:
            subject = record
            break
    others = [record for record in visible if record is not subject]

    state, withheld_reasons, receipt = "withheld", [], None
    if subject is None:
        withheld_reasons = ["subject_not_visible"]
    elif kind.startswith("own_history"):
        receipt = dislocation_own_history(
            subject, others, kind=kind, computed_at=step_instant)
        state = "computed"
    else:
        universe = universe_at(universe_versions or [], moment)
        if universe is None:
            withheld_reasons = ["universe_unavailable"]
        else:
            # universe=None would load today's universe inside the engine: that
            # is look-ahead, so it is never passed. No version in force withholds.
            receipt = dislocation_peer_divergence(
                subject, others, kind=kind, computed_at=step_instant,
                universe=universe)
            state = "computed"

    step_id = _digest("rstep:sha256:", {
        "contract_version": CONTRACT_VERSION, "step_at": step_instant,
        "subject_slot": subject_slot, "kind": kind,
        "roster_digest": roster_digest,
        "dislocation_id": receipt.get("dislocation_id") if receipt else None,
        "state": state})
    consumes = set()
    if subject is not None:
        consumes.add(subject.get("observation_id"))
    if receipt is not None:
        references = receipt.get("references") or {}
        consumes.update(references.get("used_observation_ids") or [])
        consumes.update(references.get("subject_block_ids") or [])
    return {
        "contract_version": CONTRACT_VERSION,
        "step_id": step_id,
        "step_at": step_instant,
        "subject_slot": subject_slot,
        "kind": kind,
        "state": state,
        "withheld_reasons": withheld_reasons,
        "roster_digest": roster_digest,
        "visible_count": len(visible),
        "superseded": known["superseded"],
        "receipt": receipt,
        "clocks": receipt.get("clocks") if receipt is not None else None,
        "lag": _lag(subject, subject is not None),
        "dependency_id": receipt.get("dislocation_id") if receipt is not None
        else step_id,
        "consumes": sorted(consume for consume in consumes if consume),
    }


# ---------------------------------------------------------------------------
# The rail
# ---------------------------------------------------------------------------

def _withheld_cell(step: dict) -> dict:
    return {"state": "withheld",
            "reason": (step.get("withheld_reasons") or [None])[0]}


def _q1_cell(step: dict) -> dict:
    if step["receipt"] is None:
        return _withheld_cell(step)
    receipt = step["receipt"]
    evidence = receipt.get("evidence") or {}
    return {"state": receipt.get("state"),
            "attention": evidence.get("attention"),
            "direction": evidence.get("direction")}


def _q2_cell(step: dict, kind: str) -> dict:
    if step["receipt"] is None:
        return _withheld_cell(step)
    receipt = step["receipt"]
    evidence = receipt.get("evidence") or {}
    subject = receipt.get("subject") or {}
    return {"state": receipt.get("state"),
            "decomposition": deepcopy(subject.get("decomposition")),
            "peer_attention": evidence.get("attention")
            if kind.startswith("peer_divergence") else None}


def _comparison_rows(step: dict, now_step: dict, kind: str) -> list[dict]:
    rows = []
    for question in QUESTIONS:
        if question == "Q1":
            at_step, now = _q1_cell(step), _q1_cell(now_step)
        elif question == "Q2":
            at_step, now = _q2_cell(step, kind), _q2_cell(now_step, kind)
        else:
            at_step = now = {"state": "withheld",
                             "reason": _FIXED_LATE_ROWS[question]}
        rows.append({"question": question, "at_step": at_step, "now": now,
                     "changed": _canonical(at_step) != _canonical(now),
                     "correction_note": None})
    return rows


def replay(archive, *, steps_at, subject_slot, kind, now_at,
           universe_versions=None) -> dict:
    """A rail of point-in-time steps, each compared against the view at now."""
    if kind not in DISLOCATION_KINDS:
        raise ReplayError("kind")
    now_moment = _as_moment(now_at)
    if now_moment is None:
        raise ReplayError("rail")
    moments = []
    for entry in steps_at:
        moment = _as_moment(entry)
        if moment is None:
            raise ReplayError("rail")
        moments.append(moment)
    if not 1 <= len(moments) <= MAX_RAIL_STEPS:
        raise ReplayError("rail")
    for earlier, later in zip(moments, moments[1:]):
        if later <= earlier:
            raise ReplayError("rail")
    if any(moment > now_moment for moment in moments):
        raise ReplayError("rail")

    def _step(moment: "datetime") -> dict:
        return replay_step(archive, step_at=moment.isoformat(),
                           subject_slot=subject_slot, kind=kind,
                           universe_versions=universe_versions)

    rail = [_step(moment) for moment in moments]
    now_step = _step(now_moment)
    return {
        "contract_version": CONTRACT_VERSION,
        "subject_slot": subject_slot,
        "kind": kind,
        "now_at": normalise_instant(now_moment),
        "rail": rail,
        "now": now_step,
        "at_step_vs_now": [
            {"step_id": step["step_id"], "step_at": step["step_at"],
             "rows": _comparison_rows(step, now_step, kind)}
            for step in rail],
        "archive_diagnostics": archive_diagnostics(archive),
        "limitations": list(LIMITATIONS),
        "interpretation_limits": list(INTERPRETATION_LIMITS),
    }
