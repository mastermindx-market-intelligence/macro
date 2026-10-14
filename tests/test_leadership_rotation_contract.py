"""Contract tests for engine.leadership_rotation_context (LR-MEAS-SPEC-1, lane B1).

Pure-Python fixtures only: no network, no ``data/`` reads, no clock reads.
Case ids follow the programme acceptance matrix (cf/a cases); lane LR-MEAS-B1
covers the pure measurement core (spec sections 1, 2, 3, 4, 5-partial, 8).
"""

import math

import pytest

from engine.leadership_rotation_context import (
    EPS,
    US_SECTOR_COHORT_ID,
    Breadth,
    CohortMismatch,
    Unmeasured,
    beta_only_residual,
    breadth,
    breadth_change,
    classify_coordinate,
    cohort_zscores,
    concentration,
    decompose_trailing_change,
    decompose_z_change,
    dedupe_source_roots,
    is_measured,
    normalize_weights,
    overlap,
    pair_interpretation,
    rank_measured,
    relative_wealth,
    return_difference,
    rolling_carry,
    shared_members,
    weight_coverage,
    z_for,
)


# ---------------------------------------------------------------------------
# cf -- discriminating counterexamples
# ---------------------------------------------------------------------------

def test_cf01_return_difference_is_not_relative_wealth():
    rd = return_difference(0.10, 0.05)
    rw = relative_wealth(0.10, 0.05)
    assert rd == pytest.approx(0.05)
    assert rw == pytest.approx(1.0 / 21.0)
    assert abs(rd - rw) > 1e-3
    # typed refusals stay distinct from both quantities
    assert relative_wealth(0.05, -1.0) == Unmeasured("benchmark_wealth_nonpositive")
    assert relative_wealth(-1.5, 0.0) == Unmeasured("group_wealth_negative")
    assert relative_wealth(float("nan"), 0.0) == Unmeasured("non_finite_input")
    assert relative_wealth(None, 0.0) == Unmeasured("missing_input")


def test_cf02_breadth_bounds_collapse_when_fully_covered():
    b = breadth(3, 5, 5)
    k_over_n, coverage, bounds = b  # exactly 3 fields, unpackable
    assert k_over_n == pytest.approx(0.6)
    assert coverage == pytest.approx(1.0)
    assert bounds == pytest.approx((0.6, 0.6))
    d = b.to_dict()
    assert d["bounds"][0] == pytest.approx(0.6)
    assert d["bounds"][1] == pytest.approx(0.6)
    assert d["bounds_kind"] == "identification_bounds_not_confidence_interval"
    # counts must be real ints (bool rejected) and ordered
    assert breadth(1.0, 2, 4).k_over_n == Unmeasured("invalid_counts")
    assert breadth(True, 1, 2).k_over_n == Unmeasured("invalid_counts")
    assert breadth(2, 1, 3).k_over_n == Unmeasured("invalid_counts")


def test_cf03_overlap_self_is_one():
    g = {"a": 0.5, "b": 0.3, "c": 0.2}
    assert overlap(g, g) == pytest.approx(1.0, abs=1e-12)
    g2 = {"S": 0.9, "x": 0.1}
    h = {"S": 0.9, "y": 0.1}
    assert overlap(g2, h) == pytest.approx(0.9)  # A14 shared-90% case
    assert isinstance(overlap({"a": 0.5}, None), Unmeasured)


def test_cf04_concentration_equal_weights_is_n():
    assert concentration({"a": 1, "b": 1, "c": 1, "d": 1}) == pytest.approx(4.0, abs=1e-12)
    assert concentration({"S": 0.9, "x": 0.1}) == pytest.approx(50.0 / 41.0)
    assert concentration({"a": 0.5, "b": 0.5}) == pytest.approx(2.0)


