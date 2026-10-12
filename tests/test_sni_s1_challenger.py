"""test_sni_s1_challenger.py — a synthetic panel with characteristic-dependent
beta recovers Gamma; a below-threshold panel reports NOT ESTIMABLE with counts."""
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

from s1_challenger import (CHAR_NAMES, characteristics_at, estimability,  # noqa: E402
                           fit_gamma, gamma_design, rank_standardise)
from s1_data import InjectableStore  # noqa: E402
from s1_synth import sessions_us, walk  # noqa: E402
import s1_challenger as ch  # noqa: E402


def test_gamma_recovered_from_synthetic_rows():
    """Gamma is the pooled no-interaction-intercept OLS: rows are constructed
    directly as y = (g0 + g1*z_mom + g2*z_vol + g3*z_rev) * f with known g, so
    the fitter must recover it near-exactly. (The characteristic definitions
    and the rank standardisation are covered by their own tests.)"""
    rng = np.random.default_rng(7)
    gamma_true = np.array([0.5, 1.2, -0.8, 0.6])
    rows = []
    for _ in range(6000):
        zm, zv, zr = rng.uniform(-0.5, 0.5, 3)
        f = float(rng.normal(0.0, 0.01))
        y = (gamma_true[0] + gamma_true[1] * zm + gamma_true[2] * zv
             + gamma_true[3] * zr) * f
        rows.append({"y": y, "f": f,
                     "z": {"mom_12_1": float(zm), "vol_63": float(zv),
                           "rev_21": float(zr)}})
    gamma = fit_gamma(rows)
    assert np.allclose(gamma, gamma_true, atol=1e-6), gamma


def test_characteristics_match_definitions():
    dates = sessions_us(300)
    rng = np.random.default_rng(3)
    p, closes = 100.0, []
    rets = rng.normal(0.0, 0.01, size=len(dates))
    for i in range(len(dates)):
        p *= math.exp(rets[i])
        closes.append(p)
    t = dates[-1]
    ch = characteristics_at(dates, closes, t)
    assert ch is not None
    j = len(dates) - 1          # bars strictly before t: 0..j-1 == full list
    assert abs(ch["mom_12_1"] - math.log(closes[j - 22] / closes[j - 253])) < 1e-12
    assert abs(ch["rev_21"] - math.log(closes[j - 1] / closes[j - 22])) < 1e-12
    lr = np.diff(np.log(np.asarray(closes[j - 64:j])))
    assert abs(ch["vol_63"] - float(np.std(lr, ddof=1))) < 1e-12
    assert set(ch) == set(CHAR_NAMES)
    assert characteristics_at(dates[:100], closes[:100], dates[99]) is None


def test_rank_standardise_bounds():
    vals = {"a": 3.0, "b": 1.0, "c": 2.0}
    z = rank_standardise(vals)
    assert z == {"a": 0.5, "b": -0.5, "c": 0.0}
    assert all(-0.5 <= v <= 0.5 for v in z.values())


def test_gamma_design_shape():
    row = gamma_design(0.01, 0.02, {"mom_12_1": 0.5, "vol_63": -0.5, "rev_21": 0.0})
    assert row == [0.02, 0.01, -0.01, 0.0]


def test_below_threshold_not_estimable_with_counts():
    universe = {"admitted_count": 12}
    est = estimability(universe, {})
    assert est["estimable"] is False
    assert est["admitted_names"] == 12
    assert est["characteristics"] == 3
    assert est["train_months_with_valid_cross_section"] == 0
    assert est["checks"]["admitted_names_ge_30"] is False
    assert est["checks"]["train_months_ge_60"] is False
    assert est["thresholds"] == {"min_admitted_names": 30, "n_characteristics": 3,
                                 "min_train_months": 60}


def test_universe_builder_stops_at_cap_and_records_reasons(tmp_path):
    from s1_challenger import MAX_ADMITTED, build_universe, path_sort_key

    n = 3800                                  # 2011-12 .. 2026-10 on real sessions
    dates = sessions_us(n, start=date(2011, 12, 1))
    frames = {}
    paths = []
    for i in range(MAX_ADMITTED + 40):
        p = f"data/yahoo/T{i:03d}.parquet"
        paths.append(p)
        frames[p] = {"Date": list(dates), "close": walk(dates, seed=i)}
    # late starter and a stale file
    frames["data/yahoo/LATE.parquet"] = {"Date": list(dates[-100:]),
                                         "close": walk(dates[-100:], seed=999)}
    frames["data/yahoo/SPY.parquet"] = {"Date": list(dates), "close": walk(dates, 1)}
    store = InjectableStore(frames)
    sessions = list(dates)
    u = build_universe(store, lambda p: "blob", sessions)
    assert u["admitted_count"] == MAX_ADMITTED
    assert u["rejected_by_reason"]["skipped_benchmark_or_subject"] == 1
    assert u["rejected_by_reason"]["late_first_date"] == 1
    keys = [a["path"] for a in u["admitted"]]
    assert keys == sorted(keys, key=path_sort_key)
