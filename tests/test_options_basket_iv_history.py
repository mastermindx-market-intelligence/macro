"""S3 Factor Atlas pure history semantics; all source observations synthetic."""
from dataclasses import replace
from datetime import date,datetime,timedelta,timezone
from importlib import import_module
from pathlib import Path
import copy
import json
import pandas as pd
import pytest
from engine.options_basket_aggregation import Definition, Member, aggregate

MODULE='engine.options_basket_history'
SHA='a'*64
SESSIONS=[day.date() for day in pd.bdate_range(end='2026-10-08',periods=252)]
CUTOFF=datetime(2026,10,9,3,tzinfo=timezone.utc)

def make_point(day,iv,weights=(.2,.3,.5),factor_ref='house:mag7',def_sha=SHA):
    asof=datetime.combine(day,datetime.min.time(),timezone.utc)+timedelta(hours=22)
    defn=Definition(factor_ref,'fixture:registry',def_sha,datetime(2025,1,1,tzinfo=timezone.utc))
    rows=[Member(root=root,weight=w,iv=iv,observed_at=asof-timedelta(hours=2),
       known_at=asof-timedelta(hours=1),qualified=True,source_ref=f'fixture:greeks:{root}',
       source_sha256=SHA,valid_until=asof+timedelta(hours=2),
       method='iv30_total_variance_act365f') for root,w in zip(['AAA','BBB','CCC'],weights)]
    return aggregate(rows,definition=defn,asof=asof)

@pytest.fixture
def history():
    return [make_point(day,.2+i*.001) for i,day in enumerate(SESSIONS)]

@pytest.fixture
def m():
    assert (Path(__file__).resolve().parents[1]/'engine/options_basket_history.py').is_file(),'pure history leaf not built'
    return import_module(MODULE)

def test_minmax_rank_and_midrank_percentile_are_not_synonyms(m,history):
    result=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert result['iv_rank_minmax_pct']==pytest.approx(100)
    assert result['iv_percentile_midrank_pct']==pytest.approx(100*(251+.5)/252)
    assert result['current_constituent_mean_iv']==pytest.approx(.451)
    assert result['basis']=='full_coverage_constituent_mean_iv_not_traded_basket_iv'
    assert result['coverage']['qualified_sessions']==252
    assert result['authority']=={'display_only':True,'publication':False,'prophet':False,'position_sizing':False}
    json.dumps(result,allow_nan=False)

def test_constant_iv_has_percentile_midrank_but_undefined_minmax(m):
    history=[make_point(day,.35) for day in SESSIONS]
    result=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert result['iv_rank_minmax_pct'] is None
    assert result['iv_percentile_midrank_pct']==pytest.approx(50)
    assert 'DEGENERATE_IV_RANGE' in result['reasons']

@pytest.mark.parametrize('removed',[1,75,101,126])
def test_incomplete_sessions_do_not_fabricate_252_day_history(m,history,removed):
    subset=history[:-removed]
    out=m.summarize_iv_history(subset,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['coverage']['qualified_sessions']==252-removed
    assert out['coverage']['expected_sessions']==252
    assert out['iv_rank_minmax_pct'] is None and out['iv_percentile_midrank_pct'] is None
    assert 'INCOMPLETE_SESSION_COVERAGE' in out['reasons']

def test_oversized_source_integer_withholds_history_point(m,history):
    # A finite-shaped but unrepresentable numeric source value is unqualified,
    # not a Python OverflowError escaping the read-only history boundary.
    history[50]['inputs'][0]['iv']=10**500
    result=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert result['coverage']['qualified_sessions']==251
    assert result['iv_rank_minmax_pct'] is None
    assert 'UNQUALIFIED_POINT' in result['reasons']


def test_unqualified_source_member_invalidates_history_point(m,history):
    history[50]['inputs'][0]['qualified']=False
    out=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['coverage']['qualified_sessions']==251
    assert out['iv_rank_minmax_pct'] is None
    assert 'UNQUALIFIED_POINT' in out['reasons']

def test_unknown_or_future_member_source_clock_invalidates_history(m,history):
    history[40]['inputs'][0]['known_at']='2026-10-10T00:00:00+00:00'
    out=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['coverage']['qualified_sessions']==251
    assert out['iv_percentile_midrank_pct'] is None

def test_untrusted_rank_summary_cannot_replace_raw_constituent_iv(m,history):
    history[-1]['covered']['mean_iv']=100.0
    with pytest.raises(ValueError,match='mean'):
        m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)

def test_duplicate_session_is_refused_not_winner_selected(m,history):
    with pytest.raises(ValueError,match='duplicate'):
        m.summarize_iv_history([*history,history[-1]],expected_sessions=SESSIONS,asof=CUTOFF)

