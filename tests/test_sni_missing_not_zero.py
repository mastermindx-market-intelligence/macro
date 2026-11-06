"""A10 evidence: a missing SNI numeric is never 0, never forward-filled.

Seeded properties over SEEDS = range(200). Synthetic fixtures only. This
module does not mint identity ids and does not feed a rank, gate, size,
signal, escalation, or trade path. Authority flags stay literal false.

Every assertion failure includes (seed, case).
"""
from __future__ import annotations

import math
import random
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/us_stress"))
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/common"))
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))
sys.path.insert(0, str(ROOT))

from stress_set import (  # noqa: E402
    _close_or_none,
    _dropped_return_dates,
    _inner_join_returns,
    _is_bad_close,
    _is_defined_number,
    _simple_return_values,
    _summary,
    _window_defined,
    hist_vol_normalize,
    rolling_beta_residual,
    simple_returns,
    stress_table,
)
from s1_data import InjectableStore, closes_from_frame  # noqa: E402
from s1_decomposition import (  # noqa: E402
    ABSTAIN_MISSING_ENDPOINT as S1_ABSTAIN_MISSING_ENDPOINT,
    daily_log_returns,
    window_log_ret,
)
from sni_inference import (  # noqa: E402
    ABSTAIN_NO_EPISODES,
    InferenceResult,
    binom_p_one_sided_greater,
    binom_p_two_sided,
    cluster_mean_ci,
    label_for,
    sign_test_two_sided,
    wilson_ci,
)

SEEDS = range(200)
FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
_BAD_KIND_NAMES = ("none", "nan", "pinf", "ninf", "zero", "neg")
_RTOL_RET = 1e-12


def _fail(seed, case, msg):
    raise AssertionError("(%r, %r): %s" % (seed, case, msg))


def _is_none_or_nan(x):
    if x is None:
        return True
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)) and not math.isfinite(float(x)):
        return True
    return False


def _iso_weekdays(n, start=date(2018, 1, 2)):
    out = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _date_weekdays(n, start=date(2018, 1, 2)):
    out = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _good_close_series(rng, n):
    px = rng.uniform(20.0, 400.0)
    out = [px]
    for _ in range(n - 1):
        px *= math.exp(rng.gauss(0.0, 0.012))
        px = max(px, 1e-3)
        out.append(float(px))
    return out


def _bad_value(rng, kind):
    if kind == "none":
        return None
    if kind == "nan":
        return float("nan")
    if kind == "pinf":
        return float("inf")
    if kind == "ninf":
        return float("-inf")
    if kind == "zero":
        return 0.0
    if kind == "neg":
        return -abs(rng.uniform(0.05, 80.0))
    raise ValueError(kind)


def _inject_bad_closes(rng, closes):
    n = len(closes)
    frac = rng.uniform(0.0, 0.30)
    n_bad = int(n * frac)
    idxs = rng.sample(range(n), n_bad) if n_bad else []
    out = list(closes)
    kinds = {}
    for i in idxs:
        kind = rng.choice(_BAD_KIND_NAMES)
        out[i] = _bad_value(rng, kind)
        kinds[i] = kind
    return out, kinds


def _n_adjacent_good(closes):
    n = 0
    for i in range(1, len(closes)):
        if not _is_bad_close(closes[i - 1]) and not _is_bad_close(closes[i]):
            n += 1
    return n


def _n_defined_returns(rets):
    n = 0
    for r in rets:
        val = r[1] if isinstance(r, tuple) else r
        if val is None:
            continue
        if isinstance(val, float) and not math.isfinite(val):
            continue
        n += 1
    return n


def _call_simple_returns(closes, seed, case):
    try:
        return simple_returns(closes)
    except TypeError as exc:
        pytest.fail(
            "mutant kill: TypeError on missing close (seed=%r, case=%r): %s"
            % (seed, case, exc)
        )


def _synth_profile(benches=("BENCH",)):
    return {
        "authority": {name: False for name in FLAGS},
        "stress_set": {
            "benchmarks": list(benches),
            "sector_etf": benches[0],
            "descriptive_only": True,
        },
    }


