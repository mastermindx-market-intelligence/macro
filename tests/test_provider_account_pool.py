from engine.provider_account_pool import AccountObservation, AccountSelection


def test_types_construct():
    row = AccountObservation("a", "available", 0, 0, 0)
    decision = AccountSelection("pool", "a", "sticky_account_healthy", True)
    assert row.account_id == "a"
    assert decision.account_id == "a"
