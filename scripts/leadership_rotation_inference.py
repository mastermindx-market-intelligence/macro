"""DEVELOPMENT HARNESS — no verdict authority.

Pre-registration: research/LEADERSHIP_ROTATION_PREREG_V1.md
Frozen at commit fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb (§7–§8 dependence & uncertainty).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

SEED = 20261014
REPS = 2000
MEAN_BLOCK = 21
CLUSTER_RADIUS = 10
ALPHA_ONE_SIDED = 0.025
MIN_HONEST_N = 20
COVERAGE_MIN = 0.80
H1A_DELAY_MARGIN = 5
H1A_BURDEN_NI = 0.5
H1A_DETECTION_NI = 0.05
H1B_BURDEN_CUT = 0.25
H1B_DETECTION_NI = 0.10
MARGIN_H2 = 0.0050
MARGIN_H3 = 0.0025
H2_FALSE_START_NI = 0.05
N_TESTS = 6

Item = Tuple[str, str, int]


def single_linkage_clusters(
    items: Sequence[Item],
    radius: int = CLUSTER_RADIUS,
) -> Tuple[List[int], Dict[int, int]]:
    """Within-group single-linkage clusters by consecutive index gaps (ORCH-SCI §8 / R13)."""
    if not items:
        return [], {}

    by_group: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for pos, (group, _pair_id, index) in enumerate(items):
        by_group[group].append((index, pos))

    cluster_meta: List[Tuple[str, int, List[int]]] = []

    for group in sorted(by_group.keys()):
        sorted_entries = sorted(by_group[group], key=lambda t: t[0])
        positions_in_cluster = [sorted_entries[0][1]]
        cluster_coord = sorted_entries[0][0]
        prev_index = sorted_entries[0][0]

        for index, pos in sorted_entries[1:]:
            if index - prev_index <= radius:
                positions_in_cluster.append(pos)
                cluster_coord = min(cluster_coord, index)
                prev_index = index
            else:
                cluster_meta.append((group, cluster_coord, positions_in_cluster))
                positions_in_cluster = [pos]
                cluster_coord = index
                prev_index = index
        cluster_meta.append((group, cluster_coord, positions_in_cluster))

    cluster_meta.sort(key=lambda t: (t[0], t[1]))
    coords: Dict[int, int] = {i: coord for i, (_g, coord, _p) in enumerate(cluster_meta)}
    labels = [0] * len(items)
    for label, (_g, _c, positions) in enumerate(cluster_meta):
        for pos in positions:
            labels[pos] = label

    return labels, coords


def shared_leg_components(pair_legs: Dict[str, Tuple[str, str]]) -> int:
    """Connected components of pairs sharing any leg — sensitivity only (R13)."""
    if not pair_legs:
        return 0
    pair_ids = list(pair_legs.keys())
    leg_to_pairs: Dict[str, List[int]] = defaultdict(list)
    for i, pid in enumerate(pair_ids):
        num, den = pair_legs[pid]
        leg_to_pairs[num].append(i)
        leg_to_pairs[den].append(i)

    parent = list(range(len(pair_ids)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for pairs in leg_to_pairs.values():
        for j in range(1, len(pairs)):
            union(pairs[0], pairs[j])

    roots = {find(i) for i in range(len(pair_ids))}
    return len(roots)


def stationary_bootstrap_weights(
    n: int,
    mean_block: float = MEAN_BLOCK,
    reps: int = REPS,
    seed: int = SEED,
) -> np.ndarray:
    """Paired calendar bootstrap weights (R9); vectorized idx, frozen RNG order."""
    rng = np.random.default_rng(seed)
    p_restart = 1.0 / mean_block
    W = np.empty((reps, n), dtype=np.int32)
    positions = np.arange(n, dtype=np.int64)

    for r in range(reps):
        u = rng.random(n)
        s = rng.integers(0, n, size=n)
        restart = u < p_restart
        restart[0] = True
        r_k = np.maximum.accumulate(np.where(restart, positions, 0))
        idx = (s[r_k] + positions - r_k) % n
        W[r] = np.bincount(idx.astype(np.intp), minlength=n).astype(np.int32)

    return W


def item_weights(W: np.ndarray, coords_of_items: Sequence[int]) -> np.ndarray:
    """Column j is the bootstrap weight at each item's cluster coordinate (R9)."""
    coords = np.asarray(coords_of_items, dtype=np.intp)
    return W[:, coords]


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    total = float(np.sum(weights))
    if total == 0.0:
        return float("nan")
    return float(np.sum(values * weights) / total)


def paired_replicate_contrast(
    values_a: np.ndarray,
    values_b: np.ndarray,
    W: np.ndarray,
    coords_of_items: Sequence[int],
) -> Tuple[np.ndarray, np.ndarray]:
    """Paired bootstrap contrast: same Wm for both arms (R9)."""
    Wm = item_weights(W, coords_of_items)
    diff_reps = replicate_means(values_a, Wm) - replicate_means(values_b, Wm)
    contrast_reps = replicate_means(values_a - values_b, Wm)
    return diff_reps, contrast_reps


