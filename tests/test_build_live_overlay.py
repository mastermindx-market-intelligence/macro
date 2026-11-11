"""The intraday overlay build (scripts.build_live_overlay) + Mastermind emit v2.

The offline path is load-bearing: it must always emit a VALID overlay (NaN-safe,
every leg stale, falling back to baseline) with no network — now including the
market-context + per-region session blocks. Also pins the Mastermind emit v2
(alloc weights + asof in JSON).
"""
from __future__ import annotations

from datetime import datetime
import json

import numpy as np
import pandas as pd
import pytest


def test_gtaa_phase0_uses_existing_trial_budget_without_writing(tmp_path):
    from scripts import mastermind_moderate_phase0 as phase0
    path = tmp_path / "trial_ledger.jsonl"
    raw = ('{"family":"mastermind_moderate_phase0","kind":"declared_budget",'
           '"n":8,"config_hash":"budget-fixture"}\n')
    path.write_text(raw)
    ledger, count = phase0._trial_context(path)
    assert count == 8 and ledger.literal_n(phase0.TRIAL_FAMILY) == 0
    assert path.read_text() == raw


@pytest.mark.parametrize("state", ["absent", "different_family", "corrupt"])
def test_gtaa_phase0_does_not_infer_a_trial_count_from_missing_evidence(tmp_path, state):
    from scripts import mastermind_moderate_phase0 as phase0
    path = tmp_path / "trial_ledger.jsonl"
    if state == "different_family":
        path.write_text('{"family":"other","kind":"declared_budget","n":8,"config_hash":"other-budget"}\n')
    elif state == "corrupt":
        path.write_text('{invalid json}\n')
    before = path.read_bytes() if path.exists() else None
    with pytest.raises(RuntimeError, match="GTAA trial"):
        phase0._trial_context(path)
    assert (path.read_bytes() if path.exists() else None) == before

from scripts import build_live_overlay as blo
from scripts import build_masterminds as bmm


def _gtaa_prices(rising=1, rows=800):
    index = pd.bdate_range('2018-01-02', periods=rows)
    return pd.DataFrame({asset: 100 * np.exp((.001 if i < rising else -.001) * np.arange(rows))
                         for i, asset in enumerate(bmm.M.ASSETS)}, index=index)


def _gtaa_external_data(monkeypatch, prices):
    # Supply only external I/O. Native conviction, TSMOM, weights and portfolio
    # accounting execute unchanged; unavailable macro data uses the existing
    # neutral-regime fallback. Historical qualification uses populated caches.
    monkeypatch.setattr(bmm.M.store, 'read', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bmm.M.ea, 'bill_yield', lambda: pd.Series(4.0, index=prices.index))


@pytest.mark.parametrize('profile', ['conservative', 'moderate', 'aggressive'])
@pytest.mark.parametrize('rising', [0, 1, 2, 9])
def test_gtaa_final_caps_reach_native_backtest_and_json(monkeypatch, profile, rising):
    prices = _gtaa_prices(rising)
    _gtaa_external_data(monkeypatch, prices)
    result = bmm.M.backtest(profile, P=prices)
    weights, prof = result['weights'], bmm.M.PROFILES[profile]
    assert np.isfinite(weights.to_numpy()).all()
    assert (weights.to_numpy() >= 0).all()
    assert (weights.to_numpy() <= prof['w_cap'] + 1e-12).all()
    assert (weights.sum(axis=1) <= prof['max_lev'] + 1e-12).all()
    before_warmup = weights.index < weights.index[0] + pd.Timedelta(days=300)
    assert not weights.loc[before_warmup].to_numpy().any()
    changed = weights.diff().abs().sum(axis=1).to_numpy() > 1e-12
    assert not changed[np.arange(len(weights)) % bmm.M._REBAL != 0].any()
    expected = prof['max_lev'] / 9 if rising == 9 else prof['w_cap']
    np.testing.assert_allclose(weights.iloc[-1, :rising], expected, rtol=0, atol=1e-12)
    assert not weights.iloc[-1, rising:].to_numpy().any()

    # The real accounting applies held targets one bar later. At the settled
    # final row turnover is zero, so cash/financing has a direct scalar oracle.
    gross = weights.shift(1).fillna(0).sum(axis=1)
    pd.testing.assert_series_equal(result['scorecard']['gross_lev'], gross, check_names=False)
    final_gross = float(gross.iloc[-1])
    days = (prices.index[-1] - prices.index[-2]).days
    cash = (max(1 - final_gross, 0) * .04 - max(final_gross - 1, 0) * .05) * days / 365
    asset_return = float((weights.iloc[-2] * prices.pct_change(fill_method=None).iloc[-1]).sum())
    assert result['scorecard']['net'].iloc[-1] == pytest.approx(asset_return + cash, abs=1e-12)

    card = bmm._rich_card(profile, result)
    snap = bmm._snap([card], [result], '2026-11-11 00:00 UTC')
    published = json.loads(json.dumps(snap, allow_nan=False))['cards'][0]
    assert published['alloc'] == result['alloc']
    assert published['gross_now'] == round(final_gross, 2)
    for allocation in published['alloc']:
        assert allocation['weight'] == round(float(weights.iloc[-1][allocation['asset']]) * 100, 1)
        assert allocation['weight'] <= prof['w_cap'] * 100 + 1e-9


