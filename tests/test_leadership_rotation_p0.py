"""Tests for scripts.leadership_rotation_p0 (T11 P0 synthetic grid)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts import leadership_rotation_study as st
from scripts.leadership_rotation_p0 import (
    REGIME_MAX,
    REGIME_MIN,
    TAIL,
    size_check,
    simulate_family,
    run_cell,
    window_for_target,
    wilson_interval,
)


# MUTATION: scripts/leadership_rotation_p0.py:118 replace seed_seq with np.random.SeedSequence([0])
def test_simulate_family_deterministic_and_varies_by_k():
    ss0 = np.random.SeedSequence([1, 2, 0])
    ss1 = np.random.SeedSequence([1, 2, 1])
    g0a, _ = simulate_family(0.01, 0.0, 0.5, 504, ss0)
    g0b, _ = simulate_family(0.01, 0.0, 0.5, 504, ss0)
    g1, _ = simulate_family(0.01, 0.0, 0.5, 504, ss1)
    assert np.allclose(g0a["defensive_sector"][0].num, g0b["defensive_sector"][0].num)
    assert not np.allclose(g0a["defensive_sector"][0].num, g1["defensive_sector"][0].num)


# MUTATION: scripts/leadership_rotation_p0.py:88 replace max(...) with sigma alone
def test_null_relative_return_sd_matches_sigma():
    sigma = 0.010
    n_form = 20_000 - st.WARMUP - TAIL
    groups, _ = simulate_family(sigma, 0.0, 0.5, n_form, np.random.SeedSequence(99))
    ps = groups["defensive_sector"][0]
    m = np.log(ps.num[1:] / ps.num[:-1]) - np.log(ps.den[1:] / ps.den[:-1])
    sd = float(np.std(m, ddof=1))
    assert abs(sd - sigma) / sigma < 0.05


# MUTATION: scripts/leadership_rotation_p0.py:134 replace delta / 20.0 with delta
def test_regime_drift_mean_relative_return():
    n_form = 8000
    groups, truth = simulate_family(1e-6, 0.01, 0.0, n_form, np.random.SeedSequence(7))
    g = "defensive_sector"
    regime = np.asarray(truth["regime_mask"][g], dtype=bool)
    ps = groups[g][0]
    rel = np.log(ps.num[1:] / ps.num[:-1]) - np.log(ps.den[1:] / ps.den[:-1])
    on = rel[regime[1:]]
    off = rel[~regime[1:]]
    assert float(np.mean(on)) == pytest.approx(0.01 / 20.0, rel=0.15, abs=0.0002)
    assert abs(float(np.mean(off))) < 0.0001


# MUTATION: scripts/leadership_rotation_p0.py:108 append onset at warmup - 1
def test_onsets_regime_length_no_overlap():
    n_form = 3000
    groups, truth = simulate_family(0.01, 0.005, 0.5, n_form, np.random.SeedSequence(3))
    for g in groups:
        onsets = truth["onsets"][g]
        regime = truth["regime_mask"][g]
        for t in onsets:
            assert st.WARMUP <= t < st.WARMUP + n_form
        active_end = -1
        lengths = []
        for t in sorted(onsets):
            assert t > active_end
            run = 0
            while t + run < st.WARMUP + n_form and regime[t + run]:
                run += 1
            lengths.append(run)
            active_end = t + run - 1
        assert lengths
        assert all(REGIME_MIN <= L <= REGIME_MAX for L in lengths)


# MUTATION: scripts/leadership_rotation_p0.py:131 use sqrt_rho for both legs of u
def test_within_group_u_correlation():
    n_form = 15_000
    rho = 0.5
    groups, _ = simulate_family(0.01, 0.0, rho, n_form, np.random.SeedSequence(11))
    spy = groups["defensive_sector"][0].spy

    def _u_hat(ps):
        m = np.diff(np.log(spy))
        rel = np.log(ps.num[1:] / ps.num[:-1]) - np.log(ps.den[1:] / ps.den[:-1])
        return rel + 0.3 * m

    g = groups["defensive_sector"]
    c_within = float(np.corrcoef(_u_hat(g[0]), _u_hat(g[1]))[0, 1])
    c_across = float(np.corrcoef(_u_hat(g[0]), _u_hat(groups["broadening_proxy"][0]))[0, 1])
    assert abs(c_within - rho) < 0.05
    assert abs(c_across) < 0.05


# MUTATION: scripts/leadership_rotation_p0.py:201 reverse range(st.WARMUP, last_e + 1)
def test_window_for_target_monotone_in_n_target():
    groups, _ = simulate_family(0.01, 0.005, 0.5, 252 * 12, np.random.SeedSequence(5))
    w20 = window_for_target(groups, 20, "H2")
    w40 = window_for_target(groups, 40, "H2")
    assert w20 is not None and w40 is not None
    assert w20 <= w40


# MUTATION: scripts/leadership_rotation_p0.py:348 skip done sims when appending
def test_run_cell_resumable(tmp_path: Path):
    out = tmp_path / "sims.jsonl"
    run_cell(0.01, 0.0, 0.5, 20, 1, cell_id=99, workers=1, out=out)
    n1 = sum(1 for _ in out.read_text().splitlines() if _)
    run_cell(0.01, 0.0, 0.5, 20, 1, cell_id=99, workers=1, out=out)
    n2 = sum(1 for _ in out.read_text().splitlines() if _)
    assert n1 == 1 and n2 == 1


# MUTATION: scripts/leadership_rotation_p0.py:218 replace z with 1.0 in wilson_interval
def test_wilson_interval_known_values():
    lo, hi = wilson_interval(0, 200)
    assert lo < 1e-9
    assert hi == pytest.approx(0.0188, abs=1e-3)
    lo5, hi5 = wilson_interval(5, 200)
    assert lo5 == pytest.approx(0.0107, abs=1e-3)
    assert hi5 == pytest.approx(0.0572, abs=1e-3)


# MUTATION: scripts/leadership_rotation_p0.py:519 use lo < alpha instead of lo > alpha
def test_size_check_flags_high_null_pass_rate():
    cell_bad = {
        "delta": 0.0,
        "cell_id": 0,
        "summary": {
            "by_group_hypothesis": {
                "defensive_sector/H1": {
                    "pass_rate": 20 / 200,
                    "wilson_95": {
                        "lower": wilson_interval(20, 200)[0],
                        "upper": wilson_interval(20, 200)[1],
                    },
                }
            }
        },
    }
    cell_ok = {
        "delta": 0.0,
        "cell_id": 1,
        "summary": {
            "by_group_hypothesis": {
                "defensive_sector/H1": {
                    "pass_rate": 2 / 200,
                    "wilson_95": {
                        "lower": wilson_interval(2, 200)[0],
                        "upper": wilson_interval(2, 200)[1],
                    },
                }
            }
        },
    }
    bad = size_check([cell_bad])
    ok = size_check([cell_ok])
    assert bad["violations"]
    assert not ok["violations"]
