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

from engine.sector_dated_context import (
    ATTRIBUTION_KEYS as PSL_CTX_ATTRIBUTION_KEYS,
    AUTHORITY_FLAGS as PSL_CTX_AUTHORITY_FLAGS,
    COMPARISON_IDS as PSL_CTX_COMPARISON_IDS,
    ENTRY_STATUSES as PSL_CTX_ENTRY_STATUSES,
    LIMITS as PSL_CTX_LIMITS,
    REASONS as PSL_CTX_REASONS,
    SCHEMA as PSL_CTX_SCHEMA,
    SCOPE as PSL_CTX_SCOPE,
    SECTION_STATUSES as PSL_CTX_SECTION_STATUSES,
    STATUSES as PSL_CTX_STATUSES,
    project_dated_context,
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


# ---------------------------------------------------------------------------
# PSL-DATED-CTX-1 -- the dated configured-theme context projection
# (engine/sector_dated_context.py).
#
# The first test below is the exact byte/hash check of the three published
# raw sources, read from the IMMUTABLE pinned commit object (never from the
# working tree, so a later data refresh cannot make the check lie).  Every
# reduced selected-field fixture after it is copied from those pinned bytes.
# The reduced dictionaries are fixtures; the full hashes identify the
# original files, not the reduced dictionaries.
# ---------------------------------------------------------------------------

PSL_CTX_BASE = "5f28e82be560a6ecb73832023e2823b677164747"

PSL_CTX_PUBLISHED_SOURCES = {
    "data/regime/latest.json": {
        "bytes": 992189,
        "raw_sha256": "1ec062ec0805727adb900c86a52de4c17612c4ee80ddad36a67e9405f2000f8a",
        "git_blob": "c69ddeef96ffe839bf2fd05e5ee173a3fcee731e",
    },
    "config.yml": {
        "bytes": 496073,
        "raw_sha256": "701229b33bbd6260c561023e2c2611a8fca24bc2c97e784cf97d55aa0357b402",
        "git_blob": "5be75249c98033d7ee0fbe55928713b1f50af627",
    },
    "site/riskdata/risk_envelope.json": {
        "bytes": 81982,
        "raw_sha256": "93f5b3da1dca0e6e464ef42c44cde22369ff2b2b57c521594374cc00f5ac804a",
        "git_blob": "e80df06802f6fb46cfd6db9e9a6a347986a8dd28",
    },
}

PSL_CTX_RAW_PREFIX = (
    "https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/"
    + PSL_CTX_BASE + "/"
)


def _psl_ctx_regime():
    """Reduced selected-field fixture of the pinned regime snapshot."""
    return {
        "asof": "2026-11-06",
        "freshness": {
            "asof": "2026-11-06",
            "built_at": "2026-11-07T00:11:01Z",
            "age_days": 1,
            "age_sessions": 0,
            "max_age_sessions": 1,
            "stale": False,
        },
        "theme_revisions": {
            "asof": "2026-11-06",
            "n_themes": 18,
            "weights": {
                "breadth": "mean member net-up share [-1,1]",
                "est_drift_90d": "median member 90d consensus-EPS drift %",
                "breadth_accel": (
                    "theme breadth now - breadth ~prior_snapshot ago "
                    "(PIT, the broadening gauge)"),
                "breadth_cov": (
                    "W2a coverage-normalised breadth: mean of (up-dn)/n_covering "
                    "over members with n_covering>=MIN_COVERING; None when fewer "
                    "than MIN_MEMBERS_COV members have coverage data"),
            },
            "themes": {
                "memory_storage": {
                    "name": "Memory, HBM & Storage",
                    "breadth": 0.746,
                    "level_state": "POSITIVE",
                    "est_drift_90d": 21.89,
                    "net_up_total": 24.0,
                    "breadth_accel": -0.204,
                    "broadening_state": "ROLLING",
                    "coverage": 0.6,
                    "n_covered": 3,
                    "n_members": 5,
                    "members": [
                        {"ticker": "WDC", "breadth": 0.33, "n_analysts": 3,
                         "est_chg_90d": 21.9, "n_covering": 22,
                         "breadth_cov": 0.0455},
                        {"ticker": "MU", "breadth": 0.91, "n_analysts": 21,
                         "est_chg_90d": 24.5, "n_covering": 36,
                         "breadth_cov": 0.5278},
                        {"ticker": "NTAP", "breadth": 1.0, "n_analysts": 4,
                         "est_chg_90d": 13.6, "n_covering": 20,
                         "breadth_cov": 0.2},
                    ],
                    "breadth_cov": 0.2269,
                    "basis_days": 22,
                },
            },
        },
        "bottleneck": {
            "asof": "2026-09-01",
            "n_themes": 18,
            "themes": {
                "memory_storage": {
                    "name": "Memory, HBM & Storage",
                    "naics": "3344",
                    "band": "NEUTRAL",
                    "tightness": 0.11,
                    "regime": False,
                    "n_legs": 6,
                    "numeric_composite": 0.0,
                    "numeric_band": "NEUTRAL",
                    "cap_u_latest": 76.51,
                    "ppi_yoy_latest": -2.2,
                    "language_accel": 0.5,
                    "language_hits": 3,
                    "language_n_filers": 2,
                    "leg6_detail": {"value": 0.5, "accel": 0.5, "hits": 3,
                                    "n_filers": 2, "provisional": True},
                    "text_only": False,
                    "fingerprint": {
                        "theme": "memory_storage",
                        "fingerprint_tightness": -0.091,
                        "leg7_member_inventory": -0.091,
                        "leg8_member_backlog": None,
                        "n_legs_live": 1,
                        "basis": "annual",
                        "provisional": True,
                        "components": {
                            "leg7_member_inventory": {
                                "value": -0.091, "n_reporting": 5,
                                "latest_fy": 2027, "min_required": 3,
                                "met_gate": True},
                            "leg8_member_backlog": {
                                "value": None, "n_reporting": 2,
                                "latest_fy": 2022, "min_required": 3,
                                "met_gate": False},
                        },
                    },
                },
            },
        },
    }


def _psl_ctx_config():
    """Reduced selected-field fixture of the decoded site configuration."""
    return {
        "themes": {
            "memory_storage": {
                "name": "Memory, HBM & Storage",
                "tickers": ["MU", "WDC", "SNDK", "STX", "NTAP"],
            },
        },
    }


def _psl_ctx_public_risk():
    """Reduced selected-field fixture of the published public risk envelope."""
    return {
        "schema": "mastermind.risk_envelope/v1",
        "definition_id": "grey-deer-v1-2026-08-19",
        "market": "US",
        "bundle_id": "fbf32d0f9123bafd",
        "source_session": "2026-11-06",
        "as_of": "2026-11-06",
        "observed_at": "2026-11-07T04:12:49Z",
        "produced_at": "2026-11-07T04:12:49Z",
        "revision": "settled",
        "data_state": "DEGRADED",
        "stale_after": None,
        "measured_state": {
            "as_of": "2026-11-06", "role": "slow_confirmed_trend", "score": 40,
            "source_artifact": "market-state-latest", "usable": True,
            "verdict": "RISK_OFF",
        },
        "hazard_summary": {
            "active_episode_count": 0, "capped_sources": [],
            "contributing_sources": ["risk-radar-us"], "display_only": True,
            "primary_episode_id": None, "stage": None,
            "stage_reason": "required_coverage_unavailable", "stage_since": None,
            "stage_since_basis": "no_episode_lifecycle_in_v0",
            "unmapped_required_sources": [],
            "unreadable_sources": ["leadership-crack-latest"],
        },
        "freshness": {
            "all_on_session": False,
            "off_session_sources": ["leadership-crack-latest",
                                    "site-marketdata-rotation-events"],
            "per_source": {
                "leadership-crack-latest": {"as_of": "2026-11-05",
                                            "matches_session": False,
                                            "state": "STALE"},
                "market-state-latest": {"as_of": "2026-11-06",
                                        "matches_session": True,
                                        "state": "FRESH"},
                "risk-radar-us": {"as_of": "2026-11-06", "matches_session": True,
                                  "state": "FRESH"},
                "site-marketdata-rotation-events": {"as_of": "2026-11-05",
                                                    "matches_session": False,
                                                    "state": "STALE"},
            },
            "source_session": "2026-11-06",
        },
        "coherence": {
            "compares": ["measured_state", "hazard_evidence"],
            "contradiction_count": 0, "contradictions": [], "display_only": True,
            "excludes": ["policy_summary"], "scope": "market_reads",
            "state": "MIXED",
        },
        "policy_summary": {
            "active_policy_ids": [], "basis": "zero_active_policies",
            "display_only": True, "policy_count": 0, "posture": "NORMAL",
        },
        "authority": {
            "envelope_may_execute": False, "envelope_may_gate": False,
            "envelope_may_rank": False, "envelope_may_size": False,
            "policy_actions_require_individual_authority": True,
        },
        "policies": [],
    }


def _psl_ctx_attribution():
    """The caller-supplied attribution for the three pinned published files."""
    return {
        "regime_document": {
            "source_ref": PSL_CTX_RAW_PREFIX + "data/regime/latest.json",
            "raw_sha256": PSL_CTX_PUBLISHED_SOURCES[
                "data/regime/latest.json"]["raw_sha256"],
        },
        "config_document": {
            "source_ref": PSL_CTX_RAW_PREFIX + "config.yml",
            "raw_sha256": PSL_CTX_PUBLISHED_SOURCES["config.yml"]["raw_sha256"],
        },
        "public_risk_document": {
            "source_ref": PSL_CTX_RAW_PREFIX + "site/riskdata/risk_envelope.json",
            "raw_sha256": PSL_CTX_PUBLISHED_SOURCES[
                "site/riskdata/risk_envelope.json"]["raw_sha256"],
        },
    }


def _psl_ctx_project(**overrides):
    payload = {
        "theme_key": "memory_storage",
        "regime_document": _psl_ctx_regime(),
        "config_document": _psl_ctx_config(),
        "public_risk_document": _psl_ctx_public_risk(),
        "source_attribution": _psl_ctx_attribution(),
    }
    payload.update(overrides)
    return project_dated_context(**payload)


def _psl_ctx_entries(out):
    return {entry["id"]: entry for entry in out["comparison"]["entries"]}


def test_psl_ctx_pinned_source_identities_are_the_commissioned_ones():
    """The pinned source identities are pinned as a contract, with no I/O.

    This always runs. It pins the three published identities that the
    reduced fixtures were copied from, so a change to any of them is a
    deliberate edit rather than a silent drift, and it pins the rule that the
    projection carries them as caller-supplied attribution and never claims
    to have verified them.
    """
    assert sorted(PSL_CTX_PUBLISHED_SOURCES) == [
        "config.yml",
        "data/regime/latest.json",
        "site/riskdata/risk_envelope.json",
    ]
    for path, expected in PSL_CTX_PUBLISHED_SOURCES.items():
        assert expected["bytes"] > 0, path
        assert len(expected["raw_sha256"]) == 64, path
        assert expected["raw_sha256"] == expected["raw_sha256"].lower(), path
        assert all(character in "0123456789abcdef"
                   for character in expected["raw_sha256"]), path
        assert len(expected["git_blob"]) == 40, path

    out = _psl_ctx_project()
    carried = out["provenance"]["source_attribution"]
    assert carried["regime_document"]["raw_sha256"] == \
        PSL_CTX_PUBLISHED_SOURCES["data/regime/latest.json"]["raw_sha256"]
    assert carried["config_document"]["raw_sha256"] == \
        PSL_CTX_PUBLISHED_SOURCES["config.yml"]["raw_sha256"]
    assert carried["public_risk_document"]["raw_sha256"] == \
        PSL_CTX_PUBLISHED_SOURCES["site/riskdata/risk_envelope.json"][
            "raw_sha256"]
    assert out["provenance"]["attribution_verification"] == \
        "not_established_by_projection"
    assert out["limitations"]["attribution_verification"] == \
        "not_established_by_projection"


def test_psl_ctx_published_sources_match_the_pinned_bytes():
    """Exact byte-length and SHA256 check of the three published raw sources.

    The bytes come from the repository's own object store: the immutable
    pinned commit object first, and otherwise the checkout's own HEAD blob
    when it is byte-identical to the pinned blob. The working tree is never
    read, so a nightly refresh of data/ or site/ cannot make this check lie.

    A checkout that does not carry those bytes at all cannot prove them; the
    durable proof then lives with the lane evidence, and this test reports
    that fact instead of passing silently.
    """
    import hashlib
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(root)] + list(args),
            capture_output=True, check=True, timeout=120).stdout

    for path, expected in PSL_CTX_PUBLISHED_SOURCES.items():
        blob = None
        try:
            blob = git("cat-file", "blob", "{0}:{1}".format(PSL_CTX_BASE, path))
        except (OSError, subprocess.SubprocessError):
            try:
                head_blob = git("rev-parse", "HEAD:{0}".format(path)).decode()
                if head_blob.strip() == expected["git_blob"]:
                    blob = git("cat-file", "blob", head_blob.strip())
            except (OSError, subprocess.SubprocessError):
                blob = None
        if blob is None:
            pytest.skip(
                "this checkout does not carry the pinned bytes for {0}; the "
                "byte/hash proof is in the lane evidence".format(path))
        assert len(blob) == expected["bytes"], path
        assert hashlib.sha256(blob).hexdigest() == expected["raw_sha256"], path


