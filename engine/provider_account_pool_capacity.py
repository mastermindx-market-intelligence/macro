from __future__ import annotations

from engine.provider_account_pool import AccountPoolError
from engine.provider_account_pool_checks import normalize_id, valid_percent
from engine.provider_account_pool_types import CapacityEvidence


def eligible(value: CapacityEvidence) -> bool:
    windows = (value.rolling, value.weekly, value.monthly)
    if not all(valid_percent(item.used_percent) for item in windows):
        raise AccountPoolError("invalid capacity evidence")
    if any(item.used_percent is not None and item.used_percent >= 100 for item in windows):
        return False
    if value.concurrency_used is not None and value.concurrency_limit is not None:
        return value.concurrency_used < value.concurrency_limit
    return True


def rank_key(value: CapacityEvidence) -> tuple[int, int, int, int, str]:
    def used(item: int | None) -> int:
        return 101 if item is None else item
    concurrency = 0
    if value.concurrency_used is not None and value.concurrency_limit is not None:
        concurrency = int(100 * value.concurrency_used / value.concurrency_limit)
    return (used(value.rolling.used_percent), used(value.weekly.used_percent), used(value.monthly.used_percent), concurrency, normalize_id(value.account_id, "account_id"))
