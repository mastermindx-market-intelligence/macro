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


# ---------------------------------------------------------------------------
# TTI R1-B v4 — causal fresh-low / exhaustion / reclaim research primitives
# Frozen prereg/config: Macro #7274, v4 SHA256
# a8afab8d... prereg / 24b5a89f... config. No outcomes are opened here.
# ---------------------------------------------------------------------------

def turn_cfg():
    return {
        'study_id': 'tti-r1b-exhaustion-reclaim-v4',
        'decision_grain': '5m',
        'direction': 'long_only',
        'normal_rth_only': True,
        'candidate_decision_start_minute_et': 585,
        'candidate_decision_end_minute_et': 870,
        'strict_new_session_low': True,
        'candidate_positive_volume_required': True,
        'candidate_zero_range_is_unavailable': True,
        'running_low_positive_volume_only': True,
        'recent_impulse_all_three_bars_positive_volume': True,
        'confirmation_positive_volume_required': True,
        'base_displacement_atr_min': .50,
        'recent_impulse_bars': 3,
        'recent_impulse_atr_min': .20,
        'exhaustion_close_location_min': .60,
        'exhaustion_extension_atr_max': .15,
        'confirmation_window_bars': 3,
        'continuation_extension_atr': .25,
        'execution_latency_bars_after_decision': 1,
        'clock_bin_minutes': 30,
        'selectors': (
            'BASE_FRESH_LOW', 'EXHAUSTION_FORMING', 'RECLAIM_ONLY',
            'EXHAUSTION_RECLAIM', 'CONTINUATION_RISK',
        ),
    }


def turn_frame(rows, start=BASE):
    return pd.DataFrame(rows, index=[start + i * 300 for i in range(len(rows))],
                        columns=['o','h','l','c','v'], dtype=float)


def forming_reclaim_frame():
    return turn_frame([
        [104.0,104.1,103.5,103.8,100],
        [103.8,103.9,102.5,102.8,100],
        [102.8,102.8,102.0,102.6,100],  # candidate; loc=.75, ext=.125 ATR
        [102.6,103.2,102.2,103.0,100],  # reclaim above frozen 102.5
        [103.0,103.1,102.7,102.9,100],  # processing bar for confirmed event
        [102.9,103.4,102.8,103.2,100],  # confirmed price-reference entry open
        [103.2,103.5,103.0,103.3,100],
    ])


def events_by_selector(frame):
    out = api().scan_long_turn_events(
        frame, session_open_epoch=BASE, previous_close=105.0, atr=4.0, cfg=turn_cfg())
    return {row['selector']: row for row in out}


def test_r1b_v4_forming_reclaim_has_separate_candidate_confirmation_and_entry_clocks():
    got = events_by_selector(forming_reclaim_frame())
    assert set(got) == {'BASE_FRESH_LOW','EXHAUSTION_FORMING','RECLAIM_ONLY','EXHAUSTION_RECLAIM'}
    base = got['BASE_FRESH_LOW']; confirmed = got['EXHAUSTION_RECLAIM']
    assert base['candidate_epoch'] == BASE + 2*300
    assert base['decision_epoch'] == BASE + 3*300
    assert base['entry_epoch'] == BASE + 4*300  # one full processing bar
    assert confirmed['confirmation_bar_epoch'] == BASE + 3*300
    assert confirmed['decision_epoch'] == BASE + 4*300
    assert confirmed['entry_epoch'] == BASE + 5*300
    assert confirmed['confirmation_delay_bars'] == 1
    assert confirmed['candidate_low'] == 102.0
    assert confirmed['episode_low'] == 102.0


def test_r1b_v4_equal_low_is_not_a_fresh_low():
    x = forming_reclaim_frame().iloc[:3].copy(); x.loc[BASE + 2*300,'l'] = 102.5
    assert api().scan_long_turn_events(x, session_open_epoch=BASE,
        previous_close=105., atr=4., cfg=turn_cfg()) == ()


