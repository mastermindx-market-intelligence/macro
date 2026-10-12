"""Invariants of the frozen T12 evaluation contract against incumbent functions.

Fixtures and a temp ledger only. This module does not read or write ``data/``.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from engine import alt_cycle, trial_ledger
from engine import btc_impulse_radar_backtest as impulse
from scripts import build_crypto

FAMILY = "crypto_class_rotation_t12"
DECLARED_BUDGET = 24
DECLARED_REASON = (
    "T12 class-rotation floor itemized in "
    "CRYPTO_T12_EVALUATION_CONTRACT_2026-10-12.md §9"
)
_DRIFT = (
    "drifted from CRYPTO_T12_EVALUATION_CONTRACT_2026-10-12.md §2; "
    "re-register the trial under §3 before any outcome is read"
)
_ALT_CFG = {
    "btc_season_line": 0.05,
    "alt_season_line": 0.07,
    "ethbtc_ma_d": 350,
    "slope_window_d": 56,
    "pctile_lookback_d": 1095,
}
_SEASON_BUCKET = {"btc": "BTC season", "mixed": "Mixed", "alt": "Alt season"}
_AS_OF = "2026-07-29"


def _require_frozen(name: str, got, want) -> None:
    assert got == want, f"{name}={got!r} contract={want!r} {_DRIFT}"


def _decision(exposure: int) -> dict:
    return {
        "schema": "btc.decision/v1",
        "status": "ok",
        "as_of": _AS_OF,
        "integrity_ok": True,
        "final_exposure_pct": exposure,
        "errors": [],
    }


def _signals() -> pd.DataFrame:
    index = pd.to_datetime(["2026-07-28", _AS_OF])
    return pd.DataFrame({"close": [100.0, 110.0]}, index=index)


def _install_split_fakes(monkeypatch, regime: str, bucket: str, calls: dict) -> None:
    """Keep ``_allocation`` off ``data/`` while the real ``alloc_grid`` still runs."""
    monkeypatch.setattr(
        build_crypto.config, "load", lambda: {"vector": {"alt_cycle": {}}}
    )
    monkeypatch.setattr(build_crypto.store, "read", lambda group, name: None)
    monkeypatch.setattr(build_crypto, "_series", lambda *args, **kwargs: pd.Series(dtype=float))
    monkeypatch.setattr(
        build_crypto.btc_mtf,
        "mtf_ladder",
        lambda close, high, regime=regime: {"ladder": {"regime": regime}},
    )
    monkeypatch.setattr(
        build_crypto.alt_cycle,
        "ethbtc_signal",
        lambda eth, close, cfg: {"level": 0.05},
    )
    monkeypatch.setattr(
        build_crypto.alt_cycle,
        "alt_season_score",
        lambda ethbtc, dominance, cfg, bucket=bucket: (50, bucket),
    )
    real = alt_cycle.alloc_grid

    def _wrapped(regime_arg, bucket_arg, real=real):
        calls["n"] += 1
        grid = real(regime_arg, bucket_arg)
        calls["grid"] = grid
        return grid

    monkeypatch.setattr(build_crypto.alt_cycle, "alloc_grid", _wrapped)


def _cash_dropped_legs(budget: int, weights: tuple[int, int, int]) -> tuple[int, int, int]:
    """§3 formula: cash column excluded, residual assigned to alts."""
    w_btc, w_eth, w_alts = weights
    risk = w_btc + w_eth + w_alts
    btc_pct = round(budget * w_btc / risk)
    eth_pct = round(budget * w_eth / risk)
    return btc_pct, eth_pct, budget - btc_pct - eth_pct


def _inadmissible(legs: tuple[int, int, int], weights: tuple[int, int, int]) -> bool:
    """``build_crypto.py`` withholds a negative leg or a positive on a zero weight."""
    return any(v < 0 or (w == 0 and v > 0) for v, w in zip(legs, weights))


def test_class_split_renormalizes_onto_budget_and_drops_grid_cash(monkeypatch):
    """§3: every emitted BTC/ETH/alts split sums to the budget and ignores grid cash."""
    signals = _signals()
    emitted = 0
    refused = 0
    witnessed_cash_drop = False
    for regime, seasons in alt_cycle.ALLOC_GRID.items():
        for season_key, cell in seasons.items():
            bucket = _SEASON_BUCKET[season_key]
            calls = {"n": 0, "grid": None}
            _install_split_fakes(monkeypatch, regime, bucket, calls)
            w_btc, w_eth, w_alts, w_cash = cell
            assert w_cash > 0
            weights = (w_btc, w_eth, w_alts)
            for budget in range(0, 101):
                before = calls["n"]
                out = build_crypto._allocation(signals, {}, _decision(budget))
                assert out["exposure"] == budget
                assert out["cash"] == 100 - budget
                for leg in ("btc", "eth", "alts"):
                    assert out[leg] is None or out[leg] >= 0, (regime, season_key, budget, out)
                if budget == 0:
                    assert calls["n"] == before
                    assert out["available"] is True
                    assert (out["btc"], out["eth"], out["alts"]) == (0, 0, 0)
                    assert out["btc"] + out["eth"] + out["alts"] == 0
                    continue
                assert calls["n"] == before + 1
                grid = calls["grid"]
                assert grid["regime_key"] == regime
                assert grid["season_key"] == season_key
                assert grid["cash"] == w_cash
                assert [grid[k] for k in ("btc", "eth", "alts")] == list(weights)
                legs = _cash_dropped_legs(budget, weights)
                if _inadmissible(legs, weights):
                    refused += 1
                    assert out["available"] is False
                    assert out["authority_error"] == "CLASS_SPLIT_UNAVAILABLE"
                    assert (out["btc"], out["eth"], out["alts"]) == (None, None, None)
                    continue
                emitted += 1
                assert out["available"] is True
                assert (out["btc"], out["eth"], out["alts"]) == legs
                assert out["btc"] + out["eth"] + out["alts"] == budget
                assert out["regime"] == regime
                assert out["season"] == bucket
                incl = w_btc + w_eth + w_alts + w_cash
                kept = (
                    round(budget * w_btc / incl),
                    round(budget * w_eth / incl),
                    budget - round(budget * w_btc / incl) - round(budget * w_eth / incl),
                )
                if kept != legs:
                    witnessed_cash_drop = True
                    assert (out["btc"], out["eth"], out["alts"]) != kept
    assert emitted > 0
    assert witnessed_cash_drop
    bear_btc = _signals()
    calls = {"n": 0, "grid": None}
    _install_split_fakes(monkeypatch, "bear", "BTC season", calls)
    witness = build_crypto._allocation(bear_btc, {}, _decision(60))
    assert calls["grid"]["cash"] == 70
    assert witness["cash"] == 40
    assert (witness["btc"], witness["eth"], witness["alts"]) == (50, 10, 0)
    assert witness["btc"] + witness["eth"] + witness["alts"] == 60
    assert refused > 0


def test_impulse_constants_match_t12_section_2():
    """§2 act-leg block. A drift names the contract section that must be re-registered."""
    _require_frozen("HOLDOUT_START", impulse.HOLDOUT_START, "2024-01-01")
    _require_frozen("LABEL_H", impulse.LABEL_H, 3)
    _require_frozen("LABEL_THR", impulse.LABEL_THR, 0.05)
    _require_frozen("MIN_HOLDOUT_N", impulse.MIN_HOLDOUT_N, 30)
    _require_frozen("PERM_N", impulse.PERM_N, 2000)
    _require_frozen("P_MAX", impulse.P_MAX, 0.05)
    _require_frozen("LEGS keys", set(impulse.LEGS), {"d2", "d3", "u1"})
    _require_frozen("d2 floor", impulse.LEGS["d2"]["floor"], 1.5)
    _require_frozen("d3 floor", impulse.LEGS["d3"]["floor"], 1.3)
    _require_frozen("u1 floor", impulse.LEGS["u1"]["floor"], 1.3)
    _require_frozen("d2 dir", impulse.LEGS["d2"]["dir"], "down")
    _require_frozen("d3 dir", impulse.LEGS["d3"]["dir"], "down")
    _require_frozen("u1 dir", impulse.LEGS["u1"]["dir"], "up")


def test_t12_declared_budget_is_counted_and_effective_n_never_falls_below_it(
    tmp_path, monkeypatch
):
    """§9: family floor 24 is counted, and effective_n never drops below it."""
    monkeypatch.setattr(trial_ledger, "DEFAULT_PATH", tmp_path / "not-the-canonical.jsonl")
    blind = trial_ledger.TrialLedger()
    assert blind.path == tmp_path / "not-the-canonical.jsonl"
    ledger_path = tmp_path / "t12.jsonl"
    led = trial_ledger.TrialLedger(path=ledger_path, family=FAMILY)
    assert led.path == ledger_path
    assert "data" not in ledger_path.parts

    assert led.log_declared_budget(
        DECLARED_BUDGET, family=FAMILY, reason=DECLARED_REASON
    ) is True
    assert led.declared_budget(FAMILY) == DECLARED_BUDGET
    assert led.literal_n(FAMILY) == 0
    assert led.effective_n(FAMILY) == DECLARED_BUDGET
    assert led.log_declared_budget(
        DECLARED_BUDGET, family=FAMILY, reason=DECLARED_REASON
    ) is False
    assert led.effective_n(FAMILY) == DECLARED_BUDGET

    assert led.log_trial({"cell": "one"}, family=FAMILY) is True
    assert led.literal_n(FAMILY) == 1
    assert led.effective_n(FAMILY) == DECLARED_BUDGET

    added = led.log_grid([{"cell": i} for i in range(30)], family=FAMILY)
    assert added == 30
    assert led.literal_n(FAMILY) == 31
    assert led.effective_n(FAMILY) == 31
    assert led.effective_n(FAMILY) >= DECLARED_BUDGET

    led.log_declared_budget(10, family=FAMILY, reason="smaller declaration cannot lower N")
    assert led.declared_budget(FAMILY) == DECLARED_BUDGET
    assert led.effective_n(FAMILY) == 31
    assert led.effective_n(FAMILY, correlation_credit=0.01) >= DECLARED_BUDGET

    reloaded = trial_ledger.TrialLedger(path=ledger_path)
    assert reloaded.declared_budget(FAMILY) == DECLARED_BUDGET
    assert reloaded.effective_n(FAMILY) == 31
    assert reloaded.effective_n(FAMILY) >= reloaded.declared_budget(FAMILY)
    text = ledger_path.read_text(encoding="utf-8")
    assert FAMILY in text
    assert '"n": 24' in text
    assert not Path("data/trial_ledger.jsonl").exists()


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    raise TypeError(type(value))


def _honest_n_episodes(eligible_as_of, *, gap_calendar_days: int = 90) -> dict:
    """SPEC OF RECORD, no engine owner yet.

    Missing signature: ``honest_n_episodes(eligible_as_of: Sequence[date], *,
    gap_calendar_days: int = 90) -> dict`` with keys ``episode_as_of``,
    ``n_episodes``, ``n_clock``.
    """
    rows = [_as_date(value) for value in eligible_as_of]
    episodes: list[date] = []
    for day in sorted(rows):
        if not episodes or (day - episodes[-1]).days >= gap_calendar_days:
            episodes.append(day)
    return {
        "episode_as_of": episodes,
        "n_episodes": len(episodes),
        "n_clock": len(rows),
    }


def test_honest_n_is_distinct_nonoverlapping_90_calendar_day_episodes():
    """SPEC OF RECORD, no engine owner yet."""
    assert _honest_n_episodes([]) == {
        "episode_as_of": [],
        "n_episodes": 0,
        "n_clock": 0,
    }
    single = date(2026, 10, 13)
    one = _honest_n_episodes([single])
    assert one["n_episodes"] == 1 and one["n_clock"] == 1
    assert one["episode_as_of"] == [single]

    start = date(2026, 6, 1)
    selloff = [start + timedelta(days=i) for i in range(40)]
    collapsed = _honest_n_episodes(selloff)
    assert collapsed["n_clock"] == 40
    assert collapsed["n_episodes"] == 1
    assert collapsed["episode_as_of"] == [start]
    assert collapsed["n_episodes"] != collapsed["n_clock"]

    leap_gap = [date(2024, 1, 1), date(2024, 3, 31)]
    assert (leap_gap[1] - leap_gap[0]).days == 90
    leap = _honest_n_episodes(leap_gap)
    assert leap["n_episodes"] == 2
    assert leap["episode_as_of"] == leap_gap

    short_gap = [date(2026, 1, 1), date(2026, 3, 31)]
    assert (short_gap[1] - short_gap[0]).days == 89
    held = _honest_n_episodes(short_gap)
    assert held["n_clock"] == 2
    assert held["n_episodes"] == 1
    assert held["episode_as_of"] == [date(2026, 1, 1)]

    exact = [date(2026, 1, 1), date(2026, 4, 1)]
    assert (exact[1] - exact[0]).days == 90
    assert _honest_n_episodes(exact)["episode_as_of"] == exact

    origin = date(2026, 1, 1)
    second = origin + timedelta(days=90)
    interior = second + timedelta(days=89)
    third = second + timedelta(days=90)
    mixed = _honest_n_episodes([interior, origin, third, second, origin])
    assert mixed["n_clock"] == 5
    assert mixed["n_episodes"] == 3
    assert mixed["episode_as_of"] == [origin, second, third]
    assert all(
        (mixed["episode_as_of"][i] - mixed["episode_as_of"][i - 1]).days >= 90
        for i in range(1, 3)
    )

    early = origin + timedelta(days=90)
    later = origin + timedelta(days=120)
    greedy = _honest_n_episodes([later, origin, early])
    assert greedy["episode_as_of"] == [origin, early]
    assert greedy["n_clock"] == 3
    assert greedy["n_episodes"] == 2
    assert later not in greedy["episode_as_of"]


def _stale_eth_pair(gap_bars: int):
    idx = pd.date_range("2024-01-01", periods=200, freq="D")
    btc = pd.Series(100.0, index=idx)
    btc.iloc[-1] = 250.0
    eth = pd.Series(5.0, index=idx[:-gap_bars])
    return eth, btc, idx


def test_ethbtc_forward_fill_has_no_age_cap():
    """§3 current behavior: ETH is forward-filled onto the BTC index with no age cap."""
    eth, btc, idx = _stale_eth_pair(40)
    last_real = eth.index[-1]
    age_bars = int(idx.get_loc(idx[-1]) - idx.get_loc(last_real))
    assert age_bars == 40
    out = alt_cycle.ethbtc_signal(eth, btc, _ALT_CFG)
    assert out["ratio"].index[-1] == idx[-1]
    assert out["ratio"].loc[last_real] == pytest.approx(5.0 / 100.0)
    assert out["level"] == pytest.approx(5.0 / 250.0)
    assert out["ratio"].iloc[-1] == pytest.approx(out["level"])


@pytest.mark.xfail(
    strict=True,
    reason="T12 §3 age mask is harness protocol, not engine behavior",
)
def test_eth_one_bar_age_mask_is_not_engine_behavior():
    """§3 mask: last real ETH close more than one daily bar before t is unavailable."""
    eth, btc, idx = _stale_eth_pair(40)
    age_bars = int(idx.get_loc(idx[-1]) - idx.get_loc(eth.index[-1]))
    assert age_bars > 1
    out = alt_cycle.ethbtc_signal(eth, btc, _ALT_CFG)
    assert out.get("level") is None