def test_psl_ctx_primary_case_projects_the_dated_reading():
    out = _psl_ctx_project()
    assert out["schema"] == PSL_CTX_SCHEMA == "sector_dated_context/v1"
    assert out["scope"] == PSL_CTX_SCOPE
    assert out["scope"] == "configured_theme_example_with_market_global_risk"
    assert out["status"] == "dated_context"
    assert out["status"] in PSL_CTX_STATUSES

    # -- the configured theme roster, not a sector or ETF membership --------
    theme = out["theme"]
    assert theme["status"] == "available"
    assert theme["theme_key"] == "memory_storage"
    assert theme["name"] == "Memory, HBM & Storage"
    assert theme["roster"] == ["MU", "WDC", "SNDK", "STX", "NTAP"]
    assert theme["roster_size"] == 5
    assert theme["membership_basis"] == "configured_theme_roster"

    # -- the dated revision reading, with its native units -----------------
    obs = out["observations"]
    assert obs["status"] == "available"
    assert obs["reasons"] == []
    rev = obs["revision_state"]
    assert rev["asof"] == "2026-11-06"
    assert rev["level_state"] == "POSITIVE"
    assert rev["breadth"] == 0.746
    assert rev["est_drift_90d"] == 21.89
    assert rev["net_up_total"] == 24.0
    assert rev["breadth_accel"] == -0.204
    assert rev["broadening_state"] == "ROLLING"
    assert rev["coverage"] == 0.6
    assert rev["n_covered"] == 3
    assert rev["n_members"] == 5
    assert rev["breadth_cov"] == 0.2269
    assert rev["breadth_accel_basis_days"] == 22
    assert obs["units"]["breadth"] == "mean member net-up share [-1,1]"
    assert obs["units"]["est_drift_90d"] == "median member 90d consensus-EPS drift %"
    assert "(PIT, the broadening gauge)" in obs["units"]["breadth_accel"]

    # -- covered contributors, with their own numbers ---------------------
    contributors = {row["ticker"]: row for row in obs["contributors"]}
    assert sorted(contributors) == ["MU", "NTAP", "WDC"]
    assert contributors["WDC"]["breadth"] == 0.33
    assert contributors["WDC"]["n_analysts"] == 3
    assert contributors["WDC"]["est_chg_90d"] == 21.9
    assert contributors["WDC"]["n_covering"] == 22
    assert contributors["WDC"]["breadth_cov"] == 0.0455
    assert contributors["MU"]["breadth"] == 0.91
    assert contributors["MU"]["n_analysts"] == 21
    assert contributors["MU"]["est_chg_90d"] == 24.5
    assert contributors["MU"]["n_covering"] == 36
    assert contributors["MU"]["breadth_cov"] == 0.5278
    assert contributors["NTAP"]["breadth"] == 1.0
    assert contributors["NTAP"]["n_analysts"] == 4
    assert contributors["NTAP"]["est_chg_90d"] == 13.6
    assert contributors["NTAP"]["n_covering"] == 20
    assert contributors["NTAP"]["breadth_cov"] == 0.2

    # -- every owner clock stays separate ---------------------------------
    clocks = obs["clocks"]
    assert clocks["regime_asof"] == "2026-11-06"
    assert clocks["regime_built_at"] == "2026-11-07T00:11:01Z"
    assert clocks["theme_revisions_asof"] == "2026-11-06"
    assert clocks["bottleneck_asof"] == "2026-09-01"
    assert clocks["bottleneck_asof"] != clocks["theme_revisions_asof"]
    assert clocks["regime_freshness"]["age_days"] == 1
    assert clocks["regime_freshness"]["age_sessions"] == 0
    assert clocks["regime_freshness"]["max_age_sessions"] == 1
    assert clocks["regime_freshness"]["stale"] is False

    # -- the older neutral bottleneck, with its zero and its null ----------
    bottleneck = obs["bottleneck"]
    assert bottleneck["asof"] == "2026-09-01"
    assert bottleneck["band"] == "NEUTRAL"
    assert bottleneck["numeric_band"] == "NEUTRAL"
    assert bottleneck["tightness"] == 0.11
    assert bottleneck["numeric_composite"] == 0.0
    assert bottleneck["n_legs"] == 6
    assert bottleneck["regime"] is False
    assert bottleneck["text_only"] is False
    assert bottleneck["naics"] == "3344"
    assert bottleneck["cap_u_latest"] == 76.51
    assert bottleneck["ppi_yoy_latest"] == -2.2
    assert bottleneck["language_hits"] == 3
    assert bottleneck["language_n_filers"] == 2
    assert bottleneck["leg6_detail"]["provisional"] is True
    fingerprint = bottleneck["fingerprint"]
    assert fingerprint["leg8_member_backlog"] is None
    assert fingerprint["leg7_member_inventory"] == -0.091
    assert fingerprint["n_legs_live"] == 1
    assert fingerprint["basis"] == "annual"
    assert fingerprint["provisional"] is True
    assert fingerprint["components"]["leg8_member_backlog"]["value"] is None
    assert fingerprint["components"]["leg8_member_backlog"]["latest_fy"] == 2022
    assert fingerprint["components"]["leg8_member_backlog"]["met_gate"] is False

    # -- market-global risk, separate from the sector reading -------------
    risk = out["market_risk"]
    assert risk["status"] == "available"
    assert risk["scope"] == "market_global"
    assert risk["data_state"] == "DEGRADED"
    assert risk["stale_after"] is None
    assert risk["source_session"] == "2026-11-06"
    assert risk["as_of"] == "2026-11-06"
    assert risk["observed_at"] == "2026-11-07T04:12:49Z"
    assert risk["produced_at"] == "2026-11-07T04:12:49Z"
    assert risk["revision"] == "settled"
    assert risk["definition_id"] == "grey-deer-v1-2026-08-19"
    assert risk["bundle_id"] == "fbf32d0f9123bafd"
    assert risk["measured_state"]["verdict"] == "RISK_OFF"
    assert risk["measured_state"]["score"] == 40
    assert risk["measured_state"]["usable"] is True
    assert risk["hazard_summary"]["stage"] is None
    assert risk["hazard_summary"]["stage_reason"] == "required_coverage_unavailable"
    assert risk["hazard_summary"]["unreadable_sources"] == ["leadership-crack-latest"]
    assert risk["coherence"]["state"] == "MIXED"
    assert risk["coherence"]["contradiction_count"] == 0
    assert risk["coherence"]["contradictions"] == []
    assert risk["coherence"]["scope"] == "market_reads"
    assert risk["policy_summary"]["posture"] == "NORMAL"
    assert risk["policy_summary"]["basis"] == "zero_active_policies"
    assert risk["policy_summary"]["policy_count"] == 0
    assert risk["policy_summary"]["active_policy_ids"] == []
    assert risk["source_authority"]["envelope_may_execute"] is False
    assert risk["source_authority"]["envelope_may_gate"] is False
    assert risk["source_authority"]["envelope_may_rank"] is False
    assert risk["source_authority"]["envelope_may_size"] is False
    assert risk["source_authority"][
        "policy_actions_require_individual_authority"] is True

    # -- the four per-source freshness clocks stay separate ----------------
    per_source = risk["freshness"]["per_source"]
    assert risk["freshness"]["all_on_session"] is False
    assert sorted(per_source) == [
        "leadership-crack-latest", "market-state-latest", "risk-radar-us",
        "site-marketdata-rotation-events",
    ]
    assert per_source["leadership-crack-latest"] == {
        "as_of": "2026-11-05", "matches_session": False, "state": "STALE"}
    assert per_source["market-state-latest"] == {
        "as_of": "2026-11-06", "matches_session": True, "state": "FRESH"}
    assert per_source["risk-radar-us"] == {
        "as_of": "2026-11-06", "matches_session": True, "state": "FRESH"}
    assert per_source["site-marketdata-rotation-events"] == {
        "as_of": "2026-11-05", "matches_session": False, "state": "STALE"}


