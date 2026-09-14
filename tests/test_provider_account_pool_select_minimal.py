from engine.provider_account_pool import AccountObservation
from engine.provider_account_pool_select import select


def test_selects_lower_usage_member():
    rows = [AccountObservation("a", "available", 90, 90, 90), AccountObservation("b", "available", 10, 10, 10)]
    assert select("go", rows).account_id == "b"
