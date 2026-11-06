"""test_sni_s1_mirror.py — the D9 mirror-trick CI properties."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

from engine.grading_stats import BOOT_DRAWS, BOOT_SEED, block_bootstrap_ci  # noqa: E402
from s1_stats import mirror_mean_ci  # noqa: E402


def test_identity_equals_the_hand_gap_construction():
    """(a) identity: mirror_ci(x, k) equals the gap computation done by hand."""
    x = np.array([0.01, -0.02, 0.015, 0.03, -0.005, 0.002])
    k = [f"2024-01-{d:02d}" for d in range(1, 7)]
    got = mirror_mean_ci(x, k)
    n = len(x)
    want = block_bootstrap_ci(np.array(k + k),
                              np.concatenate([x, -x]),
                              np.concatenate([np.ones(n, bool), np.zeros(n, bool)]),
                              draws=BOOT_DRAWS, seed=BOOT_SEED, stat="mean")
    assert got == want
    # and the hand computation itself on a tiny example: constant-gap behaviour
    tiny_vals = np.array([1.0, 2.0, 3.0, 4.0])
    tiny_dates = np.array(["a", "a", "b", "b"])
    tiny_mask = np.array([True, False, True, False])
    hand = block_bootstrap_ci(tiny_dates, tiny_vals, tiny_mask, draws=200, seed=3)
    assert hand is not None and hand[0] <= hand[1]


def test_constant_series_returns_point_interval():
    """(b) a constant series c returns [c, c] (to 4 dp)."""
    for c in (0.0, 0.0123, -0.25):
        got = mirror_mean_ci(np.full(9, c), [f"d{i}" for i in range(9)])
        assert got == [round(c, 4), round(c, 4)]


def test_shift_equivariance():
    """(c) CI(x + a) == CI(x) + a within 1e-4."""
    rng = np.random.default_rng(11)
    x = rng.normal(0.0, 0.02, size=40)
    k = [f"2025-{i:02d}" for i in range(40)]
    a = 0.037
    lo, hi = mirror_mean_ci(x, k)
    lo2, hi2 = mirror_mean_ci(x + a, k)
    assert abs(lo2 - (lo + a)) <= 1e-4
    assert abs(hi2 - (hi + a)) <= 1e-4


def test_none_below_two_clusters():
    assert mirror_mean_ci([0.01], ["d0"]) is None
    assert mirror_mean_ci([], []) is None