@pytest.mark.parametrize('profile', ['conservative', 'moderate', 'aggressive'])
def test_gtaa_cap_does_not_redistribute_released_exposure(monkeypatch, profile):
    prices = _gtaa_prices()
    prof = bmm.M.PROFILES[profile]
    conviction = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    conviction['SPY'], conviction['IEF'] = 1.0, prof['w_cap'] / 20
    monkeypatch.setattr(bmm.M, '_conviction', lambda _prices: conviction)
    final = bmm.M._weights(prices, prof).iloc[-1]
    assert final['SPY'] == pytest.approx(prof['w_cap'])
    assert final['IEF'] == pytest.approx(prof['w_cap'] / 2)
    assert final.sum() == pytest.approx(1.5 * prof['w_cap'])


@pytest.mark.parametrize('volatility', ['zero', 'missing', 'changing'])
def test_gtaa_volatility_cases_preserve_finite_final_limits(monkeypatch, volatility):
    prices = _gtaa_prices(rows=900)
    if volatility == 'zero':
        prices['SPY'] = 100.0
    elif volatility == 'missing':
        prices['SPY'] = np.nan
    else:
        rng = np.random.default_rng(11003)
        moves = np.r_[np.repeat(.001, 500), rng.normal(.001, .035, 400)]
        prices['SPY'] = 100 * np.exp(np.cumsum(moves))
    conviction = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    conviction['SPY'] = 1.0
    monkeypatch.setattr(bmm.M, '_conviction', lambda _prices: conviction)
    prof = bmm.M.PROFILES['moderate']
    weights = bmm.M._weights(prices, prof)
    assert np.isfinite(weights.to_numpy()).all()
    assert (weights.to_numpy() >= 0).all()
    assert (weights.to_numpy() <= prof['w_cap'] + 1e-12).all()
    assert (weights.sum(axis=1) <= prof['max_lev'] + 1e-12).all()
    if volatility == 'missing':
        assert not weights.to_numpy().any()
    elif volatility == 'zero':
        assert weights['SPY'].iloc[-1] == pytest.approx(prof['w_cap'])


def test_gtaa_signal_change_keeps_weekly_hold_and_next_bar_execution(monkeypatch):
    prices = _gtaa_prices()
    _gtaa_external_data(monkeypatch, prices)
    conviction = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    conviction.loc[:prices.index[606], 'SPY'] = 1.0
    monkeypatch.setattr(bmm.M, '_conviction', lambda _prices: conviction)
    result = bmm.M.backtest('moderate', P=prices)
    weights = result['weights']['SPY']
    assert (weights.iloc[605:610] == .4).all()
    assert weights.iloc[610] == 0
    assert result['scorecard']['gross_lev'].iloc[610] == .4
    assert result['scorecard']['gross_lev'].iloc[611] == 0


def test_gtaa_missing_optional_asset_retains_cap_and_emit(monkeypatch):
    prices = _gtaa_prices().drop(columns='BTC-USD')
    _gtaa_external_data(monkeypatch, prices)
    result = bmm.M.backtest('moderate', P=prices)
    assert 'BTC-USD' not in result['weights']
    assert result['weights']['SPY'].iloc[-1] == pytest.approx(.4)
    assert result['alloc'] == [{'asset': 'SPY', 'label_en': 'S&P 500', 'label_zh': '标普500', 'weight': 40.0}]


def test_gtaa_late_history_keeps_its_own_calendar_warmup(monkeypatch):
    prices = _gtaa_prices(9, rows=900)
    prices.loc[:prices.index[499], 'BTC-USD'] = np.nan
    _gtaa_external_data(monkeypatch, prices)
    result = bmm.M.backtest('moderate', P=prices)
    weights = result['weights']
    cutoff = prices['BTC-USD'].first_valid_index() + pd.Timedelta(days=300)
    assert not weights.loc[weights.index < cutoff, 'BTC-USD'].to_numpy().any()
    assert weights['BTC-USD'].iloc[-1] > 0
    assert (weights.to_numpy() <= .4 + 1e-12).all()


def test_universe_includes_gtaa_assets():
    uni = blo.build_universe()
    assert isinstance(uni, list) and uni
    assert "SPY" in uni and "GC=F" in uni
    assert len(uni) <= int((blo.config.load().get("live") or {}).get("max_universe", 150))