def test_r1b_v4_zero_volume_candidate_refuses_candidate_without_fabricating_nonfire():
    x = forming_reclaim_frame(); x.loc[BASE + 2*300,'v'] = 0.
    assert api().scan_long_turn_events(x, session_open_epoch=BASE,
        previous_close=105., atr=4., cfg=turn_cfg()) == ()


def test_r1b_v4_base_can_reclaim_without_forming_exhaustion():
    x = forming_reclaim_frame(); x.loc[BASE + 2*300,'c'] = 102.2  # close location .25
    got = events_by_selector(x)
    assert 'BASE_FRESH_LOW' in got and 'RECLAIM_ONLY' in got
    assert 'EXHAUSTION_FORMING' not in got and 'EXHAUSTION_RECLAIM' not in got


def test_r1b_v4_continuation_wins_before_a_later_reclaim():
    x = forming_reclaim_frame()
    x.loc[BASE + 3*300,['o','h','l','c']] = [102.6,102.7,100.7,100.9]
    x.loc[BASE + 4*300,['o','h','l','c']] = [100.9,103.2,100.8,103.0]
    got = events_by_selector(x)
    assert 'CONTINUATION_RISK' in got
    assert got['CONTINUATION_RISK']['race'] == 'continuation'
    assert got['CONTINUATION_RISK']['candidate_epoch'] == BASE + 2*300
    # A distinct later fresh-low episode may lawfully qualify a reclaim selector;
    # it cannot rewrite the first candidate's continuation outcome.
    for name in ('RECLAIM_ONLY','EXHAUSTION_RECLAIM'):
        if name in got:
            assert got[name]['candidate_epoch'] > BASE + 2*300


def test_r1b_v4_three_bar_neither_expires_and_zero_volume_race_is_unavailable():
    x = forming_reclaim_frame()
    for i, close in zip((3,4,5),(102.3,102.4,102.2)):
        x.loc[BASE+i*300,['o','h','l','c']] = [102.3,102.45,102.1,close]
    got = events_by_selector(x)
    assert set(got) == {'BASE_FRESH_LOW','EXHAUSTION_FORMING'}
    y = forming_reclaim_frame(); y.loc[BASE+3*300,'v']=0.
    got2 = events_by_selector(y)
    assert set(got2) == {'BASE_FRESH_LOW','EXHAUSTION_FORMING'}


def two_anchor_frame():
    rows = [
        [104.0,104.1,103.5,103.8,100],
        [103.8,103.9,102.5,102.8,100],
        [102.8,102.8,102.0,102.6,100],  # base/forming #1
        [102.6,102.7,102.1,102.3,100],
        [102.3,102.45,102.05,102.3,100],
        [102.3,102.4,102.02,102.2,100],  # #1 expires
        [102.2,102.3,101.95,102.1,100],
        [102.1,102.2,101.4,102.05,100],  # base/forming #2, new 30m bin
        [102.05,102.7,101.8,102.65,100], # #2 reclaim over frozen 101.95
        [102.65,102.8,102.4,102.7,100], # processing
        [102.7,103.1,102.5,102.9,100],
    ]
    return turn_frame(rows)


def test_r1b_v4_unqualified_early_anchor_does_not_consume_later_reclaim_selector():
    got = events_by_selector(two_anchor_frame())
    assert got['BASE_FRESH_LOW']['candidate_epoch'] == BASE+2*300
    assert got['EXHAUSTION_FORMING']['candidate_epoch'] == BASE+2*300
    assert got['RECLAIM_ONLY']['candidate_epoch'] == BASE+7*300
    assert got['EXHAUSTION_RECLAIM']['candidate_epoch'] == BASE+7*300


def test_r1b_v4_multiple_selectors_can_share_anchor_but_second_same_selector_is_refused():
    got = events_by_selector(forming_reclaim_frame())
    anchor = got['BASE_FRESH_LOW']['candidate_epoch']
    assert got['EXHAUSTION_FORMING']['candidate_epoch'] == anchor
    assert got['RECLAIM_ONLY']['candidate_epoch'] == anchor
    assert got['EXHAUSTION_RECLAIM']['candidate_epoch'] == anchor
    assert len([x for x in api().scan_long_turn_events(two_anchor_frame(), session_open_epoch=BASE,
        previous_close=105., atr=4., cfg=turn_cfg()) if x['selector']=='BASE_FRESH_LOW']) == 1


