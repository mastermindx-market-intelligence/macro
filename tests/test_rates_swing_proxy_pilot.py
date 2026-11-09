"""Synthetic contract tests. No vendor access or real strategy evaluation."""
from __future__ import annotations
import copy
import numpy as np
import pandas as pd
import pytest
from research.rates_direction.swing_proxy_pilot import (
    parse_capture, build_features, label_paths, walk_forward, recent_state, SPEC,
)


def payload(days=80):
    starts=pd.bdate_range('2024-01-02',periods=days,tz='UTC')+pd.Timedelta(hours=12,minutes=20)
    periods=[]; ts=[]; quotes={k:[] for k in ['open','high','low','close']}
    n=0
    for day in starts:
        periods.append([{'start':int(day.timestamp()),'end':int((day+pd.Timedelta(hours=6,minutes=40)).timestamp())}])
        for j in range(7):
            t=day+pd.Timedelta(hours=j); c=4+.12*np.sin(n/8)+.01*np.cos(n/2.3)
            ts.append(int(t.timestamp()))
            for k,v in {'open':c-.001,'close':c,'high':c+.003,'low':c-.003}.items(): quotes[k].append(v)
            n+=1
    x={'meta':{'symbol':'^TNX','dataGranularity':'1h','exchangeTimezoneName':'America/Chicago',
               'tradingPeriods':{'regular':periods}},'timestamp':ts,'indicators':{'quote':[quotes]}}
    return {'chart':{'result':[x],'error':None}},starts[-1]+pd.Timedelta(days=1)


def small_spec():
    return {**SPEC,'warmup_bars':40,'minimum_training_labels':12,'horizon_bars':4,'delay_bars':1}


def test_session_anchored_bars_and_closing_stub():
    p,cut=payload(2); h,b,q=parse_capture(p,cut)
    assert len(h)==14 and len(b)==8
    assert b.duration_seconds.tolist()==[7200,7200,7200,2400]*2
    assert b.index[0]==pd.Timestamp('2024-01-02T14:20:00Z')
    assert b.index[3]==pd.Timestamp('2024-01-02T19:00:00Z')
    assert q['missing_expected_hourly_rows']==0


def test_live_and_irregular_rows_are_not_historical_bars():
    p,_=payload(1); x=p['chart']['result'][0]
    extra=x['timestamp'][0]+17*60
    x['timestamp'].insert(1,extra)
    for v in x['indicators']['quote'][0].values(): v.insert(1,v[0])
    h,b,q=parse_capture(p,'2024-01-02T12:51:03Z')
    assert b.empty and h.empty
    assert q['off_grid_rows']==1 and q['not_closed_hourly_rows']==7


def test_missing_and_invalid_rows_do_not_compact_the_grid():
    p,cut=payload(2); x=p['chart']['result'][0]
    x['indicators']['quote'][0]['high'][2]=None
    h,b,q=parse_capture(p,cut)
    assert len(b)==8 and not b.valid.iloc[1]
    assert b.index[2]==pd.Timestamp('2024-01-02T18:20:00Z')
    assert q['invalid_ohlc_rows']==1
    assert build_features(b,small_spec()).eligible.sum()==0


@pytest.mark.parametrize('mutation',['duplicate','reverse','wrong_symbol','bad_period'])
def test_unsafe_source_identity_or_grid_refused(mutation):
    p,cut=payload(1); x=p['chart']['result'][0]
    if mutation=='duplicate': x['timestamp'][1]=x['timestamp'][0]
    if mutation=='reverse': x['timestamp'][0],x['timestamp'][1]=x['timestamp'][1],x['timestamp'][0]
    if mutation=='wrong_symbol': x['meta']['symbol']='TVC:US10Y'
    if mutation=='bad_period': x['meta']['tradingPeriods']['regular'][0][0]['end']=0
    with pytest.raises(ValueError): parse_capture(p,cut)


def test_states_expire_and_do_not_count_histogram_twice():
    idx=pd.RangeIndex(6)
    up=pd.Series([True,False,False,False,False,False],index=idx)
    dn=pd.Series(False,index=idx); align=pd.Series(1,index=idx)
    assert recent_state(up,dn,align,3).tolist()==[1,1,1,0,0,0]


def test_features_are_future_and_prefix_invariant():
    p,cut=payload(); _,b,_=parse_capture(p,cut); f=build_features(b,small_spec())
    changed=b.copy(); changed.loc[changed.index[180:],['open','high','low','close']]+=7
    pd.testing.assert_frame_equal(f.iloc[:180],build_features(changed,small_spec()).iloc[:180])
    pd.testing.assert_frame_equal(f.iloc[:180],build_features(b.iloc[:180],small_spec()))


def test_label_ignores_origin_and_delay_highs():
    p,cut=payload(10); h,b,_=parse_capture(p,cut)
    h[['open','high','low','close']]=4.; b[['open','high','low','close']]=4.
    f=build_features(b,small_spec()); f['barrier_bp']=5.
    for j in b.hour_ids.iloc[0]+b.hour_ids.iloc[1]: h.loc[j,'high']=9.
    y=label_paths(h,b,f,small_spec())
    assert y[0]['label']=='no_hit' and y[0]['entry_reference']==4.


