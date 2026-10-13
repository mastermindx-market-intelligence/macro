"""Tests for engine.sector_intelligence.finance_overlap (Finance T3).

Pure-function tests for the deterministic overlap and basket-state context
arithmetic that Finance T3 exposes. No fixtures, no I/O, no real securities —
synthetic SYN_* identifiers throughout.
"""

from __future__ import annotations

from pytest import approx

from engine.sector_intelligence.finance_overlap import (
    MACRO_DRIVER_VOCAB,
    OVERLAP_DIMENSIONS,
    WEIGHTING_FAMILIES,
    basket_state_context,
    business_line_overlap,
    macro_driver_overlap,
    market_factor_overlap,
    overlap_report,
    ownership_hierarchy_report,
    security_jaccard,
    weighted_overlap,
)


# ---------------------------------------------------------------------------
# Frozen-vocabulary sanity
# ---------------------------------------------------------------------------

def test_overlap_dimensions_frozen():
    assert OVERLAP_DIMENSIONS == (
        "SECURITY",
        "BUSINESS_LINE",
        "MACRO_DRIVER",
        "MARKET_FACTOR",
        "OWNERSHIP_HIERARCHY",
    )


def test_weighting_families_frozen():
    assert WEIGHTING_FAMILIES == (
        "EQUAL_WEIGHT",
        "FLOAT_CAP_CONTEXT",
        "EXPOSURE_WEIGHT",
        "EXPOSURE_CAPPED_WEIGHT",
        "STRATIFIED_EQUAL_WEIGHT",
    )


def test_macro_driver_vocabulary_size_and_membership():
    # 13 drivers per the FINANCE R11-9 audit.
    assert len(MACRO_DRIVER_VOCAB) == 13
    assert "policy_rates" in MACRO_DRIVER_VOCAB
    assert "liquidity" in MACRO_DRIVER_VOCAB
    assert "catastrophe_reinsurance" in MACRO_DRIVER_VOCAB


# ---------------------------------------------------------------------------
# security_jaccard
# ---------------------------------------------------------------------------

def test_security_jaccard_spec_example():
    # {V, MA} ∩ {MA, AXP} = {MA}; {V, MA} ∪ {MA, AXP} = {V, MA, AXP}; jaccard=1/3
    assert security_jaccard({"V", "MA"}, {"MA", "AXP"}) == approx(1 / 3)


def test_security_jaccard_empty_means_empty_returns_none():
    # Spec: both empty ⇒ None (NOT 0.0).
    assert security_jaccard([], []) is None
    assert security_jaccard(set(), set()) is None


def test_security_jaccard_normalizes_case_and_whitespace():
    # Whitespace and case collapse to the same key.
    assert security_jaccard([" v ", "AXP"], ["v", "axp"]) == approx(1.0)


def test_security_jaccard_disjoint_returns_zero():
    assert security_jaccard({"V", "MA"}, {"AXP", "JPM"}) == 0.0


def test_security_jaccard_identical_returns_one():
    assert security_jaccard({"V", "MA"}, {"V", "MA"}) == approx(1.0)


def test_security_jaccard_one_side_empty_returns_zero():
    # Only one side empty: union non-empty, intersection empty ⇒ 0.0.
    assert security_jaccard({"V", "MA"}, []) == 0.0
    assert security_jaccard([], {"V", "MA"}) == 0.0


# ---------------------------------------------------------------------------
# weighted_overlap
# ---------------------------------------------------------------------------

def test_weighted_overlap_symmetric():
    a = {"x": 0.6, "y": 0.4}
    b = {"x": 0.3, "y": 0.7}
    assert weighted_overlap(a, b) == approx(weighted_overlap(b, a))


def test_weighted_overlap_in_unit_interval():
    for a, b in [
        ({"x": 0.5, "y": 0.5}, {"x": 0.5, "y": 0.5}),
        ({"x": 1.0}, {"y": 1.0}),
        ({"x": 0.2, "y": 0.3, "z": 0.5}, {"x": 0.4, "y": 0.6}),
        ({"x": 1.0}, {"x": 0.0001}),
    ]:
        v = weighted_overlap(a, b)
        assert v is not None
        assert 0.0 <= v <= 1.0