def test_psl_ctx_limitations_and_authority_are_fixed_always():
    fixed_limitations = {
        "current_sector_usable": False,
        "historically_admissible": False,
        "sector_mapping": {"status": "unavailable",
                           "reason": "native_sector_mapping_not_supplied"},
        "original_available_at": None,
        "availability_reason":
            "native_availability_and_revision_selection_not_supplied",
        "attribution_verification": "not_established_by_projection",
    }
    fixed_authority = {"may_rank": False, "may_gate": False, "may_size": False,
                       "may_trade": False, "may_escalate": False}
    assert sorted(fixed_authority) == sorted(PSL_CTX_AUTHORITY_FLAGS)

    results = [
        _psl_ctx_project(),
        _psl_ctx_project(decision_cutoff="2026-11-06T21:00:00Z"),
        _psl_ctx_project(decision_cutoff="not-a-cutoff"),
        _psl_ctx_project(theme_key="no_such_theme"),
        _psl_ctx_project(regime_document=None),
    ]
    for out in results:
        assert out["limitations"] == fixed_limitations
        assert out["authority"] == fixed_authority
        assert out["schema"] == PSL_CTX_SCHEMA
        assert out["scope"] == PSL_CTX_SCOPE
        assert out["status"] in PSL_CTX_STATUSES
        for section in ("theme", "observations", "comparison", "market_risk",
                       "provenance"):
            assert out[section]["status"] in PSL_CTX_SECTION_STATUSES


def test_psl_ctx_historical_mode_withholds_every_contextual_value():
    out = _psl_ctx_project(decision_cutoff="2026-11-06T21:00:00Z")
    assert out["status"] == "partial"
    assert out["observations"]["status"] == "withheld"
    assert out["observations"]["reasons"] == [
        "historical_availability_unqualified"]
    assert out["market_risk"]["status"] == "withheld"
    assert out["market_risk"]["reasons"] == [
        "historical_availability_unqualified"]
    assert out["comparison"]["status"] == "withheld"
    assert out["comparison"]["reasons"] == [
        "historical_availability_unqualified"]

    # no contextual VALUE survives the historical claim. The owner clocks are
    # kept, because they identify which snapshot would have been projected
    # and they are not a positive claim; the limitation refuses their
    # historical admissibility.
    blob = json.dumps(out, ensure_ascii=False, sort_keys=True)
    for token in ("POSITIVE", "NEUTRAL", "RISK_OFF", "ROLLING", "0.746",
                  "21.89", "-0.204", "0.2269", "0.11"):
        assert token not in blob, token
    assert "revision_state" not in out["observations"]
    assert "bottleneck" not in out["observations"]
    assert "measured_state" not in out["market_risk"]
    clocks = out["observations"]["clocks"]
    assert clocks["bottleneck_asof"] == "2026-09-01"
    assert clocks["theme_revisions_asof"] == "2026-11-06"
    assert clocks["regime_asof"] == "2026-11-06"

    # every alternative is unresolved and names the historical reason
    entries = _psl_ctx_entries(out)
    assert sorted(entries) == sorted(PSL_CTX_COMPARISON_IDS)
    for entry in entries.values():
        assert entry["status"] == "unresolved"
        assert "historical_availability_unqualified" in entry["reasons"]
        assert entry["evidence_refs"] == []
        assert entry["falsifier"]["met"] is False
        assert entry["statement"]

    # the fixed limitations still refuse historical admissibility
    assert out["limitations"]["historically_admissible"] is False
    assert out["limitations"]["original_available_at"] is None


