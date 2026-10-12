"""Cap, breadth, issuance and subscription stay separate claims.

Fixtures only. A price move is capitalization. A supply move is issuance.
ETF creations are the subscription tape. Weekend silence, a late daily print
and a measured zero are different observation states.
"""
from __future__ import annotations

import pandas as pd

from engine.crypto_market_state import (
    build_market_state,
    class_regimes,
    total_market_cap_history,
)

_INFLOW_CLAIMS = (
    "inflow",
    "outflow",
    "Capital is",
    "wider participation",
    "participation narrowing",
    "follow flows",
    "money flow",
    "Advancing, led by Bitcoin",
    "Range-bound, waiting for participation",
    "流入",
    "流出",
    "资金",
    "参与度",
    "广度",
)


def _read(frames: dict):
    def reader(group: str, name: str):
        return frames.get((group, name))

    return reader


def _hero(state: dict) -> str:
    return "\n".join(state[key] for key in ("stance", "summary", "stance_zh", "summary_zh"))


def _assert_no_inflow_claim(state: dict) -> None:
    text = _hero(state)
    for phrase in _INFLOW_CLAIMS:
        assert phrase not in text, phrase


def _window(level: float, end: float, n: int = 80, periods: int = 31) -> list[float]:
    head = [level] * (n - periods)
    ramp = [level + (end - level) * i / (periods - 1) for i in range(periods)]
    return head + ramp


def test_price_only_cap_rise_is_not_an_inflow() -> None:
    """Price up, supply flat, dominance down, ETF prints are zero. Not an inflow."""
    dates = pd.bdate_range("2025-11-03", periods=80)
    price = _window(100_000.0, 115_000.0)
    supply = [19_500_000.0] * len(dates)
    mcap = [px * units for px, units in zip(price, supply)]
    dominance = _window(60.0, 50.0)
    frames = {
        ("coinmetrics", "mcap_usd"): pd.DataFrame({"mcap_usd": mcap}, index=dates),
        ("bgeo", "btc_dominance"): pd.DataFrame({"btc_dominance": dominance}, index=dates),
        ("coinbase", "btc_daily"): pd.DataFrame({"close": price, "volume": [1e9] * len(dates)}, index=dates),
        ("farside", "etf_flows"): pd.DataFrame({"total": [0.0] * len(dates)}, index=dates),
        ("defillama", "stablecoins"): pd.DataFrame(
            {"stablecoin_mcap_usd": [200e9] * len(dates)}, index=dates
        ),
    }
    state = build_market_state(_read(frames), today=dates[-1])
    assert state["total_30d_pct"] is not None and state["total_30d_pct"] > 3
    assert state["cap_attribution"]["kind"] == "valuation"
    assert abs(state["cap_attribution"]["supply_30d_pct"]) < 0.5
    assert state["cap_attribution"]["price_30d_pct"] > 10
    assert state["flows"]["etf"]["value"] == 0.0
    assert state["flows"]["etf"]["latest"] == 0.0
    assert state["flows"]["etf"]["observation"] == "zero"
    assert state["flows"]["etf"]["kind"] == "subscription"
    _assert_no_inflow_claim(state)
    assert "subscription" in state["summary"] or "申购" in state["summary_zh"]


def test_supply_change_is_issuance_not_flow() -> None:
    """Flat price, higher token supply, flat share. Cap rises as issuance."""
    dates = pd.bdate_range("2025-11-03", periods=80)
    price = [100_000.0] * len(dates)
    supply = _window(19_500_000.0, 19_500_000.0 * 1.05)
    mcap = [px * units for px, units in zip(price, supply)]
    frames = {
        ("coinmetrics", "mcap_usd"): pd.DataFrame({"mcap_usd": mcap}, index=dates),
        ("bgeo", "btc_dominance"): pd.DataFrame({"btc_dominance": [55.0] * len(dates)}, index=dates),
        ("coinbase", "btc_daily"): pd.DataFrame({"close": price}, index=dates),
        ("farside", "etf_flows"): pd.DataFrame({"total": [0.0] * len(dates)}, index=dates),
    }
    state = build_market_state(_read(frames), today=dates[-1])
    assert state["total_30d_pct"] is not None and state["total_30d_pct"] > 3
    assert state["cap_attribution"]["kind"] == "issuance"
    assert abs(state["cap_attribution"]["price_30d_pct"]) < 0.5
    assert state["cap_attribution"]["supply_30d_pct"] > 4
    assert "issuance" in state["stance"].lower()
    assert "发行" in state["stance_zh"] + state["summary_zh"]
    assert state["flows"]["etf"]["kind"] == "subscription"
    assert state["flows"]["etf"]["value"] == 0.0
    _assert_no_inflow_claim(state)


