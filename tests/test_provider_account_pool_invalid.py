import pytest
from engine.provider_account_pool import AccountObservation, AccountPoolError
from engine.provider_account_pool_select import select


def test_invalid_percent_refuses():
    with pytest.raises(AccountPoolError):
        select("go", [AccountObservation("a", "available", 101, 0, 0)])
