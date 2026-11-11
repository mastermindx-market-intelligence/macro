"""Smoke tests for engine/lab.py.

Tests:
  1. Module imports without error.
  2. indicator('rsi', df) matches canon.rsi exactly.
  3. A minimal 2-ticker backtest returns a Trial with finite stats.
  4. The deflated_sharpe path uses a ledger (not a literal N) — the ratchet test
     would catch it, but we verify explicitly here.
  5. Signal / confluence construction.
  6. features() returns a DataFrame.
  7. Trial.to_ledger() writes a JSONL row.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _fake_ohlcv(n: int = 600, seed: int = 42) -> pd.DataFrame:
    """Synthetic OHLCV with a realistic random-walk close."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    close = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.012, n))
    high = close * (1.0 + rng.uniform(0.0, 0.01, n))
    low = close * (1.0 - rng.uniform(0.0, 0.01, n))
    volume = rng.integers(1_000_000, 10_000_000, n).astype(float)
    return pd.DataFrame(
        {"close": close, "high": high, "low": low, "volume": volume},
        index=dates,
    )


def _fake_universe(n_tickers: int = 2, n_bars: int = 600) -> dict[str, pd.DataFrame]:
    return {f"T{i}": _fake_ohlcv(n_bars, seed=i) for i in range(n_tickers)}


@pytest.fixture
def synthetic_store(monkeypatch):
    """Replace only store I/O; exercise the actual load and benchmark readers."""
    from lib import store

    frame = _fake_ohlcv(seed=97)

    def read(group, name):
        assert group in {"stocks", "yahoo"}
        return frame.copy()

    monkeypatch.setattr(store, "read", read)
    return frame


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------

def test_import():
    import engine.lab  # noqa: F401


# ---------------------------------------------------------------------------
# 2. indicator('rsi') matches canon.rsi
# ---------------------------------------------------------------------------

def test_indicator_rsi_matches_canon():
    from engine import canon
    from engine import lab

    df = _fake_ohlcv()
    lab_rsi = lab.indicator("rsi", df, n=14)
    canon_rsi = canon.rsi(df["close"], n=14)

    # Align on common non-NaN rows
    common = lab_rsi.dropna().index.intersection(canon_rsi.dropna().index)
    assert len(common) > 100, "Too few common non-NaN bars"
    np.testing.assert_allclose(
        lab_rsi.loc[common].values,
        canon_rsi.loc[common].values,
        rtol=1e-9,
        err_msg="indicator('rsi') does not match canon.rsi",
    )


# ---------------------------------------------------------------------------
# 3. Unknown indicator raises KeyError
# ---------------------------------------------------------------------------

def test_indicator_unknown_raises():
    from engine import lab

    df = _fake_ohlcv()
    with pytest.raises(KeyError, match="Unknown indicator"):
        lab.indicator("__not_a_real_indicator__", df)


# ---------------------------------------------------------------------------
# 4. features() returns a DataFrame with expected columns
# ---------------------------------------------------------------------------

def test_features_returns_dataframe():
    from engine import lab

    df = _fake_ohlcv()
    feat = lab.features(df)
    assert isinstance(feat, pd.DataFrame), "features() must return a DataFrame"
    assert len(feat) == len(df), "features() index length mismatch"
    assert "rsi" in feat.columns, "'rsi' column expected in features()"
    assert "macd_hist" in feat.columns, "'macd_hist' column expected in features()"


def test_features_subset():
    from engine import lab

    df = _fake_ohlcv()
    feat = lab.features(df, cols=["rsi", "sma"])
    assert set(feat.columns) == {"rsi", "sma"}


# ---------------------------------------------------------------------------
# 5. Signal construction and evaluate()
# ---------------------------------------------------------------------------

def test_signal_from_expr():
    from engine import lab

    def _simple_expr(df):
        close = df["close"]
        sig = close.pct_change(5)
        pos = (sig > 0).astype(float)
        return sig, pos

    s = lab.Signal(expr=_simple_expr, horizon=5, family="test_lab")
    df = _fake_ohlcv()
    sig_out, pos_out = s.evaluate(df)
    assert isinstance(sig_out, pd.Series)
    assert isinstance(pos_out, pd.Series)
    assert len(sig_out) == len(df)


