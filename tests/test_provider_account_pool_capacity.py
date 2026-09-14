from engine.provider_account_pool_capacity import eligible, rank_key
from engine.provider_account_pool_types import CapacityEvidence, CapacityWindow


def row(account: str, rolling: int | None, weekly: int | None, monthly: int | None, used: int = 0, limit: int = 2):
    return CapacityEvidence(account, "2026-09-14T00:00:00Z", CapacityWindow(rolling), CapacityWindow(weekly), CapacityWindow(monthly), used, limit)


def test_exhausted_window_is_ineligible():
    assert not eligible(row("a", 100, 10, 10))


def test_full_concurrency_is_ineligible():
    assert not eligible(row("a", 10, 10, 10, 2, 2))


def test_rank_prefers_headroom_then_concurrency():
    assert rank_key(row("a", 10, 10, 10, 1, 2)) < rank_key(row("b", 50, 10, 10, 0, 2))
