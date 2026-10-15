"""Discriminating tests for leadership_rotation_inference (T11 §8 harness)."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.leadership_rotation_inference import (
    VERDICT_CLASSES,
    ALPHA_ONE_SIDED,
    CLUSTER_RADIUS,
    COVERAGE_MIN,
    MIN_HONEST_N,
    REPS,
    clause1,
    h1_decision,
    h2_replicates,
    h2_statistic,
    holm,
    interval_90,
    item_weights,
    lower_bound,
    one_sided_p,
    replicate_lower_median,
    paired_replicate_contrast,
    replicate_means,
    shared_leg_components,
    single_linkage_clusters,
    stability_thirds,
    stationary_bootstrap_weights,
    verdict,
)


# MUTATION: scripts/leadership_rotation_inference.py:45 change `<= radius` to `< radius`
def test_single_linkage_clusters_within_group_and_coords():
    items = [("g", "p", i) for i in (0, 10, 20, 31)]
    labels, coords = single_linkage_clusters(items, radius=CLUSTER_RADIUS)
    assert len(set(labels)) == 2
    clusters = [set(), set()]
    for lab, idx in zip(labels, (0, 10, 20, 31)):
        clusters[lab].add(idx)
    assert clusters[0] == {0, 10, 20}
    assert clusters[1] == {31}
    assert coords[0] == 0
    assert coords[1] == 31

    split = [("g1", "a", 0), ("g1", "b", 10), ("g2", "c", 5), ("g2", "d", 6)]
    labels2, _ = single_linkage_clusters(split, radius=CLUSTER_RADIUS)
    assert labels2[0] != labels2[2]
    assert labels2[2] == labels2[3]


# MUTATION: scripts/leadership_rotation_inference.py:88 skip union on shared leg
def test_shared_leg_components_sensitivity():
    defensive = {
        "XLP/XLK": ("XLP", "XLK"),
        "XLU/XLK": ("XLU", "XLK"),
        "XLV/XLK": ("XLV", "XLK"),
        "XLP/SMH": ("XLP", "SMH"),
    }
    assert shared_leg_components(defensive) == 1
    broadening = {
        "DIA/QQQ": ("DIA", "QQQ"),
        "IWM/QQQ": ("IWM", "QQQ"),
        "RSP/QQQ": ("RSP", "QQQ"),
    }
    assert shared_leg_components(broadening) == 1
    disjoint = {"AAA/BBB": ("AAA", "BBB"), "CCC/DDD": ("CCC", "DDD")}
    assert shared_leg_components(disjoint) == 2


def _sequential_bootstrap_weights(n, mean_block, reps, seed):
    rng = np.random.default_rng(seed)
    W = np.zeros((reps, n), dtype=np.int32)
    for r in range(reps):
        u = rng.random(n)
        s = rng.integers(0, n, size=n)
        idx = np.empty(n, dtype=np.intp)
        idx[0] = s[0]
        for k in range(1, n):
            if u[k] < 1.0 / mean_block:
                idx[k] = s[k]
            else:
                idx[k] = (idx[k - 1] + 1) % n
        W[r] = np.bincount(idx, minlength=n)
    return W


# MUTATION: scripts/leadership_rotation_inference.py:121 swap `u` and `s` draw order
def test_stationary_bootstrap_frozen_order_and_shape():
    n, reps, seed, mb = 5, 3, 1, 21
    got = stationary_bootstrap_weights(n, mean_block=mb, reps=reps, seed=seed)
    want = _sequential_bootstrap_weights(n, mb, reps, seed)
    np.testing.assert_array_equal(got, want)
    assert got.dtype == np.int32
    assert np.all(got.sum(axis=1) == n)
    again = stationary_bootstrap_weights(n, mean_block=mb, reps=reps, seed=seed)
    np.testing.assert_array_equal(got, again)

    def restart_count(n, mean_block, seed):
        rng = np.random.default_rng(seed)
        u = rng.random(n)
        return int(np.sum(u < 1.0 / mean_block) + 1)

    assert restart_count(200, 1, 11) > restart_count(200, 500, 11) * 5


def _lower_median_scalar(values, weights):
    order = np.argsort(values)
    sv = values[order]
    sw = weights[order]
    total = sw.sum()
    if total == 0:
        return float("nan")
    cum = np.cumsum(sw)
    idx = int(np.argmax(cum >= total / 2.0))
    return float(sv[idx])


# MUTATION: scripts/leadership_rotation_inference.py:175 use upper median (last crossing)
def test_replicate_lower_median_matches_scalar_reference():
    rng = np.random.default_rng(42)
    values = rng.normal(size=7)
    Wm = rng.integers(0, 4, size=(5, 7))
    got = replicate_lower_median(values, Wm)
    for r in range(5):
        np.testing.assert_allclose(got[r], _lower_median_scalar(values, Wm[r]))
    Wm_zero = np.zeros((1, 7), dtype=np.int64)
    assert np.isnan(replicate_lower_median(values, Wm_zero)[0])


# MUTATION: scripts/leadership_rotation_inference.py:152 re-draw W for contrast_reps
def test_paired_bootstrap_shared_replicates():
    n = 12
    W = stationary_bootstrap_weights(n, reps=20, seed=7)
    coords = [0, 0, 5, 9]
    x = np.array([1.0, 3.0, 5.0, 7.0])
    y = np.array([2.0, 0.0, 4.0, 8.0])
    diff_reps, contrast_reps = paired_replicate_contrast(x, y, W, coords)
    np.testing.assert_allclose(diff_reps, contrast_reps, rtol=0, atol=1e-12)


# MUTATION: scripts/leadership_rotation_inference.py:186 exclude NaN from le_zero count
def test_one_sided_p_all_positive_and_nan():
    reps = np.ones(REPS)
    p, n_nan = one_sided_p(reps)
    assert p == 1.0 / (1 + REPS)
    assert n_nan == 0
    mixed = np.array([1.0, np.nan, -0.1, 0.0])
    p2, n_nan2 = one_sided_p(mixed)
    assert n_nan2 == 1
    assert p2 == (1 + 3) / (1 + 4)


# MUTATION: scripts/leadership_rotation_inference.py:199 use 10th/90th percentiles
def test_interval_90_and_lower_bound():
    arr = np.arange(1.0, 101.0)
    lo, hi = interval_90(arr)
    assert lo == np.percentile(arr, 5)
    assert hi == np.percentile(arr, 95)
    assert lower_bound(arr) == np.percentile(arr, 2.5)


# MUTATION: scripts/leadership_rotation_inference.py:214 use Bonferroni only (no max step)
def test_holm_textbook_and_six_family():
    raw = [0.01, 0.04, 0.03, 0.005]
    adj = holm(raw)
    assert adj == [0.03, 0.06, 0.06, 0.02]
    for m in (4, 6):
        p = np.linspace(0.001, 0.05, m)
        h = holm(p.tolist())
        assert h == sorted(h)
    assert len(holm([0.1] * 6)) == 6


# MUTATION: scripts/leadership_rotation_inference.py:248 use cluster-count thirds not session boundaries
def test_stability_thirds_by_session_count():
    session_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    cluster_coords = np.array([0, 1, 2, 6, 7, 8])
    values = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])

    def cluster_values_fn(mask):
        if not mask.any():
            return float("nan")
        return float(values[mask].mean())

    full = cluster_values_fn(np.ones(len(cluster_coords), dtype=bool))
    res = stability_thirds(session_indices, cluster_coords, cluster_values_fn, full)
    assert res["holds"] is True

    nan_res = stability_thirds(session_indices, cluster_coords, cluster_values_fn, float("nan"))
    assert nan_res["holds"] is False


# MUTATION: scripts/leadership_rotation_inference.py:279 use point-estimate max for all replicates
def test_h2_replicates_per_replicate_max():
    a1 = np.array([0.10, 0.10])
    b1 = np.array([0.05, 0.05])
    b2 = np.array([0.02, 0.08])
    W = np.array([[1, 1], [1, 1], [1, 0], [0, 1]], dtype=np.int64)
    point = h2_statistic(a1, b1, b2)
    assert point == 0.10 - 0.05
    reps = h2_replicates(a1, W, b1, W, b2, W)
    wrong = replicate_means(a1, W) - max(replicate_means(b1, W)[0], replicate_means(b2, W)[0])
    assert not np.allclose(reps, np.full_like(reps, wrong))
    assert reps[2] == 0.10 - 0.05
    assert reps[3] == 0.10 - 0.08


# MUTATION: scripts/leadership_rotation_inference.py:305 use min(p_a, p_b) for IUT
def test_h1_iut_max_p_and_margin_clauses():
    ok = h1_decision(5.0, 0.5, -0.05, 0.01, 0.25, -0.10, 0.02)
    assert ok["p_h1"] == 0.02
    assert ok["margins_met"] is True
    miss_a = h1_decision(4.9, 0.5, -0.05, 0.01, 0.25, -0.10, 0.001)
    assert miss_a["margins_met"] is False
    miss_b = h1_decision(5.0, 0.5, -0.05, 0.001, 0.24, -0.10, 0.02)
    assert miss_b["margins_met"] is False
    ni_burden = h1_decision(5.0, 0.51, -0.05, 0.01, 0.25, -0.10, 0.02)
    assert ni_burden["cond_a"] is False
    ni_det = h1_decision(5.0, 0.5, -0.06, 0.01, 0.25, -0.10, 0.02)
    assert ni_det["cond_a"] is False


def _v1_verdict(partition, *, executable, source_limited, immature, honest_n, clause1_ok, stable, coverage, h2_safety_ok=True):
    """The pre-V2.1 verdict at head 1b17e8045cd8, kept verbatim as an oracle."""
    if not executable:
        return "NOT_EXECUTABLE"
    if source_limited:
        return "SOURCE_LIMITED"
    if immature:
        return "IMMATURE"
    if honest_n < MIN_HONEST_N:
        return "UNDERPOWERED"
    passed = clause1_ok and stable and coverage >= COVERAGE_MIN and h2_safety_ok
    if partition in ("P0", "P1"):
        return "DEVELOPMENT_PASS" if passed else "DEVELOPMENT_FAIL"
    if partition == "P2":
        return "CONSISTENT" if passed else "NOT_SUPPORTED"
    return "SUPPORTED" if passed else "NOT_SUPPORTED"


_BASE = dict(
    executable=True,
    source_limited=False,
    immature=False,
    honest_n=MIN_HONEST_N,
    margin_met=True,
    p_holm=0.001,
    stable=True,
    coverage=COVERAGE_MIN,
    ni_ok=True,
    powered_in_principle=True,
)


# MUTATION: scripts/leadership_rotation_inference.py:verdict map P1 to SUPPORTED on pass
def test_verdict_labels_per_partition():
    assert verdict("P1", **_BASE) == "DEVELOPMENT_PASS"
    assert verdict("P0", **_BASE) == "DEVELOPMENT_PASS"
    assert verdict("P2", **_BASE) == "CONSISTENT"
    assert verdict("P3", **_BASE) == "SUPPORTED"
    assert verdict("P0", **{**_BASE, "margin_met": False}) == "DEVELOPMENT_FAIL"
    assert verdict("P1", **{**_BASE, "honest_n": MIN_HONEST_N - 1}) == "UNDERPOWERED"
    with pytest.raises(ValueError):
        verdict("P4", **_BASE)


# MUTATION: scripts/leadership_rotation_inference.py:verdict let a coverage shortfall fall through to NOT_SUPPORTED
def test_no_failure_reaches_not_supported_by_exhaustion():
    """V2.1 §2 (R2): coverage, power and maturity are source/design states,
    never evidence against the hypothesis."""
    assert verdict("P3", **{**_BASE, "coverage": 0.79}) == "SOURCE_LIMITED"
    assert verdict("P2", **{**_BASE, "coverage": float("nan")}) == "SOURCE_LIMITED"
    assert verdict("P3", **{**_BASE, "powered_in_principle": None}) == "NOT_EXECUTABLE"
    assert verdict("P2", **{**_BASE, "powered_in_principle": False}) == "NOT_EXECUTABLE"
    assert verdict("P1", **{**_BASE, "powered_in_principle": None}) == "DEVELOPMENT_PASS"
    assert verdict("P3", **{**_BASE, "margin_met": None}) == "NOT_EXECUTABLE"
    # inconclusive, not contrary: margin met, p or stability short
    assert verdict("P3", **{**_BASE, "p_holm": 0.025}) == "INSUFFICIENT"
    assert verdict("P2", **{**_BASE, "p_holm": float("nan")}) == "INSUFFICIENT"
    assert verdict("P3", **{**_BASE, "stable": False}) == "INSUFFICIENT"
    # the only routes to the binding negative
    assert verdict("P3", **{**_BASE, "margin_met": False}) == "NOT_SUPPORTED"
    assert verdict("P2", **{**_BASE, "ni_ok": False}) == "NOT_SUPPORTED"
    assert verdict("P3", **{**_BASE, "margin_met": False, "p_holm": 0.9, "stable": False}) == "NOT_SUPPORTED"


# MUTATION: scripts/leadership_rotation_inference.py:verdict test immaturity before source limitation
def test_first_match_precedence_order():
    everything = {
        **_BASE,
        "executable": False,
        "source_limited": True,
        "immature": True,
        "honest_n": 0,
        "coverage": 0.0,
        "margin_met": None,
        "powered_in_principle": None,
    }
    assert verdict("P3", **{**everything, "voided": 10}) == "VOIDED:10"
    assert verdict("P3", **everything) == "NOT_EXECUTABLE"
    assert verdict("P3", **{**everything, "executable": True}) == "SOURCE_LIMITED"
    step = {**everything, "executable": True, "source_limited": False}
    assert verdict("P3", **step) == "NOT_EXECUTABLE"  # row 4: unpowered
    step["powered_in_principle"] = True
    assert verdict("P3", **step) == "IMMATURE"
    step["immature"] = False
    assert verdict("P3", **step) == "UNDERPOWERED"
    step["honest_n"] = MIN_HONEST_N
    assert verdict("P3", **step) == "SOURCE_LIMITED"  # row 7: coverage
    step["coverage"] = COVERAGE_MIN
    assert verdict("P3", **step) == "NOT_EXECUTABLE"  # row 9a: undefined point
    for bad in (0, 12, True, 1.0, "3"):
        with pytest.raises(ValueError):
            verdict("P1", **{**_BASE, "voided": bad})
    for k in range(1, 12):
        assert verdict("P0", **{**_BASE, "voided": k}) == f"VOIDED:{k}"
    assert set(VERDICT_CLASSES) >= {"VOIDED", "INSUFFICIENT", "NOT_SUPPORTED", "SUPPORTED"}


# MUTATION: scripts/leadership_rotation_inference.py:verdict drop the stability clause from the P0/P1 pass
def test_development_pass_set_is_unchanged_from_v1():
    """Exhaustive: R2 moves no P0/P1 pass, so no size count moves."""
    import itertools

    n = 0
    for part, ex, sl, im, hn, mm, p, stb, cov, ni in itertools.product(
        ("P0", "P1"), (True, False), (True, False), (True, False), (19, 20),
        (True, False, None), (0.001, 0.025, float("nan")), (True, False),
        (0.79, 0.80, float("nan")), (True, False),
    ):
        new = verdict(part, executable=ex, source_limited=sl, immature=im, honest_n=hn,
                      margin_met=mm, p_holm=p, stable=stb, coverage=cov, ni_ok=ni)
        clause = mm is True and p < ALPHA_ONE_SIDED
        old = _v1_verdict(part, executable=ex, source_limited=sl, immature=im, honest_n=hn,
                          clause1_ok=clause, stable=stb, coverage=cov, h2_safety_ok=ni)
        assert (new == "DEVELOPMENT_PASS") == (old == "DEVELOPMENT_PASS")
        if old != new:
            # the only relabel is a coverage shortfall: FAIL → SOURCE_LIMITED
            assert old == "DEVELOPMENT_FAIL" and new == "SOURCE_LIMITED" and not (cov >= COVERAGE_MIN)
        n += 1
    assert n == 2 * 2 * 2 * 2 * 2 * 3 * 3 * 2 * 3 * 2


def test_clause1_uses_holm_alpha():
    assert clause1(0.01, 0.005, 0.024) is True
    assert clause1(0.01, 0.005, ALPHA_ONE_SIDED) is False
