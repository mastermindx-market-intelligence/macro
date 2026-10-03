"""Synthetic behavior proofs; no market outcomes or trial registration are run."""
import importlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

BASE = 1789133400

def api():
    return importlib.import_module('engine.entry_radar.tactical_research')

def bars(closes=(101.,102.,103.), start=BASE, gaps=None, volume=10.):
    closes=list(closes); opens=[] if not closes else [100.]+closes[:-1]
    index=gaps if gaps is not None else [start+i*300 for i in range(len(closes))]
    return pd.DataFrame({'o':opens,'h':[max(a,b)+.1 for a,b in zip(opens,closes)],
                         'l':[min(a,b)-.1 for a,b in zip(opens,closes)],'c':closes,
                         'v':[volume]*len(closes)},index=index)

def config():
    return json.loads((Path(__file__).resolve().parents[1]/'research/species/tti_r1/config.json').read_text())

def good_feature():
    segment={'return':.01,'efficiency':.5,'above_bar_vwap_fraction':.8,
             'last_close':102.,'bar_vwap_proxy':101.,'low':99.}
    return {'comparable':True,'ah':dict(segment),'pre':dict(segment),
            'prior_close':100.,'prior_return':-.01,'three_day_change':-2.,'atr20':2.,
            'opening':None}

def test_rising_path_efficiency_is_one():
    f=api().segment_features(bars())
    assert f['efficiency']==pytest.approx(1.)
    assert f['return']==pytest.approx(.03)
    assert f['above_bar_vwap_fraction']==1.
    assert f['price_reference']=='hlc3_volume_proxy_not_trade_vwap'

def test_oscillation_reduces_efficiency_not_positive_return():
    f=api().segment_features(bars([102.,100.,103.]))
    assert f['return']==pytest.approx(.03)
    assert f['efficiency']==pytest.approx(3/7)

def test_flat_path_is_defined_not_nan():
    f=api().segment_features(bars([100.,100.,100.]))
    assert f['efficiency']==0.
    assert f['above_bar_vwap_fraction']==0.

def test_sparse_path_does_not_interpolate_bidding():
    f=api().segment_features(bars([101.,102.,103.],gaps=[BASE,BASE+300,BASE+4500]))
    assert f['observations']==3
    assert f['max_gap_minutes']==65
    assert f['span_minutes']==80
    assert f['efficiency']==pytest.approx(1.)

def test_zero_volume_is_not_synthetic_price_evidence():
    f=api().segment_features(bars(volume=0.))
    assert f['observations']==0 and f['input_rows']==3
    assert f['return'] is None and f['bar_vwap_proxy'] is None

def test_fractional_volume_is_preserved():
    f=api().segment_features(bars(volume=.25))
    assert f['volume']==pytest.approx(.75)

def test_empty_segment_is_explicit():
    f=api().segment_features(bars([]))
    assert f['observations']==0 and f['return'] is None

@pytest.mark.parametrize('column,value',[('c',float('nan')),('v',-1),('h',-10),('o',0)])
def test_invalid_visible_observation_refuses(column,value):
    x=bars();x.loc[BASE,column]=value
    with pytest.raises(ValueError): api().segment_features(x)

def test_duplicate_and_unsorted_epochs_refuse():
    x=bars()
    for changed in (pd.concat([x,x.iloc[:1]]),x.iloc[::-1]):
        with pytest.raises(ValueError): api().segment_features(changed)

def test_cutoff_excludes_unfinished_and_future_corrupt_values():
    x=bars();x.loc[BASE+600,'c']=float('nan')
    got=api().closed_prefix(x,BASE+599)
    assert list(got.index)==[BASE]
    assert api().segment_features(got)['return']==pytest.approx(.01)

def test_future_price_mutation_preserves_feature_prefix():
    x=bars();before=api().segment_features(api().closed_prefix(x,BASE+600))
    x.loc[BASE+600,['o','h','l','c']]=[900.,999.,800.,950.]
    assert api().segment_features(api().closed_prefix(x,BASE+600))==before

def test_returned_prefix_does_not_alias_source():
    x=bars();view=api().closed_prefix(x,BASE+300);view.loc[BASE,'c']=200.
    assert x.loc[BASE,'c']==101.

def test_persistence_and_weakness_have_separate_identity():
    f=good_feature();out=api().select_arms(f,config())
    assert set(out)=={'ALL_EARLY','ALL_LATE','GAP_UP','PERSISTENT','WEAKNESS_PERSISTENT','WEAKNESS_RECLAIM'}
    f['prior_return']=.01;f['three_day_change']=1.
    assert 'PERSISTENT' in api().select_arms(f,config())
    assert 'WEAKNESS_PERSISTENT' not in api().select_arms(f,config())

