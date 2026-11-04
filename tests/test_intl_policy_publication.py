"""Actual native admission composition into the frozen comparison arithmetic.

All source bytes here are explicitly synthetic offline contract fixtures; the
retained real ECB/BoE proof is emitted separately by the integration owner.
"""
from copy import deepcopy
import json
import pandas as pd
import pytest
from lib.intl_macro_publication import read_ecb_deposit_materialization
from lib.intl_boe_publication import read_boe_materialization, admit_boe_policy_field
from lib.intl_policy_publication import METHOD, MAPPING_POLICY, compare_native_policy_points
from scripts.build_intl import _ecb_publication_measure
from tests.test_intl_boe_publication import _capture, _decision, OBSERVED

GEN = 'im-workspace-generation:54b26d48-c09c-4dbf-bdba-b8ebcb22a48d'
NOW = '2026-11-04T12:00:00+00:00'

def setup(root):
    _capture(root, OBSERVED)
    series = pd.Series([2.25,2.5,2.5], index=pd.to_datetime(['2026-08-28','2026-09-30','2026-11-02']), name='ez_depo_rate')
    (root/'intl_macro/ez_depo_rate.parquet').write_bytes(b'')
    series.to_frame().to_parquet(root/'intl_macro/ez_depo_rate.parquet')
    provenance = {'provider':'ecb','status':'official','source_id':'D.U2.EUR.4F.KR.DFR.LEV',
        'last_observation':'2026-11-02','source_updated':'2026-11-02','unit':'PCPA',
        'release_period_semantics':'Daily effective policy-rate observation',
        'source_url':'https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata&startPeriod=1999-01-01',
        'requested_at':'2026-11-04T08:57:22+00:00'}
    (root/'intl_macro/provenance.json').write_text(json.dumps({'series':{'ez_depo_rate':provenance}}))
    ecb=read_ecb_deposit_materialization(data_root=root);assert ecb['status']=='ready'
    sink={};metric=_ecb_publication_measure(ecb,evaluated_at=NOW,generation=GEN,decision_sink=sink);assert metric['quality']=='qualified'
    boe=read_boe_materialization(root);bd=_decision(boe['receipt_sha256']);bd['decision_ref']=GEN+':GB.policy_rate'
    intent={'economy_a':'EZ','economy_b':'GB','lens':'nominal_policy_point_gap','definition':'absolute_gap_change_bp',
        'method_version':METHOD,'period':{'mode':'fixed_dates','start':'2026-08-28','end':'2026-09-30'},
        'vintage_policy':'latest_vintage','identity':{'principal_partition':None,'saved_id':None,'saved_revision':None,'source_generation':GEN}}
    mapping={'owner_ref':'scripts/build_intl.py','policy_ref':MAPPING_POLICY,'method_version':METHOD,
        'metadata':'allowed','value_permission':'allowed','binding':{'economy_a':'EZ','economy_b':'GB',
        'period':intent['period'],'ecb_identity':ecb['materialized_identity'],'boe_receipt_sha256':boe['receipt_sha256']}}
    args={'ecb_materialized':ecb,'ecb_decision':sink['decision'],'boe_materialized':boe,'boe_decision':bd,
        'evaluated_at':NOW,'mapping_decision':mapping}
    return intent,args

def test_native_four_points_invoke_existing_engine_and_keep_signed_gap(tmp_path):
    i,a=setup(tmp_path);r=compare_native_policy_points(i,**a)
    assert r['state']=='qualified'
    assert [r[k]for k in ['signed_start_bp','signed_end_bp','signed_change_bp','absolute_change_bp']]==[-150,-125,25,-25]
    assert r['direction']=='narrowed' and r['crosses_zero'] is False
    assert [x['observation_at']for x in r['evidence_refs']]==['2026-08-28','2026-09-30']*2
    assert all(x['qualification_ref'].startswith('intl-policy-endpoint:sha256:')for x in r['evidence_refs'])
    assert r['identity']==i

@pytest.mark.parametrize('mutation', ['mapping_absent','mapping_unknown','mapping_hash','ecb_denied','boe_denied','generation','missing_date','original_known','wrong_pair'])
def test_unavailable_source_or_scope_never_returns_partial_comparison_numbers(tmp_path,mutation):
    i,a=setup(tmp_path)
    if mutation=='mapping_absent':a['mapping_decision']=None
    if mutation=='mapping_unknown':a['mapping_decision']['value_permission']='unknown'
    if mutation=='mapping_hash':a['mapping_decision']['binding']['boe_receipt_sha256']='0'*64
    if mutation=='ecb_denied':a['ecb_decision']['value_permission']='denied'
    if mutation=='boe_denied':a['boe_decision']['metadata']='denied'
    if mutation=='generation':i['identity']['source_generation']='different-generation'
    if mutation=='missing_date':i['period']['start']='2026-08-27'
    if mutation=='original_known':i['vintage_policy']='original_known'
    if mutation=='wrong_pair':i['economy_b']='JP'
    r=compare_native_policy_points(i,**a)
    assert r['state']=='unavailable'
    assert not {'signed_start_bp','signed_end_bp','evidence_refs'}&r.keys()


def test_historical_exact_read_is_independent_from_a_stale_current_display(tmp_path):
    i,a=setup(tmp_path);a['evaluated_at']='2026-12-01T12:00:00+00:00'
    current=admit_boe_policy_field(a['boe_materialized'],a['evaluated_at'],a['boe_decision'])
    assert current['quality']=='stale'
    assert compare_native_policy_points(i,**a)['state']=='qualified'

@pytest.mark.parametrize('bad',[None,[],{'economy_a':{}},True])
def test_malformed_intent_fails_closed_without_untrusted_echo(tmp_path,bad):
    _,a=setup(tmp_path);r=compare_native_policy_points(bad,**a)
    assert r=={'state':'invalid','identity':None,'reasons':['invalid_policy_comparison'],'missing_refs':[]}


def test_mapping_identity_tracks_exact_source_and_qualification_changes(tmp_path):
    i,a=setup(tmp_path);r=compare_native_policy_points(i,**a);first=r['evidence_refs'][0]['qualification_ref']
    a['ecb_materialized']['materialized_identity']['artifact_sha256']='1'*64
    # A stale point decision cannot bless different stored source identity.
    assert compare_native_policy_points(i,**a)['state']=='unavailable'
    assert first.startswith('intl-policy-endpoint:sha256:')
