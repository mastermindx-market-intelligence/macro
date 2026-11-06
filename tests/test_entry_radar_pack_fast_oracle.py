"""Pack solver uses O(1) append oracle; canonical path remains fallback."""
from __future__ import annotations

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

TIE_CLOSES = [99.4597, 99.0027, 97.1181, 97.026, 96.2893, 94.6524, 94.7427, 94.1512, 94.047, 93.2803, 92.4366, 91.6211, 91.0543, 90.0588, 89.3828, 90.6229, 91.27, 90.7681, 90.7223, 90.4144, 89.9728, 89.4038, 89.5458, 88.4904, 88.7658, 88.2663, 88.9709, 88.6996, 88.3995, 88.4796, 88.4244, 87.9712, 87.4539, 86.5593, 86.2221, 86.7643, 86.4427, 86.0194, 85.9174, 85.161, 84.1989, 83.443, 83.4819, 82.5725]

_C2A_PREDICATE = (
    "K_T > D_T (the current half of A5.3's c2a; the K_prev <= D_prev "
    "half is a path property and is never inverted into a level)"
)


def _tie_oracle_frames() -> tuple[lp.OracleFrame, lp.OracleFrame]:
    c = np.asarray(TIE_CLOSES, dtype=float)
    idx = pd.bdate_range("2020-01-01", periods=len(c))
    nxt = idx[-1] + pd.tseries.offsets.BDay(1)
    fast = lp.oracle_frame("X", c, idx, nxt, fast=True)
    canon = lp.oracle_frame("X", c, idx, nxt, fast=False)
    return fast, canon


def _solve_c1(frame: lp.OracleFrame) -> lp.ThresholdSolution:
    return lp.solve_threshold(
        lambda p: lp._c1_margin(frame, p),
        condition="c1_arm_price",
        predicate=f"K_T < {ic.OVERSOLD} (A5.2 arm condition)",
        anchor=float(TIE_CLOSES[-1]),
        decreasing=True,
    )


def _solve_c2a(frame: lp.OracleFrame) -> lp.ThresholdSolution:
    return lp.solve_threshold(
        lambda p: lp._c2a_margin(frame, p),
        condition="c2a_cross_price",
        predicate=_C2A_PREDICATE,
        anchor=float(TIE_CLOSES[-1]),
        decreasing=False,
    )


def _fast_frame_for_kd_tests(monkeypatch: pytest.MonkeyPatch) -> lp.OracleFrame:
    frozen = lp._synthetic_daily(200, start=100.0, step=0.1, end_session=AS_OF)
    frame = _oracle_from_frame("KD", frozen)
    assert frame.append_state is not None
    return frame


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


def test_fast_pack_name_makes_one_full_history_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}
    real_kd = ic.stoch_rsi_kd

    def counting_kd(s: pd.Series) -> tuple[pd.Series, pd.Series]:
        calls["n"] += 1
        return real_kd(s)

    monkeypatch.setattr(ic, "stoch_rsi_kd", counting_kd)
    frozen = lp._synthetic_daily(600, start=100.0, step=0.01, end_session=AS_OF)
    kwargs = dict(next_session=NEXT_SESSION, market=MARKET)
    lp._pack_name("CNT", frozen, **kwargs)
    fast_calls = calls["n"]
    calls["n"] = 0
    monkeypatch.setattr(ic, "stoch_rsi_append_state", lambda _c: None)
    lp._pack_name("CNT", frozen, **kwargs)
    canon_calls = calls["n"]
    assert fast_calls <= 2
    assert canon_calls >= 40


def test_inversion_proof_never_calls_the_fast_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_entry_radar_w4_pack import build

    pack = build()
    def _proof_must_be_canonical(_s: ic.StochRsiAppendState, _p: float) -> tuple[float | None, float | None]:
        raise AssertionError("proof must be canonical")

    monkeypatch.setattr(ic, "stoch_rsi_kd_appended", _proof_must_be_canonical)
    proof = lp.build_inversion_proof(pack)
    assert proof["pass"] is True
    assert proof["cases_total"] > 0


