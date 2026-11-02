"""Contract tests for engine.leadership_rotation_context (LR-MEAS-SPEC-1).

Pure-Python fixtures only: no network, no ``data/`` reads, no clock reads.
Case ids follow the programme acceptance matrix (cf/a cases); lane LR-MEAS-B1
covered the pure measurement core (spec sections 1, 2, 3, 4, 8); lane
LR-MEAS-B2 adds the clock/input contracts (section 5), cohort_at (section 4)
and the three contract objects (section 6).
"""

import copy
import json
import math

import pytest

from engine.leadership_rotation_context import (
    EPS,
    US_SECTOR_COHORT_ID,
    Breadth,
    CohortMismatch,
    GroupMeasurement,
    ResearchEstimate,
    TransitionObservation,
    Unmeasured,
    admissible_as_known,
    admit_use,
    attribute_coordinate,
    beta_only_residual,
    breadth,
    breadth_change,
    classify_coordinate,
    clock_identities,
    cohort_at,
    cohort_zscores,
    concentration,
    confirmation_maturity,
    decompose_trailing_change,
    decompose_z_change,
    dedupe_source_roots,
    diagnose_rotation_payload,
    earliest_observable_coordinate,
    from_leadership_receipt,
    from_sector_record,
    is_measured,
    normalize_weights,
    observation_clock,
    overlap,
    pair_interpretation,
    parse_time,
    rank_measured,
    relative_wealth,
    return_difference,
    rolling_carry,
    sector_cohort_snapshot,
    separate_from_legacy,
    shared_members,
    us_sector_cohort,
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
    # coverage of a partial map is measured against the EXPECTED map: the
    # measured weight share is 0.6 (no renormalisation), never 1.0
    wc = weight_coverage({"a": 0.6, "b": 0.4}, ["a"])
    assert wc["measured_weight_share"] == pytest.approx(0.6)
    assert wc["count_coverage"] == pytest.approx(0.5)
    assert wc["missing_ids"] == ["b"]


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
    # clocks / cohort / admission: unknown stays a string state, None or []
    assert parse_time(None) == Unmeasured("missing_input")
    assert admissible_as_known(None, None) == "unknown"
    assert admit_use(None, "display") == "withheld"
    clocks = clock_identities(None, None)
    assert clocks["evidence_older_than_live"] is None
    assert clocks["merged"] is False  # a real constant, not an unknown stand-in
    cohort = cohort_at(None, as_of="2026-10-06")
    assert cohort["members"] == [] and cohort["excluded_unparseable"] == []
    # adapters (LR-MEAS-B3): every owner adapter is total over None
    sep = separate_from_legacy(None, None)
    assert sep["legacy_status"] is None
    assert sep["legacy_events"] == [] and sep["transition_observations"] == []
    assert sep["attached_to_legacy"] == 0
    assert earliest_observable_coordinate(None, before="2026-10-05") == (
        Unmeasured("missing_input")
    )
    assert from_sector_record(None) == Unmeasured("missing_input")
    snap = sector_cohort_snapshot(None)
    assert snap["measured"] == []
    assert len(snap["missing"]) == 11
    assert all(reason == "missing_input" for _, reason in snap["missing"])
    assert snap["positive_breadth"]["k_over_n"] == {
        "status": "unmeasured", "reason": "no_measured_members"
    }
    gm_none = from_leadership_receipt(None, group_id="g", cohort_id="c")
    assert gm_none.value == Unmeasured("missing_input")
    assert gm_none.session_end is None and gm_none.benchmark is None
    diag = diagnose_rotation_payload(None, cohort_id="c")
    assert diag["rows"] == [] and diag["flag_counts"] == {}
    attrib = attribute_coordinate(None, as_of="2026-10-06")
    assert attrib["observations"] == [] and attrib["unavailable_pair_ids"] == []


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


# ---------------------------------------------------------------------------
# a-cases and cf-cases pinned by the acceptance matrix (B2 slice: clocks,
# cohort membership, and the three contract objects)
# ---------------------------------------------------------------------------

def test_a05_unknown_use_withheld():
    assert admit_use({"display": "permitted"}, "derive") == "withheld"  # absent use
    assert admit_use(None, "display") == "withheld"  # no rights map at all
    assert admit_use({"redistribute": "refused"}, "redistribute") == "refused"
    assert admit_use({"display": "permitted"}, "display") == "permitted"
    assert admit_use({"display": True}, "display") == "withheld"  # truthy != permission


def test_a06_revision_after_decision_not_admissible():
    assert admissible_as_known(
        "2026-10-07T13:00:00Z", "2026-10-06T21:00:00Z"
    ) == "not_admissible"  # the revision arrived after the decision cutoff
    assert admissible_as_known(None, "2026-10-06T21:00:00Z") == "unknown"
    assert admissible_as_known("2026-10-06T20:00:00+00:00", "2026-10-06T21:00:00Z") == (
        "admissible"
    )
    assert admissible_as_known("garbage", "2026-10-06T21:00:00Z") == "unknown"


def test_a07_evidence_and_live_clocks_distinct():
    clocks = clock_identities("2026-10-05", "2026-10-06T14:30:00Z")
    assert clocks["evidence_older_than_live"] is True
    assert clocks["merged"] is False  # the two clocks are never merged
    assert clocks["evidence_label"] != clocks["live_label"]
    assert clocks["evidence_label"] == "group evidence as of 2026-10-05"
    unknown = clock_identities(None, None)
    assert unknown["evidence_older_than_live"] is None
    assert unknown["evidence_label"] == "group evidence date unknown"
    assert unknown["live_label"] == "live price unavailable"
    assert unknown["merged"] is False
    # unparseable evidence must not fake an ordering either
    garbage = clock_identities("garbage", "2026-10-06T14:30:00Z")
    assert garbage["evidence_older_than_live"] is None


def test_a08_late_joiner_not_in_old_cohort():
    memberships = [
        {"member_id": "OLD", "effective_from": "2020-01-01"},
        {"member_id": "NEW", "effective_from": "2026-09-01", "known_at": "2026-09-01"},
        {"member_id": "GONE", "effective_from": "2020-01-01", "effective_to": "2026-03-01"},
    ]
    cohort = cohort_at(memberships, as_of="2026-06-30")
    assert cohort["members"] == ["OLD"]  # the late joiner is NOT in the old cohort
    assert cohort["excluded_future_effective"] == ["NEW"]
    assert cohort["excluded_expired"] == ["GONE"]
    assert cohort["population"] == "reconstructed"
    as_known_rows = [
        {"member_id": "LATE", "effective_from": "2026-01-01", "known_at": "2026-08-01"},
        {"member_id": "NOK", "effective_from": "2026-01-01"},
    ]
    known = cohort_at(as_known_rows, as_of="2026-06-30", as_known=True)
    assert known["members"] == []
    assert known["excluded_not_yet_known"] == ["LATE"]
    assert known["excluded_knowledge_unknown"] == ["NOK"]
    assert known["population"] == "as_known"
    assert cohort_at(as_known_rows, as_of=None) == Unmeasured("missing_input")
    assert cohort_at(as_known_rows, as_of="not a date") == Unmeasured("unparseable_time")


def test_a25_reconstructed_label_kept():
    gm = GroupMeasurement(
        group_id="XLK", group_kind="sector", cohort_id=US_SECTOR_COHORT_ID,
        metric="relative_wealth_pct", units="pct", value=1.5,
    )
    payload = gm.to_dict()
    assert payload["evidence_mode"] == "reconstructed_price_history"
    assert payload["may_rank"] is False
    obs = TransitionObservation(
        definition_id="leadership_rotation_context/1",
        definition_version="leadership_rotation_context/v1",
        roles={"receiver": "XLK", "donor": "XLU"},
        coordinate={"date": "2026-10-01", "vintage": None, "as_of": "2026-10-02"},
        evidence_mode="reconstructed_price_history", naturally_observed=False,
    )
    obs_payload = obs.to_dict()
    assert obs_payload["evidence_mode"] == "reconstructed_price_history"
    assert obs_payload["naturally_observed"] is False
    assert obs.relationship == "context_only"
    assert obs_payload["relationship"] == "context_only"


def test_cf06a_reconstructed_transition_cannot_claim_natural():
    base = dict(
        definition_id="leadership_rotation_context/1",
        definition_version="leadership_rotation_context/v1",
        roles={"receiver": "XLK", "donor": "XLU"},
        coordinate={"date": "2026-10-01", "vintage": None, "as_of": "2026-10-02"},
    )
    with pytest.raises(ValueError):
        TransitionObservation(evidence_mode="reconstructed_price_history",
                              naturally_observed=True, **base)
    retained = TransitionObservation(evidence_mode="original_retained",
                                     naturally_observed=True, **base)
    assert retained.naturally_observed is True  # only original_retained may claim it
    assert TransitionObservation(evidence_mode="original_retained",
                                 naturally_observed=False, **base).naturally_observed is False
    with pytest.raises(ValueError):
        TransitionObservation(definition_id=base["definition_id"],
                              definition_version=base["definition_version"],
                              evidence_mode="original_retained", naturally_observed=True,
                              roles=base["roles"],
                              coordinate={"date": "2026-10-01", "as_of": "2026-10-02"})
    with pytest.raises(ValueError):
        TransitionObservation(definition_id=base["definition_id"],
                              definition_version=base["definition_version"],
                              evidence_mode="original_retained", naturally_observed=False,
                              roles=base["roles"], coordinate=base["coordinate"],
                              relationship="attached")


def test_a32_maturity_is_t_plus_c_plus_h():
    assert confirmation_maturity(0, 3, 20) == 23
    assert confirmation_maturity(5, 3, 20) == 28
    clock = observation_clock("2026-10-06", confirmation_sessions=3, horizon_sessions=20)
    assert clock["maturity_offset_sessions"] == 23
    assert clock["maturity_rule"] == "t+c+H from the original origin"
    assert clock["session_end"] == "2026-10-06"
    for bad_origin, bad_c, bad_h in (
        (-1, 3, 20), (0, -3, 20), (0, 3, -1), (0, True, 20), (0, 3, True),
        (0, 1.5, 20), (0, 3, None), (0.0, 3, 20),
    ):
        with pytest.raises(ValueError):
            confirmation_maturity(bad_origin, bad_c, bad_h)
    with pytest.raises(ValueError):
        observation_clock("2026-10-06", confirmation_sessions=-1)
    with pytest.raises(ValueError):
        observation_clock("2026-10-06", horizon_sessions=True)
    with pytest.raises(ValueError):
        observation_clock("2026-10-06", confirmation_sessions=2.0)


# ---------------------------------------------------------------------------
# the three contract objects (spec section 6)
# ---------------------------------------------------------------------------

def test_group_measurement_validation():
    kw = dict(group_id="XLK", group_kind="sector", cohort_id=US_SECTOR_COHORT_ID,
              metric="relative_wealth_pct", units="pct")
    for bad in ({"group_kind": "cluster"}, {"metric": "alpha"}, {"units": "ratio"},
                {"evidence_mode": "hallucinated"}):
        with pytest.raises(ValueError):
            GroupMeasurement(**{**kw, **bad})
    with pytest.raises(ValueError):
        GroupMeasurement(**{**kw, "value": True})  # a bool is never a measurement
    assert isinstance(GroupMeasurement(**kw).value, Unmeasured)  # default is typed unknown
    assert GroupMeasurement(**{**kw, "value": Unmeasured("thin_history")}).value == (
        Unmeasured("thin_history")
    )
    assert GroupMeasurement(**{**kw, "value": 0.0}).value == 0.0  # a valid zero IS measured
    coverage = GroupMeasurement(
        **{**kw, "expected_members": ("a", "b", "c", "d"), "measured_members": ("a", "b")}
    )
    assert coverage.coverage == pytest.approx(0.5)
    counts = GroupMeasurement(**{**kw, "expected_n": 4, "measured_n": 2})
    assert counts.coverage == pytest.approx(0.5)
    assert GroupMeasurement(**kw).coverage == Unmeasured("empty_population")
    assert GroupMeasurement(**{**kw, "expected_n": 0, "measured_n": 0}).coverage == (
        Unmeasured("empty_population")
    )


def test_research_estimate_unavailable_by_default():
    est = ResearchEstimate()
    assert est.status == "unavailable"
    assert est.probability == Unmeasured("no_admitted_model_support")
    with pytest.raises(ValueError):
        ResearchEstimate(probability=0.6)  # identity incomplete -> unavailable, not 0.6
    full = dict(
        target="sector leadership flip", horizon_sessions=20, origin="2026-10-01",
        exit_rule="z < 0 for 5 sessions", model="logistic_beta", protocol="prereg-1",
        cohort_id=US_SECTOR_COHORT_ID, training_cutoff="2026-09-30",
        supported_population="us sectors 11", uncertainty_definition="laplace",
        evidence_tier="synthetic",
    )
    with pytest.raises(ValueError):
        ResearchEstimate(**full, probability=1.5)  # outside [0, 1]
    with pytest.raises(ValueError):
        ResearchEstimate(**{**full, "model": None}, probability=0.6)  # identity incomplete
    assert ResearchEstimate(**full, probability=0.6).status == "estimate"
    assert ResearchEstimate(**full, probability=0).status == "estimate"  # 0.0 is measured
    with pytest.raises(ValueError):
        ResearchEstimate(**full, probability=True)  # a bool is never a probability


def test_objects_to_dict_json_safe():
    gm = GroupMeasurement(
        group_id="XLK", group_kind="sector", cohort_id=US_SECTOR_COHORT_ID,
        metric="relative_wealth_pct", units="pct", value=Unmeasured("thin_history"),
        breadth=breadth(2, 3, 5), concentration=Unmeasured("missing_input"),
        overlap_with=(("XLK", 0.9),), missing_members=(("XLF", "missing_input"),),
    )
    obs = TransitionObservation(
        definition_id="leadership_rotation_context/1",
        definition_version="leadership_rotation_context/v1",
        roles={"receiver": "XLK", "donor": "XLU"},
        coordinate={"date": "2026-10-01", "vintage": None, "as_of": "2026-10-02"},
        evidence_mode="synthetic_fixture", naturally_observed=False,
        interpretation="relative_weakness", source_context={"pair_id": "XLK>XLU"},
        contrary_evidence=(),
    )
    est = ResearchEstimate(
        target="sector leadership flip", horizon_sessions=20, origin="2026-10-01",
        exit_rule="z < 0 for 5 sessions", model="logistic_beta", protocol="prereg-1",
        cohort_id=US_SECTOR_COHORT_ID, training_cutoff="2026-09-30",
        supported_population="us sectors 11", uncertainty_definition="laplace",
        evidence_tier="synthetic",
    )  # probability stays the typed Unmeasured default
    for obj, schema in (
        (gm, "leadership_rotation_context.group_measurement/v1"),
        (obs, "leadership_rotation_context.transition_observation/v1"),
        (est, "leadership_rotation_context.research_estimate/v1"),
    ):
        payload = obj.to_dict()
        json.dumps(payload, allow_nan=False)  # must serialize, no NaN/Inf
        assert payload["schema"] == schema
        assert payload["display_only"] is True
    assert gm.to_dict()["may_rank"] is False
    assert gm.to_dict()["coverage"] == {
        "status": "unmeasured", "reason": "empty_population"
    }
    assert est.to_dict()["status"] == "unavailable"
    assert est.to_dict()["probability"] == {
        "status": "unmeasured", "reason": "no_admitted_model_support"
    }
    assert obs.to_dict()["roles"] == {"receiver": "XLK", "donor": "XLU"}


def test_extra_parse_time_and_clocks():
    assert parse_time(None) == Unmeasured("missing_input")
    assert parse_time("nonsense") == Unmeasured("unparseable_time")
    assert parse_time(True) == Unmeasured("unparseable_time")
    utc = parse_time("2026-10-06T14:30:00Z")
    assert utc is not None and not isinstance(utc, Unmeasured)
    assert parse_time("2026-10-06T14:30:00+00:00") == utc  # Z and offset agree
    assert parse_time("2026-10-06") == parse_time("2026-10-06T00:00:00Z")  # date = 00:00 UTC
    assert parse_time("2026-10-06T16:30:00+02:00") == utc  # aware offsets normalise to UTC
    assert parse_time(utc) == utc  # an aware datetime passes through
    naive = parse_time("2026-10-06T14:30:00")
    assert naive == utc  # a naive string is read as UTC
    assert naive.tzinfo is not None
    assert admissible_as_known("2026-10-06T21:00:00Z", None) == "unknown"


# ---------------------------------------------------------------------------
# owner adapters (spec section 7) -- read-only projections, lazy imports
# ---------------------------------------------------------------------------

ASOF = "2026-10-06"


def _ratio_batch(*rows):
    return {"schema": "ratio_lens.short_horizons/v1", "as_of": ASOF,
            "definition_id": "ratio_lens.short_horizons/1",
            "pairs": list(rows), "reason_codes": []}


def _ratio_receipt(group="defensive_sector", num="XLP", den="XLK",
                   num_daily=0.003, den_daily=0.001, pid=None):
    import numpy as np
    import pandas as pd

    from engine.oracle import ratio_lens as RL
    from lib import nyse_calendar as cal

    def levels(n=45, daily=0.001):
        dates = cal.sessions_between(
            pd.Timestamp(ASOF).date() - pd.Timedelta(days=n * 3),
            pd.Timestamp(ASOF).date(),
        )[-n:]
        return pd.Series(100.0 * (1 + daily) ** np.arange(len(dates)),
                         index=pd.DatetimeIndex(dates))

    pair_row = {
        "id": pid or f"{num.lower()}_vs_{den.lower()}",
        "num": num, "den": den, "kind": "etf",
        "name_en": f"{num} vs {den}", "name_zh": f"{num} / {den}",
        "reads_as_en": "Relative price context", "reads_as_zh": "相对价格",
        "context_group": group,
    }
    return RL.short_horizon_receipt(pair_row, levels(daily=num_daily),
                                    levels(daily=den_daily), as_of=ASOF)


def test_sector_cohort_is_existing_eleven():
    from engine import sector_cycles

    cohort = us_sector_cohort()
    assert cohort == tuple(sorted(sector_cycles.SECTORS))
    assert len(cohort) == 11  # the existing eleven; the adapter mints no new ids


def test_sector_adapter_names_relative_wealth_pct_and_rolling():
    rec = {"ticker": "XLK", "kind": "sector",
           "now": {"rs_21d": 1.2, "rs_63d": 3.4, "rs_126d": 5.6,
                   "rs_above_trend": True, "thin_history": False}}
    gm = from_sector_record(rec, benchmark="SPY", session_end=ASOF)
    assert gm.metric == "relative_wealth_pct"  # a pp-vs-benchmark RS reading, NOT wealth ratio
    assert gm.units == "pct"
    assert gm.group_id == "XLK" and gm.group_kind == "sector"
    assert gm.cohort_id == US_SECTOR_COHORT_ID
    assert gm.value == pytest.approx(3.4)
    assert gm.window_sessions == 63 and gm.rolling_window is True
    assert gm.price_basis == "total_return"
    assert gm.membership_source == "etf_proxy:engine.sector_cycles.SECTORS"
    assert gm.source_roots == ("engine.sector_cycles",)
    assert from_sector_record(rec, horizon="rs_21d").window_sessions == 21
    with pytest.raises(ValueError):
        from_sector_record(rec, horizon="rs_5d")
    thin = {"ticker": "XLF", "kind": "sector",
            "now": {"thin_history": True, "rs_rows": 150}}
    assert from_sector_record(thin).value == Unmeasured("thin_history")
    assert from_sector_record({"ticker": "XLE", "kind": "sector", "now": {}}).value == (
        Unmeasured("missing_input")
    )


def test_owner_receipt_adapter_names_return_difference(tmp_path):
    receipt = {"schema": "mi.leadership_receipt.v1",
               "rel_5d": 0.001, "rel_20d": 0.02, "rel_60d": None,
               "benchmark": {"label": "S&P 500", "label_zh": "标普500"},
               "as_of": ASOF,
               "sample": {"observed_n": 8, "configured_n": 10}}
    gm = from_leadership_receipt(receipt, group_id="ai_infra", cohort_id="theme:ai_infra")
    assert gm.metric == "return_difference"  # a plain difference, never a wealth relative
    assert gm.units == "fraction"
    assert gm.value == pytest.approx(0.02)
    assert gm.window_sessions == 20 and gm.rolling_window is True
    assert gm.benchmark == "S&P 500" and gm.session_end == ASOF
    assert gm.expected_n == 10 and gm.measured_n == 8
    assert gm.coverage == pytest.approx(0.8)
    assert gm.group_kind == "curated_theme"
    assert gm.source_roots == ("engine.leadership_receipt",)
    assert from_leadership_receipt(receipt, group_id="g", cohort_id="c",
                                   horizon="rel_5d").window_sessions == 5
    assert from_leadership_receipt(receipt, group_id="g", cohort_id="c",
                                   horizon="rel_60d").value == Unmeasured("missing_input")
    with pytest.raises(ValueError):
        from_leadership_receipt(receipt, group_id="g", cohort_id="c", horizon="rel_1d")
    unknown_sample = dict(receipt, sample={"observed_n": "—", "configured_n": "—"})
    gm2 = from_leadership_receipt(unknown_sample, group_id="g", cohort_id="c")
    assert gm2.expected_n is None and gm2.measured_n is None
    assert gm2.coverage == Unmeasured("empty_population")

    # (2) the REAL owner output: leadership_receipt.build_receipt -> adapter
    from engine.leadership_receipt import build_receipt

    basket = {"id": "test_basket", "created": "2020-01-01",
              "perf": {"5d": {"rel": 0.01}, "20d": {"rel": 0.02}, "60d": {"rel": 0.03}},
              "observation": {"effective_as_of": "2026-10-02", "configured_n": 10,
                              "observed_n": 10, "coverage": 1.0, "status": "complete",
                              "basis": "exact_close_at_effective_as_of",
                              "aggregate_eligible": True, "min_members": 3,
                              "min_coverage": 0.6},
              "members": []}
    theme = {"breadth": {"pct50": 0.5, "pct200": 0.4, "n": 10},
             "leadership": {"breadth": "broad",
                            "top": [{"ticker": "AAA", "ret_20d": 0.1}]},
             "leadership_split": False}
    theme_intel = {"as_of": "2026-10-02", "bench_label": "S&P 500",
                   "bench_label_zh": "标普500"}
    r = build_receipt(basket, theme, theme_intel, "us", tmp_path)
    r_frozen = copy.deepcopy(r)
    g = from_leadership_receipt(r, group_id="test_basket", cohort_id="t",
                                horizon="rel_20d")
    assert g.metric == "return_difference"
    assert g.units == "fraction"
    assert g.window_sessions == 20
    assert g.value == pytest.approx(r["rel_20d"]) == pytest.approx(0.02)
    assert g.session_end == r["as_of"]
    assert g.benchmark == "S&P 500"
    assert g.expected_n == 10 and g.measured_n == 10
    assert r == r_frozen  # the owner receipt is read, never modified


def test_a17_all_at_origin_is_neutral_not_leading():
    payload = {
        "asof": ASOF,
        "subsectors": [
            {"key": "semis", "perf": {"1M": 2.0, "3M": 5.0},
             "rs_ratio": 0.9, "rs_mom": 0.4, "quadrant": "leading"},
            {"key": "broken", "perf": {"1M": None, "3M": None},
             "rs_ratio": 0.0, "rs_mom": 0.0, "quadrant": "leading"},
        ],
    }
    frozen = copy.deepcopy(payload)
    diag = diagnose_rotation_payload(payload, cohort_id="us_subsectors")
    assert payload == frozen  # the owner payload is read, never modified
    assert diag["schema"] == "leadership_rotation_context.rotation_diagnostic/v1"
    assert diag["rs_units"] == "return_difference_pp_vs_median"
    assert diag["owner_fields_modified"] is False
    by_key = {row["key"]: row for row in diag["rows"]}
    assert by_key["semis"]["projection_quadrant"] == "leading"
    assert by_key["semis"]["flags"] == []
    # the exact origin is a tie, not Leading -- and a missing z was coerced to 0.0
    assert by_key["broken"]["projection_quadrant"] == "unmeasured"
    assert by_key["broken"]["owner_quadrant"] == "leading"
    assert by_key["broken"]["flags"] == [
        "missing_coerced_to_zero", "neutral_origin_labelled_leading"
    ]
    assert diag["flag_counts"] == {
        "missing_coerced_to_zero": 1, "neutral_origin_labelled_leading": 1
    }
    # the underlying law, pinned through THIS module's own functions as well
    assert cohort_zscores({"a": 5.0, "b": 5.0}, cohort_id="c")["state"] == "neutral_tie"
    assert classify_coordinate(0.0, 0.0) == "neutral"


def test_cf06_reconstructed_coordinate_never_naturally_observed():
    receipt = _ratio_receipt()
    batch = _ratio_batch(receipt)
    frozen = copy.deepcopy(batch)
    out = attribute_coordinate(batch, as_of=ASOF,
                               mode="reconstructed_price_history",
                               recorded_at="2026-10-06T21:00:00Z")
    assert batch == frozen  # the owner input is read, never modified
    assert out["schema"] == "leadership_rotation_context.coordinate_attribution/v1"
    assert out["relationship"] == "context_only"
    assert out["legacy_events_modified"] is False
    assert out["unavailable_pair_ids"] == []
    assert len(out["observations"]) == 1
    obs = out["observations"][0]
    assert obs.naturally_observed is False  # reconstructed: never a natural observation
    assert obs.evidence_mode == "reconstructed_price_history"
    assert obs.roles == {"receiver": "XLP", "donor": "XLK",
                         "context_group": "defensive_sector"}
    assert obs.coordinate["date"] == ASOF and obs.coordinate["as_of"] == ASOF
    assert obs.first_known_observation_id == f"rotation_early_context/1:xlp_vs_xlk:{ASOF}"
    assert isinstance(obs.source_context, dict)  # a deepcopy, not the owner row
    retained = attribute_coordinate(batch, as_of=ASOF, mode="original_retained",
                                    recorded_at="2026-10-06T21:00:00Z")
    assert retained["observations"][0].naturally_observed is True
    unrecorded = attribute_coordinate(batch, as_of=ASOF, mode="original_retained")
    assert unrecorded["observations"][0].naturally_observed is False
    with pytest.raises(ValueError):
        attribute_coordinate(batch, as_of=ASOF, mode="hallucinated")
    with pytest.raises(ValueError):
        TransitionObservation(
            definition_id="d", definition_version="v", roles={"receiver": "a", "donor": "b"},
            coordinate={"date": ASOF, "vintage": None, "as_of": ASOF},
            evidence_mode="reconstructed_price_history", naturally_observed=True,
        )


def test_extra_earliest_coordinate_and_legacy_separation():
    receipt = _ratio_receipt()
    out = attribute_coordinate(_ratio_batch(receipt), as_of=ASOF,
                               mode="reconstructed_price_history")
    first = earliest_observable_coordinate(out["observations"], before="2026-10-07")
    assert first["relationship"] == "context_only"
    assert first["legacy_event_untouched"] is True
    assert first["coordinate"]["date"] == ASOF
    assert earliest_observable_coordinate(out["observations"], before="2026-10-05") == (
        Unmeasured("missing_input")
    )
    roles_hit, roles_miss = out["observations"][0], None
    explicit = [
        TransitionObservation(
            definition_id="d", definition_version="v",
            roles={"receiver": "A", "donor": "B"},
            coordinate={"date": "2026-10-01", "vintage": None, "as_of": ASOF},
            evidence_mode="synthetic_fixture", naturally_observed=False),
        TransitionObservation(
            definition_id="d", definition_version="v",
            roles={"receiver": "B", "donor": "C"},
            coordinate={"date": "2026-10-02", "vintage": None, "as_of": ASOF},
            evidence_mode="synthetic_fixture", naturally_observed=False),
    ]
    picked = earliest_observable_coordinate(explicit, before="2026-10-07",
                                            roles={"receiver": "B"})
    assert picked["evidence_mode"] == "synthetic_fixture"
    assert picked["coordinate"]["date"] == "2026-10-02"  # the B observation, not the A one
    # legacy separation: the two evidence classes stay distinct, nothing attaches
    ledger = {"status": "OK", "rows": [
        {"lifecycle_id": "L1", "observation_date": "2026-09-30",
         "recorded_at": "2026-10-01T00:00:00Z", "mode": "RECONSTRUCTED_REPLAY",
         "from_key": "xlp", "to_key": "xlk", "native_extra": "kept-out"}]}
    ledger_frozen = copy.deepcopy(ledger)
    sep = separate_from_legacy(explicit, ledger)
    assert ledger == ledger_frozen
    assert sep["schema"] == "leadership_rotation_context.legacy_separation/v1"
    assert sep["legacy_status"] == "OK"
    assert sep["legacy_events"] == [{
        "lifecycle_id": "L1", "observation_date": "2026-09-30",
        "recorded_at": "2026-10-01T00:00:00Z", "mode": "RECONSTRUCTED_REPLAY",
        "from_key": "xlp", "to_key": "xlk"}]
    assert sep["transition_observations"] == [o.to_dict() for o in explicit]
    assert sep["relationship"] == "context_only"
    assert sep["attached_to_legacy"] == 0
    # no ledger history at all is an unknown status, never a fabricated one
    sep_none = separate_from_legacy(explicit, None)
    assert sep_none["legacy_status"] is None
    assert sep_none["attached_to_legacy"] == 0


def test_extra_sector_cohort_snapshot():
    cohort = us_sector_cohort()
    sectors = []
    values = {ticker: (2.0 + i) if i < 8 else (-1.0 - (i - 8))
              for i, ticker in enumerate(cohort)}
    thin_ticker = cohort[-1]
    for ticker in cohort:
        if ticker == thin_ticker:
            now = {"thin_history": True, "rs_rows": 150}
        else:
            now = {"rs_21d": 1.0, "rs_63d": values[ticker], "rs_126d": 0.5,
                   "rs_above_trend": True, "thin_history": False}
        sectors.append({"ticker": ticker, "kind": "sector", "now": now})
    sectors.append({"ticker": "ZZZZ", "kind": "sector",
                    "now": {"rs_63d": 9.9, "thin_history": False}})
    payload = {"meta": {"asOf": ASOF, "benchmark": "SPY"}, "sectors": sectors}
    frozen = copy.deepcopy(payload)
    snap = sector_cohort_snapshot(payload)
    assert payload == frozen  # read-only over the owner payload
    assert snap["schema"] == "leadership_rotation_context.sector_cohort/v1"
    assert snap["cohort_id"] == US_SECTOR_COHORT_ID
    assert snap["session_end"] == ASOF and snap["benchmark"] == "SPY"
    assert snap["expected"] == list(cohort)
    assert snap["measured"] == sorted(cohort[:-1])
    assert snap["missing"] == [[thin_ticker, "thin_history"]]
    assert snap["outside_cohort"] == ["ZZZZ"]
    pb = snap["positive_breadth"]
    assert pb["k_over_n"] == pytest.approx(0.8) and pb["coverage"] == pytest.approx(10 / 11)
    assert snap["ranking"]["unranked"] == [thin_ticker]
    assert snap["zscores"]["state"] == "ok"
    assert snap["zscores"]["cohort_id"] == US_SECTOR_COHORT_ID
    assert len(snap["measurements"]) == 11  # every expected ticker found in the payload
    assert all(m["metric"] == "relative_wealth_pct" for m in snap["measurements"])


def test_adapters_total_over_none_payloads():
    # F1: every owner adapter is TOTAL over a None / non-mapping payload --
    # AttributeError is never a legal outcome (spec section 0).
    snap = sector_cohort_snapshot(None)
    assert snap["cohort_id"] == US_SECTOR_COHORT_ID
    assert snap["measured"] == []
    assert len(snap["missing"]) == 11
    assert all(reason == "missing_input" for _, reason in snap["missing"])
    assert snap["positive_breadth"]["coverage"] == pytest.approx(0.0)
    assert snap["positive_breadth"]["k_over_n"] == {
        "status": "unmeasured", "reason": "no_measured_members"
    }
    assert isinstance(breadth(0, 0, 11).k_over_n, Unmeasured)  # reused breadth marker
    assert breadth(0, 0, 11).k_over_n == Unmeasured("no_measured_members")
    assert snap["ranking"]["ranked"] == []
    assert snap["ranking"]["unranked"] == list(us_sector_cohort())
    assert snap["zscores"]["state"] == "insufficient_reference"
    assert snap["session_end"] is None and snap["benchmark"] is None
    assert sector_cohort_snapshot(42) == snap  # non-mapping payload reads as {}

    diag = diagnose_rotation_payload(None, cohort_id="c")
    assert diag["rows"] == []
    assert diag["asof"] is None
    assert diag["owner_fields_modified"] is False
    assert diagnose_rotation_payload([], cohort_id="c") == diag

    g = from_leadership_receipt(None, group_id="g", cohort_id="c")
    assert isinstance(g, GroupMeasurement)
    assert g.metric == "return_difference" and g.units == "fraction"
    assert g.window_sessions == 20
    assert g.value == Unmeasured("missing_input")
    assert g.session_end is None and g.benchmark is None
    assert g.expected_n is None and g.measured_n is None
    with pytest.raises(ValueError):  # the horizon programmer error still fires first
        from_leadership_receipt(None, group_id="g", cohort_id="c", horizon="rel_1d")

    assert from_sector_record(None) == Unmeasured("missing_input")
    assert from_sector_record(42) == Unmeasured("missing_input")
    assert from_sector_record({"now": {}}) == Unmeasured("missing_input")  # no ticker
    assert from_sector_record({"ticker": 5, "now": {}}) == Unmeasured("missing_input")
    no_now = from_sector_record({"ticker": "XLF"})  # "now" None/missing: typed unknown
    assert isinstance(no_now, GroupMeasurement)
    assert no_now.value == Unmeasured("missing_input")
    with pytest.raises(ValueError):
        from_sector_record(None, horizon="rs_5d")

    # F2: non-observation items are silently skipped, never raised over
    assert earliest_observable_coordinate(
        [{"coordinate": {"date": "2026-10-01"}}, None], before="2026-10-05"
    ) == Unmeasured("missing_input")
    assert earliest_observable_coordinate(None, before="2026-10-05") == (
        Unmeasured("missing_input")
    )


def test_sector_cohort_snapshot_breadth_and_ranking():
    sectors = [
        {"id": t.lower(), "ticker": t, "kind": "sector",
         "now": {"rs_63d": v, "thin_history": False}}
        for t, v in (("XLK", 3.4), ("XLE", -2.0), ("XLF", 0.0), ("XLV", 1.0),
                     ("XLI", 0.5), ("XLB", -0.3), ("XLP", -1.1), ("XLY", 2.2),
                     ("XLC", 0.7))
    ]
    sectors.append({"id": "xlu", "ticker": "XLU", "kind": "sector",
                    "now": {"thin_history": True}})
    sectors.append({"id": "smh", "ticker": "SMH", "kind": "sector",
                    "now": {"rs_63d": 9.9}})  # in payload, NOT in the cohort
    payload = {"meta": {"asOf": "2026-10-06", "benchmark": "SPY"}, "sectors": sectors}
    snap = sector_cohort_snapshot(payload)
    assert snap["cohort_id"] == "us_sectors_11"
    # breadth: 5 positives of 9 measured, over the expected 11
    pb = snap["positive_breadth"]
    assert pb["k_over_n"] == pytest.approx(5 / 9)
    assert pb["coverage"] == pytest.approx(9 / 11)
    assert pb["bounds"] == pytest.approx((5 / 11, 7 / 11))
    # ranking: a valid 0.0 (XLF) ranks above a negative (XLB); XLRE absent and
    # XLU thin never rank; SMH is outside the cohort and never enters
    assert snap["ranking"]["unranked"] == ["XLRE", "XLU"]
    assert (snap["ranking"]["ranked"].index("XLF")
            < snap["ranking"]["ranked"].index("XLB"))
    assert "SMH" not in snap["ranking"]["ranked"]
    assert snap["outside_cohort"] == ["SMH"]
    # z-scores bind the exact 9-member measured reference
    assert snap["zscores"]["n_reference"] == 9
    assert snap["zscores"]["cohort_id"] == "us_sectors_11"
    assert ["XLRE", "missing_input"] in snap["missing"]
    assert ["XLU", "thin_history"] in snap["missing"]


def test_a20_aux_aliases_do_not_add_observations():
    kw = dict(as_of=ASOF, vintage="v1", mode="reconstructed_price_history",
              recorded_at="2026-10-06T22:00:00Z")
    # (i) one pair, one observation
    base = _ratio_receipt()
    out = attribute_coordinate(_ratio_batch(base), **kw)
    assert len(out["observations"]) == 1
    # (ii) an identical AUX alias of the same pair adds NO observation
    alias = _ratio_receipt(pid="xlp_vs_xlk_alias")
    out_alias = attribute_coordinate(_ratio_batch(base, alias), **kw)
    assert len(out_alias["observations"]) == 1
    # (iii) a CONFLICTING observation under the alias id: the pair goes
    # unavailable entirely -- typed reason codes, never a silent pick
    conflict = _ratio_receipt(num_daily=0.005, pid="xlp_vs_xlk_alias")
    out_bad = attribute_coordinate(_ratio_batch(base, conflict), **kw)
    assert len(out_bad["observations"]) == 0
    assert "CONFLICTING_PAIR_OBSERVATIONS" in out_bad["context_reason_codes"]
    assert "PARTIAL_PAIR_COVERAGE" in out_bad["context_reason_codes"]


def test_module_imports_stdlib_only():
    import ast
    from pathlib import Path

    from engine import leadership_rotation_context as lrc

    allowed = {"__future__", "math", "numbers", "copy", "dataclasses", "datetime",
               "typing", "json", "collections", "itertools", "functools", "re"}
    source = Path(lrc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported, "module-level imports must be parseable"
    assert imported <= allowed, f"non-stdlib top-level imports: {sorted(imported - allowed)}"
    # owner modules are imported LAZILY inside adapters, never at top level
    for owner in ("engine", "sector_cycles", "rotation_events", "leadership_receipt",
                  "subsector_rotation", "numpy", "pandas"):
        assert owner not in imported
    # no I/O, no clock reads, no randomness, no subprocess anywhere in code:
    # scan the module source with DOCSTRINGS STRIPPED via ast (the module
    # docstring legitimately mentions datetime.now as a prohibition)
    stripped = ast.parse(source)
    for node in ast.walk(stripped):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    code_only = ast.unparse(stripped)
    for token in ("open(", "requests", "urlopen", "datetime.now(", "random",
                  "subprocess"):
        assert token not in code_only, f"forbidden token in module code: {token!r}"


def test_inputs_not_mutated():
    sector_payload = {
        "meta": {"asOf": ASOF, "benchmark": "SPY"},
        "sectors": [{"ticker": t, "kind": "sector",
                     "now": {"rs_63d": 1.0 + i, "thin_history": False}}
                    for i, t in enumerate(us_sector_cohort())],
    }
    receipt = {"schema": "mi.leadership_receipt.v1", "rel_5d": 0.001, "rel_20d": 0.02,
               "rel_60d": -0.01, "benchmark": {"label": "S&P 500"}, "as_of": ASOF,
               "sample": {"observed_n": 8, "configured_n": 10}}
    rotation_payload = {"asof": ASOF, "subsectors": [
        {"key": "semis", "perf": {"1M": 2.0, "3M": 5.0},
         "rs_ratio": 0.9, "rs_mom": 0.4, "quadrant": "leading"}]}
    ledger = {"status": "OK", "rows": [
        {"lifecycle_id": "L1", "observation_date": "2026-09-30",
         "recorded_at": "2026-10-01T00:00:00Z", "mode": "RECONSTRUCTED_REPLAY",
         "from_key": "xlp", "to_key": "xlk"}]}
    ratio_batch = _ratio_batch(_ratio_receipt())
    frozen = {
        "sector": copy.deepcopy(sector_payload),
        "receipt": copy.deepcopy(receipt),
        "rotation": copy.deepcopy(rotation_payload),
        "ledger": copy.deepcopy(ledger),
        "ratio": copy.deepcopy(ratio_batch),
    }
    sector_cohort_snapshot(sector_payload)
    from_leadership_receipt(receipt, group_id="g", cohort_id="c")
    diagnose_rotation_payload(rotation_payload, cohort_id="c")
    attrib = attribute_coordinate(ratio_batch, as_of=ASOF,
                                  mode="reconstructed_price_history")
    separate_from_legacy(attrib["observations"], ledger)
    earliest_observable_coordinate(attrib["observations"], before="2026-10-07")
    assert sector_payload == frozen["sector"]
    assert receipt == frozen["receipt"]
    assert rotation_payload == frozen["rotation"]
    assert ledger == frozen["ledger"]
    assert ratio_batch == frozen["ratio"]
    # the pure projection functions read their mapping inputs too, never mutate
    pure = {
        "breadth_change": ({"a": True, "b": False, "c": None}, {"a": False, "b": True}),
        "cohort_zscores": ({"a": 1.0, "b": 2.0, "c": None},),
        "overlap": ({"a": 0.6, "b": 0.4}, {"a": 0.5, "c": 0.5}),
        "concentration": ({"a": 0.5, "b": 0.5},),
        "weight_coverage": ({"a": 0.6, "b": 0.4}, ["a"]),
        "dedupe_source_roots": ([{"id": "g", "source_roots": ["r"]},
                                 {"id": "h", "source_roots": ["r"]}],),
        "rank_measured": ({"a": 1.0, "b": None, "c": 0.0},),
    }
    pure_frozen = {name: copy.deepcopy(args) for name, args in pure.items()}
    breadth_change(*pure["breadth_change"])
    cohort_zscores(*pure["cohort_zscores"], cohort_id="c")
    overlap(*pure["overlap"])
    concentration(*pure["concentration"])
    weight_coverage(*pure["weight_coverage"])
    dedupe_source_roots(*pure["dedupe_source_roots"])
    rank_measured(*pure["rank_measured"])
    zc_before = {"a": 1.0, "b": 2.0}
    zc_after = {"a": 1.0, "b": 2.0, "d": -6.0}
    zc_before_frozen = copy.deepcopy(zc_before)
    zc_after_frozen = copy.deepcopy(zc_after)
    decompose_z_change("b", zc_before, zc_after,
                       cohort_id_before="c", cohort_id_after="c")
    assert zc_before == zc_before_frozen and zc_after == zc_after_frozen
    for name, args in pure.items():
        assert args == pure_frozen[name], f"{name} mutated its input"


# ---------------------------------------------------------------------------
# SYNTHETIC_FALSIFIERS -- the ten programme controls, each run THROUGH this
# module's functions (a failure names its control via the parametrize id)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("control", [
    "both_down", "breadth_missingness", "empty_is_unknown", "composition_only",
    "shared_holdings", "rolling_carry", "beta_only", "relative_units",
    "confirmation_maturity", "zero_vs_missing",
])
def test_sf_synthetic_falsifiers_ten_controls(control):
    if control == "both_down":
        # both legs down does NOT mean the receiver recovered: wealth ratio up
        res = pair_interpretation(-0.02, -0.08)
        assert res["relative_wealth"] > 0
        assert res["interpretation"] == "relative_resilience"
        assert "absolute_recovery" in res["not_claimed"]
        assert "measured_inflow" in res["not_claimed"]
    elif control == "breadth_missingness":
        # half-measured breadth carries identification bounds, never a CI
        b = breadth(1, 1, 2)
        assert b.k_over_n == pytest.approx(1.0)
        assert b.coverage == pytest.approx(0.5)
        assert b.bounds == pytest.approx((0.5, 1.0))
        assert b.to_dict()["bounds_kind"] == (
            "identification_bounds_not_confidence_interval"
        )
    elif control == "empty_is_unknown":
        empty = breadth(0, 0, 0)
        assert empty.k_over_n == Unmeasured("empty_population")
        assert empty.coverage == Unmeasured("empty_population")
        assert empty.bounds == Unmeasured("empty_population")
        assert cohort_zscores({}, cohort_id="t")["state"] == "insufficient_reference"
        assert isinstance(normalize_weights({}), Unmeasured)
    elif control == "composition_only":
        # the A12 fixture: list shrinkage that lifts k/n is composition, not breadth
        before = {f"m{i}": i < 2 for i in range(10)}
        after = {"m0": True, "m1": True}
        res = breadth_change(before, after)
        assert res["whole_list_before"].k_over_n == pytest.approx(0.2)
        assert res["whole_list_after"].k_over_n == pytest.approx(1.0)
        assert res["newly_positive_common"] == []
        assert res["composition_only"] is True
    elif control == "shared_holdings":
        # 90% shared weight is 0.9 overlap; shared source roots are ONE vote
        g = {"S": 0.9, "x": 0.1}
        h = {"S": 0.9, "y": 0.1}
        assert overlap(g, h) == pytest.approx(0.9)
        res = dedupe_source_roots([
            {"id": "g", "source_roots": ["root:shared"]},
            {"id": "h", "source_roots": ["root:shared"]},
        ])
        assert res["family_count"] == 1
    elif control == "rolling_carry":
        # a trailing window stepped inside its own length carries old terms
        res = decompose_trailing_change([-0.1, 0.0, 0.0], [0.0])
        assert res["carry_only"] is True
        assert rolling_carry(3, 1)["shared_terms"] == 2
    elif control == "beta_only":
        # a stated beta can absorb the whole move; the excess is arithmetic only
        res = beta_only_residual(-0.02, -0.10, 0.2)
        assert res["beta_residual"] == pytest.approx(0.0, abs=EPS)
        assert res["arithmetic_excess"] == pytest.approx(0.08)
    elif control == "relative_units":
        # a difference is NOT a wealth relative: the two quantities differ
        rd = return_difference(0.10, 0.05)
        rw = relative_wealth(0.10, 0.05)
        assert rd == pytest.approx(0.05)
        assert rw == pytest.approx(1.0 / 21.0)
        assert rd != rw
    elif control == "confirmation_maturity":
        # maturity counts from the origin: t + c + H, not t + max(c, H)
        assert confirmation_maturity(0, 3, 20) == 23
    elif control == "zero_vs_missing":
        res = rank_measured({"z": 0.0, "n1": -1.0, "n2": -2.0, "m": None})
        assert res["ranked"] == ["z", "n1", "n2"]  # a valid 0.0 ranks above negatives
        assert res["unranked"] == ["m"]  # a missing value never ranks
    else:  # pragma: no cover - the parametrize list is closed
        raise AssertionError(f"unknown SYNTHETIC_FALSIFIERS control: {control}")


