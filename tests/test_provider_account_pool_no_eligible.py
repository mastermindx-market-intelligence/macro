from engine.provider_account_pool import AccountObservation
from engine.provider_account_pool_select import select


def test_no_eligible_member_returns_none():
    result = select("go", [AccountObservation("a", "cooling")])
    assert result.account_id is None
    assert result.reason == "no_eligible_account"