def _counterfactual_zero_fill(seq):
    out = []
    for x in seq:
        if _is_defined_number(x):
            out.append(float(x))
        else:
            out.append(0.0)
    return out


# ---------------------------------------------------------------------------
# 01 / 02 — simple returns never zero-fill or forward-fill
# ---------------------------------------------------------------------------

def test_mnz_01_simple_returns_never_zero_fill():
    """Missing/bad close -> None return; never 0.0, never -1.0, never gap-span.

    Pin: `_simple_return_values` / `simple_returns` leave the slot in the
    series and set touching returns to None. The next finite positive close
    does not bridge across the gap (stress_set module docstring).
    """
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(5, 400)
        good = _good_close_series(rng, n)
        closes, kinds = _inject_bad_closes(rng, good)
        dated = [(d, c) for d, c in zip(_iso_weekdays(n), closes)]
        for case, series in (("undated", closes), ("dated", dated)):
            rets = _call_simple_returns(series, seed, case)
            if case == "undated":
                values = rets
            else:
                values = [r[1] for r in rets]
            if len(values) != n - 1:
                _fail(seed, case, "return length %s != %s" % (len(values), n - 1))
            for i, r in enumerate(values):
                c0 = closes[i]
                c1 = closes[i + 1]
                bad = _is_bad_close(c0) or _is_bad_close(c1)
                if bad:
                    if r is not None:
                        _fail(
                            seed,
                            case,
                            "touching bad close at i=%s kinds=%s -> %r (want None)"
                            % (i, (kinds.get(i), kinds.get(i + 1)), r),
                        )
                    if r == 0.0 or r == -1.0:
                        _fail(seed, case, "bad close produced %r at i=%s" % (r, i))
                else:
                    expected = float(c1) / float(c0) - 1.0
                    if r is None or not math.isfinite(float(r)):
                        _fail(seed, case, "good pair i=%s yielded %r" % (i, r))
                    if abs(float(r) - expected) > _RTOL_RET:
                        _fail(
                            seed,
                            case,
                            "good pair i=%s got %r want %r" % (i, r, expected),
                        )
            # Gap-span probe: a None between two goods must not become
            # last_good -> next_good.
            for i in range(1, n - 1):
                if kinds.get(i) is None:
                    continue
                if _is_bad_close(closes[i]) and not _is_bad_close(closes[i - 1]) and not _is_bad_close(closes[i + 1]):
                    # return ending on i (values[i-1]) and starting from i (values[i])
                    if values[i - 1] is not None or values[i] is not None:
                        _fail(
                            seed,
                            case,
                            "gap spanned around missing i=%s: %r %r"
                            % (i, values[i - 1], values[i]),
                        )
                    spanned = float(closes[i + 1]) / float(closes[i - 1]) - 1.0
                    if values[i] == spanned or values[i - 1] == spanned:
                        _fail(seed, case, "gap-spanning return at i=%s" % i)


def test_mnz_02_no_forward_fill():
    """Missing close at t is not a 0.0 return; defined count = adjacent goods."""
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(5, 400)
        good = _good_close_series(rng, n)
        # Guarantee at least one interior missing close so the property fires.
        hole = rng.randint(1, n - 2)
        kind = rng.choice(_BAD_KIND_NAMES)
        closes = list(good)
        closes[hole] = _bad_value(rng, kind)
        extra, extra_kinds = _inject_bad_closes(rng, closes)
        if hole not in extra_kinds:
            extra[hole] = closes[hole]
        closes = extra
        case = "hole=%s kind=%s n=%s" % (hole, kind, n)
        rets = _call_simple_returns(closes, seed, case)
        n_def = _n_defined_returns(rets)
        n_adj = _n_adjacent_good(closes)
        if n_def != n_adj:
            _fail(
                seed,
                case,
                "defined returns %s != adjacent good pairs %s" % (n_def, n_adj),
            )
        # Return ending on t=hole is rets[hole-1].
        r_at_hole = rets[hole - 1]
        if r_at_hole is not None:
            _fail(seed, case, "return at missing t=%s is %r" % (hole, r_at_hole))
        if r_at_hole == 0.0:
            _fail(seed, case, "forward-fill zero return at t=%s" % hole)
        dated = [(d, c) for d, c in zip(_iso_weekdays(n), closes)]
        drets = _call_simple_returns(dated, seed, case + "/dated")
        dr_at_hole = drets[hole - 1][1]
        if dr_at_hole is not None or dr_at_hole == 0.0:
            _fail(seed, case, "dated return at missing t=%s is %r" % (hole, dr_at_hole))
        if _n_defined_returns(drets) != n_adj:
            _fail(seed, case, "dated defined count drifted")