def test_cf05_zscore_refuses_mismatched_cohort():
    zs = cohort_zscores({"a": 1.0, "b": 2.0}, cohort_id="us_sectors_11")
    assert zs["state"] == "ok"
    assert zs["cohort_id"] == "us_sectors_11"
    with pytest.raises(CohortMismatch):
        z_for(zs, "a", cohort_id="other")
    assert z_for(zs, "a", cohort_id="us_sectors_11") == pytest.approx(-1.0)
    assert z_for(zs, "b", cohort_id="us_sectors_11") == pytest.approx(1.0)
    with pytest.raises(ValueError):
        cohort_zscores({"a": 1.0}, cohort_id="")
    with pytest.raises(ValueError):
        cohort_zscores({"a": 1.0}, cohort_id=None)


def test_cf07_rolling_carry_flag_when_terms_shared():
    assert rolling_carry(20, 5) == {
        "window_sessions": 20,
        "step_sessions": 5,
        "shared_terms": 15,
        "carry_flag": True,
    }
    assert rolling_carry(5, 5)["carry_flag"] is False  # flag set IFF L-h > 0
    assert rolling_carry(5, 5)["shared_terms"] == 0
    for bad in ((0, 1), (-1, 1), (1.5, 1), (True, 1), (None, 1)):
        with pytest.raises(ValueError):
            rolling_carry(*bad)


def test_cf08_unmeasured_never_ranks():
    values = {"a": 0.0, "b": -1.0, "c": None, "d": -2.0, "e": Unmeasured("missing_input")}
    res = rank_measured(values)
    assert res["ranked"] == ["a", "b", "d"]  # a valid 0.0 sorts above negatives
    assert res["unranked"] == ["c", "e"]  # None and Unmeasured never rank


# ---------------------------------------------------------------------------
# a-cases pinned by the acceptance matrix (B1 slice)
# ---------------------------------------------------------------------------

def test_a09_partial_weights_not_renormalised():
    nw = normalize_weights({"a": 0.5})
    assert nw == {"a": pytest.approx(1.0)}
    assert set(normalize_weights({"a": 1.0, "b": 3.0})) == {"a", "b"}
    # a partial map stays partial: no hidden completion against a bigger universe
    partial = {"a": 1.0}
    full = {"a": 0.5, "b": 0.5}
    assert overlap(partial, full) == pytest.approx(0.5)
    assert normalize_weights({}) == Unmeasured("empty_weights")
    assert normalize_weights(None) == Unmeasured("empty_weights")
    assert normalize_weights({"a": None}) == Unmeasured("missing_input")
    assert normalize_weights({"a": -0.5, "b": 1.5}) == Unmeasured("invalid_weights")
    assert normalize_weights({"a": 0.0}) == Unmeasured("invalid_weights")


def test_a10_breadth_one_of_one_measured_of_two():
    b = breadth(1, 1, 2)
    assert b.k_over_n == pytest.approx(1.0)
    assert b.coverage == pytest.approx(0.5)
    assert b.bounds == pytest.approx((0.5, 1.0))
    d = b.to_dict()
    assert d["k_over_n"] == pytest.approx(1.0)
    assert d["coverage"] == pytest.approx(0.5)


def test_a11_all_unavailable_typed_and_zero_coverage():
    b = breadth(0, 0, 4)
    assert b.k_over_n == Unmeasured("no_measured_members")
    assert b.coverage == pytest.approx(0.0)
    assert b.bounds == (pytest.approx(0.0), pytest.approx(1.0))
    empty = breadth(0, 0, 0)
    assert empty.k_over_n == Unmeasured("empty_population")
    assert empty.coverage == Unmeasured("empty_population")
    assert empty.bounds == Unmeasured("empty_population")
    assert breadth(None, 1, 2).k_over_n == Unmeasured("missing_input")


def test_a12_composition_only_breadth():
    before = {f"m{i}": i < 2 for i in range(10)}
    after = {"m0": True, "m1": True}
    assert before["m0"] is True and before["m2"] is False
    res = breadth_change(before, after)
    assert res["whole_list_before"].k_over_n == pytest.approx(0.2)
    assert res["whole_list_after"].k_over_n == pytest.approx(1.0)
    assert res["newly_positive_common"] == []
    assert res["composition_only"] is True
    assert res["exits"] == sorted(f"m{i}" for i in range(2, 10))
    assert res["entrants"] == []
    assert res["lost_coverage"] == res["exits"]
    assert res["common_known"] == ["m0", "m1"]
    assert res["common_cohort_before"].k_over_n == pytest.approx(1.0)
    assert res["common_cohort_after"].k_over_n == pytest.approx(1.0)
    assert res["same_cohort_rule"] == (
        "broadening counts only common_known members at both endpoints"
    )


