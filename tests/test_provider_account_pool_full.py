from engine.provider_account_pool import AccountObservation
from engine.provider_account_pool_select import select


def test_exhausted_member_is_skipped():
    rows = [AccountObservation("a", "available", 100, 5, 5), AccountObservation("b", "available", 40, 20, 10)]
    assert select("go", rows, "a").account_id == "b"
