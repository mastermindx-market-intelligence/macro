"""S2-P1 metadata census: all source decisions remain with incumbent owners."""
from dataclasses import replace
import pytest

import pressure as m
from source_preflight import (IntakeScope, MinuteClaim, preflight)

T=1780320600
NANO=1_000_000_000
COHORT=("AAPL","MSFT","NVDA","SPY")


def scope(*,cutoff_s=T+600,minutes=3,segments=None):
    seg=m.Segment("2026-06-01","RTH",T,T+minutes*60,
                  "CAL:RTH:2026-06-01:v1","FULL")
    return IntakeScope(COHORT,tuple(segments or (seg,)),cutoff_s*NANO)


def claim(symbol="AAPL",minute=0,**kw):
    start=T+minute*60
    end=start+60
    receipt=end*NANO+1000
    base={
        "security_id":symbol,
        "listing_ref":"canonical_listing:"+symbol+":PIT",
        "segment":scope().segments[0],
        "start_utc_s":start,
        "end_utc_s":end,
        "source_receipt_utc_ns":receipt,
        "reader_completed_utc_ns":receipt+1000,
        "source_object_sha256":"a"*64,
        "sealed_capture_prefix_sha256":"b"*64,
        "reader_receipt_sha256":"c"*64,
        "selection_receipt_sha256":"d"*64,
        "source_revision_ref":"rev:"+symbol+":"+str(minute),
        "owner_reader_ref":"engine/entry_radar/replay/terminal_minute_observations.py",
        "rights_ref":"research/licenses/MASSIVE_ENTITLEMENT_RECORD.md",
        "dataset_use_ref":"owner_dataset_use:equity_aggregates",
        "acquisition_role":"research_unadjusted",
        "request_adjusted":False,
        "response_adjusted":"FALSE",
        "basis_id":"unadjusted/USD/action-v1",
        "basis_receipt_sha256":"e"*64,
        "action_vintage_ref":"action-v1:owned",
        "volume_convention_ref":"owner:consolidated-volume-v1",
        "value_state":"PRESENT",
    }
    return MinuteClaim(**(base|kw))


def complete():
    return [claim(s,i) for s in COHORT for i in range(3)]


def test_absent_cohort_has_true_expected_denominator_and_no_admission():
    r=preflight(scope(),[])
    assert r.expected_cells==12 and r.represented_cells==0
    assert r.missing_cells==12 and r.metadata_complete is False
    assert r.status=="NOT_ADMITTED" and not any(v for _,v in r.authority)
    assert r.unknown_cells==12
    assert all(x.reason=="MISSING_SOURCE_MINUTE" for x in r.exceptions)
    assert r.coverage_ratio=="0"


def test_even_fully_filled_attested_claims_do_not_self_admit():
    r=preflight(scope(),complete())
    assert (r.expected_cells,r.represented_cells,r.missing_cells)==(12,12,0)
    assert r.metadata_complete and r.owner_review_candidate
    assert r.coverage_ratio=="1"
    assert r.status=="NOT_ADMITTED" and r.external_owner_admission_required
    assert not any(flag for _,flag in r.authority)
    assert "UNCHECKED_CUSTODY" in r.unverified_authorities


