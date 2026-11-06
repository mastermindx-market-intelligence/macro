"""Synthetic native-owner W2 composition; no current data/capture acceptance."""
from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import json
import types

import numpy as np
import pandas as pd
import pytest

from engine.neuralweb import theme_state_adapter as adapter
from engine.theme_graph import store, theme_state_w2_qualification as qualification
from tests.test_theme_state_owner_adapter import world  # noqa: F401


@pytest.fixture
def native_pilot(world, monkeypatch):
    root = world[0]
    nodes_path = root / 'data/theme_graph/nodes.parquet'
    nodes = pd.read_parquet(nodes_path)
    nodes['external_ids'] = nodes['external_ids'].astype(object)
    for symbol in ['HUBB','IBP','ABNB']:
        nodes.loc[nodes.node_id.eq('co:us:'+symbol),'external_ids'] = json.dumps({'symbol':symbol})
    nodes.to_parquet(nodes_path,index=False)
    edges_path = root / 'data/theme_graph/edges.parquet'
    old = pd.read_parquet(edges_path)
    rows = [dict(edge_id='fixture-'+symbol,type='MEMBER_OF',src='co:us:'+symbol,
        dst=qualification.BASKET,valid_from='2023-06-01',valid_to=None,
        belief_time='2026-10-01',evidence_time='2023-06-01',era='reconstruction',
        source_class='house_curation') for symbol in ['HUBB','IBP','ABNB']]
    pd.concat([old,pd.DataFrame(rows,columns=store.EDGE_COLUMNS)],ignore_index=True).to_parquet(edges_path,index=False)
    (root/'data/theme_graph/_meta.json').write_text(json.dumps({'computed_at':'2026-10-01T00:00:00Z','era':'reconstruction'}))
    prices=root/'data/baskets/ohlcv';prices.mkdir(parents=True)
    index=pd.bdate_range('2023-06-01','2026-10-02')
    rng=np.random.default_rng(20260811)
    common=rng.normal(0,.01,len(index))
    for n,symbol in enumerate(['HUBB','IBP','ABNB']):
        series=np.exp(np.cumsum(common*(1+n*.2)+rng.normal(0,.003,len(index))))*100
        pd.DataFrame({'close':series},index=index).to_parquet(prices/(symbol+'.parquet'))
    class Clock(dt.datetime):
        @classmethod
        def now(cls,tz=None):
            instant=dt.datetime.fromisoformat('2026-10-04T10:00:00+00:00')
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    namespace={key:getattr(dt,key) for key in dir(dt) if not key.startswith('__')};namespace['datetime']=Clock
    monkeypatch.setattr(qualification,'dt',types.SimpleNamespace(**namespace))
    return root


def bound(root):
    inputs=qualification.capture_w2_beta_inputs(root)
    bundle=adapter.capture_owner_bundle(root,effective_at='2026-10-03',known_at='2026-10-04T12:00:00Z')
    return bundle,inputs


def test_positive_exact_fixed_pilot_h1_reuses_owner_and_preserves_limits(native_pilot):
    bundle,inputs=bound(native_pilot)
    result=qualification.qualify_w2_beta_h1(bundle,inputs)
    assert result['status']=='COMPUTABLE',result['reason_codes']
    assert result['coverage']['fraction']>=.7
    assert result['binding']['bundle_sha256']==bundle.bundle_sha256
    assert result['binding']['graph_capture_id']==bundle.snapshot()['graph_capture_id']
    assert result['construction']=='trading_beta.v0' and result['slot']=='us_young_narrow'
    assert result['window']=={'sessions':63,'minimum_overlap':40,'causal_shift_sessions':1,'history_start':'2023-06'}
    assert result['periods'][-1]['month']=='2026-09'  # October remains incomplete
    assert result['periods'][0]['era']=='reconstruction'
    assert result['semantics']['H3_stability']=='NOT_ASSESSED'
    assert result['semantics']['measurement_eligibility']=='NOT_ESTABLISHED'
    assert result['semantics']['ThemeState_eligibility']=='NOT_QUALIFIED'
    assert result['authority']['may_publish'] is False
    assert not (native_pilot/'data/neuralweb/theme_state_current.json').exists()
    # Result is JSON-finite, with no raw beta magnitudes or source bytes exported.
    text=json.dumps(result,allow_nan=False)
    assert 'bytes_b64' not in text and 'value_display_shrunk' not in text


def test_missing_prices_remain_in_denominator_and_abstain(native_pilot):
    (native_pilot/'data/baskets/ohlcv/ABNB.parquet').unlink()
    result=qualification.qualify_w2_beta_h1(*bound(native_pilot))
    assert result['status']=='ABSTAIN'
    assert result['coverage']['fraction']<.7
    assert result['population']['missing_price_symbols']==['ABNB']
    assert all(row['n_members']==3 for row in result['periods'])


