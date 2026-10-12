"""Original controlled fixtures. No market data or institutional-flow truth."""
import importlib.util
import math
from pathlib import Path
import sys
import pytest
from scipy.special import stdtr, ndtr

HERE = Path(__file__).parent

def core():
    path = HERE / 'pressure.py'
    assert path.exists(), 'pressure prototype has not been implemented'
    if 'factor_atlas_pressure' not in sys.modules:
        spec = importlib.util.spec_from_file_location('factor_atlas_pressure', path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
    return sys.modules['factor_atlas_pressure']

# Explicit synthetic UTC envelope; not proof of a real exchange calendar.
T = 1780320600  # 2026-06-01 13:30 UTC / 09:30 EDT

def fixtures(prices=(100,101,100,102,101), *, symbol='HOUSE:A', phase='RTH',
             offset=0, session='2026-06-01', available=True, volumes=None):
    m=core()
    seg=m.Segment(session,phase,T+offset,T+offset+390*60,'SYNTHETIC_CALENDAR','FULL')
    vols=volumes if volumes is not None else [100.0]*len(prices)
    return [m.Bar(symbol,seg,T+offset+k*60,T+offset+(k+1)*60,
                  T+offset+(k+1)*60+2 if available else None,
                  p,vols[k],None,'unadjusted/USD','FIXTURE_REV_1','FIXTURE_RIGHTS')
            for k,p in enumerate(prices)]

def config(**kw):
    return core().BVCConfig(min_returns=2,**kw)

def run(bars, **kw):
    return core().bvc_series(bars,config(),cutoff_utc_s=T+90000,**kw)

@pytest.mark.parametrize('x',[-100.,-3.,-1.,0.,1.,3.,100.])
def test_student_cdf_matches_library(x):
    m=core(); actual=m.buy_fraction(x,1.,'student_t',.25,'neutral')
    assert actual == pytest.approx(float(stdtr(.25,x)),abs=1e-14)
    assert m.buy_fraction(-x,1.,'student_t',.25,'neutral') == pytest.approx(1-actual)

@pytest.mark.parametrize('x',[-3.,0.,3.])
def test_normal_comparator(x):
    assert core().buy_fraction(x,1.,'normal',None,'neutral') == pytest.approx(float(ndtr(x)))

def test_first_bar_is_explicit_neutral_not_classified():
    x=run(fixtures([100]))[0]
    assert (x.buy_fraction,x.net_usd,x.buy_usd,x.sell_usd)==(0.5,0.0,5000.0,5000.0)
    assert x.state=='FIRST_BAR_NEUTRAL' and not x.directionally_usable

def test_warmup_is_null_not_zero():
    x=run(fixtures([100,101]))[-1]
    assert x.state=='INSUFFICIENT_HISTORY' and x.net_usd is None and x.gross_usd==10100

def test_lagged_ddof_one_excludes_current_return():
    bars=fixtures([100,101,100,120]); x=run(bars)[-1]
    prior=[.01,100/101-1]
    sd=math.sqrt(sum((r-sum(prior)/2)**2 for r in prior))
    assert x.sigma==pytest.approx(sd)
    assert x.n_history==2
    assert x.buy_fraction==pytest.approx(float(stdtr(.25,.20/sd)))

def test_zero_sigma_default_and_limit_are_distinct():
    m=core()
    assert m.buy_fraction(.01,0,'student_t',.25,'neutral')==.5
    assert m.buy_fraction(.01,0,'student_t',.25,'one_sided_limit')==1
    assert m.buy_fraction(-.01,0,'student_t',.25,'one_sided_limit')==0
    assert m.buy_fraction(0,0,'student_t',.25,'one_sided_limit')==.5
    x=run(fixtures([100,100,100,101]))[-1]
    assert x.state=='ZERO_VOL_NEUTRAL' and x.net_usd==0 and not x.directionally_usable

def test_zero_volume_does_not_create_return_or_missing_flow():
    x=run(fixtures([100,101,102],volumes=[100,0,100]))
    assert x[1].state=='ZERO_VOLUME' and x[1].gross_usd==0 and x[1].net_usd==0
    assert x[2].state=='GAP_NEUTRAL'

def test_gap_not_signed_as_one_minute_return():
    bars=fixtures(); del bars[3]
    assert run(bars)[-1].state=='GAP_NEUTRAL'

def test_phase_reset_no_premarket_carry():
    bars=fixtures()+fixtures([200],phase='AH',offset=390*60)
    assert run(bars)[-1].state=='FIRST_BAR_NEUTRAL'

def test_next_session_reset():
    bars=fixtures()+fixtures([200],offset=86400,session='2026-06-02')
    assert run(bars)[-1].state=='FIRST_BAR_NEUTRAL'

def test_basis_change_cannot_bridge_split():
    from dataclasses import replace
    bars=fixtures(); bars[-1]=replace(bars[-1],basis_id='unadjusted/USD/revision2')
    assert run(bars)[-1].state=='FIRST_BAR_NEUTRAL'

def test_vwap_and_close_notional_basis_are_explicit():
    from dataclasses import replace
    x=run(fixtures([100]))[0]
    y=run([replace(fixtures([100])[0],vwap=99.)])[0]
    assert x.gross_usd==10000 and x.gross_basis=='bar_close_x_volume_proxy'
    assert y.gross_usd==9900 and y.gross_basis=='bar_vwap_x_volume_estimate'

def test_accounting_bounds():
    for x in run(fixtures([100,120,85,99,123,97,30,400,100])):
        if x.net_usd is not None:
            assert abs(x.net_usd)<=x.gross_usd+1e-8
            assert x.buy_usd+x.sell_usd==pytest.approx(x.gross_usd)
            assert x.buy_usd-x.sell_usd==pytest.approx(x.net_usd,abs=1e-8)

def test_input_order_deterministic():
    bars=fixtures()+fixtures(symbol='HOUSE:B')
    assert run(bars)==run(list(reversed(bars)))

def test_prefix_integrity_future_prices_and_duplicates_ignored():
    from dataclasses import replace
    m=core(); bars=fixtures(); cutoff=bars[3].available_at_utc_s
    prefix=m.bvc_series(bars[:4],config(),cutoff_utc_s=cutoff)
    future=[replace(bars[4],close=-100),bars[4],bars[4]]
    assert m.bvc_series(bars[:4]+future,config(),cutoff_utc_s=cutoff)==prefix

def test_close_and_availability_are_separate():
    m=core(); bars=fixtures([100]); b=bars[0]
    assert m.bvc_series(bars,config(),cutoff_utc_s=b.end_utc_s)==()
    assert len(m.bvc_series(bars,config(),cutoff_utc_s=b.available_at_utc_s))==1

def test_missing_availability_no_historical_live_claim():
    with pytest.raises(ValueError,match='availability_missing'): run(fixtures(available=False))
    x=run(fixtures(available=False),mode='corrected_history')[0]
    assert not x.availability_eligible and x.mode=='corrected_history'

def test_duplicate_current_bar_refused():
    b=fixtures([100])[0]
    with pytest.raises(ValueError,match='duplicate'): run([b,b])

@pytest.mark.parametrize('field,value',[
    ('close',float('nan')),('close',0),('volume',-1),('volume',True),
    ('available_at_utc_s',T),('start_utc_s',True),('basis_id','split_adjusted/USD')])
def test_invalid_input_refused(field,value):
    from dataclasses import replace
    with pytest.raises(ValueError): run([replace(fixtures([100])[0],**{field:value})])

def test_early_close_and_straddle_refusal():
    from dataclasses import replace
    b=fixtures([100])[0]; early=replace(b.segment,end_utc_s=T+210*60,session_class='EARLY_CLOSE')
    last=replace(b,segment=early,start_utc_s=T+209*60,end_utc_s=T+210*60,available_at_utc_s=T+210*60+2)
    assert len(run([last]))==1
    with pytest.raises(ValueError,match='segment_boundary'):
        run([replace(last,start_utc_s=T+210*60,end_utc_s=T+211*60,available_at_utc_s=T+211*60+2)])

def test_sixty_wall_minutes_not_sixty_retained_rows():
    m=core(); bars=fixtures([100+(k%3) for k in range(85)])
    result=m.bvc_series(bars,m.BVCConfig(min_returns=20),cutoff_utc_s=T+90000)
    assert result[-1].n_history==60

def key(**kw):
    m=core(); values=dict(subject='HOUSE:FACTOR_A',phase='RTH',clock_minute=600,session_class='FULL',
        measure='minute_net_usd',estimator_id='bvc-lagged60-t025-v1',membership_id='HOUSE_ROSTER_V1',
        basis_id='unadjusted/USD',interval_seconds=60,currency='USD')
    values.update(kw); return m.MatchKey(**values)

def samples(values, *, k=None):
    from datetime import date,timedelta,datetime
    from zoneinfo import ZoneInfo
    m=core(); k=k or key(); start=date(2026,4,1)
    days=[(start+timedelta(days=i)).isoformat() for i in range(len(values))]
    ends=[int(datetime.fromisoformat(d+'T10:00:00').replace(tzinfo=ZoneInfo('America/New_York')).timestamp()) for d in days]
    rows=[m.Reference(k,d,e,e+2,float(v),10000.,True,f'SYNTHETIC_{i}') for i,(d,v,e) in enumerate(zip(days,values,ends))]
    target=m.Reference(k,'2026-06-01',T+1800,T+1802,50.,10000.,True,'SYNTHETIC_TARGET')
    return target,rows,tuple(days)

def baseline(values,**config_kw):
    m=core(); target,rows,days=samples(values)
    return m.matched_baseline(target,rows,days,m.BaselineConfig(**config_kw),cutoff_utc_s=T+1810)

def test_robust_median_mad_and_midrank():
    from dataclasses import replace
    m=core(); target,rows,days=samples(range(20)); target=replace(target,value=9.5)
    x=m.matched_baseline(target,rows,days,m.BaselineConfig(),cutoff_utc_s=T+1810)
    assert (x.n,x.median,x.mad,x.z_raw,x.percentile)==(20,9.5,5.,0.,.5)
    assert x.scale==pytest.approx(1.482602218505602*5)

def test_zero_mad_no_floor_is_null():
    x=baseline([0]*20)
    assert x.status=='ZERO_SCALE' and x.z_raw is None and x.scale==0

def test_zero_mad_with_explicit_floor_flagged():
    x=baseline([0]*20,absolute_floor=10.)
    assert x.z_raw==5 and x.floor_applied and x.status=='FLOORED_SCALE'

def test_clip_does_not_destroy_raw_z():
    x=baseline([0]*20,absolute_floor=1.,display_clip=12.)
    assert x.z_raw==50 and x.z_display==12

def test_minimum_observations_and_schedule_coverage():
    assert baseline(range(19)).status=='INSUFFICIENT_OBSERVATIONS'
    m=core(); target,rows,days=samples(range(30))
    x=m.matched_baseline(target,rows[:20],days,m.BaselineConfig(),cutoff_utc_s=T+1810)
    assert x.status=='INSUFFICIENT_COVERAGE' and x.coverage==pytest.approx(2/3)

def test_current_future_wrong_clock_incomplete_and_unavailable_excluded():
    from dataclasses import replace
    m=core(); target,rows,days=samples(range(20))
    extra=[replace(target,value=1e30),replace(rows[0],session_id='2026-06-02',value=1e30),
           replace(rows[0],key=key(clock_minute=601),value=1e30),
           replace(rows[0],available_at_utc_s=T+1900,value=1e30),
           replace(rows[0],complete=False,value=1e30)]
    a=m.matched_baseline(target,rows,days,m.BaselineConfig(),cutoff_utc_s=T+1810)
    b=m.matched_baseline(target,rows+extra,days,m.BaselineConfig(),cutoff_utc_s=T+1810)
    assert a==b

def test_roster_and_minute_vs_cumulative_cannot_mix():
    from dataclasses import replace
    m=core(); t,rows,days=samples(range(20))
    altered=[replace(x,key=key(membership_id='OTHER')) for x in rows]
    altered += [replace(x,key=key(measure='session_to_date_net_usd')) for x in rows]
    x=m.matched_baseline(t,altered,days,m.BaselineConfig(),cutoff_utc_s=T+1810)
    assert x.n==0 and x.z_raw is None

def test_duplicate_reference_revision_refused():
    m=core(); t,r,d=samples(range(20))
    with pytest.raises(ValueError,match='duplicate_reference'):
        m.matched_baseline(t,r+[r[0]],d,m.BaselineConfig(),cutoff_utc_s=T+1810)

def test_current_value_and_current_gross_not_in_reference_floor():
    from dataclasses import replace
    m=core(); t,r,d=samples([0]*20); c=m.BaselineConfig(relative_floor=.01)
    a=m.matched_baseline(t,r,d,c,cutoff_utc_s=T+1810)
    b=m.matched_baseline(replace(t,value=1e9,gross_usd=1e12),r,d,c,cutoff_utc_s=T+1810)
    assert a.reference_digest==b.reference_digest and a.scale==b.scale==100

def test_baseline_reference_order_determinism():
    m=core(); t,r,d=samples(range(20)); c=m.BaselineConfig()
    assert m.matched_baseline(t,r,d,c,cutoff_utc_s=T+1810)==m.matched_baseline(t,list(reversed(r)),d,c,cutoff_utc_s=T+1810)

def groups():
    m=core()
    return [m.Membership('HOUSE:ONE','v1','current_cohort',('HOUSE:A','HOUSE:B')),
            m.Membership('HOUSE:TWO','v1','current_cohort',('HOUSE:B','HOUSE:C'))]

def final_points():
    return [run(fixtures(symbol=s))[-1] for s in ('HOUSE:A','HOUSE:B','HOUSE:C')]

def test_overlap_transparency_and_unique_union():
    m=core(); r=m.aggregate_factors(final_points(),groups())
    assert r.union_gross_usd==30300
    assert r.sum_factor_gross_usd==40400
    assert r.duplicated_gross_usd==10100
    assert r.overlap==(('HOUSE:B',('HOUSE:ONE','HOUSE:TWO')),)
    assert all(x.gross_usd_observed==20200 for x in r.factors)
    assert r.factors[0].effective_n_gross==2

def test_missing_member_not_zero_full_net():
    r=core().aggregate_factors(final_points()[:1],groups())
    assert r.factors[0].estimated_net_usd is None
    assert r.factors[0].member_coverage==.5
    assert r.factors[1].gross_usd_observed==0 and r.factors[1].estimated_net_usd is None

def test_neutral_first_bars_do_not_fake_directional_coverage():
    points=[run(fixtures([100],symbol=s))[0] for s in ('HOUSE:A','HOUSE:B','HOUSE:C')]
    r=core().aggregate_factors(points,groups())
    assert all(x.directional_notional_coverage==0 and x.estimated_net_usd is None for x in r.factors)

def test_duplicate_membership_or_source_point_refused():
    m=core()
    with pytest.raises(ValueError,match='duplicate_member'):
        m.aggregate_factors(final_points(),[m.Membership('X','v1','current_cohort',('HOUSE:A','HOUSE:A'))])
    with pytest.raises(ValueError,match='duplicate_security'):
        m.aggregate_factors(final_points()+[final_points()[0]],groups())

def test_aggregate_replay_and_authority():
    m=core(); points=final_points(); memberships=groups()
    a=m.aggregate_factors(points,memberships)
    b=m.aggregate_factors(list(reversed(points)),list(reversed(memberships)))
    assert a==b
    assert all(v is False for v in dict(a.authority).values())


def test_bar_segment_session_date_matches_true_utc():
    from dataclasses import replace
    b=fixtures([100])[0]
    with pytest.raises(ValueError,match='session_clock_mismatch'):
        run([replace(b,segment=replace(b.segment,session_id='2026-05-31'))])


def test_reference_matched_clock_is_verified_not_just_string_equality():
    from dataclasses import replace
    t,rows,days=samples(range(20))
    with pytest.raises(ValueError,match='matched_clock_mismatch'):
        core().matched_baseline(t,[replace(rows[0],event_end_utc_s=rows[0].event_end_utc_s-60)]+rows[1:],days,
                                core().BaselineConfig(),cutoff_utc_s=T+1810)


def test_reference_session_date_cannot_launder_another_day():
    from dataclasses import replace
    t,rows,days=samples(range(20)); bad=replace(rows[0],session_id=rows[1].session_id)
    with pytest.raises(ValueError,match='session_clock_mismatch'):
        bad.validate()


def test_same_et_clock_matches_across_dst_offsets():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    m=core(); rows=[]
    for i,day in enumerate(('2026-03-06','2026-03-09','2026-03-10')):
        end=int(datetime.fromisoformat(day+'T10:00:00').replace(tzinfo=ZoneInfo('America/New_York')).timestamp())
        rows.append(m.Reference(key(),day,end,end+2,float(i),1000.,True,'SYNTHETIC_DST'))
    assert rows[1].event_end_utc_s-rows[0].event_end_utc_s==71*3600
    result=m.matched_baseline(rows[-1],rows[:-1],('2026-03-06','2026-03-09'),
                             m.BaselineConfig(min_observations=2),cutoff_utc_s=rows[-1].available_at_utc_s)
    assert result.n==2 and result.status=='OK'


@pytest.mark.parametrize('field,value',[
    ('gross_usd',float('nan')),('gross_usd',-1),('net_usd',1e12),
    ('buy_fraction',1.5),('buy_usd',-5),('authority',(('may_trade',True),)),
    ('input_digest','invented'),('gross_basis','direct_print_truth')])
def test_aggregate_rejects_forged_derived_points(field,value):
    from dataclasses import replace
    points=final_points(); points[0]=replace(points[0],**{field:value})
    with pytest.raises(ValueError): core().aggregate_factors(points,groups())

def test_corrected_history_still_excludes_future_bars():
    from dataclasses import replace
    m=core(); bars=fixtures(); cutoff=bars[3].available_at_utc_s
    prefix=m.bvc_series(bars[:4],config(),cutoff_utc_s=cutoff,mode='corrected_history')
    future=[replace(bars[4],close=-100),bars[4],bars[4]]
    assert m.bvc_series(bars[:4]+future,config(),cutoff_utc_s=cutoff,mode='corrected_history')==prefix

def test_timestamp_presence_is_not_called_proof_of_source_custody():
    point=run(fixtures([100]))[0]
    assert hasattr(point,'availability_eligible') and not hasattr(point,'availability_proven')
