"""Original fabricated one-minute window fixtures; no market-data admission."""
from dataclasses import replace, asdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import importlib
import math
import pytest
import pressure as m

T=1780320600

def w():
    assert Path(__file__).with_name("window_pressure.py").exists(), "cumulative window implementation missing"
    return importlib.import_module("window_pressure")

def make(day="2026-06-01", *, pre=False, names=("A","B","C"), prices=(100,101,100,102,101), scale=1.):
    anchor=int(datetime.fromisoformat(day+"T09:30:00").replace(tzinfo=ZoneInfo("America/New_York")).timestamp())
    start=anchor-120 if pre else anchor
    segments=((m.Segment(day,"PRE",start,anchor,"SYNTHETIC_CAL","FULL"),
               m.Segment(day,"RTH",anchor,anchor+390*60,"SYNTHETIC_CAL","FULL")) if pre else
              (m.Segment(day,"RTH",anchor,anchor+390*60,"SYNTHETIC_CAL","FULL"),))
    bars=[]
    for sid in names:
        for i,price in enumerate(prices):
            t=start+i*60
            seg=next(s for s in segments if s.start_utc_s<=t<s.end_utc_s)
            bars.append(m.Bar(sid,seg,t,t+60,t+62,price,100.*scale,None,
                              "unadjusted/USD","SYNTHETIC_"+sid,"FIXTURE_RIGHTS"))
    return bars,segments,start,start+len(prices)*60

def groups():
    return [m.Membership("F1","v1","current_cohort",("A","B")),
            m.Membership("F2","v1","current_cohort",("B","C"))]

def calc(data=None, **kw):
    bars,segs,start,end=data or make()
    opts=dict(start_utc_s=start,end_utc_s=end,cutoff_utc_s=end+2,
              config=replace(m.disclosed_core_config(),min_returns=2))
    opts.update(kw)
    return w().measure_windows(bars,groups(),segs,**opts)

def test_complete_window_sums_numeric_estimates_without_claiming_all_direction_usable():
    bars,segs,start,end=make();r=calc((bars,segs,start,end));f=r.factors[0]
    points=m.bvc_series([b for b in bars if b.security_id in ("A","B")],replace(m.disclosed_core_config(),min_returns=2),cutoff_utc_s=end+2)
    assert f.expected_cells==10 and f.observed_cells==10 and f.missing_cells==0
    assert f.full_gross_usd==f.observed_gross_usd==100800
    assert f.full_estimated_net_usd==pytest.approx(math.fsum(p.net_usd for p in points))
    assert f.policy_neutral_gross_usd==60200 and f.directionally_usable_gross_usd==40600
    assert f.net_reference is not None and f.gross_reference is not None
    assert f.net_reference.complete and f.status=="COMPLETE_ESTIMATE"
    assert all(value is False for name,value in r.authority)

def test_missing_minute_retains_partial_dollars_but_withholds_full_window_and_baseline():
    bars,segs,start,end=make();bars=[b for b in bars if not (b.security_id=="A" and b.start_utc_s==start+60)]
    f=calc((bars,segs,start,end)).factors[0]
    assert f.missing_cells==1 and f.observed_gross_usd==90700
    assert f.full_gross_usd is None and f.full_estimated_net_usd is None
    assert f.gross_reference is None and f.net_reference is None and f.status=="PARTIAL_COVERAGE"
    assert f.contributions[0].first_missing_utc_s==start+60

def test_empty_input_is_missing_not_complete_zero():
    _,segs,start,end=make();f=calc(([],segs,start,end)).factors[0]
    assert f.observed_gross_usd==0 and f.missing_cells==10
    assert f.full_gross_usd is None and f.net_reference is None

def test_explicit_zero_volume_rows_are_complete_zero():
    bars,segs,start,end=make();bars=[replace(b,volume=0.) for b in bars]
    f=calc((bars,segs,start,end)).factors[0]
    assert f.full_gross_usd==0 and f.full_estimated_net_usd==0
    assert f.gross_reference.value==0 and f.net_reference.value==0