def test_a13_unknown_to_positive_is_new_coverage():
    res = breadth_change({"a": None}, {"a": True})
    assert res["new_coverage_positive"] == ["a"]
    assert res["newly_positive_common"] == []
    assert res["common_known"] == []
    assert res["lost_coverage"] == []
    assert res["composition_only"] is False  # whole-list before is unmeasured
    assert isinstance(res["whole_list_before"].k_over_n, Unmeasured)


def test_a14_aliases_one_family():
    g = {"S": 0.9, "x": 0.1}
    h = {"S": 0.9, "y": 0.1}
    assert overlap(g, h) == pytest.approx(0.9)
    assert concentration(g) == pytest.approx(50.0 / 41.0)
    res = dedupe_source_roots([
        {"id": "g", "source_roots": ["S"]},
        {"id": "h", "source_roots": ["S"]},
    ])
    assert res["family_count"] == 1
    assert res["families"] == [["g", "h"]]
    assert res["alias_ids"] == ["g", "h"]
    assert res["item_count"] == 2
    assert res["unrooted_ids"] == []
    assert res["independent_count_rule"] == "one family = one vote; aliases add no evidence"


def test_a15_peer_change_names_reference_change():
    ref_before = {"a": 1.0, "b": 2.0, "c": 3.0}
    ref_after = {"a": 1.0, "b": 2.0, "c": 3.0, "d": -6.0}
    res = decompose_z_change(
        "b", ref_before, ref_after,
        cohort_id_before=US_SECTOR_COHORT_ID, cohort_id_after=US_SECTOR_COHORT_ID,
    )
    assert res["raw_unchanged"] is True
    assert res["added_ids"] == ["d"]
    assert res["removed_ids"] == []
    assert res["reference_population_changed"] is True
    assert res["total_change"] == pytest.approx(2.0 / math.sqrt(12.5))
    assert res["total_change"] > 0
    assert res["raw_move_component"] == pytest.approx(0.0, abs=EPS)
    assert res["reference_change_component"] == pytest.approx(res["total_change"])
    assert res["promotion_from_normalization_only"] is True
    assert res["mean_changed"] is True
    assert res["sd_changed"] is True
    assert res["cohort_id_changed"] is False
    # inputs read, never mutated
    assert ref_before == {"a": 1.0, "b": 2.0, "c": 3.0}
    assert ref_after == {"a": 1.0, "b": 2.0, "c": 3.0, "d": -6.0}


def test_a16_zero_vs_missing():
    res = rank_measured({"a": None, "b": -2.0, "c": 0.0, "d": -1.0})
    assert res["ranked"] == ["c", "d", "b"]
    assert res["unranked"] == ["a"]
    # a measured 0.0 also refuses a degenerate-cohort promotion to Leading
    assert classify_coordinate(0.0, 0.0) == "neutral"


def test_a18_both_down_is_relative_resilience():
    res = pair_interpretation(-0.02, -0.08)
    assert res["relative_wealth"] == pytest.approx(0.98 / 0.92 - 1.0)
    assert res["return_difference"] == pytest.approx(0.06)
    assert res["absolute_direction"] == "both_down"
    assert res["interpretation"] == "relative_resilience"
    assert "measured_inflow" in res["not_claimed"]
    assert res["not_claimed"] == ["absolute_recovery", "measured_inflow", "causal_handoff"]


def test_a19_beta_only_residual_zero():
    res = beta_only_residual(-0.02, -0.10, 0.2)
    assert abs(res["beta_residual"]) < 1e-12
    assert res["explained_by_stated_beta"] is True
    assert res["arithmetic_excess"] == pytest.approx(0.08)
    assert res["stated_beta"] == pytest.approx(0.2)
    assert res["beta_basis"] == "stated_hypothetical_past_known"
    assert res["interpretation"] == "fully explained by stated beta"


