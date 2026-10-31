"""Pure-function tests for the physical-balance context leaf (no network).

Covers the seasonal-anomaly z (the calendar-confound fix), days-of-supply, the
composite balance gauge, and — critically — the invariant that this display leaf is
never wired into the commodity scoring path.
"""
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import commodity_supply_context as sc  # noqa: E402


def _seasonal_weekly(years=7, amp=50.0, base=1000.0, noise_sd=4.0, seed=0):
    """A weekly series with a strong 52-week seasonal cycle + idiosyncratic noise."""
    idx = pd.date_range("2017-01-08", periods=years * 52, freq="W-SUN")
    week = idx.isocalendar().week.to_numpy().astype(float)
    season = amp * np.sin(2 * np.pi * week / 52.0)
    rng = np.random.default_rng(seed)
    return pd.Series(base + season + rng.normal(0, noise_sd, len(idx)), index=idx)


def _at_trough(s):
    """Slice the series to end at the deepest seasonal trough within the last year."""
    season_like = s.rolling(5, center=True, min_periods=1).mean()   # smooth out noise
    asof = season_like.iloc[-52:].idxmin()
    return s.loc[:asof].copy()


def test_seasonal_z_beats_raw_at_a_seasonal_extreme():
    """The whole point: a value sitting ON its seasonal norm at a seasonal LOW reads
    deeply negative on a RAW z (calendar artifact) but ~flat on the seasonal z."""
    s = _at_trough(_seasonal_weekly())
    w = int(s.index[-1].isocalendar().week)
    same_week = s[s.index.isocalendar().week.to_numpy() == w]
    s.iloc[-1] = float(same_week.iloc[:-1].mean())          # force latest onto its week-norm

    raw_z = (s.iloc[-1] - s.mean()) / s.std()
    seas_z = sc.seasonal_z(s)
    assert seas_z is not None
    assert raw_z < -1.0                                      # raw is fooled by the season
    assert abs(seas_z) + 0.5 < abs(raw_z)                   # seasonal anomaly is materially flatter


def test_seasonal_z_flags_a_genuine_draw():
    """A true below-season draw (4σ under the week-norm) reads strongly negative."""
    s = _at_trough(_seasonal_weekly())
    w = int(s.index[-1].isocalendar().week)
    same_week = s[s.index.isocalendar().week.to_numpy() == w]
    s.iloc[-1] = float(same_week.iloc[:-1].mean()) - 4 * 4.0   # 4 * noise_sd below norm
    z = sc.seasonal_z(s)
    assert z is not None and z < -2.5                          # tight


def test_seasonal_z_guards():
    assert sc.seasonal_z(None) is None
    assert sc.seasonal_z(_seasonal_weekly(years=1)) is None        # < 104 weeks
    flat = pd.Series(500.0, index=pd.date_range("2019-01-06", periods=300, freq="W-SUN"))
    assert sc.seasonal_z(flat) is None                              # zero dispersion
    # inf/nan are cleaned, not crashed on
    s = _seasonal_weekly()
    s.iloc[-3:] = [np.inf, np.nan, s.iloc[-1]]
    assert sc.seasonal_z(s) is not None


def test_last_value_is_nan_safe():
    s = pd.Series([1.0, 2.0, np.nan], index=pd.date_range("2020-01-05", periods=3, freq="W"))
    assert sc.last_value(s) == 2.0                                  # trailing NaN dropped
    assert sc.last_value(None) is None
    assert sc.last_value(pd.Series([np.nan, np.nan])) is None


def test_delta_4w():
    idx = pd.date_range("2020-01-05", periods=6, freq="W")
    s = pd.Series([100, 101, 102, 103, 104, 110], index=idx, dtype=float)
    assert sc.delta_4w(s) == 110 - 101                             # latest minus value ~4 weeks (4 intervals) back
    assert sc.delta_4w(None) is None


def test_days_of_supply():
    idx = pd.date_range("2020-01-05", periods=8, freq="W")
    stocks = pd.Series(280_000.0, index=idx)                       # kbbl
    demand = pd.Series(16_000.0, index=idx)                        # kbbl/d
    assert sc.days_of_supply(stocks, demand) == 17.5              # 280000 / 16000
    assert sc.days_of_supply(stocks, None) is None
    assert sc.days_of_supply(stocks, pd.Series(0.0, index=idx)) is None   # non-positive demand


def test_balance_z_and_word():
    assert sc.balance_z({"a": -1.0, "b": -2.0, "c": None}) == -1.5    # None skipped
    assert sc.balance_z({"a": None}) is None
    assert sc.balance_word(-0.8) == "tight"
    assert sc.balance_word(0.9) == "ample"
    assert sc.balance_word(0.1) == "balanced"
    assert sc.balance_word(None) == "n/a"


def test_caveat_is_bilingual_and_non_directional():
    for k in ("en", "zh"):
        assert k in sc.SUPPLY_CAVEAT and len(sc.SUPPLY_CAVEAT[k]) > 20
    assert "≠" in sc.SUPPLY_CAVEAT["en"]                            # balance ≠ direction