# ---------------------------------------------------------------------------
# public API and acceptance-matrix closure
# ---------------------------------------------------------------------------

PUBLIC_API = (  # the 51 exported names at the judged LR-MEAS-B2 head
    "SCHEMA",
    "DEFINITION_ID",
    "UNMEASURED",
    "EPS",
    "EVIDENCE_MODES",
    "GROUP_KINDS",
    "METRICS",
    "UNITS",
    "REASONS",
    "US_SECTOR_COHORT_ID",
    "Unmeasured",
    "is_measured",
    "Breadth",
    "CohortMismatch",
    "relative_wealth",
    "return_difference",
    "breadth",
    "breadth_change",
    "cohort_zscores",
    "z_for",
    "classify_coordinate",
    "rank_measured",
    "normalize_weights",
    "overlap",
    "concentration",
    "shared_members",
    "weight_coverage",
    "cohort_at",
    "parse_time",
    "admissible_as_known",
    "admit_use",
    "observation_clock",
    "confirmation_maturity",
    "clock_identities",
    "GroupMeasurement",
    "TransitionObservation",
    "ResearchEstimate",
    "us_sector_cohort",
    "from_sector_record",
    "sector_cohort_snapshot",
    "from_leadership_receipt",
    "diagnose_rotation_payload",
    "attribute_coordinate",
    "earliest_observable_coordinate",
    "separate_from_legacy",
    "rolling_carry",
    "decompose_trailing_change",
    "beta_only_residual",
    "pair_interpretation",
    "decompose_z_change",
    "dedupe_source_roots",
)