def test_closed_members_survive_their_validity_windows(native_pilot):
    path=native_pilot/'data/theme_graph/edges.parquet';edges=pd.read_parquet(path)
    edges.loc[edges.edge_id.eq('fixture-ABNB'),'valid_to']='2025-08-01';edges.to_parquet(path,index=False)
    result=qualification.qualify_w2_beta_h1(*bound(native_pilot))
    assert result['status']=='COMPUTABLE'
    assert result['population']['closed_members_included']==['co:us:ABNB']
    periods={r['month']:r for r in result['periods']}
    assert periods['2025-07']['n_members']==3 and periods['2025-08']['n_members']==2


def test_identity_aliases_do_not_create_independent_issuers(native_pilot):
    path=native_pilot/'data/reference/security_master.parquet';master=pd.read_parquet(path)
    master.loc[master.inception_code.eq('IBP'),'issuer_id']='fixture-issuer:HUBB';master.to_parquet(path,index=False)
    result=qualification.qualify_w2_beta_h1(*bound(native_pilot))
    assert result['reason_codes']==['OWNER_HAS_NO_DUPLICATE_ISSUER_AGGREGATION_RULE']
    assert result['status']=='UNAVAILABLE'


@pytest.mark.parametrize('generated_at',[None,'2026-10-01T05:05:32','invalid','2026-10-05T00:00:00Z'])
def test_unknown_or_future_native_identity_clock_is_typed_unavailable(native_pilot,generated_at):
    path=native_pilot/'data/reference/_receipt.json'
    receipt=json.loads(path.read_text());receipt['generated_at']=generated_at
    path.write_text(json.dumps(receipt))
    result=qualification.qualify_w2_beta_h1(*bound(native_pilot))
    assert result['status']=='UNAVAILABLE'
    assert result['reason_codes']==['IDENTITY_KNOWLEDGE_UNPROVEN']
    assert result['coverage'] is None
    assert result['semantics']['historical_availability']=='UNPROVEN; current capture is an upper bound only'


def test_bound_master_producer_naive_utc_is_decoded_without_restamping(native_pilot):
    path=native_pilot/'data/reference/_receipt.json'
    receipt=json.loads(path.read_text());receipt.update(generated_at='2026-10-02T09:00:00',
        producer='scripts/build_security_master.py',code_version=qualification.NAIVE_UTC_MASTER_REVISION,
        dataset_ids=['reference.security_master','reference.vendor_aliases'])
    raw=json.dumps(receipt);path.write_text(raw)
    result=qualification.qualify_w2_beta_h1(*bound(native_pilot))
    assert result['status']=='COMPUTABLE',result['reason_codes']
    clock=result['binding']['identity_clock']
    assert clock['raw']=='2026-10-02T09:00:00'
    assert clock['comparison_clock']=='2026-10-02T09:00:00+00:00'
    assert clock['interpretation']=='BOUND_NATIVE_MASTER_PRODUCER_NAIVE_UTC_SECONDS'
    assert clock['receipt_sha256']==qualification._sha(raw.encode())
    assert path.read_text()==raw
    assert result['semantics']['historical_availability']=='UNPROVEN; current capture is an upper bound only'


@pytest.mark.parametrize('change',[lambda r:r.update(producer='other'),lambda r:r.update(code_version='invalid'),
    lambda r:r.update(code_version='d'*40),
    lambda r:r.update(generated_at='2026-10-02T09:00:00.123'),lambda r:r.update(generated_at='2026-10-02'),
    lambda r:r.update(dataset_ids=['reference.security_master']),lambda r:r.update(dataset_ids=[{}])])
def test_naive_master_decoder_is_producer_revision_and_exact_format_bound(change):
    receipt=dict(generated_at='2026-10-02T09:00:00',producer='scripts/build_security_master.py',
                 code_version=qualification.NAIVE_UTC_MASTER_REVISION,dataset_ids=['reference.security_master','reference.vendor_aliases'])
    row=dict(master_generated_at=receipt['generated_at'],master_code_version=receipt['code_version'])
    change(receipt)
    assert qualification._native_master_clock(row,receipt) is None


def test_naive_master_decoder_refuses_same_stamp_different_generation():
    receipt=dict(generated_at='2026-10-02T09:00:00',producer='scripts/build_security_master.py',
                 code_version=qualification.NAIVE_UTC_MASTER_REVISION,dataset_ids=['reference.security_master','reference.vendor_aliases'])
    assert qualification._native_master_clock(dict(master_generated_at=receipt['generated_at'],master_code_version='d'*40),receipt) is None