def test_cap_splice_discloses_basis_and_skips_fake_regime() -> None:
    """A level gap between derived and direct caps is a splice, not a new regime."""
    dates = pd.date_range("2025-10-01", periods=160, freq="D")
    derived_level = float(2**20)
    direct_level = float(2**21)
    frames = {
        ("coinmetrics", "mcap_usd"): pd.DataFrame(
            {"mcap_usd": [derived_level / 2] * len(dates)}, index=dates
        ),
        ("bgeo", "btc_dominance"): pd.DataFrame({"btc_dominance": [50.0] * len(dates)}, index=dates),
        ("coingecko", "global_market"): pd.DataFrame(
            {"total_mcap_usd": [direct_level] * 40}, index=dates[120:]
        ),
    }
    state = build_market_state(_read(frames), today=dates[-1])
    splice = state["cap_basis"]["splices"][0]
    assert splice["date"] == str(dates[120].date())
    assert splice["from_basis"] == "derived"
    assert splice["to_basis"] == "direct"
    assert splice["support_before"] == 120
    assert splice["support_after"] == 40
    assert splice["level_ratio"] == 2.0
    assert state["cap_basis"]["segments"][0]["source"].startswith("coinmetrics.mcap_usd")
    assert state["cap_basis"]["segments"][1]["source"].startswith("coingecko.global_market")
    assert {band["tone"] for band in state["regimes"]} == {"neutral"}
    assert splice["date"] not in {band["start"] for band in state["regimes"][1:]}

    carried = total_market_cap_history(_read(frames))
    assert {band["tone"] for band in class_regimes(carried)} == {"neutral"}
    bare = pd.Series(carried.to_numpy(dtype=float), index=carried.index)
    fabricated = class_regimes(bare)
    assert any(band["tone"] == "bull" for band in fabricated)


def test_cadence_separates_pending_stale_and_measured_zero() -> None:
    """Same calendar lag is pending for ETFs and stale for stablecoins.

    A published zero on a day that source owes a print is a third state.
    Missing rows stay unavailable and are not stored as zero.
    """
    published = pd.bdate_range("2026-01-02", "2026-03-13")  # Friday
    assert published[-1].weekday() == 4
    sunday = "2026-03-15"
    frames = {
        ("farside", "etf_flows"): pd.DataFrame({"total": [25.0] * len(published)}, index=published),
        ("defillama", "stablecoins"): pd.DataFrame(
            {"stablecoin_mcap_usd": [180e9] * len(published)}, index=published
        ),
    }
    weekend = build_market_state(_read(frames), today=sunday)
    etf = weekend["flows"]["etf"]
    stables = weekend["flows"]["stablecoins"]
    assert etf["expected_cadence"] == "us_business_day"
    assert stables["expected_cadence"] == "calendar_day"
    assert etf["as_of"] == stables["as_of"] == "2026-03-13"
    assert etf["observation"] == "pending"
    assert etf["value"] == 125.0
    assert etf["latest"] == 25.0
    assert stables["observation"] == "stale"
    assert stables["value"] == 180e9
    assert stables["state"] == "Unavailable"
    assert {etf["observation"], stables["observation"]} == {"pending", "stale"}

    zero_days = pd.bdate_range("2026-01-02", "2026-03-11")  # Wednesday
    assert zero_days[-1].weekday() == 2
    zero_frames = {
        ("farside", "etf_flows"): pd.DataFrame({"total": [0.0] * len(zero_days)}, index=zero_days),
        ("defillama", "stablecoins"): pd.DataFrame(
            {"stablecoin_mcap_usd": [180e9] * len(zero_days)}, index=zero_days
        ),
    }
    measured = build_market_state(_read(zero_frames), today=zero_days[-1])
    assert measured["flows"]["etf"]["observation"] == "zero"
    assert measured["flows"]["etf"]["value"] == 0.0
    assert measured["flows"]["etf"]["latest"] == 0.0
    assert measured["flows"]["stablecoins"]["observation"] == "current"
    assert measured["flows"]["stablecoins"]["value"] == 180e9

    friday_zero = {
        ("farside", "etf_flows"): pd.DataFrame({"total": [0.0] * len(published)}, index=published),
    }
    pending_zero = build_market_state(_read(friday_zero), today=sunday)
    assert pending_zero["flows"]["etf"]["latest"] == 0.0
    assert pending_zero["flows"]["etf"]["observation"] == "pending"

    empty = build_market_state(_read({}), today=sunday)
    assert empty["flows"]["etf"]["observation"] == "unavailable"
    assert empty["flows"]["etf"]["value"] is None
    assert empty["flows"]["stablecoins"]["value"] is None
    assert empty["flows"]["stablecoins"]["observation"] == "unavailable"


