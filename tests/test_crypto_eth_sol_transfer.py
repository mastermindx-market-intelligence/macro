"""ETH/SOL display-tier transfer of the BTC price-path signals. Fixtures only.

The transfer must call engine.btc_signals on the same close. It must not
reimplement the votes, and it must not emit an allocation or a size.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import btc_signals as S  # noqa: E402
from engine.crypto_universe import (  # noqa: E402
    display_price_path,
    price_path_listing_floor,
)
from lib import config  # noqa: E402

_VALUE_COLUMNS = (
    "momentum", "momentum_state", "risk_index", "risk_oscillator", "risk_regime",
)
_BANNED = ("alloc", "size", "expos", "recommend", "weight", "position")


def _close(start: str, n: int, seed: int, drift: float = 0.001, vol: float = 0.02) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="D")
    path = 100.0 * np.exp(np.cumsum(rng.normal(drift, vol, n)))
    return pd.Series(path, index=idx, name="close")


def _direct(close: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The BTC functions on this close, with every non-price leg omitted."""
    inputs = {"price": pd.DataFrame({"close": close})}
    vector = config.load()["vector"]
    mom = S.momentum(inputs, vector["momentum"])
    rk = S.risk(inputs, mom["momentum"], vector["risk"])
    return mom, rk


def _assert_no_size_columns(frame: pd.DataFrame) -> None:
    banned = [name for name in frame.columns if any(tok in name.lower() for tok in _BANNED)]
    assert banned == []
    assert list(frame.columns) == [
        "asset", "tier", "authority",
        "momentum", "momentum_state",
        "risk_index", "risk_oscillator", "risk_regime",
    ]


def _assert_display_rows(frame: pd.DataFrame, asset: str) -> None:
    assert len(frame) > 0
    assert (frame["asset"] == asset).all()
    assert (frame["tier"] == "display").all()
    assert (frame["authority"] == "none").all()
    _assert_no_size_columns(frame)


def test_listing_floors_are_the_coinbase_config_dates() -> None:
    coinbase = config.load()["coinbase"]
    assert coinbase["eth_earliest"] == "2016-06-01"
    assert coinbase["sol_earliest"] == "2021-06-17"
    assert price_path_listing_floor("ETH") == pd.Timestamp("2016-06-01")
    assert price_path_listing_floor("SOL") == pd.Timestamp("2021-06-17")


def test_btc_parity_on_shared_price_fixture() -> None:
    # Same positive daily path the BTC engine would score, dated after both
    # listing floors so the display mask does not change a single cell.
    close = _close("2022-01-01", 420, seed=1)
    mom, rk = _direct(close)
    for asset in ("ETH", "SOL"):
        out = display_price_path(close, asset)
        _assert_display_rows(out, asset)
        pd.testing.assert_series_equal(
            out["momentum"], mom["momentum"], check_names=False, check_freq=False)
        pd.testing.assert_series_equal(
            out["momentum_state"], mom["momentum_state"], check_names=False,
            check_freq=False, check_dtype=False)
        pd.testing.assert_series_equal(
            out["risk_index"], rk["risk_index"], check_names=False, check_freq=False)
        pd.testing.assert_series_equal(
            out["risk_oscillator"], rk["risk_oscillator"], check_names=False,
            check_freq=False)
        pd.testing.assert_series_equal(
            out["risk_regime"], rk["risk_regime"], check_names=False,
            check_freq=False, check_dtype=False)


def test_transfer_calls_btc_signals_on_the_price_only(monkeypatch) -> None:
    close = _close("2022-06-01", 80, seed=2)
    seen = {}
    real_mom = S.momentum
    real_risk = S.risk

    def momentum(inputs, cfg):
        seen["momentum_keys"] = set(inputs)
        seen["price_columns"] = list(inputs["price"].columns)
        return real_mom(inputs, cfg)

    def risk(inputs, mom, cfg):
        seen["risk_keys"] = set(inputs)
        seen["mom_is_momentum_output"] = mom.equals(seen["mom_series"])
        return real_risk(inputs, mom, cfg)

    def momentum_record(inputs, cfg):
        out = momentum(inputs, cfg)
        seen["mom_series"] = out["momentum"]
        return out

    monkeypatch.setattr(S, "momentum", momentum_record)
    monkeypatch.setattr(S, "risk", risk)
    out = display_price_path(close, "ETH")
    assert seen["momentum_keys"] == {"price"}
    assert seen["risk_keys"] == {"price"}
    assert seen["price_columns"] == ["close"]
    assert seen["mom_is_momentum_output"] is True
    _assert_display_rows(out, "ETH")


def test_no_value_before_listing_floor() -> None:
    for asset, start, n in (
        ("ETH", "2015-01-01", 900),
        ("SOL", "2020-01-01", 900),
    ):
        floor = price_path_listing_floor(asset)
        close = _close(start, n, seed=4 if asset == "ETH" else 5)
        assert close.index[0] < floor < close.index[-1]
        out = display_price_path(close, asset)
        pre = out.loc[out.index < floor]
        assert len(pre) > 100
        assert pre["momentum"].isna().all()
        assert pre["risk_index"].isna().all()
        assert pre["risk_oscillator"].isna().all()
        assert (pre["momentum_state"] == "unavailable").all()
        assert (pre["risk_regime"] == "unavailable").all()
        # A missing pre-listing row is not a zero print and not a backfill
        # of the first session on or after the floor.
        assert not pre["momentum"].eq(0).any()
        assert not pre["risk_index"].eq(0).any()
        assert not pre["risk_oscillator"].eq(0).any()
        # The listing date itself is an observation. It is not backfilled from
        # a later print, and it is not held at zero.
        assert out.loc[floor, "momentum_state"] != "unavailable"
        assert pd.notna(out.loc[floor, "momentum"])
        post = out.loc[out.index >= floor, "momentum"]
        assert post.notna().any()
        _assert_display_rows(out, asset)


