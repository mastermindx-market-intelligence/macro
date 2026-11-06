"""Adversarial randomized properties for sealed S1 residual modules.

Consumes s1_stats, s1_infoleak, and s1_decomposition as an SNI-local draft
contract (caller-supplied opaque identity ids; no rank/gate/size/signal/
escalation/trade authority). Inputs are synthetic. Each property uses
random.Random with a fixed seed and at least 50 cases.
"""
from __future__ import annotations

import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("numpy")
import numpy as np  # noqa: E402

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"),
)

from s1_decomposition import (  # noqa: E402
    ABSTAIN_INSUFFICIENT_HISTORY,
    ABSTAIN_MISSING_ENDPOINT,
    MIN_OBS,
    WINDOW,
    beta_window_dates,
    daily_log_returns,
    decompose_unit,
    spec_hash,
    window_log_ret,
)
from s1_infoleak import STEP_TOLERANCE, detect, vintage_series  # noqa: E402
from s1_stats import (  # noqa: E402
    binom_p_one_sided_greater,
    binom_sf_ge,
    mirror_mean_ci,
    sign_test_two_sided,
)

N_CASES = 60
BINOM_TOL = 1e-12
LOG_TOL = 1e-9


def _weekday_sessions(n: int, start: date) -> list[date]:
    out: list[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _comb_sf_ge(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(k, n + 1)) / float(2 ** n)


def test_binom_sf_ge_matches_comb_tail_monotone_and_k0():
    rng = random.Random(1101)
    for _ in range(N_CASES):
        n = rng.randint(0, 60)
        assert binom_sf_ge(0, n) == 1.0
        prev = None
        for k in range(0, n + 1):
            got = binom_sf_ge(k, n)
            assert abs(got - _comb_sf_ge(k, n)) < BINOM_TOL
            if prev is not None:
                assert got <= prev
            prev = got
        assert binom_sf_ge(n + 1, n) == 0.0


def test_sign_test_symmetric_unit_interval_and_ties_are_one():
    rng = random.Random(2202)
    for _ in range(N_CASES):
        pos = rng.randint(0, 80)
        neg = rng.randint(0, 80)
        p = sign_test_two_sided(pos, neg)
        q = sign_test_two_sided(neg, pos)
        assert p == q
        assert 0.0 <= p <= 1.0
        tie_n = rng.randint(0, 80)
        assert sign_test_two_sided(tie_n, tie_n) == 1.0


def test_mirror_mean_ci_deterministic_ci_ordered_and_permutation_invariant():
    rng = random.Random(3303)
    for _ in range(N_CASES):
        n = rng.randint(2, 16)
        nclust = rng.randint(2, n)
        keys = [f"c{rng.randint(0, nclust - 1)}" for _ in range(n)]
        if len(set(keys)) < 2:
            keys[0], keys[1] = "cX", "cY"
        vals = [rng.uniform(-5.0, 5.0) for _ in range(n)]
        seed = rng.randint(1, 10_000)
        draws = 64
        a = mirror_mean_ci(vals, keys, draws=draws, seed=seed)
        b = mirror_mean_ci(vals, keys, draws=draws, seed=seed)
        assert a == b
        if a is None:
            continue
        assert len(a) == 2
        lo, hi = a
        assert lo <= hi
        pairs = list(zip(vals, keys))
        rng.shuffle(pairs)
        v2, k2 = zip(*pairs)
        c = mirror_mean_ci(list(v2), list(k2), draws=draws, seed=seed)
        assert c == a


def test_infoleak_no_revision_clean_above_tol_detected_below_not():
    rng = random.Random(4404)
    for _ in range(N_CASES):
        n = rng.randint(8, 36)
        start = date(2024, 1, 2) + timedelta(days=rng.randint(0, 200))
        dates = _weekday_sessions(n, start)
        q0 = rng.uniform(0.5, 2.0)
        close_price = [rng.uniform(10.0, 400.0) for _ in range(n)]
        close = [q0 * p for p in close_price]
        steps0, state0 = vintage_series(dates, close, close_price)
        assert state0 == "OK"
        assert steps0 == []
        assert detect(steps0, state0, dates[0], dates[-1]) is None

        idx = rng.randint(2, n - 2)
        sign = 1.0 if rng.random() < 0.5 else -1.0
        delta_hi = rng.uniform(1e-4, 5e-2)
        close_hi = list(close)
        for j in range(idx, n):
            close_hi[j] *= 1.0 + sign * delta_hi
        steps_hi, state_hi = vintage_series(dates, close_hi, close_price)
        assert state_hi == "OK"
        assert len(steps_hi) == 1
        assert steps_hi[0][0] == dates[idx]
        assert steps_hi[0][1] > STEP_TOLERANCE
        hit = detect(steps_hi, state_hi, dates[0], dates[-1])
        assert hit is not None
        assert hit["first_offending_date"] == dates[idx].isoformat()
        assert hit["contamination_class"] == "information_leak"
        assert hit["count_of_steps_in_window"] == 1

        delta_lo = rng.uniform(1e-12, 1e-8)
        close_lo = list(close)
        for j in range(idx, n):
            close_lo[j] *= 1.0 + sign * delta_lo
        steps_lo, state_lo = vintage_series(dates, close_lo, close_price)
        assert state_lo == "OK"
        assert steps_lo == []
        assert detect(steps_lo, state_lo, dates[0], dates[-1]) is None


def test_spec_hash_deterministic_and_single_argument_changes_hash():
    rng = random.Random(5505)
    models = ("M0", "M1", "M2")
    for _ in range(N_CASES):
        model = rng.choice(models)
        sid = f"SEC:SYN-{rng.randint(0, 10_000):05d}"
        nfac = rng.randint(0, 4)
        factors = [f"F{rng.randint(0, 50)}" for _ in range(nfac)]
        h = rng.randint(1, 63)
        a = spec_hash(model, sid, factors, h)
        b = spec_hash(model, sid, list(factors), h)
        assert a == b
        assert len(a) == 64
        int(a, 16)
        assert spec_hash(model + "x", sid, factors, h) != a
        assert spec_hash(model, sid + "x", factors, h) != a
        assert spec_hash(model, sid, factors + ["FZ"], h) != a
        assert spec_hash(model, sid, factors, h + 1) != a
        if factors:
            tweaked = list(factors)
            tweaked[0] = tweaked[0] + "x"
            assert spec_hash(model, sid, tweaked, h) != a


def test_daily_and_window_log_returns_telescope_and_beta_window_no_lookahead():
    rng = random.Random(6606)
    for _ in range(N_CASES):
        n = rng.randint(5, 40)
        start = date(2019, 1, 2) + timedelta(days=rng.randint(0, 1500))
        dates = _weekday_sessions(n, start)
        p = rng.uniform(5.0, 200.0)
        closes: dict[date, float] = {}
        for d in dates:
            p *= math.exp(rng.uniform(-0.04, 0.04))
            p = max(p, 1e-3)
            closes[d] = p
        dly = daily_log_returns(closes, dates)
        i = rng.randint(0, n - 2)
        j = rng.randint(i + 1, n - 1)
        chained = sum(dly[dates[k]] for k in range(i + 1, j + 1))
        expected = math.log(closes[dates[j]] / closes[dates[i]])
        assert abs(chained - expected) < LOG_TOL
        w = window_log_ret(closes, dates[i], dates[j])
        assert w is not None
        assert abs(w - expected) < LOG_TOL
        assert abs(chained - w) < LOG_TOL

        missing = dict(closes)
        del missing[dates[j]]
        assert window_log_ret(missing, dates[i], dates[j]) is None
        missing_fill = dict(closes)
        del missing_fill[dates[i]]
        assert window_log_ret(missing_fill, dates[i], dates[j]) is None

        cut_i = rng.randint(0, n - 1)
        d_cutoff = dates[cut_i]
        win = rng.randint(1, WINDOW)
        got = beta_window_dates(dates, d_cutoff, window=win)
        assert all(d <= d_cutoff for d in got)
        assert not any(d > d_cutoff for d in got)
        past = [d for d in dates if d <= d_cutoff]
        assert got == past[-win:]
        assert len(got) == min(win, len(past))


def test_binom_p_one_sided_greater_equals_sf_ge():
    rng = random.Random(7707)
    for _ in range(N_CASES):
        n = rng.randint(0, 60)
        k = rng.randint(0, n + 2)
        assert binom_p_one_sided_greater(k, n) == binom_sf_ge(k, n)


def test_sign_test_matches_double_larger_tail_capped_at_one():
    rng = random.Random(8808)
    for _ in range(N_CASES):
        pos = rng.randint(0, 60)
        neg = rng.randint(0, 60)
        n = pos + neg
        if n == 0:
            assert sign_test_two_sided(pos, neg) == 1.0
            continue
        b = max(pos, neg)
        expected = min(1.0, 2.0 * binom_sf_ge(b, n))
        assert sign_test_two_sided(pos, neg) == expected


def test_infoleak_detect_none_outside_window_or_unverifiable():
    rng = random.Random(9909)
    for _ in range(N_CASES):
        n = rng.randint(8, 28)
        dates = _weekday_sessions(
            n, date(2024, 2, 1) + timedelta(days=rng.randint(0, 80))
        )
        close_price = [100.0 + i for i in range(n)]
        close = [float(p) for p in close_price]
        idx = rng.randint(2, n - 3)
        for j in range(idx, n):
            close[j] *= 1.01
        steps, state = vintage_series(dates, close, close_price)
        assert state == "OK" and steps
        after = dates[idx] + timedelta(days=1)
        assert detect(steps, state, after, dates[-1]) is None
        before = dates[idx] - timedelta(days=1)
        assert detect(steps, state, dates[0], before) is None
        steps_u, state_u = vintage_series(dates, close, [None] * n)
        assert state_u == "VINTAGE_UNVERIFIABLE" and steps_u == []
        assert detect(steps_u, state_u, dates[0], dates[-1]) is None
        one = vintage_series(dates[:1], close[:1], close_price[:1])
        assert one == ([], "VINTAGE_UNVERIFIABLE")


def test_window_log_ret_depends_only_on_endpoints_and_rejects_nonpositive():
    rng = random.Random(10101)
    for _ in range(N_CASES):
        n = rng.randint(4, 20)
        dates = _weekday_sessions(
            n, date(2021, 3, 1) + timedelta(days=rng.randint(0, 400))
        )
        fill, coverage = dates[0], dates[-1]
        a = rng.uniform(1.0, 200.0)
        b = rng.uniform(1.0, 200.0)
        sparse = {fill: a, coverage: b}
        got = window_log_ret(sparse, fill, coverage)
        assert got is not None
        assert abs(got - math.log(b / a)) < LOG_TOL
        assert window_log_ret({fill: a, coverage: 0.0}, fill, coverage) is None
        assert window_log_ret({fill: 0.0, coverage: b}, fill, coverage) is None
        assert window_log_ret({fill: -a, coverage: b}, fill, coverage) is None
        assert window_log_ret({fill: a}, fill, coverage) is None


def test_daily_log_returns_breaks_chain_on_nonpositive():
    rng = random.Random(11111)
    for _ in range(N_CASES):
        n = rng.randint(6, 18)
        dates = _weekday_sessions(
            n, date(2022, 5, 2) + timedelta(days=rng.randint(0, 200))
        )
        closes = {d: rng.uniform(10.0, 80.0) for d in dates}
        hole = rng.randint(2, n - 3)
        bad = 0.0 if rng.random() < 0.5 else -abs(rng.uniform(0.1, 5.0))
        closes[dates[hole]] = bad
        dly = daily_log_returns(closes, dates)
        assert dates[hole] not in dly
        assert dates[hole + 1] not in dly
        assert dates[hole + 2] in dly
        assert abs(
            dly[dates[hole + 2]]
            - math.log(closes[dates[hole + 2]] / closes[dates[hole + 1]])
        ) < LOG_TOL


def test_mirror_mean_ci_none_with_fewer_than_two_cluster_labels():
    rng = random.Random(12121)
    for _ in range(N_CASES):
        n = rng.randint(1, 12)
        label = f"only{rng.randint(0, 9)}"
        vals = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        keys = [label] * n
        assert mirror_mean_ci(vals, keys, draws=32, seed=3) is None
    assert mirror_mean_ci([], [], draws=32, seed=3) is None


def test_decompose_resid_equals_r_minus_common_z_scales_and_dc_respects_cutoff():
    rng = random.Random(13131)
    ok_rows = 0
    for _ in range(N_CASES):
        n = 280
        start = date(2018, 1, 2) + timedelta(days=rng.randint(0, 200))
        dates = _weekday_sessions(n, start)
        ps = rng.uniform(20.0, 150.0)
        pf = rng.uniform(20.0, 150.0)
        subject: dict[date, float] = {}
        factor: dict[date, float] = {}
        for d in dates:
            ps *= math.exp(rng.uniform(-0.03, 0.03))
            pf *= math.exp(rng.uniform(-0.02, 0.02))
            subject[d] = max(ps, 1e-3)
            factor[d] = max(pf, 1e-3)
        d_s = dates[230 + rng.randint(0, 20)]
        fill = dates[255]
        coverage = dates[260 + rng.randint(0, 10)]
        h = rng.choice((1, 5, 10, 21))
        model = rng.choice(("M0", "M1"))
        fac_closes = {} if model == "M0" else {"SPY": factor}
        fac_dates = {} if model == "M0" else {"SPY": dates}
        row = decompose_unit(
            model, "US", h, dates[-2], d_s, fill, coverage,
            subject, dates, fac_closes, fac_dates,
        )
        if row["beta_window_last__dc"] is not None:
            last = date.fromisoformat(row["beta_window_last__dc"])
            first = date.fromisoformat(row["beta_window_first__dc"])
            assert last <= d_s
            assert first <= last
        if row["abstention"] != "OK":
            continue
        ok_rows += 1
        assert abs(row["resid__oc"] - (row["r__oc"] - row["common__oc"])) < 1e-12
        if model == "M0":
            assert row["common__oc"] == 0.0
        else:
            assert abs(
                row["common__oc"] - row["beta_SPY__dc"] * row["F_SPY__oc"]
            ) < 1e-12
        expected_z = row["resid__oc"] / (row["sigma_hat__dc"] * float(np.sqrt(h)))
        assert abs(row["z__oc"] - expected_z) < 1e-12
        r_oc = window_log_ret(subject, fill, coverage)
        assert r_oc is not None
        assert abs(row["r__oc"] - r_oc) < 1e-12
    assert ok_rows >= 40


def test_decompose_missing_endpoint_abstains_and_a25_zero_sigma_abstains():
    rng = random.Random(14141)
    for _ in range(N_CASES):
        n = 260
        dates = _weekday_sessions(
            n, date(2019, 6, 3) + timedelta(days=rng.randint(0, 90))
        )
        level = rng.uniform(10.0, 80.0)
        subject = {d: level for d in dates}
        factor = {d: level + 1.0 for d in dates}
        fill, coverage = dates[-12], dates[-4]
        d_s = dates[-40]
        broken = dict(subject)
        del broken[coverage]
        row_miss = decompose_unit(
            "M0", "US", 5, dates[-2], d_s, fill, coverage,
            broken, dates, {}, {},
        )
        assert row_miss["abstention"] == ABSTAIN_MISSING_ENDPOINT
        assert window_log_ret(broken, fill, coverage) is None

        row_flat = decompose_unit(
            "M0", "US", rng.choice((1, 5, 21)), dates[-2], d_s, fill, coverage,
            subject, dates, {}, {},
        )
        assert row_flat["n_obs__dc"] is not None
        assert row_flat["n_obs__dc"] >= MIN_OBS
        assert row_flat["abstention"] == ABSTAIN_INSUFFICIENT_HISTORY
        assert row_flat["z__oc"] is None

        fac_broken = {d: factor[d] for d in dates if d != coverage}
        subject_rand = {d: rng.uniform(20.0, 40.0) for d in dates}
        row_fac_miss = decompose_unit(
            "M1", "US", 5, dates[-2], d_s, fill, coverage,
            subject_rand, dates, {"SPY": fac_broken}, {"SPY": dates},
        )
        assert row_fac_miss["abstention"] == ABSTAIN_MISSING_ENDPOINT


def test_vintage_series_skips_invalid_prices_without_inventing_steps():
    rng = random.Random(15151)
    for _ in range(N_CASES):
        n = rng.randint(6, 20)
        dates = _weekday_sessions(
            n, date(2023, 1, 3) + timedelta(days=rng.randint(0, 100))
        )
        q0 = rng.uniform(0.8, 1.4)
        close_price = [rng.uniform(20.0, 60.0) for _ in range(n)]
        close = [q0 * p for p in close_price]
        hole = rng.randint(1, n - 2)
        kind = rng.choice(("none_cp", "nan_c", "nonpos_cp"))
        cp = list(close_price)
        cl = list(close)
        if kind == "none_cp":
            cp[hole] = None
        elif kind == "nan_c":
            cl[hole] = float("nan")
        else:
            cp[hole] = 0.0 if rng.random() < 0.5 else -1.0
        steps, state = vintage_series(dates, cl, cp)
        assert state == "OK"
        assert steps == []
