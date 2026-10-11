"""Contract-pinned interpretation of the HELD Macro retained-minute decoder.

No source reads, corpus materialization or live proxy measurement. All rows
and byte receipts below are FABRICATED and are not proof of installed source.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import copy,json
import pytest

from test_source_preflight import T,NANO,COHORT,scope
from owner_reader_abi import inspect_candidate

_EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)


def utc(ns):
    return (_EPOCH+timedelta(microseconds=(ns+999)//1000)).isoformat().replace("+00:00","Z")


def minute(symbol="AAPL", i=0, volume=10., *, role="research_unadjusted",
           corrected_basis=None):
    start=T+i*60
    end=start+60
    source=end*NANO+1000
    read=end*NANO+2000
    h=sha256(f"{symbol}/{i}".encode()).hexdigest()
    source_obs=dict(
        observer_id="terminal.backfill_intraday",
        capture_id=f"capture:{symbol}",
        capture_sequence=1,capture_sha256=h,
        source_received_at_utc_ns=source,
        source_response_sha256="a"*64,
        owner_reader_identity="SYNTHETIC_OWNER_READER",
        owner_read_completed_at_utc_ns=read,
        request_adjusted=False if role=="research_unadjusted" else True,
        response_adjusted="FALSE" if role=="research_unadjusted" else "TRUE",
        page_index=0,row_index=i,
        owner_read_receipt_sha256="b"*64,
        volume_state="observed" if volume is not None else "null",
        acquisition_role=role,
        capture_payload_schema="mastermind.intraday_minute_capture_payload.v3")
    row=dict(
        stream="stock",security_id=symbol,
        basis_id=corrected_basis,
        basis_refusals=["TERMINAL_BASIS_UNPROVEN"],
        revision_id=f"capture:{symbol}:0:{i}",
        start=utc(start*NANO),end=utc(end*NANO),
        known_at=utc(read),
        open=100.,high=102.,low=99.,close=101.,
        volume=volume,
        source_ref=f"terminal-minute-capture:{h}:0:{i}",
        source_observation=source_obs)
    seal=json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)
    row["receipt_sha256"]=sha256(seal.encode()).hexdigest()
    return row


def packet(rows=(),status=None):
    rows=list(rows)
    return dict(
        schema="mastermind.entry_radar.terminal_minute_observations.v1",
        status=status or ("REVISION_INPUTS_BUILT_NOT_ADMITTED" if rows else "UNAVAILABLE"),
        minutes=rows,diagnostics={},
        unproven_owner_requirements=[
            "stable_security_identity","price_volume_corporate_action_basis",
            "calendar_and_exceptional_sessions","complete_pilot_population"],
        authority={"may_fire":False,"may_rank":False,"may_trade":False})


def allrows():
    return [minute(s,i) for s in COHORT for i in range(3)]


def eval_(rows=None,**change):
    p=packet(allrows() if rows is None else rows)
    p.update(change)
    return inspect_candidate(p,scope())


def test_actual_held_candidate_basis_null_remains_not_admitted_even_with_12_rows():
    out=eval_()
    assert out.decoder_schema=="mastermind.entry_radar.terminal_minute_observations.v1"
    assert out.stage=="OWNER_BASIS_UNPROVEN"
    assert out.source_owner_head=="6cff6ef8aba28dc7ee6f7779a81ef18856d9b3b6"
    assert out.mapped_rows==12
    assert out.preflight.expected_cells==12
    assert not out.preflight.metadata_complete
    assert all("MONETARY_BASIS_UNPROVEN" in issue.reasons
               for issue in out.preflight.exceptions)
    assert out.market_pilot_admitted is False
    assert out.customer_publishable is False
    assert out.source_authenticated is False
    assert out.verified_rights is False
    assert out.pit_listing_verified is False
    assert all(not value for _,value in out.authority)


def test_missing_owner_payload_stays_unavailable():
    out=eval_([])
    assert out.stage=="OWNER_READER_UNAVAILABLE"
    assert out.mapped_rows==0
    assert out.preflight.missing_cells==12


def test_one_owner_row_is_not_a_full_four_name_input():
    out=eval_([minute()])
    assert out.mapped_rows==1 and out.preflight.missing_cells==11
    assert out.stage=="OWNER_BASIS_UNPROVEN"


def test_decoder_missing_volume_is_unknown_not_numeric_zero():
    out=eval_([minute(volume=None)])
    assert out.mapped_rows==1
    assert out.mapped_volume_states==(("UNKNOWN",1),)
    assert out.preflight.explicit_zero_cells==0
    assert out.preflight.unknown_cells==12


def test_decoder_explicit_zero_volume_is_counted_without_source_admission():
    out=eval_([minute(volume=0.)])
    assert out.mapped_volume_states==(("EXPLICIT_ZERO_VOLUME",1),)
    assert out.preflight.explicit_zero_cells==1
    assert out.market_pilot_admitted is False


def test_later_owner_read_is_not_antedated_by_source_response():
    x=minute()
    x["source_observation"]["owner_read_completed_at_utc_ns"]=(T+700)*NANO
    x["known_at"]=utc((T+700)*NANO)
    x["receipt_sha256"]=seal(x)
    out=eval_([x])
    assert any("READER_AFTER_CUTOFF" in issue.reasons for issue in out.preflight.exceptions)


def seal(row):
    c={key:value for key,value in row.items() if key!="receipt_sha256"}
    return sha256(json.dumps(c,sort_keys=True,separators=(",",":"),
                             ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def test_forged_actual_reader_microsecond_stamp_is_refused():
    x=minute()
    x["known_at"]=utc((T+60)*NANO)
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="read_clock_mismatch"):
        eval_([x])


def test_corrupted_row_receipt_is_refused():
    x=minute();x["receipt_sha256"]="0"*64
    with pytest.raises(ValueError,match="row_receipt_digest_mismatch"):
        eval_([x])


def test_inconsistent_capture_sha_and_revision_identity_is_refused():
    x=minute()
    x["source_ref"]="terminal-minute-capture:"+"1"*64+":0:0"
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="source_ref_mismatch"):
        eval_([x])


def test_candidate_cannot_upgrade_basis_via_unverified_label():
    x=minute(corrected_basis="unadjusted/USD")
    with pytest.raises(ValueError,match="candidate_basis_claim_not_supported"):
        eval_([x])


def test_candidate_contract_downgrade_cannot_claim_new_authority():
    with pytest.raises(ValueError,match="decoder_schema"):
        eval_([],schema="mastermind.entry_radar.terminal_minute_observations.v2")
    with pytest.raises(ValueError,match="owner_authority_not_closed"):
        eval_([],authority={"may_trade":True})


def test_chart_adjusted_role_remains_not_research_unadjusted():
    out=eval_([minute(role="chart_adjusted")])
    assert out.stage=="OWNER_BASIS_UNPROVEN"
    assert any("NOT_RESEARCH_UNADJUSTED" in issue.reasons for issue in out.preflight.exceptions)
    assert not out.market_pilot_admitted


def test_owner_unavailable_cannot_carry_hidden_observed_rows():
    with pytest.raises(ValueError,match="decoder_status_payload_conflict"):
        eval_([minute()],status="UNAVAILABLE")


def test_owner_source_without_explicit_selected_security_identity_refuses():
    x=minute();x["security_id"]=None;x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="canonical_security_id_required"):
        eval_([x])


def test_future_observation_outside_calendar_remains_non_measurement():
    out=eval_()
    assert out.preflight.owner_review_candidate is False
    assert "SOURCE_BASIS_OWNER_UNVERIFIED" in out.preflight.unverified_authorities
    assert out.owner_admission_required
    assert not hasattr(out,"window")


def test_replay_permutation_has_stable_identity():
    rows=allrows()
    assert eval_(rows)==eval_(list(reversed(rows)))


def test_no_real_raw_source_bytes_or_original_receipt_signatures_claimed():
    out=eval_()
    assert out.mapped_listing_refs_are_null
    assert out.mapped_basis_refs_are_null
    assert out.fully_selected_revisions is False
    assert out.knowledge_class=="HELD_TERMINAL_READER_INTEROP_NOT_MARKET_MEASUREMENT"


def test_owner_row_after_its_source_response_is_not_incorrectly_qualified():
    x=minute()
    x["source_observation"]["owner_read_completed_at_utc_ns"] = (
        x["source_observation"]["source_received_at_utc_ns"]-1)
    x["known_at"]=utc(x["source_observation"]["owner_read_completed_at_utc_ns"])
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="reader_before_source"):
        eval_([x])


def test_candidate_rounded_microsecond_clock_preserved():
    x=minute()
    old=x["source_observation"]["owner_read_completed_at_utc_ns"]
    x["source_observation"]["owner_read_completed_at_utc_ns"]=old+1
    x["known_at"]=utc(old+1)
    x["receipt_sha256"]=seal(x)
    out=eval_([x])
    assert out.stage=="OWNER_BASIS_UNPROVEN" and not out.source_authenticated


def test_duplicate_visible_owner_revisions_are_not_selected_by_factor_atlas():
    x=minute()
    y=copy.deepcopy(x)
    y["revision_id"]="CORRECTION_NEW_VERSION"
    y["receipt_sha256"]=seal(y)
    with pytest.raises(ValueError,match="duplicate_slot"):
        eval_([x,y])


def test_malformed_source_observation_index_is_refused():
    x=minute()
    x["source_observation"]["page_index"]=-1
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="page_or_row_index"):
        eval_([x])


def test_unrecognized_source_response_adjusted_does_not_give_raw_basis():
    x=minute()
    x["source_observation"]["response_adjusted"]="AMBIGUOUS"
    x["receipt_sha256"]=seal(x)
    out=eval_([x])
    assert any("RAW_RESPONSE_NOT_CONFIRMED" in r.reasons for r in out.preflight.exceptions)
    assert out.stage=="OWNER_BASIS_UNPROVEN"


def test_nonfinite_or_negative_source_close_refused_even_as_candidate():
    for val in (float("nan"),float("inf"),0.,-1.):
        x=minute()
        x["close"]=val
        if val==val and val not in (float("inf"),float("-inf")):
            x["receipt_sha256"]=seal(x)
            with pytest.raises(ValueError,match="owner_close"):
                eval_([x])
        else:
            with pytest.raises(ValueError):
                eval_([x])


def test_observed_negative_or_null_volume_is_not_positive_observation():
    x=minute(volume=10.)
    x["volume"]=-10.
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="owner_volume"):
        eval_([x])
    x=minute(volume=None)
    x["source_observation"]["volume_state"]="observed"
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="owner_volume"):
        eval_([x])


def test_absence_of_canonical_identity_cannot_be_filled_from_stream_symbol():
    x=minute()
    x["security_id"]="UNREGISTERED_STOCK"
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="canonical_security_id"):
        eval_([x])


def test_source_data_role_labels_do_not_change_external_rights_gate():
    out=eval_([minute(role="research_unadjusted")])
    assert not out.verified_rights and out.mapped_basis_refs_are_null
    assert out.preflight.status=="NOT_ADMITTED"
    assert out.owner_admission_required


def test_unsupported_owner_source_timestamp_format_is_refused():
    x=minute()
    x["end"]="2026-06-01 09:31:00"
    x["receipt_sha256"]=seal(x)
    with pytest.raises(ValueError,match="owner_timestamp"):
        eval_([x])