def test_pre_floor_prices_do_not_enter_the_signal() -> None:
    for asset in ("ETH", "SOL"):
        floor = price_path_listing_floor(asset)
        start = floor - pd.Timedelta(days=300)
        close = _close(str(start.date()), 700, seed=8)
        full = display_price_path(close, asset)
        listed = display_price_path(close.loc[close.index >= floor], asset)
        pd.testing.assert_series_equal(
            full.loc[listed.index, "momentum"], listed["momentum"],
            check_names=False, check_freq=False)
        pd.testing.assert_series_equal(
            full.loc[listed.index, "risk_index"], listed["risk_index"],
            check_names=False, check_freq=False)
        pd.testing.assert_series_equal(
            full.loc[listed.index, "risk_oscillator"], listed["risk_oscillator"],
            check_names=False, check_freq=False)
        assert (
            full.loc[listed.index, "momentum_state"].to_numpy()
            == listed["momentum_state"].to_numpy()
        ).all()
        assert (
            full.loc[listed.index, "risk_regime"].to_numpy()
            == listed["risk_regime"].to_numpy()
        ).all()


def test_lookahead_invariance() -> None:
    close = _close("2022-01-01", 500, seed=6)
    close.iloc[120] = np.nan
    close.iloc[121] = np.nan
    cut = 310
    for asset in ("ETH", "SOL"):
        full = display_price_path(close, asset)
        prefix = display_price_path(close.iloc[:cut], asset)
        for column in _VALUE_COLUMNS:
            left = prefix[column]
            right = full[column].iloc[:cut]
            if column in ("momentum", "risk_index", "risk_oscillator"):
                both_missing = left.isna() & right.isna()
                assert np.allclose(
                    left.to_numpy(dtype=float)[~both_missing.to_numpy()],
                    right.to_numpy(dtype=float)[~both_missing.to_numpy()],
                    atol=0.0, rtol=0.0, equal_nan=True,
                )
                assert left.isna().to_numpy().tolist() == right.isna().to_numpy().tolist()
            else:
                assert left.tolist() == right.tolist()
        t = prefix.index[-1]
        assert prefix.loc[t, "momentum_state"] == full.loc[t, "momentum_state"]
        assert prefix.loc[t, "risk_regime"] == full.loc[t, "risk_regime"]
        if pd.notna(prefix.loc[t, "momentum"]):
            assert prefix.loc[t, "momentum"] == full.loc[t, "momentum"]
        _assert_display_rows(prefix, asset)


def test_missing_day_stays_missing() -> None:
    close = _close("2022-01-01", 450, seed=9)
    hole = close.index[200:215]  # 15 sessions, longer than a 3-day fill limit
    gappy = close.copy()
    gappy.loc[hole] = np.nan
    gappy.loc[close.index[240]] = 0.0
    gappy.loc[close.index[241]] = -3.0
    gappy.loc[close.index[242]] = np.inf
    out = display_price_path(gappy, "SOL")
    blocked = hole.append(close.index[240:243])
    assert out.loc[blocked, "momentum"].isna().all()
    assert out.loc[blocked, "risk_index"].isna().all()
    assert out.loc[blocked, "risk_oscillator"].isna().all()
    assert (out.loc[blocked, "momentum_state"] == "unavailable").all()
    assert (out.loc[blocked, "risk_regime"] == "unavailable").all()
    assert not out.loc[blocked, "momentum"].eq(0).any()
    assert not out.loc[blocked, "risk_index"].eq(0).any()
    assert not out.loc[blocked, "risk_oscillator"].eq(0).any()
    # Forward-filling the hole would publish a number. This frame does not.
    filled = display_price_path(gappy.ffill(), "SOL")
    assert filled.loc[hole, "momentum"].notna().all()
    assert out.loc[hole, "momentum"].isna().all()
    # The hole is not a copy of the last good print.
    last_good = close.index[199]
    assert out.loc[last_good, "momentum_state"] != "unavailable"
    assert (out.loc[hole, "momentum_state"] == "unavailable").all()
    _assert_display_rows(out, "SOL")


def test_absent_calendar_day_is_not_inserted() -> None:
    close = _close("2022-03-01", 160, seed=11)
    dropped_at = close.index[40:48]
    kept = close.drop(dropped_at)
    out = display_price_path(kept, "ETH")
    assert out.index.equals(kept.index)
    assert all(day not in out.index for day in dropped_at)
    _assert_display_rows(out, "ETH")


def test_rows_carry_display_tier_and_no_allocation() -> None:
    close = _close("2021-01-01", 200, seed=12)  # straddles the SOL floor, not the ETH floor
    eth = display_price_path(close, "ETH")
    sol = display_price_path(close, "SOL")
    _assert_display_rows(eth, "ETH")
    _assert_display_rows(sol, "SOL")
    assert eth["momentum"].notna().any()
    assert sol.loc[sol.index < price_path_listing_floor("SOL"), "momentum"].isna().all()
    for frame in (eth, sol):
        assert "allocation" not in frame.columns
        assert not any(name.startswith("alloc_") for name in frame.columns)
