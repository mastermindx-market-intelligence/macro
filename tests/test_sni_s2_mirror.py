"""S2 mirror trick (E9): the ONLY permitted bootstrap for a mean.

Pins three properties of s2_stats.mirror_trick_ci over
engine.grading_stats.block_bootstrap_ci:
(a) identity vs a hand computation that replays the same RNG procedure;
(b) a constant series c returns [c, c] at 4 dp;
(c) shift equivariance: CI(x + a) == CI(x) + a within +/-1e-4.
block_bootstrap_scalar_ci is never imported or used.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from engine.grading_stats import BOOT_DRAWS, BOOT_SEED  # noqa: E402
from s2_stats import mirror_trick_ci  # noqa: E402


def _hand_mirror_ci(cluster_keys, excesses):
    """Replay of the mirror panel through the primitive's documented RNG
    procedure: whole cluster labels resampled with default_rng(BOOT_SEED),
    gap = mean(cond) - mean(all), 2.5/97.5 percentiles at 4 dp."""
    keys = np.asarray(cluster_keys)
    x = np.asarray(excesses, dtype=float)
    n = len(x)
    dates = np.concatenate([keys, keys])
    vals = np.concatenate([x, -x])
    mask = np.concatenate([np.ones(n, dtype=bool), np.zeros(n, dtype=bool)])
    uniq = np.unique(dates)
    by = {d: np.where(dates == d)[0] for d in uniq}
    rng = np.random.default_rng(BOOT_SEED)
    gaps = []
    for _ in range(BOOT_DRAWS):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ridx = np.concatenate([by[d] for d in pick])
        m = mask[ridx]
        if int(m.sum()) == 0:
            continue
        gaps.append(float(np.mean(vals[ridx][m])) - float(np.mean(vals[ridx])))
    assert len(gaps) >= BOOT_DRAWS // 2
    return [round(float(np.percentile(gaps, 2.5)), 4),
            round(float(np.percentile(gaps, 97.5)), 4)]


def test_identity_against_hand_computation() -> None:
    keys = ["2026-05-13", "2026-05-13", "2026-06-01", "2026-06-01", "2026-06-02"]
    x = [0.01, -0.02, 0.03, -0.01, 0.05]
    got = mirror_trick_ci(keys, x)
    want = _hand_mirror_ci(keys, x)
    assert got == want


def test_constant_series_returns_point_interval() -> None:
    c = 0.0125
    ci = mirror_trick_ci(["d1", "d2", "d3"], [c, c, c])
    assert ci is not None
    assert abs(ci[0] - c) < 5e-5 and abs(ci[1] - c) < 5e-5
    assert round(ci[0], 4) == round(c, 4) and round(ci[1], 4) == round(c, 4)


def test_shift_equivariance() -> None:
    keys = ["a", "a", "b", "b", "c"]
    x = [0.03, -0.07, 0.11, -0.02, 0.06]
    lo = mirror_trick_ci(keys, x)
    for shift in (0.5, -1.25):
        hi = mirror_trick_ci(keys, [v + shift for v in x])
        assert hi is not None and lo is not None
        assert abs(hi[0] - (lo[0] + shift)) <= 1e-4
        assert abs(hi[1] - (lo[1] + shift)) <= 1e-4


def test_fewer_than_two_clusters_returns_none() -> None:
    assert mirror_trick_ci(["only"], [0.1]) is None
    assert mirror_trick_ci([], []) is None


def test_scalar_ci_primitive_is_never_called() -> None:
    import s2_outcomes
    import s2_stats
    for mod in (s2_stats, s2_outcomes):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "block_bootstrap_scalar_ci(" not in src
        assert not hasattr(mod, "block_bootstrap_scalar_ci") or \
            mod.block_bootstrap_scalar_ci.__module__ != mod.__name__
