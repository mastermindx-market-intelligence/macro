from engine.provider_account_pool import AccountObservation
from engine.provider_account_pool_select import select


def test_member_identity_normalizes_lowercase():
    result = select("go", [AccountObservation("A", "available", 1, 1, 1)])
    assert result.account_id == "a"