def test_weighted_overlap_identical_maps_normalized_to_one():
    # {x:1, y:1} normalizes to {x:0.5, y:0.5}; identical maps ⇒ Σ min(w,w)=1.0.
    assert weighted_overlap({"x": 1.0, "y": 1.0}, {"x": 1.0, "y": 1.0}) == approx(1.0)


def test_weighted_overlap_disjoint_returns_zero():
    assert weighted_overlap({"x": 1.0}, {"y": 1.0}) == approx(0.0)


def test_weighted_overlap_negative_weight_raises():
    raised = False
    try:
        weighted_overlap({"x": -0.1}, {"y": 1.0})
    except ValueError:
        raised = True
    assert raised, "negative weight must raise ValueError"

    raised_b = False
    try:
        weighted_overlap({"x": 1.0}, {"y": -0.1})
    except ValueError:
        raised_b = True
    assert raised_b, "negative weight on b side must raise ValueError"


def test_weighted_overlap_non_positive_total_returns_none():
    # Both sides zero ⇒ None.
    assert weighted_overlap({}, {}) is None
    # One side all zeros / non-positive ⇒ None.
    assert weighted_overlap({"x": 0.0}, {"y": 1.0}) is None
    assert weighted_overlap({"x": 1.0}, {"y": 0.0}) is None


def test_weighted_overlap_unnormalized_inputs():
    # Raw weights {1:2, 2:3} and {1:4, 2:6} should give 1.0 (same normalized dir).
    assert weighted_overlap(
        {"x": 2.0, "y": 3.0}, {"x": 4.0, "y": 6.0}
    ) == approx(1.0)


# ---------------------------------------------------------------------------
# business_line_overlap
# ---------------------------------------------------------------------------

def test_business_line_overlap_basic():
    # Lower-case + collapsed-whitespace normalization: "Card Lending" == "card   lending".
    # A = {card lending, deposits}; B = {card lending, wealth}; ∩=1, ∪=3; jaccard=1/3.
    assert business_line_overlap(
        ["Card Lending", "deposits"], ["card   lending", "wealth"]
    ) == approx(1 / 3)


def test_business_line_overlap_one_shared_label():
    # A = {card lending}; B = {card lending, wealth}; ∩=1, ∪=2; jaccard=1/2.
    assert business_line_overlap(
        ["Card Lending"], ["card lending", "wealth"]
    ) == approx(0.5)


def test_business_line_overlap_empty_both_returns_none():
    assert business_line_overlap([], []) is None


def test_business_line_overlap_disjoint_returns_zero():
    assert business_line_overlap(["a"], ["b"]) == 0.0


# ---------------------------------------------------------------------------
# macro_driver_overlap
# ---------------------------------------------------------------------------

def test_macro_driver_overlap_spec_example():
    assert macro_driver_overlap(
        ["policy_rates", "credit_growth"], ["policy_rates", "liquidity"]
    ) == approx(1 / 3)


def test_macro_driver_overlap_unknown_token_raises_with_token():
    raised = False
    msg = ""
    try:
        macro_driver_overlap(["policy_rates", "totally_made_up"], [])
    except ValueError as e:
        raised = True
        msg = str(e)
    assert raised
    assert "totally_made_up" in msg


def test_macro_driver_overlap_both_empty_returns_none():
    assert macro_driver_overlap([], []) is None


def test_macro_driver_overlap_disjoint_returns_zero():
    assert macro_driver_overlap(
        ["policy_rates"], ["liquidity"]
    ) == 0.0


# ---------------------------------------------------------------------------
# market_factor_overlap
# ---------------------------------------------------------------------------

def test_market_factor_overlap_identical_direction_is_one():
    assert market_factor_overlap(
        {"rates_beta": 0.5, "credit_beta": 0.5},
        {"rates_beta": 0.5, "credit_beta": 0.5},
    ) == approx(1.0)


def test_market_factor_overlap_orthogonal_is_zero():
    assert market_factor_overlap(
        {"rates_beta": 1.0, "credit_beta": 0.0},
        {"rates_beta": 0.0, "credit_beta": 1.0},
    ) == approx(0.0)


