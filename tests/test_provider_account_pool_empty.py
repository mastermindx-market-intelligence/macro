import pytest
from engine.provider_account_pool import AccountPoolError
from engine.provider_account_pool_select import select


def test_empty_pool_refuses():
    with pytest.raises(AccountPoolError):
        select("go", [])
