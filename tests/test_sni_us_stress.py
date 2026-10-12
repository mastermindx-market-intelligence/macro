"""test_sni_us_stress.py — US/Mag-7 science stress set (synthetic data only)."""
import copy
import datetime
import math
import random
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/us_stress"),
)

from stress_set import (  # noqa: E402
    AuthorityMap,
    check_profile,
    hist_vol_normalize,
    load_closes_from_parquet,
    load_profiles,
    rolling_beta_residual,
    simple_returns,
    stress_table,
    _summary,
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


def _business_days(start, end):
    out = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def _closes(rng, n=400, sigma=0.01, start=100.0, start_date=None):
    px = start
    vals = [px]
    for _ in range(n - 1):
        px *= 1.0 + rng.gauss(0.0, sigma)
        vals.append(px)
    if start_date is None:
        start_date = datetime.date(2015, 1, 2)
    dates = []
    d = start_date
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return list(zip(dates, vals))


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


def _aligned_return_legs(stock_closes, bench_closes):
    stock_map = dict(simple_returns(stock_closes))
    bench_map = dict(simple_returns(bench_closes))
    shared = sorted(set(stock_map) & set(bench_map))
    return (
        [stock_map[d] for d in shared],
        [bench_map[d] for d in shared],
        shared,
    )


def _synth_profile(benches=("BENCH",)):
    return {
        "authority": {name: False for name in FLAGS},
        "canonical_issuer_id": None,
        "counters": {"x": {"security_id": None, "issuer_link": "UNRESOLVED"}},
        "stress_set": {
            "benchmarks": list(benches),
            "sector_etf": benches[0],
            "descriptive_only": True,
        },
    }


def _assert_no_nan(values):
    for x in values:
        if isinstance(x, float):
            assert math.isfinite(x)


def _try_pandas():
    try:
        import pandas as pd
        import pyarrow  # noqa: F401

        return pd
    except ImportError:
        return None


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
    with pytest.raises(ValueError, match="stress profiles never carry identity ids"):
        bad["authority"]["rank_authority"] = True
    bad2 = copy.deepcopy(profiles[one_key])
    bad2["authority"] = dict(bad2["authority"])
    bad2["authority"]["rank_authority"] = True
    with pytest.raises(ValueError, match="stress profiles never carry identity ids"):
        check_profile(bad2)
    with pytest.raises(ValueError, match="stress profiles never carry identity ids"):
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
    assert table["window"] == WINDOW
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
        for bench in benches:
            pair_count += 1
            stats = summaries[ticker][bench]
            stock_al, bench_al, shared = _aligned_return_legs(closes[ticker], closes[bench])
            resid = rolling_beta_residual(stock_al, bench_al, window=WINDOW)
            normed = hist_vol_normalize(resid, window=WINDOW)
            n_non = sum(1 for x in normed if x is not None)
            assert stats["n"] == n_non
            assert stats["n"] > 0
            assert stats["n_shared_dates"] == len(shared)
            assert stats["first_date"] is not None
            assert stats["last_date"] is not None
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


def test_r1_01_date_alignment(tmp_path):
    rng = random.Random(RNG_SEED)
    stock_dates = _business_days(datetime.date(2020, 1, 2), datetime.date(2020, 12, 31))
    bench_dates = _business_days(datetime.date(2019, 1, 2), datetime.date(2020, 12, 31))
    bench_px = 100.0
    bench_closes = []
    for i, d in enumerate(bench_dates):
        if i > 0:
            bench_px *= 1.0 + rng.gauss(0.0, 0.01)
        bench_closes.append((d, bench_px))
    bench_by_date = dict(bench_closes)
    stock_px = 100.0
    stock_closes = [(stock_dates[0], stock_px)]
    for i in range(1, len(stock_dates)):
        d = stock_dates[i]
        prev_d = stock_dates[i - 1]
        b_ret = bench_by_date[d] / bench_by_date[prev_d] - 1.0
        stock_px = stock_px * (1.0 + 2.0 * b_ret)
        stock_closes.append((d, stock_px))
    profiles = {"STOCK": _synth_profile(("BENCH",))}
    table = stress_table(
        profiles,
        {"STOCK": stock_closes, "BENCH": bench_closes},
        window=WINDOW,
    )
    stats = table["summaries"]["STOCK"]["BENCH"]
    stock_al, bench_al, shared = _aligned_return_legs(stock_closes, bench_closes)
    resid = rolling_beta_residual(stock_al, bench_al, window=WINDOW)
    defined = [x for x in resid if x is not None]
    assert defined
    for x in defined:
        assert abs(x) < 1e-9
    assert stats["n"] > 0

    trimmed = bench_closes[50:]
    table2 = stress_table(
        profiles,
        {"STOCK": stock_closes, "BENCH": trimmed},
        window=WINDOW,
    )
    stock_al2, bench_al2, shared2 = _aligned_return_legs(stock_closes, trimmed)
    resid2 = rolling_beta_residual(stock_al2, bench_al2, window=WINDOW)
    by_date = {shared[i]: resid[i] for i in range(len(shared)) if resid[i] is not None}
    by_date2 = {shared2[i]: resid2[i] for i in range(len(shared2)) if resid2[i] is not None}
    common = sorted(set(by_date) & set(by_date2))
    assert common
    for d in common:
        assert abs(by_date[d] - by_date2[d]) < 1e-12
    assert table2["summaries"]["STOCK"]["BENCH"]["n"] > 0

    with pytest.raises(ValueError):
        simple_returns([("2020-01-03", 1.0), ("2020-01-02", 1.1)])
    with pytest.raises(ValueError):
        simple_returns([("2020-01-02", 1.0), ("2020-01-02", 1.1)])

    pd = _try_pandas()
    if pd is not None:
        idx = pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-06"])
        df = pd.DataFrame(
            {
                "close_price": [100.0, 101.0, 102.0],
                "close": [100.0, 101.0, 102.0],
                "volume": [1, 1, 1],
            },
            index=idx,
        )
        path = tmp_path / "dated.parquet"
        df.to_parquet(path)
        loaded = load_closes_from_parquet(path)
        assert loaded == [
            ("2020-01-02", 100.0),
            ("2020-01-03", 101.0),
            ("2020-01-06", 102.0),
        ]
        nodate = tmp_path / "nodate.parquet"
        pd.DataFrame({"close": [1.0, 2.0], "volume": [1, 1]}).to_parquet(nodate)
        assert load_closes_from_parquet(nodate) is None
        datecol = tmp_path / "datecol.parquet"
        pd.DataFrame(
            {"Date": ["2020-01-02", "2020-01-03"], "close": [10.0, 11.0]}
        ).to_parquet(datecol)
        assert load_closes_from_parquet(datecol) == [
            ("2020-01-02", 10.0),
            ("2020-01-03", 11.0),
        ]
        dup = tmp_path / "dup.parquet"
        pd.DataFrame(
            {"close": [1.0, 2.0]},
            index=pd.DatetimeIndex(["2020-01-02", "2020-01-02"]),
        ).to_parquet(dup)
        with pytest.raises(ValueError):
            load_closes_from_parquet(dup)


def test_r1_02_gaps_never_bridged(tmp_path):
    d1, d2, d3, d4 = "2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"
    closes = [(d1, 100.0), (d2, float("nan")), (d3, 102.0), (d4, 103.0)]
    rets = simple_returns(closes)
    by_date = dict(rets)
    assert set(by_date) == {d2, d3, d4}
    assert by_date[d2] is None
    assert by_date[d3] is None
    assert by_date[d4] == pytest.approx(103.0 / 102.0 - 1.0)
    none_closes = [(d1, 100.0), (d2, None), (d3, 102.0), (d4, 103.0)]
    none_rets = dict(simple_returns(none_closes))
    assert none_rets[d2] is None
    assert none_rets[d3] is None
    assert none_rets[d4] == pytest.approx(103.0 / 102.0 - 1.0)

    pd = _try_pandas()
    if pd is not None:
        idx = pd.DatetimeIndex([d1, d2, d3, d4])
        df = pd.DataFrame(
            {
                "close_price": [100.0, float("nan"), 102.0, 103.0],
                "close": [100.0, float("nan"), 102.0, 103.0],
                "volume": [1, 1, 1, 1],
            },
            index=idx,
        )
        path = tmp_path / "gapped.parquet"
        df.to_parquet(path)
        loaded = load_closes_from_parquet(path)
        assert [row[0] for row in loaded] == [d1, d2, d3, d4]
        assert loaded[1][1] is None
        loaded_rets = dict(simple_returns(loaded))
        assert loaded_rets[d2] is None
        assert loaded_rets[d3] is None
        assert loaded_rets[d4] == pytest.approx(103.0 / 102.0 - 1.0)


def test_r1_03_nonfinite_nonpositive_closes():
    nan_rets = simple_returns([1.0, float("nan"), 2.0])
    assert nan_rets == [None, None]
    inf_rets = simple_returns([1.0, float("inf"), 2.0])
    assert inf_rets == [None, None]
    neg_rets = simple_returns([1.0, -1.0, 2.0])
    assert neg_rets == [None, None]
    zero_rets = simple_returns([1.0, 0.0, 2.0])
    assert zero_rets == [None, None]
    for series in (nan_rets, inf_rets, neg_rets, zero_rets):
        _assert_no_nan(series)
        assert all(x is None for x in series)

    mixed = [0.01, float("nan"), 0.02] + [0.01] * 80
    bench = [0.01] * len(mixed)
    resid = rolling_beta_residual(mixed, bench, window=5)
    _assert_no_nan([x for x in resid if x is not None])
    assert all(x is None or math.isfinite(x) for x in resid)

    stats = _summary([None, float("nan"), 1.0, float("inf"), float("-inf")])
    assert stats["n"] == 1
    assert stats["mean"] == 1.0
    assert stats["min"] == 1.0
    assert stats["max"] == 1.0
    assert stats["last"] == 1.0
    for key, value in stats.items():
        if value is None:
            continue
        if isinstance(value, float):
            assert math.isfinite(value)

    dates = _business_days(datetime.date(2020, 1, 2), datetime.date(2020, 6, 30))
    stock = []
    bench = []
    px_s = 100.0
    px_b = 100.0
    rng = random.Random(RNG_SEED)
    for i, d in enumerate(dates):
        if i == 10:
            stock.append((d, float("nan")))
            bench.append((d, px_b))
            continue
        if i > 0:
            r = rng.gauss(0.0, 0.01)
            px_s *= 1.0 + r
            px_b *= 1.0 + r * 0.5
        stock.append((d, px_s))
        bench.append((d, px_b))
    table = stress_table(
        {"STOCK": _synth_profile(("BENCH",))},
        {"STOCK": stock, "BENCH": bench},
        window=20,
    )
    out = table["summaries"]["STOCK"]["BENCH"]
    for key in ("n", "mean", "stdev", "min", "max", "last"):
        val = out[key]
        if val is None:
            continue
        assert math.isfinite(float(val))


def test_r1_04_authority_must_be_literal_false():
    with pytest.raises(ValueError):
        check_profile({"authority": {"trade_authority": 1}})
    with pytest.raises(ValueError):
        check_profile({"authority": {"trade_authority": "true"}})
    am = AuthorityMap((name, False) for name in FLAGS)
    with pytest.raises(ValueError):
        am |= {"trade_authority": True}
    with pytest.raises(ValueError):
        am.update({"rank_authority": 1})
    copied = am.copy()
    assert isinstance(copied, AuthorityMap)
    with pytest.raises(ValueError):
        copied["gate_authority"] = True
    with pytest.raises(ValueError):
        check_profile({"authority": {"trade_authority": None}})
    with pytest.raises(ValueError):
        check_profile({"authority": {"trade_authority": 0}})


def test_r1_05_identity_ids_at_any_depth():
    with pytest.raises(ValueError):
        check_profile({"authority": {}, "counters": {"x": {"security_id": "SEC-123"}}})
    with pytest.raises(ValueError):
        check_profile({"authority": {}, "counters": {"x": {"issuer_link": "ISS-9"}}})
    with pytest.raises(ValueError):
        check_profile({"authority": {}, "nested": {"canonical_issuer_id": "ISS-1"}})
    loaded = load_profiles(PROFILES_DIR)
    assert len(loaded) == 7
    assert set(loaded) == set(TICKERS)


def test_r1_06_reproducibility_fields():
    rng = random.Random(RNG_SEED)
    profiles = load_profiles(PROFILES_DIR)
    closes = {name: _closes(rng) for name in _needed_names(profiles)}
    table = stress_table(profiles, closes, window=WINDOW)
    assert table["window"] == WINDOW
    assert table["descriptive_only"] is True
    assert table["causal_claims"] == "none"
    for flag in FLAGS:
        assert table["authority_flags"][flag] is False
    for ticker, benches in table["summaries"].items():
        for bench, stats in benches.items():
            assert "first_date" in stats
            assert "last_date" in stats
            assert "n_shared_dates" in stats
            assert stats["n"] > 0
            assert stats["first_date"] is not None
            assert stats["last_date"] is not None
            assert stats["n_shared_dates"] >= stats["n"]
            assert stats["first_date"] <= stats["last_date"]
            _assert_no_nan(
                [stats[k] for k in ("mean", "stdev", "min", "max", "last") if stats[k] is not None]
            )
    missing = stress_table(profiles, {}, window=WINDOW)
    assert missing["descriptive_only"] is True
    assert missing["causal_claims"] == "none"
    assert missing["window"] == WINDOW
    for flag in FLAGS:
        assert missing["authority_flags"][flag] is False
    one = next(iter(missing["summaries"].values()))
    empty = next(iter(one.values()))
    assert empty["n"] == 0
    assert empty["first_date"] is None
    assert empty["last_date"] is None
    assert empty["n_shared_dates"] == 0