def test_bound_producer_naive_future_clock_does_not_advance_cutoff(native_pilot):
    path=native_pilot/'data/reference/_receipt.json'
    receipt=json.loads(path.read_text());receipt.update(generated_at='2026-10-05T09:00:00',
        producer='scripts/build_security_master.py',code_version=qualification.NAIVE_UTC_MASTER_REVISION,
        dataset_ids=['reference.security_master','reference.vendor_aliases'])
    path.write_text(json.dumps(receipt))
    result=qualification.qualify_w2_beta_h1(*bound(native_pilot))
    assert result['status']=='UNAVAILABLE' and result['reason_codes']==['IDENTITY_KNOWLEDGE_UNPROVEN']


def test_capture_after_bundle_cutoff_refuses(native_pilot):
    bundle,inputs=bound(native_pilot)
    payload=inputs.snapshot();payload['observed_at']='2026-10-05T12:00:00Z'
    text=adapter._json(payload);later=dataclasses.replace(inputs,payload_json=text,sha256=qualification._sha(text.encode()))
    assert qualification.qualify_w2_beta_h1(bundle,later)['reason_codes']==['NATIVE_W2_CAPTURE_AFTER_CUTOFF']


@pytest.mark.parametrize('path',['data/theme_graph/edges.parquet','data/reference/security_master.parquet'])
def test_split_generation_refuses(native_pilot,path):
    inputs=qualification.capture_w2_beta_inputs(native_pilot)
    p=native_pilot/path;frame=pd.read_parquet(p);frame.to_parquet(p,index=False,compression=None)
    bundle=adapter.capture_owner_bundle(native_pilot,effective_at='2026-10-03',known_at='2026-10-04T12:00:00Z')
    assert qualification.qualify_w2_beta_h1(bundle,inputs)['reason_codes']==['NATIVE_OWNER_GENERATION_MISMATCH']


def test_capture_integrity_and_fixed_scope_refuse(native_pilot):
    bundle,inputs=bound(native_pilot)
    with pytest.raises(ValueError,match='digest'):
        qualification.qualify_w2_beta_h1(bundle,dataclasses.replace(inputs,payload_json=inputs.payload_json+' '))
    payload=inputs.snapshot();payload['slot']='us_institutional';text=adapter._json(payload)
    with pytest.raises(ValueError,match='fixed-pilot'):
        qualification.qualify_w2_beta_h1(bundle,dataclasses.replace(inputs,payload_json=text,sha256=qualification._sha(text.encode())))


def test_arbitrary_dict_is_not_native_capture(native_pilot):
    bundle,_=bound(native_pilot)
    with pytest.raises(TypeError,match='capabilities'):
        qualification.qualify_w2_beta_h1(bundle,{'status':'QUALIFIED'})


def test_measurement_observation_cannot_arrive_after_owner_capture(native_pilot):
    bundle,inputs=bound(native_pilot)
    payload=inputs.snapshot();payload['observed_at']='2026-10-04T11:30:00Z'
    text=adapter._json(payload);later=dataclasses.replace(inputs,payload_json=text,sha256=qualification._sha(text.encode()))
    assert qualification.qualify_w2_beta_h1(bundle,later)['reason_codes']==['NATIVE_W2_CAPTURE_AFTER_OWNER_CAPTURE']


def test_source_race_cannot_be_captured(native_pilot,monkeypatch):
    from pathlib import Path
    original=Path.read_bytes
    reads=[]
    def changed(self):
        raw=original(self)
        if self==native_pilot/'data/baskets/ohlcv/HUBB.parquet':
            reads.append(self)
            if len(reads)>1:
                return raw+b'changed'
        return raw
    monkeypatch.setattr(Path,'read_bytes',changed)
    with pytest.raises(ValueError,match='source changed'):
        qualification.capture_w2_beta_inputs(native_pilot)


def test_short_native_history_abstains_without_imputation(native_pilot):
    for path in (native_pilot/'data/baskets/ohlcv').glob('*.parquet'):
        prices=pd.read_parquet(path).iloc[-25:]
        prices.to_parquet(path)
    result=qualification.qualify_w2_beta_h1(*bound(native_pilot))
    assert result['status']=='ABSTAIN'
    assert result['coverage']['computed_member_periods']==0
    assert result['owner_omitted_months']
    assert result['reason_codes']==['W2_H1_COVERAGE_FLOOR']


def composed(root,with_measurement=True):
    bundle,inputs=bound(root)
    options={'w2_beta_inputs':inputs} if with_measurement else {}
    result=adapter.compose_from_owner_bundle(bundle,generated_at='2026-10-04T12:00:00Z',**options)
    return result,bundle,inputs


def read_composed(result,bundle,inputs,**changes):
    options=dict(effective_at='2026-10-03',known_at='2026-10-04T12:00:00Z',
                 expected_generation_id=result['state']['generation_id'])
    options.update(changes)
    return qualification.read_internal_w2_h1(result,bundle=bundle,inputs=inputs,**options)


