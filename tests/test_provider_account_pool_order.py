from engine.provider_account_pool import AccountObservation
from engine.provider_account_pool_select import select


def test_equal_headroom_uses_stable_member_order():
    rows = [AccountObservation("b", "available", 10, 10, 10), AccountObservation("a", "available", 10, 10, 10)]
    assert select("go", rows).account_id == "a"
