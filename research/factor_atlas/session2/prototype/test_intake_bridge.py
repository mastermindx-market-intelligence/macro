"""S2-P2: source-shaped record -> existing BVC/window geometry, synthetic only.

Never grants source admission; its "OWNER_UNVERIFIED" setting only inspects
metadata and never runs the actual factor-pressure calculation.
"""
from __future__ import annotations
from dataclasses import replace,asdict
from decimal import Decimal
import pytest

import pressure as m
from source_preflight import preflight
from test_source_preflight import T,NANO,COHORT,scope,claim
from intake_bridge import MinuteEnvelope, preview_intake

SEG=scope().segments[0]
CUT=(T+240)*NANO


def records():
    return tuple(MinuteEnvelope(
        claim(sid,i),
        float(100+i),float(10),float(100+i)) for sid in COHORT for i in range(3))


def memberships():
    return (m.Membership("F_TECH","v1","point_in_time",
                         ("AAPL","MSFT","NVDA")),
            m.Membership("F_ETF","v1","point_in_time",("SPY",)))


def run(rows=None, *, origin="SYNTHETIC_FIXTURE", cutoff_ns=CUT,
        groups=None, start=T, end=T+180):
    return preview_intake(
        scope(cutoff_s=T+240),records() if rows is None else rows,
        memberships() if groups is None else groups,
        config=replace(m.disclosed_core_config(),min_returns=2),
        start_utc_s=start,end_utc_s=end,cutoff_utc_ns=cutoff_ns,
        input_class=origin)


def test_complete_synthetic_owner_shape_projects_without_admitting_market_data():
    v=run()
    assert v.status=="NOT_ADMITTED"
    assert v.stage=="SYNTHETIC_WINDOW_PREVIEW"
    assert v.source_quality=="NOT_ADMITTED"
    assert v.source_authenticated is False
    assert v.source_rights_verified is False
    assert v.market_pilot_admitted is False
    assert v.may_execute_market_pilot is False
    assert v.customer_publishable is False
    assert v.preflight.metadata_complete and v.preflight.expected_cells==12
    assert v.preflight.missing_cells==0
    assert v.window is not None
    assert v.window.authority==m.AUTHORITY
    assert [x.factor_id for x in v.window.factors]==["F_ETF","F_TECH"]
    assert v.window.factors[0].full_gross_usd==pytest.approx(3030)
    assert v.window.factors[1].full_gross_usd==pytest.approx(9090)
    assert not any(flag for _,flag in v.authority)
    assert v.normalized_bar_count==12
    assert v.earliest_bar_available_utc_s==T+61
    assert v.latest_bar_available_utc_s==T+181


def test_valid_looking_live_owner_claims_are_not_run_as_real_pilot():
    v=run(origin="OWNER_UNVERIFIED")
    assert v.preflight.owner_review_candidate is True
    assert v.preflight.metadata_complete is True
    assert v.stage=="OWNER_ADMISSION_REQUIRED"
    assert v.window is None
    assert v.normalized_bar_count==0
    assert v.source_quality=="NOT_ADMITTED"
    assert not v.may_execute_market_pilot


def test_all_absent_minutes_are_missing_not_measured_zero():
    v=run([])
    assert v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"
    assert v.preflight.missing_cells==12 and v.preflight.unknown_cells==12
    assert v.window is None
    assert v.normalized_bar_count==0


def test_absent_one_security_minute_blocks_full_preview_not_zero_fill():
    rows=[x for x in records() if not
          (x.claim.security_id=="NVDA" and x.claim.start_utc_s==T+60)]
    v=run(rows)
    assert v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"
    assert v.preflight.missing_cells==1
    assert v.window is None
    assert v.preflight.unknown_cells>=1


def test_source_unadjusted_request_does_not_elevate_missing_basis():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,basis_id=None))
    v=run(rows)
    assert v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"
    assert v.window is None
    assert any("MONETARY_BASIS_UNPROVEN" in e.reasons
               for e in v.preflight.exceptions)


def test_owner_reader_receipt_is_ceiled_to_next_second_not_relabelled_bar_close():
    v=run()
    assert v.earliest_bar_available_utc_s==T+61
    assert v.latest_bar_available_utc_s==T+181
    assert v.window.input_digest is not None