def test_market_factor_overlap_zero_vector_returns_none():
    assert market_factor_overlap({}, {"rates_beta": 0.5}) is None
    assert market_factor_overlap({"rates_beta": 0.5}, {}) is None
    assert market_factor_overlap({}, {}) is None
    # Mapping of all-zero entries is also a zero vector.
    assert market_factor_overlap({"rates_beta": 0.0}, {"rates_beta": 0.5}) is None


def test_market_factor_overlap_cosine_in_unit_interval():
    a = {"rates_beta": 0.7, "credit_beta": 0.3, "vol_beta": -0.2}
    b = {"rates_beta": 0.4, "credit_beta": 0.6, "vol_beta": -0.1}
    v = market_factor_overlap(a, b)
    assert v is not None
    assert -1.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# ownership_hierarchy_report
# ---------------------------------------------------------------------------

def test_ownership_hierarchy_manager_vehicle_pair_across_slices():
    members_a = [
        {"security_id": "SYN_MGR", "entity_role": "MANAGER",
         "parent_security_id": None},
        {"security_id": "SYN_OC1", "entity_role": "OPERATING_COMPANY",
         "parent_security_id": None},
    ]
    members_b = [
        {"security_id": "SYN_BDC", "entity_role": "VEHICLE",
         "parent_security_id": "SYN_MGR"},
        {"security_id": "SYN_OC2", "entity_role": "OPERATING_COMPANY",
         "parent_security_id": None},
    ]
    rep = ownership_hierarchy_report(members_a, members_b)

    pairs = rep["manager_vehicle_pairs"]
    assert len(pairs) == 1, f"expected exactly one manager-vehicle pair, got {pairs}"
    pair = pairs[0]
    assert pair["manager"] == "SYN_MGR"
    assert pair["vehicle"] == "SYN_BDC"
    assert pair["in_a"] is True
    assert pair["in_b"] is True
    # The manager appears only as a manager on side A and only as a vehicle's
    # parent on side B; it does not appear as a member dict on side B, so the
    # raw shared-managers / shared-vehicles intersection is empty. The
    # manager_vehicle_pairs list still surfaces the cross-slice relationship.
    assert rep["shared_managers"] == []
    assert rep["shared_vehicles"] == []
    assert "never merged" in rep["note"]


def test_ownership_hierarchy_pair_observed_in_one_side_only():
    members_a = [
        {"security_id": "SYN_BDC", "entity_role": "VEHICLE",
         "parent_security_id": "SYN_MGR"},
    ]
    members_b = []
    rep = ownership_hierarchy_report(members_a, members_b)
    assert len(rep["manager_vehicle_pairs"]) == 1
    pair = rep["manager_vehicle_pairs"][0]
    assert pair["in_a"] is True
    assert pair["in_b"] is False
    # Shared lists are empty because the relationship was only on side A.
    assert rep["shared_managers"] == []
    assert rep["shared_vehicles"] == []


def test_ownership_hierarchy_empty_inputs():
    rep = ownership_hierarchy_report([], [])
    assert rep["manager_vehicle_pairs"] == []
    assert rep["shared_managers"] == []
    assert rep["shared_vehicles"] == []
    assert "never merged" in rep["note"]


# ---------------------------------------------------------------------------
# overlap_report — dimension results
# ---------------------------------------------------------------------------

def _slice(slice_id, *, business_lines=None, macro_drivers=None, market_factors=None,
           members=None, securities=None, weights=None):
    return {
        "slice_id": slice_id,
        "securities": list(securities or []),
        "weights": weights,
        "business_lines": list(business_lines or []),
        "macro_drivers": list(macro_drivers or []),
        "market_factors": market_factors,
        "members": list(members or []),
    }


def test_overlap_report_security_dimension():
    a = _slice("a", securities=["SYN_A", "SYN_B"],
               weights={"SYN_A": 0.6, "SYN_B": 0.4})
    b = _slice("b", securities=["SYN_B", "SYN_C"],
               weights={"SYN_B": 0.5, "SYN_C": 0.5})
    rep = overlap_report(a, b)
    sec = rep["dimensions"]["SECURITY"]
    assert sec["jaccard"] == approx(1 / 3)
    assert sec["weighted"] == approx(0.4)  # min(0.4, 0.5) / 1.0 normalized = 0.4
    assert sec["shared"] == ["SYN_B"]


