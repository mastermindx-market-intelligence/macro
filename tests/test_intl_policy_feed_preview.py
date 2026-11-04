"""Pinned policy-point feed composition; all fixtures are synthetic/offline."""
from copy import deepcopy
import hashlib,json,sys,types
import pytest
from lib.intl_generation_publication import publish_generation,serialize_generation,read_generation_publication,publish_unavailable_generation
from lib.intl_policy_publication import build_policy_points,publish_policy_points,preview_published_policy_points,METHOD,MAPPING_POLICY
from tests.test_intl_generation_publication import (_build,_ecb_measure,_ecb_receipt,_ecb_decision,_measure,_receipt,_decision,_evidence,GENERATION)
NOW='2026-11-04T12:20:00+00:00'
POLICY={'status':'confirmed','policy_ref':MAPPING_POLICY,'metadata':'allowed','value_permission':'allowed'}

def prepared(tmp_path,monkeypatch):
    measures={'EZ.policy_rate':_ecb_measure(),'GB.policy_rate':_measure('GB.policy_rate',value=3.75,instrument={'kind':'official_policy','id':'bank_rate','market_id':'GB'})}
    evidence={'EZ.policy_rate':_evidence('EZ.policy_rate',_ecb_receipt(),_ecb_decision()),'GB.policy_rate':_evidence('GB.policy_rate',_receipt(),_decision('GB.policy_rate'))}
    c=_build(config={'markets':['EZ','GB'],'horizons':['3m'],'bases':['local'],'fields':{'EZ':['policy_rate'],'GB':['policy_rate']}},measures=measures,evidence=evidence,documents={sid:'c'*64 for sid in measures})
    clocks={'requested_at':'2026-11-04T10:00:00+00:00','response_received_at':'2026-11-04T10:00:01+00:00','input_verified_at':'2026-11-04T10:01:00+00:00','committed_at':'2026-11-04T10:02:00+00:00','provider_published_at':None,'revision_vintage':None}
    sources={}
    for economy,values in [('EZ',[2.25,2.5]),('GB',[3.75,3.75])]:
        rows=[{'date':d,'value':v,'status':'observed'}for d,v in zip(['2026-08-28','2026-09-30'],values)]
        sources[economy]={'status':'ready','receipt_sha256':('a'if economy=='EZ'else'b')*64,'receipt':{**clocks,'source_url':'https://official.example.invalid/'+economy,'rows':rows},'parsed':{'observations':rows}}
    points=build_policy_points(generation=GENERATION,ecb=sources['EZ'],boe=sources['GB'],policies=c['policies'],mapping_policy=POLICY,mapping_document_sha256='d'*64,evaluated_at=NOW)
    ref=publish_policy_points(data_root=tmp_path,contract=points);c['policy_points_ref']=ref
    descriptor=publish_generation(data_root=tmp_path,contract=c);directory=tmp_path/'intl/publication/generations'
    class Reader:
        reads=[]
        def __init__(self,base):assert base=='https://configured.example.invalid'
        def read(self,name,*,max_bytes):
            Reader.reads.append(name);data=(directory/name).read_bytes();assert len(data)<=max_bytes;return data
    monkeypatch.setitem(sys.modules,'lib.intl_feed_reader',types.SimpleNamespace(FixedFeedReader=Reader,FeedReadError=OSError))
    settings={'economy_a':'EZ','economy_b':'GB','lens':'nominal_policy_point_gap','definition':'absolute_gap_change_bp','method_version':METHOD,'period':{'mode':'fixed_dates','start':'2026-08-28','end':'2026-09-30'},'instrument_a_ref':'EZ.policy_rate','instrument_b_ref':'GB.policy_rate','revision_policy':'latest_vintage'}
    args={'feed_base':'https://configured.example.invalid','source_generation':GENERATION,'artifact_sha256':descriptor['artifact_sha256'],'settings':settings,'evaluated_at':NOW}
    return c,points,descriptor,directory,args,Reader,sources