def test_inversion_proof_fails_when_the_fast_oracle_is_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_entry_radar_w4_pack import build

    real_appended = ic.stoch_rsi_kd_appended

    def wrong_k(_s: ic.StochRsiAppendState, price: float) -> tuple[float | None, float | None]:
        k, d = real_appended(_s, price)
        return (k + 15.0 if k is not None else None, d)

    monkeypatch.setattr(ic, "stoch_rsi_kd_appended", wrong_k)
    pack = build()
    monkeypatch.undo()
    proof = lp.build_inversion_proof(pack)
    assert proof["pass"] is False
    failures = proof.get("failures") or []
    assert any(f.get("family") == "threshold_boundary" for f in failures)


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


def test_tie_series_solves_identically_fast_and_canonical() -> None:
    fast, canon = _tie_oracle_frames()
    reproduced = not _solve_c2a(canon).no_threshold_exists
    assert _solve_c2a(fast).to_dict() == _solve_c2a(canon).to_dict()
    assert _solve_c1(fast).to_dict() == _solve_c1(canon).to_dict()
    _ = reproduced


def test_kd_inside_the_k_equals_d_band_answers_canonically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _fast_frame_for_kd_tests(monkeypatch)
    calls = {"n": 0}

    def canon(_self: lp.OracleFrame, _price: float) -> tuple[float, float]:
        calls["n"] += 1
        return (5.0, 5.0)

    monkeypatch.setattr(
        ic, "stoch_rsi_kd_appended", lambda _s, _p: (5.0 + 2.5e-14, 5.0),
    )
    monkeypatch.setattr(lp.OracleFrame, "kd_canonical", canon)
    assert frame.kd(50.0) == (5.0, 5.0)
    assert calls["n"] == 1
    assert lp._c2a_margin(frame, 50.0) == 0.0


def test_kd_inside_the_oversold_band_answers_canonically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _fast_frame_for_kd_tests(monkeypatch)
    calls = {"n": 0}

    def canon(_self: lp.OracleFrame, _price: float) -> tuple[float, float]:
        calls["n"] += 1
        return (20.0, 3.0)

    monkeypatch.setattr(
        ic, "stoch_rsi_kd_appended", lambda _s, _p: (20.0 - 4e-13, 3.0),
    )
    monkeypatch.setattr(lp.OracleFrame, "kd_canonical", canon)
    assert frame.kd(50.0) == (20.0, 3.0)
    assert calls["n"] == 1
    assert lp._c1_margin(frame, 50.0) == 0.0


@pytest.mark.parametrize(
    "fast_tuple",
    [
        (5.0 + 1e-6, 5.0),
        (20.0 - 1e-6, 3.0),
        (55.0, 40.0),
        (None, None),
        (7.0, None),
    ],
)
def test_kd_outside_the_band_stays_on_the_fast_path(
    monkeypatch: pytest.MonkeyPatch, fast_tuple: tuple,
) -> None:
    frame = _fast_frame_for_kd_tests(monkeypatch)
    monkeypatch.setattr(ic, "stoch_rsi_kd_appended", lambda _s, _p: fast_tuple)

    def boom(_self: lp.OracleFrame, _price: float) -> tuple[float | None, float | None]:
        raise AssertionError("canonical must not run outside the tie band")

    monkeypatch.setattr(lp.OracleFrame, "kd_canonical", boom)
    assert frame.kd(50.0) == fast_tuple


@pytest.mark.parametrize(
    "delta,use_canonical",
    [
        (1e-9 * 0.5, True),
        (1e-9 * 4, False),
    ],
)
def test_band_edges(
    monkeypatch: pytest.MonkeyPatch, delta: float, use_canonical: bool,
) -> None:
    d = 5.0
    fast_k = d + delta
    assert (abs(fast_k - d) <= lp.ORACLE_TIE_BAND) is use_canonical
    frame = _fast_frame_for_kd_tests(monkeypatch)
    canon_calls = {"n": 0}

    def canon(_self: lp.OracleFrame, _price: float) -> tuple[float, float]:
        canon_calls["n"] += 1
        return (d, d)

    monkeypatch.setattr(ic, "stoch_rsi_kd_appended", lambda _s, _p: (fast_k, d))
    monkeypatch.setattr(lp.OracleFrame, "kd_canonical", canon)
    result = frame.kd(50.0)
    if use_canonical:
        assert result == (d, d)
        assert canon_calls["n"] == 1
    else:
        assert result == (fast_k, d)
        assert canon_calls["n"] == 0


def test_oracle_tie_band_is_one_billionth() -> None:
    assert lp.ORACLE_TIE_BAND == 1e-9
