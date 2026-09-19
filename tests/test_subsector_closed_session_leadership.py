"""Lane C: closed-session parent/subtheme leadership observations."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import subsector_rotation as sr


def _bars(returns: list[float], *, start: str = "2026-01-02", volume: float = 100.0) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(returns) + 1)
    close = 100.0 * np.cumprod(np.array([1.0, *[1.0 + r for r in returns]], dtype=float))
    return pd.DataFrame({"close": close, "volume": volume}, index=idx)


def _child(theme: dict, key: str) -> dict:
    return next(row for row in theme["subthemes"] if row["key"] == key)


def test_strong_subtheme_is_visible_inside_flat_parent_and_negative_long_window():
    # Last 60 sessions: Fast loses 1% for 55 sessions, then gains 3% for five.
    # Offset does the inverse. The unique-member parent is flat every day, while
    # Fast is improving over five sessions but remains negative over sixty.
    fast = [0.0] * 10 + [-0.01] * 55 + [0.03] * 5
    offset = [0.0] * 10 + [0.01] * 55 + [-0.03] * 5
    market = _bars([0.0] * 70)
    bars = {t: _bars(fast) for t in ("A", "B", "C")}
    bars.update({t: _bars(offset) for t in ("D", "E", "F")})
    tree = [{"theme": "Semiconductors", "subsectors": [
        {"key": "fast", "name": "Fast", "members": ["A", "B", "C"]},
        {"key": "offset", "name": "Offset", "members": ["D", "E", "F"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, bars, market, asof=str(market.index[-1].date()),
        parent_keys={"Semiconductors"},
    )
    theme = out["themes"]["Semiconductors"]
    row = _child(theme, "fast")

    assert theme["parent"]["windows"]["5"]["return_pct"] == pytest.approx(0.0, abs=1e-9)
    assert row["windows"]["5"]["return_pct"] > 15.0
    assert row["windows"]["5"]["relative_strength"]["change_vs_market_pct"] > 15.0
    assert row["windows"]["5"]["relative_strength"]["slope_vs_market_pct_per_session"] > 0.0
    assert row["windows"]["60"]["return_pct"] < 0.0
    assert row["acceleration"]["state"] == "IMPROVING"
    assert "SHORT_WINDOW_POSITIVE_LONG_WINDOW_NEGATIVE" in row["reason_codes"]
    assert row["strength_level"]["window_sessions"] == 20
    assert out["basis"]["membership_is_point_in_time"] is False
    assert out["permissions"] == {
        "may_rank": False, "may_gate": False, "may_size": False,
        "may_escalate": False, "may_trade": False,
    }
    assert out["is_context_only"] is True
    assert out["is_forecast"] is False
    assert out["bar_status"] == "CLOSED"


def test_parent_dedupes_members_and_one_name_move_is_not_broad_participation():
    flat = [0.0] * 65
    mover = [0.0] * 60 + [0.10] * 5
    market = _bars(flat)
    bars = {"X": _bars(mover)}
    bars.update({t: _bars(flat) for t in ("Y", "Z", "Q", "R")})
    tree = [{"theme": "Hardware", "subsectors": [
        {"key": "servers", "name": "Servers", "members": ["X", "Y", "Z"]},
        {"key": "storage", "name": "Storage", "members": ["X", "Q", "R"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, bars, market, asof=str(market.index[-1].date()), parent_keys={"Hardware"}
    )
    theme = out["themes"]["Hardware"]
    parent = theme["parent"]
    servers = _child(theme, "servers")

    assert parent["coverage"]["declared_member_assignments"] == 6
    assert parent["coverage"]["unique_members"] == 5
    assert parent["coverage"]["duplicate_members_removed"] == 1
    assert "DUPLICATE_MEMBERS_DEDUPED" in parent["reason_codes"]
    p5 = servers["windows"]["5"]["participation"]
    assert p5["priced_members"] == 3
    assert p5["positive_share"] == pytest.approx(0.3333)
    assert p5["top_abs_move_share"] == pytest.approx(1.0)
    assert "ONE_NAME_CONCENTRATION" in servers["windows"]["5"]["reason_codes"]


def test_sparse_new_listing_keeps_unsupported_windows_null_with_reasons():
    market = _bars([0.0] * 70)
    idx = market.index[-11:]
    newcomer = pd.DataFrame({"close": np.linspace(10.0, 12.0, len(idx)), "volume": 100.0}, index=idx)
    tree = [{"theme": "Semiconductors", "subsectors": [
        {"key": "new", "name": "New", "members": ["NEW"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"NEW": newcomer}, market, asof=str(market.index[-1].date()),
        parent_keys={"Semiconductors"},
    )
    row = _child(out["themes"]["Semiconductors"], "new")

    assert row["status"] == "PARTIAL"
    assert row["windows"]["5"]["return_pct"] is not None
    assert row["windows"]["20"]["return_pct"] is None
    assert row["windows"]["60"]["return_pct"] is None
    assert "INSUFFICIENT_HISTORY" in row["windows"]["60"]["reason_codes"]
    assert "SPARSE_GROUP" in row["reason_codes"]
    assert "SHORT_MEMBER_HISTORY" in row["reason_codes"]


def test_explicit_completed_asof_excludes_a_later_partial_bar():
    market = _bars([0.0] * 10)
    member = _bars([0.0] * 9 + [1.0])
    completed_asof = str(market.index[-2].date())
    tree = [{"theme": "Artificial Intelligence", "subsectors": [
        {"key": "compute", "name": "Compute", "members": ["A", "B", "C"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"A": member, "B": member, "C": member}, market,
        asof=completed_asof, parent_keys={"Artificial Intelligence"},
    )
    row = _child(out["themes"]["Artificial Intelligence"], "compute")

    assert out["asof"] == completed_asof
    assert row["windows"]["1"]["return_pct"] == pytest.approx(0.0)


def test_missing_sessions_and_extreme_price_jump_are_disclosed_not_repaired():
    market = _bars([0.0] * 70)
    normal = _bars([0.0] * 70)
    jump = _bars([0.0] * 64 + [1.0] + [0.0] * 5)
    missing = normal.drop(index=normal.index[-8])
    tree = [{"theme": "Semiconductors", "subsectors": [
        {"key": "memory", "name": "Memory", "members": ["A", "B", "C"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"A": jump, "B": missing, "C": normal}, market,
        asof=str(market.index[-1].date()), parent_keys={"Semiconductors"},
    )
    row = _child(out["themes"]["Semiconductors"], "memory")

    assert row["coverage"]["missing_member_sessions"] >= 1
    assert row["status"] == "PARTIAL"
    assert "MISSING_MEMBER_SESSIONS" in row["reason_codes"]
    assert "EXTREME_SINGLE_SESSION_MOVE" in row["reason_codes"]
    assert out["basis"]["corporate_action_basis"] == "OWNER_CLOSE_SERIES_UNVERIFIED"


def test_failed_breakout_turns_deteriorating_without_sticky_heating_state():
    # Prior five sessions beat market; current five give the advantage back.
    returns = [0.0] * 55 + [0.02] * 5 + [-0.02] * 5
    market = _bars([0.0] * 65)
    bars = {t: _bars(returns) for t in ("A", "B", "C")}
    tree = [{"theme": "Hardware", "subsectors": [
        {"key": "servers", "name": "Servers", "members": ["A", "B", "C"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, bars, market, asof=str(market.index[-1].date()), parent_keys={"Hardware"}
    )
    row = _child(out["themes"]["Hardware"], "servers")

    assert row["acceleration"]["state"] == "DETERIORATING"
    assert "heating" not in row
    assert "campaign" not in row


def test_missing_declared_member_downgrades_measured_windows_to_partial():
    market = _bars([0.0] * 70)
    member = _bars([0.001] * 70)
    tree = [{"theme": "Hardware", "subsectors": [
        {"key": "servers", "name": "Servers", "members": ["A", "B", "MISSING"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"A": member, "B": member}, market,
        asof=str(market.index[-1].date()), parent_keys={"Hardware"},
    )
    row = _child(out["themes"]["Hardware"], "servers")

    assert row["windows"]["60"]["return_pct"] is not None
    assert row["status"] == "PARTIAL"
    assert row["coverage"]["unpriced_members"] == ["MISSING"]
    assert "PARTIAL_MEMBER_COVERAGE" in row["reason_codes"]


def test_trailing_stale_tape_is_not_forward_filled_as_zero_return():
    market = _bars([0.0] * 70)
    live = _bars([0.001] * 70)
    stale = live.iloc[:-5].copy()
    tree = [{"theme": "Hardware", "subsectors": [
        {"key": "servers", "name": "Servers", "members": ["STALE", "B", "C"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"STALE": stale, "B": live, "C": live}, market,
        asof=str(market.index[-1].date()), parent_keys={"Hardware"},
    )
    row = _child(out["themes"]["Hardware"], "servers")

    assert row["status"] == "PARTIAL"
    assert row["windows"]["5"]["participation"]["priced_members"] == 2
    assert row["coverage"]["current_session_members"] == 2
    assert row["coverage"]["stale_members"] == [{
        "ticker": "STALE",
        "last_observed_session": str(stale.index[-1].date()),
        "lag_sessions": 5,
    }]
    assert "STALE_MEMBER_TAPE" in row["reason_codes"]


def test_gap_older_than_longest_window_does_not_poison_current_coverage():
    market = _bars([0.0] * 140)
    complete = _bars([0.001] * 140)
    old_gap = complete.drop(index=complete.index[10])
    tree = [{"theme": "Hardware", "subsectors": [
        {"key": "servers", "name": "Servers", "members": ["A", "B", "C"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"A": old_gap, "B": complete, "C": complete}, market,
        asof=str(market.index[-1].date()), parent_keys={"Hardware"},
    )
    row = _child(out["themes"]["Hardware"], "servers")

    assert row["status"] == "MEASURED"
    assert row["coverage"]["internal_missing_member_sessions"] == 0
    assert "MISSING_MEMBER_SESSIONS" not in row["reason_codes"]


def test_mixed_cohort_with_new_member_is_partial_even_when_group_window_exists():
    market = _bars([0.0] * 70)
    complete = _bars([0.001] * 70)
    idx = market.index[-11:]
    newcomer = pd.DataFrame(
        {"close": np.linspace(10.0, 11.0, len(idx)), "volume": 100.0},
        index=idx,
    )
    tree = [{"theme": "Hardware", "subsectors": [
        {"key": "servers", "name": "Servers", "members": ["A", "B", "NEW"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"A": complete, "B": complete, "NEW": newcomer}, market,
        asof=str(market.index[-1].date()), parent_keys={"Hardware"},
    )
    row = _child(out["themes"]["Hardware"], "servers")

    assert row["windows"]["60"]["return_pct"] is not None
    assert row["status"] == "PARTIAL"
    assert row["coverage"]["members_with_complete_window_history"] == 2
    assert row["coverage"]["pre_listing_member_sessions"] > 0
    assert "SHORT_MEMBER_HISTORY" in row["reason_codes"]



def test_first_close_on_window_boundary_is_short_history():
    market = _bars([0.0] * 70)
    complete = _bars([0.001] * 70)
    # The first close exists on the first 60-session return date, but no prior
    # close exists to compute that first return. Coverage must remain partial.
    idx = market.index[-60:]
    boundary = pd.DataFrame(
        {"close": np.linspace(10.0, 12.0, len(idx)), "volume": 100.0},
        index=idx,
    )
    tree = [{"theme": "Hardware", "subsectors": [
        {"key": "servers", "name": "Servers", "members": ["A", "B", "BOUNDARY"]},
    ]}]

    out = sr.compute_closed_session_leadership(
        tree, {"A": complete, "B": complete, "BOUNDARY": boundary}, market,
        asof=str(market.index[-1].date()), parent_keys={"Hardware"},
    )
    row = _child(out["themes"]["Hardware"], "servers")

    assert row["status"] == "PARTIAL"
    assert row["coverage"]["pre_listing_member_sessions"] == 0
    assert row["coverage"]["short_history_members"] == [{
        "ticker": "BOUNDARY",
        "first_observed_session": str(idx[0].date()),
        "leading_unavailable_sessions": 1,
    }]
    assert "SHORT_MEMBER_HISTORY" in row["reason_codes"]