def test_a31_old_negative_expiry_is_carry_only():
    res = decompose_trailing_change([-0.1, 0.0, 0.0], [0.0])
    assert res["trailing_change"] == pytest.approx(0.1)
    assert res["expiry_component"] == pytest.approx(0.1)
    assert res["new_return_component"] == pytest.approx(0.0, abs=1e-12)
    assert res["carry_flag"] is True
    assert res["carry_only"] is True
    assert res["shared_terms"] == 2
    assert res["trailing_change"] == pytest.approx(
        res["expiry_component"] + res["new_return_component"]
    )


# ---------------------------------------------------------------------------
# laws
# ---------------------------------------------------------------------------

def test_unmeasured_has_no_truth_value_and_no_arithmetic():
    u = Unmeasured("missing_input")
    with pytest.raises(TypeError):
        bool(u)
    with pytest.raises(TypeError):
        if u:  # pragma: no cover - the raise IS the assertion
            pass
    with pytest.raises(TypeError):
        _ = u + 1.0
    with pytest.raises(TypeError):
        _ = u < 0.0
    with pytest.raises(TypeError):
        _ = u or 0.0
    assert u.status == "unmeasured"
    assert u.to_dict() == {"status": "unmeasured", "reason": "missing_input"}
    assert u == Unmeasured("missing_input")
    with pytest.raises(ValueError):
        Unmeasured("not_a_reason")
    # measured-ness: bools / None / nan / inf are not measurements; 0.0 is
    assert not is_measured(u)
    assert not is_measured(None)
    assert not is_measured(True)
    assert not is_measured(float("nan"))
    assert not is_measured(float("inf"))
    assert is_measured(0)
    assert is_measured(0.0)
    assert is_measured(-0.5)


def test_functions_total_over_none():
    # T05
    assert isinstance(relative_wealth(None, None), Unmeasured)
    assert isinstance(return_difference(None, None), Unmeasured)
    assert isinstance(breadth(None, None, None).k_over_n, Unmeasured)
    bc = breadth_change(None, None)
    assert isinstance(bc["whole_list_after"].k_over_n, Unmeasured)
    assert bc["composition_only"] is False
    zs = cohort_zscores(None, cohort_id=US_SECTOR_COHORT_ID)
    assert zs["state"] == "insufficient_reference"
    assert isinstance(zs["mean"], Unmeasured)
    assert zs["n_reference"] == 0
    assert isinstance(z_for(zs, "x", cohort_id=US_SECTOR_COHORT_ID), Unmeasured)
    assert classify_coordinate(None, None) == "unmeasured"
    assert rank_measured(None) == {"ranked": [], "unranked": []}
    # T04
    assert isinstance(normalize_weights(None), Unmeasured)
    assert isinstance(overlap(None, None), Unmeasured)
    assert isinstance(concentration(None), Unmeasured)
    assert shared_members(None, None) == []
    wc = weight_coverage(None, None)
    assert wc["expected_n"] == 0
    assert isinstance(wc["count_coverage"], Unmeasured)
    assert isinstance(wc["measured_weight_share"], Unmeasured)
    # T03 (pure math slice) -- ValueError is the documented programmer-error path
    with pytest.raises(ValueError):
        rolling_carry(None, 1)
    assert isinstance(decompose_trailing_change(None, None), Unmeasured)
    # T08
    assert isinstance(beta_only_residual(None, None, None), Unmeasured)
    assert isinstance(pair_interpretation(None, None), Unmeasured)
    dz = decompose_z_change("zz", None, None,
                            cohort_id_before="c", cohort_id_after="c")
    assert isinstance(dz["total_change"], Unmeasured)
    assert isinstance(dz["raw_move_component"], Unmeasured)
    dd = dedupe_source_roots(None)
    assert dd["family_count"] == 0
    assert dd["item_count"] == 0
    assert dd["families"] == []


# ---------------------------------------------------------------------------
# additional contract pins within the B1 slice
# ---------------------------------------------------------------------------