MATRIX_CASES = {
    # acceptance-matrix case id -> the test function that pins it
    "A05": "test_a05_unknown_use_withheld",
    "A06": "test_a06_revision_after_decision_not_admissible",
    "A07": "test_a07_evidence_and_live_clocks_distinct",
    "A08": "test_a08_late_joiner_not_in_old_cohort",
    "A09": "test_a09_partial_weights_not_renormalised",
    "A10": "test_a10_breadth_one_of_one_measured_of_two",
    "A11": "test_a11_all_unavailable_typed_and_zero_coverage",
    "A12": "test_a12_composition_only_breadth",
    "A13": "test_a13_unknown_to_positive_is_new_coverage",
    "A14": "test_a14_aliases_one_family",
    "A15": "test_a15_peer_change_names_reference_change",
    "A16": "test_a16_zero_vs_missing",
    "A17": "test_a17_all_at_origin_is_neutral_not_leading",
    "A18": "test_a18_both_down_is_relative_resilience",
    "A19": "test_a19_beta_only_residual_zero",
    "A20-aux": "test_a20_aux_aliases_do_not_add_observations",
    "A25-aux": "test_a25_reconstructed_label_kept",
    "A31": "test_a31_old_negative_expiry_is_carry_only",
    "A32": "test_a32_maturity_is_t_plus_c_plus_h",
    "SF-1": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-2": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-3": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-4": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-5": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-6": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-7": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-8": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-9": "test_sf_synthetic_falsifiers_ten_controls",
    "SF-10": "test_sf_synthetic_falsifiers_ten_controls",
    "CF-01": "test_cf01_return_difference_is_not_relative_wealth",
    "CF-02": "test_cf02_breadth_bounds_collapse_when_fully_covered",
    "CF-03": "test_cf03_overlap_self_is_one",
    "CF-04": "test_cf04_concentration_equal_weights_is_n",
    "CF-05": "test_cf05_zscore_refuses_mismatched_cohort",
    "CF-06": "test_cf06_reconstructed_coordinate_never_naturally_observed",
    "CF-07": "test_cf07_rolling_carry_flag_when_terms_shared",
    "CF-08": "test_cf08_unmeasured_never_ranks",
}


