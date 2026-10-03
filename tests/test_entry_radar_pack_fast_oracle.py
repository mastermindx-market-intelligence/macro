"""Pack solver uses O(1) append oracle; canonical path remains fallback."""
from __future__ import annotations

import time
from datetime import date

import numpy as np
import pandas as pd
import pytest

from engine import session_anchor
from engine.entry_radar import indicator_core as ic
from engine.entry_radar import live_pack as lp

AS_OF = date(2026, 8, 14)
NEXT_SESSION = date(2026, 8, 17)
MARKET = "US"


def _random_walk_frame(n: int, *, seed: int = 20261003, end: date = AS_OF) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    reference = session_anchor.reference_sessions("US")
    position = int(reference.searchsorted(pd.Timestamp(end).normalize(), side="right"))
    sessions = reference[max(0, position - n):position]
    n = len(sessions)
    closes = 100.0 + np.cumsum(rng.normal(0, 1.0, n))
    return pd.DataFrame(
        {"high": closes * 1.01, "low": closes * 0.99, "close": closes},
        index=pd.DatetimeIndex(sessions),
    )


def _oracle_from_frame(ticker: str, frozen: pd.DataFrame) -> lp.OracleFrame:
    index = pd.DatetimeIndex(frozen.index)
    return lp.oracle_frame(
        ticker=ticker,
        closes=frozen["close"].astype(float).to_numpy(dtype=float),
        index=index,
        next_session_ts=pd.Timestamp(NEXT_SESSION).normalize(),
    )


def _prices_for_frame(frozen: pd.DataFrame, n: int = 30) -> np.ndarray:
    last = float(frozen["close"].astype(float).iloc[-1])
    return np.geomspace(0.05 * last, 3.0 * last, n)


@pytest.mark.parametrize("n_bars", (300, 600, 3000))
def test_fast_and_canonical_kd_agree(n_bars: int) -> None:
    frozen = lp._synthetic_daily(n_bars, start=120.0, step=-0.2, end_session=AS_OF)
    oracle = _oracle_from_frame("SYN", frozen)
    for price in _prices_for_frame(frozen):
        fast_k, fast_d = oracle.kd(float(price))
        canon_k, canon_d = oracle.kd_canonical(float(price))
        assert (fast_k is None) == (canon_k is None)
        assert (fast_d is None) == (canon_d is None)
        if fast_k is not None and canon_k is not None:
            assert abs(fast_k - canon_k) <= 1e-9
        if fast_d is not None and canon_d is not None:
            assert abs(fast_d - canon_d) <= 1e-9


@pytest.mark.parametrize("n_bars", (300, 600, 3000))
def test_pack_name_is_identical_with_fast_and_canonical_oracle(
    n_bars: int, monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _random_walk_frame(n_bars)
    kwargs = dict(next_session=NEXT_SESSION, market=MARKET)
    fast_name = lp._pack_name("RW", frozen, **kwargs)
    monkeypatch.setattr(ic, "stoch_rsi_append_state", lambda _c: None)
    canon_name = lp._pack_name("RW", frozen, **kwargs)
    assert fast_name == canon_name


def test_pack_hash_is_identical_with_fast_and_canonical_oracle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_entry_radar_w4_pack import build

    fast_pack = build()
    monkeypatch.setattr(ic, "stoch_rsi_append_state", lambda _c: None)
    canon_pack = build()
    assert fast_pack.pack_hash == canon_pack.pack_hash


def test_short_history_falls_back_to_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    frozen = lp._synthetic_daily(20, start=100.0, step=0.5, end_session=AS_OF)
    oracle = _oracle_from_frame("SHORT", frozen)
    assert oracle.append_state is None
    kwargs = dict(next_session=NEXT_SESSION, market=MARKET)
    fast_name = lp._pack_name("SHORT", frozen, **kwargs)
    monkeypatch.setattr(ic, "stoch_rsi_append_state", lambda _c: None)
    canon_name = lp._pack_name("SHORT", frozen, **kwargs)
    assert fast_name == canon_name


def test_pack_name_is_much_faster_with_the_fast_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    frozen = lp._synthetic_daily(11544, start=100.0, step=0.01, end_session=AS_OF)
    kwargs = dict(next_session=NEXT_SESSION, market=MARKET)
    monkeypatch.setattr(lp, "substrate_fingerprint", lambda _f: "bench")
    monkeypatch.setattr(ic, "stoch_rsi_append_state", lambda _c: None)
    t0 = time.perf_counter()
    lp._pack_name("BIG", frozen, **kwargs)
    canon_s = time.perf_counter() - t0
    monkeypatch.undo()
    monkeypatch.setattr(lp, "substrate_fingerprint", lambda _f: "bench")
    t1 = time.perf_counter()
    lp._pack_name("BIG", frozen, **kwargs)
    fast_s = time.perf_counter() - t1
    assert fast_s * 5 <= canon_s, f"fast={fast_s:.4f}s canon={canon_s:.4f}s ratio={canon_s/fast_s:.1f}x"


def test_default_oracle_frame_construction_is_canonical() -> None:
    frozen = lp._synthetic_daily(200, start=100.0, step=0.1, end_session=AS_OF)
    index = pd.DatetimeIndex(frozen.index)
    closes = frozen["close"].astype(float).to_numpy(dtype=float)
    oracle = lp.OracleFrame(
        ticker="LEG",
        closes=closes,
        index=index,
        next_session_ts=pd.Timestamp(NEXT_SESSION).normalize(),
    )
    assert oracle.append_state is None
    for price in _prices_for_frame(frozen, n=10):
        assert oracle.kd(float(price)) == oracle.kd_canonical(float(price))
