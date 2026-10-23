"""Secret-free multi-account capacity selection for Shared Provider Control.

This module owns no credential bytes, provider calls, lifecycle, retries, or
persistent account registry. It deterministically selects one member from a
caller-supplied snapshot of canonical Provider Control observations.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_STATES = frozenset({"available", "cooling", "unavailable", "unknown"})
_HORIZONS = ("five_hour", "weekly", "monthly")
_EFFECT_STATES = frozenset({"proven_no_effect", "effect_unknown", "effect_observed"})
_SAFE_REFUSALS = frozenset({"usage_limit"})


class AccountPoolError(ValueError):
    """The supplied pool snapshot is malformed or unsafe to select from."""


@dataclass(frozen=True)
class UsageWindow:
    used_percent: int | float | None
    reset_at: str | None = None


@dataclass(frozen=True)
class AccountObservation:
    account_id: str
    state: str
    observed_at: str
    stale_after: str
    five_hour: UsageWindow
    weekly: UsageWindow
    monthly: UsageWindow
    concurrency_used: int | None = None
    concurrency_limit: int | None = None


@dataclass(frozen=True)
class PoolSnapshot:
    pool_id: str
    provider: str
    product: str
    generated_at: str
    required_horizons: tuple[str, ...]
    members: tuple[AccountObservation, ...]
    generation: str


@dataclass(frozen=True)
class AccountSelection:
    pool_id: str
    pool_generation: str
    account_id: str | None
    reason: str
    sticky_retained: bool


@dataclass(frozen=True)
class RolloverDecision:
    allowed: bool
    reason: str


def _id(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise AccountPoolError(f"invalid {field}")
    text = value.strip().lower()
    if _ID_RE.fullmatch(text) is None:
        raise AccountPoolError(f"invalid {field}")
    return text


def _time(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise AccountPoolError(f"invalid {field}")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AccountPoolError(f"invalid {field}") from exc
    if parsed.tzinfo is None:
        raise AccountPoolError(f"invalid {field}")
    return parsed.astimezone(timezone.utc)


def _percent(value: int | float | None) -> int | float | None:
    if value is None:
        return None
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not 0 <= value <= 100 or not math.isfinite(value)):
        raise AccountPoolError("invalid usage percent")
    return value


def _window(value: UsageWindow) -> UsageWindow:
    if not isinstance(value, UsageWindow):
        raise AccountPoolError("invalid usage window")
    reset = value.reset_at
    if reset is not None:
        _time(reset, "reset_at")
    return UsageWindow(_percent(value.used_percent), reset)


def _observation(value: AccountObservation) -> AccountObservation:
    if not isinstance(value, AccountObservation):
        raise AccountPoolError("invalid account observation")
    account = _id(value.account_id, "account_id")
    state = str(value.state or "").strip().lower()
    if state not in _STATES:
        raise AccountPoolError("invalid account state")
    observed = _time(value.observed_at, "observed_at")
    stale = _time(value.stale_after, "stale_after")
    if stale < observed:
        raise AccountPoolError("stale_after precedes observed_at")
    used, limit = value.concurrency_used, value.concurrency_limit
    if (used is None) != (limit is None):
        raise AccountPoolError("incomplete concurrency evidence")
    if used is not None:
        if any(isinstance(item, bool) or not isinstance(item, int) for item in (used, limit)):
            raise AccountPoolError("invalid concurrency evidence")
        if used < 0 or limit is None or limit <= 0 or used > limit:
            raise AccountPoolError("invalid concurrency evidence")
    return AccountObservation(
        account,
        state,
        value.observed_at,
        value.stale_after,
        _window(value.five_hour),
        _window(value.weekly),
        _window(value.monthly),
        used,
        limit,
    )


def build_snapshot(
    *,
    pool_id: str,
    provider: str,
    product: str,
    generated_at: str,
    members: Iterable[AccountObservation],
    required_horizons: Iterable[str] = _HORIZONS,
) -> PoolSnapshot:
    """Validate one ephemeral pool snapshot and derive stable membership identity."""

    pool = _id(pool_id, "pool_id")
    provider_id = _id(provider, "provider")
    product_id = _id(product, "product")
    _time(generated_at, "generated_at")
    required = tuple(sorted({str(item).strip().lower() for item in required_horizons}))
    if not required or any(item not in _HORIZONS for item in required):
        raise AccountPoolError("invalid required_horizons")
    rows = tuple(_observation(item) for item in members)
    if not rows:
        raise AccountPoolError("pool cannot be empty")
    ids = [row.account_id for row in rows]
    if len(ids) != len(set(ids)):
        raise AccountPoolError("duplicate account_id")
    identity = {
        "pool_id": pool,
        "provider": provider_id,
        "product": product_id,
        "required_horizons": required,
        "member_ids": sorted(ids),
    }
    generation = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return PoolSnapshot(pool, provider_id, product_id, generated_at, required, rows, generation)


def observation_from_usage_rows(
    *, account_id: str, state: str, observed_at: str, stale_after: str,
    quota_rows: Iterable[Mapping[str, Any]],
    concurrency_used: int | None = None, concurrency_limit: int | None = None,
) -> AccountObservation:
    """Compose native account-shared usage rows, without making capacity authority.

    Enrollment identity, enablement, health and freshness are supplied by the
    existing owner. This function neither authenticates nor records an account.
    Missing windows remain unknown. Provider exhaustion dominates a display state.
    """
    windows = {name: UsageWindow(None) for name in _HORIZONS}
    seen = set()
    exhausted = False
    observed = _time(observed_at, "observed_at")
    for row in quota_rows:
        if not isinstance(row, Mapping):
            raise AccountPoolError("invalid quota row")
        horizon = row.get("horizon")
        if horizon not in _HORIZONS or horizon in seen:
            raise AccountPoolError("duplicate or unsupported quota horizon")
        if row.get("metric") != "provider_allocation" or row.get("scope") != "account_shared":
            raise AccountPoolError("quota row is not account-shared allocation")
        if _time(row.get("observed_at"), "observed_at") != observed:
            raise AccountPoolError("mixed-time quota observation")
        seen.add(horizon)
        status = row.get("status")
        if status not in {"limited", "exhausted"}:
            continue
        windows[horizon] = _window(UsageWindow(row.get("used_percent"), row.get("reset_at")))
        exhausted = exhausted or status == "exhausted"
    if exhausted and str(state).strip().lower() == "available":
        state = "cooling"
    return _observation(AccountObservation(
        account_id, state, observed_at, stale_after,
        windows["five_hour"], windows["weekly"], windows["monthly"],
        concurrency_used, concurrency_limit,
    ))


def _window_by_name(row: AccountObservation, horizon: str) -> UsageWindow:
    if horizon == "five_hour":
        return row.five_hour
    if horizon == "weekly":
        return row.weekly
    if horizon == "monthly":
        return row.monthly
    raise AccountPoolError("unsupported horizon")


def member_eligible(
    snapshot: PoolSnapshot, row: AccountObservation, *, now: str | None = None
) -> bool:
    """Check capacity at the request clock; never infer reset or freshness."""

    if row.state != "available":
        return False
    generated = _time(snapshot.generated_at, "generated_at")
    at = _time(now, "now") if now is not None else generated
    if generated > at or _time(row.observed_at, "observed_at") > generated:
        return False
    if at >= _time(row.stale_after, "stale_after"):
        return False
    windows = tuple(_window_by_name(row, horizon) for horizon in _HORIZONS)
    if any(window.used_percent is not None and window.used_percent >= 100 for window in windows):
        return False
    for horizon in snapshot.required_horizons:
        window = _window_by_name(row, horizon)
        if window.used_percent is None or window.reset_at is None:
            return False
        if _time(window.reset_at, "reset_at") <= at:
            return False
    if row.concurrency_limit is not None and row.concurrency_used is not None:
        if row.concurrency_used >= row.concurrency_limit:
            return False
    return True


def _session(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AccountPoolError("invalid session_id")
    text = value.strip()
    if value != text or not text or len(text) > 512 or any(ord(ch) < 33 or ord(ch) > 126 for ch in text):
        raise AccountPoolError("invalid session_id")
    return text


def _affinity(session_id: str, account_id: str) -> int:
    payload = f"{session_id}\n{account_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _rank(snapshot: PoolSnapshot, row: AccountObservation, session_id: str | None) -> tuple[object, ...]:
    required = [_window_by_name(row, horizon).used_percent for horizon in snapshot.required_horizons]
    if any(value is None for value in required):
        raise AccountPoolError("required horizon unexpectedly unknown")
    pressure = [value for value in required if value is not None]
    concurrency = 0
    if row.concurrency_used is not None and row.concurrency_limit is not None:
        concurrency = (100 * row.concurrency_used) // row.concurrency_limit
    base: tuple[object, ...] = (max(pressure), sum(pressure), concurrency)
    if session_id is None:
        return base + (row.account_id,)
    return base + (-_affinity(session_id, row.account_id), row.account_id)


def select_account(
    snapshot: PoolSnapshot,
    *,
    sticky_account_id: str | None = None,
    session_id: str | None = None,
    excluded_account_ids: Iterable[str] = (),
    now: str | None = None,
) -> AccountSelection:
    """Select one member while preserving healthy session stickiness."""

    if not isinstance(snapshot, PoolSnapshot):
        raise AccountPoolError("invalid pool snapshot")
    checked = build_snapshot(
        pool_id=snapshot.pool_id, provider=snapshot.provider, product=snapshot.product,
        generated_at=snapshot.generated_at, members=snapshot.members,
        required_horizons=snapshot.required_horizons,
    )
    if checked.generation != snapshot.generation:
        raise AccountPoolError("pool generation disagrees with membership")
    snapshot = checked
    if isinstance(excluded_account_ids, (str, bytes)):
        raise AccountPoolError("excluded accounts must be an iterable of ids")
    excluded = {_id(item, "excluded_account_id") for item in excluded_account_ids}
    if not excluded.issubset({row.account_id for row in snapshot.members}):
        raise AccountPoolError("excluded account is not a pool member")
    sticky = _id(sticky_account_id, "sticky_account_id") if sticky_account_id else None
    session = _session(session_id)
    eligible = [row for row in snapshot.members
                if row.account_id not in excluded and member_eligible(snapshot, row, now=now)]
    if sticky is not None:
        for row in eligible:
            if row.account_id == sticky:
                return AccountSelection(
                    snapshot.pool_id, snapshot.generation, sticky, "sticky_account_healthy", True
                )
    if not eligible:
        return AccountSelection(
            snapshot.pool_id, snapshot.generation, None, "no_eligible_account", False
        )
    chosen = min(eligible, key=lambda row: _rank(snapshot, row, session))
    reason = "best_headroom_session_affinity" if session else "best_headroom"
    return AccountSelection(snapshot.pool_id, snapshot.generation, chosen.account_id, reason, False)


def rollover_decision(effect_state: str, error_class: str | None) -> RolloverDecision:
    """Permit in-pool replay only after a provably pre-effect refusal."""

    effect = str(effect_state or "").strip().lower()
    if effect not in _EFFECT_STATES:
        raise AccountPoolError("invalid effect_state")
    error = str(error_class or "").strip().lower() or None
    if effect != "proven_no_effect":
        return RolloverDecision(False, "effect_not_proven_absent")
    if error not in _SAFE_REFUSALS:
        return RolloverDecision(False, "refusal_not_safe_for_replay")
    return RolloverDecision(True, f"pre_effect_{error}_refusal")


__all__ = [
    "AccountObservation",
    "AccountPoolError",
    "AccountSelection",
    "PoolSnapshot",
    "RolloverDecision",
    "UsageWindow",
    "build_snapshot",
    "member_eligible",
    "observation_from_usage_rows",
    "rollover_decision",
    "select_account",
]