def test_offline_build_emits_valid_v2_overlay(tmp_path, monkeypatch):
    # Pin the input universe/baseline so this schema contract does not require
    # production data to be materialized in a sparse checkout.
    monkeypatch.setattr(blo, "build_universe", lambda: ["SPY", "GC=F"])
    monkeypatch.setattr(blo, "_load_baseline", lambda ticker, close: {
        "ticker": ticker, "asof": "2026-09-30", "tech": {"close": 100.0},
    })
    # site_dir=tmp_path: output never lands in the repo's real site/ tree
    res = blo.build(offline=True, limit=8, site_dir=tmp_path)
    assert res["status"] == "ok"
    site = tmp_path
    raw = (site / "live" / "overlay.json").read_text()
    assert "NaN" not in raw                         # allow_nan=False -> never invalid JSON
    out = json.loads(raw)
    assert out["schema"] == "live.overlay.v2"
    assert out["n_quotes"] == 0 and out["n"] >= 1
    for rec in out["tickers"].values():
        assert rec["stale"] is True and "tech" in rec and "region" in rec
    # Existing globe regions plus independently eligible Stock Connect.
    assert set(out["sessions"]) == {
        "us", "cn", "hk", "ca", "connect", "jp", "kr", "tw", "gb", "eu",
    }
    assert "VIX" in out["market"] and "band" in out["market"]["VIX"]
    assert (site / "live_config.js").exists()


def test_offline_allocations_are_stale_marked(tmp_path):
    blo.build(offline=True, limit=4, site_dir=tmp_path)
    out = json.loads((tmp_path / "live" / "overlay.json").read_text())
    for region in out.get("allocations", {}).values():
        for card in region["cards"]:
            for leg in card["alloc"]:
                assert leg["stale"] is True and leg["live_price"] is None


def test_market_session_block_shape(tmp_path):
    blo.build(offline=True, limit=2, site_dir=tmp_path)
    out = json.loads((tmp_path / "live" / "overlay.json").read_text())
    us = out["sessions"]["us"]
    assert {"region", "open", "local_time", "state", "timezone",
            "calendar_verified", "checked_at", "valid_until", "expected_session",
            "next_open", "data_frozen", "source_urls"} <= set(us)
    assert us["region"] == "us" and us["timezone"] == "America/New_York"
    assert isinstance(us["local_time"], str) and isinstance(us["data_frozen"], bool)
    if us["calendar_verified"]:
        assert isinstance(us["open"], bool) and us["source_urls"]
    else:
        assert us["open"] is None and us["state"] == "unverified"
    checked = datetime.fromisoformat(us["checked_at"])
    expires = datetime.fromisoformat(us["valid_until"])
    assert checked.tzinfo is not None and expires > checked
    assert datetime.fromisoformat(us["next_open"]).tzinfo is not None
    assert datetime.fromisoformat(us["expected_session"]).date().isoformat() == us["expected_session"]
    # The other five venue clocks retain their incumbent shape.
    assert set(out["sessions"]["jp"]) == {"region", "open", "local_time"}


def test_live_config_js_carries_worker_url(tmp_path):
    blo.write_live_config(tmp_path)
    js = (tmp_path / "live_config.js").read_text()
    assert "LIVE_QUOTES_URL" in js and "LIVE_POLL_SEC" in js


def test_resolve_worker_url_env_override_and_https_guard(monkeypatch):
    # env var overrides config + strips a trailing slash (turn-on via a GitHub repo variable)
    monkeypatch.setenv("LIVE_QUOTES_WORKER_URL", "https://q.example.workers.dev/")
    assert blo.resolve_worker_url() == "https://q.example.workers.dev"
    # a non-https value is rejected so a malformed variable can't break live.js
    monkeypatch.setenv("LIVE_QUOTES_WORKER_URL", "http://insecure.dev")
    assert blo.resolve_worker_url() == ""
    # empty env -> falls back to config.yml (default "")
    monkeypatch.delenv("LIVE_QUOTES_WORKER_URL", raising=False)
    assert blo.resolve_worker_url() == str((blo.config.load().get("live") or {}).get("quotes_worker_url", "") or "")


def test_masterminds_snap_v2_carries_alloc_and_asof():
    if not hasattr(bmm, "_snap"):
        import pytest
        pytest.skip("build_masterminds._snap (v2 alloc emit) is a main-only refactor not "
                    "yet on feat/signal-engine-buy-filter; auto-reactivates after merge")
    cards = [{"key": "mm_moderate", "name_en": "MM Moderate", "cagr": 11.5,
              "sharpe": 1.1, "maxdd": -24.0}]
    ress = [{"asof": "2026-06-20", "gross_now": 1.4,
             "alloc": [{"asset": "SPY", "weight": 40.0},
                       {"asset": "GC=F", "weight": 20.0}]}]
    snap = bmm._snap(cards, ress, "2026-06-21 08:20 UTC")
    assert snap["schema"] == "masterminds.latest.v2"
    assert snap["asof"] == "2026-06-20" and snap["stale_after_min"] == 1440
    c0 = snap["cards"][0]
    assert c0["alloc"][0]["asset"] == "SPY" and c0["gross_now"] == 1.4
