import sys
from pathlib import Path

RESEARCH = Path(__file__).parents[1] / "scripts" / "research"
sys.path.insert(0, str(RESEARCH))
import spy_0dte_a0_a1_policy as p


def c(family, strike, credit=.10):
    return {"family": family, "short_strike": strike, "entry_credit": credit}


def test_validation_grid_is_exactly_sixty_and_has_no_dual_gamma_or_sensitivity_rows():
    grid = p.validation_grid()
    assert len(grid) == 60 and len(set(grid)) == 60
    text = str(grid).lower()
    assert "dual" not in text and "gamma" not in text and "gex" not in text
    assert sum(row[0] == "A0" for row in grid) == 30
    assert sum(row[0] == "A1" for row in grid) == 30


def test_a0_selects_farthest_otm_inside_requested_family():
    candidates = [c("bull_put", 99, .12), c("bull_put", 98, .09), c("bear_call", 102, .15)]
    chosen = p.select_a0_candidate(candidates, "bull_put", 100)
    assert chosen["short_strike"] == 98


def test_a0_and_a1_cannot_widen_frozen_credit_band():
    a0 = [c("bull_put", 97, .16), c("bull_put", 98, .10)]
    assert p.select_a0_candidate(a0, "bull_put", 100)["short_strike"] == 98
    features = {
        "gap_direction": -1, "event_fomc": 0, "decision_price": 100.0,
        "expected_move_lower": 98.0, "expected_move_upper": 102.0,
        "expected_move_1sigma_abs": 2.0,
    }
    a1 = [c("bull_put", 96, .16), c("bull_put", 97, .10)]
    assert p.select_a1_candidate(a1, features, "contrarian_gap")["short_strike"] == 97


def test_a0_rejects_non_otm_candidates():
    assert p.select_a0_candidate([c("bull_put", 101)], "bull_put", 100) is None


def test_contrarian_gap_maps_down_to_put_and_up_to_call():
    assert p.permitted_a1_family({"gap_direction": -1, "event_fomc": 0}, "contrarian_gap") == "bull_put"
    assert p.permitted_a1_family({"gap_direction": 1, "event_fomc": 0}, "contrarian_gap") == "bear_call"


def test_price_confirmed_requires_reversal_and_fomc_always_abstains():
    assert p.permitted_a1_family({"gap_direction": -1, "reversal_from_gap_extreme_flag": 0, "event_fomc": 0}, "price_confirmed") is None
    assert p.permitted_a1_family({"gap_direction": -1, "reversal_from_gap_extreme_flag": 1, "event_fomc": 0}, "price_confirmed") == "bull_put"
    assert p.permitted_a1_family({"gap_direction": -1, "reversal_from_gap_extreme_flag": 1, "event_fomc": 1}, "price_confirmed") is None


def test_missing_or_malformed_event_and_gap_state_fail_closed_to_abstain():
    assert p.permitted_a1_family({"gap_direction": -1}, "contrarian_gap") is None
    assert p.permitted_a1_family({"gap_direction": -1, "event_fomc": "0"}, "contrarian_gap") is None
    assert p.permitted_a1_family({"gap_direction": "-1", "event_fomc": 0}, "contrarian_gap") is None


def test_dual_mode_is_held_not_silently_executable():
    try:
        p.permitted_a1_family({"gap_direction": -1}, "dual_candidate")
    except p.PolicyError as exc:
        assert "not executable" in str(exc)
    else:
        raise AssertionError("held dual mode gained trade authority")


def test_a1_requires_short_beyond_expected_move_envelope_and_ranks_margin():
    features = {
        "gap_direction": -1,
        "event_fomc": 0,
        "decision_price": 100.0,
        "expected_move_lower": 98.0,
        "expected_move_upper": 102.0,
        "expected_move_1sigma_abs": 2.0,
    }
    candidates = [c("bull_put", 98.5, .15), c("bull_put", 98.0, .10), c("bull_put", 97.5, .08)]
    chosen = p.select_a1_candidate(candidates, features, "contrarian_gap")
    assert chosen["short_strike"] == 97.5


def test_structural_breach_is_strict_completed_close_beyond_short():
    assert p.structural_breach("bull_put", 100, 99.99) is True
    assert p.structural_breach("bull_put", 100, 100) is False
    assert p.structural_breach("bear_call", 100, 100.01) is True
    assert p.structural_breach("bear_call", 100, 100) is False


def test_circular_bootstrap_is_reproducible_and_empirical_bound_has_no_interpolation():
    values = [1.0, -1.0, 0.5, 0.0, 2.0, -0.5]
    a = p.circular_block_bootstrap_means(values, block_sessions=2, replicates=20, seed=7)
    b = p.circular_block_bootstrap_means(values, block_sessions=2, replicates=20, seed=7)
    assert a == b and len(a) == 20
    assert p.empirical_lower_bound([5, 1, 4, 2, 3], .2) == 1.0
    assert p.empirical_lower_bound([5, 1, 4, 2, 3], .4) == 2.0


def test_expected_shortfall_95_is_worst_ceil_five_percent_calendar_sessions():
    values = list(range(-10, 90))
    assert len(values) == 100
    assert p.expected_shortfall_95(values) == (-10 - 9 - 8 - 7 - 6) / 5


def test_validation_ties_use_lexicographic_configuration_id():
    grid = p.validation_grid()
    a, b = grid[0], grid[1]
    chosen = p.select_highest_lower_bound({b: .01, a: .01})
    assert chosen == min((a, b), key=p.configuration_id)


def test_holm_step_down_stops_after_first_failure():
    out = p.holm_bonferroni_rejections({"a": .001, "b": .02, "c": .06}, alpha=.05)
    assert out == {"a": True, "b": True, "c": False}
    out2 = p.holm_bonferroni_rejections({"a": .02, "b": .021, "c": .022}, alpha=.05)
    assert out2 == {"a": False, "b": False, "c": False}