def test_incumbent_envelope_composes_and_reads_internal_h1_without_changing_state(native_pilot):
    result,bundle,inputs=composed(native_pilot)
    ordinary=adapter.compose_from_owner_bundle(bundle,generated_at='2026-10-04T12:00:00Z')
    internal=result.pop('internal_measurements')
    assert result==ordinary  # every existing field and unsupported leg is preserved
    result['internal_measurements']=internal
    assert qualification.MEASUREMENT_KEY not in result['state']
    assert all(row['eligibility']['status']=='NOT_QUALIFIED' for row in result['state']['subjects'])
    assert result['publication_allowed'] is False
    read=read_composed(result,bundle,inputs)
    assert read['status']=='COMPUTABLE',read['reason_codes']
    assert read['state_ref']['state_sha256']==result['state']['state_sha256']
    assert read['measurement']['subject']['canonical_membership']=='NOT_ASSERTED'
    assert read['public_display_allowed'] is False
    assert all(value is False for key,value in read['authority'].items() if key.startswith('may_'))
    assert 'bytes_b64' not in json.dumps(read)


def test_internal_abstention_is_consumed_without_a_fake_positive(native_pilot):
    (native_pilot/'data/baskets/ohlcv/ABNB.parquet').unlink()
    result,bundle,inputs=composed(native_pilot)
    read=read_composed(result,bundle,inputs)
    assert read['status']=='ABSTAIN'
    assert read['reason_codes']==['W2_H1_COVERAGE_FLOOR']
    assert read['measurement']['population']['missing_price_symbols']==['ABNB']


@pytest.mark.parametrize('query,reason',[
    ({'expected_generation_id':'wrong'},'GENERATION_MISMATCH'),
    ({'effective_at':'2026-10-02'},'EFFECTIVE_TIME_MISMATCH'),
    ({'known_at':'2026-10-04T11:59:59Z'},'STATE_NOT_YET_EMITTED'),
    ({'known_at':'2026-10-06T12:00:00Z'},'STATE_STALE'),
])
def test_internal_reader_keeps_exact_state_visibility(native_pilot,query,reason):
    result,bundle,inputs=composed(native_pilot)
    read=read_composed(result,bundle,inputs,**query)
    assert read['status']=='UNAVAILABLE' and reason in read['reason_codes']
    assert read['measurement'] is None


def test_rehashed_internal_record_cannot_promote_or_forward_arbitrary_fields(native_pilot):
    result,bundle,inputs=composed(native_pilot)
    record=result['internal_measurements'][qualification.MEASUREMENT_KEY]
    record['measurement']['semantics']['ThemeState_eligibility']='QUALIFIED'
    record['authority']['may_publish']=True
    record['private_body']='MUST_NOT_FORWARD'
    record['sha256']=qualification.theme_state.canonical_sha256({k:v for k,v in record.items() if k!='sha256'})
    read=read_composed(result,bundle,inputs)
    assert read['reason_codes']==['INTERNAL_MEASUREMENT_BINDING_INVALID']
    assert 'MUST_NOT_FORWARD' not in json.dumps(read)


def test_internal_measurement_cannot_cross_native_input_captures(native_pilot):
    result,bundle,_=composed(native_pilot)
    path=native_pilot/'data/baskets/ohlcv/HUBB.parquet';prices=pd.read_parquet(path)
    prices.iloc[0,0]*=1.01;prices.to_parquet(path)
    other=qualification.capture_w2_beta_inputs(native_pilot)
    assert read_composed(result,bundle,other)['reason_codes']==['INTERNAL_MEASUREMENT_BINDING_INVALID']


def test_default_envelope_does_not_manufacture_internal_measurement(native_pilot):
    result,bundle,inputs=composed(native_pilot,with_measurement=False)
    assert 'internal_measurements' not in result
    assert read_composed(result,bundle,inputs)['reason_codes']==['INTERNAL_MEASUREMENT_NOT_COMPOSED']
    result['internal_measurements']=None
    assert read_composed(result,bundle,inputs)['reason_codes']==['INTERNAL_MEASUREMENT_BINDING_INVALID']


def test_ordinary_adapter_import_does_not_load_research_probe_or_require_scipy():
    import subprocess
    import sys
    code="""
import importlib.abc,sys
class DenyResearch(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='scipy' or fullname.startswith('scipy.') or fullname in {
            'scripts.probe_theme_exposure_axes','engine.theme_graph.theme_state_w2_qualification'}:
            raise AssertionError('ordinary adapter imported optional research: '+fullname)
sys.meta_path.insert(0,DenyResearch())
from engine.neuralweb import theme_state_adapter
assert 'engine.theme_graph.theme_state_w2_qualification' not in sys.modules
"""
    completed=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr
