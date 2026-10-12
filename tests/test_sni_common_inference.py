"""test_sni_common_inference.py — audited SNI inference contract."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/common"),
)

from sni_inference import (  # noqa: E402
    ABSTAIN_INSUFFICIENT_CLUSTERS,
    ABSTAIN_NO_EPISODES,
    AUTHORITY_FLAGS,
    DESCRIPTIVE_ONLY,
    MIN_CLUSTERS,
    TESTED,
    binom_p_one_sided_greater,
    binom_p_two_sided,
    cluster_mean_ci,
    label_for,
    plain_word_null,
    sign_test_two_sided,
    wilson_ci,
)


def test_wilson_known_values():
    r0 = wilson_ci(0, 10)
    assert r0.estimate == 0.0
    assert r0.ci_lo == 0.0
    assert r0.ci_hi is not None
    assert abs(r0.ci_hi - 0.278) < 1e-3
    assert r0.abstained is False
    assert r0.method == "wilson"

    r1 = wilson_ci(10, 10)
    assert r1.estimate == 1.0
    assert r1.ci_hi == 1.0
    assert r1.ci_lo is not None
    assert abs(r1.ci_lo - 0.722) < 1e-3

    r5 = wilson_ci(5, 10)
    assert r5.ci_lo is not None and r5.ci_hi is not None
    assert abs(r5.ci_lo - 0.237) < 1e-3
    assert abs(r5.ci_hi - 0.763) < 1e-3


def test_wilson_cross_check_engine():
    pytest.importorskip("engine.grading_stats")
    try:
        from engine.grading_stats import wilson_ci as engine_wilson_ci
    except Exception:
        pytest.skip("engine.grading_stats import raised")

    for k, n in ((3, 17), (50, 120)):
        ours = wilson_ci(k, n, alpha=0.05)
        try:
            eng = engine_wilson_ci(k, n, z=1.959964)
        except Exception:
            pytest.skip("engine.grading_stats.wilson_ci raised")
        assert ours.ci_lo is not None and ours.ci_hi is not None
        assert eng is not None
        elo, ehi = float(eng[0]), float(eng[1])
        # Full-precision agreement when the engine returns unrounded bounds;
        # the canonical engine copy rounds to 3 decimal places.
        if abs(ours.ci_lo - elo) < 1e-9 and abs(ours.ci_hi - ehi) < 1e-9:
            continue
        assert abs(round(ours.ci_lo, 3) - elo) < 1e-9
        assert abs(round(ours.ci_hi, 3) - ehi) < 1e-9


def test_binomial_exactness():
    expected = sum(math.comb(10, i) for i in range(7, 11)) / float(2 ** 10)
    assert binom_p_one_sided_greater(7, 10) == expected
    assert binom_p_one_sided_greater(0, 10) == 1.0
    assert binom_p_one_sided_greater(0, 3) == 1.0
    assert binom_p_two_sided(7, 10) <= 1.0
    assert binom_p_two_sided(5, 10) <= 1.0
    assert binom_p_two_sided(0, 10) <= 1.0
    assert binom_p_two_sided(10, 10) <= 1.0


def test_sign_test_symmetry():
    pairs = ((9, 0), (0, 9), (7, 3), (3, 7), (5, 5), (1, 8), (0, 0), (12, 4))
    for a, b in pairs:
        assert sign_test_two_sided(a, b) == sign_test_two_sided(b, a)


def test_abstain_empty_and_one_cluster():
    empty = cluster_mean_ci([], [])
    assert empty.abstained is True
    assert empty.reason == ABSTAIN_NO_EPISODES
    assert empty.estimate is None
    assert empty.ci_lo is None and empty.ci_hi is None
    assert empty.n_obs == 0
    assert empty.n_clusters == 0
    assert label_for(empty, min_episodes=1) == ABSTAIN_NO_EPISODES

    values = [float(i) for i in range(50)]
    keys = ["only"] * 50
    one = cluster_mean_ci(values, keys)
    assert one.abstained is True
    assert one.reason == ABSTAIN_INSUFFICIENT_CLUSTERS
    assert one.n_obs == 50
    assert one.n_clusters == 1
    assert one.n_clusters < MIN_CLUSTERS
    assert one.ci_lo is None and one.ci_hi is None
    mean = sum(values) / 50.0
    assert one.estimate == mean
    assert label_for(one, min_episodes=1) == ABSTAIN_INSUFFICIENT_CLUSTERS

    w0 = wilson_ci(0, 0)
    assert w0.abstained is True
    assert w0.reason == ABSTAIN_NO_EPISODES


def test_determinism():
    values = [0.1, 0.2, 0.3, 1.5, 1.6, 1.4, -0.2, 0.0, 0.1]
    keys = ["a", "a", "a", "b", "b", "b", "c", "c", "c"]
    r1 = cluster_mean_ci(values, keys, draws=500, seed=7)
    r2 = cluster_mean_ci(values, keys, draws=500, seed=7)
    r3 = cluster_mean_ci(values, keys, draws=500, seed=99)
    assert (r1.estimate, r1.ci_lo, r1.ci_hi) == (r2.estimate, r2.ci_lo, r2.ci_hi)
    assert r1.estimate == r3.estimate
    assert r1.abstained is False


def test_permutation_invariance():
    values = [0.4, -0.1, 0.8, 1.2, 0.0, -0.5, 0.3, 0.9, 1.1, 0.2]
    keys = ["z", "z", "m", "m", "m", "a", "a", "a", "a", "z"]
    base = cluster_mean_ci(values, keys, draws=800, seed=11)
    pairs = list(zip(values, keys))
    rng = random.Random(12345)
    rng.shuffle(pairs)
    shuffled_v = [p[0] for p in pairs]
    shuffled_k = [p[1] for p in pairs]
    perm = cluster_mean_ci(shuffled_v, shuffled_k, draws=800, seed=11)
    assert perm.estimate == base.estimate
    assert perm.ci_lo == base.ci_lo
    assert perm.ci_hi == base.ci_hi
    assert perm.n_clusters == base.n_clusters


def test_coverage_sanity():
    rng = random.Random(20261012)
    values: list[float] = []
    keys: list[str] = []
    for cluster in ("c0", "c1", "c2"):
        for _ in range(40):
            values.append(rng.gauss(1.0, 0.1))
            keys.append(cluster)
    result = cluster_mean_ci(values, keys, draws=2000, seed=0, alpha=0.05)
    assert result.abstained is False
    assert result.n_clusters == 3
    assert result.n_obs == 120
    assert result.ci_lo is not None and result.ci_hi is not None
    assert result.ci_lo < 1.0 < result.ci_hi


def test_label_for_descriptive_vs_tested():
    values: list[float] = []
    keys: list[str] = []
    for i in range(5):
        for _ in range(12):
            values.append(0.01 * i)
            keys.append(f"k{i}")
    result = cluster_mean_ci(values, keys, draws=400, seed=1)
    assert result.abstained is False
    assert result.n_obs == 60
    assert result.n_clusters == 5
    assert label_for(result, min_episodes=153) == DESCRIPTIVE_ONLY
    assert label_for(result, min_episodes=50) == TESTED
    assert result.reason is None


def test_plain_word_null_forbidden_phrases_and_unknown():
    values = [1.0, 2.0, 3.0, 4.0]
    keys = ["a", "a", "b", "b"]
    tested = cluster_mean_ci(values, keys, draws=200, seed=0)
    descriptive = tested
    empty = cluster_mean_ci([], [])
    one_cluster = cluster_mean_ci([1.0, 2.0, 3.0], ["x", "x", "x"])

    cases = (
        (TESTED, tested, 1),
        (DESCRIPTIVE_ONLY, descriptive, 153),
        (ABSTAIN_INSUFFICIENT_CLUSTERS, one_cluster, 10),
        (ABSTAIN_NO_EPISODES, empty, 10),
    )
    forbidden = ("coin flip", "50/50", "forecast")
    for label, result, min_ep in cases:
        text = plain_word_null(label, result, min_episodes=min_ep)
        lowered = text.lower()
        for phrase in forbidden:
            assert phrase not in text
            assert phrase not in lowered
        assert text  # non-empty contract string

    assert plain_word_null(TESTED, tested, min_episodes=1) == (
        f"Tested: {tested.n_obs} episodes across {tested.n_clusters} date clusters."
    )
    assert plain_word_null(DESCRIPTIVE_ONLY, descriptive, min_episodes=153) == (
        f"Descriptive only: {descriptive.n_obs} episodes across "
        f"{descriptive.n_clusters} date clusters, below the registered "
        "minimum of 153 episodes; no test is claimed."
    )
    assert plain_word_null(
        ABSTAIN_INSUFFICIENT_CLUSTERS, one_cluster, min_episodes=10
    ) == (
        "This family abstains: fewer than 2 independent date clusters, "
        "so no interval is estimable."
    )
    assert (
        plain_word_null(ABSTAIN_NO_EPISODES, empty, min_episodes=10)
        == "This family abstains: no episodes."
    )

    with pytest.raises(KeyError):
        plain_word_null("NOT_A_LABEL", tested, min_episodes=10)


def test_authority_flags_frozen_all_false():
    expected = {
        "rank_authority",
        "gate_authority",
        "size_authority",
        "signal_authority",
        "escalation_authority",
        "trade_authority",
    }
    assert set(AUTHORITY_FLAGS.keys()) == expected
    assert len(AUTHORITY_FLAGS) == 6
    assert all(v is False for v in AUTHORITY_FLAGS.values())
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True  # type: ignore[index]
    with pytest.raises(ValueError):
        wilson_ci(1, 2, rank_authority=True)
    with pytest.raises(ValueError):
        cluster_mean_ci([1.0, 2.0], ["a", "b"], trade_authority=True)


def test_input_validation_raises():
    with pytest.raises(ValueError):
        wilson_ci(2, 1)
    with pytest.raises(ValueError):
        binom_p_one_sided_greater(5, 3)
    with pytest.raises(ValueError):
        cluster_mean_ci([1.0], ["a"], alpha=0)
    with pytest.raises(ValueError):
        wilson_ci(0, 10, alpha=0)
    with pytest.raises(ValueError):
        cluster_mean_ci([1.0, 2.0], ["a"])
    with pytest.raises(ValueError):
        cluster_mean_ci([1.0], ["a", "b"])
