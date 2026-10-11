"""S2-P1 Tiingo L1 research-source fitness, no provider / second reader.

Designed to accept the ORIGINAL Data OS tiingo_reader.TiingoView shape.
Test rows are entirely synthetic; real read-only exercise is separately witnessed.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import copy
import math
import pytest

import pressure as m
from tiingo_source_fitness import assess_tiingo_view, aggregate_cohort_fitness

SHA="a"*64
RECEIPT="b"*64
CAPTURE="2026-10-11T17:51:08.299672+00:00"
COHORT=("AAPL","MSFT","NVDA","SPY")


@dataclass(frozen=True)
class OwnerResearchView:
    source: str="boats-bars"
    source_sha256: str=SHA
    source_observed_at_utc: str=CAPTURE
    purpose: str="RETROSPECTIVE_EXPLORATORY"
    pit_backtest_eligible: bool=False
    redistribution_admitted: bool=False
    rows: tuple=()
    authority: str="RESEARCH_ONLY_VENDOR_SOURCE"
    source_request_path: str="/boats/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close,volume"


def row(at="2026-10-08T20:00:00-04:00",*,volume=100,
        source="boats-bars",symbol="AAPL",venue="BOATS",scope="single_ats",
        session="overnight",unit="shares",schema="mastermind.tiingo.research_views.v2"):
    return dict(
        source_view_schema=schema,
        dataset_source=source,source_vendor="tiingo",
        source_sha256=SHA,source_receipt_id=RECEIPT,
        source_observed_at_utc=CAPTURE,
        source_rights_admitted=False,pit_backtest_eligible=False,
        dataos_identity_admitted=False,
        canonical_price_basis_admitted=False,
        executable_price_proven=False,is_nbbo=False,
        ticker_vendor=symbol,bar_at_vendor=at,
        venue=venue,venue_scope=scope,session=session,
        volume_unit_vendor=unit,
        requested_resample_frequency="1min",
        requested_after_hours=None,
        vendor_volume=volume,volume_available=volume is not None,
        vendor_open=100.,vendor_high=102.,vendor_low=99.,vendor_close=101.,
        projection_version="tiingo.additional_history.v1"
    )


def view(rows=None,**change):
    items=(row(),row(at="2026-10-08T20:01:00-04:00",volume=0)) if rows is None else tuple(rows)
    return replace(OwnerResearchView(rows=items),**change)


def assess(v=None,*,pilot=COHORT):
    return assess_tiingo_view(view() if v is None else v,required_symbols=pilot)


def test_boats_real_shape_keeps_overnight_venue_separate_from_daytime_factor_flow():
    r=assess()
    assert r.schema=="factor_atlas.tiingo_source_fitness.v1"
    assert r.status=="BOATS_OVERNIGHT_SINGLE_ATS_RESEARCH_ONLY"
    assert r.source=="boats-bars" and r.vendor=="tiingo"
    assert r.audited_rows==2 and r.source_kind=="RESEARCH_L1_NOT_CANONICAL"
    assert r.venue_scope=="single_ats"
    assert r.venue=="BOATS"
    assert r.observed_in_pilot==("AAPL",)
    assert r.unobserved_in_pilot_partition==("MSFT","NVDA","SPY")
    assert r.overnight_sessions[0].date_end_et=="2026-10-09"
    assert r.overnight_sessions[0].requested_minute_slots==480
    assert r.overnight_sessions[0].observed_unique_minutes==2
    assert r.overnight_sessions[0].unreported_minutes==478
    assert r.overnight_sessions[0].zero_vendor_volume_rows==1
    assert r.read_purpose=="RETROSPECTIVE_EXPLORATORY"
    assert r.source_observed_at_utc==CAPTURE
    assert r.source_admitted is False
    assert r.pit_backtest_eligible is False
    assert r.may_compute_daytime_pressure is False
    assert r.customer_publishable is False
    assert r.authority==m.AUTHORITY
    assert all(not flag for _,flag in r.authority)
    assert "BOATS_NOT_DAYTIME_CONSOLIDATED" in r.refusals


def test_research_zero_volume_is_observed_vendor_zero_not_verified_no_trade():
    r=assess()
    assert r.overnight_sessions[0].zero_vendor_volume_rows==1
    assert "ZERO_VENDOR_VOLUME_NOT_TRADE_PROOF" in r.refusals


def test_previous_evening_session_partial_request_does_not_claim_false_480_gap():
    x=view(rows=(
        row(at="2026-10-08T00:00:00-04:00"),
        row(at="2026-10-08T00:01:00-04:00")))
    r=assess(x)
    assert r.overnight_sessions[0].date_end_et=="2026-10-08"
    assert r.overnight_sessions[0].requested_minute_slots==240
    assert r.overnight_sessions[0].observed_unique_minutes==2
    assert r.overnight_sessions[0].unreported_minutes==238
    assert r.overnight_sessions[0].request_left_clipped is True


def test_two_true_overnight_sessions_remain_distinct_after_midnight():
    v=view(rows=(
       row(at="2026-10-08T00:00:00-04:00"),
       row(at="2026-10-08T20:00:00-04:00"),
       row(at="2026-10-09T03:59:00-04:00")))
    a=assess(v)
    assert tuple(s.date_end_et for s in a.overnight_sessions)==("2026-10-08","2026-10-09")
    assert a.overnight_sessions[0].requested_minute_slots==240
    assert a.overnight_sessions[1].requested_minute_slots==480
    assert a.overnight_sessions[1].observed_unique_minutes==2


def test_exact_vendor_timestamp_dedupe_and_out_of_phase_refusal():
    z=row()
    with pytest.raises(ValueError,match="duplicate_vendor_minute"):
        assess(view(rows=(z,z)))
    with pytest.raises(ValueError,match="outside_overnight"):
        assess(view(rows=(row(at="2026-10-08T11:00:00-04:00"),)))


def test_request_must_prove_true_one_minute_not_five_minute_or_chart_fill():
    for query in (
        "/boats/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=5min&columns=volume",
        "/boats/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&forceFill=true&columns=open,high,low,close,volume",
        "/boats/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close",
    ):
        with pytest.raises(ValueError,match="requested_one_minute_unfilled_volume"):
            assess(view(source_request_path=query))


def test_bogus_rights_identity_or_basis_claim_cannot_be_l1_vendor_admission():
    flags=("source_rights_admitted","pit_backtest_eligible",
           "dataos_identity_admitted","canonical_price_basis_admitted",
           "executable_price_proven","is_nbbo")
    for key in flags:
        x=row()
        x[key]=True
        with pytest.raises(ValueError,match="owner_source_admission_spoof"):
            assess(view(rows=(x,)))


def test_source_read_wrapper_cannot_elevate_pit_or_redistribution():
    for kw in ({"pit_backtest_eligible":True},{"redistribution_admitted":True},
               {"authority":"ADMITTED_MARKET_DATA"},
               {"purpose":"PIT_BACKTEST"}):
        with pytest.raises(ValueError,match="owner_view_authority_or_purpose"):
            assess(view(**kw))


def test_vendor_market_clock_cannot_be_inferred_from_later_archive_capture():
    changed=view(source_observed_at_utc="2026-10-07T20:00:00+00:00")
    with pytest.raises(ValueError,match="source_observed_before_event"):
        assess(changed)


def test_source_day_request_and_row_hour_must_be_consistent():
    for instant in ("2026-10-07T23:59:00-04:00","2026-10-10T00:00:00-04:00"):
        with pytest.raises(ValueError,match="bar_outside_original_request"):
            assess(view(rows=(row(at=instant),)))


@pytest.mark.parametrize("bad",["2026-10-08T20:00:30-04:00","2026-10-08T20:00:00",True,None])
def test_unaligned_or_unaware_vendor_minute_does_not_count(bad):
    with pytest.raises(ValueError,match="invalid_vendor_minute_clock"):
        assess(view(rows=(row(at=bad),)))


def test_retained_row_self_hash_and_context_must_match_selected_source():
    for field,bad in (
        ("source_sha256","0"*64),("source_receipt_id",None),
        ("source_observed_at_utc","2026-10-11T12:00:00+00:00"),
        ("dataset_source","iex-bars"),("ticker_vendor","NVDA"),
    ):
        x=row();x[field]=bad
        with pytest.raises(ValueError,match="source_row_context_mismatch"):
            assess(view(rows=(x,)))


def test_present_nonnumeric_or_negative_vendor_volume_refuses():
    for volume in (-1.,float("nan"),float("inf"),True,"1.0"):
        with pytest.raises(ValueError,match="invalid_vendor_volume"):
            assess(view(rows=(row(volume=volume),)))


def test_null_vendor_volume_is_unavailable_not_measured_zero():
    a=assess(view(rows=(row(volume=None),)))
    s=a.overnight_sessions[0]
    assert s.observed_unique_minutes==1
    assert s.missing_volume_rows==1
    assert s.zero_vendor_volume_rows==0
    assert a.may_compute_daytime_pressure is False


def test_impossible_ohlc_geometry_is_rejected():
    x=row();x["vendor_high"]=99.
    with pytest.raises(ValueError,match="invalid_vendor_ohlc"):
        assess(view(rows=(x,)))


def test_iex_single_exchange_not_qualified_consolidated_equity():
    x=row(at="2026-10-08T09:30:00-04:00",source="iex-bars",
          venue="IEX",scope="single_exchange",session="vendor_request_session",unit="shares")
    ref=view(rows=(x,),source="iex-bars",
             source_request_path="/iex/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close,volume")
    result=assess(ref)
    assert result.status=="IEX_SINGLE_EXCHANGE_RESEARCH_ONLY"
    assert "SINGLE_EXCHANGE_NOT_CONSOLIDATED" in result.refusals
    assert not result.source_admitted


def test_consolidated_beta_source_is_a_potential_candidate_but_not_admitted():
    x=row(at="2026-10-08T09:30:00-04:00",source="equity-intraday-bars",
          venue=None,scope="vendor_equity_reference",session="unqualified",unit="unqualified")
    ref=view(rows=(x,),source="equity-intraday-bars",
        source_request_path="/tiingo/equity/intraday/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close,volume")
    result=assess(ref)
    assert result.status=="CONSOLIDATED_BETA_CANDIDATE_NOT_ADMITTED"
    assert "CONSOLIDATED_VOLUME_UNIT_UNQUALIFIED" in result.refusals
    assert result.may_compute_daytime_pressure is False
    assert result.venue_scope=="vendor_equity_reference"


def test_eod_is_not_a_one_minute_bar_even_if_it_contains_daily_volume():
    source=view(rows=(),source="eod-bars",source_request_path="/tiingo/daily/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09")
    a=assess(source)
    assert a.status=="EOD_NOT_INTRADAY"
    assert a.audited_rows==0 and not a.may_compute_daytime_pressure


def test_unregistered_vendor_source_is_not_silently_assigned_to_consolidated():
    with pytest.raises(ValueError,match="unsupported_tiingo_source"):
        assess(view(source="boats-firehose"))


def test_input_permutation_does_not_change_source_fitness_evidence_fingerprint():
    a=assess()
    b=assess(view(rows=tuple(reversed(view().rows))))
    assert a==b and a.evidence_digest==b.evidence_digest


def test_changed_observed_volume_changes_fingerprint_with_same_metadata():
    a=assess()
    items=list(view().rows);items[0]["vendor_volume"]=20.
    b=assess(view(rows=items))
    assert a.evidence_digest!=b.evidence_digest
    assert a.source_sha256==b.source_sha256
    assert not a.source_admitted and not b.source_admitted


def test_cohort_aggregator_separates_sampled_vendor_symbols_from_pilot_population():
    a=assess()
    amd_row=row(symbol="AMD")
    amd_row["source_sha256"]="c"*64
    amd_row["source_receipt_id"]="d"*64
    amdv=view(source_sha256="c"*64,
              source_request_path="/boats/AMD/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close,volume",
              rows=(amd_row,))
    b=assess_tiingo_view(amdv,required_symbols=COHORT)
    c=aggregate_cohort_fitness((a,b),required_symbols=COHORT)
    assert c.sampled_symbols==("AAPL","AMD")
    assert c.pilot_symbols_with_retained_rows==("AAPL",)
    assert c.pilot_symbols_not_in_examined_partitions==("MSFT","NVDA","SPY")
    assert c.outside_pilot_sampled_symbols==("AMD",)
    assert c.qualified_four_stock_daytime_source is False
    assert c.all_dataos_rights_admitted is False


def test_aggregator_does_not_claim_global_absence_from_two_sampled_partitions():
    a=assess()
    c=aggregate_cohort_fitness((a,),required_symbols=COHORT)
    assert c.unexamined_archives_are_unknown is True
    assert c.pilot_symbols_not_in_examined_partitions==("MSFT","NVDA","SPY")
    assert c.qualified_four_stock_daytime_source is False


def test_claimed_permission_from_chairman_is_not_a_programmatic_source_admission_flag():
    a=assess()
    assert a.redistribution_admitted is False
    assert a.pit_backtest_eligible is False
    assert "DATASET_LICENSE_OWNER_BINDING_REQUIRED" in a.refusals


def test_identical_raw_sha_used_for_distinct_vendor_symbol_contexts_refused():
    # Producer PR #8698 repaired precisely this kind of cross-context aliasing;
    # the consumer may not reintroduce it by pooling selected partitions.
    a=assess()
    fake_amd=assess(view(
        source_request_path="/boats/AMD/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close,volume",
        rows=(row(symbol="AMD"),)))
    with pytest.raises(ValueError,match="source_sha_context_alias_collision"):
        aggregate_cohort_fitness((a,fake_amd),required_symbols=COHORT)



def test_duplicate_volume_columns_or_unexpected_query_field_is_refused():
    base=view().source_request_path
    for bad in (
        base+"&columns=open,high,low,close,volume",
        base+"&access_token=not-a-key",
        base+"&resampleFreq=5min",
    ):
        with pytest.raises(ValueError,match="source_request_query_identity"):
            assess(view(source_request_path=bad))


def test_explicit_forcefill_false_does_not_promote_venue_coverage():
    path=view().source_request_path+"&forceFill=false"
    result=assess(view(source_request_path=path))
    assert result.audited_rows==2
    assert result.source_admitted is False
    assert result.customer_publishable is False
    assert "BOATS_NOT_DAYTIME_CONSOLIDATED" in result.refusals


def test_future_vendor_bar_clock_never_backdates_the_source_capture():
    row_after=row(at="2026-10-12T01:00:00-04:00")
    with pytest.raises(ValueError,match="source_observed_before_event"):
        assess(view(rows=(row_after,)))


def test_not_even_four_synthetically_full_names_can_grant_an_authorized_pilot():
    readings=[]
    for symbol,sha_char in (("AAPL","a"),("MSFT","c"),("NVDA","d"),("SPY","e")):
        record=row(symbol=symbol)
        record["source_sha256"]=sha_char*64
        record["source_receipt_id"]="f"*64
        v=view(rows=(record,),source_sha256=sha_char*64,
          source_request_path=f"/boats/{symbol}/prices?startDate=2026-10-08&endDate=2026-10-09&resampleFreq=1min&columns=open,high,low,close,volume")
        readings.append(assess(v))
    cohort=aggregate_cohort_fitness(readings)
    assert cohort.pilot_symbols_with_retained_rows==COHORT
    assert cohort.pilot_symbols_not_in_examined_partitions==()
    assert cohort.qualified_four_stock_daytime_source is False
    assert not cohort.all_dataos_rights_admitted


def test_real_volume_rich_EOD_history_cannot_satisfy_any_one_minute_pilot_member():
    """Tiingo's growing multi-million-row EOD archive is a distinct input.

    Its daily rows do not satisfy the four-stock minute cohort regardless of
    tickers or raw/adjusted OHLCV availability.
    """
    eod_rows=tuple({"ticker_vendor":"AAPL","source_sha256":SHA,
                    "vendor_close":101.,"vendor_volume":10000,
                    "market_date":f"2026-10-{d:02d}"}
                   for d in range(8,10))
    eod=view(source="eod-bars",rows=eod_rows,
       source_request_path="/tiingo/daily/AAPL/prices?startDate=2026-10-08&endDate=2026-10-09")
    fit=assess(eod)
    assert fit.status=="EOD_NOT_INTRADAY"
    assert fit.audited_rows==2
    assert fit.observed_in_pilot==()
    cohort=aggregate_cohort_fitness((fit,),required_symbols=COHORT)
    assert cohort.sampled_symbols==("AAPL",)
    assert cohort.pilot_symbols_with_retained_rows==()
    assert cohort.pilot_symbols_not_in_examined_partitions==COHORT
    assert cohort.qualified_four_stock_daytime_source is False
