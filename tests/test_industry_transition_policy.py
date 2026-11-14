import numpy as np
import pandas as pd
import pytest
from engine.industry_transition_policy import (
    POLICIES, calendar_paired_interval, combine_predictions, momentum_protected, reversal_half,
)


def candidates():
    rows = []
    for date in pd.date_range("2000-01-31", periods=24, freq="ME"):
        for i in range(10):
            rows.append({"decision_date": date, "industry": f"I{i}", "relative126": i / 10,
                         "vol63": (10 - i) / 100, "p_bad_loss": i / 15,
                         "p_bad_loss_price": (9 - i) / 15, "expected_excess_net": (i % 3) / 100,
                         "state": "reversal_attempt" if i < 7 else "continuation",
                         "fold": 2000, "terminal_net": .01 * i, "bad_loss": i % 2})
    return pd.DataFrame(rows)


def test_all_policies_same_coverage_and_momentum_pool():
    frame = candidates()
    for policy in POLICIES:
        take = momentum_protected(frame, policy)
        assert len(take) == 48
        assert set(take.industry).issubset({"I6", "I7", "I8", "I9"})
    assert set(momentum_protected(frame, "momentum").industry) == {"I8", "I9"}
    assert set(momentum_protected(frame, "context_risk").industry) == {"I6", "I7"}


def test_future_outcomes_cannot_change_selection():
    a = candidates(); b = a.copy()
    b["terminal_net"] = np.arange(len(b)) * 999; b["bad_loss"] = -100
    for policy in POLICIES:
        aa, bb = momentum_protected(a, policy), momentum_protected(b, policy)
        pd.testing.assert_frame_equal(aa[["decision_date", "industry"]], bb[["decision_date", "industry"]])


def test_same_population_join_and_mismatch():
    frame = candidates()
    c = frame.copy(); c["model"] = "context"
    p = frame.copy(); p["model"] = "price"; p["p_bad_loss"] = .2
    both = pd.concat([c, p], ignore_index=True)
    result = combine_predictions(both)
    assert (result.p_bad_loss_price == .2).all()
    with pytest.raises(ValueError, match="populations"): combine_predictions(both.iloc[:-1])
    with pytest.raises(ValueError, match="duplicate"): combine_predictions(pd.concat([both, c.head(1)]))


def test_nonfinite_feature_does_not_become_a_safe_vote():
    f = candidates(); f.iloc[0, f.columns.get_loc("p_bad_loss")] = np.nan
    with pytest.raises(ValueError, match="nonfinite"): momentum_protected(f, "context_risk")
    with pytest.raises(ValueError): momentum_protected(candidates(), "unknown")
    with pytest.raises(ValueError): momentum_protected(candidates(), "momentum", fraction=.6, pool_fraction=.4)


def test_reversal_policies_identical_half_coverage():
    frame = candidates()
    for policy in ("momentum_half", "context_risk_half", "price_risk_half", "expected_excess_half"):
        take = reversal_half(frame, policy)
        assert set(take.state) == {"reversal_attempt"}
        assert set(take.groupby("decision_date").size()) == {4}
    assert reversal_half(frame, "momentum_half", minimum_candidates=8).empty


def test_calendar_blocks_retain_missing_month_positions():
    frame = candidates()
    a = frame[frame.decision_date.dt.month != 6].copy()
    b = a.copy(); b["terminal_net"] -= .01
    result = calendar_paired_interval(a, b, "terminal_net", replicates=100)
    assert result["months"] == 22 and result["calendar_month_span"] == 24
    assert result["difference"] == pytest.approx(.01)
    assert result["ci95"] == pytest.approx([.01, .01])
