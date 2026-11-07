"""Factor Atlas research-only IV inversion-residual sensitivity, test-first.

Exact-zero remains the legacy *research* baseline. Explicit alternative
tolerances neither certify vendor EOD quote clocks nor authorize production.
"""
from datetime import date
import numpy as np
import pandas as pd
import pytest

from research.factor_atlas.session3.retrospective import select_iv30

DAY=date(2026,10,7)

def rows(errors=(1e-5,-2e-5,3e-5,-4e-5),bid=9.5,ask=10.,iv=.35):
    result=[]
    for idx,(days,right) in enumerate(((30,'C'),(30,'P'),(37,'C'),(37,'P'))):
        result.append({'root':'TSLA','date':pd.Timestamp(DAY),
           'expiration':pd.Timestamp(DAY)+pd.Timedelta(days=days),
           'strike':375.,'right':right,'bid':bid,'ask':ask,
           'underlying_price':375.,'implied_vol':iv,'iv_error':errors[idx]})
    return pd.DataFrame(result)


def test_original_exact_zero_result_stays_identical():
    x=rows(errors=(0.,0.,0.,0.))
    baseline=select_iv30(x,root='TSLA',anchor=DAY)
    forced_default=select_iv30(x,root='TSLA',anchor=DAY,research_iv_error_abs_max=0.)
    assert forced_default==baseline
    assert 'research_sensitivity' not in baseline
    assert baseline['iv30']==pytest.approx(.35)


def test_tiny_signed_solver_residuals_only_admitted_under_explicit_sensitivity():
    data=rows()
    baseline=select_iv30(data,root='TSLA',anchor=DAY)
    allowed=select_iv30(data,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-5)
    assert baseline['iv30'] is None
    assert 'NO_30D_BRACKET' in baseline['reasons']
    assert allowed['iv30']==pytest.approx(.35)
    assert allowed['tenors']==[30]
    assert allowed['research_sensitivity']=={
        'iv_error_abs_max':5e-5,
        'only_exploratory':True,
        'source_quality_certified':False,
        'historical_known_at_certified':False,
    }


@pytest.mark.parametrize('bad',[True,False,'0.00005',-1e-5,float('nan'),float('inf'),0.001,1])
def test_unbounded_or_untyped_threshold_rejected(bad):
    with pytest.raises(ValueError,match='threshold'):
        select_iv30(rows(),root='TSLA',anchor=DAY,research_iv_error_abs_max=bad)


@pytest.mark.parametrize('allowed',[5e-5,1e-4,5e-4])
def test_closed_exploratory_tolerance_grid(allowed):
    assert select_iv30(rows(),root='TSLA',anchor=DAY,research_iv_error_abs_max=allowed)['iv30']==pytest.approx(.35)


def test_quality_guards_remain_after_small_error_tolerance():
    f=rows(bid=0.)
    assert select_iv30(f,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-5)['iv30'] is None
    f=rows(bid=1,ask=3)
    assert select_iv30(f,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-5)['iv30'] is None
    f=rows(errors=(.002,.002,.002,.002))
    assert select_iv30(f,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-4)['iv30'] is None


def test_method_retains_call_put_bracket_and_finite_input_guards():
    f=rows()
    f.loc[f.right=='P','strike']=390.
    assert select_iv30(f,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-4)['iv30'] is None
    f=rows()
    f.loc[0,'iv_error']=float('nan')
    assert select_iv30(f,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-5)['iv30'] is None
    f=rows()
    f.loc[0,'root']='OTHER'
    assert 'ROOT_MISMATCH' in select_iv30(f,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-5)['reasons']


def test_threshold_only_changes_iv_error_convention_not_input_source():
    frame=rows();before=frame.copy(deep=True)
    select_iv30(frame,root='TSLA',anchor=DAY,research_iv_error_abs_max=5e-5)
    pd.testing.assert_frame_equal(frame,before)

def test_residual_sensitivity_suite_is_in_incumbent_options_code_group():
    from pathlib import Path
    import yaml
    root=Path(__file__).resolve().parents[1]
    job=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())['jobs']['options-skew-engine']
    assert job['gate']=='code' and job['scope']=='exclusive'
    assert 'tests/test_factor_options_iv_error_sensitivity.py' in job['paths']
    assert any('tests/test_factor_options_iv_error_sensitivity.py' in step.get('run','') for step in job['steps'])
