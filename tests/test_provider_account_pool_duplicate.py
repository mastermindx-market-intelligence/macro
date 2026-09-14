import pytest
from engine.provider_account_pool import AccountObservation, AccountPoolError
from engine.provider_account_pool_select import select


def test_duplicate_member_refuses():
    rows = [AccountObservation("a", "available"), AccountObservation("A", "available")]
    with pytest.raises(AccountPoolError):
        select("go", rows)