def test_extra_cohort_reference_rules():
    single = cohort_zscores({"a": 3.0}, cohort_id="c")
    assert single["state"] == "insufficient_reference"
    assert single["mean"] == pytest.approx(3.0)
    assert single["z"]["a"] == Unmeasured("insufficient_reference")
    assert single["sd"] == Unmeasured("insufficient_reference")
    tie = cohort_zscores({"a": 5.0, "b": 5.0}, cohort_id="c")
    assert tie["state"] == "neutral_tie"  # a tie at the origin is not Leading
    assert tie["z"]["a"] == Unmeasured("degenerate_dispersion")
    mixed = cohort_zscores({"a": 5.0, "b": 5.0, "c": None}, cohort_id="c")
    assert mixed["z"]["c"] == Unmeasured("missing_input")
    assert z_for(cohort_zscores({"a": 1.0}, cohort_id="c"), "zz", cohort_id="c") == (
        Unmeasured("not_in_reference")
    )


def test_extra_weight_coverage_and_shared_members():
    wc = weight_coverage({"a": 0.6, "b": 0.4}, ["a", "z"])
    assert wc["expected_n"] == 2
    assert wc["measured_n"] == 1
    assert wc["missing_ids"] == ["b"]
    assert wc["unexpected_ids"] == ["z"]
    assert wc["weight_known_n"] == 2
    assert wc["count_coverage"] == pytest.approx(0.5)
    assert wc["measured_weight_share"] == pytest.approx(0.6)
    partial_wc = weight_coverage({"a": 0.6, "b": None}, ["a"])
    assert partial_wc["weight_known_n"] == 1
    assert isinstance(partial_wc["measured_weight_share"], Unmeasured)
    assert shared_members({"a": 0.5, "b": 0.5}, {"a": 0.2, "b": 0.0, "c": 0.3}) == ["a"]
    assert shared_members({"a": 0.5}, {"a": None}) == []


def test_extra_trailing_change_full_refresh_and_empty():
    fresh = decompose_trailing_change([0.02, -0.01], [0.03, 0.04])
    assert fresh["carry_flag"] is False
    assert fresh["shared_terms"] == 0
    assert fresh["trailing_change"] == pytest.approx(0.06)
    assert fresh["expiry_component"] == pytest.approx(-0.01)
    assert fresh["new_return_component"] == pytest.approx(0.07)
    assert fresh["trailing_change"] == pytest.approx(
        fresh["expiry_component"] + fresh["new_return_component"]
    )
    assert fresh["carry_only"] is False
    assert decompose_trailing_change([], [0.01]) == Unmeasured("empty_population")
    assert decompose_trailing_change([0.01, None], [0.01]) == Unmeasured("missing_input")


def test_extra_pair_interpretation_other_quadrants():
    assert pair_interpretation(0.02, -0.03)["interpretation"] == "divergent_price_action"
    assert pair_interpretation(0.02, -0.03)["absolute_direction"] == "mixed"
    weak = pair_interpretation(-0.05, -0.02)
    assert weak["absolute_direction"] == "both_down"
    assert weak["interpretation"] == "relative_weakness"
    strong = pair_interpretation(0.03, 0.01)
    assert strong["interpretation"] == "relative_strength"
    flat = pair_interpretation(0.0, 0.0)
    assert flat["interpretation"] == "no_relative_change"
    assert isinstance(pair_interpretation(-1.0, -1.0), Unmeasured)  # benchmark wealth <= 0


def test_extra_dedupe_unrooted_and_transitive():
    res = dedupe_source_roots([
        {"id": "a", "source_roots": ["r1", "r2"]},
        {"id": "b", "source_roots": ["r2", "r3"]},
        {"id": "c", "source_roots": ["r3"]},
        {"id": "solo", "source_roots": []},
    ])
    assert res["family_count"] == 2
    assert res["families"] == [["a", "b", "c"], ["solo"]]
    assert res["alias_ids"] == ["a", "b", "c"]
    assert res["unrooted_ids"] == ["solo"]
