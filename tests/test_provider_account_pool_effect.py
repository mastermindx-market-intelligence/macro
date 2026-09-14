from engine.provider_account_pool_effect import rollover_allowed


def test_usage_limit_with_no_effect_can_roll():
    assert rollover_allowed("usage_limit", "no_effect")


def test_account_rejection_with_no_effect_can_roll():
    assert rollover_allowed("account_rejected", "no_effect")


def test_timeout_or_unknown_effect_cannot_roll():
    assert not rollover_allowed("timeout", "no_effect")
    assert not rollover_allowed("usage_limit", "effect_unknown")
    assert not rollover_allowed("server_error", "effect_unknown")
