"""GS-local watch-condition evaluator: pure lifecycle over recorded evidence.

IM18 engine half (ORCH-5 CONTRACT_WATCH.md, frozen 2026-10-31). A watch is a
declared condition over one surveillance scope; :func:`evaluate_watch` folds
one evaluation of recorded IM12/IM15 evidence plus the previous evaluation row
into the next row. The evaluator is a pure function over its inputs (the
caller persists rows) and never mutates them.

Lifecycle precedence mirrors the R14 §7 state grammar — Abstain > Stale >
Corrected > Qualified — with expiry decided before any evidence is consulted
and missing evidence never resolving an active watch: it pauses the evaluation
instead. A row is one of six states (``STATES``) reached by one of the closed
transition tokens (``TRANSITIONS``); counts and trigger timestamps are
lifecycle history, never a sizing or ranking input, and there is no score,
no composite and no forecast anywhere in the row.

Declared, not built here: escalation, acknowledgement, delivery and Saved
persistence are owned by the IM08/IM09 investigation workflow; the
``track_record`` field stays None with the ``track_record_unavailable``
caveat until that owner exists.

Contract-silent choices, documented here and pinned by tests:
* rules 2–4 name no transition for rows without an active trigger; those rows
  carry the state-named token ``pending``/``withheld`` (``paused`` replaces
  ``withheld`` whenever the previous row holds an active trigger), and a
  repeated evaluation re-reports the same token rather than ``none`` —
  ``none`` stays reserved for the contract's named cases (step-6 no-change
  and an already-expired row).
* an expired row consults no evidence: ``evidence_considered`` is 0 and
  nothing is consumed, while the trigger history is carried, not resolved.
* ``seen_qualified`` turns True only on evidence the watch actually stood on
  (fresh, qualified rows from rules 5–6); an abstained or stale offer never
  counts as the watch's first qualified observation.
* a corrected row that lands ``met`` sets ``first_triggered_at`` when it is
  still unset, exactly like a ``qualified`` transition.
* ``dependency_id`` aliases ``evaluation_id``; it enters the id hash as null
  because hashing its own alias would be circular.
* among fully tied candidates (same window end, same visibility instant) the
  ascending evidence id picks the latest, per the contract's sort order.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone

from engine.intl_global_dislocation import (
    CONTRACT_VERSION as DISLOCATION_CONTRACT_VERSION,
    KINDS as DISLOCATION_KINDS,
)
from engine.intl_global_observation import (
    CURRENCY_BASES,
    CONTRACT_VERSION as OBSERVATION_CONTRACT_VERSION,
)

CONTRACT_VERSION = "intl-global-watch-v1"

CONDITION_KINDS = ("dislocation_attention", "observation_qualified")
#: Condition families the programme has declared but not yet frozen a
#: contract for; naming one is a request error, never a silent pass.
DECLARED_NOT_IMPLEMENTED = ("transmission_status", "dollar_credit_state",
                            "scenario_threshold")

STATES = ("pending", "armed", "triggered", "withheld", "corrected", "expired")
TRANSITIONS = ("pending", "withheld", "paused", "first_observation",
               "qualified", "persisted", "resolved", "revised", "expired",
               "none")
CONDITION_DIRECTIONS = ("above", "below", "any")

WATCH_FIELDS = ("watch_id", "condition", "scope", "created_at", "expires_at",
                "evidence_due_at", "max_evidence_age_days")
SCOPE_FIELDS = ("universe_id", "horizon", "currency_basis")
DISLOCATION_CONDITION_FIELDS = ("kind", "dislocation_kind", "attention",
                                "direction")
OBSERVATION_CONDITION_FIELDS = ("kind",)

CAVEATS = ("track_record_unavailable",)
INTERPRETATION_LIMITS = (
    "A watch reports whether recorded evidence meets a stated condition; it "
    "is not a forecast.",
    "Escalation and acknowledgement are owned by the incumbent investigation "
    "workflow.",
)

#: The exact row key set, in canonical order. ``evaluation_id`` is the sha256
#: of the canonical JSON of the row minus ``evaluation_id``, ``evaluated_at``,
#: ``last_check``, ``evidence_age_days``, ``transition`` and ``previous``
#: (with ``dependency_id`` at its hashing-time null alias).
ROW_KEYS = (
    "contract_version", "watch_id", "evaluation_id", "evaluated_at",
    "condition", "scope", "state", "outcome", "reasons", "prior_state",
    "transition", "active_trigger", "seen_qualified", "first_triggered_at",
    "consecutive_triggered", "evidence_ref", "evidence_age_days",
    "last_check", "supersedes", "previous", "caveats", "track_record",
    "interpretation_limits", "dependency_id", "consumes",
)

_ID_EXCLUDED = frozenset({"evaluation_id", "evaluated_at", "last_check",
                          "evidence_age_days", "transition", "previous"})


class WatchError(ValueError):
    """Malformed watch request. The contract never guesses a condition."""


# ---------------------------------------------------------------------------
# Instants and dates (ISO-8601 in, comparable UTC values out)
# ---------------------------------------------------------------------------

def _parse_instant(value) -> "datetime | None":
    """UTC instant of an ISO-8601 string (Z, offset or naive = UTC), or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:  # a naive value is UTC
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _instant(value, token: str) -> datetime:
    moment = _parse_instant(value)
    if moment is None:
        raise WatchError(token)
    return moment