def test_subsecond_cutoff_preserves_owner_microsecond_reader_ceiling():
    # All self-described receipt metadata are known by this subsecond cutoff,
    # but WindowPressure uses seconds: a later second is not backdated.
    v=run(cutoff_ns=(T+180)*NANO+3000)
    assert v.preflight.metadata_complete
    assert v.stage=="CUTOFF_PRECISION_WITHHELD"
    assert v.window is None


def test_unknown_price_volume_or_vwap_refused_not_published():
    for field,number in (("close",0.),("close",float("nan")),
                         ("volume",-1.),("volume",float("inf")),
                         ("vwap",0.)):
        rows=list(records())
        rows[0]=replace(rows[0],**{field:number})
        with pytest.raises(ValueError,match="bar|close|volume|vwap"):
            run(rows)


def test_present_zero_volume_needs_explicit_zero_state():
    rows=list(records())
    rows[0]=replace(rows[0],volume=0.)
    with pytest.raises(ValueError,match="zero_state"):
        run(rows)


def test_explicit_zero_volume_is_measured_activity_not_missing_cell():
    rows=list(records())
    rows[0]=replace(rows[0],volume=0.,
        claim=replace(rows[0].claim,value_state="EXPLICIT_ZERO_VOLUME"))
    v=run(rows)
    assert v.stage=="SYNTHETIC_WINDOW_PREVIEW"
    assert v.preflight.explicit_zero_cells==1
    assert v.preflight.missing_cells==0
    assert v.window.factors[0].full_gross_usd==pytest.approx(3030)
    assert v.window.factors[1].full_gross_usd==pytest.approx(8090)


def test_different_quote_trade_basis_is_not_recoded_as_price_adjustment():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
            basis_id="split_adjusted/USD",response_adjusted="TRUE"))
    v=run(rows)
    assert not v.preflight.metadata_complete
    assert v.window is None
    assert v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"


def test_duplicate_selected_revision_is_rejected_by_incumbent_metadata_logic():
    a=records()[0]
    with pytest.raises(ValueError,match="duplicate_slot"):
        run(list(records())+[replace(a,claim=replace(a.claim,source_revision_ref="CORR"))])


def test_negative_event_or_reversed_receipt_refuses():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
       source_receipt_utc_ns=rows[0].claim.end_utc_s*NANO-1))
    with pytest.raises(ValueError,match="source_before_bar_close"):
        run(rows)


def test_roster_must_not_be_promoted_from_current_cohort_to_pit():
    groups=(m.Membership("FACTOR","v1","current_cohort",COHORT),)
    with pytest.raises(ValueError,match="membership_requires_point_in_time"):
        run(groups=groups)


def test_noncohort_factor_member_is_refused():
    groups=(m.Membership("FACTOR","v1","point_in_time",("AAPL","FAKE")),)
    with pytest.raises(ValueError,match="member_outside_intake"):
        run(groups=groups)


def test_outside_window_extra_late_row_does_not_change_old_prefix():
    v=run()
    src=records()[0]
    future=replace(src,claim=replace(src.claim,start_utc_s=T+180,
                         end_utc_s=T+240,
                         source_receipt_utc_ns=(T+240)*NANO+1000,
                         reader_completed_utc_ns=(T+240)*NANO+2000),
                   close=-1.)
    assert run(list(records())+[future])==v


def test_ordering_of_owner_selected_claims_does_not_change_evidence_digest():
    a=run()
    b=run(tuple(reversed(records())))
    assert a==b and a.input_digest==b.input_digest


def test_arbitrary_origin_class_refused_not_promoted():
    with pytest.raises(ValueError,match="input_class"):
        run(origin="ADMITTED_REAL_MARKET")


def test_unqualified_rights_receipt_refuses_even_synthetic_projection():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
                      dataset_use_ref=None))
    v=run(rows)
    assert v.window is None and v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"


