"""Pure account-pool selection for Provider Control."""
from __future__ import annotations

from dataclasses import dataclass


class AccountPoolError(ValueError):
    pass


@dataclass(frozen=True)
class AccountObservation:
    account_id: str
    state: str
    rolling_used_percent: int | None = None
    weekly_used_percent: int | None = None
    monthly_used_percent: int | None = None


@dataclass(frozen=True)
class AccountSelection:
    pool_id: str
    account_id: str | None
    reason: str
    sticky_retained: bool