def test_overlap_report_business_line_dimension():
    a = _slice("a", business_lines=["card lending", "deposits"])
    b = _slice("b", business_lines=["Card Lending", "wealth"])
    rep = overlap_report(a, b)
    bl = rep["dimensions"]["BUSINESS_LINE"]
    # A = {card lending, deposits}, B = {card lending, wealth}; ∩=1, ∪=3.
    assert bl["jaccard"] == approx(1 / 3)
    assert bl["shared"] == ["card lending"]


def test_overlap_report_macro_driver_dimension():
    a = _slice("a", macro_drivers=["policy_rates", "credit_growth"])
    b = _slice("b", macro_drivers=["policy_rates", "liquidity"])
    rep = overlap_report(a, b)
    md = rep["dimensions"]["MACRO_DRIVER"]
    assert md["jaccard"] == approx(1 / 3)
    assert md["shared"] == ["policy_rates"]


def test_overlap_report_market_factor_dimension():
    a = _slice("a", market_factors={"rates_beta": 0.5})
    b = _slice("b", market_factors={"rates_beta": 0.5, "credit_beta": 0.5})
    rep = overlap_report(a, b)
    mf = rep["dimensions"]["MARKET_FACTOR"]
    # cos( (0.5,0) , (0.5,0.5) ) = 0.5 / (0.5 * sqrt(0.5)) = sqrt(0.5) ≈ 0.7071
    assert mf["cosine"] == approx(0.70710678, rel=1e-6)


def test_overlap_report_ownership_hierarchy_dimension():
    a = _slice("a", members=[
        {"security_id": "SYN_MGR", "entity_role": "MANAGER",
         "parent_security_id": None},
    ])
    b = _slice("b", members=[
        {"security_id": "SYN_BDC", "entity_role": "VEHICLE",
         "parent_security_id": "SYN_MGR"},
    ])
    rep = overlap_report(a, b)
    hier = rep["dimensions"]["OWNERSHIP_HIERARCHY"]
    assert hier["manager_vehicle_pairs"][0]["manager"] == "SYN_MGR"
    assert hier["manager_vehicle_pairs"][0]["vehicle"] == "SYN_BDC"
    # Manager is a member only on side A; vehicle is a member only on side B.
    assert hier["shared_managers"] == []
    assert hier["shared_vehicles"] == []


def test_overlap_report_independence_shared_securities():
    a = _slice("a", securities=["SYN_X", "SYN_Y"])
    b = _slice("b", securities=["SYN_Y", "SYN_Z"])
    rep = overlap_report(a, b)
    assert rep["independence_note"] == "SHARED_SECURITIES"


def test_overlap_report_independence_shared_drivers_only():
    a = _slice("a", securities=["SYN_X"], macro_drivers=["policy_rates"])
    b = _slice("b", securities=["SYN_Z"], macro_drivers=["policy_rates"])
    rep = overlap_report(a, b)
    assert rep["independence_note"] == "SHARED_DRIVERS_ONLY"


def test_overlap_report_independence_shared_factors_only():
    a = _slice("a", securities=["SYN_X"],
               market_factors={"rates_beta": 1.0})
    b = _slice("b", securities=["SYN_Z"],
               market_factors={"rates_beta": 0.8, "credit_beta": 0.6})
    rep = overlap_report(a, b)
    # cos = 0.8 / (1.0 * 1.0) = 0.8 > 0.5; securities disjoint; drivers absent.
    assert rep["dimensions"]["MARKET_FACTOR"]["cosine"] == approx(0.8)
    assert rep["independence_note"] == "SHARED_FACTORS_ONLY"


def test_overlap_report_independence_independent():
    a = _slice("a", securities=["SYN_X"], macro_drivers=["policy_rates"],
               market_factors={"rates_beta": 1.0})
    b = _slice("b", securities=["SYN_Z"], macro_drivers=["liquidity"],
               market_factors={"credit_beta": 1.0})
    rep = overlap_report(a, b)
    assert rep["independence_note"] == "INDEPENDENT"