def test_psl_ctx_invalid_decision_cutoff_fails_closed():
    for bad in ("2026-11-06", "2026-11-06T00:00:00", "not-a-date", "", 42,
                None.__class__, True):
        out = _psl_ctx_project(decision_cutoff=bad)
        assert out["status"] == "unavailable", bad
        assert "invalid_decision_cutoff" in out["observations"]["reasons"], bad
        assert out["comparison"]["entries"] == []
        assert out["observations"]["status"] == "unavailable"
        assert out["market_risk"]["status"] == "unavailable"
        assert out["limitations"]["historically_admissible"] is False


def test_psl_ctx_changed_observation_cannot_keep_the_fixture_claim():
    regime = _psl_ctx_regime()
    regime["theme_revisions"]["themes"]["memory_storage"]["level_state"] = "NEUTRAL"
    out = _psl_ctx_project(regime_document=regime)
    entries = _psl_ctx_entries(out)
    first = entries["earnings_expectations"]
    assert first["status"] == "unresolved"
    assert first["reasons"] == ["revision_level_state_not_positive"]
    assert "Positive revision breadth" not in first["statement"]
    assert "NEUTRAL" in first["statement"]
    # the second reading is regenerated from the changed value, not copied
    second = entries["narrow_or_fading_revisions"]
    assert "despite a NEUTRAL level state" in second["statement"]
    assert "POSITIVE" not in second["statement"]
    # independent valid sections remain
    assert out["market_risk"]["status"] == "available"
    assert out["market_risk"]["measured_state"]["verdict"] == "RISK_OFF"
    assert out["observations"]["status"] == "available"
    assert out["status"] == "partial"


def test_psl_ctx_missing_observation_section_keeps_independent_sections():
    regime = _psl_ctx_regime()
    del regime["theme_revisions"]
    out = _psl_ctx_project(regime_document=regime)
    assert out["status"] == "partial"
    assert out["observations"]["status"] == "partial"
    assert "revision_state_unavailable" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]
    # the separately dated bottleneck reading survives independently
    assert out["observations"]["bottleneck"]["asof"] == "2026-09-01"
    assert out["observations"]["bottleneck"]["band"] == "NEUTRAL"
    entries = _psl_ctx_entries(out)
    assert entries["earnings_expectations"]["status"] == "unresolved"
    assert "Positive revision breadth" not in \
        entries["earnings_expectations"]["statement"]
    assert entries["physical_supply_constraint"]["status"] == "supported"
    assert out["market_risk"]["status"] == "available"


def test_psl_ctx_refuses_duplicate_outside_and_mismatched_contributors():
    base = _psl_ctx_regime()
    theme = base["theme_revisions"]["themes"]["memory_storage"]

    duplicated = copy.deepcopy(base)
    members = duplicated["theme_revisions"]["themes"]["memory_storage"]["members"]
    members.append(dict(members[0]))
    out = _psl_ctx_project(regime_document=duplicated)
    assert "contributors_duplicate" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]
    assert out["status"] == "partial"

    outside = copy.deepcopy(base)
    rows = outside["theme_revisions"]["themes"]["memory_storage"]["members"]
    rows[0] = dict(rows[0])
    rows[0]["ticker"] = "ZZZZ"
    out = _psl_ctx_project(regime_document=outside)
    assert "contributors_outside_roster" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]

    mismatched = copy.deepcopy(base)
    mismatched["theme_revisions"]["themes"]["memory_storage"]["n_members"] = 9
    out = _psl_ctx_project(regime_document=mismatched)
    assert "roster_count_mismatch" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]

    covered_mismatch = copy.deepcopy(base)
    covered_mismatch["theme_revisions"]["themes"]["memory_storage"][
        "n_covered"] = 4
    out = _psl_ctx_project(regime_document=covered_mismatch)
    assert "contributors_count_mismatch" in out["observations"]["reasons"]

    over_covered = copy.deepcopy(base)
    over_covered["theme_revisions"]["themes"]["memory_storage"]["n_covered"] = 9
    over_covered["theme_revisions"]["themes"]["memory_storage"][
        "coverage"] = 1.8
    out = _psl_ctx_project(regime_document=over_covered)
    assert "revision_counts_invalid" in out["observations"]["reasons"]

    # the theme is untouched by every refusal above
    assert theme["members"][0]["ticker"] == "WDC"


def test_psl_ctx_refuses_boolean_nonfinite_and_mistyped_numbers():
    for field, value, reason in (
        ("breadth", True, "boolean_not_numeric"),
        ("breadth", float("inf"), "non_finite_value"),
        ("breadth", float("nan"), "non_finite_value"),
        ("breadth", "0.746", "revision_field_invalid"),
        ("n_members", -1, "revision_counts_invalid"),
        ("n_members", 2.5, "revision_counts_invalid"),
        ("n_covered", True, "boolean_not_numeric"),
    ):
        regime = _psl_ctx_regime()
        regime["theme_revisions"]["themes"]["memory_storage"][field] = value
        out = _psl_ctx_project(regime_document=regime)
        assert reason in out["observations"]["reasons"], (field, value)
        assert "revision_state" not in out["observations"], (field, value)
        entries = _psl_ctx_entries(out)
        assert entries["earnings_expectations"]["status"] == "unresolved"
        assert "Positive revision breadth" not in \
            entries["earnings_expectations"]["statement"]
        assert out["status"] == "partial"


def test_psl_ctx_enforces_the_named_bounds():
    # theme key
    out = _psl_ctx_project(theme_key="x" * 65)
    assert out["status"] == "unavailable"
    assert "invalid_theme_key" in out["observations"]["reasons"]

    # theme name
    config = _psl_ctx_config()
    config["themes"]["memory_storage"]["name"] = "N" * 121
    out = _psl_ctx_project(config_document=config)
    assert "theme_name_invalid" in out["theme"]["reasons"]
    assert out["theme"]["status"] == "unavailable"

    # ticker length
    config = _psl_ctx_config()
    config["themes"]["memory_storage"]["tickers"] = ["T" * 17]
    out = _psl_ctx_project(config_document=config)
    assert "roster_ticker_invalid" in out["theme"]["reasons"]

    # roster size
    config = _psl_ctx_config()
    config["themes"]["memory_storage"]["tickers"] = [
        "T{0:02d}".format(i) for i in range(65)]
    out = _psl_ctx_project(config_document=config)
    assert "roster_too_large" in out["theme"]["reasons"]

    # duplicate roster ticker
    config = _psl_ctx_config()
    config["themes"]["memory_storage"]["tickers"] = ["MU", "MU"]
    out = _psl_ctx_project(config_document=config)
    assert "roster_duplicate_ticker" in out["theme"]["reasons"]

    # contributor size
    regime = _psl_ctx_regime()
    theme = regime["theme_revisions"]["themes"]["memory_storage"]
    theme["members"] = [
        {"ticker": "T{0:02d}".format(i), "breadth": 0.5, "n_analysts": 1,
         "est_chg_90d": 1.0, "n_covering": 2, "breadth_cov": 0.1}
        for i in range(65)]
    theme["n_members"] = 65
    theme["n_covered"] = 65
    theme["coverage"] = 1.0
    out = _psl_ctx_project(regime_document=regime)
    assert "contributors_too_large" in out["observations"]["reasons"]

    # source_ref length
    attribution = _psl_ctx_attribution()
    attribution["regime_document"]["source_ref"] = "s" * 513
    out = _psl_ctx_project(source_attribution=attribution)
    assert "source_ref_invalid" in out["provenance"]["reasons"]

    # raw_sha256 must be exact 64 lowercase hex
    for bad in ("A" * 64, "a" * 63, "a" * 65, "g" * 64, 123):
        attribution = _psl_ctx_attribution()
        attribution["config_document"]["raw_sha256"] = bad
        out = _psl_ctx_project(source_attribution=attribution)
        assert "raw_sha256_invalid" in out["provenance"]["reasons"], bad

    # the declared limits are the ones the commission names
    assert PSL_CTX_LIMITS["max_configured_tickers"] == 64
    assert PSL_CTX_LIMITS["max_contributors"] == 64
    assert PSL_CTX_LIMITS["max_ticker_chars"] == 16
    assert PSL_CTX_LIMITS["max_theme_key_chars"] == 64
    assert PSL_CTX_LIMITS["max_theme_name_chars"] == 120
    assert PSL_CTX_LIMITS["max_source_ref_chars"] == 512
    assert PSL_CTX_LIMITS["max_selected_depth"] == 10
    assert PSL_CTX_LIMITS["max_selected_nodes"] == 2048
    assert PSL_CTX_LIMITS["max_comparison_entries"] == 4
    assert PSL_CTX_LIMITS["max_statement_chars"] == 320
    assert PSL_CTX_LIMITS["max_check_chars"] == 320
    assert PSL_CTX_LIMITS["max_output_bytes"] == 16384