def test_r1b_v4_future_corruption_or_duplicate_does_not_erase_earlier_base_or_forming_fire():
    x = forming_reclaim_frame().iloc[:3].copy()
    clean = api().scan_long_turn_events(x, session_open_epoch=BASE,
        previous_close=105., atr=4., cfg=turn_cfg())
    future = pd.DataFrame({'o':[1.,1.], 'h':[0.,0.], 'l':[2.,2.], 'c':[float('nan'),float('nan')],
                           'v':[-1.,-1.]}, index=[BASE+20*300, BASE+20*300])
    dirty = pd.concat([x,future])
    got = api().scan_long_turn_events(dirty, session_open_epoch=BASE,
        previous_close=105., atr=4., cfg=turn_cfg())
    def immediate(rows):
        return tuple((r['selector'],r['candidate_epoch'],r['decision_epoch'],r['entry_epoch'])
                     for r in rows if r['selector'] in ('BASE_FRESH_LOW','EXHAUSTION_FORMING'))
    assert immediate(got) == immediate(clean)


def test_r1b_v4_control_census_is_bin_local_and_independent_of_future_family_labels():
    x = two_anchor_frame()
    before = api().base_turn_control_census(x, session_open_epoch=BASE,
        previous_close=105., atr=4., cfg=turn_cfg())
    changed = x.copy()
    changed.loc[BASE+8*300,'c'] = 101.7  # remove the second anchor's later reclaim label
    after = api().base_turn_control_census(changed, session_open_epoch=BASE,
        previous_close=105., atr=4., cfg=turn_cfg())
    assert before == after
    assert tuple(r['candidate_epoch'] for r in before) == (BASE+2*300, BASE+7*300)
    assert tuple(r['clock_bin'] for r in before) == (0,1)



def test_r1b_v4_price_reference_is_after_latency_and_reports_availability_without_gating_fire():
    got = events_by_selector(forming_reclaim_frame())
    assert got['BASE_FRESH_LOW']['entry_reference_available'] is True
    assert got['BASE_FRESH_LOW']['entry_open'] == pytest.approx(103.0)
    assert got['EXHAUSTION_RECLAIM']['entry_reference_available'] is True
    assert got['EXHAUSTION_RECLAIM']['entry_open'] == pytest.approx(102.9)

    x = forming_reclaim_frame().drop(BASE + 5*300)
    events = {r['selector']:r for r in api().scan_long_turn_events(
        x, session_open_epoch=BASE, previous_close=105., atr=4., cfg=turn_cfg())}
    assert 'EXHAUSTION_RECLAIM' in events  # fire survives unavailable entry reference
    assert events['EXHAUSTION_RECLAIM']['entry_reference_available'] is False
    assert events['EXHAUSTION_RECLAIM']['entry_open'] is None


def test_r1b_v4_zero_volume_entry_reference_does_not_erase_fire():
    x = forming_reclaim_frame(); x.loc[BASE+5*300,'v']=0.
    got = events_by_selector(x)
    assert got['EXHAUSTION_RECLAIM']['entry_reference_available'] is False
    assert got['EXHAUSTION_RECLAIM']['entry_open'] is None


def test_r1b_v4_candidate_low_and_preconfirmation_episode_low_remain_separate():
    x = forming_reclaim_frame()
    # The first confirmation bar undercuts the candidate intrabar but closes over
    # the frozen reclaim level; close-based continuation does not fire.
    x.loc[BASE+3*300,['o','h','l','c']] = [102.6,103.2,100.8,103.0]
    got = events_by_selector(x)
    ev = got['EXHAUSTION_RECLAIM']
    assert ev['candidate_low'] == 102.0
    assert ev['episode_low'] == 100.8
    assert ev['race'] == 'reclaim'