def test_definition_version_change_refuses_false_rank_continuity(m,history):
    history[20]['definition']['sha256']='b'*64
    out=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['iv_rank_minmax_pct'] is None
    assert 'INCOMPATIBLE_BASKET_DEFINITION' in out['reasons']

def test_weight_version_change_refuses_false_rank_continuity(m,history):
    history[1]['inputs'][0]['weight']=.1
    out=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['iv_percentile_midrank_pct'] is None
    assert 'INCOMPATIBLE_BASKET_WEIGHTS' in out['reasons']

def test_wrong_tenor_or_basis_cannot_enter_history(m,history):
    history[10]['horizon']['basis']='TRADING/252'
    out=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['coverage']['qualified_sessions']==251
    assert out['iv_rank_minmax_pct'] is None

def test_points_outside_expected_calendar_are_refused(m,history):
    later=SESSIONS[-1]+timedelta(days=1)
    with pytest.raises(ValueError,match='outside'):
        m.summarize_iv_history(history+[make_point(later,.4)],expected_sessions=SESSIONS,asof=CUTOFF+timedelta(days=2))

def test_query_cutoff_before_last_point_refuses_future_leak(m,history):
    with pytest.raises(ValueError,match='future'):
        m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF-timedelta(days=3))

def test_bad_calendar_or_no_series_is_rejected(m,history):
    with pytest.raises(ValueError):m.summarize_iv_history(history,expected_sessions=SESSIONS[:-1]+SESSIONS[-2:-1],asof=CUTOFF)
    with pytest.raises(ValueError):m.summarize_iv_history(history,expected_sessions=[],asof=CUTOFF)
    with pytest.raises(ValueError):m.summarize_iv_history([],expected_sessions=SESSIONS,asof=CUTOFF)

def test_observation_order_and_member_order_do_not_matter(m,history):
    original=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    for point in history:
        point['inputs'].reverse()
    changed=m.summarize_iv_history(history[::-1],expected_sessions=SESSIONS,asof=CUTOFF)
    assert changed==original

def test_vendor_legacy_iv_rank_252_is_not_interpreted_as_minmax(m,history):
    for point in history:point['legacy_iv_rank_252']=.5
    out=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['iv_rank_minmax_pct']==pytest.approx(100)
    assert out['iv_percentile_midrank_pct']!=out['iv_rank_minmax_pct']

def test_explicit_incumbent_headline_withholding_is_not_overridden(m,history):
    history[5]['headline_mean_iv']=None
    out=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert out['coverage']['qualified_sessions']==251
    assert out['iv_rank_minmax_pct'] is None and out['iv_percentile_midrank_pct'] is None


def test_history_code_has_no_live_data_or_prod_imports():
    from pathlib import Path
    code=(Path(__file__).resolve().parents[1]/'engine/options_basket_history.py').read_text()
    for banned in ['thetadata_store','supabase','requests.get','httpx','subprocess','publisher','open(']:
        assert banned not in code

def test_iv_history_is_in_existing_options_code_pack():
    import yaml
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    job=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())['jobs']['options-skew-engine']
    assert job['gate']=='code' and job['scope']=='exclusive'
    assert 'engine/options_basket_history.py' in job['paths']
    assert 'tests/test_options_basket_iv_history.py' in job['paths']
    assert any('tests/test_options_basket_iv_history.py' in step.get('run','') for step in job['steps'])

def test_coverage_policy_version_change_must_not_create_false_iv_rank(m,history):
    # Identical qualified constituent quotes but different historical
    # coverage admission rules cannot be silently treated as one rank series.
    history[70]['policy']='factor_options_coverage/v2'
    r=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert r['iv_rank_minmax_pct'] is None
    assert r['iv_percentile_midrank_pct'] is None
    assert 'INCOMPATIBLE_COVERAGE_POLICY' in r['reasons']


def test_coverage_policy_threshold_change_requires_new_history_vintage(m,history):
    history[100]['policy_parameters']['max_missing_name_weight']=0.2
    r=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert r['iv_rank_minmax_pct'] is None
    assert 'INCOMPATIBLE_COVERAGE_POLICY' in r['reasons']


def test_mixed_exact_tenor_and_variance_interpolation_iv_method_requires_cohort_proof(m,history):
    history[130]['inputs'][0]['method']='iv30_exact_act365f'
    r=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert r['iv_rank_minmax_pct'] is None
    assert r['iv_percentile_midrank_pct'] is None
    assert 'INCOMPATIBLE_IV_METHOD_VINTAGE' in r['reasons']


def test_unchanged_policy_and_method_have_consistent_rank(m,history):
    x=m.summarize_iv_history(history,expected_sessions=SESSIONS,asof=CUTOFF)
    assert x['iv_rank_minmax_pct']==pytest.approx(100)
    assert x['iv_percentile_midrank_pct']==pytest.approx(100*(251.5)/252)
