"""S2 statistics: exact one-sided binomial, Wilson CI and the mirror trick.

E9 (binding): the ONLY permitted bootstrap use for a mean is the mirror-trick
construction over `engine.grading_stats.block_bootstrap_ci` — CI of mean(x)
with cluster labels k, where the panel is the horizontal mirror of itself:

    dates = concat(k, k); vals = concat(x, -x); mask = concat([True]*n, [False]*n)

so the gap statistic (conditional mean − base mean) equals mean(x) while whole
CLUSTERS (the cluster key = trade date of s) are resampled together.
The moving-block scalar-CI sibling primitive is not permitted here and is
never called by this lane.
"""
from __future__ import annotations

import math

import numpy as np

from engine.grading_stats import block_bootstrap_ci, wilson_ci

MIRROR_BLOCK_NAME = "one episode window W_h (both mirrored halves share the block)"
MIRROR_CLUSTER_VARIABLE = "cluster key (trade date of s, MARKET_US)"


def sign_exact(x: float) -> int:
    """+1 / -1 / 0 with exact-zero handling (a zero excess is a tie, non-hit)."""
    if x == 0:
        return 0
    return 1 if x > 0 else -1


def binomial_one_sided_greater(k: int, n: int) -> float:
    """P(X >= k) under H0 p = 0.50, exact via math.comb."""
    if n <= 0:
        raise ValueError("n must be >= 1")
    k = max(0, min(k, n))
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i)
    return total / (2 ** n)


def hit_rate_test(hits: list[int]) -> dict:
    """Exact one-sided (greater) binomial test of H0 hit rate = 0.50 with the
    Wilson interval on the observed rate. hits: 1/0 per episode (ties are 0)."""
    n = len(hits)
    k = int(sum(hits))
    p_value = binomial_one_sided_greater(k, n)
    return {
        "test": "exact one-sided binomial (greater), H0: post-event hit rate = 0.50",
        "sidedness": "one-sided (greater)",
        "alpha": 0.05,
        "hits": k,
        "n": n,
        "hit_rate": round(k / n, 6) if n else None,
        "p_value": round(p_value, 6),
        "reject_at_alpha": bool(p_value <= 0.05),
        "wilson_ci": wilson_ci(k, n),
    }


def mirror_trick_ci(cluster_keys: list[str], excesses: list[float]) -> list[float] | None:
    """CI of mean(excess) via the mirror-trick panel (E9). Returns None when the
    primitive declines (fewer than 2 unique cluster labels)."""
    n = len(excesses)
    if n == 0:
        return None
    dates = np.concatenate([np.asarray(cluster_keys), np.asarray(cluster_keys)])
    vals = np.concatenate([np.asarray(excesses, dtype=float),
                           -np.asarray(excesses, dtype=float)])
    mask = np.concatenate([np.ones(n, dtype=bool), np.zeros(n, dtype=bool)])
    return block_bootstrap_ci(dates, vals, mask, stat="mean")