def test_signal_from_precomputed():
    from engine import lab

    df = _fake_ohlcv()
    sig = df["close"].pct_change(5)
    pos = (sig > 0).astype(float)
    s = lab.Signal(signal=sig, pos=pos, horizon=5, family="test_lab")
    out_s, out_p = s.evaluate(df)
    pd.testing.assert_series_equal(out_s, sig)
    pd.testing.assert_series_equal(out_p, pos)


def test_signal_missing_raises():
    from engine import lab

    s = lab.Signal(horizon=5, family="test_lab")
    with pytest.raises(ValueError, match="Signal must have"):
        s.evaluate(pd.DataFrame())


# ---------------------------------------------------------------------------
# 6. confluence()
# ---------------------------------------------------------------------------

def test_confluence_all():
    from engine import lab

    def _rsi_sig(df):
        r = lab.indicator("rsi", df, n=14)
        pos = (r < 40).astype(float)
        return r, pos

    def _mom_sig(df):
        m = df["close"].pct_change(21)
        pos = (m > 0).astype(float)
        return m, pos

    s1 = lab.Signal(expr=_rsi_sig, horizon=21, family="test_lab", name="rsi")
    s2 = lab.Signal(expr=_mom_sig, horizon=21, family="test_lab", name="mom")
    combined = lab.confluence(s1, s2, mode="all")

    df = _fake_ohlcv()
    sig_out, pos_out = combined.evaluate(df)
    assert isinstance(pos_out, pd.Series)
    # 'all' mode: combined pos <= each individual pos
    _, p1 = s1.evaluate(df)
    _, p2 = s2.evaluate(df)
    common = pos_out.dropna().index.intersection(p1.dropna().index).intersection(
        p2.dropna().index
    )
    assert (pos_out.loc[common] <= p1.reindex(common).fillna(0)).all()


# ---------------------------------------------------------------------------
# 7. Minimal 2-ticker backtest returns a Trial with finite stats
# ---------------------------------------------------------------------------

def test_backtest_returns_trial_with_finite_stats():
    from engine import lab

    universe = _fake_universe(n_tickers=2, n_bars=600)

    def _rsi_signal(df):
        r = lab.indicator("rsi", df, n=14)
        pos = (r < 40).astype(float)
        return r, pos

    sig = lab.Signal(
        expr=_rsi_signal, horizon=21, family="test_lab_backtest", name="rsi_oversold"
    )
    trial = lab.backtest(sig, universe, cost_bps=5.0, n_configs_searched=1)

    assert isinstance(trial, lab.Trial)
    assert trial.survivorship_biased is True
    assert isinstance(trial.stats, dict)

    # At least one finite numeric stat must be present
    finite_stats = [
        k for k, v in trial.stats.items()
        if isinstance(v, (int, float)) and np.isfinite(v)
    ]
    assert finite_stats, (
        f"Expected at least one finite numeric stat, got: {trial.stats}"
    )


# ---------------------------------------------------------------------------
# 8. deflated_sharpe path uses a ledger (not a literal n_trials)
# ---------------------------------------------------------------------------

def test_backtest_uses_ledger_not_literal_n():
    """Verify that engine.lab never calls deflated_sharpe with a literal n_trials.

    This is checked statically by tests/test_no_literal_ntrials.py but we also
    verify at runtime that the Trial stats contain 'n_trials' and that it came
    from TrialLedger.with_declared_budget, not a bare literal argument.
    """
    import ast
    import inspect
    from engine import lab

    source = inspect.getsource(lab)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute) else
                    f.id if isinstance(f, ast.Name) else None)
            if name == "deflated_sharpe":
                kw_names = {k.arg for k in node.keywords if k.arg}
                assert "ledger" in kw_names, (
                    "engine/lab.py calls deflated_sharpe without ledger= "
                    "— this violates the CI ratchet"
                )
                assert "n_trials" not in kw_names, (
                    "engine/lab.py passes n_trials= to deflated_sharpe "
                    "— use the Trial Ledger instead"
                )