@pytest.mark.parametrize(("field","value","reason"),[
    ("acquisition_role","chart_adjusted","NOT_RESEARCH_UNADJUSTED"),
    ("request_adjusted",True,"NOT_RAW_REQUEST"),
    ("request_adjusted","false","NOT_RAW_REQUEST"),
    ("response_adjusted","UNKNOWN","RAW_RESPONSE_NOT_CONFIRMED"),
    ("basis_id",None,"MONETARY_BASIS_UNPROVEN"),
    ("basis_receipt_sha256",None,"MONETARY_BASIS_UNPROVEN"),
    ("action_vintage_ref",None,"MONETARY_BASIS_UNPROVEN"),
    ("volume_convention_ref",None,"MONETARY_BASIS_UNPROVEN"),
    ("listing_ref",None,"LISTING_IDENTITY_UNPROVEN"),
    ("rights_ref",None,"DATASET_RIGHTS_UNPROVEN"),
    ("dataset_use_ref",None,"DATASET_RIGHTS_UNPROVEN"),
    ("source_object_sha256",None,"SOURCE_BINDING_MISSING"),
    ("reader_receipt_sha256",None,"READER_RECEIPT_MISSING"),
    ("sealed_capture_prefix_sha256",None,"SOURCE_BINDING_MISSING"),
    ("selection_receipt_sha256",None,"REVISION_SELECTION_UNPROVEN"),
    ("source_revision_ref",None,"REVISION_SELECTION_UNPROVEN"),
    ("source_receipt_utc_ns",None,"SOURCE_RECEIPT_MISSING"),
    ("reader_completed_utc_ns",None,"READER_RECEIPT_MISSING"),
    ("value_state","MISSING_VOLUME","MINUTE_VALUE_UNAVAILABLE"),
    ("value_state","UNKNOWN","MINUTE_VALUE_UNAVAILABLE"),
])
def test_missing_or_inconsistent_owner_evidence_never_promotes(field,value,reason):
    r=preflight(scope(),[replace(claim(),**{field:value})])
    assert r.status=="NOT_ADMITTED"
    assert reason in r.exceptions[0].reasons
    assert not r.owner_review_candidate


def test_adjusted_false_and_signed_hashes_cannot_fill_missing_basis_receipt():
    r=preflight(scope(),[claim(basis_id=None)])
    assert "MONETARY_BASIS_UNPROVEN" in r.exceptions[0].reasons
    assert r.external_owner_admission_required


def test_unknown_source_or_reader_clock_does_not_backdate_late_data():
    r=preflight(scope(cutoff_s=T+190),[claim(reader_completed_utc_ns=(T+260)*NANO)])
    assert "READER_AFTER_CUTOFF" in r.exceptions[0].reasons
    assert not r.metadata_complete


def test_source_receipt_before_bar_close_is_contradictory():
    with pytest.raises(ValueError,match="source_before_bar_close"):
        preflight(scope(),[claim(source_receipt_utc_ns=(T+50)*NANO)])


def test_reader_completion_before_source_receipt_is_contradictory():
    with pytest.raises(ValueError,match="reader_before_source"):
        preflight(scope(),[claim(reader_completed_utc_ns=(T+59)*NANO)])


def test_invalid_digest_shape_is_refused_not_assumed_authenticated():
    with pytest.raises(ValueError,match="digest"):
        preflight(scope(),[claim(source_object_sha256="pretty-file-name")])


def test_duplicate_source_revision_per_slot_refuses_selection():
    with pytest.raises(ValueError,match="duplicate_slot"):
        preflight(scope(),[claim(),replace(claim(),source_revision_ref="correction:2")])


def test_unknown_symbol_or_calendar_identity_is_refused():
    with pytest.raises(ValueError,match="unexpected_security"):
        preflight(scope(),[claim("TSLA")])
    s=scope()
    other=m.Segment("2026-06-01","RTH",T,T+180,"DIFFERENT_CALENDAR","FULL")
    with pytest.raises(ValueError,match="segment_identity"):
        preflight(s,[claim(segment=other)])


def test_early_close_owner_window_is_not_padded_to_regular_hours():
    s=scope(minutes=2)
    c=[claim(k,i,segment=s.segments[0]) for k in COHORT for i in range(2)]
    r=preflight(s,c)
    assert r.expected_cells==8 and r.missing_cells==0


def test_unknown_value_is_not_explicit_zero_volume():
    a=preflight(scope(),[claim(value_state="EXPLICIT_ZERO_VOLUME")])
    b=preflight(scope(),[claim(value_state="MISSING_VOLUME")])
    assert a.explicit_zero_cells==1
    assert b.explicit_zero_cells==0
    assert b.unknown_cells>a.unknown_cells


def test_later_event_outside_owner_window_does_not_retroactively_change_prefix():
    a=preflight(scope(),[claim()])
    later=claim(minute=3,start_utc_s=T+180,end_utc_s=T+240)
    b=preflight(scope(),[claim(),later])
    assert a==b


