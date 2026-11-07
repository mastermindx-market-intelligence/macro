"""Incumbent validator/reader integration over explicitly synthetic evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from engine.market_navigator import ContractError
from engine import market_navigator_memory as nav
from engine.neuralweb import market_memory as mm, market_memory_pit as pit
FIXTURE=Path(__file__).parent/'fixtures/market_navigator/owner_context.synthetic.json'

def packet():
    return mm.validate_as_known_at_context(json.loads(FIXTURE.read_text()))

def rebuild(p,**changes):
    fields={k:deepcopy(p[k]) for k in ('subject','mode','source_receipts','identity_receipt',
        'feature_receipts','feature_registry_version','source_registry_version',
        'state_snapshot_ref','required_domains')}
    fields.update(event_time=p['clocks']['event_time'],as_known_at=p['clocks']['as_known_at'])
    fields.update(changes)
    cutoff=datetime.fromisoformat(fields['as_known_at'].replace('Z','+00:00'))
    for source in fields['source_receipts']:
        measured=datetime.fromisoformat(source['measurement_end'].replace('Z','+00:00'))
        source['age_at_cutoff_seconds']=(cutoff-measured).total_seconds()
    return mm.build_as_known_at_context(**fields)

class Reader:
    """Test transport only; not source authenticity."""
    def __init__(self,value=None,error=None):
        self.value,self.error,self.calls=value,error,[]
    def read_as_known_at(self,**query):
        self.calls.append(deepcopy(query))
        if self.error: raise self.error
        return self.value

def query(p=None,**changes):
    p=p or packet()
    return dict(subject=p['subject'],event_time=p['clocks']['event_time'],
        as_known_at=p['clocks']['as_known_at'],horizon='swing')|changes

def test_clock_meaning_and_exact_retention():
    p=packet();r=Reader(p);out=nav.read_evidence(r,**query(p))
    assert out['source_context']==p and len(r.calls)==1
    row=next(x for x in out['view']['features'] if x['feature_id']=='price.ret_20d')
    c=row['source_clocks'][0]
    assert c['measurement_end']=='2026-08-07T20:00:00Z'
    assert c['available_at']=='2026-08-07T20:00:01Z'
    assert c['observed_at']=='2026-08-07T20:00:03Z'
    assert row['value']==.04
    assert out['view']['status']=='recorded_context'
    assert out['view']['condition_eligibility']=='not_evaluated'
    assert not any(out['authority'].values())

def test_public_view_excludes_source_internals():
    p=packet();out=nav.evidence_view(p,horizon='intraday');text=json.dumps(out)
    for s in p['source_receipts']:
        for k in ('source_id','artifact_sha256','receipt_id'): assert s[k] not in text
    assert p['subject']['instrument_id'] not in text
    assert 'transform_version' not in text
    for row in out['features']:
        if row['unit']=='snapshot_ref':
            assert row['value'] is None
            assert row['representation']=='retained_reference_not_resolved'

def test_detached_results():
    p=packet();original=deepcopy(p);out=nav.read_evidence(Reader(p),**query(p))
    out['source_context']['authority']['may_trade']=True
    out['view']['features'][0]['quality']['flags'].append('changed')
    assert p==original and out['view']['authority']['trading'] is False
    assert 'changed' not in nav.evidence_view(p,horizon='swing')['features'][0]['quality']['flags']

@pytest.mark.parametrize('error,reason',[
    (pit.MarketMemoryContextNotFound('private path'),'exact_context_absent'),
    (PermissionError('secret path'),'source_access_denied'),
    (pit.MarketMemoryStoreError('corrupt reference'),'source_unavailable'),
    (OSError('network path'),'source_unavailable')])
def test_failure_classes_and_no_retry(error,reason):
    r=Reader(error=error);out=nav.read_evidence(r,**query())
    assert len(r.calls)==1 and out['source_context'] is None
    assert out['source_status']==reason and out['view']['status']==reason
    assert str(error) not in json.dumps(out) and not any(out['authority'].values())

@pytest.mark.parametrize('change',[
    {'horizon':'tomorrow'},{'event_time':'2026-08-08T00:00:00Z'},
    {'as_known_at':'2026-08-07'},{'subject':{'subject_id':'x'}}])
def test_bad_query_precedes_read(change):
    r=Reader(packet())
    with pytest.raises(ContractError): nav.read_evidence(r,**query(**change))
    assert not r.calls

@pytest.mark.parametrize('change',[
    {'event_time':'2026-08-07T19:59:59Z'},{'as_known_at':'2026-08-07T20:05:01Z'},
    {'subject':{'subject_id':'different','instrument_id':'different'}}])
def test_response_exact_query_binding(change):
    with pytest.raises(ContractError,match='exact request'):
        nav.read_evidence(Reader(packet()),**query(**change))

def test_equivalent_timezone_query():
    p=packet()
    out=nav.read_evidence(Reader(p),**query(p,event_time='2026-08-07T16:00:00-04:00',
        as_known_at='2026-08-07T16:05:00-04:00'))
    assert out['source_context']==p

@pytest.mark.parametrize('field,value',[
    ('context_id','mmctx_'+'f'*64),('authority',{'may_trade':True}),
    ('outcomes',{'return':.12}),('labels',{'winner':True})])
def test_tamper_and_outcomes_refused(field,value):
    p=packet();p[field]=value
    with pytest.raises(ContractError,match='invalid incumbent'):
        nav.read_evidence(Reader(p),**query())

def test_reconstruction_not_operational():
    p=rebuild(packet(),mode='public_reconstruction')
    with pytest.raises(ContractError,match='reconstruction'):
        nav.read_evidence(Reader(p),**query(p))
    assert nav.evidence_view(p,horizon='swing')['mode']=='public_reconstruction'

def later(p,**changes):
    return rebuild(p,as_known_at='2026-08-07T20:06:00Z',**changes)

def missing(p):
    f=deepcopy(p['feature_receipts']);row=next(x for x in f if x['feature_id']=='price.ret_20d')
    row.update(value=None,status='missing',source_receipt_ids=[],pit_basis='unknown',
        transform_version='market_memory.missing.v1',missing_reason='no_point_in_time_vintage',
        quality={'status':'missing','flags':['not_captured'],'staleness_seconds':None,'imputed':False})
    ids=set(p['identity_receipt']['source_receipt_ids'])
    return rebuild(p,feature_receipts=f,
        source_receipts=[s for s in p['source_receipts'] if s['receipt_id'] in ids])

def test_unchanged_context_no_change():
    p=packet();original=deepcopy(p);out=nav.compare_evidence(p,p,horizon='swing')
    assert out['changes']==[] and p==original
    assert out['original_preserved'] and not any(out['authority'].values())

def test_value_change_preserves_original():
    p=packet();f=deepcopy(p['feature_receipts'])
    next(x for x in f if x['feature_id']=='price.ret_20d')['value']=.08
    q=later(p,feature_receipts=f);row=nav.compare_evidence(p,q,horizon='swing')['changes'][0]
    assert row['kinds']==['recorded_value_changed'] and row['numeric_comparison_permitted']
    assert row['before']['value']==.04 and row['after']['value']==.08
    assert p==packet()

def test_missing_not_zero():
    p=packet();q=later(missing(p));out=nav.compare_evidence(p,q,horizon='position')
    row=next(r for r in out['changes'] if r['feature_id']=='price.ret_20d')
    assert 'became_unavailable' in row['kinds']
    assert row['after']['value'] is None and not row['numeric_comparison_permitted']

def test_new_coverage_not_directional_improvement():
    p=missing(packet());q=later(packet())
    row=nav.compare_evidence(p,q,horizon='swing')['changes'][0]
    assert 'became_available' in row['kinds'] and not row['numeric_comparison_permitted']

def test_time_cannot_regress():
    p=packet()
    with pytest.raises(ContractError,match='regress'):
        nav.compare_evidence(later(p),p,horizon='swing')

def test_exact_query_conflict_is_not_a_refresh():
    p=packet();f=deepcopy(p['feature_receipts'])
    next(x for x in f if x['feature_id']=='price.ret_20d')['value']=.11
    with pytest.raises(ContractError,match='conflicting'):
        nav.compare_evidence(p,rebuild(p,feature_receipts=f),horizon='swing')

def test_comparison_mode_mismatch():
    p=packet()
    with pytest.raises(ContractError,match='same subject'):
        nav.compare_evidence(p,rebuild(p,mode='public_reconstruction'),horizon='swing')

def test_real_owner_file_reader_exact_roundtrip(tmp_path,monkeypatch):
    p=missing(packet())
    monkeypatch.setattr(pit,'_utc_now',lambda:datetime(2026,8,7,20,5,30,tzinfo=timezone.utc))
    stored=pit.capture_context(tmp_path/'owner-store',p)
    reader=pit.FileAsKnownAtReader(tmp_path/'owner-store')
    out=nav.read_evidence(reader,**query(p))
    assert out['source_context']==stored.packet
    assert all(r['status']=='missing' for r in out['view']['features'])
    equivalent=nav.read_evidence(reader,**query(p,event_time='2026-08-07T16:00:00-04:00',as_known_at='2026-08-07T16:05:00-04:00'))
    assert equivalent['source_context']==stored.packet
    monkeypatch.setattr(pit,'_utc_now',lambda:datetime(2026,8,7,20,6,1,tzinfo=timezone.utc))
    absent=nav.read_evidence(reader,**query(p,as_known_at='2026-08-07T20:06:00Z'))
    assert absent['source_status']=='exact_context_absent'

def snapshot_packet():
    return mm.validate_as_known_at_context(json.loads(
        (FIXTURE.parent/'owner_snapshot.synthetic.json').read_text()))

def test_observed_reference_is_not_misrepresented_as_resolved_data():
    p=snapshot_packet();out=nav.evidence_view(p,horizon='swing')
    feature=next(r for r in out['features'] if r['feature_id']=='macro.regime_state')
    original=next(r for r in p['feature_receipts'] if r['feature_id']=='macro.regime_state')
    assert feature['status']=='observed' and feature['value'] is None
    assert feature['representation']=='retained_reference_not_resolved'
    assert original['value']['snapshot_id'] not in json.dumps(out)

def test_changed_reference_does_not_invent_market_direction():
    p=snapshot_packet();f=deepcopy(p['feature_receipts'])
    row=next(r for r in f if r['feature_id']=='macro.regime_state')
    row['value']['snapshot_id']='mmsnap_'+'c'*64
    row['value']['content_sha256']='c'*64
    q=later(p,feature_receipts=f)
    result=nav.compare_evidence(p,q,horizon='swing')['changes'][0]
    assert result['kinds']==['reference_changed']
    assert not result['numeric_comparison_permitted']
    assert result['before']['value'] is result['after']['value'] is None
