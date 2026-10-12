"""Native Data OS TiingoView -> EXISTING S2 metadata preflight, no BVC math.

All records are synthetic source-shaped objects. A separate bounded ORIGINAL
Tiingo reader can supply real views; no source access, customer or PIT admission.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date,datetime,timezone,timedelta
from zoneinfo import ZoneInfo
import pytest
import pressure as m
from source_preflight import IntakeScope
from test_tiingo_source_fitness import view,row
from tiingo_preflight_bridge import inspect_tiingo_preflight

NAMES=("AAPL","MSFT","NVDA","SPY")
ET=ZoneInfo("America/New_York")
DATE="2026-10-09"
START=int(datetime(2026,10,9,9,30,tzinfo=ET).timestamp())
END=START+390*60
SCOPE=IntakeScope(NAMES,(m.Segment(DATE,"RTH",START,END,
     "OWNER_CALENDAR_CANDIDATE_UNQUALIFIED:2026-10-09","FULL"),),
     int(datetime(2026,10,9,20,tzinfo=timezone.utc).timestamp())*10**9)
CUTOFF_LATER=int(datetime(2026,10,12,0,tzinfo=timezone.utc).timestamp())*10**9
MARK={"AAPL":"a","MSFT":"c","NVDA":"d","SPY":"e"}


def source(sym:str,*,minutes:int=2,missing:tuple[int,...]=(),
           timestamp_tail:str="",unknown_vol:bool=False,all_zero:bool=False):
    source_sha=MARK[sym]*64
    rows=[]
    for i in range(minutes):
        if i in missing:
            continue
        time=(datetime(2026,10,9,9,30,tzinfo=ET)+timedelta(minutes=i)).isoformat()
        entry=row(at=time,symbol=sym,source="equity-intraday-bars",
                  venue=None,scope="vendor_equity_reference",
                  session="unqualified",unit="unqualified",
                  volume=None if unknown_vol else 0 if all_zero else 100)
        entry["source_sha256"]=source_sha
        entry["source_receipt_id"]="f"*64
        if timestamp_tail:
            entry["source_observed_at_utc"]=timestamp_tail
        rows.append(entry)
    return view(rows=tuple(rows),source="equity-intraday-bars",
      source_sha256=source_sha,
      source_observed_at_utc=timestamp_tail or "2026-10-11T17:51:08.299672+00:00",
      source_request_path=f"/tiingo/equity/intraday/{sym}/prices?startDate=2026-10-09&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close,volume&afterHours=true&forceFill=false")


def audit(views=None,*,scope=SCOPE):
    return inspect_tiingo_preflight(
        tuple(source(s) for s in NAMES) if views is None else tuple(views),
        scope=scope)


def test_full_four_vendor_minute_shapes_still_have_unadmitted_preflight():
    v=audit()
    assert v.schema=="factor_atlas.tiingo_l1_source_preflight_bridge.v1"
    assert v.status=="SOURCE_METADATA_NOT_ADMITTED"
    assert v.source_population=="TIINGO_CONSOLIDATED_RESEARCH_L1"
    assert v.preflight.status=="NOT_ADMITTED"
    assert v.preflight.expected_cells==4*390
    assert v.preflight.represented_cells==8
    assert v.preflight.missing_cells==4*390-8
    assert v.preflight.unknown_cells==4*390
    assert v.preflight.metadata_complete is False
    assert v.actual_market_flow_computed is False
    assert v.source_rights_admitted is False
    assert v.calendar_attested is False
    assert v.canonical_identity_admitted is False
    assert v.may_execute_market_pilot is False
    assert v.authority==m.AUTHORITY
    assert v.observed_vendor_tickers==NAMES
    assert "SOURCE_AFTER_CUTOFF" in v.refusal_reasons
    assert "LISTING_IDENTITY_UNPROVEN" in v.refusal_reasons
    assert "MONETARY_BASIS_UNPROVEN" in v.refusal_reasons
    assert "DATASET_RIGHTS_UNPROVEN" in v.refusal_reasons


def test_retrospective_source_clock_is_not_relabelled_original_2026_10_09_pit():
    v=audit()
    assert v.preflight.exceptions
    one=next(x for x in v.preflight.exceptions if x.security_id=="AAPL"
             and x.start_utc_s==START)
    assert "SOURCE_AFTER_CUTOFF" in one.reasons
    assert "READER_RECEIPT_MISSING" in one.reasons
    assert "REVISION_SELECTION_UNPROVEN" in one.reasons
    assert v.source_capture_is_after_decision_for_some_rows is True


def test_later_research_cutoff_does_not_admit_source_or_mint_reader_receipt():
    v=audit(scope=replace(SCOPE,cutoff_utc_ns=CUTOFF_LATER))
    assert "SOURCE_AFTER_CUTOFF" not in v.refusal_reasons
    assert "READER_RECEIPT_MISSING" in v.refusal_reasons
    assert "MONETARY_BASIS_UNPROVEN" in v.refusal_reasons
    assert "LISTING_IDENTITY_UNPROVEN" in v.refusal_reasons
    assert v.preflight.status=="NOT_ADMITTED"
    assert not v.may_execute_market_pilot


def test_explicit_vendor_zero_is_not_relabelled_as_qualified_no_trade():
    v=audit((source("AAPL",all_zero=True),))
    assert v.vendor_zero_rows_in_scope==2
    assert v.preflight.explicit_zero_cells==0
    assert v.preflight.unknown_cells==1560
    assert "UNQUALIFIED_VENDOR_VOLUME_NOT_EXPLICIT_NO_TRADE" in v.refusal_reasons


def test_missing_source_row_retains_expected_slot_not_zero_filled():
    v=audit((source("AAPL",minutes=3,missing=(1,)),))
    assert v.preflight.expected_cells==1560
    assert v.preflight.represented_cells==2
    assert v.preflight.missing_cells==1558
    assert v.vendor_zero_rows_in_scope==0


def test_null_volume_represented_but_always_unusable_as_signed_flow():
    v=audit((source("AAPL",unknown_vol=True),))
    assert v.vendor_missing_volume_rows_in_scope==2
    assert v.preflight.unknown_cells==1560
    assert v.preflight.explicit_zero_cells==0


def test_unknown_vendor_ticker_not_promoted_to_four_stock_cohort():
    x=source("AAPL")
    # The original TiingoView request ID, not a client-asserted alias, binds
    # the symbol. A cross-ticker source cannot be mapped to another name.
    bad=replace(x,source_request_path=x.source_request_path.replace("AAPL","OTHER"))
    with pytest.raises(ValueError,match="source|vendor"):
        audit((bad,))


def test_duplicate_raw_revision_of_same_vendor_symbol_requires_original_owner():
    x=source("AAPL")
    with pytest.raises(ValueError,match="competing_source_partitions"):
        audit((x,x))


def test_unaccepted_boats_or_daily_source_never_enters_consolidated_preflight():
    x=source("AAPL")
    with pytest.raises(ValueError,match="consolidated_equity_source_required"):
        audit((replace(x,source="boats-bars"),))


def test_out_of_session_rows_are_not_injected_into_rth_denominator():
    x=source("AAPL")
    pre=row(at="2026-10-09T03:15:00-04:00",symbol="AAPL",
            source="equity-intraday-bars",venue=None,
            scope="vendor_equity_reference",session="unqualified",unit="unqualified")
    pre["source_sha256"]=MARK["AAPL"]*64
    pre["source_receipt_id"]="f"*64
    v=audit((replace(x,rows=(*x.rows,pre)),))
    assert v.out_of_calendar_source_minutes==1
    assert v.preflight.represented_cells==2
    assert v.preflight.expected_cells==1560


def test_extra_future_archive_source_cannot_change_old_scope_prefix():
    x=source("AAPL")
    future=row(at="2026-10-10T09:30:00-04:00",symbol="AAPL",
              source="equity-intraday-bars",venue=None,
              scope="vendor_equity_reference",session="unqualified",unit="unqualified")
    future["source_sha256"]=MARK["AAPL"]*64
    future["source_receipt_id"]="f"*64
    # Exact original request rejects bar date outside selected request.
    with pytest.raises(ValueError,match="source|request|outside"):
        audit((replace(x,rows=(*x.rows,future)),))


def test_full_390_rth_grid_from_unqualified_source_never_mints_flow_permission():
    v=audit(tuple(source(s,minutes=390) for s in NAMES))
    assert v.preflight.expected_cells==1560
    assert v.preflight.represented_cells==1560
    assert v.preflight.missing_cells==0
    assert v.preflight.unknown_cells==1560
    assert v.preflight.metadata_complete is False
    assert v.status=="SOURCE_METADATA_NOT_ADMITTED"
    assert not v.market_pilot_admitted and not v.actual_market_flow_computed


def test_original_reader_without_actual_receipt_cannot_use_build_asof_clock():
    v=audit()
    assert v.reader_receipts_attested is False
    assert "READER_RECEIPT_MISSING" in v.refusal_reasons
    assert v.derived_cutoff_from_processing_time is False


def test_reordered_sources_and_rows_have_identical_causal_research_fingerprint():
    a=audit()
    inputs=[source(s) for s in NAMES]
    inputs.reverse()
    reordered=tuple(replace(x,rows=tuple(reversed(x.rows))) for x in inputs)
    b=audit(reordered)
    assert a==b and a.input_digest==b.input_digest


def test_unqualified_vendor_first_capture_cannot_become_source_revision_selection():
    v=audit()
    assert "REVISION_SELECTION_UNPROVEN" in v.refusal_reasons
    assert v.source_owner_revision_selection_proven is False


def test_dataos_rights_flag_spoof_refused():
    x=source("AAPL")
    bad=replace(x,redistribution_admitted=True)
    with pytest.raises(ValueError,match="authority_or_purpose"):
        audit((bad,))


def test_unsupported_source_time_precision_fails_closed():
    invalid=source("AAPL",timestamp_tail="2026-10-11T17:51:08.299672888888+00:00")
    with pytest.raises(ValueError,match="source_timestamp_precision"):
        audit((invalid,))


def test_source_first_seen_submicrosecond_tail_is_never_backdated():
    stamp="2026-10-11T17:51:08.299672001+00:00"
    x=source("AAPL",timestamp_tail=stamp)
    before=int(datetime(2026,10,11,17,51,8,299672,tzinfo=timezone.utc).timestamp()*10**9)
    early=replace(SCOPE,cutoff_utc_ns=before)
    v=audit((x,),scope=early)
    assert "SOURCE_AFTER_CUTOFF" in v.refusal_reasons


def test_source_hash_mutation_changes_digest_but_not_permission():
    x=source("AAPL")
    other=replace(x,source_sha256="b"*64,
                  rows=tuple(dict(r,source_sha256="b"*64) for r in x.rows))
    a=audit((x,))
    b=audit((other,))
    assert a.input_digest!=b.input_digest
    assert not a.source_rights_admitted and not b.source_rights_admitted


def test_same_raw_source_hash_across_two_vendor_names_requires_original_context_selection():
    a=source("AAPL")
    original=source("MSFT")
    forged=replace(original,source_sha256=a.source_sha256,
                   rows=tuple(dict(r,source_sha256=a.source_sha256)
                              for r in original.rows))
    with pytest.raises(ValueError,match="source_sha_context_alias_collision"):
        audit((a,forged))


def test_changed_vendor_price_alters_source_fingerprint_without_exposing_price_output():
    a=source("AAPL")
    changed=list(a.rows)
    changed[0]=dict(changed[0],vendor_close=100.9)
    original=audit((a,))
    modified=audit((replace(a,rows=tuple(changed)),))
    assert original.preflight.input_digest==modified.preflight.input_digest
    assert original.input_digest!=modified.input_digest
    assert modified.actual_market_flow_computed is False
    assert not hasattr(modified,"vendor_close")