def test_public_api_is_exported():
    from engine import leadership_rotation_context as lrc

    constants = {"SCHEMA", "DEFINITION_ID", "UNMEASURED", "EPS", "EVIDENCE_MODES",
                 "GROUP_KINDS", "METRICS", "UNITS", "REASONS", "US_SECTOR_COHORT_ID"}
    assert len(PUBLIC_API) == 51
    for name in PUBLIC_API:
        assert name in lrc.__all__, f"{name} missing from __all__"
        value = getattr(lrc, name)
        if name in constants:
            continue  # a module constant, present and exported
        assert isinstance(value, type) or callable(value), name
    assert not any(name.startswith("_") for name in lrc.__all__)
    assert len(set(lrc.__all__)) == len(lrc.__all__)  # no duplicate exports


def test_matrix_cases_each_have_a_test():
    expected_keys = (
        [f"A{n:02d}" for n in range(5, 20)]          # A05..A19
        + ["A20-aux", "A25-aux", "A31", "A32"]
        + [f"SF-{n}" for n in range(1, 11)]           # SF-1..SF-10
        + [f"CF-{n:02d}" for n in range(1, 9)]        # CF-01..CF-08
    )
    assert len(expected_keys) == 37
    assert set(MATRIX_CASES) == set(expected_keys), (
        "MATRIX_CASES keys must equal the acceptance-matrix case set exactly"
    )
    for key in expected_keys:
        test_name = MATRIX_CASES[key]
        fn = globals().get(test_name)
        # a case with no pinning test is a FAIL, not a skip
        assert callable(fn), f"matrix case {key} has no pinning test {test_name}"
        assert fn.__name__.startswith("test_")


