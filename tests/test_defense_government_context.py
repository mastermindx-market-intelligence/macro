from copy import deepcopy
from pathlib import Path
from datetime import datetime,timezone
import json
import pytest
from engine.government_revenue.defense_government_context import load_government_context_inputs,qualify_government_context
from engine.government_revenue.defense_economics import validate_defense_economics_payload,defense_economics_content_id

FIXTURES=Path(__file__).parent/'fixtures'
NOW='2026-10-13T07:45:00Z'

@pytest.fixture(scope='module')
def inputs():
    from hashlib import sha256
    out=json.loads((FIXTURES/'defense_government_context_inputs.json').read_text())
    raw={k:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode() for k,v in out.items()}
    return {**out,'raw_bytes':raw,'file_sha256':{k:sha256(v).hexdigest() for k,v in raw.items()}}
@pytest.fixture(scope='module')
def subjects():
    p=json.loads((FIXTURES/'defense_government_context.json').read_text())
    return {r['ticker_display']:{'identity':{'issuer_binding':{'issuer_id':r['issuer_id']},'security_id':r['security_id']}} for r in p['profiles']}


def test_actual_exact_native_prime_paths_all_four_are_dated_and_not_program_capture(inputs,subjects):
    out=qualify_government_context(inputs,subjects,generated_at=NOW)
    assert set(out['axes_by_ticker'])=={'LMT','RTX','NOC','LHX'}
    assert out['local_proof']['source_as_of']=='2026-09-01'
    assert out['local_proof']['current_graph_review_clock'].startswith('2026-10-13')
    assert all(v['demand']['state']=='stale' and set(v)=={'demand'} for v in out['axes_by_ticker'].values())
    assert all('not new orders' in v['demand']['summary_en'] and 'deobligations' in v['demand']['summary_en'] and 'remain unknown' in v['demand']['summary_en'] for v in out['axes_by_ticker'].values())
    assert not out['local_proof']['did_use_collection_ticker'] and not out['local_proof']['did_allocate_amounts']
    for t,row in out['local_proof']['selected'].items():
        assert row['resolution']['source_identity_stable'] and row['resolution']['issuer']['ticker']==t
        assert row['record_known_at']<row['current_graph_review_clock']
    payload=json.loads((FIXTURES/'defense_government_context.json').read_text());assert validate_defense_economics_payload(payload)
    assert all(p['research_state']=='EVIDENCE_INSUFFICIENT' and p['program_workshare'] is None and p['shareholder_capture']['state']=='not_asserted' for p in payload['profiles'])


def test_collection_bucket_and_display_name_are_never_used_for_attribution(inputs,subjects):
    changed=deepcopy(inputs);changed.pop('raw_bytes');changed.pop('file_sha256')
    d=changed['dossier']
    for row in d['awards']:row['collection_scope_tickers']=[];row['recipient']['name']='MISLEADING SAME NAME'
    d['companies']=[]
    from engine.government_revenue.dossiers import dossier_content_id
    d['content_id']=dossier_content_id(d)
    out=qualify_government_context(changed,subjects,generated_at=NOW)
    assert set(out['axes_by_ticker'])=={'LMT','RTX','NOC','LHX'}


def test_current_projection_date_cannot_relabel_old_source_observations(inputs,subjects):
    changed=deepcopy(inputs);changed.pop('raw_bytes');changed.pop('file_sha256')
    changed['dossier']['as_of']='2026-10-13'
    from engine.government_revenue.dossiers import dossier_content_id
    changed['dossier']['content_id']=dossier_content_id(changed['dossier'])
    out=qualify_government_context(changed,subjects,generated_at=NOW)
    for ticker,axes in out['axes_by_ticker'].items():
        source_clock=out['local_proof']['selected'][ticker]['record_known_at']
        assert source_clock.startswith('2026-09-01')
        for axis in axes.values():
            assert axis['state']=='stale'
            assert source_clock in axis['summary_en'] and source_clock in axis['summary_zh']
            assert 'Source cutoff 2026-10-13' not in axis['summary_en']
            assert '来源截点2026-10-13' not in axis['summary_zh']


@pytest.mark.parametrize('fault',['raw_body_mismatch','wrong_hash','future_graph','foreign_security','missing_cik_scope'])
def test_unqualified_source_identity_or_clock_cannot_promote_context(inputs,subjects,fault):
    changed=deepcopy(inputs);financial=deepcopy(subjects)
    if fault=='raw_body_mismatch':changed['dossier']['known_at']='2026-09-02T00:00:00Z'
    if fault=='wrong_hash':changed['file_sha256']['dossier']='a'*64
    if fault=='future_graph':changed['recipient_graph']['graph_known_at']='2026-11-13T00:00:00Z';changed.pop('raw_bytes');changed.pop('file_sha256')
    if fault=='foreign_security':financial['LMT']['identity']['security_id']='xnys:AAPL'
    if fault=='missing_cik_scope':
        changed.pop('raw_bytes');changed.pop('file_sha256')
        refs=next(c['evidence_refs'] for c in changed['recipient_graph']['companies'] if c['ticker']=='LMT')
        for e in changed['recipient_graph']['evidence']:
            if e['evidence_id'] in refs:e['url']=e['url'].replace('/936468/','/320193/')
        out=qualify_government_context(changed,financial,generated_at=NOW);assert 'LMT' not in out['axes_by_ticker'];return
    with pytest.raises(ValueError):qualify_government_context(changed,financial,generated_at=NOW)


def test_rehashed_foreign_nonfinancial_owner_binding_is_rejected():
    p=json.loads((FIXTURES/'defense_government_context.json').read_text());lm=next(v for v in p['profiles'] if v['ticker_display']=='LMT');noc=next(v for v in p['profiles'] if v['ticker_display']=='NOC')
    lm['axes']['demand']['owner_ref']=noc['axes']['demand']['owner_ref'];p['content_id']=defense_economics_content_id(p)
    with pytest.raises(ValueError,match='government_context_subject'):validate_defense_economics_payload(p)


def test_offline_absent_owner_does_not_invent_zero_or_program_presence(subjects):
    out=qualify_government_context(None,subjects,generated_at=NOW);assert out['axes_by_ticker']=={} and out['source_bindings']=={}


def test_qualified_input_projects_through_incumbent_entitled_composer(inputs,subjects):
    from engine.government_revenue.defense_economics import _axis
    out=qualify_government_context(inputs,subjects,generated_at=NOW)
    for ticker,axes in out['axes_by_ticker'].items():
        subject={'issuer_id':subjects[ticker]['identity']['issuer_binding']['issuer_id'],'security_id':subjects[ticker]['identity']['security_id']}
        for name,axis in axes.items():
            projected=_axis(name,axis,out['source_bindings'],datetime.fromisoformat(NOW.replace('Z','+00:00')),subject)
            assert projected['state']=='stale' and 'display_scope' not in projected
            assert projected['owner_ref']==axis['owner_ref']
