from engine.provider_account_pool import AccountObservation
from engine.provider_account_pool_select import select


def _rows():
    return [
        AccountObservation("a", "available", 0, 0, 0),
        AccountObservation("b", "available", 0, 0, 0),
        AccountObservation("c", "available", 0, 0, 0),
    ]


def test_same_session_is_stable():
    first = select("go", _rows(), session_id="session-1")
    second = select("go", list(reversed(_rows())), session_id="session-1")
    assert first.account_id == second.account_id
    assert first.reason == "best_observed_headroom_session_affinity"


def test_sessions_spread_across_equal_members():
    selected = {select("go", _rows(), session_id=f"session-{index}").account_id for index in range(20)}
    assert len(selected) >= 2


def test_sticky_member_overrides_new_session_affinity():
    result = select("go", _rows(), sticky="b", session_id="session-1")
    assert result.account_id == "b"
    assert result.sticky_retained is True