def test_conservative_null_warmup_does_not_erase_gross_or_become_full_net():
    f=calc(config=m.BVCConfig(min_returns=2)).factors[0]
    assert f.full_gross_usd==100800 and f.gross_reference is not None
    assert f.full_estimated_net_usd is None and f.net_reference is None
    assert f.unestimated_gross_usd==40200 and f.status=="DIRECTION_UNAVAILABLE"

def test_overlap_union_counted_once_per_security_minute():
    r=calc()
    assert r.union_observed_gross_usd==151200
    assert r.sum_factor_observed_gross_usd==201600 and r.duplicated_gross_usd==50400
    assert r.overlap==(("B",("F1","F2")),)

def test_input_membership_order_and_replay_are_deterministic():
    bars,segs,start,end=make();a=calc((bars,segs,start,end))
    b=w().measure_windows(reversed(bars),list(reversed(groups())),segs,start_utc_s=start,end_utc_s=end,cutoff_utc_s=end+2,config=replace(m.disclosed_core_config(),min_returns=2))
    assert a==b and m.digest(asdict(a))==m.digest(asdict(b))

def test_after_window_corruption_and_late_duplicate_do_not_change_old_result():
    bars,segs,start,end=make();a=calc((bars,segs,start,end))
    b=replace(bars[-1],start_utc_s=end,end_utc_s=end+60,available_at_utc_s=end+62,close=-100)
    late=replace(bars[0],available_at_utc_s=end+500,close=900)
    assert calc((bars+[b,b,late],segs,start,end))==a

def test_late_arriving_row_is_missing_at_earlier_cutoff():
    bars,segs,start,end=make();bars[0]=replace(bars[0],available_at_utc_s=end+100)
    a=calc((bars,segs,start,end));b=calc((bars,segs,start,end),cutoff_utc_s=end+100)
    assert a.factors[0].missing_cells==1 and b.factors[0].missing_cells==0

def test_pre_window_history_availability_is_part_of_reference_clock():
    bars,segs,start,end=make();bars=[replace(b,available_at_utc_s=end+100) if b.start_utc_s==start else b for b in bars]
    r=calc((bars,segs,start+180,end),cutoff_utc_s=end+100)
    assert r.factors[0].net_reference.available_at_utc_s==end+100

def test_cross_phase_window_keeps_same_session_estimator_history():
    bars,segs,start,end=make(pre=True);f=calc((bars,segs,start,end)).factors[0]
    assert f.full_gross_usd==100800 and f.net_reference is not None
    assert f.net_reference.key.phase=="RTH" and f.net_reference.key.interval_seconds==300

def test_windows_with_same_endpoint_but_different_anchor_cannot_share_baseline():
    bars,segs,start,end=make();a=calc((bars,segs,start,end)).factors[0]
    b=calc((bars,segs,start+60,end)).factors[0]
    assert a.gross_reference.key!=b.gross_reference.key

def test_actual_roster_not_just_version_string_enters_reference_identity():
    bars,segs,start,end=make();a=calc((bars,segs,start,end)).factors[0]
    changed=[replace(groups()[0],member_ids=("A","C"))]
    b=w().measure_windows(bars,changed,segs,start_utc_s=start,end_utc_s=end,cutoff_utc_s=end+2,config=replace(m.disclosed_core_config(),min_returns=2)).factors[0]
    assert a.gross_reference.key.membership_id!=b.gross_reference.key.membership_id

def test_corrected_history_never_manufactures_as_observed_reference():
    bars,segs,start,end=make();bars=[replace(b,available_at_utc_s=None) for b in bars]
    f=calc((bars,segs,start,end),mode="corrected_history").factors[0]
    assert f.full_gross_usd==100800 and f.gross_reference is None and f.net_reference is None
    assert f.availability_eligible is False