def test_overlap_report_independence_insufficient_data():
    a = _slice("a")
    b = _slice("b")
    rep = overlap_report(a, b)
    assert rep["independence_note"] == "INSUFFICIENT_DATA"


def test_overlap_report_authority_is_literal_false():
    a = _slice("a")
    b = _slice("b")
    rep = overlap_report(a, b)
    auth = rep["authority"]
    assert auth == {
        "is_score": False,
        "is_membership_signal": False,
        "may_rank": False,
        "may_gate": False,
        "may_size": False,
        "may_trade": False,
    }
    # No key named like a score anywhere in the report.
    _assert_no_score_or_rank_keys(rep)


def _assert_no_score_or_rank_keys(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_low = str(k).lower()
            assert k_low not in {"score", "rank", "attractiveness", "composite"}, (
                f"Forbidden key {k!r} at {path + (k,)}"
            )
            _assert_no_score_or_rank_keys(v, path + (k,))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _assert_no_score_or_rank_keys(v, path + (i,))


# ---------------------------------------------------------------------------
# basket_state_context
# ---------------------------------------------------------------------------

def test_basket_state_context_semantic_only_no_candidates_no_incumbents():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=[],
        candidate_members=[],
        pit_validated_ids=[],
        identity_validated_ids=[],
        exposure_measured_ids=[],
    )
    assert rep["slice_id"] == "synthetic_slice"
    assert rep["posture"] == "SEMANTIC_ONLY"
    assert rep["membership_state"] == "NONE"
    assert rep["incumbent_basket_ids"] == []
    assert rep["member_count"] == 0
    assert rep["held"] == []
    assert rep["authority"] == {"may_admit": False, "may_mutate_existing_basket": False}


def test_basket_state_context_broad_context_available_incumbents_only():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=["regional_banks", "payments_fintech"],
        candidate_members=[],
        pit_validated_ids=[],
        identity_validated_ids=[],
        exposure_measured_ids=[],
    )
    assert rep["posture"] == "BROAD_CONTEXT_AVAILABLE"
    assert rep["membership_state"] == "NONE"
    assert rep["incumbent_basket_ids"] == ["payments_fintech", "regional_banks"]


def test_basket_state_context_research_candidate_no_pit():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=["regional_banks"],
        candidate_members=[
            {"security_id": "SYN_A"},
            {"security_id": "SYN_B"},
        ],
        pit_validated_ids=[],
        identity_validated_ids=[],
        exposure_measured_ids=[],
    )
    assert rep["posture"] == "RESEARCH_CANDIDATE"
    assert rep["membership_state"] == "CURRENT_MEMBERSHIP_ONLY"
    # Each candidate misses all three, in exposure → identity → pit order.
    states_seen = [h["state"] for h in rep["held"]]
    assert states_seen == [
        "HELD_MISSING_EXPOSURE", "HELD_MISSING_IDENTITY", "HELD_MISSING_PIT",
        "HELD_MISSING_EXPOSURE", "HELD_MISSING_IDENTITY", "HELD_MISSING_PIT",
    ]


def test_basket_state_context_research_candidate_pit_incomplete():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=[],
        candidate_members=[
            {"security_id": "SYN_A"},  # PIT only
            {"security_id": "SYN_B"},  # nothing
        ],
        pit_validated_ids=["SYN_A"],
        identity_validated_ids=[],
        exposure_measured_ids=[],
    )
    assert rep["posture"] == "RESEARCH_CANDIDATE"
    assert rep["membership_state"] == "PIT_MEMBERSHIP_INCOMPLETE"


def test_basket_state_context_research_candidate_pit_validated_but_missing_exposure():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=[],
        candidate_members=[
            {"security_id": "SYN_A"},
            {"security_id": "SYN_B"},
        ],
        pit_validated_ids=["SYN_A", "SYN_B"],
        identity_validated_ids=["SYN_A", "SYN_B"],
        exposure_measured_ids=["SYN_A"],  # SYN_B missing exposure
    )
    # All PIT-validated ⇒ membership_state PIT_MEMBERSHIP_VALIDATED.
    # But SYN_B lacks exposure, so posture stays RESEARCH_CANDIDATE.
    assert rep["posture"] == "RESEARCH_CANDIDATE"
    assert rep["membership_state"] == "PIT_MEMBERSHIP_VALIDATED"
    states = sorted({h["state"] for h in rep["held"]})
    assert states == ["HELD_MISSING_EXPOSURE"]