# ---------------------------------------------------------------------------
# LR-MEAS-R2 review fixes: totality of numeric functions + T08 reason letter
# (spec addendum LR-MEAS-SPEC-1-A-R2). R1: un-floatable ints never raise.
# R1b: finite-float overflow is Unmeasured("non_finite_input"), never inf.
# R2: an unmeasured INPUT to a T08/carry function is missing_input.
# ---------------------------------------------------------------------------


def _no_nonfinite(x):
    """Assert no bare non-finite float escapes as a value (Unmeasured skipped)."""
    if isinstance(x, Unmeasured):
        return
    if isinstance(x, dict):
        for value in x.values():
            _no_nonfinite(value)
    elif isinstance(x, (list, tuple)):
        for value in x:
            _no_nonfinite(value)
    elif isinstance(x, float):
        assert math.isfinite(x), f"non-finite float escaped as a value: {x}"


def test_r1_unfloatable_int_never_raises():
    big = 10 ** 400
    assert is_measured(big) is False
    assert relative_wealth(big, 0.05) == Unmeasured("non_finite_input")
    assert return_difference(big, 0.05) == Unmeasured("non_finite_input")
    assert normalize_weights({"a": big}) == Unmeasured("missing_input")
    assert isinstance(overlap({"a": big}, {"a": 1.0}), Unmeasured)
    assert isinstance(concentration({"a": big}), Unmeasured)
    zs = cohort_zscores({"a": big, "b": 1.0, "c": 2.0}, cohort_id="t")
    assert zs["state"] == "ok"
    assert zs["n_reference"] == 2
    assert zs["z"]["a"] == Unmeasured("missing_input")
    assert beta_only_residual(big, 0.1, 1.0) == Unmeasured("missing_input")
    assert pair_interpretation(big, 0.1) == Unmeasured("missing_input")
    assert decompose_trailing_change([big], [0.01]) == Unmeasured("missing_input")


