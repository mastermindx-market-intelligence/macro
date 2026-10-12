"""test_sni_us_stress.py — US/Mag-7 science stress set (synthetic data only)."""
import copy
import math
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/us_stress"),
)

from stress_set import (  # noqa: E402
    check_profile,
    hist_vol_normalize,
    load_closes_from_parquet,
    load_profiles,
    rolling_beta_residual,
    simple_returns,
    stress_table,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "research/single_name_intelligence/us_stress/profiles"
MODULE_PATH = ROOT / "research/single_name_intelligence/us_stress/stress_set.py"

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
FORBIDDEN = TICKERS + ["BABA"]
FLAGS = [
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
]
WINDOW = 63
RNG_SEED = 7


def _closes(rng, n=400, sigma=0.01, start=100.0):
    px = start
    out = [px]
    for _ in range(n - 1):
        px *= 1.0 + rng.gauss(0.0, sigma)
        out.append(px)
    return out


def _needed_names(profiles):
    names = set(profiles)
    for profile in profiles.values():
        ss = profile["stress_set"]
        names.update(ss["benchmarks"])
        names.add(ss["sector_etf"])
    return names


def _beta_at(stock_ret, bench_ret, t, window=WINDOW):
    s_win = stock_ret[t - window : t]
    b_win = bench_ret[t - window : t]
    mb = sum(b_win) / float(window)
    ms = sum(s_win) / float(window)
    var_b = sum((b - mb) ** 2 for b in b_win)
    cov = sum((s - ms) * (b - mb) for s, b in zip(s_win, b_win))
    return cov / var_b


def test_no_ticker_branch_law():
    src = MODULE_PATH.read_text(encoding="utf-8")
    for tok in FORBIDDEN:
        assert tok not in src


def test_profiles_load_and_refuse_authority():
    profiles = load_profiles(PROFILES_DIR)
    assert set(profiles) == set(TICKERS)
    for profile in profiles.values():
        for flag in FLAGS:
            assert profile["authority"][flag] is False
        assert profile["canonical_issuer_id"] is None
        counters = profile["counters"]
        assert counters
        for counter in counters.values():
            assert counter["security_id"] is None
            assert counter["issuer_link"] == "UNRESOLVED"
        assert profile["stress_set"]["descriptive_only"] is True
    one_key = next(iter(profiles))
    bad = copy.deepcopy(profiles[one_key])
    with __import__("pytest").raises(ValueError, match="stress profiles never carry identity ids"):
        bad["authority"]["rank_authority"] = True
    bad2 = copy.deepcopy(profiles[one_key])
    bad2["authority"] = dict(bad2["authority"])
    bad2["authority"]["rank_authority"] = True
    with __import__("pytest").raises(ValueError, match="stress profiles never carry identity ids"):
        check_profile(bad2)
    with __import__("pytest").raises(ValueError, match="stress profiles never carry identity ids"):
        stress_table({one_key: bad2}, {one_key: [1.0, 1.1]})


def test_beta_recovery():
    rng = random.Random(RNG_SEED)
    n = 400
    bench = [rng.gauss(0.0, 0.01) for _ in range(n)]
    stock = [1.5 * b + rng.gauss(0.0, 0.002) for b in bench]
    resid = rolling_beta_residual(stock, bench, window=WINDOW)
    betas = [_beta_at(stock, bench, t) for t in range(max(WINDOW, 100), n)]
    assert abs(sum(betas) / len(betas) - 1.5) < 0.1
    tail = [resid[t] for t in range(max(WINDOW, 100), n) if resid[t] is not None]
    assert tail
    assert abs(sum(tail) / len(tail) - 0.0) < 0.001


def test_no_look_ahead():
    rng = random.Random(RNG_SEED)
    n = 250
    bench = [rng.gauss(0.0, 0.01) for _ in range(n)]
    stock = [1.2 * b + rng.gauss(0.0, 0.003) for b in bench]
    base = rolling_beta_residual(stock, bench, window=WINDOW)
    t = 180
    stock2 = list(stock)
    bench2 = list(bench)
    stock2[t] = stock[t] + 0.4
    bench2[t] = bench[t] + 0.4
    shocked = rolling_beta_residual(stock2, bench2, window=WINDOW)
    for i in range(t):
        assert shocked[i] == base[i]
    assert any(shocked[i] != base[i] for i in range(t, n))


def test_hist_vol_normalize():
    rng = random.Random(RNG_SEED)
    series = [rng.gauss(0.0, 0.02) for _ in range(400)]
    normed = hist_vol_normalize(series, window=WINDOW)
    tail = [x for x in normed[200:] if x is not None]
    assert tail
    mean = sum(tail) / len(tail)
    var = sum((x - mean) ** 2 for x in tail) / float(len(tail))
    stdev = math.sqrt(var)
    assert 0.8 <= stdev <= 1.2
    zeros = [1.0] * 120
    znorm = hist_vol_normalize(zeros, window=WINDOW)
    assert all(x is None for x in znorm)


def test_stress_table_descriptive():
    rng = random.Random(RNG_SEED)
    profiles = load_profiles(PROFILES_DIR)
    closes = {name: _closes(rng) for name in _needed_names(profiles)}
    table = stress_table(profiles, closes, window=WINDOW)
    assert table["descriptive_only"] is True
    assert table["causal_claims"] == "none"
    for flag in FLAGS:
        assert table["authority_flags"][flag] is False
    summaries = table["summaries"]
    pair_count = 0
    for ticker, profile in profiles.items():
        benches = list(profile["stress_set"]["benchmarks"])
        sector = profile["stress_set"]["sector_etf"]
        if sector not in benches:
            benches.append(sector)
        assert set(summaries[ticker]) == set(benches)
        stock_ret = simple_returns(closes[ticker])
        for bench in benches:
            pair_count += 1
            stats = summaries[ticker][bench]
            bench_ret = simple_returns(closes[bench])
            n = min(len(stock_ret), len(bench_ret))
            resid = rolling_beta_residual(stock_ret[:n], bench_ret[:n], window=WINDOW)
            normed = hist_vol_normalize(resid, window=WINDOW)
            n_non = sum(1 for x in normed if x is not None)
            assert stats["n"] == n_non
            assert stats["n"] > 0
    assert pair_count == sum(len(v) for v in summaries.values())


def test_held_out_onboarding(tmp_path):
    rng = random.Random(RNG_SEED)
    dst = tmp_path / "profiles"
    shutil.copytree(PROFILES_DIR, dst)
    sample = (dst / "AAPL.yml").read_text(encoding="utf-8")
    held = (
        sample.replace("Apple Inc.", "Held Out Co.")
        .replace("apple", "heldout")
        .replace("AAPL", "ZZZZ")
        .replace("aapl", "zzzz")
    )
    (dst / "ZZZZ.yml").write_text(held, encoding="utf-8")
    loaded = load_profiles(dst)
    assert len(loaded) == 8
    assert "ZZZZ" in loaded
    assert loaded["ZZZZ"]["canonical_issuer_id"] is None
    closes = {name: _closes(rng) for name in _needed_names(loaded)}
    table = stress_table(loaded, closes, window=WINDOW)
    assert "ZZZZ" in table["summaries"]
    assert table["descriptive_only"] is True
    z_benches = table["summaries"]["ZZZZ"]
    assert "SPY" in z_benches
    assert all(z_benches[b]["n"] > 0 for b in z_benches)


def test_parquet_loader_returns_none(tmp_path, monkeypatch):
    missing = tmp_path / "no_such.parquet"
    assert load_closes_from_parquet(missing) is None
    dummy = tmp_path / "x.parquet"
    dummy.write_bytes(b"not-a-parquet-file")
    monkeypatch.setitem(sys.modules, "pandas", None)
    assert load_closes_from_parquet(dummy) is None
    monkeypatch.delitem(sys.modules, "pandas", raising=False)
    import builtins

    real_import = builtins.__import__

    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pandas" or name.startswith("pandas."):
            raise ImportError("simulated missing pandas")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked)
    assert load_closes_from_parquet(dummy) is None
    assert load_closes_from_parquet(missing) is None