def test_basket_state_context_candidate_ready_for_owner_review():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=["regional_banks"],
        candidate_members=[
            {"security_id": "SYN_A"},
            {"security_id": "SYN_B"},
        ],
        pit_validated_ids=["SYN_A", "SYN_B"],
        identity_validated_ids=["SYN_A", "SYN_B"],
        exposure_measured_ids=["SYN_A", "SYN_B"],
    )
    assert rep["posture"] == "CANDIDATE_READY_FOR_OWNER_REVIEW"
    assert rep["membership_state"] == "PIT_MEMBERSHIP_VALIDATED"
    assert rep["held"] == []
    assert rep["authority"]["may_admit"] is False  # admission belongs to owner


def test_basket_state_context_held_missing_exposure():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=[],
        candidate_members=[{"security_id": "SYN_A"}],
        pit_validated_ids=[],
        identity_validated_ids=["SYN_A"],
        exposure_measured_ids=[],
    )
    states = [h["state"] for h in rep["held"]]
    assert "HELD_MISSING_EXPOSURE" in states
    assert "HELD_MISSING_PIT" in states


def test_basket_state_context_held_missing_identity():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=[],
        candidate_members=[{"security_id": "SYN_A"}],
        pit_validated_ids=["SYN_A"],
        identity_validated_ids=[],
        exposure_measured_ids=["SYN_A"],
    )
    states = [h["state"] for h in rep["held"]]
    assert "HELD_MISSING_IDENTITY" in states
    assert "HELD_MISSING_EXPOSURE" not in states
    assert "HELD_MISSING_PIT" not in states


def test_basket_state_context_held_missing_pit():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=[],
        candidate_members=[{"security_id": "SYN_A"}],
        pit_validated_ids=[],
        identity_validated_ids=["SYN_A"],
        exposure_measured_ids=["SYN_A"],
    )
    states = [h["state"] for h in rep["held"]]
    assert "HELD_MISSING_PIT" in states
    assert "HELD_MISSING_EXPOSURE" not in states
    assert "HELD_MISSING_IDENTITY" not in states


def test_basket_state_context_never_admits():
    # Exhaustive small grid: ADMITTED must never appear anywhere in any
    # basket_state_context output, regardless of candidate/incumbent mix.
    grids = [
        # (incumbents, candidates, pit, identity, exposure)
        ([], [], [], [], []),
        (["inc_a"], [], [], [], []),
        ([], [{"security_id": "SYN_X"}], [], [], []),
        (["inc_a"], [{"security_id": "SYN_X"}], [], [], []),
        ([], [{"security_id": "SYN_X"}], ["SYN_X"], ["SYN_X"], ["SYN_X"]),
        (["inc_a"], [{"security_id": "SYN_X"}], ["SYN_X"], ["SYN_X"], ["SYN_X"]),
        (["inc_a", "inc_b"], [
            {"security_id": "SYN_X"}, {"security_id": "SYN_Y"},
        ], ["SYN_X"], ["SYN_Y"], ["SYN_X", "SYN_Y"]),
    ]
    for incumbents, candidates, pit, ident, exp in grids:
        rep = basket_state_context(
            "synthetic_slice",
            incumbent_basket_ids=incumbents,
            candidate_members=candidates,
            pit_validated_ids=pit,
            identity_validated_ids=ident,
            exposure_measured_ids=exp,
        )
        s = repr(rep)
        assert "ADMITTED" not in s, f"ADMITTED must never appear: {rep}"
        # No key named like a score anywhere in the report either.
        _assert_no_score_or_rank_keys(rep)


def test_basket_state_context_authority_is_literal_false():
    rep = basket_state_context(
        "synthetic_slice",
        incumbent_basket_ids=["regional_banks"],
        candidate_members=[{"security_id": "SYN_A"}],
        pit_validated_ids=["SYN_A"],
        identity_validated_ids=["SYN_A"],
        exposure_measured_ids=["SYN_A"],
    )
    assert rep["authority"] == {
        "may_admit": False,
        "may_mutate_existing_basket": False,
    }