def test_psl_ctx_refuses_cycles_and_type_violations():
    # a cycle inside a selected branch
    regime = _psl_ctx_regime()
    theme = regime["theme_revisions"]["themes"]["memory_storage"]
    theme["self"] = theme
    out = _psl_ctx_project(regime_document=regime)
    assert out["status"] == "unavailable"
    assert "input_cycle_detected" in out["observations"]["reasons"]

    # a non-JSON type inside a selected branch
    regime = _psl_ctx_regime()
    regime["theme_revisions"]["themes"]["memory_storage"]["weird"] = {1, 2}
    out = _psl_ctx_project(regime_document=regime)
    assert out["status"] == "unavailable"
    assert "input_type_violation" in out["observations"]["reasons"]

    # a non-string mapping key inside a selected branch
    regime = _psl_ctx_regime()
    regime["theme_revisions"]["themes"]["memory_storage"][7] = "x"
    out = _psl_ctx_project(regime_document=regime)
    assert out["status"] == "unavailable"
    assert "input_type_violation" in out["observations"]["reasons"]

    # an oversized selected branch exceeds the node budget
    config = _psl_ctx_config()
    config["themes"]["memory_storage"]["tickers"] = [
        "T{0:04d}".format(i) for i in range(2100)]
    out = _psl_ctx_project(config_document=config)
    assert out["status"] == "unavailable"
    assert "input_bound_exceeded" in out["observations"]["reasons"]


def test_psl_ctx_attribution_is_carried_without_a_verification_claim():
    out = _psl_ctx_project()
    provenance = out["provenance"]
    assert provenance["status"] == "available"
    assert provenance["attribution_verification"] == "not_established_by_projection"
    assert sorted(provenance["source_attribution"]) == sorted(
        PSL_CTX_ATTRIBUTION_KEYS)
    for key in PSL_CTX_ATTRIBUTION_KEYS:
        entry = provenance["source_attribution"][key]
        assert entry["raw_sha256"] == _psl_ctx_attribution()[key]["raw_sha256"]
        assert entry["source_ref"] == _psl_ctx_attribution()[key]["source_ref"]

    # a changed attribution is carried through, and never verified
    attribution = _psl_ctx_attribution()
    attribution["regime_document"]["raw_sha256"] = "b" * 64
    attribution["regime_document"]["source_ref"] = "https://example.invalid/x"
    changed = _psl_ctx_project(source_attribution=attribution)
    carried = changed["provenance"]["source_attribution"]["regime_document"]
    assert carried["raw_sha256"] == "b" * 64
    assert carried["source_ref"] == "https://example.invalid/x"
    assert changed["provenance"]["attribution_verification"] == \
        "not_established_by_projection"
    assert changed["limitations"]["attribution_verification"] == \
        "not_established_by_projection"
    assert changed["limitations"]["original_available_at"] is None
    blob = json.dumps(changed, ensure_ascii=False, sort_keys=True)
    for token in ("verified", "custody", "attested"):
        assert token not in blob.lower(), token


def test_psl_ctx_output_is_deterministic_detached_and_strict_json():
    regime = _psl_ctx_regime()
    config = _psl_ctx_config()
    risk = _psl_ctx_public_risk()
    attribution = _psl_ctx_attribution()
    frozen = {
        "regime": copy.deepcopy(regime),
        "config": copy.deepcopy(config),
        "risk": copy.deepcopy(risk),
        "attribution": copy.deepcopy(attribution),
    }
    first = project_dated_context(
        theme_key="memory_storage", regime_document=regime,
        config_document=config, public_risk_document=risk,
        source_attribution=attribution)
    second = project_dated_context(
        theme_key="memory_storage", regime_document=regime,
        config_document=config, public_risk_document=risk,
        source_attribution=attribution)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    # the inputs are read, never mutated
    assert regime == frozen["regime"]
    assert config == frozen["config"]
    assert risk == frozen["risk"]
    assert attribution == frozen["attribution"]

    # strict JSON: no NaN, no Infinity, and it round-trips
    encoded = json.dumps(first, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":"), sort_keys=True)
    assert "NaN" not in encoded and "Infinity" not in encoded
    assert json.loads(encoded) == first

    # the projection reads nothing ambient
    from engine import sector_dated_context as sdc

    assert not hasattr(sdc, "open")
    assert not hasattr(sdc, "os")
    assert not hasattr(sdc, "requests")


def test_psl_ctx_module_imports_stdlib_only_and_never_reads_a_clock():
    import ast
    from pathlib import Path

    from engine import sector_dated_context as sdc

    allowed = {"__future__", "json", "math", "re", "datetime"}
    source = Path(sdc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported, "module-level imports must be parseable"
    assert imported <= allowed, "non-stdlib top-level imports: {0}".format(
        sorted(imported - allowed))
    # owner modules, builders and providers are never imported
    for owner in ("engine", "risk_envelope", "leadership_rotation_context",
                  "yaml", "numpy", "pandas", "os", "subprocess", "urllib"):
        assert owner not in imported

    # no I/O, no clock read, no randomness, anywhere in the code
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
    for token in ("open(", "urlopen", "datetime.now(", "random", "subprocess",
                  "os.environ", "time.time", "importlib"):
        assert token not in code_only, token


def test_psl_ctx_output_bound_is_enforced_without_truncation():
    tickers = ["T{0:015d}".format(i) for i in range(64)]
    members = [{"ticker": ticker, "breadth": 0.5, "n_analysts": 10,
                "est_chg_90d": 1.5, "n_covering": 20, "breadth_cov": 0.25}
               for ticker in tickers]
    regime = _psl_ctx_regime()
    theme = regime["theme_revisions"]["themes"]["memory_storage"]
    theme["name"] = "X" * 120
    theme["members"] = members
    theme["n_members"] = 64
    theme["n_covered"] = 64
    theme["coverage"] = 1.0
    config = _psl_ctx_config()
    config["themes"]["memory_storage"]["name"] = "X" * 120
    config["themes"]["memory_storage"]["tickers"] = tickers

    out = _psl_ctx_project(regime_document=regime, config_document=config)
    assert out["status"] == "unavailable"
    assert "output_bound_exceeded" in out["observations"]["reasons"]
    encoded = json.dumps(out, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":"), sort_keys=True)
    assert len(encoded.encode("utf-8")) <= PSL_CTX_LIMITS["max_output_bytes"]
    # nothing was silently truncated: the refused result carries no roster
    assert out["theme"]["roster"] == []

    # a normal-sized input stays inside the bound
    small = _psl_ctx_project()
    encoded = json.dumps(small, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":"), sort_keys=True)
    assert len(encoded.encode("utf-8")) <= PSL_CTX_LIMITS["max_output_bytes"]


def test_psl_ctx_comparison_has_exactly_four_fixed_entries():
    out = _psl_ctx_project()
    comparison = out["comparison"]
    assert comparison["evaluation"] == "prospective_unevaluated"
    assert len(comparison["entries"]) == PSL_CTX_LIMITS["max_comparison_entries"]
    assert [entry["id"] for entry in comparison["entries"]] == list(
        PSL_CTX_COMPARISON_IDS)

    for entry in comparison["entries"]:
        assert entry["evaluation"] == "prospective_unevaluated"
        assert entry["status"] in PSL_CTX_ENTRY_STATUSES
        assert 0 < len(entry["statement"]) <= PSL_CTX_LIMITS["max_statement_chars"]
        assert 0 < len(entry["falsifier"]["check"]) <= \
            PSL_CTX_LIMITS["max_check_chars"]
        # a falsifier is never marked met, and no entry ranks or scores
        assert entry["falsifier"]["met"] is False
        assert "score" not in entry
        assert "rank" not in entry

    entries = _psl_ctx_entries(out)
    assert entries["earnings_expectations"]["status"] == "supported"
    assert entries["narrow_or_fading_revisions"]["status"] == "supported"
    assert entries["physical_supply_constraint"]["status"] == "supported"
    assert entries["market_or_other_causes"]["status"] == "unresolved"
    assert "alternatives_not_resolved_by_supplied_evidence" in \
        entries["market_or_other_causes"]["reasons"]

    # the statements carry the supplied values, not a copied conclusion
    assert "3 of 5" in entries["narrow_or_fading_revisions"]["statement"]
    assert "ROLLING" in entries["narrow_or_fading_revisions"]["statement"]
    assert "NEUTRAL" in entries["physical_supply_constraint"]["statement"]
    assert "2026-09-01" in entries["physical_supply_constraint"]["statement"]
    assert "2026-11-06" in entries["physical_supply_constraint"]["statement"]


