"""test_sni_s1_stats.py — exact binomial and sign-test p-values against hand
values; tie and direction-0 handling."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

from s1_direction import direction_trailing63, sign_of  # noqa: E402
from s1_stats import (binom_p_one_sided_greater, sign_test_two_sided,  # noqa: E402
                      wilson_ci)
from s1_manifest import last_session_before, session_n_back  # noqa: E402


def test_binomial_hand_values():
    # P(X>=8), n=10, p=0.5: (C(10,8)+C(10,9)+C(10,10))/1024 = (45+10+1)/1024
    assert abs(binom_p_one_sided_greater(8, 10) - 56 / 1024) < 1e-15
    # P(X>=7), n=10: (120+45+10+1)/1024
    assert abs(binom_p_one_sided_greater(7, 10) - 176 / 1024) < 1e-15
    assert binom_p_one_sided_greater(0, 10) == 1.0
    assert binom_p_one_sided_greater(11, 10) == 0.0
    # k at the median: p > alpha
    assert binom_p_one_sided_greater(5, 10) > 0.05
    # all hits: p = 1/1024
    assert abs(binom_p_one_sided_greater(10, 10) - 1 / 1024) < 1e-15


def test_sign_test_hand_values():
    # n=9 all one side: p = 2 * 1/512 = 1/256
    assert abs(sign_test_two_sided(9, 0) - 2 / 512) < 1e-15
    # n=4, 3 vs 1: larger tail P(X>=3) = (4+1)/16 = 5/16, doubled = 10/16
    assert abs(sign_test_two_sided(3, 1) - 10 / 16) < 1e-15
    # n=4, 2 vs 2: larger tail P(X>=2) = 11/16, doubled = 22/16 -> capped at 1
    assert sign_test_two_sided(2, 2) == 1.0
    assert sign_test_two_sided(0, 0) == 1.0


def test_wilson_known_values():
    # hand-computed against the canonical implementation (z = 1.96, 3 dp);
    # the grading_stats docstring examples carry stale numbers (0.336/0.718).
    assert wilson_ci(0, 0) is None
    assert wilson_ci(0, 10) == (0.0, 0.278)
    assert wilson_ci(10, 10) == (0.722, 1.0)
    assert wilson_ci(30, 50) == (0.462, 0.724)


def test_sign_of_ties():
    assert sign_of(0.0) == 0
    assert sign_of(1e-12) == 1
    assert sign_of(-1e-12) == -1


def test_direction_trail63_tie_and_missing_endpoints():
    from lib import nyse_calendar as cal

    # build 80 real NYSE sessions
    from datetime import date, timedelta
    cur, out = date(2024, 1, 2), []
    while len(out) < 80:
        if cal.is_session(cur):
            out.append(cur)
        cur += timedelta(days=1)
    dates = out
    closes = {dt: 100.0 * (1.001 ** i) for i, dt in enumerate(dates)}
    bench = {dt: 50.0 * (1.0002 ** i) for i, dt in enumerate(dates)}
    s = dates[70]
    d_s = last_session_before(cal.is_session, s)
    d63 = session_n_back(cal.is_session, d_s, 63)
    assert d63 in closes
    # faster-drifting subject -> trailing excess positive
    assert direction_trailing63(closes, bench, s, cal.is_session, 63) == 1
    # slower-drifting subject -> trailing excess negative
    assert direction_trailing63(bench, closes, s, cal.is_session, 63) == -1
    # identical series -> excess exactly 0 -> direction 0 (tie abstains)
    assert direction_trailing63(closes, dict(closes), s, cal.is_session, 63) == 0
    # missing endpoint -> direction 0
    broken = dict(closes)
    del broken[d63]
    assert direction_trailing63(broken, bench, s, cal.is_session, 63) == 0