def test_conflicting_first_seen_fields_or_noninteger_clocks_are_refused():
    with pytest.raises(ValueError,match="timestamp"):
        preflight(scope(),[claim(source_receipt_utc_ns=True)])
    with pytest.raises(ValueError,match="timestamp"):
        preflight(scope(),[claim(reader_completed_utc_ns="2026-06-01")])


def test_reordered_source_claims_produce_same_evidence_fingerprint():
    a=preflight(scope(),complete())
    b=preflight(scope(),list(reversed(complete())))
    assert a==b


def test_metadata_can_be_counted_but_cannot_certify_signatures_or_actual_file_bytes():
    r=preflight(scope(),complete())
    assert r.owner_review_candidate
    assert {"INPUT_DIGEST_NOT_AUTHENTICATED","EXTERNAL_SOURCE_RIGHTS_UNPROVEN",
            "SOURCE_BASIS_OWNER_UNVERIFIED"}<=set(r.unverified_authorities)
    assert r.may_execute_market_pilot is False


def test_listing_identity_version_drift_within_one_security_is_not_a_complete_intake():
    x=preflight(scope(),[claim("AAPL",0),
                         claim("AAPL",1,listing_ref="canonical_listing:AAPL:CHANGED")])
    assert any("LISTING_IDENTITY_CONFLICT" in e.reasons for e in x.exceptions)
    assert x.metadata_complete is False


def test_monetary_basis_version_drift_within_one_security_is_not_comparable():
    x=preflight(scope(),[claim("AAPL",0),
                         claim("AAPL",1,basis_id="unadjusted/USD/action-v2")])
    assert any("MONETARY_BASIS_CONFLICT" in e.reasons for e in x.exceptions)
    assert not x.owner_review_candidate


def test_empty_one_minute_value_marked_present_cannot_certify_actual_row_content():
    x=preflight(scope(),[claim("AAPL",0)])
    assert not x.metadata_complete
    assert "UNCHECKED_CUSTODY" in x.unverified_authorities
    assert x.may_execute_market_pilot is False


def test_externally_unverified_rights_reference_never_promotes_broad_entitlement():
    altered=claim(dataset_use_ref="operator_claim:ALL_FINANCIAL_DATA")
    r=preflight(scope(),[altered])
    assert "EXTERNAL_SOURCE_RIGHTS_UNPROVEN" in r.unverified_authorities
    assert r.status=="NOT_ADMITTED"


def test_reader_receipt_beyond_cutoff_is_not_known_at_earlier_decision():
    early=scope(cutoff_s=T+181)
    x=preflight(early,[claim("AAPL",0,reader_completed_utc_ns=(T+182)*NANO)])
    assert "READER_AFTER_CUTOFF" in x.exceptions[0].reasons
    assert x.unknown_cells==x.expected_cells


def test_reader_nanosecond_receipt_ceil_to_supported_microsecond_before_cutoff():
    from dataclasses import replace as dc_replace
    base=scope()
    first_close=(T+60)*NANO
    cutoff=first_close+1234
    near=claim(source_receipt_utc_ns=first_close+1000,
               reader_completed_utc_ns=first_close+1200)
    result=preflight(dc_replace(base,cutoff_utc_ns=cutoff),[near])
    assert any(e.security_id=="AAPL" and e.start_utc_s==T and
               "READER_AFTER_CUTOFF" in e.reasons for e in result.exceptions)


def test_reader_microsecond_receipt_at_exact_cutoff_is_eligible_metadata_only():
    from dataclasses import replace as dc_replace
    base=scope()
    first_close=(T+60)*NANO
    cutoff=first_close+2000
    near=claim(source_receipt_utc_ns=first_close+1000,
               reader_completed_utc_ns=first_close+1200)
    result=preflight(dc_replace(base,cutoff_utc_ns=cutoff),[near])
    assert not any(e.security_id=="AAPL" and e.start_utc_s==T
                   for e in result.exceptions)
    assert result.status=="NOT_ADMITTED"