def test_r1b_finite_overflow_is_unmeasured_never_inf():
    assert relative_wealth(1e308, -0.5) == Unmeasured("non_finite_input")
    assert return_difference(1e308, -1e308) == Unmeasured("non_finite_input")
    assert normalize_weights({"a": 1e308, "b": 1e308}) == Unmeasured("non_finite_input")
    assert concentration({"a": 1e308, "b": 1e308}) == Unmeasured("non_finite_input")
    assert overlap({"a": 1e308, "b": 1e308}, {"a": 1.0}) == Unmeasured("non_finite_input")
    coverage = weight_coverage({"a": 1e308, "b": 1e308}, ["a"])
    assert coverage["measured_weight_share"] == Unmeasured("non_finite_input")
    zs = cohort_zscores({"a": 1e308, "b": -1e308, "c": 0.0}, cohort_id="t")
    assert zs["state"] == "non_finite"
    assert zs["sd"] == Unmeasured("non_finite_input")
    assert zs["mean"] == pytest.approx(0.0)
    assert zs["n_reference"] == 3
    for value in zs["z"].values():
        assert value == Unmeasured("non_finite_input")
    zs2 = cohort_zscores({"a": 1e308, "b": 1e308, "m": None}, cohort_id="t")
    assert zs2["state"] == "non_finite"
    assert zs2["mean"] == Unmeasured("non_finite_input")
    assert zs2["z"]["m"] == Unmeasured("missing_input")
    d = decompose_z_change(
        "a", {"a": 1e308, "b": -1e308, "c": 0.0}, {"a": 1.0, "b": 2.0, "c": 3.0},
        cohort_id_before="t", cohort_id_after="t",
    )
    assert isinstance(d["raw_move_component"], Unmeasured)
    assert beta_only_residual(1e308, -1e308, 10.0) == Unmeasured("non_finite_input")
    assert decompose_trailing_change([1e308, 1e308], [0.0]) == Unmeasured("non_finite_input")
    _no_nonfinite(zs)
    _no_nonfinite(zs2)
    _no_nonfinite(d)
    _no_nonfinite(coverage)