def test_leaf_is_never_wired_into_the_scoring_path():
    """Guardrail: physical balance is DISPLAY-ONLY. The commodity scoring/alert modules
    must not import or reference this leaf, and the leaf must not import them."""
    from engine import (commodity_conviction, commodity_alerts,
                         commodity_signals, commodity_mtf)
    for mod in (commodity_conviction, commodity_alerts, commodity_signals, commodity_mtf):
        src = inspect.getsource(mod)
        assert "commodity_supply_context" not in src, f"{mod.__name__} references the display leaf"
    # the leaf must not IMPORT the scoring path (docstrings may mention it for context)
    import_lines = "\n".join(ln for ln in inspect.getsource(sc).splitlines()
                             if ln.strip().startswith(("import ", "from ")))
    for forbidden in ("conviction", "commodity_alerts", "commodity_signals", "commodity_mtf"):
        assert forbidden not in import_lines, f"leaf must not import the scoring path ({forbidden})"


def test_four_week_change_requires_calendar_endpoints_not_row_count():
    idx = pd.date_range("2026-08-07", periods=6, freq="7D")
    values = pd.Series([100, 101, 102, 103, 104, 110], index=idx)
    assert sc.delta_4w(values.tail(2)) is None
    assert sc.delta_4w(values.drop(idx[-5])) is None
    # Intermediate weeks are not needed for a stock endpoint difference.
    assert sc.delta_4w(values.loc[[idx[-5], idx[-1]]]) == 9
    duplicate = pd.concat([values, pd.Series([999], index=[idx[-1]])])
    assert sc.delta_4w(duplicate) is None
    assert sc.delta_4w(pd.concat([values, values.tail(1)])) == 9


def test_cover_requires_all_aligned_weeks_and_excludes_future_demand():
    idx = pd.date_range("2026-08-07", periods=8, freq="7D")
    stocks = pd.Series(280_000.0, index=idx)
    demand = pd.Series(16_000.0, index=idx)
    assert sc.days_of_supply(stocks, demand.iloc[:-1]) is None
    assert sc.days_of_supply(stocks, demand.tail(3)) is None
    assert sc.days_of_supply(stocks, demand.drop(idx[-2])) is None
    future = pd.concat([demand, pd.Series([80_000.0], index=[idx[-1] + pd.Timedelta(weeks=1)])])
    assert sc.days_of_supply(stocks, future) == 17.5
    assert sc.days_of_supply(stocks, demand, weeks=0) is None
    assert sc.days_of_supply(stocks, demand, weeks=True) is None
    demand.iloc[-2] = -1
    assert sc.days_of_supply(stocks, demand) is None


def test_seasonal_reference_discloses_actual_history_instead_of_fixed_five_year_claim():
    s = _seasonal_weekly(years=2)
    ref = sc.seasonal_reference(s)
    assert ref["observations"] == 104
    assert ref["start"] == s.index[0].date().isoformat()
    assert ref["end"] == s.index[-1].date().isoformat()
    assert ref["latest_included"] is True
    assert sc.seasonal_z(s) is not None
    short = sc.build_physical_context({"crude_stocks": s}, as_of=ref["end"])
    assert short["evidence"]["crude_z"]["reference"] == ref
    assert short["point_in_time_verified"] is False
    assert short["release_at"] is None


def test_context_filters_observation_periods_without_claiming_release_vintage():
    s = _seasonal_weekly()
    cutoff = s.index[-2].date().isoformat()
    s.iloc[-1] = 1_000_000
    context = sc.build_physical_context({"crude_stocks": s}, as_of=cutoff)
    assert context["crude_stocks_mb"] == round(s.iloc[-2] / 1000, 1)
    assert context["sources"]["crude_stocks"]["input_latest_observation"] > cutoff
    assert context["sources"]["crude_stocks"]["observation_at"] == cutoff
    assert all(r["observation_at"] <= cutoff for r in context["evidence"].values() if r["observation_at"])
    assert context["hypothesis_confirmation_eligible"] is False
    assert context["observation_filter_only"] is True


def test_context_preserves_missing_demand_and_each_stock_date():
    s = _seasonal_weekly()
    context = sc.build_physical_context({
        "crude_stocks": s, "gasoline_stocks": s.iloc[:-1],
        "refinery_inputs": pd.Series(10.0, index=s.index[:-1]),
    }, as_of=s.index[-1].date().isoformat())
    assert "days_supply" not in context
    assert context["evidence"]["days_supply"]["state"] == "aligned_demand_weeks_missing"
    assert context["evidence"]["gasoline_z"]["observation_at"] != context["asof"]
    assert context["balance_z"] == round(sc.seasonal_z(s), 2)
    assert context["evidence"]["crude_chg_4w_mb"]["window_start"] == (s.index[-1] - pd.Timedelta(weeks=4)).date().isoformat()


def test_impossible_negative_stock_does_not_become_a_tightness_claim():
    s = _seasonal_weekly()
    s.iloc[-1] = -1
    context = sc.build_physical_context({"crude_stocks": s}, as_of=s.index[-1].date().isoformat())
    assert "crude_stocks_mb" not in context
    assert context["evidence"]["crude_z"]["value"] is None
    assert context["sources"]["crude_stocks"]["state"] == "invalid_negative_stock"


def test_builder_reader_and_pure_owner_have_identical_context(monkeypatch):
    from scripts import build_commodities
    from lib import store

    raw = {name: _seasonal_weekly() for name in sc.SERIES}
    monkeypatch.setattr(store, "read", lambda group, name: raw[name].to_frame(name))
    monkeypatch.setattr(build_commodities.config, "load",
                        lambda: {"eia": {"supply": {"seasonal_years": 5, "dos_window_weeks": 4}}})
    cutoff = raw["crude_stocks"].index[-1].date().isoformat()
    expected = sc.build_physical_context(raw, as_of=cutoff)
    assert build_commodities._oil_supply_read(cutoff) == expected
    assert build_commodities._oil_supply_read() == expected