def replicate_means(values: np.ndarray, Wm: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    Wm = np.asarray(Wm, dtype=np.float64)
    totals = Wm.sum(axis=1)
    numer = Wm @ values
    out = np.full(Wm.shape[0], np.nan, dtype=np.float64)
    np.divide(numer, totals, out=out, where=totals > 0)
    return out


def replicate_lower_median(values: np.ndarray, Wm: np.ndarray) -> np.ndarray:
    """Lower weighted median per bootstrap replicate (R8 delay)."""
    values = np.asarray(values, dtype=np.float64)
    Wm = np.asarray(Wm, dtype=np.float64)
    reps, _ = Wm.shape
    order = np.argsort(values)
    sorted_v = values[order]
    sorted_w = Wm[:, order]
    cum = np.cumsum(sorted_w, axis=1)
    totals = Wm.sum(axis=1)
    half = totals[:, np.newaxis] / 2.0
    reached = cum >= half
    idx = np.argmax(reached, axis=1)
    out = sorted_v[idx].astype(np.float64)
    out[totals == 0] = np.nan
    return out


def one_sided_p(rep_stats: Sequence[float]) -> Tuple[float, int]:
    arr = np.asarray(rep_stats, dtype=np.float64)
    n_nan = int(np.isnan(arr).sum())
    le_zero = int(np.sum((arr <= 0) | np.isnan(arr)))
    p = (1.0 + le_zero) / (1.0 + len(arr))
    return p, n_nan


def interval_90(rep_stats: Sequence[float]) -> Tuple[float, float]:
    finite = np.asarray(rep_stats, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(finite, [5.0, 95.0])
    return float(lo), float(hi)


def lower_bound(rep_stats: Sequence[float]) -> float:
    finite = np.asarray(rep_stats, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return float("nan")
    return float(np.percentile(finite, 2.5))


def holm(pvals: Sequence[float]) -> List[float]:
    """Standard Holm step-down adjusted p-values (R11, m = N_TESTS family)."""
    m = len(pvals)
    p = np.asarray(pvals, dtype=np.float64)
    order = np.argsort(p)
    sorted_p = p[order]
    adj_sorted = np.empty(m, dtype=np.float64)
    running = 0.0
    for k in range(m):
        candidate = min(1.0, (m - k) * sorted_p[k])
        running = max(running, candidate)
        adj_sorted[k] = running
    out = np.empty(m, dtype=np.float64)
    out[order] = adj_sorted
    return out.tolist()


def stability_thirds(
    session_indices: Sequence[int],
    cluster_coords: Sequence[int],
    cluster_values_fn: Callable[[np.ndarray], float],
    full_point: float,
) -> Dict[str, Union[float, bool, Tuple[float, float, float]]]:
    """§7 stability via session-count thirds on cluster coordinates."""
    s = np.sort(np.asarray(session_indices, dtype=np.int64))
    n = len(s)
    if n == 0:
        return {
            "third_1": float("nan"),
            "third_2": float("nan"),
            "third_3": float("nan"),
            "holds": False,
        }
    b1 = int(s[n // 3])
    b2 = int(s[(2 * n) // 3])
    coords = np.asarray(cluster_coords, dtype=np.int64)
    masks = [
        coords < b1,
        (coords >= b1) & (coords < b2),
        coords >= b2,
    ]
    points = tuple(cluster_values_fn(m) for m in masks)
    if not np.isfinite(full_point):
        same_sign = 0
    else:
        same_sign = sum(
            1
            for pt in points
            if np.isfinite(pt) and ((pt > 0 and full_point > 0) or (pt < 0 and full_point < 0))
        )
    holds = same_sign >= 2
    return {
        "third_1": points[0],
        "third_2": points[1],
        "third_3": points[2],
        "holds": holds,
    }


def h2_statistic(a1_vals: np.ndarray, b1_vals: np.ndarray, b2_vals: np.ndarray) -> float:
    return float(np.mean(a1_vals) - max(np.mean(b1_vals), np.mean(b2_vals)))


def h2_replicates(
    a1_vals: np.ndarray,
    a1_W: np.ndarray,
    b1_vals: np.ndarray,
    b1_W: np.ndarray,
    b2_vals: np.ndarray,
    b2_W: np.ndarray,
) -> np.ndarray:
    m_a1 = replicate_means(a1_vals, a1_W)
    m_b1 = replicate_means(b1_vals, b1_W)
    m_b2 = replicate_means(b2_vals, b2_W)
    return m_a1 - np.maximum(m_b1, m_b2)


def h3_statistic(a1_res: np.ndarray, b3_res: np.ndarray) -> float:
    return float(np.mean(a1_res) - np.mean(b3_res))


def h3_replicates(
    a1_res: np.ndarray,
    a1_W: np.ndarray,
    b3_res: np.ndarray,
    b3_W: np.ndarray,
) -> np.ndarray:
    return replicate_means(a1_res, a1_W) - replicate_means(b3_res, b3_W)


def h1_decision(
    delay_reduction: float,
    burden_diff_a: float,
    detection_diff_a: float,
    p_a: float,
    burden_cut_b: float,
    detection_diff_b: float,
    p_b: float,
) -> Dict[str, Union[float, bool]]:
    """H1 IUT: max of condition p-values; both margin clauses required (§7)."""
    cond_a = (
        delay_reduction >= H1A_DELAY_MARGIN
        and burden_diff_a <= H1A_BURDEN_NI
        and detection_diff_a >= -H1A_DETECTION_NI
    )
    cond_b = (
        burden_cut_b >= H1B_BURDEN_CUT
        and detection_diff_b >= -H1B_DETECTION_NI
    )
    p_h1 = max(p_a, p_b)
    margins_met = cond_a and cond_b
    return {
        "cond_a": cond_a,
        "cond_b": cond_b,
        "p_h1": p_h1,
        "margins_met": margins_met,
    }


def clause1(point: float, margin: float, p_holm: float) -> bool:
    return point >= margin and p_holm < ALPHA_ONE_SIDED


# Prereg V2.1 §2 (R1/R2): the closed outcome-class vocabulary. ``VOIDED`` is
# always emitted with its invalidator number (``VOIDED:<k>``, V1 §12 / V2 §7 /
# V2.1 §1 items 1–11). ``INSUFFICIENT`` is non-binding: the point estimate met its
# practical margin and every non-inferiority clause held, but the Holm-adjusted
# p-value or the stability clause did not — inconclusive, never NOT_SUPPORTED.
VERDICT_CLASSES: Tuple[str, ...] = (
    "VOIDED",
    "NOT_EXECUTABLE",
    "SOURCE_LIMITED",
    "IMMATURE",
    "UNDERPOWERED",
    "DEVELOPMENT_PASS",
    "DEVELOPMENT_FAIL",
    "NOT_SUPPORTED",
    "INSUFFICIENT",
    "CONSISTENT",
    "SUPPORTED",
)
MAX_INVALIDATOR = 11
PARTITIONS: Tuple[str, ...] = ("P0", "P1", "P2", "P3")


def verdict(
    partition: str,
    *,
    executable: bool,
    source_limited: bool,
    immature: bool,
    honest_n: int,
    margin_met: Optional[bool],
    p_holm: float,
    stable: bool,
    coverage: float,
    ni_ok: bool = True,
    powered_in_principle: Optional[bool] = None,
    voided: Optional[int] = None,
) -> str:
    """Prereg V2.1 §2 clause→outcome table (R2). FIRST MATCH WINS.

    1. ``voided`` set                         → ``VOIDED:<k>``
    2. not executable                         → NOT_EXECUTABLE
    3. source-limited input                   → SOURCE_LIMITED
    4. P2/P3 and not POWERED_IN_PRINCIPLE     → NOT_EXECUTABLE   (V2 §4.3)
    5. immature                               → IMMATURE
    6. honest-N < 20                          → UNDERPOWERED
    7. all-event coverage < 0.80 (or NaN)     → SOURCE_LIMITED   (V1 §7 clause 3)
    8. P0/P1: margin, Holm p < α, stability and non-inferiority all hold
                                              → DEVELOPMENT_PASS, else DEVELOPMENT_FAIL
    9. P2/P3: point estimate undefined        → NOT_EXECUTABLE
              margin missed or an NI/safety clause failed → NOT_SUPPORTED (binding)
              margin met but Holm p ≥ α or unstable       → INSUFFICIENT (non-binding)
              otherwise                       → CONSISTENT (P2) / SUPPORTED (P3)

    No failure reaches NOT_SUPPORTED by exhaustion: only a margin miss or an
    NI/safety failure does. The P0/P1 pass set is exactly V1's (clause 1 ∧ 2 ∧ 3 ∧
    safety), so no size count moves.
    """
    if partition not in PARTITIONS:
        raise ValueError(f"unknown partition: {partition}")
    if voided is not None:
        if isinstance(voided, bool) or not isinstance(voided, int) or not 1 <= voided <= MAX_INVALIDATOR:
            raise ValueError(f"invalidator number must be an int in 1..{MAX_INVALIDATOR}, got {voided!r}")
        return f"VOIDED:{voided}"
    if not executable:
        return "NOT_EXECUTABLE"
    if source_limited:
        return "SOURCE_LIMITED"
    if partition in ("P2", "P3") and powered_in_principle is not True:
        return "NOT_EXECUTABLE"
    if immature:
        return "IMMATURE"
    if honest_n < MIN_HONEST_N:
        return "UNDERPOWERED"
    if not (coverage >= COVERAGE_MIN):
        return "SOURCE_LIMITED"
    p_ok = bool(p_holm < ALPHA_ONE_SIDED)
    stable_ok = stable is True
    ni = ni_ok is True
    if partition in ("P0", "P1"):
        passed = margin_met is True and p_ok and stable_ok and ni
        return "DEVELOPMENT_PASS" if passed else "DEVELOPMENT_FAIL"
    if margin_met is None:
        return "NOT_EXECUTABLE"
    if margin_met is not True or not ni:
        return "NOT_SUPPORTED"
    if not (p_ok and stable_ok):
        return "INSUFFICIENT"
    return "CONSISTENT" if partition == "P2" else "SUPPORTED"
