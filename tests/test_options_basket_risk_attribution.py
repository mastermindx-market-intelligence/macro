"""S3 source-qualified, display-only Euler risk attribution acceptance."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import json
import numpy as np
import pytest
from engine.options_basket_aggregation import Correlation, Definition, Member, aggregate

NOW=datetime(2026,10,8,22,tzinfo=timezone.utc)
HASH='a'*64

def inputs(weights=(.3,.3,.4), vols=(.2,.3,.4), corr=None):
    roots=[f'R{i}' for i in range(len(weights))]
    members=[Member(root=r,weight=w,iv=v,observed_at=NOW-timedelta(hours=2),known_at=NOW-timedelta(hours=1),
          qualified=True, source_ref=f'source:{r}',source_sha256=HASH,valid_until=NOW+timedelta(hours=2),
          method='iv30_exact_act365f') for r,w,v in zip(roots,weights,vols)]
    defn=Definition('basket:research','house:source',HASH,NOW-timedelta(days=2))
    corr=np.eye(len(roots)) if corr is None else np.array(corr,dtype=float)
    matrix=Correlation(tuple(roots),corr,'historical:source',HASH,NOW-timedelta(days=1),NOW-timedelta(hours=2),
                       NOW+timedelta(days=1),'historical_correlation')
    return members,defn,matrix

def run(members,defn,matrix):
    return aggregate(members,definition=defn,asof=NOW,correlation=matrix)

@pytest.mark.parametrize('giant',[10**500,-10**500,Fraction(10**500,1)])
def test_unrepresentable_integer_input_is_controlled_refusal(giant):
    # Fail closed for both signs without treating a huge number as market IV.
    from engine.options_basket_aggregation import standardized_iv
    with pytest.raises(ValueError,match='nonfinite|minimum'):
        standardized_iv([(30,giant)])
    members,definition,correlation=inputs()
    members[0]=replace(members[0],iv=giant)
    with pytest.raises(ValueError,match='nonfinite|minimum'):
        run(members,definition,correlation)


def test_finite_float_conversion_boundary_not_misclassified_as_overflow():
    # A finite scalar at the edge of float range is representable; numeric
    # parsing is not source-quality, model-fit, or publication admission.
    from engine.options_basket_aggregation import _number
    assert _number(10**308,'numeric scalar',0)==pytest.approx(1e308)


def test_euler_contributions_sum_exact_modeled_horizon_move():
    m,d,c=inputs(corr=[[1,.4,.2],[.4,1,.3],[.2,.3,1]])
    result=run(m,d,c)
    attribution=result['hybrid_risk_attribution']
    assert attribution is not None
    assert attribution['horizon_days']==30 and attribution['day_count_basis']=='ACT/365F'
    assert attribution['display_only']==True
    parts=attribution['components']
    assert len(parts)==3
    assert sum(p['component_move'] for p in parts)==pytest.approx(result['hybrid_expected_move'],rel=1e-12)
    assert sum(p['share_of_modeled_move'] for p in parts)==pytest.approx(1,abs=1e-12)
    R=np.array(c.values);sig=np.array([x.iv for x in m]);w=np.array([x.weight for x in m]);z=w*sig
    sigma=np.sqrt(float(z@R@z));scale=np.sqrt(30/365)
    expected=sigma*scale
    assert attribution['total_modeled_move']==pytest.approx(expected)
    for i,row in enumerate(parts):
        component=z[i]*(R@z)[i]/sigma*scale
        marginal=sig[i]*(R@z)[i]/sigma*scale
        assert row['root']==m[i].root
        assert row['component_move']==pytest.approx(component)
        assert row['marginal_per_unit_weight']==pytest.approx(marginal)
        assert row['component_move']==pytest.approx(w[i]*row['marginal_per_unit_weight'])
    json.dumps(result,allow_nan=False)

def test_negative_components_are_preserved_not_clamped():
    m,d,c=inputs(weights=(.1,.6,.3),vols=(.2,.3,.3),corr=[[1,-.9,0],[-.9,1,0],[0,0,1]])
    a=run(m,d,c)['hybrid_risk_attribution']
    assert a['components'][0]['component_move']<0
    assert a['components'][0]['share_of_modeled_move']<0
    assert sum(x['component_move'] for x in a['components'])==pytest.approx(a['total_modeled_move'])

def test_historical_source_order_does_not_change_root_attribution():
    m,d,c=inputs(corr=[[1,.35,.2],[.35,1,.1],[.2,.1,1]])
    expected=run(m,d,c)['hybrid_risk_attribution']
    permutation=[2,0,1]
    altered=replace(c,roots=tuple(c.roots[i] for i in permutation),values=np.array(c.values)[np.ix_(permutation,permutation)])
    assert run(m[::-1],d,altered)['hybrid_risk_attribution']==expected

def test_missing_iv_withholds_total_and_all_attribution():
    m,d,c=inputs()
    m[0]=replace(m[0],qualified=False)
    out=run(m,d,c)
    assert out['hybrid_expected_move'] is None
    assert out['hybrid_risk_attribution'] is None
    assert out['covered']['mean_iv'] is not None

def test_future_correlation_source_never_emits_attribution():
    m,d,c=inputs()
    c=replace(c,known_at=NOW+timedelta(seconds=10))
    out=run(m,d,c)
    assert out['hybrid_expected_move'] is None
    assert out['hybrid_risk_attribution'] is None

def test_true_zero_risk_psd_cancels_with_undefined_derivative():
    m,d,c=inputs(weights=(.5,.5),vols=(.2,.2),corr=[[1,-1],[-1,1]])
    out=run(m,d,c)
    assert out['hybrid_expected_move']==pytest.approx(0,abs=1e-12)
    assert out['hybrid_risk_attribution'] is None
    assert 'ZERO_MODELED_RISK_ATTRIBUTION_UNDEFINED' in out['reasons']

def test_unsupported_dealer_sign_and_sizing_authority_stays_false():
    m,d,c=inputs()
    r=run(m,d,c)
    assert r['authority']=={'display_only':True,'publication':False,'prophet':False,'position_sizing':False}
    assert r['hybrid_risk_attribution']['method']=='iv_scaled_correlation_euler'
    assert r['hybrid_risk_attribution']['not_dealer_inventory']==True

def test_scenario_correlation_cannot_be_mislabeled_historical():
    m,d,c=inputs()
    c=replace(c,method='scenario_assumption')
    attribution=run(m,d,c)['hybrid_risk_attribution']
    assert attribution['method']=='iv_scaled_correlation_euler'
    assert attribution['correlation_method']=='scenario_assumption'
    assert attribution['correlation_source_ref']==c.source_ref

def test_risk_attribution_suite_is_in_existing_options_ci_group():
    from pathlib import Path
    import yaml
    root=Path(__file__).resolve().parents[1]
    job=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())['jobs']['options-skew-engine']
    assert job['gate']=='code' and job['scope']=='exclusive'
    assert 'tests/test_options_basket_risk_attribution.py' in job['paths']
    assert any('tests/test_options_basket_risk_attribution.py' in x.get('run','') for x in job['steps'])