def test_gapped_up_is_not_equivalent_to_persistence():
    f=good_feature();f['ah']['efficiency']=.01
    out=api().select_arms(f,config())
    assert 'GAP_UP' in out and 'PERSISTENT' not in out

def test_missing_evidence_never_becomes_false_weakness():
    f=good_feature();f['prior_return']=None;f['three_day_change']=None
    assert 'WEAKNESS_PERSISTENT' not in api().select_arms(f,config())

def test_incomparable_input_abstains_all_arms():
    f=good_feature();f['comparable']=False
    assert api().select_arms(f,config())==()

def test_open_accept_requires_new_completed_information():
    f=good_feature();assert 'PERSISTENT_OPEN_ACCEPT' not in api().select_arms(f,config())
    f['opening']={'complete':True,'last_close':103.,'bar_vwap_proxy':102.5,'low':100.}
    assert 'PERSISTENT_OPEN_ACCEPT' in api().select_arms(f,config())
    f['opening']['complete']=False
    assert 'PERSISTENT_OPEN_ACCEPT' not in api().select_arms(f,config())

def test_touch_same_bar_is_ambiguous():
    x=bars([100.]);x.loc[BASE,['h','l']]=[102.,98.]
    assert api().first_touch(x,100.,2.)=='same_bar_ambiguous'

def test_touch_uses_first_hit_not_later_rescue():
    x=bars([99.,103.]);x.loc[BASE,'h']=100.1
    assert api().first_touch(x,100.,2.)=='adverse_first'

def test_outcome_uses_entry_open_not_previous_close():
    x=bars([101.,102.]);b=bars([100.,100.]);expected=[BASE,BASE+300]
    o=api().fixed_outcome(x,b,BASE,BASE+600,1.,2.,expected)
    assert o['raw_return']==pytest.approx(.02)
    assert o['beta_residual']==pytest.approx(.02)
    assert o['status']=='available' and o['execution_proven'] is False

def test_missing_intermediate_bar_censors_not_last_available_exit():
    x=bars([101.,102.,103.]);expected=[BASE,BASE+300,BASE+600]
    o=api().fixed_outcome(x.drop(BASE+300),x,BASE,BASE+900,1.,2.,expected)
    assert o['status']=='censored' and o['raw_return'] is None

def test_missing_benchmark_does_not_mean_zero_market_return():
    x=bars([101.,102.]);b=x.iloc[:0]
    o=api().fixed_outcome(x,b,BASE,BASE+600,1.,2.,[BASE,BASE+300])
    assert o['raw_return']==pytest.approx(.02) and o['beta_residual'] is None

def test_outcome_excludes_future_endpoint_extension():
    x=bars([101.,102.,500.]);b=bars([100.,100.,100.])
    o=api().fixed_outcome(x,b,BASE,BASE+600,1.,2.,[BASE,BASE+300])
    assert o['raw_return']==pytest.approx(.02)

def test_negative_or_unknown_beta_does_not_fabricate_excess():
    x=bars()
    for beta in (None,float('nan'),-1):
        o=api().fixed_outcome(x,x,BASE,BASE+900,beta,2.,[BASE,BASE+300,BASE+600])
        assert o['beta_residual'] is None


def test_future_duplicate_outside_cutoff_does_not_change_prefix():
    x=bars([101.,102.,103.])
    future=pd.concat([x.iloc[[2]],x.iloc[[2]]])
    source=pd.concat([x.iloc[:2],future])
    got=api().closed_prefix(source,BASE+600)
    assert list(got.index)==[BASE,BASE+300]


def test_invalid_expected_outcome_bar_censors_without_erasing_fire():
    x=bars([101.,102.]); b=bars([100.,100.]); x.loc[BASE+300,'c']=float('nan')
    out=api().fixed_outcome(x,b,BASE,BASE+600,1.,2.,[BASE,BASE+300])
    assert out['status']=='censored' and out['raw_return'] is None


def test_future_duplicate_outside_outcome_path_is_ignored():
    x=bars([101.,102.,103.]); future=pd.concat([x.iloc[[2]],x.iloc[[2]]]); source=pd.concat([x.iloc[:2],future])
    b=bars([100.,100.,100.])
    out=api().fixed_outcome(source,b,BASE,BASE+600,1.,2.,[BASE,BASE+300])
    assert out['status']=='available' and out['raw_return']==pytest.approx(.02)

