"""Synthetic counterexamples; never a market accuracy estimate."""
from pathlib import Path
import importlib.util, sys
import pytest

def module():
    p=Path(__file__).with_name('witnesses.py')
    assert p.exists(), 'identifiability witness not implemented'
    if 'factor_atlas_witnesses' not in sys.modules:
        sys.path.insert(0,str(p.parent))
        spec=importlib.util.spec_from_file_location('factor_atlas_witnesses',p)
        m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
    return sys.modules['factor_atlas_witnesses']

def test_identical_bars_can_hide_opposite_quote_signed_tapes():
    x=module().identifiability_witness()
    assert x['bar_input_equal'] and x['bar_pressure_equal']
    assert x['quote_net_a_usd']==pytest.approx(x['gross_usd'])
    assert x['quote_net_b_usd']==pytest.approx(-x['gross_usd'])
    assert x['quote_net_a_usd']!=x['quote_net_b_usd']
    assert x['source']=='SYNTHETIC' and not x['empirical_accuracy_measured']

def test_witness_is_deterministic_and_quotes_precede_trades():
    a=module().identifiability_witness(); b=module().identifiability_witness()
    assert a==b and a['all_quote_ages_ms']==200 and a['n_trades']==15

def test_witness_covers_every_completed_bar_after_capture_latency():
    x=module().identifiability_witness()
    assert x.get('n_bars')==5