# ---------------------------------------------------------------------------
# 03 — summary n excludes missing
# ---------------------------------------------------------------------------

def test_mnz_03_summary_n_excludes_missing():
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(1, 250)
        values = [rng.gauss(0.0, 1.0) for _ in range(n)]
        # Keep some genuine zeros so a real 0 is counted, a missing is not.
        for i in range(n):
            if rng.random() < 0.05:
                values[i] = 0.0
        n_inject = rng.randint(0, max(1, n // 2))
        idxs = rng.sample(range(n), n_inject) if n_inject else []
        for i in idxs:
            values[i] = None if rng.random() < 0.5 else float("nan")
        case = "n=%s injected=%s" % (n, len(idxs))
        stats = _summary(values)
        defined = [float(x) for x in values if _is_defined_number(x)]
        if stats["n"] != len(defined):
            _fail(seed, case, "n=%s want %s" % (stats["n"], len(defined)))
        if not defined:
            if stats["mean"] is not None or stats["stdev"] is not None:
                _fail(seed, case, "empty summary not None: %r" % stats)
            continue
        want_mean = statistics.mean(defined)
        if abs(stats["mean"] - want_mean) > 1e-12:
            _fail(seed, case, "mean %r want %r" % (stats["mean"], want_mean))
        if len(defined) == 1:
            if stats["stdev"] is not None:
                _fail(seed, case, "stdev for n=1 is %r" % stats["stdev"])
        else:
            want_sd = statistics.stdev(defined)
            if stats["stdev"] is None or abs(stats["stdev"] - want_sd) > 1e-12:
                _fail(seed, case, "stdev %r want %r" % (stats["stdev"], want_sd))
        # `_summary` does not disclose a missing count (no n_missing key).
        if "n_missing" in stats:
            if stats["n_missing"] != n - len(defined):
                _fail(seed, case, "n_missing mismatch")


# ---------------------------------------------------------------------------
# 04 — rolling beta / hist vol respect missing windows
# ---------------------------------------------------------------------------

def test_mnz_04_rolling_beta_and_vol_respect_missing():
    """Pin: `_window_defined` is all(_is_defined_number); a hole skips t (None).

    A window that contains a missing value never yields a finite number that
    matches the counterfactual with the hole replaced by 0.0.
    """
    # Direct pin of `_window_defined`.
    if _window_defined([]) is not True:
        _fail(0, "empty", "_window_defined([]) is not True (all([]) convention)")
    if _window_defined([0.0, 0.0]) is not True:
        _fail(0, "zeros", "defined zeros must pass _window_defined")
    if _window_defined([1.0, None, 2.0]) is not False:
        _fail(0, "none", "None must fail _window_defined")
    if _window_defined([1.0, float("nan")]) is not False:
        _fail(0, "nan", "NaN must fail _window_defined")
    if _window_defined([float("inf")]) is not False:
        _fail(0, "inf", "inf must fail _window_defined")

    window = 63
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(window + 8, window + 180)
        bench = [rng.gauss(0.0, 0.01) for _ in range(n)]
        stock = [1.3 * b + rng.gauss(0.0, 0.003) for b in bench]
        n_holes = rng.randint(1, 6)
        holes = rng.sample(range(n), n_holes)
        kinds = [_BAD_KIND_NAMES[rng.randrange(4)] for _ in holes]  # none/nan/pinf/ninf
        for i, kind in zip(holes, kinds):
            stock[i] = _bad_value(rng, kind)
            if rng.random() < 0.4:
                bench[i] = _bad_value(rng, kind)
        case = "n=%s holes=%s" % (n, holes)
        resid = rolling_beta_residual(stock, bench, window=window)
        vol = hist_vol_normalize(resid, window=window)
        zstock = _counterfactual_zero_fill(stock)
        zbench = _counterfactual_zero_fill(bench)
        zresid = rolling_beta_residual(zstock, zbench, window=window)

        hole_set = set(holes)
        for t, val in enumerate(resid):
            s_win = stock[t - window : t] if t >= window else None
            b_win = bench[t - window : t] if t >= window else None
            win_has_hole = False
            if t < window:
                if val is not None:
                    _fail(seed, case, "t=%s < window yielded %r" % (t, val))
                continue
            if not _window_defined(s_win) or not _window_defined(b_win):
                win_has_hole = True
            if not _is_defined_number(stock[t]) or not _is_defined_number(bench[t]):
                win_has_hole = True
            if win_has_hole:
                if val is not None:
                    _fail(
                        seed,
                        case,
                        "t=%s window/point missing yielded finite %r" % (t, val),
                    )
                zval = zresid[t]
                if zval is not None and math.isfinite(float(zval)):
                    # Mutant that treats missing as 0 would have emitted zval.
                    if val == zval:
                        _fail(seed, case, "t=%s missing computed as zero-fill" % t)
            else:
                if val is not None and not math.isfinite(float(val)):
                    _fail(seed, case, "t=%s non-finite residual %r" % (t, val))

        for t, val in enumerate(vol):
            if t < window:
                if val is not None:
                    _fail(seed, case, "vol t=%s < window yielded %r" % (t, val))
                continue
            win = resid[t - window : t]
            if not _window_defined(win) or not _is_defined_number(resid[t]):
                if val is not None:
                    _fail(
                        seed,
                        case,
                        "vol t=%s missing window yielded %r" % (t, val),
                    )
            elif val is not None and not math.isfinite(float(val)):
                _fail(seed, case, "vol t=%s non-finite %r" % (t, val))

        # hist_vol on a series with a hole: never a finite number at those t
        # equal to the zero-filled counterpart.
        series = [rng.gauss(0.0, 0.02) for _ in range(n)]
        h = rng.randrange(n)
        series[h] = None if rng.random() < 0.5 else float("nan")
        got = hist_vol_normalize(series, window=window)
        zeroed = hist_vol_normalize(_counterfactual_zero_fill(series), window=window)
        for t, val in enumerate(got):
            if t < window:
                continue
            touched = (h in range(t - window, t)) or (h == t)
            if touched:
                if val is not None:
                    _fail(seed, case, "hist_vol t=%s hole yielded %r" % (t, val))
                if val == 0.0:
                    _fail(seed, case, "hist_vol t=%s hole became 0" % t)
                if zeroed[t] is not None and val == zeroed[t]:
                    _fail(seed, case, "hist_vol t=%s used zero-fill" % t)
        del hole_set  # silence unused if holes only used via list


# ---------------------------------------------------------------------------
# 05 — stress_table discloses calendar gaps
# ---------------------------------------------------------------------------

def test_mnz_05_stress_table_discloses():
    window = 8
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(window * 4, window * 12)
        start = date(2020, 1, 2)
        all_days = _iso_weekdays(n + 12, start)
        stock_idx = sorted(rng.sample(range(n + 8), n))
        bench_idx = sorted(rng.sample(range(n + 8), n))
        # Guarantee a calendar mismatch on at least one side.
        if set(stock_idx) == set(bench_idx):
            bench_idx = sorted(set(bench_idx) | {n + 8})
            bench_idx = bench_idx[:n] if len(bench_idx) >= n else bench_idx
            if set(stock_idx) == set(bench_idx):
                stock_idx = stock_idx[:-1] + [n + 9 if n + 9 < len(all_days) else 0]
                stock_idx = sorted(set(stock_idx))
        stock_dates = [all_days[i] for i in stock_idx if i < len(all_days)]
        bench_dates = [all_days[i] for i in bench_idx if i < len(all_days)]
        if len(stock_dates) < window * 2 or len(bench_dates) < window * 2:
            stock_dates = all_days[:n]
            bench_dates = all_days[3 : n + 3]
        stock_px = _good_close_series(rng, len(stock_dates))
        bench_px = _good_close_series(rng, len(bench_dates))
        # Value-gap on each leg (same calendar slot if shared).
        s_hole = rng.randrange(1, len(stock_px) - 1)
        b_hole = rng.randrange(1, len(bench_px) - 1)
        stock_px[s_hole] = _bad_value(rng, rng.choice(_BAD_KIND_NAMES))
        bench_px[b_hole] = _bad_value(rng, rng.choice(_BAD_KIND_NAMES))
        stock_closes = list(zip(stock_dates, stock_px))
        bench_closes = list(zip(bench_dates, bench_px))
        profile = {"STOCK": _synth_profile(("BENCH",))}
        closes_map = {"STOCK": stock_closes, "BENCH": bench_closes}
        case = "nS=%s nB=%s s_hole=%s b_hole=%s" % (
            len(stock_closes),
            len(bench_closes),
            s_hole,
            b_hole,
        )

        stock_rets = simple_returns(stock_closes)
        bench_rets = simple_returns(bench_closes)
        want_dropped_s, want_dropped_b = _dropped_return_dates(stock_rets, bench_rets)
        join_dates, stock_al, bench_al = _inner_join_returns(stock_rets, bench_rets)

        none_table = stress_table(profile, closes_map, window=window, join_policy=None)
        none_stats = none_table["summaries"]["STOCK"]["BENCH"]
        if want_dropped_s or want_dropped_b:
            if none_stats.get("reason") != "DATE_JOIN_MISMATCH":
                _fail(seed, case, "join_policy None reason=%r" % none_stats.get("reason"))
            if none_stats.get("dropped_stock_dates") != want_dropped_s:
                _fail(
                    seed,
                    case,
                    "dropped_stock_dates %r want %r"
                    % (none_stats.get("dropped_stock_dates"), want_dropped_s),
                )
            if none_stats.get("dropped_bench_dates") != want_dropped_b:
                _fail(
                    seed,
                    case,
                    "dropped_bench_dates %r want %r"
                    % (none_stats.get("dropped_bench_dates"), want_dropped_b),
                )
            if none_stats.get("n") != 0 or none_stats.get("mean") is not None:
                _fail(seed, case, "mismatch did not abstain: %r" % none_stats)
        else:
            # Identical return calendars: no DATE_JOIN_MISMATCH. Value holes
            # stay as None returns and are excluded from n.
            if none_stats.get("reason") == "DATE_JOIN_MISMATCH":
                _fail(seed, case, "false DATE_JOIN_MISMATCH on identical calendars")

        inner_table = stress_table(
            profile, closes_map, window=window, join_policy="inner"
        )
        inner = inner_table["summaries"]["STOCK"]["BENCH"]
        if inner.get("dropped_stock_dates") != want_dropped_s:
            _fail(seed, case, "inner dropped_stock_dates mismatch")
        if inner.get("dropped_bench_dates") != want_dropped_b:
            _fail(seed, case, "inner dropped_bench_dates mismatch")
        resid = rolling_beta_residual(stock_al, bench_al, window=window)
        normed = hist_vol_normalize(resid, window=window)
        hand = _summary(normed, dates=join_dates)
        if inner.get("n") != hand["n"]:
            _fail(seed, case, "inner n=%s want %s" % (inner.get("n"), hand["n"]))
        if inner.get("n_shared_dates") != len(stock_al):
            _fail(seed, case, "n_shared_dates %s want %s" % (
                inner.get("n_shared_dates"), len(stock_al)))
        if hand["mean"] is None:
            if inner.get("mean") is not None:
                _fail(seed, case, "inner mean %r want None" % inner.get("mean"))
        else:
            if inner.get("mean") is None or abs(inner["mean"] - hand["mean"]) > 1e-12:
                _fail(seed, case, "inner mean %r want %r" % (inner.get("mean"), hand["mean"]))
        if hand["stdev"] is None:
            if inner.get("stdev") is not None:
                _fail(seed, case, "inner stdev %r want None" % inner.get("stdev"))
        else:
            if inner.get("stdev") is None or abs(inner["stdev"] - hand["stdev"]) > 1e-12:
                _fail(seed, case, "inner stdev mismatch")
        if inner.get("join_policy") != "inner":
            _fail(seed, case, "join_policy not recorded")

        for flag in FLAGS:
            if none_table["authority_flags"][flag] is not False:
                _fail(seed, case, "authority flag %s not false" % flag)
            if inner_table["authority_flags"][flag] is not False:
                _fail(seed, case, "inner authority flag %s not false" % flag)


# ---------------------------------------------------------------------------
# 06 — S1 in-memory store + daily/window returns
# ---------------------------------------------------------------------------

def test_mnz_06_s1_frame_missing():
    """NaN close through InjectableStore never yields a 0 return for that date.

    `closes_from_frame` drops None/NaN from the date->close map and does not
    expose a drop count (finding MNZ-F1 in the review). The never-zero
    contract is the assertion here.
    """
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(8, 80)
        dates = _date_weekdays(n, date(2019, 1, 2) + timedelta(days=rng.randint(0, 400)))
        px = _good_close_series(rng, n)
        hole = rng.randint(1, n - 2)
        kind = rng.choice(("nan", "pinf", "ninf", "zero", "neg"))
        px[hole] = _bad_value(rng, kind)
        frames = {"synthetic.parquet": {"Date": list(dates), "close": list(px)}}
        store = InjectableStore(frames)
        case = "hole=%s kind=%s n=%s" % (hole, kind, n)
        try:
            got_dates, cols = store.frame("synthetic.parquet", ["close"])
        except (TypeError, ValueError) as exc:
            # None in the frame raises; NaN/inf/0/neg must not.
            if kind == "none":
                continue
            _fail(seed, case, "frame raised %s: %s" % (type(exc).__name__, exc))
        close_vals = cols["close"]
        _, cmap = closes_from_frame(got_dates, close_vals)
        hole_d = dates[hole]
        dly = daily_log_returns(cmap, got_dates)
        if hole_d in dly:
            ret = dly[hole_d]
            if ret == 0.0 or ret == -1.0:
                _fail(seed, case, "daily_log_returns[%s]=%r" % (hole_d, ret))
            # NaN dropped from cmap: date must not appear. inf/0/neg handled below.
            if kind == "nan":
                _fail(seed, case, "NaN date present in daily returns as %r" % ret)
        if kind == "nan":
            if hole_d in cmap:
                _fail(seed, case, "NaN close kept in map as %r" % cmap[hole_d])
            # Drop is silent: access_log has the frame call only.
            # Finding MNZ-F1: no n_dropped / exclusion log on the store.
        if kind in ("zero", "neg"):
            # daily_log_returns treats <=0 as a chain break, omits the date.
            if hole_d in dly:
                _fail(seed, case, "non-positive close produced return %r" % dly[hole_d])
        w = window_log_ret(cmap, hole_d, dates[-1])
        if kind in ("nan", "zero", "neg"):
            if w is not None:
                _fail(seed, case, "window_log_ret on missing fill is %r" % w)
            if w == 0.0:
                _fail(seed, case, "window_log_ret zero-filled missing fill")
        # Next date after a NaN hole must not be a gap-span vs the previous good.
        if kind == "nan" and hole + 1 < n:
            nxt = dates[hole + 1]
            if nxt in dly and hole > 0:
                prev_good = dates[hole - 1]
                if prev_good in cmap and nxt in cmap:
                    spanned = math.log(cmap[nxt] / cmap[prev_good])
                    if abs(dly[nxt] - spanned) <= 1e-12:
                        _fail(seed, case, "S1 daily return spanned the NaN hole")
        # Public S1 missing-endpoint token still names the drop when the
        # close is absent from the map.
        if hole_d not in cmap:
            if window_log_ret(cmap, hole_d, dates[-1]) is not None:
                _fail(seed, case, "missing fill not None")
            # No visible count on the store.
            drop_tokens = [str(x) for x in store.access_log]
            if any("dropped" in t.lower() or "missing" in t.lower() for t in drop_tokens):
                pass  # would be the disclosure we want
            # MNZ-F1: access_log is [('frame', path, ('close',))] only.


# ---------------------------------------------------------------------------
# 07 — S2 event window missing close
# ---------------------------------------------------------------------------

def test_mnz_07_s2_window_missing():
    """Missing/bad endpoint close must abstain, never a 0 or -1 scored return.

    Idiom: `episode_excess` -> ABSTAIN_MISSING_ENDPOINT when `leg_return`
    is None (KeyError or falsy 0.0). NaN/inf currently bypass that guard.
    """
    pd = pytest.importorskip("pandas")
    from s2_outcomes import (  # noqa: WPS433
        ABSTAIN_MISSING_ENDPOINT,
        BABA_PATH,
        SPY_PATH,
        OutcomeEngine,
    )

    sess = pd.bdate_range("2020-01-02", periods=24).date.tolist()
    h = 5

    class _Loader:
        def __init__(self, baba, spy):
            self.baba = baba
            self.spy = spy

        def read_parquet(self, path, columns=None):
            return self.baba if path == BABA_PATH else self.spy

    def _df(closes):
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(sess),
                "close": list(closes),
                "close_price": list(closes),
            }
        )

    for seed in SEEDS:
        rng = random.Random(seed)
        baba = [100.0 + i + rng.uniform(-0.2, 0.2) for i in range(len(sess))]
        spy = [200.0 + 0.4 * i + rng.uniform(-0.1, 0.1) for i in range(len(sess))]
        hole = rng.randint(2, 12)
        kind = rng.choice(_BAD_KIND_NAMES + ("absent",))
        case = "hole=%s kind=%s s_us=%s" % (hole, kind, sess[hole])
        baba_m = list(baba)
        if kind == "absent":
            # Drop the fill date from the subject frame.
            keep = [i for i in range(len(sess)) if i != hole]
            baba_df = pd.DataFrame(
                {
                    "Date": pd.to_datetime([sess[i] for i in keep]),
                    "close": [baba_m[i] for i in keep],
                    "close_price": [baba_m[i] for i in keep],
                }
            )
        else:
            baba_m[hole] = _bad_value(rng, kind)
            baba_df = _df(baba_m)
        spy_df = _df(spy)
        eng = OutcomeEngine(_Loader(baba_df, spy_df))
        s_us = sess[hole]
        out = eng.episode_excess(s_us, h)
        subj = out.get("subject_ret")
        state = out.get("state")
        # Never a scored 0.0 / -1.0 from a missing/bad fill close.
        if subj == 0.0 or subj == -1.0:
            _fail(seed, case, "scored subject_ret=%r state=%r" % (subj, state))
        if state == "OK" and _is_none_or_nan(subj):
            _fail(seed, case, "OK with non-finite subject_ret=%r" % subj)
        if state not in (ABSTAIN_MISSING_ENDPOINT, "OK") and state not in (
            "ABSTAIN_RESOLVER_NONE",
            "ABSTAIN_FILL_MISMATCH",
        ):
            pass
        fill_ret = eng.leg_return(eng.baba_close, sess[hole], sess[min(hole + 5, len(sess) - 1)])
        if fill_ret == 0.0 or fill_ret == -1.0:
            _fail(seed, case, "leg_return=%r for kind=%s" % (fill_ret, kind))
        if kind in ("none", "nan", "pinf", "ninf", "zero", "neg", "absent"):
            if state == "OK" and fill_ret is not None and math.isfinite(float(fill_ret)):
                _fail(
                    seed,
                    case,
                    "bad close scored finite return %r state=%s" % (fill_ret, state),
                )
            # Required: excluded or abstained, never a zero return.
            if state == "OK":
                _fail(seed, case, "missing close scored state=OK ret=%r" % subj)
            if state != ABSTAIN_MISSING_ENDPOINT and fill_ret is not None:
                # Resolver mismatch is a named abstain; still not a score.
                if state not in ("ABSTAIN_RESOLVER_NONE", "ABSTAIN_FILL_MISMATCH"):
                    _fail(seed, case, "unabated state=%r ret=%r" % (state, subj))


