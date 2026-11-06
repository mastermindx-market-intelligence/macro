"""options_capability_manifest/v0 — a pure read-time adapter over existing receipts.

The manifest answers one question per receipt-backed capability: what does the
accepted source clock say, which population counts does the receipt actually
carry, and what is the honest read_state of each fact.  Each row's
``capability_id`` is its ``source_family``: the capability is the family of
source data it reads.  It is a read-time adapter only — it adds no job, store,
collector, pricer, clock, queue or plane, and nothing latches: every call
re-derives the manifest from its inputs.

This module is pure: no filesystem, no clock, no network.  The caller supplies
``now`` and the already-parsed receipt mappings, exactly as in
``engine/options_episode_coverage.py``.  No threshold is bound in v0: no named
source-age threshold for the options live tape exists at BASE, so an accepted
clock is reported with reason ``no_threshold_source`` and the consumer applies
its own threshold to ``source_asof``.  ``stale`` stays in the read-state enum
for schema stability but is unreachable in v0.

A single trailing ``Z`` is rewritten to ``+00:00`` before parsing, as the
producer's own reader does, so parsing does not depend on Python >= 3.11 ``Z``
support; fractional seconds are accepted.  An accepted clock that cannot be
expressed in UTC makes its row ``unknown`` with a ``clock_unparseable`` reason:
no receipt content raises out of ``build_manifest``.  ``session`` and
``cohort`` are caller- or constant-asserted labels, not observed facts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Any

SCHEMA = "options_capability_manifest/v0"

#: One cohort: the live-flow configured root universe at BASE d533508a4e66.
COHORT = "live_flow.configured_root_universe@d533508a4e66"

READ_STATES = ("data", "missing", "failed_read", "stale", "unknown")
CLAIM_CLASSES = ("OBSERVED", "DERIVED", "SCENARIO", "FORECAST")

#: Precedence: failed_read > missing > unknown > stale > data.
_READ_STATE_RANK = {"data": 0, "stale": 1, "unknown": 2, "missing": 3, "failed_read": 4}

_V2_SCHEMA = "live_flow.meta/v2"
_V2_CLOCK_FIELDS = (
    "cycle_started_at",
    "source_response_at_first",
    "source_response_at_last",
    "asof",
)
_V2_ASO_FIELD = "asof"
_V2_CLOCK_PROVENANCE = "live_flow.meta/v2:asof"
_FALLBACK_CLOCK_FIELD = "source_asof"
_FALLBACK_CLOCK_PROVENANCE = "live_flow_meta:source_asof"
_EOD_CLOCK_PROVENANCE = "eod252_baselines:source_asof"
_OBS_INTERVAL_FIELD = "observed_start_to_start_sec"


def build_manifest(receipts: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    """Build the v0 manifest from ``receipts`` at caller-supplied ``now``."""
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime supplied by the caller")
    if not isinstance(receipts, Mapping):
        raise TypeError("receipts must be a Mapping of receipt name to receipt value")
    now_utc = now.astimezone(timezone.utc)
    session = _session_of(receipts)
    rows = [
        _live_tape_row(receipts.get("live_flow_meta"), now_utc, session),
        _eod_baselines_row(receipts.get("eod252_baselines"), now_utc, session),
    ]
    return {
        "schema": SCHEMA,
        "evaluated_at": now_utc.isoformat(),
        "cohort": COHORT,
        "session": session,
        "rows": rows,
    }


def _session_of(receipts: Mapping[str, Any]) -> str | None:
    value = receipts.get("session")
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    if parsed.isoformat() != value:
        return None
    return value


def _parse_aware(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.utcoffset() is None:
        return None
    return parsed


def _utc_iso(stamp: datetime, reasons: list[str]) -> str | None:
    try:
        return stamp.astimezone(timezone.utc).isoformat()
    except (OverflowError, ValueError) as exc:
        _note(reasons, "clock_unparseable:" + type(exc).__name__)
        return None


def _is_finite(value: int | float) -> bool:
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _schema_label(value: Any) -> str:
    try:
        return str(value)[:64]
    except (ValueError, RecursionError):
        return "<" + type(value).__name__ + ">"


def _note(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _base_row(
    capability_id: str,
    family: str,
    owner: str,
    claim_class: str,
    session: str | None,
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "census_observed_state": "ACCEPTED_SLICE",
        "source_family": family,
        "source_owner": owner,
        "cohort": COHORT,
        "session": session,
        "claim_class": claim_class,
        "populations": {
            "requested": None,
            "configured": None,
            "captured": None,
            "qualified": None,
            "displayed": None,
        },
        "source_asof": None,
        "clock_provenance": None,
        "read_state": None,
        "entitlement": "unbound",
        "accepted_use": "unbound",
        "reasons": [],
    }


def _read_receipt(
    value: Any, reasons: list[str]
) -> tuple[str | None, Mapping[str, Any] | None]:
    """Classify the raw receipt value; (state, mapping) — state None means readable."""
    if value is None:
        _note(reasons, "receipt_absent")
        return "missing", None
    if isinstance(value, BaseException):
        _note(reasons, "read_raised:" + type(value).__name__)
        return "failed_read", None
    if not isinstance(value, Mapping):
        _note(reasons, "receipt_unparseable")
        return "failed_read", None
    return None, value


def _live_tape_clock(
    meta: Mapping[str, Any], reasons: list[str]
) -> tuple[str, datetime | None, str | None]:
    if meta.get("schema") == _V2_SCHEMA:
        return _v2_clock(meta, reasons)
    if "schema" in meta:
        _note(reasons, "unrecognized_schema:" + _schema_label(meta["schema"]))
        return "unknown", None, None
    stamp = _parse_aware(meta.get(_FALLBACK_CLOCK_FIELD))
    if stamp is None:
        _note(reasons, "no_accepted_clock")
        return "unknown", None, None
    return "data", stamp, _FALLBACK_CLOCK_PROVENANCE


def _v2_clock(
    meta: Mapping[str, Any], reasons: list[str]
) -> tuple[str, datetime | None, str | None]:
    parsed: dict[str, datetime] = {}
    for field in _V2_CLOCK_FIELDS:
        raw = meta.get(field)
        if raw is None:
            _note(reasons, "clock_incomplete:" + field)
            return "unknown", None, None
        stamp = _parse_aware(raw)
        if stamp is None:
            _note(reasons, "clock_unparseable:" + field)
            return "unknown", None, None
        parsed[field] = stamp
    if _OBS_INTERVAL_FIELD not in meta:
        _note(reasons, "clock_incomplete:" + _OBS_INTERVAL_FIELD)
        return "unknown", None, None
    interval = meta[_OBS_INTERVAL_FIELD]
    if interval is not None and (
        isinstance(interval, bool)
        or not isinstance(interval, (int, float))
        or not _is_finite(interval)
        or interval <= 0
    ):
        _note(reasons, "clock_unparseable:" + _OBS_INTERVAL_FIELD)
        return "unknown", None, None
    if not (
        parsed["cycle_started_at"]
        <= parsed["source_response_at_first"]
        <= parsed["source_response_at_last"]
        <= parsed[_V2_ASO_FIELD]
    ):
        _note(reasons, "clock_out_of_order")
        return "unknown", None, None
    return "data", parsed[_V2_ASO_FIELD], _V2_CLOCK_PROVENANCE


def _live_tape_populations(
    meta: Mapping[str, Any], row: dict[str, Any], reasons: list[str]
) -> str | None:
    """Bind the receipted counts; returns a candidate read_state or None."""
    pops = row["populations"]
    malformed = False
    for field, receipt_key in (
        ("requested", "roots_requested"),
        ("configured", "universe_n"),
        ("captured", "roots_with_source_payload"),
    ):
        value = meta.get(receipt_key)
        if value is None:
            _note(reasons, "count_absent:" + field)
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _note(reasons, "count_malformed:" + field)
            malformed = True
            continue
        pops[field] = value
        if field == "configured":
            _note(reasons, "configured_via_compat_alias:universe_n")
    _note(reasons, "qualified_not_receipted")
    _note(reasons, "displayed_unbound_v0")
    if (
        pops["captured"] is not None
        and pops["requested"] is not None
        and pops["captured"] > pops["requested"]
    ):
        _note(reasons, "population_order_violated")
        return "unknown"
    if malformed:
        return "unknown"
    return None


def _live_tape_row(
    receipt: Any, now_utc: datetime, session: str | None
) -> dict[str, Any]:
    row = _base_row(
        "option_flow.live_tape",
        "option_flow.live_tape",
        "scripts/live_flow_poller.py",
        "OBSERVED",
        session,
    )
    reasons = row["reasons"]
    if session is None:
        _note(reasons, "session_not_supplied")
    state, meta = _read_receipt(receipt, reasons)
    if state is not None:
        row["read_state"] = state
        return row
    clock_state, accepted, provenance = _live_tape_clock(meta, reasons)
    candidates = [clock_state]
    if accepted is None:
        candidates.append("unknown")
    elif accepted > now_utc:
        _note(reasons, "future_dated_clock")
        candidates.append("unknown")
    else:
        iso = _utc_iso(accepted, reasons)
        if iso is None:
            candidates.append("unknown")
        else:
            row["source_asof"] = iso
            row["clock_provenance"] = provenance
            _note(reasons, "no_threshold_source")
    pop_state = _live_tape_populations(meta, row, reasons)
    if pop_state is not None:
        candidates.append(pop_state)
    row["read_state"] = max(candidates, key=lambda s: _READ_STATE_RANK[s])
    return row


def _eod_baselines_row(
    receipt: Any, now_utc: datetime, session: str | None
) -> dict[str, Any]:
    row = _base_row(
        "option_flow.eod252_baseline",
        "option_flow.eod252_baseline",
        "scripts/build_live_flow_baselines.py",
        "DERIVED",
        session,
    )
    reasons = row["reasons"]
    if session is None:
        _note(reasons, "session_not_supplied")
    state, baselines = _read_receipt(receipt, reasons)
    if state is not None:
        row["read_state"] = state
        return row
    _note(reasons, "population_counts_log_only")
    _note(reasons, "no_threshold_source")
    stamp = _parse_aware(baselines.get(_FALLBACK_CLOCK_FIELD))
    if stamp is None:
        _note(reasons, "no_accepted_clock")
        row["read_state"] = "unknown"
        return row
    if stamp > now_utc:
        _note(reasons, "future_dated_clock")
        row["read_state"] = "unknown"
        return row
    iso = _utc_iso(stamp, reasons)
    if iso is None:
        row["read_state"] = "unknown"
        return row
    row["source_asof"] = iso
    row["clock_provenance"] = _EOD_CLOCK_PROVENANCE
    row["read_state"] = "unknown"
    return row