def test_psl_ctx_evidence_references_resolve_to_projected_fields():
    out = _psl_ctx_project()
    context = {
        "theme": out["theme"],
        "observations": out["observations"],
        "market_risk": out["market_risk"],
    }
    for entry in out["comparison"]["entries"]:
        assert entry["evidence_refs"], entry["id"]
        for ref in entry["evidence_refs"]:
            node = context
            for part in ref.split("."):
                assert isinstance(node, dict), ref
                assert part in node, ref
                node = node[part]
            assert node is not None, ref

    # a reference into an unprojected section never survives
    regime = _psl_ctx_regime()
    del regime["bottleneck"]
    out = _psl_ctx_project(regime_document=regime)
    entries = _psl_ctx_entries(out)
    assert entries["physical_supply_constraint"]["status"] == "unresolved"
    assert entries["physical_supply_constraint"]["evidence_refs"] == []
    assert "bottleneck_band_unavailable" in \
        entries["physical_supply_constraint"]["reasons"]


def test_psl_ctx_unknown_theme_and_unknown_owner_sections_are_typed():
    out = _psl_ctx_project(theme_key="no_such_theme")
    assert out["status"] == "unavailable"
    assert "theme_not_in_config" in out["theme"]["reasons"]

    regime = _psl_ctx_regime()
    del regime["bottleneck"]
    out = _psl_ctx_project(regime_document=regime)
    assert "bottleneck_unavailable" in out["observations"]["reasons"]
    assert "bottleneck" not in out["observations"]
    # the revision reading survives independently
    assert out["observations"]["revision_state"]["level_state"] == "POSITIVE"

    regime = _psl_ctx_regime()
    del regime["freshness"]
    out = _psl_ctx_project(regime_document=regime)
    assert out["observations"]["clocks"]["regime_built_at"] is None
    assert out["observations"]["revision_state"]["asof"] == "2026-11-06"

    out = _psl_ctx_project(public_risk_document={})
    assert out["market_risk"]["status"] == "unavailable"
    assert "market_risk_schema_missing" in out["market_risk"]["reasons"]

    out = _psl_ctx_project(regime_document="not-a-document")
    assert out["status"] == "unavailable"
    assert "invalid_regime_document" in out["observations"]["reasons"]


def test_psl_ctx_declared_reason_codes_are_typed_and_bounded():
    assert "historical_availability_unqualified" in PSL_CTX_REASONS
    assert "output_bound_exceeded" in PSL_CTX_REASONS
    assert "invalid_decision_cutoff" in PSL_CTX_REASONS
    assert "input_cycle_detected" in PSL_CTX_REASONS
    assert "input_bound_exceeded" in PSL_CTX_REASONS
    assert "boolean_not_numeric" in PSL_CTX_REASONS
    assert "non_finite_value" in PSL_CTX_REASONS
    # every reason is a stable snake_case token, never raw exception prose
    for reason in PSL_CTX_REASONS:
        assert reason == reason.lower()
        assert " " not in reason
        assert reason.replace("_", "").isalnum()
    out = _psl_ctx_project()
    seen = set(out["observations"]["reasons"]) | set(out["theme"]["reasons"])
    seen |= set(out["market_risk"]["reasons"]) | set(out["provenance"]["reasons"])
    assert seen <= set(PSL_CTX_REASONS)


# ---------------------------------------------------------------------------
# PSL-DATED-CTX-2 -- the corrective commission's focused cases.
#
# Every case below is a defect that the reconstructed projection still
# carries.  Each one is written so that it fails against the reconstruction
# and holds only after the correction lands.  The cases are grouped by the
# commission's six concrete corrections.
# ---------------------------------------------------------------------------


def _psl_ctx_revision(theme):
    """The selected revision theme of a regime fixture."""
    return theme["theme_revisions"]["themes"]["memory_storage"]


def _psl_ctx_bottleneck(theme):
    """The selected bottleneck theme of a regime fixture."""
    return theme["bottleneck"]["themes"]["memory_storage"]


def _psl_ctx_statements(out):
    """Every comparison statement, joined for prose assertions."""
    return " || ".join(
        entry["statement"] for entry in out["comparison"]["entries"])


def _psl_ctx_encoded(out):
    """The strict JSON encoding of a result, as UTF-8 bytes."""
    return json.dumps(
        out, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"), sort_keys=True).encode("utf-8")


# -- correction 1: one accepted-count predicate, and a guarded zero --------

def test_psl_ctx_correction_zero_member_counts_never_divide_by_zero():
    """A zero-member roster is typed, not a ZeroDivisionError."""
    regime = _psl_ctx_regime()
    theme = _psl_ctx_revision(regime)
    theme["n_members"] = 0
    theme["n_covered"] = 0
    theme["coverage"] = 0.0
    theme["members"] = []
    out = _psl_ctx_project(regime_document=regime)
    assert out["status"] in PSL_CTX_STATUSES
    assert "revision_coverage_inconsistent" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]
    assert len(_psl_ctx_encoded(out)) <= PSL_CTX_LIMITS["max_output_bytes"]


def test_psl_ctx_correction_a_float_member_count_is_checked_against_the_roster():
    """A float member count is checked exactly like an integer member count."""
    regime = _psl_ctx_regime()
    _psl_ctx_revision(regime)["n_members"] = 9.0
    out = _psl_ctx_project(regime_document=regime)
    assert "roster_count_mismatch" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]


def test_psl_ctx_correction_float_counts_are_checked_for_cover_and_coverage():
    """Float covered/member counts are checked for cover and for coverage."""
    regime = _psl_ctx_regime()
    theme = _psl_ctx_revision(regime)
    theme["n_members"] = 5.0
    theme["n_covered"] = 9.0
    theme["coverage"] = 1.8
    out = _psl_ctx_project(regime_document=regime)
    assert "revision_counts_invalid" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]

    regime = _psl_ctx_regime()
    theme = _psl_ctx_revision(regime)
    theme["n_members"] = 5.0
    theme["n_covered"] = 3.0
    theme["coverage"] = 0.5
    out = _psl_ctx_project(regime_document=regime)
    assert "revision_coverage_inconsistent" in out["observations"]["reasons"]
    assert "revision_state" not in out["observations"]


def test_psl_ctx_correction_a_genuine_integral_float_count_keeps_its_value():
    """A valid integral float count is never rejected and never rewritten."""
    out = _psl_ctx_project()
    net_up_total = out["observations"]["revision_state"]["net_up_total"]
    assert net_up_total == 24.0
    assert isinstance(net_up_total, float)
    assert "revision_counts_invalid" not in out["observations"]["reasons"]
    assert out["observations"]["status"] == "available"


# -- correction 2: the owner label is not the numeric support --------------

def test_psl_ctx_correction_a_positive_label_without_breadth_is_not_supported():
    """The owner label alone never carries the strong positive statement."""
    regime = _psl_ctx_regime()
    del _psl_ctx_revision(regime)["breadth"]
    out = _psl_ctx_project(regime_document=regime)
    first = _psl_ctx_entries(out)["earnings_expectations"]
    assert first["status"] == "unresolved"
    assert "Positive revision breadth" not in first["statement"]
    assert "revision_breadth_unavailable" in first["reasons"]
    assert out["comparison"]["status"] == "partial"


def test_psl_ctx_correction_a_negative_breadth_conflicts_with_a_positive_label():
    """A negative numeric breadth conflicts with the supplied owner label."""
    regime = _psl_ctx_regime()
    _psl_ctx_revision(regime)["breadth"] = -0.25
    out = _psl_ctx_project(regime_document=regime)
    first = _psl_ctx_entries(out)["earnings_expectations"]
    assert first["status"] == "unresolved"
    assert "Positive revision breadth" not in first["statement"]
    # the raw owner label is preserved, and the conflict is named
    assert "POSITIVE" in first["statement"]
    assert "revision_breadth_not_positive" in first["reasons"]