def test_missing_family_keeps_other_measurements() -> None:
    """A missing optional family withholds only the claim that needs it."""
    dates = pd.bdate_range("2025-08-01", periods=120)
    snapshot = _window(1.0e12, 1.2e12, n=120)
    price = _window(100_000.0, 110_000.0, n=120)
    eth = _window(2_000.0, 2_400.0, n=120)
    frames = {
        ("coingecko", "global_market"): pd.DataFrame({"total_mcap_usd": snapshot}, index=dates),
        ("coinbase", "btc_daily"): pd.DataFrame(
            {"close": price, "volume": list(range(len(dates)))}, index=dates
        ),
        ("yahoo", "ETH-USD"): pd.DataFrame({"close": eth}, index=dates),
        ("farside", "etf_flows"): pd.DataFrame({"total": [40.0] * len(dates)}, index=dates),
        ("defillama", "stablecoins"): pd.DataFrame(
            {"stablecoin_mcap_usd": _window(200e9, 210e9, n=120)}, index=dates
        ),
        ("sentiment_crypto", "fear_greed"): pd.DataFrame({"fear_greed": [42.0] * len(dates)}, index=dates),
        ("vector", "signals"): pd.DataFrame(
            {"funding_annual_pct": [4.0], "oi_mcap_ratio": [0.02], "oi_mcap_pctile": [45.0],
             "dvol": [48.0], "dvol_pctile": [55.0]},
            index=dates[-1:],
        ),
    }
    state = build_market_state(_read(frames), today=dates[-1])
    assert state["btc_dominance"] is None
    assert state["dominance_state"] == "Unavailable"
    assert state["total_market_cap"] == snapshot[-1]
    assert state["flows"]["etf"]["value"] == 200.0
    assert state["flows"]["etf"]["observation"] == "current"
    assert state["flows"]["stablecoins"]["value"] == 210e9
    assert state["fear_greed"] == 42.0
    assert state["heat"]["funding"]["state"] == "Balanced"
    assert state["heat"]["altseason"]["value"] is None
    assert state["heat"]["altseason"]["state"] == "Unavailable"
    assert state["heat"]["altseason"]["kind"] == "relative_price"
    _assert_no_inflow_claim(state)
    assert "led by Bitcoin" not in state["stance"]

    no_cap = {
        ("farside", "etf_flows"): frames[("farside", "etf_flows")],
        ("defillama", "stablecoins"): frames[("defillama", "stablecoins")],
        ("coinbase", "btc_daily"): frames[("coinbase", "btc_daily")],
    }
    withheld = build_market_state(_read(no_cap), today=dates[-1])
    assert withheld["total_market_cap"] is None
    assert withheld["stance"] == "Market-cap read unavailable"
    assert withheld["flows"]["etf"]["value"] == 200.0
    assert withheld["flows"]["stablecoins"]["change_30d_usd"] is not None
    _assert_no_inflow_claim(withheld)

    no_volume = dict(frames)
    no_volume[("coinbase", "btc_daily")] = pd.DataFrame({"close": price}, index=dates)
    quiet = build_market_state(_read(no_volume), today=dates[-1])
    assert quiet["flows"]["volume"]["percentile"] is None
    assert quiet["flows"]["volume"]["state"] == "Unavailable"
    assert quiet["flows"]["volume"]["value"] is None
    assert quiet["flows"]["etf"]["value"] == 200.0