def test_exact_published_four_points_use_engine_and_fresh_current_policy(tmp_path,monkeypatch):
    c,points,d,root,args,reader,_=prepared(tmp_path,monkeypatch)
    assert read_generation_publication(data_root=tmp_path)['status']=='ready'
    r=preview_published_policy_points(**args)
    assert set(r)=={'schema','state','source_generation','artifact_sha256','mapping_identity','qualification_identity','result'}
    assert r['state']=='qualified' and r['result']['absolute_change_bp']==-25
    assert [r['result'][k]for k in ['signed_start_bp','signed_end_bp','signed_change_bp']]==[-150,-125,25]
    assert r['mapping_identity']==points['mapping_identity'] and r['qualification_identity']==points['qualification_identity']
    assert reader.reads.count('intl_generation_current.json')==2
    assert all(value is None for key,value in r['result']['identity']['identity'].items()if key!='source_generation')

@pytest.mark.parametrize('fault',['missing_point','changed_point','changed_generation','missing_witness','revoked','changed_current','wrong_instrument','original_known','missing_date','future_period'])
def test_unavailable_never_falls_back_or_returns_comparison_numbers(tmp_path,monkeypatch,fault):
    c,points,d,root,args,reader,_=prepared(tmp_path,monkeypatch)
    if fault=='missing_point':(root/c['policy_points_ref']['artifact_name']).unlink()
    elif fault=='changed_point':(root/c['policy_points_ref']['artifact_name']).write_bytes(b'{}')
    elif fault=='changed_generation':(root/d['artifact_name']).write_bytes(b'{}')
    elif fault=='missing_witness':
        raw=(root/'intl_generation_current.json').read_bytes();(root/('intl_generation_descriptor_'+hashlib.sha256(raw).hexdigest()+'.json')).unlink()
    elif fault=='revoked':publish_unavailable_generation(data_root=tmp_path)
    elif fault=='changed_current':
        original=reader.read
        def read(self,name,**kw):
            result=original(self,name,**kw)
            if name==c['policy_points_ref']['artifact_name']:publish_unavailable_generation(data_root=tmp_path)
            return result
        monkeypatch.setattr(reader,'read',read)
    elif fault=='wrong_instrument':args['settings']['instrument_a_ref']='arbitrary'
    elif fault=='original_known':args['settings']['revision_policy']='original_known'
    elif fault=='missing_date':args['settings']['period']['start']='2026-08-27'
    else:args['settings']['period']['end']='2027-09-30'
    r=preview_published_policy_points(**args)
    assert r['state']=='unavailable'
    assert not any(k.endswith('_bp')for k in r['result'])

@pytest.mark.parametrize('fault',['no_grant','source_failed','future_commit','missing_revision'])
def test_producer_requires_real_source_and_separate_adopted_mapping_policy(tmp_path,monkeypatch,fault):
    c,p,d,root,args,reader,sources=prepared(tmp_path,monkeypatch);policy=dict(POLICY);digest='d'*64
    if fault=='no_grant':policy['value_permission']='unknown'
    elif fault=='source_failed':sources['EZ']['status']='failed'
    elif fault=='future_commit':sources['EZ']['receipt']['committed_at']='2026-11-05T00:00:00+00:00'
    else:digest=None
    try:r=build_policy_points(generation=GENERATION,ecb=sources['EZ'],boe=sources['GB'],policies=c['policies'],mapping_policy=policy,mapping_document_sha256=digest,evaluated_at=NOW)
    except ValueError:r=None
    assert r is None


def test_expected_feed_transport_failure_is_typed_unavailable(tmp_path,monkeypatch):
    _,_,_,_,args,reader,_=prepared(tmp_path,monkeypatch)
    def unavailable(self,*a,**kw):raise OSError('offline')
    monkeypatch.setattr(reader,'read',unavailable)
    r=preview_published_policy_points(**args)
    assert r['state']=='unavailable' and r['mapping_identity'] is None
    assert not any(k.endswith('_bp') for k in r['result'])
