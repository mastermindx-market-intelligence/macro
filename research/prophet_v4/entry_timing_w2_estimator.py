"""Entry Timing W2 — the frozen estimator (registration r6, W2-ADJ-05 / W2-ADJ-07).

Deciding one-sided 95% bounds are the more conservative of

(a) a circular moving block bootstrap over the look's NYSE session calendar: units are grouped
    into per-session cohorts by ``t_disc`` (empty cohorts stay in the calendar), a block is
    ``ELL`` = 44 consecutive sessions (2 x (K + H + 2)), blocks start at uniformly drawn sessions
    and wrap circularly, enough blocks are drawn to cover the calendar, and the statistic is the
    unit-weighted mean over the units in the drawn sessions; ``RESAMPLES`` = 4,000 draws from
    ``numpy.random.Generator(PCG64(SEED))``; ONE index set is shared by every endpoint, bound and
    tolerance of a look (``shared_index_set``);
(b) a Student-t bound with B - 1 degrees of freedom on the mean of the B full non-overlapping
    block means, blocks aligned from the first session of the calendar; the trailing partial
    block is in (a) and not in (b); a block's mean is the unit-weighted mean of its units.

Lower deciding bound = min of the two lower bounds; upper = max of the two upper bounds. A look
whose full blocks are fewer than the floor, or any of whose full blocks holds no unit, has no
deciding bound (``identified`` False). This module reads no price, outcome or registry: callers
pass per-unit values and the session index of each unit.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

ELL = 44
RESAMPLES = 4000
SEED = 20261031
ALPHA = 0.05
FULL_BLOCKS_FIXED_LOOK = 5
FULL_BLOCKS_FUTILITY = 3
AUTOCORR_FLOOR = 0.17        # planning lag-1 autocorrelation of adjacent block means (registration r7, ADJ-10)


def shared_index_set(n_sessions: int, *, ell: int = ELL, resamples: int = RESAMPLES, seed: int = SEED) -> np.ndarray:
    """(resamples, n_sessions) session indices; drawn once per look and reused for every statistic."""
    if n_sessions <= 0:
        raise ValueError("empty calendar")
    rng = np.random.Generator(np.random.PCG64(seed))
    n_blocks = math.ceil(n_sessions / ell)
    starts = rng.integers(0, n_sessions, size=(resamples, n_blocks))
    idx = (starts[:, :, None] + np.arange(ell)[None, None, :]) % n_sessions
    return idx.reshape(resamples, -1)[:, :n_sessions]


def _cohorts(values: np.ndarray, session_idx: np.ndarray, n_sessions: int) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    session_idx = np.asarray(session_idx, dtype=int)
    if values.shape != session_idx.shape:
        raise ValueError("values and session_idx differ in shape")
    if len(session_idx) and (session_idx.min() < 0 or session_idx.max() >= n_sessions):
        raise ValueError("session index outside the calendar")
    sums = np.bincount(session_idx, weights=values, minlength=n_sessions)
    counts = np.bincount(session_idx, minlength=n_sessions).astype(float)
    return sums, counts


def mbb_bounds(values, session_idx, n_sessions: int, *, index_set: np.ndarray, alpha: float = ALPHA) -> dict:
    """Circular moving block bootstrap percentile bounds of the unit-weighted mean."""
    sums, counts = _cohorts(values, session_idx, n_sessions)
    s = sums[index_set].sum(axis=1)
    c = counts[index_set].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = np.where(c > 0, s / c, np.nan)
    ok = means[~np.isnan(means)]
    if len(ok) == 0:
        return {"lower": None, "upper": None, "resamples_used": 0}
    return {"lower": float(np.percentile(ok, 100 * alpha)), "upper": float(np.percentile(ok, 100 * (1 - alpha))),
            "resamples_used": int(len(ok)), "point": float(sums.sum() / counts.sum()) if counts.sum() else None}


def full_block_t_bounds(values, session_idx, n_sessions: int, *, ell: int = ELL, alpha: float = ALPHA,
                        autocorr_floor: float = AUTOCORR_FLOOR) -> dict:
    """Student-t one-sided bounds (B - 1 df) on the mean of the B full non-overlapping block means.

    The SE is inflated for lag-1 autocorrelation of adjacent block means (overlapping holds leak across the
    block edge): r = max(observed lag-1 autocorrelation, AUTOCORR_FLOOR), see se_inflation()."""
    sums, counts = _cohorts(values, session_idx, n_sessions)
    B = n_sessions // ell
    out = {"full_blocks": int(B), "block_means": None, "lower": None, "upper": None, "t_quantile": None, "sd_block_means": None}
    if B < 2:
        return out
    bs = sums[: B * ell].reshape(B, ell).sum(axis=1)
    bc = counts[: B * ell].reshape(B, ell).sum(axis=1)
    if (bc == 0).any():
        out["empty_full_blocks"] = int((bc == 0).sum())
        return out
    bm = bs / bc
    m, sd = float(bm.mean()), float(bm.std(ddof=1))
    tq = float(stats.t.ppf(1 - alpha, B - 1))
    r = max(lag1_autocorr(bm), autocorr_floor)
    infl = se_inflation(r, B)
    se = infl * sd / math.sqrt(B)
    out.update({"block_means": [float(x) for x in bm], "mean_of_block_means": m, "sd_block_means": sd,
                "t_quantile": tq, "lag1_autocorr_observed": lag1_autocorr(bm), "lag1_autocorr_used": r,
                "se_inflation": infl, "lower": m - tq * se, "upper": m + tq * se})
    return out


def lag1_autocorr(block_means) -> float:
    """Lag-1 autocorrelation of adjacent full-block means (0.0 when fewer than 3 blocks or zero variance)."""
    x = np.asarray(block_means, dtype=float)
    if x.size < 3:
        return 0.0
    d = x - x.mean()
    den = float((d * d).sum())
    if den == 0.0:
        return 0.0
    return float((d[:-1] * d[1:]).sum() / den)


def se_inflation(r: float, B: int) -> float:
    """SE inflation for B adjacent block means with lag-1 autocorrelation r (AR(1)-at-lag-1 approximation).

    Var(mean) = (sigma^2 / B) * (1 + 2 r (B-1)/B); the sample variance of the block means is itself biased
    down by a factor (1 - 2 r / B), so the ratio of the correct SE to the naive SE is
    sqrt((1 + 2 r (B-1)/B) / (1 - 2 r / B)).  At B = 5 and r = 0.17 this is ~1.165.
    """
    if B < 2 or r <= 0.0:
        return 1.0
    return math.sqrt((1.0 + 2.0 * r * (B - 1) / B) / (1.0 - 2.0 * r / B))


def deciding_bounds(values, session_idx, n_sessions: int, *, index_set: np.ndarray, ell: int = ELL,
                    full_blocks_min: int = FULL_BLOCKS_FIXED_LOOK, alpha: float = ALPHA) -> dict:
    """The look record for one endpoint: both bounds, which decided, and the identification flag."""
    a = mbb_bounds(values, session_idx, n_sessions, index_set=index_set, alpha=alpha)
    b = full_block_t_bounds(values, session_idx, n_sessions, ell=ell, alpha=alpha)
    rec = {"mbb": a, "t_full_blocks": b, "full_blocks": b["full_blocks"], "full_blocks_min": full_blocks_min,
           "distinct_sessions_with_units": int((_cohorts(values, session_idx, n_sessions)[1] > 0).sum()),
           "identified": False, "lower": None, "upper": None, "lower_decided_by": None, "upper_decided_by": None}
    if b["full_blocks"] < full_blocks_min or b["lower"] is None or a["lower"] is None:
        return rec
    rec["identified"] = True
    rec["lower"], rec["lower_decided_by"] = (a["lower"], "mbb") if a["lower"] <= b["lower"] else (b["lower"], "t")
    rec["upper"], rec["upper_decided_by"] = (a["upper"], "mbb") if a["upper"] >= b["upper"] else (b["upper"], "t")
    rec["point"] = a.get("point")
    return rec


def dependence_diagnostic(values, session_idx, n_sessions: int, *, ell: int = ELL, resamples: int = RESAMPLES,
                          seed: int = SEED + 1) -> dict:
    """Descriptive only: per-session cluster bootstrap bound and the implied design effect."""
    values = np.asarray(values, dtype=float)
    sums, counts = _cohorts(values, session_idx, n_sessions)
    live = np.flatnonzero(counts > 0)
    rng = np.random.Generator(np.random.PCG64(seed))
    draws = rng.choice(live, size=(resamples, len(live)), replace=True) if len(live) else np.zeros((0, 0), int)
    with np.errstate(invalid="ignore", divide="ignore"):
        cm = sums[draws].sum(axis=1) / counts[draws].sum(axis=1) if len(live) else np.array([])
    n = len(values)
    iid_se = float(values.std(ddof=1) / math.sqrt(n)) if n > 1 else None
    fb = full_block_t_bounds(values, session_idx, n_sessions, ell=ell)
    block_se = (fb["sd_block_means"] / math.sqrt(fb["full_blocks"])) if fb.get("sd_block_means") else None
    return {"cluster_lower": float(np.percentile(cm, 5)) if len(cm) else None,
            "cluster_upper": float(np.percentile(cm, 95)) if len(cm) else None,
            "iid_se": iid_se, "block_mean_se": block_se,
            "implied_design_effect": (block_se / iid_se) ** 2 if (block_se and iid_se) else None,
            "distinct_sessions": int(len(live)), "full_blocks": fb["full_blocks"]}