def test_psl_ctx_correction_missing_counts_or_contributors_block_the_reading():
    """Missing counts and missing contributors block the positive reading."""
    regime = _psl_ctx_regime()
    theme = _psl_ctx_revision(regime)
    del theme["n_covered"]
    del theme["n_members"]
    out = _psl_ctx_project(regime_document=regime)
    first = _psl_ctx_entries(out)["earnings_expectations"]
    assert first["status"] == "unresolved"
    assert "Positive revision breadth" not in first["statement"]
    assert "coverage_unavailable" in first["reasons"]

    regime = _psl_ctx_regime()
    del _psl_ctx_revision(regime)["members"]
    out = _psl_ctx_project(regime_document=regime)
    first = _psl_ctx_entries(out)["earnings_expectations"]
    assert first["status"] == "unresolved"
    assert "Positive revision breadth" not in first["statement"]
    # the missing contributor rows are typed on the observation section, and
    # the reading they support is not asserted
    assert "contributors_unavailable" in out["observations"]["reasons"]
    assert "contributors_count_mismatch" in first["reasons"]


def test_psl_ctx_correction_a_complete_primary_reading_is_unchanged():
    """A complete, consistent reading keeps its supported positive statement."""
    out = _psl_ctx_project()
    first = _psl_ctx_entries(out)["earnings_expectations"]
    assert first["status"] == "supported"
    assert first["statement"] == (
        "Positive revision breadth in the supplied snapshot is consistent "
        "with improving covered-member expectations; price cause is not "
        "established.")
    assert first["reasons"] == []
    assert out["observations"]["revision_state"]["breadth"] == 0.746
    assert out["observations"]["revision_state"]["n_covered"] == 3
    assert out["observations"]["revision_state"]["n_members"] == 5


# -- correction 3: the configured theme identity fences theme assertions --

def test_psl_ctx_correction_a_missing_config_entry_withholds_theme_assertions():
    """A theme that is not in the configuration asserts nothing."""
    out = _psl_ctx_project(theme_key="no_such_theme")
    assert out["theme"]["status"] == "unavailable"
    assert "theme_not_in_config" in out["theme"]["reasons"]
    assert out["status"] == "unavailable"
    entries = _psl_ctx_entries(out)
    for entry_id in ("earnings_expectations", "narrow_or_fading_revisions",
                     "physical_supply_constraint"):
        entry = entries[entry_id]
        assert entry["status"] == "unresolved", entry_id
        assert entry["evidence_refs"] == [], entry_id
        assert "theme_identity_unqualified" in entry["reasons"], entry_id
    # the independent market-global risk stays qualified
    assert out["market_risk"]["status"] == "available"
    assert out["market_risk"]["measured_state"]["verdict"] == "RISK_OFF"


def test_psl_ctx_correction_an_invalid_or_duplicate_roster_withholds_theme_assertions():
    """An invalid or duplicated configured roster asserts nothing either."""
    for tickers, reason in (
        (["MU", "WDC", "", "STX", "NTAP"], "roster_ticker_invalid"),
        (["MU", "MU", "WDC", "STX", "NTAP"], "roster_duplicate_ticker"),
        (["T" * 17, "WDC", "SNDK", "STX", "NTAP"], "roster_ticker_invalid"),
    ):
        config = _psl_ctx_config()
        config["themes"]["memory_storage"]["tickers"] = tickers
        out = _psl_ctx_project(config_document=config)
        assert out["theme"]["status"] == "unavailable"
        assert reason in out["theme"]["reasons"]
        entries = _psl_ctx_entries(out)
        for entry_id in ("earnings_expectations",
                         "narrow_or_fading_revisions",
                         "physical_supply_constraint"):
            entry = entries[entry_id]
            assert entry["status"] == "unresolved", entry_id
            assert entry["evidence_refs"] == [], entry_id
            assert "theme_identity_unqualified" in entry["reasons"], entry_id


def test_psl_ctx_correction_an_invalid_roster_keeps_the_independent_market_risk():
    """A broken theme identity never reclassifies the independent risk."""
    config = _psl_ctx_config()
    config["themes"]["memory_storage"]["tickers"] = ["MU", "MU"]
    out = _psl_ctx_project(config_document=config)
    risk = out["market_risk"]
    assert risk["status"] == "available"
    assert risk["data_state"] == "DEGRADED"
    assert risk["measured_state"]["verdict"] == "RISK_OFF"
    assert risk["measured_state"]["score"] == 40
    assert risk["hazard_summary"]["stage"] is None
    assert risk["hazard_summary"]["stage_reason"] == "required_coverage_unavailable"
    assert risk["policy_summary"]["posture"] == "NORMAL"
    assert risk["policy_summary"]["policy_count"] == 0
    assert risk["source_authority"]["envelope_may_execute"] is False
    # the market-global alternative keeps its own evidence references
    market = _psl_ctx_entries(out)["market_or_other_causes"]
    assert "market_risk.measured_state.verdict" in market["evidence_refs"]


# -- correction 4: valid owner clocks, and each own provisional flag -------

def test_psl_ctx_correction_a_missing_revision_clock_is_typed_and_undated():
    """A missing revision clock is typed and makes no dated claim."""
    regime = _psl_ctx_regime()
    del regime["theme_revisions"]["asof"]
    out = _psl_ctx_project(regime_document=regime)
    assert "revision_asof_unavailable" in out["observations"]["reasons"]
    assert out["observations"]["revision_state"].get("asof") is None
    assert "2026-11-06" not in _psl_ctx_statements(out)
    assert "is contemporaneous with" not in _psl_ctx_statements(out)


def test_psl_ctx_correction_an_invalid_owner_clock_makes_no_dated_claim():
    """A malformed owner clock is typed and makes no dated claim."""
    regime = _psl_ctx_regime()
    regime["theme_revisions"]["asof"] = "whenever"
    out = _psl_ctx_project(regime_document=regime)
    assert "revision_asof_invalid" in out["observations"]["reasons"]
    assert out["observations"]["revision_state"].get("asof") is None
    assert "dated whenever" not in _psl_ctx_statements(out)
    # the raw owner clock is still preserved, separately and unchanged
    assert out["observations"]["clocks"]["theme_revisions_asof"] == "whenever"

    regime = _psl_ctx_regime()
    regime["bottleneck"]["asof"] = "2026-13-45"
    out = _psl_ctx_project(regime_document=regime)
    assert "bottleneck_asof_invalid" in out["observations"]["reasons"]
    assert out["observations"]["bottleneck"].get("asof") is None
    assert "2026-13-45" not in _psl_ctx_statements(out)
    assert out["observations"]["clocks"]["bottleneck_asof"] == "2026-13-45"


def test_psl_ctx_correction_the_same_malformed_clock_is_never_contemporaneous():
    """Two identical malformed clocks never make a contemporaneous claim."""
    regime = _psl_ctx_regime()
    regime["theme_revisions"]["asof"] = "not-a-clock"
    regime["bottleneck"]["asof"] = "not-a-clock"
    out = _psl_ctx_project(regime_document=regime)
    assert "is contemporaneous with" not in _psl_ctx_statements(out)
    assert "not-a-clock" not in _psl_ctx_statements(out)
    assert "revision_asof_invalid" in out["observations"]["reasons"]
    assert "bottleneck_asof_invalid" in out["observations"]["reasons"]
    physical = _psl_ctx_entries(out)["physical_supply_constraint"]
    assert physical["status"] == "unresolved"


def test_psl_ctx_correction_provisional_language_uses_each_own_flag():
    """Each provisional sentence is generated from its own owner flag."""
    statements = {}
    for leg6 in (True, False):
        for fingerprint in (True, False):
            regime = _psl_ctx_regime()
            _psl_ctx_bottleneck(regime)["leg6_detail"]["provisional"] = leg6
            _psl_ctx_bottleneck(regime)["fingerprint"]["provisional"] = \
                fingerprint
            out = _psl_ctx_project(regime_document=regime)
            statements[(leg6, fingerprint)] = _psl_ctx_entries(out)[
                "physical_supply_constraint"]["statement"]

    both = statements[(True, True)]
    language_only = statements[(True, False)]
    fingerprint_only = statements[(False, True)]
    neither = statements[(False, False)]

    assert "language leg" in both and "member fingerprint" in both
    assert "language leg" in language_only
    assert "member fingerprint" not in language_only
    assert "member fingerprint" in fingerprint_only
    assert "language leg" not in fingerprint_only
    assert "provisional" not in neither

    # all four combinations are meaningfully different
    assert len(set(statements.values())) == 4