# ---------------------------------------------------------------------------
# 08 — sni_inference NaN input
# ---------------------------------------------------------------------------

def test_mnz_08_inference_nan_input():
    """Each public sni_inference function: refuse or drop+disclose; never NaN-as-0."""
    keys = ["a", "a", "b", "b", "c", "c", "d", "d"]
    finite = [0.1, -0.2, 0.3, 0.05, -0.1, 0.2, 0.0, 0.4]
    zero_as_missing = [0.1, -0.2, 0.3, 0.05, -0.1, 0.2, 0.0, 0.0]
    # cluster_mean_ci with a trailing 0 is a real 0, not a missing. Contrast NaN.

    for seed in SEEDS:
        rng = random.Random(seed)
        case = "cluster_mean_ci"
        vals = list(finite)
        hole = rng.randrange(len(vals))
        kind = rng.choice(("nan", "pinf", "ninf"))
        vals[hole] = _bad_value(rng, kind)
        with pytest.raises(ValueError, match="finite real"):
            cluster_mean_ci(vals, keys, draws=50, seed=0)
        # None is also refused (not coerced to 0).
        vals_none = list(finite)
        vals_none[hole] = None
        with pytest.raises(ValueError, match="finite real"):
            cluster_mean_ci(vals_none, keys, draws=50, seed=0)

        # If NaN were 0, the estimate would equal the zero-substituted mean.
        substituted = list(finite)
        substituted[hole] = 0.0
        try:
            got = cluster_mean_ci(vals, keys, draws=50, seed=0)
        except ValueError:
            got = None
        else:
            zeroed = cluster_mean_ci(substituted, keys, draws=50, seed=0)
            if got.estimate == zeroed.estimate:
                _fail(seed, case, "NaN treated as 0 in cluster_mean_ci")

        # wilson_ci / binom / sign_test take ints; a float NaN is refused.
        with pytest.raises(ValueError):
            wilson_ci(float("nan"), 10)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            binom_p_one_sided_greater(3, 10, p0=float("nan"))
        with pytest.raises(ValueError):
            binom_p_two_sided(3, 10, p0=float("nan"))
        with pytest.raises(ValueError):
            sign_test_two_sided(0, 0)

        empty = cluster_mean_ci([], [])
        if empty.abstained is not True or empty.reason != ABSTAIN_NO_EPISODES:
            _fail(seed, "empty", "empty input did not abstain: %r" % empty)
        if empty.n_obs != 0:
            _fail(seed, "empty", "empty n_obs=%s" % empty.n_obs)

        w0 = wilson_ci(0, 0)
        if w0.abstained is not True or w0.n_obs != 0:
            _fail(seed, "wilson0", "n=0 not abstained")

        # label_for refuses a non-abstained NaN CI rather than treating it as 0.
        bogus = InferenceResult(
            estimate=0.0,
            ci_lo=float("nan"),
            ci_hi=0.9,
            n_obs=10,
            n_clusters=10,
            effective_n=10.0,
            method="wilson",
            abstained=False,
            reason=None,
            alpha=0.05,
            seed=None,
            draws=None,
        )
        with pytest.raises(ValueError, match="finite CI"):
            label_for(bogus, min_episodes=1)

        # Real zeros in the sample are counted (n_obs not reduced). Contrast missing.
        z = cluster_mean_ci(zero_as_missing, keys, draws=40, seed=1)
        if z.n_obs != 8:
            _fail(seed, "real-zero", "real 0 dropped from n_obs=%s" % z.n_obs)

    # `_close_or_none` pin (stress parquet path): non-finite -> None, never 0.
    if _close_or_none(None) is not None:
        _fail(0, "close_or_none", "None became %r" % _close_or_none(None))
    if _close_or_none(float("nan")) is not None:
        _fail(0, "close_or_none", "NaN became %r" % _close_or_none(float("nan")))
    if _close_or_none(float("inf")) is not None:
        _fail(0, "close_or_none", "inf became %r" % _close_or_none(float("inf")))
    if _close_or_none(0.0) != 0.0:
        _fail(0, "close_or_none", "real 0.0 was dropped")
    if _close_or_none(12.5) != 12.5:
        _fail(0, "close_or_none", "finite close lost")
