"""Clock and absence injections for the Crypto/Vector read projections.

The contract is the one T02 has to qualify: a projection that consumes a
collector frame must not turn a missing cell into zero, must not surface a
future-dated row as an available value, must distinguish a stale print from a
real zero, and must keep an A→B revision visible.

``AS_OF`` is the decision clock. The projections under test have no as-of
argument. They are still required to withhold rows after ``AS_OF`` and rows
whose receipt column is after ``AS_OF``. A projection that cannot do that
fails the test. Do not loosen these assertions to match today's code.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from engine import btc_inputs
from engine import crypto_market_state as cms
from lib import store

AS_OF = pd.Timestamp("2026-10-11")
FUTURE = pd.Timestamp("2026-10-20")
RECEIPT_AFTER = "2026-10-20T00:00:00+00:00"


def _put(root: Path, group: str, name: str, frame: pd.DataFrame) -> None:
    path = root / group / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)


def _idx(*days: str) -> pd.DatetimeIndex:
    return pd.to_datetime(list(days))


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(store.config, "data_dir", lambda: tmp_path)
    return tmp_path


def _price(root: Path, close: float = 100.0, day: str = "2026-10-10") -> None:
    _put(
        root,
        "coinbase",
        "btc_daily",
        pd.DataFrame(
            {
                "open": [close],
                "high": [close],
                "low": [close],
                "close": [close],
                "volume": [1.0],
            },
            index=_idx(day),
        ),
    )


# --- absence and zero stay distinct (these projections already do this) ---


def test_col_absent_frame_is_none_not_zero(root: Path) -> None:
    assert btc_inputs._col("coinmetrics", "mcap_usd") is None


def test_col_empty_frame_is_none_not_zero(root: Path) -> None:
    _put(
        root,
        "coinmetrics",
        "mcap_usd",
        pd.DataFrame({"mcap_usd": pd.Series(dtype="float64")}, index=pd.DatetimeIndex([])),
    )
    assert btc_inputs._col("coinmetrics", "mcap_usd") is None


def test_col_nan_cell_is_not_replaced_with_zero(root: Path) -> None:
    _put(
        root,
        "coinmetrics",
        "mcap_usd",
        pd.DataFrame({"mcap_usd": [float("nan")]}, index=_idx("2026-10-10")),
    )
    series = btc_inputs._col("coinmetrics", "mcap_usd", "mcap_usd")
    assert series is not None and len(series) == 1
    assert pd.isna(series.iloc[0])


def test_col_observed_zero_stays_zero(root: Path) -> None:
    _put(
        root,
        "coinmetrics",
        "mcap_usd",
        pd.DataFrame({"mcap_usd": [0.0]}, index=_idx("2026-10-10")),
    )
    series = btc_inputs._col("coinmetrics", "mcap_usd", "mcap_usd")
    assert series is not None
    assert float(series.iloc[0]) == 0.0
    assert not pd.isna(series.iloc[0])


def test_funding_missing_field_is_none_not_mark_price(root: Path) -> None:
    _put(
        root,
        "bgeo",
        "funding_rate",
        pd.DataFrame({"funding_rate_markPrice": [65000.0]}, index=_idx("2026-10-10")),
    )
    assert btc_inputs._funding() is None


def test_funding_nan_is_not_zero(root: Path) -> None:
    _put(
        root,
        "bgeo",
        "funding_rate",
        pd.DataFrame(
            {"funding_rate_fundingRate": [float("nan")], "funding_rate_markPrice": [65000.0]},
            index=_idx("2026-10-10"),
        ),
    )
    series = btc_inputs._funding()
    assert series is not None and len(series) == 1
    assert pd.isna(series.iloc[0])


def test_funding_observed_zero_stays_zero(root: Path) -> None:
    _put(
        root,
        "bgeo",
        "funding_rate",
        pd.DataFrame(
            {"funding_rate_fundingRate": [0.0], "funding_rate_markPrice": [65000.0]},
            index=_idx("2026-10-10"),
        ),
    )
    series = btc_inputs._funding()
    assert series is not None
    assert float(series.iloc[0]) == 0.0


def test_load_price_absent_raises_instead_of_a_zero_frame(root: Path) -> None:
    with pytest.raises(RuntimeError, match="no BTC price"):
        btc_inputs.load_price()


def test_load_price_missing_close_is_dropped_not_zeroed(root: Path) -> None:
    _put(
        root,
        "coinbase",
        "btc_daily",
        pd.DataFrame(
            {
                "open": [1.0, 5.0],
                "high": [1.0, 5.0],
                "low": [1.0, 5.0],
                "close": [float("nan"), 5.0],
                "volume": [1.0, 2.0],
            },
            index=_idx("2026-10-09", "2026-10-10"),
        ),
    )
    price = btc_inputs.load_price()
    assert list(price["close"]) == [5.0]
    assert 0.0 not in set(price["close"])


def test_hourly_absent_is_none(root: Path) -> None:
    assert btc_inputs.load_hourly() is None


def test_intraday_vol_absent_hourly_is_none(root: Path) -> None:
    assert btc_inputs.intraday_vol_daily(None) is None
    assert btc_inputs.intraday_vol_daily(pd.DataFrame()) is None


def test_intraday_vol_partial_bar_is_not_zero(root: Path) -> None:
    _put(
        root,
        "coinbase",
        "btc_hourly",
        pd.DataFrame(
            {
                "open": [10.0],
                "high": [float("nan")],
                "low": [10.0],
                "close": [10.0],
                "volume": [1.0],
            },
            index=pd.to_datetime(["2026-10-10 12:00"]),
        ),
    )
    vol = btc_inputs.intraday_vol_daily(btc_inputs.load_hourly())
    assert vol is not None and len(vol) == 1
    assert pd.isna(vol.iloc[0])


def test_series_absent_is_empty_not_zero(root: Path) -> None:
    series = cms._series(store.read, "sentiment_crypto", "fear_greed", ("fear_greed",))
    assert series.empty


def test_market_state_absent_inputs_are_none_not_zero(root: Path) -> None:
    state = cms.build_market_state()
    assert state["total_market_cap"] is None
    assert state["total_30d_pct"] is None
    assert state["btc_dominance"] is None
    assert state["fear_greed"] is None
    assert state["fear_state"] == "Unavailable"
    assert state["flows"]["etf"]["value"] is None
    assert state["flows"]["stablecoins"]["value"] is None
    assert state["flows"]["volume"]["value"] is None
    assert state["heat"]["funding"]["value"] is None
    assert state["heat"]["funding"]["state"] == "Unavailable"
    assert state["heat"]["open_interest"]["value"] is None
    assert state["heat"]["open_interest"]["state"] == "Unavailable"
    assert state["heat"]["volatility"]["value"] is None
    assert state["heat"]["volatility"]["state"] == "Unavailable"
    assert state["history"]["vals"] == []


def test_heat_funding_observed_zero_stays_balanced(root: Path) -> None:
    _put(
        root,
        "vector",
        "signals",
        pd.DataFrame({"funding_annual_pct": [0.0]}, index=_idx("2026-10-11")),
    )
    state = cms.build_market_state()
    assert state["heat"]["funding"]["value"] == 0.0
    assert state["heat"]["funding"]["state"] == "Balanced"


# --- cases the projections cannot distinguish: these must fail as written ---


def test_col_future_row_is_not_available(root: Path) -> None:
    _put(
        root,
        "coinmetrics",
        "mcap_usd",
        pd.DataFrame({"mcap_usd": [100.0, 999.0]}, index=pd.DatetimeIndex([AS_OF - pd.Timedelta(days=1), FUTURE])),
    )
    series = btc_inputs._col("coinmetrics", "mcap_usd", "mcap_usd")
    assert series is not None
    assert series.index.max() <= AS_OF
    assert 999.0 not in set(series.dropna().tolist())


def test_funding_future_row_is_not_available(root: Path) -> None:
    _put(
        root,
        "bgeo",
        "funding_rate",
        pd.DataFrame(
            {"funding_rate_fundingRate": [0.0001, 0.01]},
            index=pd.DatetimeIndex([AS_OF - pd.Timedelta(days=1), FUTURE]),
        ),
    )
    series = btc_inputs._funding()
    assert series is not None
    assert series.index.max() <= AS_OF
    assert 0.01 not in set(series.dropna().tolist())


def test_load_price_future_close_is_not_available(root: Path) -> None:
    _put(
        root,
        "coinbase",
        "btc_daily",
        pd.DataFrame(
            {
                "open": [100.0, 999.0],
                "high": [100.0, 999.0],
                "low": [100.0, 999.0],
                "close": [100.0, 999.0],
                "volume": [1.0, 1.0],
            },
            index=pd.DatetimeIndex([AS_OF - pd.Timedelta(days=1), FUTURE]),
        ),
    )
    price = btc_inputs.load_price()
    assert price.index.max() <= AS_OF
    assert 999.0 not in set(price["close"].tolist())


def test_intraday_vol_future_bar_is_not_available(root: Path) -> None:
    _put(
        root,
        "coinbase",
        "btc_hourly",
        pd.DataFrame(
            {
                "open": [10.0],
                "high": [12.0],
                "low": [9.0],
                "close": [11.0],
                "volume": [1.0],
            },
            index=pd.to_datetime(["2026-10-20 15:00"]),
        ),
    )
    vol = btc_inputs.intraday_vol_daily(btc_inputs.load_hourly())
    assert vol is None or vol.index.max() <= AS_OF


def test_series_future_row_is_not_available(root: Path) -> None:
    _put(
        root,
        "sentiment_crypto",
        "fear_greed",
        pd.DataFrame({"fear_greed": [80.0]}, index=pd.DatetimeIndex([FUTURE])),
    )
    series = cms._series(store.read, "sentiment_crypto", "fear_greed", ("fear_greed",))
    assert series.empty or series.index.max() <= AS_OF


def test_market_state_future_cap_is_not_available(root: Path) -> None:
    _put(
        root,
        "coingecko",
        "global_market",
        pd.DataFrame(
            {"total_mcap_usd": [1.0e12, 9.0e12]},
            index=pd.DatetimeIndex([AS_OF - pd.Timedelta(days=1), FUTURE]),
        ),
    )
    state = cms.build_market_state()
    assert state["as_of"] <= str(AS_OF.date())
    assert state["total_market_cap"] != 9.0e12
    assert 9.0e12 not in state["history"]["vals"]


def test_col_revision_a_to_b_is_visible(root: Path) -> None:
    _put(
        root,
        "coinmetrics",
        "mcap_usd",
        pd.DataFrame({"mcap_usd": [1.0, 2.0]}, index=_idx("2026-10-10", "2026-10-10")),
    )
    series = btc_inputs._col("coinmetrics", "mcap_usd", "mcap_usd")
    assert series is not None
    seen = [float(v) for v in series.tolist()]
    assert 1.0 in seen and 2.0 in seen


def test_funding_revision_a_to_b_is_visible(root: Path) -> None:
    _put(
        root,
        "bgeo",
        "funding_rate",
        pd.DataFrame(
            {"funding_rate_fundingRate": [0.0001, 0.0002]},
            index=_idx("2026-10-10", "2026-10-10"),
        ),
    )
    series = btc_inputs._funding()
    assert series is not None
    seen = [float(v) for v in series.tolist()]
    assert 0.0001 in seen and 0.0002 in seen


def test_market_state_revision_a_to_b_is_visible(root: Path) -> None:
    _put(
        root,
        "sentiment_crypto",
        "fear_greed",
        pd.DataFrame({"fear_greed": [10.0, 40.0]}, index=_idx("2026-10-10", "2026-10-10")),
    )
    state = cms.build_market_state()
    assert state.get("fear_prior") == 10.0 or state.get("fear_revised") is True


def test_market_state_stale_zero_is_not_a_current_zero(root: Path) -> None:
    _price(root, day="2026-10-11")
    _put(
        root,
        "sentiment_crypto",
        "fear_greed",
        pd.DataFrame({"fear_greed": [0.0]}, index=_idx("2026-09-01")),
    )
    state = cms.build_market_state()
    fear_as_of = state.get("fear_as_of")
    assert not (
        state["fear_greed"] == 0.0
        and state["fear_state"] == "Extreme fear"
        and state["as_of"] == "2026-10-11"
        and fear_as_of in (None, "2026-10-11")
    )


def test_heat_funding_stale_zero_is_not_a_current_zero(root: Path) -> None:
    _price(root, day="2026-10-11")
    _put(
        root,
        "vector",
        "signals",
        pd.DataFrame({"funding_annual_pct": [0.0]}, index=_idx("2026-09-01")),
    )
    state = cms.build_market_state()
    funding = state["heat"]["funding"]
    assert not (
        funding["value"] == 0.0
        and funding["state"] == "Balanced"
        and state["as_of"] == "2026-10-11"
        and funding.get("as_of") in (None, "2026-10-11")
    )


def test_market_state_delayed_receipt_is_not_available(root: Path) -> None:
    _put(
        root,
        "sentiment_crypto",
        "fear_greed",
        pd.DataFrame(
            {"fear_greed": [10.0], "received_at": [RECEIPT_AFTER]},
            index=_idx("2026-10-10"),
        ),
    )
    state = cms.build_market_state()
    assert state["fear_greed"] is None
    assert state["fear_state"] == "Unavailable"


def test_col_delayed_receipt_is_not_available(root: Path) -> None:
    _put(
        root,
        "coinmetrics",
        "mcap_usd",
        pd.DataFrame(
            {"mcap_usd": [100.0], "received_at": [RECEIPT_AFTER]},
            index=_idx("2026-10-10"),
        ),
    )
    series = btc_inputs._col("coinmetrics", "mcap_usd", "mcap_usd")
    assert series is not None
    receipt = series.attrs.get("received_at")
    assert receipt is not None and pd.Timestamp(receipt) <= AS_OF


def test_market_state_partial_latest_cell_stays_unavailable(root: Path) -> None:
    _put(
        root,
        "sentiment_crypto",
        "fear_greed",
        pd.DataFrame({"fear_greed": [20.0, float("nan")]}, index=_idx("2026-10-09", "2026-10-10")),
    )
    state = cms.build_market_state()
    assert state["fear_greed"] is None
    assert state["fear_state"] == "Unavailable"


def test_market_state_absent_volume_state_is_not_normal(root: Path) -> None:
    state = cms.build_market_state()
    assert state["flows"]["volume"]["value"] is None
    assert state["flows"]["volume"]["state"] != "Normal"


def test_ssr_missing_stablecoin_day_stays_missing(root: Path) -> None:
    _price(root)
    days = _idx("2026-10-09", "2026-10-10")
    _put(root, "coinmetrics", "mcap_usd", pd.DataFrame({"mcap_usd": [100.0, 100.0]}, index=days))
    _put(
        root,
        "defillama",
        "stablecoins",
        pd.DataFrame({"stablecoin_mcap_usd": [50.0, float("nan")]}, index=days),
    )
    loaded = btc_inputs.load_all()
    ssr = loaded.get("ssr")
    assert ssr is not None
    assert pd.isna(ssr.loc[pd.Timestamp("2026-10-10")])


def test_supply_fraction_missing_supply_day_stays_missing(root: Path) -> None:
    _price(root)
    days = _idx("2026-10-09", "2026-10-10")
    _put(
        root,
        "bgeo",
        "supply_in_profit",
        pd.DataFrame({"supply_in_profit": [10.0, 10.0]}, index=days),
    )
    _put(
        root,
        "coinmetrics",
        "supply",
        pd.DataFrame({"supply": [100.0, float("nan")]}, index=days),
    )
    loaded = btc_inputs.load_all()
    frac = loaded.get("supply_in_profit_pct")
    assert frac is not None
    assert pd.isna(frac.loc[pd.Timestamp("2026-10-10")])


def test_total_cap_gap_is_not_filled(root: Path) -> None:
    _put(
        root,
        "coinmetrics",
        "mcap_usd",
        pd.DataFrame({"mcap_usd": [100.0, 100.0]}, index=_idx("2026-10-08", "2026-10-11")),
    )
    _put(
        root,
        "bgeo",
        "btc_dominance",
        pd.DataFrame({"btc_dominance": [50.0]}, index=_idx("2026-10-08")),
    )
    history = cms.total_market_cap_history()
    assert pd.Timestamp("2026-10-11") not in history.index


def test_etf_partial_window_is_not_a_five_day_sum(root: Path) -> None:
    _put(
        root,
        "farside",
        "etf_flows",
        pd.DataFrame(
            {"total": [10.0, 10.0, 10.0, 10.0, 10.0]},
            index=_idx("2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-11"),
        ),
    )
    state = cms.build_market_state()
    # Calendar window [2026-10-07, 2026-10-11] contains only the last print.
    assert state["flows"]["etf"]["value"] in (None, 10.0)


def test_fred_weekend_gap_is_labeled_nonpublication(root: Path) -> None:
    _put(
        root,
        "fred",
        "DGS10",
        pd.DataFrame({"DGS10": [4.1, 4.2]}, index=_idx("2026-10-09", "2026-10-12")),
    )
    series = btc_inputs._col("fred", "DGS10")
    assert series is not None
    labeled = list(series.attrs.get("nonpublication") or [])
    assert pd.Timestamp("2026-10-10") in labeled
    assert pd.Timestamp("2026-10-11") in labeled
