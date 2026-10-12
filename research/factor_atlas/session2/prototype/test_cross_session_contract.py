"""S1 PIT index candidate vs S2 inferred capital-pressure: STRUCTURAL non-join.

The source-shape fixture below is fabricated. It models fields in S1 native
factor_atlas_read.v1 (PR #8680), not the original rights/identity owner.
"""
from __future__ import annotations

from dataclasses import replace, asdict
from datetime import datetime
from hashlib import sha256
import copy
import json
import pytest

import pressure as m
from test_window_pressure import calc, make, groups
import window_pressure as wp
from cross_session_contract import review_s1_s2, fingerprint_s1


def s1(*, roster=("A","B"), mode="PIT_AS_KNOWN", basket="F1",
       source_date="2026-06-01", source_basis="tradj",
       source_status="READY", caller_rights=False):
    root={
        "schema":"factor_atlas_read.v1",
        "basket_id":basket,
        "release_state":"CANDIDATE_NOT_ADMITTED",
        "input_admission":"REFERENCE_CHECKS_ONLY_NOT_RECEIPT_AUTHENTICATION",
        "evidence_kind":"SYNTHETIC_FIXTURE",
        "history_mode":mode,
        "as_of":"2026-06-01",
        "status":source_status,
        "method":{"return_basis":source_basis,"currency":"USD","session":"regular",
                  "rebalance":"monthly","weighting":"equal",
                  "between_rebalances":"drift"},
        "source_refs":{"cohorts":[{"effective_close":source_date,
                                     "members":list(roster),
                                     "snapshot_ref":"synthetic:unattested"}],
                       "calendar":"synthetic:calendar","rights":"synthetic:rights"},
        "authority":{"may_rank":caller_rights,"may_gate":False,
                     "may_size":False,"may_trade":False,
                     "may_publish":False,"may_escalate":False},
    }
    root["result_digest"]=fingerprint_s1(root)
    return root


def pit_window(**kwargs):
    bars,segs,start,end=make()
    roster=[replace(g,basis="point_in_time") for g in groups()]
    params=dict(start_utc_s=start,end_utc_s=end,cutoff_utc_s=end+2,
                config=replace(m.disclosed_core_config(),min_returns=2))
    params.update(kwargs)
    return wp.measure_windows(bars,roster,segs,**params)


def view(x=None,y=None,**kwargs):
    return review_s1_s2(x if x is not None else s1(),
                        y if y is not None else pit_window(),
                        factor_ref="F1",**kwargs)


def test_source_matching_synthetic_pit_roster_still_cannot_admit_numeric_join():
    out=view()
    assert out.schema=="factor_atlas.s1_s2_boundary_review.v1"
    assert out.s1_mode=="PIT_AS_KNOWN"
    assert out.s1_return_basis=="tradj"
    assert out.s2_required_source_basis=="unadjusted/USD"
    assert "S2_RAW_BASIS_NOT_ATTESTED_BY_WINDOW_PROJECTION" in out.reasons
    assert out.member_id_sets_match is True
    assert out.compared_member_count==2
    assert "TRADJ_RETURN_VS_UNADJUSTED_NOTIONAL" in out.reasons
    assert "S1_PIT_SELECTION_RECEIPT_NOT_EXPOSED" in out.reasons
    assert "REAL_SOURCE_BASIS_RIGHTS_NOT_ADMITTED" in out.reasons
    assert out.status=="HOLD_SEPARATE_READ_MODELS"
    assert out.allow_joint_numeric_arithmetic is False
    assert out.allow_use_s1_prices_for_s2_notional is False
    assert out.pit_roster_verified is False
    assert out.customer_publishable is False
    assert out.market_pilot_admitted is False
    assert out.authority==m.AUTHORITY


def test_current_roster_is_not_promoted_to_historical_pit():
    out=view(s1(mode="CURRENT_ROSTER"))
    assert "S1_CURRENT_ROSTER_NOT_PIT" in out.reasons
    assert out.pit_roster_verified is False
    assert out.member_id_sets_match is None


def test_wrong_basket_identity_fails_closed_not_silently_mapped():
    out=view(s1(basket="OTHER_FACTOR"))
    assert "FACTOR_ID_MISMATCH" in out.reasons
    assert out.member_id_sets_match is None


def test_roster_mismatch_is_visible_and_denies_member_comparability():
    v=view(s1(roster=("A","C")))
    assert v.member_id_sets_match is False
    assert "SELECTED_MEMBER_SET_MISMATCH" in v.reasons
    assert v.pit_roster_verified is False