# -- correction 5: the risk schema and the independently qualified parts --

def test_psl_ctx_correction_an_unexpected_risk_schema_fails_closed():
    """An incompatible risk envelope admits no reading and no reference."""
    risk = _psl_ctx_public_risk()
    risk["schema"] = "mastermind.risk_envelope/v2"
    out = _psl_ctx_project(public_risk_document=risk)
    assert out["market_risk"]["status"] == "unavailable"
    assert out["market_risk"]["reasons"] == ["market_risk_schema_unexpected"]
    for field in ("measured_state", "hazard_summary", "policy_summary",
                  "freshness", "coherence", "source_authority"):
        assert field not in out["market_risk"], field
    market = _psl_ctx_entries(out)["market_or_other_causes"]
    assert market["evidence_refs"] == []
    assert "market_risk_unavailable" in market["reasons"]


def test_psl_ctx_correction_a_failed_risk_subsection_is_withheld_and_unreferenced():
    """A failed risk subsection is withheld; its independent siblings stay."""
    risk = _psl_ctx_public_risk()
    del risk["hazard_summary"]
    out = _psl_ctx_project(public_risk_document=risk)
    assert out["market_risk"]["status"] == "partial"
    assert "market_risk_field_invalid" in out["market_risk"]["reasons"]
    assert "hazard_summary" not in out["market_risk"]
    assert out["market_risk"]["measured_state"]["verdict"] == "RISK_OFF"
    assert out["market_risk"]["freshness"]["source_session"] == "2026-11-06"
    assert out["market_risk"]["policy_summary"]["posture"] == "NORMAL"
    refs = _psl_ctx_entries(out)["market_or_other_causes"]["evidence_refs"]
    assert not any(ref.startswith("market_risk.hazard_summary") for ref in refs)
    assert "market_risk.measured_state.verdict" in refs

    risk = _psl_ctx_public_risk()
    risk["measured_state"]["score"] = "forty"
    out = _psl_ctx_project(public_risk_document=risk)
    assert out["market_risk"]["status"] == "partial"
    assert "measured_state" not in out["market_risk"]
    assert out["market_risk"]["policy_summary"]["posture"] == "NORMAL"
    assert out["market_risk"]["freshness"]["all_on_session"] is False
    refs = _psl_ctx_entries(out)["market_or_other_causes"]["evidence_refs"]
    assert "market_risk.measured_state.verdict" not in refs

    risk = _psl_ctx_public_risk()
    risk["freshness"]["per_source"]["market-state-latest"] = "not-a-mapping"
    out = _psl_ctx_project(public_risk_document=risk)
    assert out["market_risk"]["status"] == "partial"
    assert "freshness" not in out["market_risk"]
    assert out["market_risk"]["measured_state"]["verdict"] == "RISK_OFF"
    assert out["market_risk"]["policy_summary"]["posture"] == "NORMAL"


# -- correction 6: every return is bounded, and every value is detached ---

def test_psl_ctx_correction_every_refusal_is_bounded_and_never_echoes_the_selector():
    """No refusal echoes an invalid selector and no refusal exceeds the bound."""
    huge = "z" * 200000
    refusals = [
        _psl_ctx_project(theme_key=huge),
        _psl_ctx_project(theme_key=huge, decision_cutoff="not-a-cutoff"),
        _psl_ctx_project(theme_key="x" * 65),
        _psl_ctx_project(theme_key=42),
        _psl_ctx_project(regime_document=None),
        _psl_ctx_project(config_document=None),
        _psl_ctx_project(public_risk_document=None),
        _psl_ctx_project(decision_cutoff="not-a-cutoff"),
    ]
    for out in refusals:
        encoded = _psl_ctx_encoded(out)
        assert len(encoded) <= PSL_CTX_LIMITS["max_output_bytes"]
        assert b"z" * 1000 not in encoded
        assert out["status"] in PSL_CTX_STATUSES
        for section in ("theme", "observations", "comparison", "market_risk",
                        "provenance"):
            assert out[section]["status"] in PSL_CTX_SECTION_STATUSES
    assert refusals[0]["theme"]["theme_key"] is None
    assert refusals[1]["theme"]["theme_key"] is None
    assert "invalid_decision_cutoff" in refusals[1]["observations"]["reasons"]
    assert "invalid_theme_key" in refusals[0]["observations"]["reasons"]


def test_psl_ctx_correction_the_contradiction_list_is_detached_in_both_directions():
    """A projected contradiction list shares nothing with its source."""
    risk = _psl_ctx_public_risk()
    risk["coherence"]["contradictions"] = [
        {"kind": "measured_vs_hazard", "detail": "mismatch"}]
    risk["coherence"]["contradiction_count"] = 1

    # mutating the projected result never reaches the supplied document
    out = _psl_ctx_project(public_risk_document=risk)
    contradictions = out["market_risk"]["coherence"]["contradictions"]
    assert contradictions == [
        {"kind": "measured_vs_hazard", "detail": "mismatch"}]
    contradictions.append("mutated")
    contradictions[0]["detail"] = "mutated"
    assert risk["coherence"]["contradictions"] == [
        {"kind": "measured_vs_hazard", "detail": "mismatch"}]

    # mutating the supplied document never reaches the projected result
    out = _psl_ctx_project(public_risk_document=risk)
    risk["coherence"]["contradictions"].append("added later")
    risk["coherence"]["contradictions"][0]["detail"] = "changed later"
    assert out["market_risk"]["coherence"]["contradictions"] == [
        {"kind": "measured_vs_hazard", "detail": "mismatch"}]


def test_psl_ctx_correction_the_pinned_primary_source_projects_the_same_reading():
    """The real pinned bytes project the same dated reading as the fixture."""
    import subprocess
    from pathlib import Path

    import yaml

    root = str(Path(__file__).resolve().parents[1])

    def pinned(path):
        return subprocess.run(
            ["git", "-C", root, "cat-file", "blob",
             "{0}:{1}".format(PSL_CTX_BASE, path)],
            capture_output=True, check=True, timeout=120).stdout

    try:
        regime = json.loads(pinned("data/regime/latest.json"))
        config = yaml.safe_load(pinned("config.yml"))
        risk = json.loads(pinned("site/riskdata/risk_envelope.json"))
    except (OSError, subprocess.SubprocessError, ValueError):
        pytest.skip(
            "this checkout does not carry the pinned bytes; the byte/hash "
            "proof is in the lane evidence")
    if not isinstance(config, dict) or "themes" not in config:
        pytest.skip("the pinned configuration does not carry the themes map")

    out = project_dated_context(
        theme_key="memory_storage", regime_document=regime,
        config_document=config, public_risk_document=risk,
        source_attribution=_psl_ctx_attribution())
    fixture = _psl_ctx_project()

    assert out["status"] == "dated_context"
    assert out["theme"]["roster"] == fixture["theme"]["roster"]
    assert out["observations"]["revision_state"] == \
        fixture["observations"]["revision_state"]
    assert out["observations"]["contributors"] == fixture["observations"]["contributors"]
    assert out["observations"]["bottleneck"]["band"] == "NEUTRAL"
    assert out["observations"]["bottleneck"]["asof"] == "2026-09-01"
    assert out["observations"]["clocks"]["theme_revisions_asof"] == "2026-11-06"
    assert out["market_risk"]["measured_state"] == fixture["market_risk"]["measured_state"]
    assert out["market_risk"]["data_state"] == "DEGRADED"
    assert out["market_risk"]["hazard_summary"]["stage"] is None
    assert out["market_risk"]["policy_summary"]["posture"] == "NORMAL"

    # the scope never widens into a sector or a global claim
    assert out["scope"] == PSL_CTX_SCOPE
    assert out["theme"]["membership_basis"] == "configured_theme_roster"
    assert out["limitations"]["current_sector_usable"] is False
    assert out["limitations"]["historically_admissible"] is False
    assert all(flag is False for flag in out["authority"].values())
