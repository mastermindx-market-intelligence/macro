from engine.provider_account_pool import AccountObservation
from engine.provider_account_pool_select import select


def test_known_headroom_beats_unknown():
    rows = [AccountObservation("a", "available"), AccountObservation("b", "available", 99, 99, 99)]
    assert select("go", rows).account_id == "b"