def _optional_instant(value, token: str) -> "datetime | None":
    return None if value is None else _instant(value, token)


def _norm(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_date(value) -> "date | None":
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Evidence accessors (observation-v1 and dislocation-v1 output rows)
# ---------------------------------------------------------------------------

def _clocks(record: dict) -> dict:
    clocks = record.get("clocks")
    return clocks if isinstance(clocks, dict) else {}


def _clock_instant(record: dict, name: str) -> "datetime | None":
    clock = _clocks(record).get(name)
    return _parse_instant(clock.get("at")) if isinstance(clock, dict) else None


def _is_dislocation(record: dict) -> bool:
    return record.get("contract_version") == DISLOCATION_CONTRACT_VERSION


def _is_observation(record: dict) -> bool:
    return record.get("contract_version") == OBSERVATION_CONTRACT_VERSION


def _evidence_id(record: dict):
    value = (record.get("dislocation_id") if _is_dislocation(record)
             else record.get("observation_id"))
    return value if isinstance(value, str) and value.strip() else None


def _evidence_kind(record: dict):
    if _is_dislocation(record):
        return record.get("kind")
    return "observation"


def _scope_of(record: dict) -> dict:
    """universe_id / horizon / currency_basis / window pair of the record."""
    if _is_dislocation(record):
        subject = record.get("subject")
        return subject if isinstance(subject, dict) else {}
    identity = record.get("identity")
    return identity if isinstance(identity, dict) else {}


def _window(record: dict) -> "tuple[str, str]":
    scope = _scope_of(record)
    return scope.get("window_start"), scope.get("window_end")


def _visibility(record: dict) -> "datetime | None":
    """Instant from which the record is visible, or None when never.

    Dislocation: the computation clock, pushed later by the ingestion clock
    when one is carried (a carried but unreadable clock is never visible).
    Observation: the ingestion rule — exact/upper_bound from its instant,
    session_date from the next day 00:00Z, missing never.
    """
    if _is_dislocation(record):
        seen = _clock_instant(record, "computation")
        if seen is None:
            return None
        clock = _clocks(record).get("ingestion")
        if isinstance(clock, dict):
            ingested = _parse_instant(clock.get("at"))
            if ingested is None:
                return None  # carried but unreadable: visibility unknowable
            if ingested > seen:
                seen = ingested
        return seen
    if _is_observation(record):
        clock = _clocks(record).get("ingestion")
        if not isinstance(clock, dict):
            return None
        at = _parse_instant(clock.get("at"))
        if at is None:
            return None
        if clock.get("precision") == "session_date":
            return at.replace(hour=0, minute=0, second=0,
                              microsecond=0) + timedelta(days=1)
        return at
    return None


def _is_relevant(record: dict, condition: dict) -> bool:
    """The record belongs to this watch's condition family and scope."""
    if condition["kind"] == "dislocation_attention":
        if not _is_dislocation(record):
            return False
        if record.get("kind") != condition["dislocation_kind"]:
            return False
    else:  # observation_qualified
        if not _is_observation(record):
            return False
    scope = _scope_of(record)
    if any(scope.get(field) is None for field in SCOPE_FIELDS):
        return False
    if _evidence_id(record) is None or _as_date(_window(record)[1]) is None:
        return False
    return True


def _matches_scope(record: dict, watch_scope: dict) -> bool:
    scope = _scope_of(record)
    return all(scope.get(field) == watch_scope[field]
               for field in SCOPE_FIELDS)


def _outcome(record: dict, condition: dict) -> str:
    """met / not_met of the fresh qualified evidence for this condition."""
    if condition["kind"] == "observation_qualified":
        return "met" if record.get("state") == "qualified" else "not_met"
    evidence = record.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    if evidence.get("attention") != "outside_reference_range":
        return "not_met"
    if condition["direction"] == "any":
        return "met"
    return "met" if evidence.get("direction") == condition["direction"] \
        else "not_met"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(watch) -> tuple[dict, dict, "datetime | None", "datetime | None"]:
    if not isinstance(watch, dict) or set(watch) != set(WATCH_FIELDS):
        raise WatchError("watch_fields")
    watch = deepcopy(watch)
    if not isinstance(watch["watch_id"], str) or not watch["watch_id"].strip():
        raise WatchError("watch_id")
    condition = watch["condition"]
    if not isinstance(condition, dict):
        raise WatchError("condition")
    kind = condition.get("kind")
    if kind in DECLARED_NOT_IMPLEMENTED:
        raise WatchError(f"condition_not_implemented:{kind}")
    if kind not in CONDITION_KINDS:
        raise WatchError("condition_unknown")
    if kind == "dislocation_attention":
        if set(condition) != set(DISLOCATION_CONDITION_FIELDS):
            raise WatchError("condition_fields")
        if condition["dislocation_kind"] not in DISLOCATION_KINDS:
            raise WatchError("condition_dislocation_kind")
        if condition["attention"] != "outside_reference_range":
            raise WatchError("condition_attention")
        if condition["direction"] not in CONDITION_DIRECTIONS:
            raise WatchError("condition_direction")
    elif set(condition) != set(OBSERVATION_CONDITION_FIELDS):
        raise WatchError("condition_fields")
    scope = watch["scope"]
    if (not isinstance(scope, dict) or set(scope) != set(SCOPE_FIELDS)
            or any(not isinstance(scope[field], str) or not scope[field].strip()
                   for field in SCOPE_FIELDS)
            or scope["currency_basis"] not in CURRENCY_BASES):
        raise WatchError("scope")
    _instant(watch["created_at"], "created_at")
    expires = _optional_instant(watch["expires_at"], "expires_at")
    due = _optional_instant(watch["evidence_due_at"], "evidence_due_at")
    max_age = watch["max_evidence_age_days"]
    if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 1:
        raise WatchError("max_evidence_age_days")
    return watch, scope, expires, due


# ---------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------

def evaluate_watch(watch, evidence, *, evaluated_at, previous=None) -> dict:
    """Fold one evaluation of recorded evidence into the next lifecycle row.

    ``evidence`` is a list of observation-v1 or dislocation-v1 output rows;
    only relevant, point-in-time-visible records are considered, the latest
    one decides, and every input is deep-copied and left unmutated.
    """
    watch, scope, expires, due = _validate(watch)
    condition = watch["condition"]
    if not isinstance(evidence, list):
        raise WatchError("evidence_must_be_a_list")
    evidence = deepcopy(evidence)
    moment = _instant(evaluated_at, "evaluated_at")
    if moment < _instant(watch["created_at"], "created_at"):
        raise WatchError("evaluated_before_created")
    if previous is not None:
        if not isinstance(previous, dict):
            raise WatchError("previous_row")
        if previous.get("watch_id") != watch["watch_id"]:
            raise WatchError("previous_watch_mismatch")
        previous = deepcopy(previous)

    prior_state = previous.get("state") if previous else None
    prev_active = bool(previous.get("active_trigger")) if previous else False
    prev_count = int(previous.get("consecutive_triggered") or 0) \
        if previous else 0
    prev_seen = bool(previous.get("seen_qualified")) if previous else False
    prev_first = previous.get("first_triggered_at") if previous else None
    prev_first = (_norm(_instant(prev_first, "first_triggered_at"))
                  if prev_first is not None else None)
    prev_ref = previous.get("evidence_ref") if previous else None
    prev_ref = prev_ref if isinstance(prev_ref, dict) else None
    prev_eid = prev_ref.get("evidence_id") if prev_ref else None

    # Latest relevant visible evidence: greatest window_end, then latest
    # visibility instant, then ascending evidence id.
    considered = []
    for record in evidence:
        if not isinstance(record, dict):
            continue
        if not _is_relevant(record, condition):
            continue
        if not _matches_scope(record, scope):
            continue
        if _visibility(record) is None or _visibility(record) > moment:
            continue
        considered.append(record)
    latest = None
    if considered:
        def _rank(record: dict):
            return (_as_date(_window(record)[1]), _visibility(record))

        top = max(considered, key=_rank)
        tied = [record for record in considered if _rank(record) == _rank(top)]
        latest = min(tied, key=_evidence_id)

    supersedes = None
    if expires is not None and moment >= expires:
        # Rule 1: expiry is decided before any evidence is consulted.
        state, outcome, reasons = "expired", None, []
        transition = "none" if prior_state == "expired" else "expired"
        evidence_ref, age_days, consumes = None, None, []
        active, count, seen = prev_active, prev_count, prev_seen
        first = prev_first
        considered_count = 0
    elif latest is None:
        # Rule 2: missing data never resolves; it pauses or awaits.
        if prev_active:
            state, reasons, transition = "withheld", ["evidence_missing"], "paused"
        elif due is None or moment < due:
            state, reasons, transition = ("pending",
                                          ["awaiting_first_evidence"], "pending")
        else:
            state, reasons, transition = "withheld", ["evidence_missing"], "withheld"
        outcome, evidence_ref, age_days, consumes = None, None, None, []
        active, count, seen, first = (prev_active, prev_count, prev_seen,
                                      prev_first)
        considered_count = 0
    else:
        window_start, window_end = _window(latest)
        age_days = (moment.date() - _as_date(window_end)).days
        evidence_ref = {"evidence_id": _evidence_id(latest),
                        "kind": _evidence_kind(latest),
                        "window_start": window_start,
                        "window_end": window_end,
                        "state": latest.get("state")}
        consumes = [_evidence_id(latest)]
        considered_count = len(considered)
        if latest.get("state") == "abstain":
            # Rule 3: abstain carries its own closed reasons, verbatim.
            state, outcome = "withheld", None
            reasons = list(latest.get("abstain_reasons") or [])
            transition = "paused" if prev_active else "withheld"
            active, count, seen, first = (prev_active, prev_count, prev_seen,
                                          prev_first)
        elif age_days > watch["max_evidence_age_days"]:
            # Rule 4: a too-old window withholds before any revision counts.
            state, outcome, reasons = "withheld", None, ["evidence_stale"]
            transition = "paused" if prev_active else "withheld"
            active, count, seen, first = (prev_active, prev_count, prev_seen,
                                          prev_first)
        elif (prev_eid is not None and prev_eid != _evidence_id(latest)
              and prev_ref.get("kind") == _evidence_kind(latest)
              and _as_date(prev_ref.get("window_start"))
              == _as_date(window_start)
              and _as_date(prev_ref.get("window_end"))
              == _as_date(window_end)):
            # Rule 5: a revision of the same window under a new id.
            outcome = _outcome(latest, condition)
            state, reasons, transition = "corrected", [], "revised"
            supersedes = prev_eid
            active = outcome == "met"
            count = max(1, prev_count) if active else 0
            first = (prev_first or _norm(moment)) if active else prev_first
            seen = True
        else:
            # Rule 6: qualified evidence, met or not.
            outcome = _outcome(latest, condition)
            met = outcome == "met"
            state = "triggered" if met else "armed"
            reasons = []
            if not prev_seen:
                transition = "first_observation"
                active, count = met, (1 if met else 0)
                first = (prev_first or _norm(moment)) if met else prev_first
            elif prev_eid == _evidence_id(latest) and prior_state == state:
                transition = "none"
                active, count, first = prev_active, prev_count, prev_first
            elif met and not prev_active:
                transition = "qualified"
                active, count = True, 1
                first = prev_first or _norm(moment)
            elif met and prev_active and prev_eid != _evidence_id(latest):
                transition = "persisted"
                active, count = True, prev_count + 1
                first = prev_first or _norm(moment)
            elif not met and prev_active:
                transition = "resolved"
                active, count, first = False, 0, prev_first
            else:
                transition = "none"
                active, count, first = prev_active, prev_count, prev_first
            seen = True

    row = {
        "contract_version": CONTRACT_VERSION,
        "watch_id": watch["watch_id"],
        "evaluation_id": None,
        "evaluated_at": _norm(moment),
        "condition": condition,
        "scope": scope,
        "state": state,
        "outcome": outcome,
        "reasons": reasons,
        "prior_state": prior_state,
        "transition": transition,
        "active_trigger": active,
        "seen_qualified": seen,
        "first_triggered_at": first,
        "consecutive_triggered": count,
        "evidence_ref": evidence_ref,
        "evidence_age_days": age_days,
        "last_check": {"at": _norm(moment),
                       "evidence_offered": len(evidence),
                       "evidence_considered": considered_count},
        "supersedes": supersedes,
        "previous": None,
        "caveats": list(CAVEATS),
        "track_record": None,
        "interpretation_limits": list(INTERPRETATION_LIMITS),
        "dependency_id": None,  # aliases evaluation_id; null while hashing
        "consumes": consumes,
    }
    if previous is not None:
        embedded = deepcopy(previous)
        embedded["previous"] = None
        row["previous"] = embedded
    payload = {key: value for key, value in row.items()
               if key not in _ID_EXCLUDED}
    digest = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    row["evaluation_id"] = f"watch:sha256:{digest}"
    row["dependency_id"] = row["evaluation_id"]
    return row
