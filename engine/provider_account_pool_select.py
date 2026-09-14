from __future__ import annotations

from hashlib import sha256

from engine.provider_account_pool import AccountObservation, AccountSelection, AccountPoolError
from engine.provider_account_pool_checks import normalize_id, valid_percent


def _affinity(session_id: str, account_id: str) -> int:
    payload = f"{session_id}\n{account_id}".encode("utf-8")
    return int.from_bytes(sha256(payload).digest()[:8], "big")


def select(
    pool_id: str,
    rows: list[AccountObservation],
    sticky: str | None = None,
    session_id: str | None = None,
) -> AccountSelection:
    pool = normalize_id(pool_id, "pool_id")
    if not rows:
        raise AccountPoolError("pool cannot be empty")
    normalized = []
    for row in rows:
        values = (row.rolling_used_percent, row.weekly_used_percent, row.monthly_used_percent)
        if row.state not in {"available", "cooling", "unavailable", "unknown"} or not all(valid_percent(v) for v in values):
            raise AccountPoolError("invalid account observation")
        normalized.append(AccountObservation(normalize_id(row.account_id, "account_id"), row.state, *values))
    if len({row.account_id for row in normalized}) != len(normalized):
        raise AccountPoolError("duplicate account")
    eligible = [row for row in normalized if row.state == "available" and all(v is None or v < 100 for v in (row.rolling_used_percent, row.weekly_used_percent, row.monthly_used_percent))]
    sticky_id = normalize_id(sticky, "sticky") if sticky else None
    if sticky_id and any(row.account_id == sticky_id for row in eligible):
        return AccountSelection(pool, sticky_id, "sticky_account_healthy", True)
    if not eligible:
        return AccountSelection(pool, None, "no_eligible_account", False)
    session = normalize_id(session_id, "session_id") if session_id else None
    def key(row: AccountObservation) -> tuple[object, ...]:
        usage = tuple(101 if value is None else value for value in (row.rolling_used_percent, row.weekly_used_percent, row.monthly_used_percent))
        if session is None:
            return usage + (row.account_id,)
        return usage + (-_affinity(session, row.account_id), row.account_id)
    chosen = min(eligible, key=key)
    reason = "best_observed_headroom_session_affinity" if session else "best_observed_headroom"
    return AccountSelection(pool, chosen.account_id, reason, False)
