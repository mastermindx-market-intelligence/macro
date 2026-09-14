from __future__ import annotations

from engine.provider_account_pool import AccountObservation, AccountSelection, AccountPoolError


def select(pool_id: str, rows: list[AccountObservation], sticky: str | None = None) -> AccountSelection:
    if not rows:
        raise AccountPoolError("pool cannot be empty")
    normalized = [AccountObservation(r.account_id.strip().lower(), r.state, r.rolling_used_percent, r.weekly_used_percent, r.monthly_used_percent) for r in rows]
    if len({r.account_id for r in normalized}) != len(normalized):
        raise AccountPoolError("duplicate account")
    eligible = [r for r in normalized if r.state == "available" and all(v is None or v < 100 for v in (r.rolling_used_percent, r.weekly_used_percent, r.monthly_used_percent))]
    if sticky and any(r.account_id == sticky for r in eligible):
        return AccountSelection(pool_id, sticky, "sticky_account_healthy", True)
    if not eligible:
        return AccountSelection(pool_id, None, "no_eligible_account", False)
    chosen = min(eligible, key=lambda r: tuple(101 if v is None else v for v in (r.rolling_used_percent, r.weekly_used_percent, r.monthly_used_percent)) + (r.account_id,))
    return AccountSelection(pool_id, chosen.account_id, "best_observed_headroom", False)
