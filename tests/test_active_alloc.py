"""Unit guards for engine.active_alloc — the leverage-aware active-allocation engine.

Pure-math checks on synthetic series so they run with no data cache: leverage/financing
accounting, vol-targeting caps, the scorecard contract (keys the detail template needs),
the multi-asset portfolio book, and the split-half OOS panel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import active_alloc as aa


def _ramp(n=600, drift=0.0004, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-01", periods=n)
    ret = rng.normal(drift, 0.012, n)
    return pd.Series(100 * np.cumprod(1 + ret), index=idx)


def test_backtest_lev_financing_and_scorecard():
    px = _ramp(drift=0.0010)                            # clean uptrend so 2x reliably out-earns 1x
    bill = pd.Series(4.0, index=px.index)              # 4% cash/borrow base
    # full 2x leverage the whole time -> ~2x the asset return minus financing on the 1x borrow
    size = pd.Series(2.0, index=px.index)
    r = aa.backtest_lev(px, size, bill, cost_bps=0.0, borrow_spread=1.0)
    assert set(["cagr", "hodl_cagr", "sharpe", "hodl_sharpe", "maxdd", "hodl_maxdd",
                "sortino", "time_in_market", "turnover_annual", "avg_leverage",
                "max_leverage", "years"]).issubset(r)
    assert abs(r["avg_leverage"] - 2.0) < 0.01 and abs(r["max_leverage"] - 2.0) < 1e-6  # day-1 ramps from 0
    # levered book is ~2x the asset's excess path: its CAGR exceeds buy-&-hold in an uptrend
    assert r["cagr"] > r["hodl_cagr"]
    # a flat (cash) book earns ~the bill, never the asset
    flat = aa.backtest_lev(px, pd.Series(0.0, index=px.index), bill)
    assert flat["time_in_market"] == 0.0 and 2.5 < flat["cagr"] < 4.5


def test_vol_target_size_caps_and_scales():
    px = _ramp()
    conv = pd.Series(1.0, index=px.index)               # full bullish conviction
    size = aa.vol_target_size(conv, px, target_vol=0.15, max_lev=2.0)
    assert size.dropna().max() <= 2.0 + 1e-9 and size.dropna().min() >= 0.0
    # higher target vol -> larger average position
    hi = aa.vol_target_size(conv, px, target_vol=0.30, max_lev=3.0)
    assert hi.dropna().mean() >= size.dropna().mean()


def test_blend_renormalizes_missing_legs():
    idx = pd.bdate_range("2015-01-01", periods=300)
    a = pd.Series(1.0, index=idx)
    b = pd.Series(-1.0, index=idx); b.iloc[:150] = np.nan      # warms up halfway
    out = aa.blend({"a": (a, 1.0), "b": (b, 1.0)}, idx)
    assert abs(out.iloc[0] - 1.0) < 1e-9                       # only 'a' active early
    assert abs(out.iloc[-1] - 0.0) < 1e-9                      # +1 and -1 cancel later
    assert out.between(-1, 1).all()


def test_backtest_portfolio_levers_and_scores():
    idx = pd.bdate_range("2015-01-01", periods=600)
    rng = np.random.default_rng(3)
    closes = pd.DataFrame({
        "SPY": 100 * np.cumprod(1 + rng.normal(0.0004, 0.011, 600)),
        "IEF": 100 * np.cumprod(1 + rng.normal(0.0001, 0.004, 600)),
    }, index=idx)
    bill = pd.Series(3.0, index=idx)
    w = pd.DataFrame({"SPY": 0.6, "IEF": 0.6}, index=idx)      # 1.2x gross
    p = aa.backtest_portfolio(w, closes, bill, cost_bps=0.0)
    assert abs(p["gross_lev"].mean() - 1.2) < 0.01            # day-1 ramps from 0
    assert "cagr" in p and "sharpe" in p and "net" in p
    # diversified levered book has a higher Sharpe than the equity sleeve alone here
    assert p["sharpe"] >= p["hodl_sharpe"] - 0.05


def test_split_half_oos_flags_non_robust():
    idx = pd.bdate_range("2010-01-01", periods=1000)
    # net beats hodl in the first half, loses in the second -> robust must be False
    net = pd.Series(np.r_[np.full(500, 0.0010), np.full(500, -0.0002)], index=idx)
    hodl = pd.Series(np.r_[np.full(500, 0.0005), np.full(500, 0.0006)], index=idx)
    oos = aa.split_half_oos(net, hodl)
    assert oos["first"]["beats_cagr"] is True and oos["second"]["beats_cagr"] is False
    assert oos["robust"] is False


@pytest.fixture
def gtaa_io(monkeypatch):
    """Only replace external data; conviction, sizing and return accounting stay native."""
    from engine import masterminds as mm, inputs

    def absent_macro():
        raise RuntimeError("synthetic fixture has no macro observations")

    monkeypatch.setattr(mm.store, "read", lambda *a, **kw: None)
    monkeypatch.setattr(inputs, "build_features", absent_macro)
    monkeypatch.setattr(mm.ea, "bill_yield", lambda: pd.Series(
        0.0, index=pd.bdate_range("2015-01-01", periods=800)))
    return mm


def _gtaa_prices(mm, winners=1, rows=800):
    idx = pd.bdate_range("2015-01-01", periods=rows)
    wiggle = 0.00005 * np.sin(np.arange(len(idx)) / 7)
    return pd.DataFrame({a: 100 * np.cumprod(
        1 + (0.001 if i < winners else -0.001) + wiggle)
        for i, a in enumerate(mm.ASSETS)}, index=idx)


@pytest.mark.parametrize("profile", ["conservative", "moderate", "aggressive"])
@pytest.mark.parametrize("winners", [1, 2, 9])
def test_gtaa_final_name_caps_and_diversified_control(gtaa_io, profile, winners):
    mm = gtaa_io
    p = _gtaa_prices(mm, winners)
    prof = mm.PROFILES[profile]
    result = mm.backtest(profile, p)
    w = result["weights"]
    assert np.isfinite(w.to_numpy()).all()
    assert w.min().min() >= 0
    assert w.max().max() <= prof["w_cap"] + 1e-12
    assert w.sum(axis=1).max() <= prof["max_lev"] + 1e-12
    # One/two trends hit the FINAL name limit; the nine-trend control still
    # reaches its unchanged gross limit without being concentrated into a name.
    expected = min(prof["w_cap"], prof["max_lev"] / winners)
    np.testing.assert_allclose(w.iloc[-1, :winners], expected, atol=1e-12)
    assert w.iloc[-1, winners:].eq(0).all()
    assert w.loc[w.index < w.index[0] + pd.Timedelta(days=300)].eq(0).all().all()
    changed = w.diff().fillna(0).abs().sum(axis=1).to_numpy() > 1e-12
    assert not changed[np.arange(len(w)) % mm._REBAL != 0].any()
    assert result["gross_now"] == round(winners * expected, 2)
    assert all(a["weight"] <= 100 * prof["w_cap"] for a in result["alloc"])
    assert {"first", "second", "robust"} <= result["oos"].keys()
    for key in ("cagr", "sharpe", "maxdd", "avg_leverage"):
        assert np.isfinite(result["scorecard"][key])


@pytest.mark.parametrize("profile", ["conservative", "moderate", "aggressive"])
def test_gtaa_zero_conviction_and_missing_assets(gtaa_io, monkeypatch, profile):
    mm = gtaa_io
    p = _gtaa_prices(mm, 9).drop(columns=["QQQ"])
    p["BTC-USD"] = np.nan
    p.loc[p.index[:650], "HG=F"] = np.nan
    w = mm._weights(p, mm.PROFILES[profile])
    assert np.isfinite(w.to_numpy()).all()
    assert "QQQ" not in w
    assert w[["BTC-USD", "HG=F"]].eq(0).all().all()
    assert w.max().max() <= mm.PROFILES[profile]["w_cap"] + 1e-12
    monkeypatch.setattr(mm, "_conviction", lambda frame: frame * 0)
    assert mm._weights(p, mm.PROFILES[profile]).eq(0).all().all()


@pytest.mark.parametrize("profile", ["conservative", "moderate", "aggressive"])
def test_gtaa_changing_signal_keeps_weekly_and_next_bar_contract(gtaa_io, monkeypatch, profile):
    mm = gtaa_io
    p = _gtaa_prices(mm, 1)
    conv = pd.DataFrame(0.0, index=p.index, columns=p.columns)
    conv.iloc[502:548, 0] = 1.0
    monkeypatch.setattr(mm, "_conviction", lambda frame: conv)
    result = mm.backtest(profile, p)
    cap = mm.PROFILES[profile]["w_cap"]
    w, sc = result["weights"], result["scorecard"]
    assert w.iloc[502:505].eq(0).all().all()
    assert w.iloc[505:550]["SPY"].eq(cap).all()
    assert w.iloc[550:].eq(0).all().all()
    # Signals first enter the held target at 505, earn returns at 506, and pay
    # the native 3-bp entry cost once; exit target550 applies at551.
    assert sc["net"].iloc[505] == 0
    first_return = p["SPY"].iloc[506] / p["SPY"].iloc[505] - 1
    assert sc["net"].iloc[506] == pytest.approx(cap * (first_return - 0.0003))
    assert sc["gross_lev"].iloc[550] == cap
    assert sc["net"].iloc[551] == pytest.approx(-cap * 0.0003)
    assert sc["gross_lev"].iloc[551] == 0


@pytest.mark.parametrize("profile", ["conservative", "moderate", "aggressive"])
@pytest.mark.parametrize("volatility", [0.0, 0.09])
def test_gtaa_flat_and_volatile_prices_keep_both_limits(gtaa_io, monkeypatch, profile, volatility):
    mm = gtaa_io
    p = _gtaa_prices(mm, 9)
    rng = np.random.default_rng(11003)
    p[:] = 100 * np.cumprod(1 + rng.uniform(-volatility, volatility, p.shape), axis=0)
    monkeypatch.setattr(mm, "_conviction", lambda frame: frame * 0 + 1)
    w = mm._weights(p, mm.PROFILES[profile])
    assert np.isfinite(w.to_numpy()).all()
    assert w.min().min() >= 0
    assert w.max().max() <= mm.PROFILES[profile]["w_cap"] + 1e-12
    assert w.sum(axis=1).max() <= mm.PROFILES[profile]["max_lev"] + 1e-12


def test_gtaa_native_builder_snapshot_and_bilingual_pages_agree(gtaa_io, monkeypatch, tmp_path):
    import json
    from pathlib import Path
    from bs4 import BeautifulSoup
    from lib import config
    from scripts import build_masterminds as builder

    mm = gtaa_io
    p = _gtaa_prices(mm, 1)
    monkeypatch.setattr(mm, "_prices", lambda: p)
    source_root = Path(__file__).resolve().parent.parent
    (tmp_path / "templates").symlink_to(source_root / "templates", target_is_directory=True)
    (tmp_path / "site").mkdir()
    # Resolve the real config before redirecting only the builder's output root.
    config.load()
    monkeypatch.setattr(config, "ROOT", tmp_path)
    builder.build()
    snap = json.loads((tmp_path / "data/regime/masterminds_latest.json").read_text())
    assert snap["schema"] == "masterminds.latest.v2" and snap["n"] == 3
    assert snap["asof"] == str(p.index[-1].date())
    for card in snap["cards"]:
        profile = card["key"].removeprefix("mm_")
        cap = mm.PROFILES[profile]["w_cap"]
        assert card["alloc"] == mm.backtest(profile, p)["alloc"]
        assert card["alloc"][0]["weight"] == pytest.approx(100 * cap)
        assert card["gross_now"] == cap
        page = (tmp_path / f"site/strategy_mm_{profile}.html").read_text()
        soup = BeautifulSoup(page, "html.parser")
        rows = soup.select(".allocrow")
        assert len(rows) == 1
        assert "SPY" in rows[0].get_text() and f"{100 * cap:.1f}%" in rows[0].get_text()
        assert "Per-name cap" in page and "单一上限" in page
        assert "Historical split comparison" in page and "历史分段比较" in page
        assert "out-of-sample-stable" not in page and "genuine risk-adjusted alpha" not in page
        assert "样本外稳定" not in page and "真实的风险调整阿尔法" not in page


def test_gtaa_quote_matches_corrected_native_report_without_promoting_overlay():
    import json
    from engine import signal_lab
    from pathlib import Path
    d = json.loads((Path(__file__).resolve().parents[1] / "reports/gtaa-final-cap-revalidation.json").read_text())
    m = d["moderate_diagnostics"]
    row = next(r for r in signal_lab.REGISTRY if r["name"].startswith("Mastermind GTAA (Moderate)"))
    trend = next(r for r in signal_lab.REGISTRY if r["name"].startswith("Cross-asset TSMOM — masterminds"))
    assert row["tier"] == "confirmer" and trend["tier"] == "scored"
    assert row["dsr"] == m["dsr"]["dsr"] and row["sharpe"] == round(m["strategy"]["sharpe"], 2)
    assert row["dsr_n_trials"] == m["effective_n"] and row["dsr_basis"] == "frozen-quote"
    assert m["cagr_both_halves"] is False
    losses = sum(f["delta_sharpe"] < 0 for f in m["incrementality"]["folds"])
    assert f"{losses}/5" in row["why"] and f"{losses}/5" in row["why_zh"]
    assert "revised-macro" in row["why"] and "修订宏观" in row["why_zh"]
    assert trend["dsr"] == 0.9952 and trend["sharpe"] is None
    assert "separate historical 60/40 + 30%" in trend["why"]
    assert "1.07" not in trend["why"] and "0.98 / 1.15" not in trend["why"]


@pytest.mark.parametrize("profile", ["conservative", "moderate", "aggressive"])
def test_gtaa_cap_does_not_redistribute_released_exposure(gtaa_io, monkeypatch, profile):
    mm = gtaa_io
    idx = pd.bdate_range("2018-01-02", periods=800)
    prices = pd.DataFrame({asset: 100 * np.exp((.001 if i == 0 else -.001) * np.arange(800))
                           for i, asset in enumerate(mm.ASSETS)}, index=idx)
    prof = mm.PROFILES[profile]
    conviction = pd.DataFrame(0.0, index=idx, columns=prices.columns)
    conviction["SPY"], conviction["IEF"] = 1.0, prof["w_cap"] / 20
    monkeypatch.setattr(mm, "_conviction", lambda _prices: conviction)
    final = mm._weights(prices, prof).iloc[-1]
    assert final["SPY"] == pytest.approx(prof["w_cap"])
    assert final["IEF"] == pytest.approx(prof["w_cap"] / 2)
    assert final.sum() == pytest.approx(1.5 * prof["w_cap"])


@pytest.mark.parametrize("profile", ["conservative", "moderate", "aggressive"])
@pytest.mark.parametrize("winners", [0, 1, 9])
def test_gtaa_final_caps_preserve_native_cash_financing_and_emit(gtaa_io, monkeypatch, profile, winners):
    import json
    from scripts import build_masterminds as builder

    mm = gtaa_io
    prices = _gtaa_prices(mm, winners)
    monkeypatch.setattr(mm.ea, "bill_yield", lambda: pd.Series(4.0, index=prices.index))
    result = mm.backtest(profile, prices)
    weights, prof = result["weights"], mm.PROFILES[profile]
    gross = weights.shift(1).fillna(0).sum(axis=1)
    pd.testing.assert_series_equal(result["scorecard"]["gross_lev"], gross, check_names=False)
    final_gross = float(gross.iloc[-1])
    days = (prices.index[-1] - prices.index[-2]).days
    cash = (max(1 - final_gross, 0) * .04 - max(final_gross - 1, 0) * .05) * days / 365
    asset_return = float((weights.iloc[-2] * prices.pct_change(fill_method=None).iloc[-1]).sum())
    assert result["scorecard"]["net"].iloc[-1] == pytest.approx(asset_return + cash, abs=1e-12)
    assert weights.max().max() <= prof["w_cap"] + 1e-12
    assert weights.sum(axis=1).max() <= prof["max_lev"] + 1e-12
    if winners == 0:
        assert weights.eq(0).all().all() and result["alloc"] == []
    card = builder._rich_card(profile, result)
    snap = builder._snap([card], [result], "2026-11-11 00:00 UTC")
    published = json.loads(json.dumps(snap, allow_nan=False))["cards"][0]
    assert published["alloc"] == result["alloc"]
    assert published["gross_now"] == round(final_gross, 2)


def test_gtaa_late_history_keeps_its_own_calendar_warmup(gtaa_io):
    mm = gtaa_io
    prices = _gtaa_prices(mm, 9, rows=900)
    prices.loc[:prices.index[499], "BTC-USD"] = np.nan
    result = mm.backtest("moderate", prices)
    cutoff = prices["BTC-USD"].first_valid_index() + pd.Timedelta(days=300)
    assert result["weights"].loc[prices.index < cutoff, "BTC-USD"].eq(0).all()
    assert result["weights"]["BTC-USD"].iloc[-1] > 0
    assert result["weights"].max().max() <= .4 + 1e-12


def test_gtaa_missing_optional_asset_retains_cap_and_emit(gtaa_io):
    mm = gtaa_io
    prices = _gtaa_prices(mm, 1).drop(columns="BTC-USD")
    result = mm.backtest("moderate", prices)
    assert "BTC-USD" not in result["weights"]
    assert result["weights"]["SPY"].iloc[-1] == pytest.approx(.4)
    assert result["alloc"] == [{"asset": "SPY", "label_en": "S&P 500", "label_zh": "标普500", "weight": 40.0}]


def test_gtaa_changing_volatility_preserves_finite_final_limits(gtaa_io, monkeypatch):
    mm = gtaa_io
    prices = _gtaa_prices(mm, 1, rows=900)
    rng = np.random.default_rng(11003)
    moves = np.r_[np.repeat(.001, 500), rng.normal(.001, .035, 400)]
    prices["SPY"] = 100 * np.exp(np.cumsum(moves))
    conviction = prices * 0
    conviction["SPY"] = 1.0
    monkeypatch.setattr(mm, "_conviction", lambda _prices: conviction)
    weights = mm._weights(prices, mm.PROFILES["moderate"])
    assert np.isfinite(weights.to_numpy()).all() and weights.min().min() >= 0
    assert weights.max().max() <= .4 + 1e-12
    assert weights.sum(axis=1).max() <= 1.6 + 1e-12


def test_gtaa_phase0_uses_existing_trial_budget_without_writing(tmp_path, monkeypatch):
    from scripts import mastermind_moderate_phase0 as phase

    path = tmp_path / "trial_ledger.jsonl"
    raw = b'{"family":"mastermind_moderate_phase0","kind":"declared_budget","n":8,"config_hash":"budget-fixture"}\n'
    path.write_bytes(raw)
    native_ledger = phase.TrialLedger
    monkeypatch.setattr(phase, "TrialLedger", lambda _path: native_ledger(path))
    ledger = phase._trial_ledger()
    assert ledger.effective_n(phase.FAMILY) == 8 and ledger.literal_n(phase.FAMILY) == 0
    assert path.read_bytes() == raw


@pytest.mark.parametrize("state", ["absent", "different_family", "corrupt", "partial_corrupt", "under_budget", "invalid_utf8"])
def test_gtaa_phase0_does_not_qualify_from_incomplete_trial_evidence(tmp_path, monkeypatch, state):
    from scripts import mastermind_moderate_phase0 as phase

    path = tmp_path / "trial_ledger.jsonl"
    valid = b'{"family":"mastermind_moderate_phase0","kind":"declared_budget","n":8,"config_hash":"budget-fixture"}\n'
    raw = {"different_family": valid.replace(b"mastermind_moderate_phase0", b"other"),
           "corrupt": b'{invalid json}\n', "partial_corrupt": valid + b'{invalid json}\n',
           "under_budget": valid.replace(b'"n":8', b'"n":2'), "invalid_utf8": b'\xff\n'}
    if state != "absent":
        path.write_bytes(raw[state])
    before = path.read_bytes() if path.exists() else None
    native_ledger = phase.TrialLedger
    monkeypatch.setattr(phase, "TrialLedger", lambda _path: native_ledger(path))
    with pytest.raises(RuntimeError, match="GTAA"):
        phase._trial_ledger()
    assert (path.read_bytes() if path.exists() else None) == before
