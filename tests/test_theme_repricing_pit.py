"""PIT membership + exact-session price replay for theme repricing context."""
from datetime import date, timedelta

import pandas as pd
import pytest

from engine import theme_repricing_pit as pit
from engine.theme_graph import local_sources
from lib import nyse_calendar


def _tree(members):
    return ({
        "theme": "Semiconductors",
        "key": "Semiconductors",
        "subsectors": [{
            "key": "semiscompute",
            "name": "Compute",
            "description": "Compute",
            "members": list(members),
        }],
    },)


def _ladder():
    return local_sources.Ladder(vintages=[
        local_sources.Vintage(
            asof="2026-01-02",
            source_ref="seed@2026-01-02",
            themes=_tree(["A", "B", "C", "D"]),
        ),
        local_sources.Vintage(
            asof="2026-01-15",
            source_ref="tree_history@2026-01-15",
            themes=_tree(["B", "C", "D", "E"]),
        ),
    ])


def _sessions(end: date, n=110):
    start = end - timedelta(days=180)
    rows = nyse_calendar.sessions_between(start, end)
    return rows[-n:]


def _price_series(end: date, daily: float):
    sessions = _sessions(end)
    vals = [100.0 * ((1.0 + daily) ** i) for i in range(len(sessions))]
    return pd.Series(vals, index=pd.DatetimeIndex(sessions), dtype=float)


def _prices(end=date(2026, 1, 16)):
    return {
        "A": _price_series(end, 0.012),
        "B": _price_series(end, 0.008),
        "C": _price_series(end, 0.006),
        "D": _price_series(end, 0.004),
        "E": _price_series(end, 0.003),
    }


def test_vintage_at_never_reads_a_future_membership():
    ladder = _ladder()
    early = pit.membership_at(ladder, "2026-01-14")
    late = pit.membership_at(ladder, "2026-01-16")

    assert early.vintage_asof == "2026-01-02"
    assert early.members_by_subtheme["semiscompute"] == ("A", "B", "C", "D")
    assert "E" not in early.members_by_subtheme["semiscompute"]

    assert late.vintage_asof == "2026-01-15"
    assert late.members_by_subtheme["semiscompute"] == ("B", "C", "D", "E")
    assert "A" not in late.members_by_subtheme["semiscompute"]


def test_replay_before_first_vintage_refuses_instead_of_backdating():
    with pytest.raises(pit.ReplayRefusal, match="no Finviz structure vintage"):
        pit.membership_at(_ladder(), "2025-12-31")


def test_non_session_replay_refuses():
    with pytest.raises(pit.ReplayRefusal, match="requires an NYSE session date"):
        pit.membership_at(_ladder(), "2026-01-17")  # Saturday


def test_exact_horizon_return_requires_both_exchange_session_endpoints():
    close = _price_series(date(2026, 1, 16), 0.01)
    value = pit.exact_horizon_return(close, "2026-01-16", 5)
    assert value is not None and value > 0

    missing_tip = close.drop(pd.Timestamp("2026-01-16"))
    assert pit.exact_horizon_return(missing_tip, "2026-01-16", 5) is None

    start = pit.prior_session("2026-01-16", 5)
    missing_start = close.drop(pd.Timestamp(start))
    assert pit.exact_horizon_return(missing_start, "2026-01-16", 5) is None


def test_member_perf_uses_frozen_vintage_and_reports_coverage():
    prices = _prices()
    membership = pit.membership_at(_ladder(), "2026-01-16")
    perf, coverage = pit.member_perf_at(membership, prices.get)

    assert set(perf) == {"B", "C", "D", "E"}
    assert "A" not in perf
    assert coverage["expected_unique_members"] == 4
    assert coverage["readable_price_series"] == 4
    assert coverage["horizons"]["1W"]["coverage"] == 1.0
    assert all(set(row) == {"1W", "1M", "3M"} for row in perf.values())


def test_missing_tip_is_coverage_loss_not_stale_fill():
    prices = _prices()
    prices["C"] = prices["C"].drop(pd.Timestamp("2026-01-16"))
    membership = pit.membership_at(_ladder(), "2026-01-16")
    perf, coverage = pit.member_perf_at(membership, prices.get)

    assert "C" not in perf
    assert coverage["horizons"]["1W"]["observed"] == 3
    assert coverage["horizons"]["1W"]["coverage"] == 0.75


def test_build_pit_context_reuses_current_repricing_contract_without_authority():
    prices = _prices()
    out = pit.build_pit_context(
        ladder=_ladder(),
        asof="2026-01-16",
        subsector_perf={
            "semiscompute": {"1W": 4.0, "1M": 8.0, "3M": 12.0},
        },
        close_loader=prices.get,
        price_source="fixture:split-adjusted",
        price_basis="split_adjusted_price_return",
    )

    assert out["schema"] == pit.SCHEMA
    assert out["membership"]["vintage_asof"] == "2026-01-15"
    assert out["membership"]["source_ref"] == "tree_history@2026-01-15"
    assert out["prices"]["endpoint_policy"] == "exact_session_only_no_ffill"
    assert out["coverage"]["horizons"]["1M"]["coverage"] == 1.0

    row = out["repricing"]["subthemes"][0]
    assert row["shape"] == "broad_price_repricing"
    assert row["price_leader"]["ticker"] == "B"
    assert out["authority"]["may_rank"] is False
    assert out["authority"]["may_escalate"] is False
    assert out["authority"]["may_trade"] is False
