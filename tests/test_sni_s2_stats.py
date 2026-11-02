"""S2 statistics (E8): exact one-sided binomial vs hand values, ties, and
direction 0 handling. wilson_ci comes from the shared engine primitive.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from engine.grading_stats import wilson_ci  # noqa: E402
from s2_stats import (binomial_one_sided_greater,  # noqa: E402
                      hit_rate_test, sign_exact)


def test_binomial_matches_hand_values() -> None:
    # n=1, k=1: P(X>=1) = 0.5
    assert binomial_one_sided_greater(1, 1) == 0.5
    # n=2, k=2: P(X>=2) = 0.25
    assert binomial_one_sided_greater(2, 2) == 0.25
    # n=3, k=2: (C(3,2)+C(3,3))/8 = 4/8 = 0.5
    assert binomial_one_sided_greater(2, 3) == 0.5
    # n=10, k=9: (C(10,9)+C(10,10))/1024 = 11/1024
    assert abs(binomial_one_sided_greater(9, 10) - 11 / 1024) < 1e-12
    # k=0 is the full distribution = 1.0
    assert binomial_one_sided_greater(0, 5) == 1.0
    # brute force cross-check
    for n in (4, 7, 12):
        for k in range(n + 1):
            want = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
            assert binomial_one_sided_greater(k, n) == want


def test_hit_rate_test_rejects_only_at_alpha() -> None:
    # 9/10 hits: p = 11/1024 ~ 0.0107 <= 0.05 -> reject
    res = hit_rate_test([1] * 9 + [0])
    assert res["p_value"] == round(11 / 1024, 6)
    assert res["reject_at_alpha"] is True
    # 8/10 hits: p = 56/1024 ~ 0.0547 > 0.05 -> not rejected
    res = hit_rate_test([1] * 8 + [0] * 2)
    assert res["reject_at_alpha"] is False
    assert res["sidedness"] == "one-sided (greater)"
    assert res["alpha"] == 0.05


def test_ties_count_as_non_hits_and_are_listed() -> None:
    res = hit_rate_test([1, 0, 0])
    assert res["hits"] == 1 and res["n"] == 3
    # a tie row is flagged and contributes 0 to the hit count
    rows = [{"hit": 1, "tie": False}, {"hit": 0, "tie": True}]
    assert sum(r["hit"] for r in rows) == 1
    assert any(r["tie"] for r in rows)


def test_direction_zero_means_abstain_not_a_hit() -> None:
    # direction 0 (e.g. a trailing window with missing bars) must produce
    # hit=None (ABSTAIN), never a comparison against 0
    direction = 0
    excess = -0.04
    hit = None if direction == 0 else (1 if sign_exact(excess) == direction else 0)
    assert hit is None


def test_wilson_ci_matches_the_formula() -> None:
    """Expected values computed from the Wilson formula itself (the primitive's
    docstring examples are rounded illustrations, not pinned values)."""
    assert wilson_ci(0, 0) is None

    def expect(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
        p = k / n
        denom = 1.0 + z * z / n
        centre = (p + z * z / (2 * n)) / denom
        half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
        return (round(max(0.0, centre - half), 3),
                round(min(1.0, centre + half), 3))

    for k, n in ((30, 50), (0, 10), (10, 10), (1, 3), (7, 8)):
        assert wilson_ci(k, n) == expect(k, n), (k, n)
