# Historical RED test contract — superseded by executed tests

This file preserves the initial pre-implementation RED packet. The first executed test failed with `ModuleNotFoundError` exactly as recorded below. Implementation later proceeded test-first on the same carrier; the current executable tests are `tests/test_tactical_research.py` and `tests/test_tactical_research_cli.py`, and current results/verification live in `TTI_R1A_REPORT.md` and `STATUS.md`. The code block below is retained as historical design evidence and is not the current complete test inventory.

```python
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
    closes=list(closes); opens=[100.]+closes[:-1]
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

```