def test_duplicate_member_ids_cannot_fake_population_coverage():
    with pytest.raises(ValueError,match="duplicate_cohort_member"):
        view(s1(roster=("A","A")))


def test_s1_monthly_effective_close_is_not_automatically_reused_in_june():
    v=view(s1(source_date="2026-05-29"))
    assert "NO_SAME_SESSION_COHORT_OBSERVATION" in v.reasons
    assert v.member_id_sets_match is None


def test_two_conflicting_cohorts_at_one_clock_cannot_select_first():
    x=s1()
    x["source_refs"]["cohorts"].append(
        {"effective_close":"2026-06-01","members":["A","C"],"snapshot_ref":"synthetic:other"})
    x["result_digest"]=fingerprint_s1(x)
    with pytest.raises(ValueError,match="duplicate_owner_cohort_at_clock"):
        view(x)


def test_s1_tradj_total_return_basis_is_not_a_minute_ohlcv_basis():
    with pytest.raises(ValueError,match="invalid_s1_return_basis"):
        view(s1(source_basis="unadjusted/USD"))
    with pytest.raises(ValueError,match="invalid_s1_return_basis"):
        view(s1(source_basis="vwap_if_present"))


def test_provided_s1_source_ready_flag_is_not_external_market_admission():
    r=view(s1(source_status="READY"))
    assert r.status=="HOLD_SEPARATE_READ_MODELS"
    assert not r.pit_roster_verified and not r.customer_publishable


def test_source_pretending_to_authorize_publishing_refused():
    with pytest.raises(ValueError,match="s1_authority_overclaim"):
        view(s1(caller_rights=True))


def test_wrong_candidate_schema_cannot_be_accepted_as_s1():
    x=s1()
    x["schema"]="factor_atlas_read.v2"
    x["result_digest"]=fingerprint_s1(x)
    with pytest.raises(ValueError,match="s1_schema"):
        view(x)


def test_s1_tampered_source_dollar_or_roster_receipt_caught_by_digest():
    x=s1()
    x["source_refs"]["cohorts"][0]["members"]=["A","C"]
    with pytest.raises(ValueError,match="s1_result_digest"):
        view(x)
    x=s1()
    x["method"]["return_basis"]="unadjusted/USD"
    with pytest.raises(ValueError,match="s1_result_digest"):
        view(x)


def test_s2_internal_authority_forgery_refused():
    with pytest.raises(ValueError,match="s2_authority"):
        view(y=replace(pit_window(),authority=(("may_trade",True),)))


def test_s2_corrected_history_is_not_live_pit_measurement():
    v=view(y=pit_window(mode="corrected_history"))
    assert "S2_CORRECTED_HISTORY_NOT_AS_OBSERVED" in v.reasons
    assert v.market_pilot_admitted is False


def test_s2_factor_without_pit_membership_cannot_equal_source_owner_pit():
    r=pit_window()
    f=replace(r.factors[0],membership_basis="current_cohort")
    v=view(y=replace(r,factors=(f,*r.factors[1:])))
    assert "S2_ROSTER_NOT_PIT" in v.reasons
    assert v.member_id_sets_match is None


def test_s1_unknown_members_are_not_joined_to_the_same_ticker_label():
    x=s1(roster=("A", "OTHER_VENDOR:A"))
    v=view(x)
    assert v.member_id_sets_match is False
    assert "SELECTED_MEMBER_SET_MISMATCH" in v.reasons


def test_unmatched_s2_factor_has_no_accidental_first_factor_fallback():
    v=review_s1_s2(s1(basket="OTHER"),calc(),factor_ref="OTHER")
    assert "S2_FACTOR_NOT_IN_WINDOW" in v.reasons
    assert v.member_id_sets_match is None


def test_identities_are_permutation_stable_for_owner_provided_member_order():
    a=view(s1(roster=("A","B")))
    b=view(s1(roster=("B","A")))
    assert a.reasons==b.reasons
    assert a.member_id_sets_match==b.member_id_sets_match
    assert a.input_digest==b.input_digest


def test_spoofed_s1_digest_not_authority_or_canonical_receipt():
    x=s1()
    x["evidence_kind"]="RETAINED_OWNER_INPUT"
    x["result_digest"]=fingerprint_s1(x)
    r=view(x)
    assert "UNVERIFIED_S1_SOURCE_CUSTODY" in r.reasons
    assert not r.customer_publishable