def test_early_close_window_does_not_admit_1300_start_bar():
    bars,segs,start,end=make();seg=replace(segs[0],end_utc_s=start+210*60,session_class="EARLY_CLOSE")
    tail=[replace(b,segment=seg,start_utc_s=seg.end_utc_s-60,end_utc_s=seg.end_utc_s,available_at_utc_s=seg.end_utc_s+2) for b in bars if b.start_utc_s==start]
    outside=[replace(b,start_utc_s=seg.end_utc_s,end_utc_s=seg.end_utc_s+60,available_at_utc_s=seg.end_utc_s+62) for b in tail]
    r=calc((tail+outside,(seg,),seg.end_utc_s-60,seg.end_utc_s),cutoff_utc_s=seg.end_utc_s+120)
    assert r.factors[0].expected_cells==2 and r.factors[0].full_gross_usd==20000
    assert r.factors[0].gross_reference.key.session_class=="EARLY_CLOSE"

def test_duplicate_eligible_revision_requires_incumbent_resolution():
    bars,segs,start,end=make()
    with pytest.raises(ValueError,match="duplicate"):
        calc((bars+[bars[0]],segs,start,end))

def test_changed_basis_within_security_window_is_not_one_money_series():
    bars,segs,start,end=make();bars[3]=replace(bars[3],basis_id="unadjusted/USD/action-v2")
    with pytest.raises(ValueError,match="basis"):
        calc((bars,segs,start,end))

def test_rows_must_match_supplied_calendar_segments():
    bars,segs,start,end=make();bars[0]=replace(bars[0],segment=replace(segs[0],calendar_ref="OTHER"))
    with pytest.raises(ValueError,match="segment"):
        calc((bars,segs,start,end))

@pytest.mark.parametrize("case",["forming","misaligned","empty","calendar_gap","overlap","unknown_mode"])
def test_invalid_window_or_calendar_refused(case):
    bars,segs,start,end=make()
    kw={}
    if case=="forming":kw["cutoff_utc_s"]=end-1
    if case=="misaligned":kw["start_utc_s"]=start+1
    if case=="empty":kw["end_utc_s"]=start
    if case=="calendar_gap":segs=(replace(segs[0],end_utc_s=start+120),replace(segs[0],start_utc_s=start+180))
    if case=="overlap":segs=(segs[0],segs[0])
    if case=="unknown_mode":kw["mode"]="pretend_live"
    with pytest.raises(ValueError):calc((bars,segs,start,end),**kw)


@pytest.mark.parametrize(("golden_case","expected_canonical_sha256"),[
    ("complete","b90642a93c8ea4bb17d73a600d26688a75b5fa2a503d7574d26c4ed0d6b07098"),
    ("corrected_history","4784158ab88c5c39cd38b87507b57679d0af5ab2e585d0e64d963c83b06605b8"),
    ("one_missing_minute","6c91d627535a359bdbc370111274b8585dc3c8793102bee0f47f69fece1bd2d6"),
    ("explicit_zero","299cf1239c29ea2cd977067d02047074bdbab95563ad6cdbc59a5c1ec781f37f"),
    ("multi_phase","11a239ee7048a8ee63a4b5f531b1ccc2573b9013a10bbff3fe928cf5364f2005"),
])
def test_full_window_canonical_output_bytes_stable_across_history_serialization(golden_case,expected_canonical_sha256):
    # Golden hashes captured from the exact accepted original PR #8677 head
    # 748bceb73ae025ee48782cb1c3d541497558e53a, before optimization.
    # They cover full hierarchy: values, baseline identities, timestamps,
    # missing vs zero, historical mode and source-window provenance.
    if golden_case=="complete":
        observed=calc()
    elif golden_case=="corrected_history":
        observed=calc(mode="corrected_history")
    elif golden_case=="one_missing_minute":
        bars,segs,start,end=make()
        observed=calc(([b for b in bars if not
                       (b.security_id=="A" and b.start_utc_s==start+60)],segs,start,end))
    elif golden_case=="explicit_zero":
        bars,segs,start,end=make()
        observed=calc(([replace(b,volume=0.) for b in bars],segs,start,end))
    else:
        observed=calc(make(pre=True))
    assert m.digest(asdict(observed))==expected_canonical_sha256
    assert observed.authority==m.AUTHORITY