def test_r2_t08_unmeasured_input_reason_is_missing_input():
    assert decompose_trailing_change([0.01, float("nan")], [0.01]) == Unmeasured("missing_input")
    assert decompose_trailing_change([0.01], [float("inf")]) == Unmeasured("missing_input")
    assert beta_only_residual(float("nan"), 0.1, 1.0) == Unmeasured("missing_input")
    assert beta_only_residual(0.1, 0.1, float("inf")) == Unmeasured("missing_input")
    assert pair_interpretation(float("nan"), 0.1) == Unmeasured("missing_input")
    # counter-pin: T05 comparables keep the section 3.1 reason letter unchanged
    assert relative_wealth(float("nan"), 0.1) == Unmeasured("non_finite_input")


# ---------------------------------------------------------------------------
# LR-FIX-A repairs (ORCH-CHAL #9240 R1/R2, acceptance case A26): set-based
# coverage and owner adapters that stay total over NESTED malformed payloads.
# ---------------------------------------------------------------------------

_GM_KW = dict(group_id="XLK", group_kind="sector", cohort_id=US_SECTOR_COHORT_ID,
              metric="relative_wealth_pct", units="pct")

_MEMBER_ALPHABET = ("A", "B", "C")


def _member_tuples(max_len: int = 3) -> list:
    """Every member tuple over the alphabet with length 0..max_len (sweep)."""
    level = [()]
    out = [()]
    for _ in range(max_len):
        level = [prefix + (member,) for prefix in level for member in _MEMBER_ALPHABET]
        out = out + level
    return out


