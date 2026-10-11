"""s1_stats.py — pre-registered statistics for the S1 residual lane.

Only existing engine primitives plus exact stdlib combinatorics:
  * wilson_ci                    -> engine/grading_stats.py L56 (re-exported)
  * block_bootstrap_ci           -> engine/grading_stats.py L121 (via the D9 mirror trick)
  * exact binomial / sign tests  -> math.comb (no scipy)

Sidedness is frozen in the seal: H0_1 one-sided (greater), H0_2 two-sided.
`block_bootstrap_scalar_ci` (grading_stats L193) is NOT used anywhere here.
"""
from __future__ import annotations

import math

import numpy as np

from engine.grading_stats import (BOOT_DRAWS, BOOT_SEED, block_bootstrap_ci,
                                  wilson_ci)

ALPHA = 0.05


def binom_sf_ge(k: int, n: int) -> float:
    """Exact P(X >= k) for X ~ Bin(n, 0.5), via math.comb."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return sum(math.comb(n, i) for i in range(k, n + 1)) / float(2 ** n)


def binom_p_one_sided_greater(k: int, n: int) -> float:
    """H0_1: hit rate = 0.50, exact one-sided (greater), alpha 0.05."""
    return binom_sf_ge(k, n)


def sign_test_two_sided(pos: int, neg: int) -> float:
    """H0_2: median excess = 0. Exact two-sided sign test: double the larger
    tail, capped at 1. Zeros (exact ties) are excluded by the caller."""
    n = pos + neg
    if n == 0:
        return 1.0
    b = max(pos, neg)
    return min(1.0, 2.0 * binom_sf_ge(b, n))


def mirror_mean_ci(vals, cluster_keys, *, draws: int = BOOT_DRAWS,
                   seed: int = BOOT_SEED) -> list[float] | None:
    """D9 mirror trick — the ONLY permitted bootstrap use for a mean.

    CI of mean(x) built from block_bootstrap_ci by concatenating the series
    with its negation under the SAME cluster labels:

        dates = concat(k, k); vals = concat(x, -x); mask = concat(1, 0)

    Every resampled block then carries each date's x-row and its mirror, so the
    resampled gap is exactly the block-resampled mean of x. The block is one
    non-overlapping anchor unit (h+1 sessions >= h); the cluster variable is
    the cluster key = trade date of the anchor s. None when the engine returns
    None (< 2 unique cluster labels).
    """
    x = np.asarray(list(vals), dtype=float)
    n = int(x.size)
    if n == 0:
        return None
    k = list(cluster_keys)
    dates = np.array(k + k)
    vv = np.concatenate([x, -x])
    mask = np.concatenate([np.ones(n, dtype=bool), np.zeros(n, dtype=bool)])
    return block_bootstrap_ci(dates, vv, mask, draws=draws, seed=seed, stat="mean")