def test_hourly_order_and_same_hour_ambiguity():
    p,cut=payload(10); h,b,_=parse_capture(p,cut)
    h[['open','high','low','close']]=4.; b[['open','high','low','close']]=4.
    f=build_features(b,small_spec()); f['barrier_bp']=5.
    hours=b.hour_ids.iloc[2]
    h.loc[hours[0],'high']=4.1; h.loc[hours[1],'low']=3.9
    assert label_paths(h,b,f,small_spec())[0]['label']=='up'
    h.loc[hours[0],'low']=3.9
    assert label_paths(h,b,f,small_spec())[0]['label']=='ambiguous'


def test_unfinished_or_missing_full_horizon_censored():
    p,cut=payload(10); h,b,_=parse_capture(p,cut); f=build_features(b,small_spec())
    f['barrier_bp']=5.; b.loc[b.index[3],'valid']=False
    y=label_paths(h,b,f,small_spec())
    assert y[0]['label']=='censored' and y[-1]['label']=='censored'


def test_probabilities_and_training_cut_are_causal():
    p,cut=payload(); h,b,_=parse_capture(p,cut); spec=small_spec()
    f=build_features(b,spec); labels=label_paths(h,b,f,spec); rows=walk_forward(b,f,labels,spec)
    assert rows
    for r in rows:
        assert pd.Timestamp(r['last_training_target_end'])<pd.Timestamp(r['origin'])
        assert len(r['probabilities'])==9
        for probabilities in r['probabilities'].values():
            assert np.isfinite(probabilities).all() and min(probabilities)>0
            assert sum(probabilities)==pytest.approx(1.)
    changed=copy.deepcopy(labels)
    for j in range(180,len(changed)): changed[j]['label']='up'
    other=walk_forward(b,f,changed,spec)
    a=[r['probabilities'] for r in rows if r['origin_index']<=180]
    z=[r['probabilities'] for r in other if r['origin_index']<=180]
    assert a==z


def test_none_state_means_no_increment_over_the_baseline():
    p,cut=payload(); h,b,_=parse_capture(p,cut); spec=small_spec(); f=build_features(b,spec)
    for name in ['M','P','R','MP','MR','PR','MPR']: f[name]=0
    rows=walk_forward(b,f,label_paths(h,b,f,spec),spec)
    assert rows and all(r['probabilities']['MPR']==r['probabilities']['trend_vol'] for r in rows)


def test_missing_expected_timestamp_is_preserved():
    p,cut=payload(3); x=p['chart']['result'][0]
    del x['timestamp'][2]
    for v in x['indicators']['quote'][0].values(): del v[2]
    h,b,q=parse_capture(p,cut)
    assert len(h)==21 and len(b)==12 and q['missing_expected_hourly_rows']==1
    assert not h.valid.iloc[2] and not b.valid.iloc[1]


def test_parser_prefix_at_closed_boundary_never_uses_future_bar():
    p,cut=payload(3)
    _,full,_=parse_capture(p,cut)
    _,prefix,_=parse_capture(p,'2024-01-03T16:20:00Z')
    pd.testing.assert_frame_equal(full.loc[:'2024-01-03T16:20:00Z'],prefix)


def test_frozen_bytes_are_a_gate(tmp_path):
    from research.rates_direction.swing_proxy_pilot import verify_freeze,FROZEN_PATHS,SOURCE_SHA,file_hash
    for path in FROZEN_PATHS:
        p=tmp_path/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('frozen')
    receipt={'source_sha256':SOURCE_SHA,'spec':SPEC,'files':{p:file_hash(tmp_path/p) for p in FROZEN_PATHS}}
    verify_freeze(tmp_path,receipt)
    (tmp_path/FROZEN_PATHS[0]).write_text('changed')
    with pytest.raises(ValueError,match='post-freeze'): verify_freeze(tmp_path,receipt)


def test_summary_uses_same_origins_and_counts_neither_as_nonwin():
    from research.rates_direction.swing_proxy_pilot import summarize,MODELS,COMBINATIONS
    rows=[]
    for i,label in enumerate(['no_hit','ambiguous','down','up']):
        origin=pd.Timestamp('2024-01-01T12:00Z')+pd.Timedelta(days=i)
        rows.append({'origin_index':20*i,'origin':origin.isoformat(),'session':str(origin.date()),
                     'states':{m:1 for m in COMBINATIONS},
                     'probabilities':{m:[.2,.3,.5] for m in MODELS},
                     'outcome':{'label':label,'target_end_index':20*i+13,'barrier_bp':5,
                                'up_excursion_bp':6,'down_excursion_bp':-6}})
    s=summarize(rows)
    assert all(v['n']==3 for v in s['models'].values())
    m=s['models']['M']; assert m['nonoverlapping_episodes']==4 and m['resolved_episodes']==3
    assert m['wins']==1 and m['hit_fraction']==pytest.approx(1/3)
    assert not m['enough_for_ranking'] and not s['primary_promoted']


def test_summary_does_not_skip_ambiguous_episode_for_a_later_winner():
    from research.rates_direction.swing_proxy_pilot import summarize,MODELS,COMBINATIONS
    rows=[]
    for i,label in enumerate(['ambiguous','up']):
        rows.append({'origin_index':i,'origin':f'2024-01-01T1{2+i}:00:00Z','session':'2024-01-01',
                     'states':{m:1 for m in COMBINATIONS},'probabilities':{m:[.2,.3,.5] for m in MODELS},
                     'outcome':{'label':label,'target_end_index':i+13,'barrier_bp':5,
                                'up_excursion_bp':6,'down_excursion_bp':-6}})
    m=summarize(rows)['models']['M']
    assert m['nonoverlapping_episodes']==1 and m['resolved_episodes']==0
    assert m['hit_fraction'] is None