# ---------------------------------------------------------------------------
# 9. Trial.verdict() returns one of the allowed strings
# ---------------------------------------------------------------------------

def test_trial_verdict_taxonomy():
    from engine import lab

    trial = lab.Trial(
        name="test",
        family="test_lab",
        stats={"dsr": 0.96, "sharpe_ci": [0.1, 0.5, 1.2], "split_half_consistent": True,
               "mean_ic": 0.05},
    )
    v = trial.verdict()
    assert v in ("TRADABLE", "ENTRY-OVERLAY", "RISK-CONTROL", "NO-EDGE")


def test_trial_verdict_no_edge():
    from engine import lab

    trial = lab.Trial(name="test", family="test_lab", stats={"dsr": 0.3})
    assert trial.verdict() == "NO-EDGE"


# ---------------------------------------------------------------------------
# 10. Trial.to_ledger() writes a JSONL row
# ---------------------------------------------------------------------------

def test_trial_to_ledger():
    import json
    from engine import lab

    trial = lab.Trial(
        name="test_ticker",
        family="test_lab_ledger",
        stats={"dsr": 0.85, "mean_ic": 0.03},
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trials.jsonl"
        trial.to_ledger(path)
        assert path.exists()
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        assert len(rows) == 1
        row = rows[0]
        assert row["name"] == "test_ticker"
        assert row["family"] == "test_lab_ledger"
        assert row["stats"]["dsr"] == 0.85
        assert "verdict" in row


# ---------------------------------------------------------------------------
# 11. load() with shortcuts
# ---------------------------------------------------------------------------

def test_load_quick(synthetic_store):
    """load('quick') should return at most 8 tickers and each is a DataFrame."""
    from engine import lab

    result = lab.load("quick")
    assert result, "the deterministic store must exercise the loader assertions"
    for ticker, df in result.items():
        assert isinstance(df, pd.DataFrame)
        assert "close" in df.columns


# ---------------------------------------------------------------------------
# 12. bench() returns a Series
# ---------------------------------------------------------------------------

def test_bench_returns_series(synthetic_store):
    from engine import lab

    s = lab.bench("_GSPC")
    assert isinstance(s, pd.Series)
    pd.testing.assert_series_equal(s, synthetic_store["close"].rename("_GSPC"))


# ---------------------------------------------------------------------------
# 13. characterize() returns a dict and writes indicator_characterization.json
# ---------------------------------------------------------------------------

def test_characterize_returns_dict_and_writes_json(synthetic_store):
    """characterize() must return a dict with per-indicator keys and write JSON."""
    import json
    import tempfile
    from pathlib import Path
    from unittest import mock
    from engine import lab

    universe = _fake_universe(n_tickers=3, n_bars=600)

    # Patch the _LAB_DIR so the test does not write to the real data dir
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_lab_dir = Path(tmpdir) / "lab"
        with mock.patch.object(lab, "_LAB_DIR", fake_lab_dir):
            result = lab.characterize(["rsi", "macd_hist"], universe)

    assert isinstance(result, dict), "characterize() must return a dict"
    assert "rsi" in result, "Result must contain 'rsi' key"
    assert "macd_hist" in result, "Result must contain 'macd_hist' key"

    for name in ("rsi", "macd_hist"):
        entry = result[name]
        assert isinstance(entry, dict), f"Entry for {name!r} must be a dict"
        # Status must not be 'pending' (stub is gone)
        assert entry.get("status") != "pending", (
            f"Entry for {name!r} still shows stub status 'pending'"
        )
        # Must have the four characterization sections
        for section in ("base_rate", "persistence", "regime", "orthogonality"):
            assert section in entry, (
                f"Entry for {name!r} missing section '{section}'"
            )


def test_characterize_unknown_indicator(synthetic_store):
    """characterize() must mark unknown indicator names rather than raising."""
    import tempfile
    from pathlib import Path
    from unittest import mock
    from engine import lab

    universe = _fake_universe(n_tickers=2, n_bars=300)

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_lab_dir = Path(tmpdir) / "lab"
        with mock.patch.object(lab, "_LAB_DIR", fake_lab_dir):
            result = lab.characterize(["__not_a_real_indicator__"], universe)

    assert result["__not_a_real_indicator__"]["status"] == "unknown_indicator"


def test_characterize_writes_json(synthetic_store):
    """characterize() must write data/lab/indicator_characterization.json."""
    import json
    import tempfile
    from pathlib import Path
    from unittest import mock
    from engine import lab

    universe = _fake_universe(n_tickers=2, n_bars=300)

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_lab_dir = Path(tmpdir) / "lab"
        with mock.patch.object(lab, "_LAB_DIR", fake_lab_dir):
            lab.characterize(["rsi"], universe)
            json_path = fake_lab_dir / "indicator_characterization.json"
            assert json_path.exists(), "indicator_characterization.json must be written"
            data = json.loads(json_path.read_text())
            assert "rsi" in data


# ---------------------------------------------------------------------------
# 14. list_signals() passthrough and catalog_backtest() returns a Trial
# ---------------------------------------------------------------------------

def test_list_signals_returns_list():
    """list_signals() must return a list of dicts with signal_id keys."""
    from engine import lab

    sigs = lab.list_signals()
    assert isinstance(sigs, list), "list_signals() must return a list"
    # Catalog may be empty if source modules are missing — just check types
    for entry in sigs:
        assert isinstance(entry, dict), "Each signal entry must be a dict"
        assert "signal_id" in entry, "Each entry must have 'signal_id'"


def test_list_signals_family_filter():
    """list_signals(family=...) must filter to the given family."""
    from engine import lab

    all_sigs = lab.list_signals()
    if not all_sigs:
        return  # empty catalog in CI; skip
    first_family = all_sigs[0]["family"]
    filtered = lab.list_signals(family=first_family)
    assert all(s["family"] == first_family for s in filtered), (
        "list_signals(family=...) returned signals from a different family"
    )


def test_catalog_backtest_returns_trial():
    """catalog_backtest(signal_id, universe) must return a Trial."""
    from engine import lab, tech_catalog

    # Pick the first available signal from the catalog
    sigs = tech_catalog.list_signals()
    if not sigs:
        pytest.skip("tech_catalog returned an empty catalog; skipping")

    signal_id = sigs[0]["signal_id"]
    universe = _fake_universe(n_tickers=2, n_bars=600)

    trial = lab.catalog_backtest(signal_id, universe, cost_bps=5.0)
    assert isinstance(trial, lab.Trial), (
        f"catalog_backtest must return a Trial, got {type(trial)}"
    )
    assert trial.survivorship_biased is True
    assert isinstance(trial.stats, dict)


# ---------------------------------------------------------------------------
# 18. characterize() forward-return MATURITY (#10996)
#
# `characterize()` used to read its forward-return labels with `Series.asof(date)`.
# `asof` returns the last value at or before the date, so a formation date whose
# forward window had not been observed yet silently inherited the most recent
# MATURED return instead of reading as missing. Two consequences, both tested here:
#   (a) immature dates were counted in the IC sample and could clear `min_ics`,
#       publishing a sufficient-looking characterization from too little evidence;
#   (b) the same stale return vector was reused against several different later
#       signal vectors, so repeat observations were not independent observations.
# The fixtures use 30 names because `validation.rank_ic` returns NaN below 10
# joint names -- the older 2-3 ticker fixtures never exercised this path at all.
# ---------------------------------------------------------------------------

_MATURITY_HORIZON = 21


def _maturity_universe(n_tickers: int = 30, n_bars: int = 80) -> dict[str, pd.DataFrame]:
    """30 names x 80 business days, deterministic (seeds from the #10996 fixture)."""
    return {f"S{i:02d}": _fake_ohlcv(n_bars, seed=20261111 + i) for i in range(n_tickers)}


def _no_bench(_name: str = "_GSPC") -> pd.Series:
    """Regime benchmark stub: an empty series disables the SPX/VIX regime splits."""
    return pd.Series(dtype=float)


def _run_characterize(universe, min_ics=6, horizon=_MATURITY_HORIZON, indicator="ema"):
    """Run characterize() with the store reads and the artifact dir stubbed out."""
    import tempfile
    from pathlib import Path
    from unittest import mock
    from engine import lab

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_lab_dir = Path(tmpdir) / "lab"
        with mock.patch.object(lab, "_LAB_DIR", fake_lab_dir), \
                mock.patch.object(lab, "bench", _no_bench):
            return lab.characterize([indicator], universe, horizon=horizon, min_ics=min_ics)


def _exact_date_ic_reference(universe, indicator="ema", horizon=_MATURITY_HORIZON):
    """Independent reference: only dates whose forward return is actually observed.

    Computed straight from the raw arrays with exact-date lookups and no `asof`
    anywhere, so it cannot inherit the producer's backfill behaviour.
    """
    from engine import lab
    from engine import validation as V

    signals, forwards = {}, {}
    grid = None
    for tkr, df in universe.items():
        signals[tkr] = lab.INDICATORS[indicator](df)
        forwards[tkr] = df["close"].pct_change(horizon).shift(-horizon)
        if grid is None:
            grid = signals[tkr].index

    # Preserve the producer's original formation grid. Each ticker's maturity is
    # checked independently below; a short first history cannot truncate peers.
    dates = grid[::max(1, horizon // 2)]

    ics: list[float] = []
    for date in dates:
        sc, fc = {}, {}
        for tkr in universe:
            sv = signals[tkr].get(date, np.nan)
            fv = forwards[tkr].get(date, np.nan)
            if np.isfinite(sv) and np.isfinite(fv):
                sc[tkr], fc[tkr] = float(sv), float(fv)
        if len(sc) < 5:
            continue
        ic = V.rank_ic(pd.Series(sc), pd.Series(fc))
        if np.isfinite(ic):
            ics.append(ic)
    return len(ics), (float(np.mean(ics)) if ics else None)


def test_characterize_ignores_immature_formation_dates():
    """The IC sample must match an exact-date reference, not an asof-backfilled one."""
    universe = _maturity_universe(n_tickers=30, n_bars=80)
    result = _run_characterize(universe, min_ics=6)["ema"]

    ref_n, _ref_mean = _exact_date_ic_reference(universe)
    assert result["base_rate"]["n"] == ref_n, (
        f"characterize() counted {result['base_rate']['n']} IC observations but only "
        f"{ref_n} formation dates have matured forward returns"
    )
    assert ref_n == 5, f"fixture drifted: expected 5 matured dates, got {ref_n}"
    # 5 matured observations cannot clear a floor of 6. Before the fix the two immature
    # tail dates were backfilled and counted, so this same call published a summary.
    assert result["base_rate"] == {"n": 5, "insufficient": True}
    assert result["status"] == "insufficient"


def test_characterize_mean_ic_matches_exact_date_reference():
    """A published mean IC must be the exact-date mean over matured dates (#10996)."""
    # 120 bars so the matured sample is long enough for ic_summary (which needs n >= 6);
    # the point is the VALUE, not the floor.
    universe = _maturity_universe(n_tickers=30, n_bars=120)
    result = _run_characterize(universe, min_ics=6)["ema"]
    assert result["status"] == "ok"

    ref_n, ref_mean = _exact_date_ic_reference(universe)
    assert ref_mean is not None and ref_n >= 6
    assert result["base_rate"]["n"] == ref_n
    # ic_summary rounds mean_ic to 4 dp.
    assert result["base_rate"]["mean_ic"] == pytest.approx(ref_mean, abs=1e-4), (
        "mean IC must be the exact-date mean over matured formation dates"
    )
    assert (result["base_rate"]["mean_ic"] > 0) == (ref_mean > 0)


def test_characterize_never_reuses_a_forward_return_vector(monkeypatch):
    """No two sampled formation dates may share one forward-return cross-section.

    Under the asof read the last two dates both received the offset-58 return
    vector, so this set contained fewer members than the call log.
    """
    from engine import validation as V

    seen: list[tuple] = []
    real_rank_ic = V.rank_ic

    def spy(signal, fwd):
        seen.append(tuple(np.round(np.asarray(pd.Series(fwd), dtype=float), 12)))
        return real_rank_ic(signal, fwd)

    monkeypatch.setattr(V, "rank_ic", spy)
    universe = _maturity_universe(n_tickers=30, n_bars=80)
    result = _run_characterize(universe, min_ics=6)["ema"]

    assert len(seen) == result["base_rate"]["n"]
    assert len(set(seen)) == len(seen), (
        "a forward-return vector was reused across formation dates: "
        f"{len(seen)} IC calls but only {len(set(seen))} distinct return vectors"
    )


def test_characterize_min_ics_still_rejects_matured_only_sample():
    """A higher floor must reject the same fixture; the stale tail cannot rescue it."""
    universe = _maturity_universe(n_tickers=30, n_bars=80)
    result = _run_characterize(universe, min_ics=8)["ema"]

    assert result["status"] == "insufficient"
    assert result["base_rate"] == {"n": 5, "insufficient": True}
    assert result["regime"] == {}


def test_characterize_longer_history_does_not_leak_the_tail():
    """100 bars: the count must track matured dates, not bar count."""
    universe = _maturity_universe(n_tickers=30, n_bars=100)
    result = _run_characterize(universe, min_ics=6)["ema"]

    ref_n, _ref_mean = _exact_date_ic_reference(universe)
    assert result["base_rate"]["n"] == ref_n
    assert result["status"] == ("ok" if ref_n >= 6 else "insufficient")


def test_characterize_ten_name_floor_is_intact():
    """9 names cannot form a cross-sectional IC: 0 observations, not a false pass."""
    universe = _maturity_universe(n_tickers=9, n_bars=80)
    result = _run_characterize(universe, min_ics=6)["ema"]

    assert result["base_rate"] == {"n": 0, "insufficient": True}
    assert result["status"] == "insufficient"


@pytest.mark.parametrize("first_bars,other_bars,expected_n", [(80, 120, 7), (400, 500, 39)])
def test_characterize_preserves_mature_peers_with_short_first_history(
        monkeypatch, tmp_path, first_bars, other_bars, expected_n):
    """A short first ticker must not discard mature cross-sections from its peers."""
    import json
    from engine import lab

    universe = _maturity_universe(n_tickers=30, n_bars=other_bars)
    universe["S00"] = universe["S00"].iloc[:first_bars].copy()
    monkeypatch.setattr(lab, "_LAB_DIR", tmp_path)
    monkeypatch.setattr(lab, "bench", _no_bench)

    produced = lab.characterize(["ema"], universe, horizon=_MATURITY_HORIZON, min_ics=6)
    persisted = json.loads((tmp_path / "indicator_characterization.json").read_text())
    assert persisted == produced
    result = persisted["ema"]
    ref_n, ref_mean = _exact_date_ic_reference(universe)
    assert ref_n == expected_n, "fixture must retain mature peers on the original grid"
    assert result["base_rate"]["n"] == expected_n
    assert result["status"] == "ok"
    assert result["base_rate"]["mean_ic"] == pytest.approx(ref_mean, abs=1e-4)


def test_characterize_missing_formation_dates_are_not_backfilled(monkeypatch, tmp_path):
    """Missing rows cannot borrow earlier labels to pass the ten-name IC floor."""
    import json
    from engine import lab

    universe = _maturity_universe(n_tickers=30, n_bars=80)
    missing_date = universe["S00"].index[40]
    # Keep the first ticker's grid intact, but leave only nine names on this date.
    for tkr in list(universe)[1:22]:
        universe[tkr] = universe[tkr].drop(index=missing_date)
    monkeypatch.setattr(lab, "_LAB_DIR", tmp_path)
    monkeypatch.setattr(lab, "bench", _no_bench)

    produced = lab.characterize(["ema"], universe, horizon=_MATURITY_HORIZON, min_ics=6)
    persisted = json.loads((tmp_path / "indicator_characterization.json").read_text())
    assert persisted == produced
    ref_n, _ = _exact_date_ic_reference(universe)
    assert ref_n == 4, "the missing formation date must remove one eligible cross-section"
    assert persisted["ema"]["base_rate"] == {"n": 4, "insufficient": True}
    assert persisted["ema"]["status"] == "insufficient"