# TTI R1-B v4 fixed-outcome / LOD research tests. Outcome evaluation lives
# outside W3 detector suites so PIT-23 remains outcome-blind. Synthetic only.
def _ttib_config():
    return (Path(__file__).resolve().parents[1] /
            "research/species/tti_r1b/config_v4.json").read_bytes()


# Moved byte-for-byte in substance from the W3 suite after PIT-23 correctly
# rejected outcome-shaped test identifiers there.
def _ttib_outcome_frames(day=None):
    from datetime import date
    import pandas as pd
    from engine.session_digest import session_window_et
    day = day or date(2026, 9, 17)
    start, close = session_window_et(day)
    index = pd.date_range(start, close - pd.Timedelta(minutes=5), freq='5min')
    stock = pd.DataFrame([[100.0, 100.2, 99.8, 100.0, 100.0] for _ in index],
                         index=index, columns=['open','high','low','close','volume'])
    qqq = pd.DataFrame([[100.0, 100.1, 99.9, 100.0, 100.0] for _ in index],
                       index=index, columns=['open','high','low','close','volume'])
    return stock, qqq


def _ttib_outcome_event(day=None):
    from datetime import date, timedelta
    from engine.session_digest import session_window_et
    day = day or date(2026, 9, 17)
    start, _ = session_window_et(day)
    return {
        'selector': 'EXHAUSTION_RECLAIM',
        'anchor_id': f'AMD:{day.isoformat()}:synthetic',
        'candidate_at': (start + timedelta(minutes=15)).isoformat(),   # 09:45 decision
        'decision_at': (start + timedelta(minutes=25)).isoformat(),    # 09:55 confirmation
        'entry_reference_at': (start + timedelta(minutes=30)).isoformat(),
        'confirmation_delay_bars': 2,
        'processing_latency_minutes': 5,
        'candidate_low': 99.0,
        'episode_low': 98.8,
        'prior_atr': 2.0,
        'previous_regular_close': 101.0,
        'authority': 'research_construction_only',
    }


def test_TTIB_outcome_uses_delayed_entry_open_and_exact_30m_path():
    from datetime import date, timedelta
    from engine.entry_radar.tactical_exhaustion import measure_event_outcome
    from engine.session_digest import session_window_et
    day=date(2026,9,17); start,_=session_window_et(day)
    stock,qqq=_ttib_outcome_frames(day); event=_ttib_outcome_event(day)
    # Confirmation path undercuts candidate low, but no later break of episode low.
    stock.loc[start+timedelta(minutes=20),'low']=98.8
    # Fixed 30m path: target first at second post-entry bar, end +0.6%.
    stock.loc[start+timedelta(minutes=35),'high']=101.2
    stock.loc[start+timedelta(minutes=55),['high','close']]=[100.7,100.6]
    qqq.loc[start+timedelta(minutes=55),['high','close']]=[100.3,100.2]
    got=measure_event_outcome(stock,qqq,event=event,session=day,horizon='30m',
                              beta=2.0,cost_bps=25,config_bytes=_ttib_config())
    assert got['status']=='available'
    assert got['entry_open']==pytest.approx(100.0)
    assert got['raw_return']==pytest.approx(0.006)
    assert got['benchmark_return']==pytest.approx(0.002)
    assert got['beta_residual']==pytest.approx(0.002)
    assert got['net_beta_residual']==pytest.approx(-0.0005)
    assert got['touch']=='target_first'
    assert got['candidate_lod_survives'] is False
    assert got['episode_lod_survives'] is True
    assert got['candidate_delay_atr']==pytest.approx(0.5)
    assert got['episode_delay_atr']==pytest.approx(0.6)
    assert got['remaining_to_prior_close_atr']==pytest.approx(0.5)
    assert got['execution_proven'] is False and got['may_trade'] is False


def test_TTIB_outcome_same_bar_touch_stays_ambiguous():
    from datetime import date, timedelta
    from engine.entry_radar.tactical_exhaustion import measure_event_outcome
    from engine.session_digest import session_window_et
    day=date(2026,9,17); start,_=session_window_et(day)
    stock,qqq=_ttib_outcome_frames(day); event=_ttib_outcome_event(day)
    stock.loc[start+timedelta(minutes=35),['high','low']]=[101.2,98.8]
    got=measure_event_outcome(stock,qqq,event=event,session=day,horizon='30m',
                              beta=1.0,cost_bps=10,config_bytes=_ttib_config())
    assert got['touch']=='same_bar_ambiguous'