def test_fix_a1_coverage_counts_distinct_expected_ids():
    # MUTATION: list-length coverage (len(measured_members) / len(expected_members))
    dupes = GroupMeasurement(**{**_GM_KW, "expected_members": ("A", "A"),
                                "measured_members": ("A", "A", "A")})
    assert dupes.coverage == pytest.approx(1.0)          # was 1.5 on list length
    assert dupes.unexpected_members == ()
    partial = GroupMeasurement(**{**_GM_KW, "expected_members": ("A", "A", "B"),
                                  "measured_members": ("A", "A")})
    assert partial.coverage == pytest.approx(0.5)        # |{A}| / |{A, B}|
    outside = GroupMeasurement(**{**_GM_KW, "expected_members": ("A", "B"),
                                  "measured_members": ("A", "Z")})
    assert outside.coverage == pytest.approx(0.5)        # an UNEXPECTED id never raises it
    assert outside.unexpected_members == ("Z",)
    over = GroupMeasurement(**{**_GM_KW, "expected_n": 2, "measured_n": 3})
    assert over.coverage == Unmeasured("invalid_counts")
    assert GroupMeasurement(**_GM_KW).unexpected_members == ()
    # to_dict() carries the set-based coverage AND the outside ids
    assert dupes.to_dict()["coverage"] == pytest.approx(1.0)
    assert dupes.to_dict()["unexpected_members"] == []
    assert outside.to_dict()["coverage"] == pytest.approx(0.5)
    assert outside.to_dict()["unexpected_members"] == ["Z"]
    assert over.to_dict()["coverage"] == {"status": "unmeasured", "reason": "invalid_counts"}
    json.dumps(outside.to_dict(), allow_nan=False)       # still JSON-safe


def test_fix_a1_coverage_bound_sweep():
    # MUTATION: unbounded ratio (a coverage value outside [0.0, 1.0])
    tuples = _member_tuples(3)
    assert len(tuples) == 40 and len(set(tuples)) == 40   # 1 + 3 + 9 + 27, no repeats
    for expected in tuples:
        for measured in tuples:
            cov = GroupMeasurement(**{**_GM_KW, "expected_members": expected,
                                      "measured_members": measured}).coverage
            if isinstance(cov, Unmeasured):
                assert expected == ()                  # only an empty expected set is unknown
                assert cov == Unmeasured("empty_population")
            else:
                assert isinstance(cov, float)
                assert 0.0 <= cov <= 1.0, f"coverage out of bounds: {expected} {measured} {cov}"
    for expected_n in range(0, 4):
        for measured_n in range(0, 5):
            cov = GroupMeasurement(**{**_GM_KW, "expected_n": expected_n,
                                      "measured_n": measured_n}).coverage
            assert not (isinstance(cov, float) and cov > 1.0), (
                f"count coverage exceeded 1: n={expected_n} k={measured_n} -> {cov!r}"
            )
            if expected_n >= 1 and measured_n > expected_n:
                assert cov == Unmeasured("invalid_counts")
            elif expected_n >= 1:
                assert isinstance(cov, float) and 0.0 <= cov <= 1.0
            else:
                assert cov == Unmeasured("empty_population")


def test_fix_a26_duplicate_members_count_once():
    # MUTATION: duplicate double count (a repeated measured id counted twice)
    gm = GroupMeasurement(**{**_GM_KW, "expected_members": ("A", "B"),
                             "measured_members": ("A", "A")})
    assert gm.coverage == pytest.approx(0.5)             # one distinct id of two expected
    assert gm.to_dict()["coverage"] == pytest.approx(0.5)
    assert gm.unexpected_members == ()                   # a duplicate is not an outside id
    assert gm.to_dict()["unexpected_members"] == []
    dup_expected = GroupMeasurement(**{**_GM_KW, "expected_members": ("A", "A", "B"),
                                       "measured_members": ("B", "B", "B")})
    assert dup_expected.coverage == pytest.approx(0.5)   # |{B}| / |{A, B}|


def test_fix_a2_adapters_total_on_nested_malformed_payloads():
    # MUTATION: `x.get(k) or {}` on a truthy non-mapping (AttributeError, not a total adapter)
    hostile_snapshots = (
        ({"sectors": [None]}, 1, False),
        ({"sectors": {"XLK": {}}}, 0, True),             # a dict is never iterated by key
        ({"sectors": ["XLK"]}, 1, False),
        ({"sectors": 42}, 0, True),
        ({"meta": "x", "sectors": [{"ticker": "XLK", "now": "x"}]}, 0, False),
        ({"sectors": [None, {"ticker": "XLK", "now": {}}]}, 1, False),
    )
    for payload, rows, container in hostile_snapshots:
        frozen = copy.deepcopy(payload)
        snap = sector_cohort_snapshot(payload)
        assert payload == frozen                         # read-only over a hostile payload
        assert snap["malformed_rows"] == rows, payload
        assert snap["malformed_container"] is container, payload
        assert snap["cohort_id"] == US_SECTOR_COHORT_ID
        assert len(snap["expected"]) == 11
        assert len(snap["missing"]) == 11 - len(snap["measured"])
        assert all(m["metric"] == "relative_wealth_pct" for m in snap["measurements"])
        assert snap["ranking"]["ranked"] == []           # nothing hostile ever ranks
    # a clean / None / non-mapping payload carries no flags (base equality holds)
    assert sector_cohort_snapshot(None)["malformed_rows"] == 0
    assert sector_cohort_snapshot(None)["malformed_container"] is False
    assert sector_cohort_snapshot(42) == sector_cohort_snapshot(None)
    clean = {"meta": {"asOf": ASOF, "benchmark": "SPY"},
             "sectors": [{"ticker": "XLK", "now": {"rs_63d": 1.0, "thin_history": False}}]}
    assert sector_cohort_snapshot(clean)["malformed_rows"] == 0
    assert sector_cohort_snapshot(clean)["malformed_container"] is False

    for rec in ({"ticker": "XLK", "now": "x"}, {"ticker": "XLK", "now": [1]}):
        frozen = copy.deepcopy(rec)
        gm = from_sector_record(rec)
        assert rec == frozen
        assert isinstance(gm, GroupMeasurement)
        assert gm.value == Unmeasured("missing_input")   # typed unknown, never a crash
        assert gm.price_basis == "total_return"          # the declared literal stays

    for receipt in ({"benchmark": "x", "sample": [1]}, {"benchmark": 1, "sample": "s"}):
        frozen = copy.deepcopy(receipt)
        g = from_leadership_receipt(receipt, group_id="g", cohort_id="c")
        assert receipt == frozen
        assert isinstance(g, GroupMeasurement)
        assert g.value == Unmeasured("missing_input")
        assert g.benchmark is None
        assert g.expected_n is None and g.measured_n is None

    rows_payload = {"asof": ASOF, "subsectors": [None, "x", {"perf": "x"}]}
    frozen = copy.deepcopy(rows_payload)
    diag = diagnose_rotation_payload(rows_payload, cohort_id="c")
    assert rows_payload == frozen
    assert diag["malformed_rows"] == 2                   # None and "x" are not rows
    assert diag["malformed_container"] is False
    assert len(diag["rows"]) == 1                        # the mapping row still projects
    assert diag["rows"][0]["flags"] == ["missing_coerced_to_zero"]
    assert diag["owner_fields_modified"] is False
    keyed = diagnose_rotation_payload({"subsectors": {"a": 1}}, cohort_id="c")
    assert keyed["malformed_container"] is True
    assert keyed["rows"] == [] and keyed["malformed_rows"] == 0
    assert diagnose_rotation_payload(None, cohort_id="c")["malformed_rows"] == 0
    assert diagnose_rotation_payload(None, cohort_id="c")["malformed_container"] is False