def test_cross_session_output_does_not_include_prices_returns_or_trade_sizing():
    r=view()
    fields=json.dumps(asdict(r))
    assert "predicted_return" not in fields
    assert "signed_hedge_fund_flow" not in fields
    assert "TRADE" not in r.status
    assert r.allow_joint_numeric_arithmetic is False


def test_matched_roster_with_unadmitted_source_references_is_still_not_pit_proof():
    x=s1()
    x["source_refs"]["rights"]="synthetic:pretend-entitlement-granted"
    x["source_refs"]["cohorts"][0]["snapshot_ref"]="synthetic:certified-looking-pit"
    x["result_digest"]=fingerprint_s1(x)
    r=view(x)
    assert r.member_id_sets_match is True
    assert r.pit_roster_verified is False
    assert r.source_receipts_authenticated is False
    assert r.data_use_rights_proven is False
    assert r.source_measurement_basis_compatible is False
    assert r.status=="HOLD_SEPARATE_READ_MODELS"


def test_s2_pressure_digest_is_distinct_from_s1_owner_result_digest():
    x=s1()
    y=pit_window()
    result=view(x,y)
    assert x["result_digest"]!=result.input_digest
    assert result.s2_required_source_basis=="unadjusted/USD"
    assert "S2_RAW_BASIS_NOT_ATTESTED_BY_WINDOW_PROJECTION" in result.reasons


def test_s2_missing_full_gross_stays_not_joinable_to_s1_total_return():
    from test_window_pressure import make
    bars,segs,start,end=make()
    bars=[b for b in bars if not (b.security_id=="A" and b.start_utc_s==start+60)]
    group=[replace(g,basis="point_in_time") for g in groups()]
    partial=wp.measure_windows(bars,group,segs,start_utc_s=start,
        end_utc_s=end,cutoff_utc_s=end+2,
        config=replace(m.disclosed_core_config(),min_returns=2))
    assert partial.factors[0].full_gross_usd is None
    result=view(y=partial)
    assert not result.allow_joint_numeric_arithmetic
    assert "REAL_SOURCE_BASIS_RIGHTS_NOT_ADMITTED" in result.reasons


def test_s1_result_digest_binds_utf8_semantics_but_not_source_authentication():
    x=s1()
    x["source_refs"]["rights"]="synthetic:所有者"
    x["result_digest"]=fingerprint_s1(x)
    r=view(x)
    assert r.status=="HOLD_SEPARATE_READ_MODELS"
    assert not r.source_receipts_authenticated
    x["source_refs"]["rights"]="synthetic:modified"
    with pytest.raises(ValueError,match="s1_result_digest"):
        view(x)


def test_s1_source_date_after_s2_is_not_selected_as_historical_pit():
    out=view(s1(source_date="2026-06-04"))
    assert "NO_SAME_SESSION_COHORT_OBSERVATION" in out.reasons
    assert out.member_id_sets_match is None


def test_s1_inconsistent_external_admission_claim_is_rejected():
    x=s1()
    x["release_state"]="READY_FOR_CUSTOMER"
    x["result_digest"]=fingerprint_s1(x)
    with pytest.raises(ValueError,match="s1_unqualified_admission_state"):
        view(x)


@pytest.mark.parametrize("missing_key",["cohorts","rights"])
def test_original_s1_reduced_projection_missing_source_field_never_proves_pit(missing_key):
    x=s1()
    del x["source_refs"][missing_key]
    x["result_digest"]=fingerprint_s1(x)
    if missing_key=="cohorts":
        with pytest.raises(ValueError,match="s1_cohorts"):
            view(x)
    else:
        r=view(x)
        assert not r.data_use_rights_proven
        assert r.market_pilot_admitted is False


def test_actual_held_s1_current_roster_sample_is_a_negative_shape_witness():
    # This module's consumed S1 fixture shape is pinned by source head.
    # The actual ~5KB S1 native sample is only inspected in the local
    # ignored cross-owner reproduction log, not mirrored into the PR.
    x=s1(mode="CURRENT_ROSTER",basket="mag7",
         source_date="2026-01-28",roster=("SEC:US-XNYS-AAA",
              "SEC:US-XNYS-BBB","SEC:US-XNYS-CCC"))
    r=view(x)
    assert "S1_CURRENT_ROSTER_NOT_PIT" in r.reasons
    assert "FACTOR_ID_MISMATCH" in r.reasons
    assert "NO_SAME_SESSION_COHORT_OBSERVATION" in r.reasons
    assert not r.allow_use_s1_prices_for_s2_notional