def test_source_proof_is_not_cryptographically_attested_by_input_hashes():
    v=run()
    assert v.preflight.owner_review_candidate
    assert "UNCHECKED_CUSTODY" in v.preflight.unverified_authorities
    assert "EXTERNAL_SOURCE_RIGHTS_UNPROVEN" in v.preflight.unverified_authorities
    assert v.knowledge_class=="SYNTHETIC_SOURCE_SHAPED_PREVIEW_NOT_MARKET_MEASUREMENT"
    assert "institutional_buying" not in str(asdict(v)).lower()


def test_complete_but_fake_sha_receipts_do_not_grant_source_quality():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
                         source_object_sha256="0"*64,
                         reader_receipt_sha256="0"*64,
                         rights_ref="UNVERIFIED:CLAIMED_FULL_RIGHTS"))
    v=run(rows)
    assert v.preflight.owner_review_candidate
    assert not v.source_authenticated and not v.source_rights_verified
    assert v.status=="NOT_ADMITTED" and not v.may_execute_market_pilot


def test_reader_completion_later_than_cutoff_withholds_preview():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
        source_receipt_utc_ns=(T+250)*NANO,
        reader_completed_utc_ns=(T+250)*NANO+1000))
    v=run(rows)
    assert v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"
    assert any("SOURCE_AFTER_CUTOFF" in e.reasons or
               "READER_AFTER_CUTOFF" in e.reasons
               for e in v.preflight.exceptions)
    assert v.window is None


def test_early_reader_receipt_cannot_precede_actual_source_response():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
          reader_completed_utc_ns=rows[0].claim.source_receipt_utc_ns-1))
    with pytest.raises(ValueError,match="reader_before_source"):
        run(rows)


def test_claimed_explicit_zero_but_positive_printed_volume_is_rejected():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
                                      value_state="EXPLICIT_ZERO_VOLUME"))
    with pytest.raises(ValueError,match="explicit_zero_state"):
        run(rows)


def test_same_security_monetary_basis_drift_stays_unqualified():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
                                basis_id="unadjusted/USD/action-v99"))
    v=run(rows)
    assert v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"
    assert any("MONETARY_BASIS_CONFLICT" in e.reasons for e in v.preflight.exceptions)


def test_same_security_listing_identity_drift_stays_unqualified():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
                                      listing_ref="NEW_UNVERIFIED_LISTING"))
    v=run(rows)
    assert v.stage=="INCOMPLETE_OR_UNPROVEN_INTAKE"
    assert any("LISTING_IDENTITY_CONFLICT" in e.reasons for e in v.preflight.exceptions)


def test_noninteger_nanosecond_asof_never_becomes_source_stamp():
    with pytest.raises(ValueError,match="timestamp"):
        run(cutoff_ns=True)
    with pytest.raises(ValueError,match="timestamp"):
        run(cutoff_ns="2026-06-01T09:35")


def test_outside_window_membership_side_effect_cannot_modify_predecessor():
    r=run()
    assert r.window.duplicated_gross_usd==0
    assert r.window.union_observed_gross_usd==pytest.approx(12120)
    assert r.window.sum_factor_observed_gross_usd==pytest.approx(12120)
    assert r.window.input_digest


def test_source_revision_mutation_changes_provenance_not_authority():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
                                      source_revision_ref="SYNTHETIC_NEW_REV"))
    result=run(rows)
    assert result.input_digest!=run().input_digest
    assert result.status=="NOT_ADMITTED"
    assert not any(flag for _,flag in result.authority)


def test_observation_metadata_changes_earlier_source_digest_without_forcing_a_trade():
    rows=list(records())
    rows[0]=replace(rows[0],claim=replace(rows[0].claim,
                              reader_receipt_sha256="f"*64))
    altered=run(rows)
    assert altered.preflight.input_digest!=run().preflight.input_digest
    assert altered.window is not None
    assert not altered.market_pilot_admitted


def test_corrected_retroactive_source_cannot_replace_current_slot_in_flight():
    rows=list(records())
    corrected=replace(rows[0],claim=replace(rows[0].claim,
                           source_revision_ref="LATER_CORRECTION"))
    with pytest.raises(ValueError,match="duplicate_slot"):
        run(rows+[corrected])


def test_input_dict_or_untyped_payload_is_not_accepted_as_owner_claim():
    rows=list(records())
    rows[0]=asdict(rows[0])
    with pytest.raises(ValueError,match="minute_envelope_required"):
        run(rows)