def test_TTIB_outcome_missing_or_zero_volume_bar_censors_exact_path_not_fire():
    from datetime import date, timedelta
    from engine.entry_radar.tactical_exhaustion import measure_event_outcome
    from engine.session_digest import session_window_et
    day=date(2026,9,17); start,_=session_window_et(day); event=_ttib_outcome_event(day)
    stock,qqq=_ttib_outcome_frames(day)
    missing=stock.drop(start+timedelta(minutes=40))
    got=measure_event_outcome(missing,qqq,event=event,session=day,horizon='30m',
                              beta=1.0,cost_bps=25,config_bytes=_ttib_config())
    assert got['status']=='censored' and got['reason']=='stock_path_missing_or_ambiguous'
    stock2,qqq2=_ttib_outcome_frames(day); stock2.loc[start+timedelta(minutes=40),'volume']=0
    got2=measure_event_outcome(stock2,qqq2,event=event,session=day,horizon='30m',
                               beta=1.0,cost_bps=25,config_bytes=_ttib_config())
    assert got2['status']=='censored' and got2['reason']=='stock_path_invalid'


def test_TTIB_outcome_missing_benchmark_never_becomes_zero_market_return():
    from datetime import date, timedelta
    from engine.entry_radar.tactical_exhaustion import measure_event_outcome
    from engine.session_digest import session_window_et
    day=date(2026,9,17); start,_=session_window_et(day); event=_ttib_outcome_event(day)
    stock,qqq=_ttib_outcome_frames(day); qqq=qqq.drop(start+timedelta(minutes=40))
    got=measure_event_outcome(stock,qqq,event=event,session=day,horizon='30m',
                              beta=1.5,cost_bps=25,config_bytes=_ttib_config())
    assert got['status']=='available'
    assert got['benchmark_return'] is None and got['beta_residual'] is None
    assert got['net_beta_residual'] is None


def test_TTIB_outcome_horizon_does_not_read_future_corrupt_bar_but_lod_becomes_unavailable():
    from datetime import date, timedelta
    import math
    from engine.entry_radar.tactical_exhaustion import measure_event_outcome
    from engine.session_digest import session_window_et
    day=date(2026,9,17); start,_=session_window_et(day); event=_ttib_outcome_event(day)
    stock,qqq=_ttib_outcome_frames(day)
    # This is well after the 30m endpoint; fixed return remains measurable, LOD is not.
    stock.loc[start+timedelta(minutes=180),'high']=float('nan')
    got=measure_event_outcome(stock,qqq,event=event,session=day,horizon='30m',
                              beta=1.0,cost_bps=25,config_bytes=_ttib_config())
    assert got['status']=='available'
    assert got['candidate_lod_survives'] is None and got['episode_lod_survives'] is None
    assert got['lod_status']=='unavailable'


def test_TTIB_outcome_close_horizon_requires_every_remaining_session_bar():
    from datetime import date, timedelta
    from engine.entry_radar.tactical_exhaustion import measure_event_outcome
    from engine.session_digest import session_window_et
    day=date(2026,9,17); start,_=session_window_et(day); event=_ttib_outcome_event(day)
    stock,qqq=_ttib_outcome_frames(day)
    stock=stock.drop(start+timedelta(minutes=300))
    got=measure_event_outcome(stock,qqq,event=event,session=day,horizon='close',
                              beta=1.0,cost_bps=25,config_bytes=_ttib_config())
    assert got['status']=='censored'
    assert got['reason']=='stock_path_missing_or_ambiguous'


def test_TTIB_outcome_refuses_retargeted_config_cost_or_event_clock():
    from datetime import date, timedelta
    from engine.entry_radar.tactical_exhaustion import measure_event_outcome
    from engine.session_digest import session_window_et
    day=date(2026,9,17); start,_=session_window_et(day); stock,qqq=_ttib_outcome_frames(day)
    event=_ttib_outcome_event(day)
    with pytest.raises(ValueError,match='cost'):
        measure_event_outcome(stock,qqq,event=event,session=day,horizon='30m',beta=1.0,cost_bps=17,config_bytes=_ttib_config())
    bad=dict(event); bad['entry_reference_at']=(start+timedelta(minutes=31)).isoformat()
    got=measure_event_outcome(stock,qqq,event=bad,session=day,horizon='30m',beta=1.0,cost_bps=25,config_bytes=_ttib_config())
    assert got['status']=='censored' and got['reason']=='entry_off_session_grid'
