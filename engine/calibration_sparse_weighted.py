from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED.

Q06 sparse-data calibration reference for the FS-3 held weighted-calibration
decision (PR #8385).

Verdict: REJECT under the frozen prereg (K1 failed). The continuous rule
R_alt gave false reassurance at 0.105 (21/200) against the 0.10 bar in two
local-reversal (T3) steady cells: H=5 at T=1260 and H=21 at T=1512. K2 held:
the #8385 draft gate reached support in no simulated cell. K3 is
INSUFFICIENT_DATA, and OUTCOME_CALIBRATION is INSUFFICIENT_DATA. Evidence
lives in
research/quant_assessment_2026_10/Q06_sparse_weighted_calibration/VERDICT.md.
The verdict is a property of this research reference and of its proposed
amendment, not a calibration claim about any FS-3 score. Nothing imports
this module. It registers nothing, schedules nothing and promotes nothing.
FS-3 scoring stays disabled and the study stays ``building_history``.

The module provides:

* ``native_units``: the frozen FS-3/FS-5 uniqueness weight law on integer
  NYSE positions. A unit is (fill session, ROOT). Its interval runs over the
  inclusive positions [fill, end]. Concurrency counts units globally. The unit
  weight is the mean of 1/c over the interval, and each event receives the
  unit weight divided by the unit's event count. This reproduces
  ``lib.flow_score.uniqueness_weights_nyse_intervals``. It does not replace
  that function.
* Support geometry. The native effective N is sum(w); with equal-length
  intervals it equals covered sessions / L. Kish N is reported separately as a
  weight-concentration index, and the honest dependence count is anchor blocks.
  The feasibility bound is T >= N*L - H.
* Whole-tie, contiguous, weight-balanced bins found by an exact dynamic
  program with a lexicographic tie-break. Also weighted ECE, Brier against
  base rate, and the draft's circular moving-block max-statistic monotonicity
  test.
* A parsimonious continuous alternative: weighted logistic recalibration
  ``logit pi = a + b*logit p`` with an anchor-block bootstrap and a
  simultaneous bin-residual misfit flag. Also a partially pooled bin
  diagnostic. Pooling may only de-escalate; it can never create a PASS.
* A three-state review record that keeps the Opus recommendation, the
  statistical acceptance and the Fable ratification separate.
* A seeded synthetic panel simulator, used for operating characteristics.

Pure functions only. Inputs are bounded and there is no I/O, wall-clock read
or global state mutation at import or call time.
"""

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from scipy.special import expit, logit, ndtr

RESEARCH_ONLY = True

# Frozen numbers reused verbatim. None of these is a new threshold.
ECE_THRESHOLD = 0.05            # FS-3 §5
N_BINS = 10                     # FS-3 §5 (10 equal-mass bins)
BUCKET_FLOOR = 30.0             # FS-3 §7 per condition bucket (effective obs)
CELL_FLOOR = 20.0               # FS-3 §7 per era cell (effective obs)
DRAFT_TOTAL_FLOOR = 200.0       # PR #8385 draft example total
DRAFT_BIN_FLOOR = 20.0          # PR #8385 draft per-bin floor
DRAFT_MIN_BLOCKS = 20           # PR #8385 draft floor(T/b) >= 20
DRAFT_VALID_FRACTION = 0.95     # PR #8385 draft 9,500 / 9,999 valid replicates
DRAFT_REPLICATES = 9_999        # PR #8385 draft replicate count
MONOTONE_POINT_TOL = 1e-3       # lib.flow_score.is_reliability_monotone default
SESSIONS_PER_YEAR = 252

MAX_EVENTS = 5_000_000
MAX_POSITIONS = 200_000
MAX_GROUPS = 20_000
MAX_REPLICATES = 100_000
_LOGIT_CLIP = 1e-6
_COEF_LIMIT = 50.0

DECISIONS = ("PASS", "FAIL", "NO_VERDICT")

OPUS_RECOMMENDATION_STATES = ("NONE", "PROPOSE_AMENDMENT", "RECOMMEND_REJECT", "WITHDRAWN")
STATISTICAL_ACCEPTANCE_STATES = ("NOT_REVIEWED", "ACCEPTED", "REJECTED", "CHANGES_REQUESTED")
FABLE_RATIFICATION_STATES = ("UNRATIFIED", "RATIFIED", "REFUSED")

# Distinct support states. Unknown, excluded, pending and a measured zero are
# never folded together.
SUPPORT_STATES = ("UNKNOWN", "EMPTY", "MEASURED_ZERO", "MEASURED")


# ── seeds and resampling ─────────────────────────────────────────────────────

def rng_from_label(*parts: str) -> np.random.Generator:
    """Return a PCG64 generator seeded by SHA-256 of the NUL-joined label parts."""
    label = "\0".join(str(part) for part in parts)
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(digest, "big")))


def circular_block_counts(
    n_sessions: int, block_len: int, n_rep: int, rng: np.random.Generator
) -> np.ndarray:
    """Return a circular moving-block bootstrap count matrix of shape (n_rep, n_sessions).

    Each row records how many times each calendar session index is drawn.
    Blocks of ``block_len`` consecutive sessions wrap circularly and the
    concatenation is truncated to ``n_sessions``.
    """
    n = int(n_sessions)
    b = int(block_len)
    r = int(n_rep)
    if n < 1 or b < 1 or r < 1:
        raise ValueError("bootstrap_dimensions_invalid")
    if n > MAX_POSITIONS or r > MAX_REPLICATES:
        raise ValueError("bootstrap_dimensions_exceed_bound")
    k = -(-n // b)
    starts = rng.integers(0, n, size=(r, k))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(r, k * b)[:, :n] % n
    flat = idx + (np.arange(r)[:, None] * n)
    counts = np.bincount(flat.ravel(), minlength=r * n).reshape(r, n)
    return counts.astype(float)


def order_statistic_quantile(values: np.ndarray, q: float) -> float:
    """Return the ceil(q*R)-th order statistic (1-based), as specified in the draft."""
    v = np.sort(np.asarray(values, dtype=float))
    if v.size == 0:
        return float("nan")
    k = max(1, int(math.ceil(q * v.size)))
    return float(v[min(k, v.size) - 1])


# ── frozen native weight law ─────────────────────────────────────────────────

@dataclass(frozen=True)
class NativeUnits:
    unit_start: np.ndarray
    unit_end: np.ndarray
    unit_weight: np.ndarray
    unit_size: np.ndarray
    event_unit: np.ndarray
    event_weight: np.ndarray
    concurrency: np.ndarray


def _root_codes(roots: Sequence[Any] | np.ndarray) -> np.ndarray:
    arr = np.asarray(roots)
    if arr.dtype.kind in "iu":
        return arr.astype(np.int64)
    cleaned = np.asarray([str(value).strip().upper() for value in arr.tolist()])
    if np.any(cleaned == ""):
        raise ValueError("root_missing")
    _, codes = np.unique(cleaned, return_inverse=True)
    return codes.astype(np.int64)


def native_units(
    fill_positions: Sequence[int] | np.ndarray,
    end_positions: Sequence[int] | np.ndarray,
    roots: Sequence[Any] | np.ndarray,
    *,
    exact: bool = True,
) -> NativeUnits:
    """Apply the frozen FS-3 §4.4 / FS-5 native uniqueness law on integer NYSE positions.

    ``exact=True`` uses ``math.fsum`` per unit, matching the incumbent.
    ``exact=False`` uses a float prefix sum. It is for simulation speed only and
    agrees to about 1e-13.
    The inputs are never mutated.
    """
    fill = np.array(fill_positions, dtype=np.int64, copy=True)
    end = np.array(end_positions, dtype=np.int64, copy=True)
    if fill.ndim != 1 or fill.shape != end.shape:
        raise ValueError("positions_shape_mismatch")
    n = fill.size
    if n == 0:
        raise ValueError("population_empty")
    if n > MAX_EVENTS:
        raise ValueError("population_exceeds_bound")
    if np.any(fill < 0):
        raise ValueError("position_negative")
    if np.any(end < fill):
        raise ValueError("boundary_noncausal_end")
    if int(end.max()) + 2 > MAX_POSITIONS:
        raise ValueError("positions_exceed_bound")
    codes = _root_codes(roots)
    if codes.shape != fill.shape:
        raise ValueError("roots_shape_mismatch")
    n_codes = int(codes.max()) + 1
    key = fill * n_codes + codes
    _, first_idx, event_unit, unit_size = np.unique(
        key, return_index=True, return_inverse=True, return_counts=True
    )
    unit_start = fill[first_idx]
    unit_end = end[first_idx]
    if np.any(end != unit_end[event_unit]):
        raise ValueError("uniqueness_unit_boundary_mismatch")
    delta = np.zeros(int(unit_end.max()) + 2, dtype=np.int64)
    np.add.at(delta, unit_start, 1)
    np.add.at(delta, unit_end + 1, -1)
    concurrency = np.cumsum(delta)
    inverse = np.divide(
        1.0, concurrency, out=np.zeros(concurrency.shape, dtype=float), where=concurrency > 0
    )
    lengths = (unit_end - unit_start + 1).astype(float)
    if exact:
        unit_weight = np.array(
            [math.fsum(inverse[s : e + 1].tolist()) for s, e in zip(unit_start.tolist(), unit_end.tolist())],
            dtype=float,
        ) / lengths
    else:
        prefix = np.concatenate(([0.0], np.cumsum(inverse)))
        unit_weight = (prefix[unit_end + 1] - prefix[unit_start]) / lengths
    if not np.all(np.isfinite(unit_weight)) or np.any(unit_weight <= 0) or np.any(unit_weight > 1 + 1e-12):
        raise ValueError("uniqueness_weight_invalid")
    event_weight = unit_weight[event_unit] / unit_size[event_unit]
    return NativeUnits(
        unit_start=unit_start,
        unit_end=unit_end,
        unit_weight=unit_weight,
        unit_size=unit_size.astype(np.int64),
        event_unit=event_unit.astype(np.int64),
        event_weight=event_weight,
        concurrency=concurrency,
    )


def anchor_accrual_series(units: NativeUnits, first_position: int, last_position: int) -> np.ndarray:
    """Return s_t = the sum of unit weights anchored (filled) at each position in [first, last].

    Sessions with no anchored unit contribute a measured 0.0.
    """
    first = int(first_position)
    last = int(last_position)
    if last < first:
        raise ValueError("window_empty")
    if last - first + 1 > MAX_POSITIONS:
        raise ValueError("window_exceeds_bound")
    s = np.zeros(last - first + 1, dtype=float)
    inside = (units.unit_start >= first) & (units.unit_start <= last)
    np.add.at(s, units.unit_start[inside] - first, units.unit_weight[inside])
    return s


def position_decomposition(units: NativeUnits) -> np.ndarray:
    """Return a_t = the sum over covering units of (1/c_t)/L_unit. Then sum_t a_t == sum_units u exactly."""
    size = units.concurrency.size
    per_len = np.zeros(size + 1, dtype=float)
    lengths = (units.unit_end - units.unit_start + 1).astype(float)
    np.add.at(per_len, units.unit_start, 1.0 / lengths)
    np.add.at(per_len, units.unit_end + 1, -1.0 / lengths)
    load = np.cumsum(per_len)[:size]
    inverse = np.divide(
        1.0, units.concurrency, out=np.zeros(size, dtype=float), where=units.concurrency > 0
    )
    return load * inverse


# ── support geometry (requirement 2: weight ESS is never the dependence count) ──

def kish_effective_n(weights: Sequence[float] | np.ndarray) -> float:
    """Kish weight-concentration index (sum w)^2 / sum w^2. It is not a temporal-dependence count."""
    w = np.asarray(weights, dtype=float)
    if w.size == 0:
        return 0.0
    if not np.all(np.isfinite(w)) or np.any(w < 0):
        raise ValueError("weights_invalid")
    sq = math.fsum((w * w).tolist())
    if sq == 0.0:
        return 0.0
    return math.fsum(w.tolist()) ** 2 / sq


def block_count(n_sessions: int, block_len: int) -> int:
    if block_len < 1 or n_sessions < 0:
        raise ValueError("block_arguments_invalid")
    return int(n_sessions) // int(block_len)


def support_summary(
    weights: Sequence[float] | np.ndarray | None,
    anchor_positions: Sequence[int] | np.ndarray | None,
    block_len: int,
) -> dict[str, Any]:
    """Report the native effective N, Kish N and the anchor-block count as separate fields.

    ``weights=None`` means UNKNOWN, which is distinct from EMPTY (no rows)
    and from MEASURED_ZERO (rows present, total weight 0).
    """
    if weights is None or anchor_positions is None:
        return {"state": "UNKNOWN", "native_effective_n": None, "kish_n": None,
                "n_rows": None, "span_sessions": None, "anchor_sessions": None,
                "anchor_blocks": None, "block_len": int(block_len)}
    w = np.asarray(weights, dtype=float)
    a = np.asarray(anchor_positions, dtype=np.int64)
    if w.shape != a.shape:
        raise ValueError("support_shape_mismatch")
    if w.size == 0:
        return {"state": "EMPTY", "native_effective_n": 0.0, "kish_n": 0.0, "n_rows": 0,
                "span_sessions": 0, "anchor_sessions": 0, "anchor_blocks": 0,
                "block_len": int(block_len)}
    total = math.fsum(w.tolist())
    span = int(a.max() - a.min() + 1)
    return {
        "state": "MEASURED_ZERO" if total == 0.0 else "MEASURED",
        "native_effective_n": total,
        "kish_n": kish_effective_n(w),
        "n_rows": int(w.size),
        "span_sessions": span,
        "anchor_sessions": int(np.unique(a[w > 0]).size),
        "anchor_blocks": block_count(span, block_len),
        "block_len": int(block_len),
    }


def native_rate_cap(interval_len: int, n_sessions: int) -> float:
    """Upper bound on the native accrual rate per anchor session: (1 + (L-1)/T)/L."""
    if interval_len < 1 or n_sessions < 1:
        raise ValueError("cap_arguments_invalid")
    return (1.0 + (interval_len - 1) / n_sessions) / interval_len


def min_sessions_for_total(total: float, interval_len: int, horizon: int) -> int:
    """Smallest anchor-session span T with (T + H)/L >= total, i.e. T >= total*L - H (perfect coverage)."""
    if total <= 0:
        return 0
    return max(1, int(math.ceil(total * interval_len - horizon)))


def projected_sessions(rate: float, total_floor: float, horizon: int, min_blocks: int) -> float:
    """Sessions needed for sum(w) >= floor at ``rate`` and floor(T/H) >= min_blocks."""
    if not np.isfinite(rate) or rate <= 0:
        return float("inf")
    return max(total_floor / rate, float(min_blocks * horizon))


def gate_ratio(rate: float, horizon: int) -> dict[str, float]:
    """Return T_inc, T_alt and their ratio Q = T_inc / T_alt (PREREG §2)."""
    t_inc = projected_sessions(rate, DRAFT_TOTAL_FLOOR, horizon, DRAFT_MIN_BLOCKS)
    t_alt = projected_sessions(rate, BUCKET_FLOOR, horizon, DRAFT_MIN_BLOCKS)
    ratio = t_inc / t_alt if np.isfinite(t_alt) and t_alt > 0 else float("nan")
    return {"t_inc": t_inc, "t_alt": t_alt, "ratio": ratio,
            "years_inc": t_inc / SESSIONS_PER_YEAR, "years_alt": t_alt / SESSIONS_PER_YEAR}


# ── whole-tie groups and bins (requirement 1) ────────────────────────────────

@dataclass(frozen=True)
class TieGroups:
    p: np.ndarray            # distinct predictions, ascending
    weight: np.ndarray       # sum w per group
    weighted_p: np.ndarray   # sum w*p per group
    weighted_y: np.ndarray   # sum w*y per group (zeros when y is None)
    row_group: np.ndarray    # group index per retained row (-1 means a zero-weight row was dropped)
    zero_weight_rows: int


def tie_groups(
    p: Sequence[float] | np.ndarray,
    w: Sequence[float] | np.ndarray,
    y: Sequence[float] | np.ndarray | None = None,
) -> TieGroups:
    """Collapse rows into whole-tie groups of identical prediction.

    Rules:
    * Ties are never split across bins.
    * Zero-weight rows are dropped and counted. They are neither a measured
      zero nor an empty cell.
    * Negative or non-finite weights, predictions outside [0, 1], and labels
      outside {0, 1} are refused.
    """
    pa = np.array(p, dtype=float, copy=True)
    wa = np.array(w, dtype=float, copy=True)
    if pa.ndim != 1 or pa.shape != wa.shape:
        raise ValueError("tie_shape_mismatch")
    if pa.size > MAX_EVENTS:
        raise ValueError("population_exceeds_bound")
    if not np.all(np.isfinite(pa)) or np.any(pa < 0) or np.any(pa > 1):
        raise ValueError("prediction_invalid")
    if not np.all(np.isfinite(wa)) or np.any(wa < 0):
        raise ValueError("weights_invalid")
    if y is None:
        ya = np.zeros_like(pa)
    else:
        ya = np.array(y, dtype=float, copy=True)
        if ya.shape != pa.shape or not np.all(np.isin(ya, (0.0, 1.0))):
            raise ValueError("label_invalid")
    keep = wa > 0
    row_group = np.full(pa.size, -1, dtype=np.int64)
    if not np.any(keep):
        empty = np.zeros(0, dtype=float)
        return TieGroups(empty, empty, empty, empty, row_group, int(pa.size))
    values, inv = np.unique(pa[keep], return_inverse=True)
    if values.size > MAX_GROUPS:
        raise ValueError("groups_exceed_bound")
    g = values.size
    weight = np.bincount(inv, weights=wa[keep], minlength=g)
    wp = np.bincount(inv, weights=wa[keep] * pa[keep], minlength=g)
    wy = np.bincount(inv, weights=wa[keep] * ya[keep], minlength=g)
    row_group[keep] = inv
    return TieGroups(values, weight, wp, wy, row_group, int((~keep).sum()))


def whole_tie_partition(
    group_weights: Sequence[float] | np.ndarray, n_bins: int = N_BINS, floor: float = 0.0
) -> list[int] | None:
    """Exact contiguous partition of whole-tie groups into B = min(n_bins, G) bins.

    The DP minimizes sum_j (W_j - W/B)^2 subject to every W_j >= ``floor``.
    Among equal objectives the lexicographically smallest cut vector wins.
    The return value lists bin start indices (the first is 0). ``None`` means
    the partition is infeasible: either there are no groups or the floor
    cannot be met.
    """
    wts = np.asarray(group_weights, dtype=float)
    g = wts.size
    if g == 0:
        return None
    if g > MAX_GROUPS:
        raise ValueError("groups_exceed_bound")
    if not np.all(np.isfinite(wts)) or np.any(wts <= 0):
        raise ValueError("group_weights_invalid")
    b = min(int(n_bins), g)
    if b < 1:
        raise ValueError("n_bins_invalid")
    prefix = np.array([0.0] + [math.fsum(wts[: j + 1].tolist()) for j in range(g)], dtype=float)
    total = prefix[-1]
    target = total / b
    inf = float("inf")
    # f[k][i]: the best cost to split groups i..g-1 into k bins. choice[k][i] is the first end index.
    f = np.full((b + 1, g + 1), inf)
    choice = np.full((b + 1, g + 1), -1, dtype=np.int64)
    f[0, g] = 0.0
    for k in range(1, b + 1):
        for i in range(g - 1, -1, -1):
            js = np.arange(i + 1, g + 1)
            seg = prefix[js] - prefix[i]
            cost = (seg - target) ** 2 + f[k - 1, js]
            cost = np.where(seg >= floor, cost, inf)
            if np.all(~np.isfinite(cost)):
                continue
            pos = int(np.argmin(cost))
            f[k, i] = cost[pos]
            choice[k, i] = js[pos]
    if not np.isfinite(f[b, 0]):
        return None
    starts = [0]
    i = 0
    for k in range(b, 1, -1):
        i = int(choice[k, i])
        starts.append(i)
    return starts


def bin_index_for_groups(starts: Sequence[int], n_groups: int) -> np.ndarray:
    idx = np.zeros(n_groups, dtype=np.int64)
    for j, s in enumerate(starts):
        idx[s:] = j
    return idx


def bin_table(groups: TieGroups, starts: Sequence[int]) -> dict[str, np.ndarray]:
    """Return W_j, pred_j and rate_j for each bin. W_j > 0 always holds (empty bins cannot form)."""
    gi = bin_index_for_groups(starts, groups.p.size)
    nb = len(starts)
    weight = np.bincount(gi, weights=groups.weight, minlength=nb)
    wp = np.bincount(gi, weights=groups.weighted_p, minlength=nb)
    wy = np.bincount(gi, weights=groups.weighted_y, minlength=nb)
    return {"weight": weight, "pred": wp / weight, "rate": wy / weight, "group_bin": gi}


def weighted_ece_from_bins(weight: np.ndarray, pred: np.ndarray, rate: np.ndarray) -> float:
    total = math.fsum(np.asarray(weight, dtype=float).tolist())
    if total <= 0:
        return float("nan")
    return math.fsum((weight / total * np.abs(rate - pred)).tolist())


def weighted_brier_difference(groups: TieGroups) -> dict[str, float]:
    """Return the weighted Brier of p, the base-rate Brier, and D = Brier(p) - Brier(base)."""
    n = groups.weight
    s = groups.weighted_y
    p = groups.p
    total = math.fsum(n.tolist())
    if total <= 0:
        return {"brier": float("nan"), "base_brier": float("nan"), "difference": float("nan")}
    brier = math.fsum((s * (1 - p) ** 2 + (n - s) * p ** 2).tolist()) / total
    base = math.fsum(s.tolist()) / total
    base_brier = base * (1 - base)
    return {"brier": brier, "base_brier": base_brier, "difference": brier - base_brier}


def point_monotone(rate: Sequence[float] | np.ndarray, tol: float = MONOTONE_POINT_TOL) -> bool:
    """Point check that bin rates are non-decreasing within ``tol`` (same rule as the incumbent helper)."""
    r = np.asarray(rate, dtype=float)
    if tol < 0:
        raise ValueError("tolerance_negative")
    return bool(np.all(np.diff(r) >= -tol))


def _pair_drops(rate: np.ndarray) -> np.ndarray:
    """Return delta_jk = rate_j - rate_k for j < k along the last axis. Positive means a decrease."""
    nb = rate.shape[-1]
    j, k = np.triu_indices(nb, 1)
    return rate[..., j] - rate[..., k]


def maxstat_monotonicity(
    observed_rate: np.ndarray, replicate_rate: np.ndarray, valid: np.ndarray, level: float = 0.95
) -> dict[str, Any]:
    """The draft's max-statistic test.

    z_r = max_{j<k}(delta*_jk - delta_jk) and c = max(0, z_(ceil(level*R_valid))).
    The curve is broken when max_{j<k}(delta_jk - c) > 0. With fewer than two
    bins there are no pairs, so the curve is trivially not broken.
    """
    obs = np.asarray(observed_rate, dtype=float)
    if obs.size < 2:
        return {"broken": False, "critical": 0.0, "max_drop": 0.0, "pairs": 0}
    drops = _pair_drops(obs)
    rep = np.asarray(replicate_rate, dtype=float)[np.asarray(valid, dtype=bool)]
    if rep.shape[0] == 0:
        return {"broken": None, "critical": float("nan"), "max_drop": float(drops.max()), "pairs": int(drops.size)}
    z = np.max(_pair_drops(rep) - drops[None, :], axis=1)
    critical = max(0.0, order_statistic_quantile(z, level))
    return {"broken": bool(np.max(drops - critical) > 0), "critical": critical,
            "max_drop": float(drops.max()), "pairs": int(drops.size)}


# ── weighted logistic recalibration (batched, fractional counts) ─────────────

def _loglik(a: np.ndarray, b: np.ndarray, x: np.ndarray, n: np.ndarray, s: np.ndarray) -> np.ndarray:
    eta = a[:, None] + b[:, None] * x[None, :]
    return np.sum(-s * np.logaddexp(0.0, -eta) - (n - s) * np.logaddexp(0.0, eta), axis=1)


def fit_logistic_recalibration(
    p_groups: np.ndarray, n: np.ndarray, s: np.ndarray, max_iter: int = 100, tol: float = 1e-10
) -> dict[str, np.ndarray]:
    """Weighted MLE of logit pi = a + b * logit p for each row of (n, s).

    ``n`` and ``s`` have shape (R, G) or (G,). The result contains a, b and
    ``converged``. A row is not converged when the slope is unidentified (fewer
    than two groups carry weight), when all weight sits on one label value,
    when Newton fails, or when a coefficient exceeds the separation limit.
    """
    x = logit(np.clip(np.asarray(p_groups, dtype=float), _LOGIT_CLIP, 1 - _LOGIT_CLIP))
    n2 = np.atleast_2d(np.asarray(n, dtype=float))
    s2 = np.atleast_2d(np.asarray(s, dtype=float))
    r = n2.shape[0]
    a = np.zeros(r)
    b = np.ones(r)
    total = n2.sum(axis=1)
    succ = s2.sum(axis=1)
    support_groups = (n2 > 0).sum(axis=1)
    ok = (total > 0) & (succ > 0) & (succ < total) & (support_groups >= 2)
    active = ok.copy()
    converged = np.zeros(r, dtype=bool)
    ll = _loglik(a, b, x, n2, s2)
    for _ in range(max_iter):
        if not np.any(active):
            break
        eta = a[:, None] + b[:, None] * x[None, :]
        mu = expit(eta)
        resid = s2 - n2 * mu
        g0 = resid.sum(axis=1)
        g1 = (resid * x[None, :]).sum(axis=1)
        wt = n2 * mu * (1 - mu)
        h00 = wt.sum(axis=1)
        h01 = (wt * x[None, :]).sum(axis=1)
        h11 = (wt * x[None, :] ** 2).sum(axis=1)
        det = h00 * h11 - h01 * h01
        bad = active & ~(det > 1e-14 * np.maximum(1.0, h00 * h11))
        active &= ~bad
        safe = np.where(det > 0, det, 1.0)
        da = (h11 * g0 - h01 * g1) / safe
        db = (h00 * g1 - h01 * g0) / safe
        da = np.where(active, da, 0.0)
        db = np.where(active, db, 0.0)
        step = np.ones(r)
        new_a, new_b = a + da, b + db
        new_ll = _loglik(new_a, new_b, x, n2, s2)
        for _h in range(40):
            worse = active & (new_ll < ll - 1e-12)
            if not np.any(worse):
                break
            step = np.where(worse, step / 2, step)
            new_a = np.where(worse, a + step * da, new_a)
            new_b = np.where(worse, b + step * db, new_b)
            new_ll = np.where(worse, _loglik(new_a, new_b, x, n2, s2), new_ll)
        moved = np.maximum(np.abs(new_a - a), np.abs(new_b - b))
        a = np.where(active, new_a, a)
        b = np.where(active, new_b, b)
        ll = np.where(active, new_ll, ll)
        done = active & (moved < tol)
        converged |= done
        active &= ~done
        blown = active & ((np.abs(a) > _COEF_LIMIT) | (np.abs(b) > _COEF_LIMIT))
        active &= ~blown
    converged &= ok & (np.abs(a) <= _COEF_LIMIT) & (np.abs(b) <= _COEF_LIMIT)
    return {"a": a, "b": b, "converged": converged}


def implied_ece(a: np.ndarray, b: np.ndarray, p_groups: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Model-implied calibration error: the weighted mean of |sigma(a + b*logit p) - p| (per row)."""
    x = logit(np.clip(np.asarray(p_groups, dtype=float), _LOGIT_CLIP, 1 - _LOGIT_CLIP))
    n2 = np.atleast_2d(np.asarray(n, dtype=float))
    a1 = np.atleast_1d(a)
    b1 = np.atleast_1d(b)
    fitted = expit(a1[:, None] + b1[:, None] * x[None, :])
    tot = n2.sum(axis=1)
    return np.sum(n2 * np.abs(fitted - p_groups[None, :]), axis=1) / np.where(tot > 0, tot, np.nan)


# ── session x group matrices and the three decision rules ────────────────────

@dataclass(frozen=True)
class Panel:
    groups: TieGroups
    session_weight: np.ndarray    # (T, G): sum w per (anchor session, group)
    session_success: np.ndarray   # (T, G): sum w*y per (anchor session, group)
    n_sessions: int


def build_panel(p, y, w, anchor_positions) -> Panel:
    """Aggregate rows to calendar anchor sessions x whole-tie groups. Empty sessions stay as zero rows."""
    groups = tie_groups(p, w, y)
    anchors = np.array(anchor_positions, dtype=np.int64, copy=True)
    if anchors.shape != np.asarray(p).shape:
        raise ValueError("anchor_shape_mismatch")
    keep = groups.row_group >= 0
    if not np.any(keep):
        raise ValueError("population_empty")
    first = int(anchors[keep].min())
    t = int(anchors[keep].max()) - first + 1
    if t > MAX_POSITIONS:
        raise ValueError("window_exceeds_bound")
    g = groups.p.size
    wa = np.asarray(w, dtype=float)[keep]
    ya = np.asarray(y, dtype=float)[keep]
    cell = (anchors[keep] - first) * g + groups.row_group[keep]
    sw = np.bincount(cell, weights=wa, minlength=t * g).reshape(t, g)
    sy = np.bincount(cell, weights=wa * ya, minlength=t * g).reshape(t, g)
    return Panel(groups, sw, sy, t)


def _ci(values: np.ndarray, lo: float = 0.05, hi: float = 0.95) -> tuple[float, float]:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return (float("nan"), float("nan"))
    return (order_statistic_quantile(v, lo), order_statistic_quantile(v, hi))


def calibration_error_report(panel: Panel, counts: np.ndarray) -> dict[str, Any]:
    """Return the weighted ECE (whole-tie bins, floor 0) and implied ECE with block-bootstrap intervals.

    This report is always produced, even when no verdict is supportable (requirement 4).
    """
    g = panel.groups
    starts = whole_tie_partition(g.weight, N_BINS, 0.0)
    tab = bin_table(g, starts)
    ece = weighted_ece_from_bins(tab["weight"], tab["pred"], tab["rate"])
    nb = counts @ panel.session_weight
    sb = counts @ panel.session_success
    gi = tab["group_bin"]
    nbin = len(starts)
    bw = np.zeros((nb.shape[0], nbin))
    bp = np.zeros((nb.shape[0], nbin))
    by = np.zeros((nb.shape[0], nbin))
    for j in range(nbin):
        cols = gi == j
        bw[:, j] = nb[:, cols].sum(axis=1)
        bp[:, j] = (nb[:, cols] * g.p[cols][None, :]).sum(axis=1)
        by[:, j] = sb[:, cols].sum(axis=1)
    valid = np.all(bw > 0, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rep_ece = np.sum(bw / bw.sum(axis=1, keepdims=True) * np.abs(by / bw - bp / bw), axis=1)
    fit = fit_logistic_recalibration(g.p, g.weight, g.weighted_y)
    rep_fit = fit_logistic_recalibration(g.p, nb, sb)
    point_implied = float(implied_ece(fit["a"], fit["b"], g.p, g.weight)[0]) if fit["converged"][0] else float("nan")
    rep_implied = np.where(rep_fit["converged"], implied_ece(rep_fit["a"], rep_fit["b"], g.p, nb), np.nan)
    return {
        "binned_ece": ece,
        "binned_ece_interval_90": _ci(rep_ece[valid]),
        "implied_ece": point_implied,
        "implied_ece_interval_90": _ci(rep_implied),
        "recalibration_a": float(fit["a"][0]) if fit["converged"][0] else None,
        "recalibration_b": float(fit["b"][0]) if fit["converged"][0] else None,
        "n_bins": nbin,
        "valid_replicate_fraction": float(valid.mean()),
        "note": "binned ECE intervals are biased upward at small support; reported, not a verdict",
    }


def rule_incumbent(panel: Panel, horizon: int, counts: np.ndarray) -> dict[str, Any]:
    """R_inc: the PR #8385 draft rule as written (PREREG §12)."""
    g = panel.groups
    total = math.fsum(g.weight.tolist())
    blocks = block_count(panel.n_sessions, horizon)
    out: dict[str, Any] = {"rule": "R_inc", "native_effective_n": total, "anchor_blocks": blocks}
    starts = whole_tie_partition(g.weight, N_BINS, DRAFT_BIN_FLOOR) if g.p.size else None
    reasons = []
    if total < DRAFT_TOTAL_FLOOR:
        reasons.append("total_below_200")
    if blocks < DRAFT_MIN_BLOCKS:
        reasons.append("blocks_below_20")
    if starts is None:
        reasons.append("bin_floor_infeasible")
    else:
        gi = bin_index_for_groups(starts, g.p.size)
        anchors_per_bin = [int(np.count_nonzero(panel.session_weight[:, gi == j].sum(axis=1) > 0))
                           for j in range(len(starts))]
        out["anchors_per_bin"] = anchors_per_bin
        if min(anchors_per_bin) < 20:
            reasons.append("anchors_per_bin_below_20")
    if reasons:
        out.update({"decision": "NO_VERDICT", "reason": "CALIBRATION_INSUFFICIENT:" + ",".join(reasons)})
        return out
    tab = bin_table(g, starts)
    ece = weighted_ece_from_bins(tab["weight"], tab["pred"], tab["rate"])
    brier = weighted_brier_difference(g)
    nb = counts @ panel.session_weight
    sb = counts @ panel.session_success
    gi = tab["group_bin"]
    nbin = len(starts)
    bw = np.stack([nb[:, gi == j].sum(axis=1) for j in range(nbin)], axis=1)
    by = np.stack([sb[:, gi == j].sum(axis=1) for j in range(nbin)], axis=1)
    valid = np.all(bw > 0, axis=1)
    frac = float(valid.mean())
    out.update({"ece": ece, "brier_difference": brier["difference"], "valid_replicate_fraction": frac})
    if frac < DRAFT_VALID_FRACTION:
        out.update({"decision": "NO_VERDICT", "reason": "CALIBRATION_INSUFFICIENT:valid_replicates_below_95pct"})
        return out
    with np.errstate(invalid="ignore", divide="ignore"):
        rep_rate = by / bw
    mono = maxstat_monotonicity(tab["rate"], rep_rate, valid)
    out["monotonicity"] = mono
    passed = ece < ECE_THRESHOLD and brier["difference"] < 0 and mono["broken"] is False
    out.update({"decision": "PASS" if passed else "FAIL",
                "reason": "all_criteria_met" if passed else "criterion_failed"})
    return out


def _alt_support(panel: Panel, horizon: int) -> list[str]:
    total = math.fsum(panel.groups.weight.tolist())
    reasons = []
    if total < BUCKET_FLOOR:
        reasons.append("total_below_bucket_floor_30")
    if block_count(panel.n_sessions, horizon) < DRAFT_MIN_BLOCKS:
        reasons.append("blocks_below_20")
    return reasons


def rule_recalibration(panel: Panel, horizon: int, counts: np.ndarray) -> dict[str, Any]:
    """R_alt: weighted logistic recalibration with anchor-block bootstrap and a simultaneous misfit flag."""
    g = panel.groups
    out: dict[str, Any] = {"rule": "R_alt", "native_effective_n": math.fsum(g.weight.tolist()),
                           "anchor_blocks": block_count(panel.n_sessions, horizon)}
    reasons = _alt_support(panel, horizon)
    fit = fit_logistic_recalibration(g.p, g.weight, g.weighted_y)
    nb = counts @ panel.session_weight
    sb = counts @ panel.session_success
    rep = fit_logistic_recalibration(g.p, nb, sb)
    tot = nb.sum(axis=1)
    succ = sb.sum(axis=1)
    valid = rep["converged"] & (succ > 0) & (succ < tot)
    frac = float(valid.mean())
    out["valid_replicate_fraction"] = frac
    if not fit["converged"][0]:
        reasons.append("point_fit_not_identified")
    if frac < DRAFT_VALID_FRACTION:
        reasons.append("valid_replicates_below_95pct")
    if fit["converged"][0]:
        point_i = float(implied_ece(fit["a"], fit["b"], g.p, g.weight)[0])
        rep_i = implied_ece(rep["a"], rep["b"], g.p, nb)[valid]
        i_lo, i_hi = _ci(rep_i)
        bd = weighted_brier_difference(g)["difference"]
        with np.errstate(invalid="ignore", divide="ignore"):
            rep_brier = (np.sum(sb * (1 - g.p) ** 2 + (nb - sb) * g.p ** 2, axis=1) / tot
                         - (succ / tot) * (1 - succ / tot))
        d_lo, d_hi = _ci(rep_brier[valid])
        starts = whole_tie_partition(g.weight, N_BINS, 0.0)
        gi = bin_index_for_groups(starts, g.p.size)
        x = logit(np.clip(g.p, _LOGIT_CLIP, 1 - _LOGIT_CLIP))
        fitted = expit(fit["a"][0] + fit["b"][0] * x)
        nbin = len(starts)
        w_j = np.array([g.weight[gi == j].sum() for j in range(nbin)])
        r_j = np.array([(g.weighted_y[gi == j].sum() - (g.weight[gi == j] * fitted[gi == j]).sum()) / w_j[j]
                        for j in range(nbin)])
        rep_fitted = expit(rep["a"][:, None] + rep["b"][:, None] * x[None, :])
        rep_w = np.stack([nb[:, gi == j].sum(axis=1) for j in range(nbin)], axis=1)
        rep_r = np.stack([(sb[:, gi == j].sum(axis=1) - (nb[:, gi == j] * rep_fitted[:, gi == j]).sum(axis=1))
                          for j in range(nbin)], axis=1)
        ok_rows = valid & np.all(rep_w > 0, axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            rep_r = rep_r / rep_w
        band = order_statistic_quantile(np.max(np.abs(rep_r[ok_rows] - r_j[None, :]), axis=1), 0.95) \
            if np.any(ok_rows) else float("inf")
        flagged = [int(j) for j in range(nbin)
                   if w_j[j] >= CELL_FLOOR and abs(r_j[j]) > band and abs(r_j[j]) >= ECE_THRESHOLD]
        out.update({
            "a": float(fit["a"][0]), "b": float(fit["b"][0]),
            "implied_ece": point_i, "implied_ece_interval_90": (i_lo, i_hi),
            "brier_difference": bd, "brier_difference_interval_90": (d_lo, d_hi),
            "bin_residuals": r_j.tolist(), "bin_weights": w_j.tolist(),
            "misfit_band": band, "misfit_bins": flagged,
        })
    if reasons:
        out.update({"decision": "NO_VERDICT", "reason": "NOT_YET_ESTIMABLE:" + ",".join(reasons)})
        return out
    i_lo, i_hi = out["implied_ece_interval_90"]
    d_lo, d_hi = out["brier_difference_interval_90"]
    if i_lo >= ECE_THRESHOLD or out["misfit_bins"] or d_lo >= 0:
        out.update({"decision": "FAIL", "reason": "miscalibration_supported"})
    elif i_hi < ECE_THRESHOLD and d_hi < 0:
        out.update({"decision": "PASS", "reason": "calibration_supported"})
    else:
        out.update({"decision": "NO_VERDICT", "reason": "inconclusive_interval"})
    return out


def pooled_bin_diagnostic(panel: Panel, counts: np.ndarray) -> dict[str, Any]:
    """Partially pooled bin deviations (empirical Bayes toward the recalibration line).

    tau^2 and the line are re-estimated in every replicate. The bootstrap
    variance v_j comes from the same replicate set and is held fixed. These
    estimates are for display and de-escalation only (``can_promote`` is
    always False).
    """
    g = panel.groups
    starts = whole_tie_partition(g.weight, N_BINS, 0.0)
    gi = bin_index_for_groups(starts, g.p.size)
    nbin = len(starts)
    x = logit(np.clip(g.p, _LOGIT_CLIP, 1 - _LOGIT_CLIP))

    def pooled(n: np.ndarray, s: np.ndarray, fit: dict[str, np.ndarray], v: np.ndarray | None):
        fitted = expit(fit["a"][:, None] + fit["b"][:, None] * x[None, :])
        w = np.stack([n[:, gi == j].sum(axis=1) for j in range(nbin)], axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            pred = np.stack([(n[:, gi == j] * g.p[gi == j][None, :]).sum(axis=1) for j in range(nbin)], axis=1) / w
            rate = np.stack([s[:, gi == j].sum(axis=1) for j in range(nbin)], axis=1) / w
            line = np.stack([(n[:, gi == j] * fitted[:, gi == j]).sum(axis=1) for j in range(nbin)], axis=1) / w
        d = rate - pred
        m = line - pred
        share = w / w.sum(axis=1, keepdims=True)
        if v is None:
            return d, m, share, None, None
        tau2 = np.maximum(0.0, np.sum(share * (d - m) ** 2, axis=1) - np.sum(share * v[None, :], axis=1))
        kappa = tau2[:, None] / (tau2[:, None] + v[None, :])
        kappa = np.where(np.isfinite(kappa), kappa, 0.0)
        shrunk = m + kappa * (d - m)
        return d, m, share, shrunk, np.sum(share * np.abs(shrunk), axis=1)

    fit = fit_logistic_recalibration(g.p, g.weight, g.weighted_y)
    nb = counts @ panel.session_weight
    sb = counts @ panel.session_success
    rep_fit = fit_logistic_recalibration(g.p, nb, sb)
    d_rep, _, _, _, _ = pooled(nb, sb, rep_fit, None)
    ok = rep_fit["converged"] & np.all(np.isfinite(d_rep), axis=1)
    if not fit["converged"][0] or not np.any(ok):
        return {"available": False, "reason": "recalibration_not_identified", "can_promote": False}
    v = np.var(d_rep[ok], axis=0)
    d, m, share, shrunk, pooled_ece = pooled(g.weight[None, :], g.weighted_y[None, :], fit, v)
    rep_sub = {"a": rep_fit["a"][ok], "b": rep_fit["b"][ok]}
    _, _, _, _, rep_pooled = pooled(nb[ok], sb[ok], rep_sub, v)
    return {
        "available": True,
        "raw_deviation": d[0].tolist(),
        "line_deviation": m[0].tolist(),
        "pooled_deviation": shrunk[0].tolist(),
        "bootstrap_variance": v.tolist(),
        "pooled_ece": float(pooled_ece[0]),
        "pooled_ece_interval_90": _ci(rep_pooled),
        "valid_replicate_fraction": float(ok.mean()),
        "can_promote": False,
    }


def rule_pooled(panel: Panel, horizon: int, counts: np.ndarray) -> dict[str, Any]:
    """R_pool: the generic partially pooled bin ECE decision. It is evaluated for comparison; Q06 does not propose it."""
    out: dict[str, Any] = {"rule": "R_pool"}
    reasons = _alt_support(panel, horizon)
    diag = pooled_bin_diagnostic(panel, counts)
    out["diagnostic"] = diag
    if not diag.get("available"):
        reasons.append("pooled_not_available")
    elif diag["valid_replicate_fraction"] < DRAFT_VALID_FRACTION:
        reasons.append("valid_replicates_below_95pct")
    if reasons:
        out.update({"decision": "NO_VERDICT", "reason": "NOT_YET_ESTIMABLE:" + ",".join(reasons)})
        return out
    lo, hi = diag["pooled_ece_interval_90"]
    bd = weighted_brier_difference(panel.groups)["difference"]
    if lo >= ECE_THRESHOLD:
        out.update({"decision": "FAIL", "reason": "pooled_ece_lower_at_or_above_threshold"})
    elif hi < ECE_THRESHOLD and bd < 0:
        out.update({"decision": "PASS", "reason": "pooled_ece_upper_below_threshold"})
    else:
        out.update({"decision": "NO_VERDICT", "reason": "inconclusive_interval"})
    return out


def proposed_decision(alt: dict[str, Any], pooled: dict[str, Any]) -> str:
    """The amendment's combined decision. Pooling only de-escalates and never creates a PASS."""
    base = alt.get("decision", "NO_VERDICT")
    if base not in DECISIONS:
        raise ValueError("decision_invalid")
    if base == "PASS" and pooled.get("decision") == "FAIL":
        return "NO_VERDICT"
    return base


def evaluate_rules(p, y, w, anchor_positions, horizon: int, n_rep: int, rng: np.random.Generator) -> dict[str, Any]:
    """Run R_inc, R_alt and R_pool on one sample with a shared block-bootstrap draw (block length = H)."""
    if horizon < 1:
        raise ValueError("horizon_invalid")
    panel = build_panel(p, y, w, anchor_positions)
    counts = circular_block_counts(panel.n_sessions, horizon, n_rep, rng)
    inc = rule_incumbent(panel, horizon, counts)
    alt = rule_recalibration(panel, horizon, counts)
    pool = rule_pooled(panel, horizon, counts)
    return {"R_inc": inc, "R_alt": alt, "R_pool": pool,
            "proposed": proposed_decision(alt, pool),
            "error_report": calibration_error_report(panel, counts),
            "support": support_summary(np.asarray(w, dtype=float), np.asarray(anchor_positions), horizon)}


# ── review record (requirement 6) ────────────────────────────────────────────

@dataclass(frozen=True)
class ReviewRecord:
    opus_recommendation: str
    statistical_acceptance: str
    fable_ratification: str

    def as_dict(self) -> dict[str, str]:
        return {"opus_recommendation": self.opus_recommendation,
                "statistical_acceptance": self.statistical_acceptance,
                "fable_ratification": self.fable_ratification}


def review_record(
    opus_recommendation: str = "NONE",
    statistical_acceptance: str = "NOT_REVIEWED",
    fable_ratification: str = "UNRATIFIED",
) -> ReviewRecord:
    """Return three independent states. No state is derived from another, and none activates anything."""
    if opus_recommendation not in OPUS_RECOMMENDATION_STATES:
        raise ValueError("opus_recommendation_invalid")
    if statistical_acceptance not in STATISTICAL_ACCEPTANCE_STATES:
        raise ValueError("statistical_acceptance_invalid")
    if fable_ratification not in FABLE_RATIFICATION_STATES:
        raise ValueError("fable_ratification_invalid")
    return ReviewRecord(opus_recommendation, statistical_acceptance, fable_ratification)


# ── synthetic panel simulator (seeded, integer clocks only) ──────────────────

TRUTHS = ("T0", "T1", "T2", "T3")
REGIMES = ("steady", "bursty")


def truth_probability(p: np.ndarray, truth: str) -> np.ndarray:
    pa = np.asarray(p, dtype=float)
    if truth == "T0":
        return pa.copy()
    lp = logit(np.clip(pa, _LOGIT_CLIP, 1 - _LOGIT_CLIP))
    if truth == "T1":
        return expit(0.5 * lp)
    if truth == "T2":
        return expit(lp - 0.6)
    if truth == "T3":
        band = (pa >= 0.55 - 1e-12) & (pa <= 0.75 + 1e-12)
        return np.where(band, pa - 0.15, pa)
    raise ValueError("truth_unknown")


def simulate_panel(
    rng: np.random.Generator,
    n_sessions: int,
    horizon: int,
    truth: str,
    regime: str,
    copula_rho: float = 0.5,
) -> dict[str, np.ndarray]:
    """Simulate one sparse correlated panel under the native weight law.

    The simulation draws, in order:
    * units per session (steady Poisson(3), or bursty Gamma(0.5, 6)-mixed Poisson);
    * one event per unit;
    * p from Beta(2,3), or Beta(3,2) on bursty above-median sessions, rounded to
      a 0.05 grid and clipped to [0.05, 0.95];
    * labels from a Gaussian copula with a shared window shock, so the marginal
      P(y=1 | p) equals pi(p) exactly.
    """
    t = int(n_sessions)
    h = int(horizon)
    if t < 1 or h < 1 or t + h + 2 > MAX_POSITIONS:
        raise ValueError("simulation_dimensions_invalid")
    if regime not in REGIMES or truth not in TRUTHS:
        raise ValueError("simulation_arguments_invalid")
    if not 0 <= copula_rho < 1:
        raise ValueError("copula_rho_invalid")
    length = h + 1
    if regime == "steady":
        lam = np.full(t, 3.0)
    else:
        lam = rng.gamma(0.5, 6.0, size=t)
    n_units = rng.poisson(lam)
    anchors = np.repeat(np.arange(t), n_units)
    roots = np.concatenate([np.arange(k) for k in n_units]) if anchors.size else np.zeros(0, dtype=np.int64)
    hot = lam > np.median(lam) if regime == "bursty" else np.zeros(t, dtype=bool)
    hot_rows = hot[anchors]
    raw = np.where(hot_rows, rng.beta(3.0, 2.0, size=anchors.size), rng.beta(2.0, 3.0, size=anchors.size))
    p = np.clip(np.round(raw / 0.05) * 0.05, 0.05, 0.95)
    p = np.round(p, 2)
    e = rng.standard_normal(t + length)
    ce = np.concatenate(([0.0], np.cumsum(e)))
    eps = (ce[anchors + length] - ce[anchors]) / math.sqrt(length)
    z = copula_rho * eps + math.sqrt(1 - copula_rho ** 2) * rng.standard_normal(anchors.size)
    y = (ndtr(z) < truth_probability(p, truth)).astype(float)
    end = anchors + h
    if anchors.size == 0:
        return {"p": p, "y": y, "w": np.zeros(0), "anchor": anchors, "end": end, "root": roots}
    units = native_units(anchors, end, roots, exact=False)
    return {"p": p, "y": y, "w": units.event_weight, "anchor": anchors, "end": end, "root": roots}


def true_calibration_gap(p: np.ndarray, w: np.ndarray, truth: str) -> float:
    """Weighted mean of |pi(p) - p| under the simulated truth (a materiality reference)."""
    pa = np.asarray(p, dtype=float)
    wa = np.asarray(w, dtype=float)
    if wa.sum() <= 0:
        return float("nan")
    return float(np.sum(wa * np.abs(truth_probability(pa, truth) - pa)) / wa.sum())
