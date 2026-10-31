"""Synthetic qualification only; no real candidate, publication or live proof."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from engine.company_intelligence import opportunity_qualification as q
from engine.company_intelligence.documents import SourceDocument, text_span
from engine.entry_radar import challengers as ch, detectors as dt, live_ledger as ll
from engine.entry_radar.replay.identity_observation_snapshot import IdentitySnapshotRead
from lib import evidence_foundation as ef
from tests import test_dataos_identity as identity_fixtures

CIK = '0000723125'
STAMP = '2026-10-07T14:00:00Z'


def workspace(generation='1' * 24, *, available='2026-10-06T20:00:00Z', observed='2026-10-06T20:01:00Z', generated='2026-10-06T20:02:00Z'):
    event = 'evt_cik' + CIK + '_2026q3_results'
    span=text_span(document_id='doc:synthetic-release',document_version=1,body_sha256='a'*64,
        segment_index=0,segment_text='Revenue 1234',start_byte=8,end_byte=12,text='1234',rights_profile='rp_public_primary_v1').to_payload()
    return {'schema':'event_workspace.v1','event_id':event,'generation_id':generation,'generated_at':generated,
        'issuer':{'company_id':'cik:'+CIK,'display_name':'Synthetic issuer'},
        'fiscal_period':{'year':2026,'quarter':3},
        'lifecycle':{'source_available_at':available,'observed_at':observed,'state':'complete'},
        'facts':[{'schema':'event_fact.v1','metric':'revenue','value':1234,'unit':'usd_millions','period':'2026Q3',
                  'basis':'reported','event_id':event,'source_span':span}],
        'deltas':[],'guidance':[],'claims':[],'sources':[{'kind':'issuer_release','document_id':'doc:synthetic-release',
            'source_sha256':'a'*64,'receipt_state':'byte_replayed',
            'filing_key':{'cik':CIK,'accession':'0000723125-26-000001'},'form':'8-K'}],
        'aliases':[],'warnings':[],'completeness':{},'qa_exchanges':[],
        'authority':'context_only','prophet_flags':dict.fromkeys(['may_rank','may_size','may_gate','prophet_authority'],False),
        'claim_citations_pending':False}


def revision(body):
    raw=ef.canonical_json_bytes(body)
    return {'generation_id':body['generation_id'],'workspace':body,
        'source_available_at':body['lifecycle']['source_available_at'],'observed_at':body['lifecycle']['observed_at'],
        'source_sha256':'a'*64,'workspace_receipt':{'sha256':sha256(raw).hexdigest(),'bytes':len(raw)}}


@pytest.fixture
def inputs():
    original, history, aliases, master = identity_fixtures._obs_base()
    for row in master:
        if row['security_id']=='SEC:US-XNAS-MU':
            row.update(issuer_id='ISS:US-XNAS-MU',issuer_cik=CIK,issuer_state='RESOLVED')
    snapshot, receipt = identity_fixtures._obs_snapshot(original,history,aliases,master)
    read = IdentitySnapshotRead(snapshot,receipt)
    spec=dt.get_spec(ch.C2_DETECTOR_ID)
    episode=ll.LiveEpisode(episode_id=ll.compute_episode_id(ticker='MU',detector_id=ch.C2_DETECTOR_ID,
        variant='JC2',first_armed_at=STAMP), ticker='MU',detector_id=ch.C2_DETECTOR_ID,
        detector_version=spec.version,detector_spec_hash=spec.spec_hash,state='CANDIDATE',variant='JC2',
        first_armed_at=STAMP,candidate_at=STAMP,market_session='2026-10-07').to_dict()
    return dict(episode=episode,event_id=workspace()['event_id'],revisions=[revision(workspace())],identity_read=read,vendor='polygon')


def test_qualifies_native_earnings_context_without_claiming_quote_identity_or_rights(inputs):
    result=q.qualify_candidate_workspace(**inputs)
    assert result['state']=='qualified_context'
    assert result['observation']['value']==1234 and result['observation']['unit']=='usd_millions'
    assert result['observation']['field_path']=='facts[0]'
    bind=result['candidate_binding']
    assert bind['episode_id']==inputs['episode']['episode_id']
    assert bind['episode_canonical_sha256']==sha256(ll.LiveEpisode.from_dict(inputs['episode']).canonical.encode()).hexdigest()
    assert bind['identity']['cik']==CIK and bind['identity']['security_id']=='SEC:US-XNAS-MU'
    assert bind['identity']['identity_read_receipt']==inputs['identity_read'].receipt.as_record()
    assert bind['candidate_quote_security_join']=='not_established'
    assert result['live_projection_eligible'] is False
    assert result['remaining_input']=='native_candidate_quote_listing_identity_provenance'
    assert result['purpose_scope']['whole_workspace_rights']=='unknown'
    evidence=result['evidence']
    ref=next(iter(evidence['references'].values()))
    assert ref['rights']=={'state':'unknown','policy_id':None}
    assert ref['subject']=={'key_type':'cik','key':CIK} and ref['secondary_subjects']==[]
    assert evidence['recipe']['recipe_name']=='earnings_workspace_k5.v1'
    assert evidence['recipe']['identity_joins']==[]
    receipt=ef.compile_recipe(evidence['recipe'],blocks=evidence['blocks'],references=evidence['references'])
    assert receipt['state']=='partial' and receipt['denominator']['total']==1
    wire=json.dumps(result)
    assert 'source_document.v1' not in wire and 'Synthetic issuer' not in wire
    assert not any(result['authority'].values())
    assert q.qualify_candidate_workspace(**inputs)==result


@pytest.mark.parametrize('mutation,code',[
    ('terminal','candidate_required'),('episode_id','candidate_identity_mismatch'),('spec','candidate_identity_mismatch'),
    ('naive_cut','qualification_clock_unknown'),('clock_order','candidate_clock_order_invalid'),
    ('vendor','candidate_alias_not_bound_by_cutoff'),('unknown_cik','candidate_issuer_unresolved'),
    ('wrong_cik','workspace_owner_binding_invalid'),('future','workspace_not_known_at_candidate'),
    ('clock_unknown','qualification_clock_unknown'),('clock_reversed','workspace_clock_order_invalid'),
    ('tie','workspace_revision_clock_tie'),('rights','workspace_derived_rights_unqualified'),
    ('missing_rights','workspace_derived_rights_unqualified'),('doc_hash','workspace_derived_rights_unqualified'),
    ('source_clock','workspace_document_after_candidate'),('missing_source','workspace_fact_source_ambiguous'),
    ('metric','workspace_revenue_ambiguous_or_absent'),('units','workspace_fact_unqualified'),
    ('bool','workspace_fact_unqualified'),('double_fact','workspace_revenue_ambiguous_or_absent'),
    ('source_binding','workspace_owner_binding_invalid'),('generation','workspace_owner_binding_invalid'),
    ('other_event','workspace_owner_binding_invalid'),('huge_value','workspace_fact_unqualified'),
    ('private_source','workspace_derived_rights_unqualified'),
])
def test_refuses_unqualified_inputs_without_substitution(inputs,mutation,code):
    inp={**inputs,'episode':deepcopy(inputs['episode']),'revisions':deepcopy(inputs['revisions'])}
    body=inp['revisions'][0]['workspace']
    if mutation in {'rights','doc_hash','source_clock','private_source'}:
        from engine.company_intelligence.documents import FilingKey
        body['sources'][0]['source_document']=SourceDocument(document_id='doc:synthetic-release',event_id=body['event_id'],
            document_kind='release',source_class='issuer_release',content_sha256='a'*64,content_bytes=100,
            fetched_at='2026-10-06T20:01:00Z',available_at='2026-10-06T20:00:00Z',
            filing_key=FilingKey(**body['sources'][0]['filing_key']),
            rights_profile='rp_public_primary_v1',rights_state='public_primary').to_payload()
    if mutation=='terminal':inp['episode']['state']='RESOLVED'
    elif mutation=='episode_id':inp['episode']['episode_id']='another-episode'
    elif mutation=='spec':inp['episode']['detector_spec_hash']='0'*64
    elif mutation=='naive_cut':inp['episode']['candidate_at']=STAMP[:-1]
    elif mutation=='clock_order':inp['episode']['candidate_at']='2026-10-07T13:59:59Z'
    elif mutation=='vendor':inp['vendor']='store'
    elif mutation=='unknown_cik':
        o,h,a,m=identity_fixtures._obs_base();s,r=identity_fixtures._obs_snapshot(o,h,a,m);inp['identity_read']=IdentitySnapshotRead(s,r)
    elif mutation=='wrong_cik':body['issuer']['company_id']='cik:0000320193'
    elif mutation=='future':inp['revisions']=[revision(workspace(available='2026-10-08T20:00:00Z',observed='2026-10-08T20:01:00Z',generated='2026-10-08T20:02:00Z'))]
    elif mutation=='clock_unknown':body['lifecycle']['observed_at']=None;inp['revisions'][0]['observed_at']=None
    elif mutation=='clock_reversed':body['generated_at']='2026-10-06T19:00:00Z'
    elif mutation=='tie':inp['revisions'].append(deepcopy(inp['revisions'][0]))
    elif mutation=='rights':body['sources'][0]['source_document']['rights_state']='unknown'
    elif mutation=='missing_rights':body['facts'][0]['source_span']['rights_profile']='rp_unknown_v1'
    elif mutation=='doc_hash':body['sources'][0]['source_document']['content_sha256']='b'*64
    elif mutation=='source_clock':body['sources'][0]['source_document']['fetched_at']='2026-10-08T00:00:00Z'
    elif mutation=='missing_source':body['facts'][0]['source_span']['document_id']='absent'
    elif mutation=='metric':body['facts'][0]['metric']='invented_signal'
    elif mutation=='units':body['facts'][0]['unit']='guessed_USD'
    elif mutation=='bool':body['facts'][0]['value']=True
    elif mutation=='double_fact':body['facts'].append(deepcopy(body['facts'][0]))
    elif mutation=='source_binding':inp['revisions'][0]['source_sha256']='b'*64
    elif mutation=='generation':inp['revisions'][0]['generation_id']='2'*24
    elif mutation=='other_event':inp['event_id']=inp['event_id'].replace('2026q3','2026q2')
    elif mutation=='huge_value':body['facts'][0]['value']=10**400
    elif mutation=='private_source':body['sources'][0]['source_document']['source_class']='third_party'
    with pytest.raises(q.EarningsQualificationError,match='^'+code+'$'):
        q.qualify_candidate_workspace(**inp)


def test_selects_latest_pre_cut_revision_not_later_correction(inputs):
    inputs['revisions'] += [revision(workspace('2'*24,available='2026-10-08T20:00:00Z',observed='2026-10-08T20:01:00Z',generated='2026-10-08T20:02:00Z'))]
    result=q.qualify_candidate_workspace(**inputs)
    assert next(iter(result['evidence']['references'].values()))['native_identity']['generation_id']=='1'*24


def test_read_after_candidate_is_not_a_historical_identity_witness(inputs):
    read=inputs['identity_read'];snap=read.snapshot
    after=int(datetime.fromisoformat(STAMP.replace('Z','+00:00')).timestamp())*10**9+1
    rr=read.receipt.as_record();rr.update(read_started_at_utc_ns=str(after),read_completed_at_utc_ns=str(after+1))
    from lib.dataos.identity import ReferenceReadReceipt
    inputs['identity_read']=IdentitySnapshotRead(snap,ReferenceReadReceipt.from_record(rr))
    with pytest.raises(q.EarningsQualificationError,match='^candidate_alias_not_bound_by_cutoff$'):
        q.qualify_candidate_workspace(**inputs)


def test_native_release_source_shape_needs_no_new_document_export(inputs):
    body=inputs['revisions'][0]['workspace']
    assert 'source_document' not in body['sources'][0]
    result=q.qualify_candidate_workspace(**inputs)
    assert result['observation']['lineage_state']=='owner_byte_replay_receipt'
    assert result['observation']['locally_replayed'] is False
    assert result['purpose_scope']['whole_workspace_rights']=='unknown'


@pytest.mark.parametrize('field,value',[
    ('form',None), ('filing_key',{'cik':'0000320193','accession':'0000723125-26-000001'}),
])
def test_native_release_identity_is_not_just_a_public_span_profile(inputs,field,value):
    inputs['revisions'][0]['workspace']['sources'][0][field]=value
    with pytest.raises(q.EarningsQualificationError,match='^workspace_release_identity_invalid$'):
        q.qualify_candidate_workspace(**inputs)


def test_unknown_supplement_profile_cannot_inherit_release_admission(inputs):
    source=inputs['revisions'][0]['workspace']['sources'][0]
    source.update(kind='issuer_supplement',supplement_profile='invented_profile')
    # Keep an issuer-release row for the native revision source-hash binding.
    inputs['revisions'][0]['workspace']['sources'].append({'kind':'issuer_release','source_sha256':'a'*64})
    with pytest.raises(q.EarningsQualificationError,match='^workspace_fact_lineage_invalid$'):
        q.qualify_candidate_workspace(**inputs)


@pytest.mark.parametrize('mutation', ['span_hash','span_address','span_id','document_id','period','fact_event'])
def test_refuses_forged_field_lineage_and_non_period_prose(inputs,mutation):
    fact=inputs['revisions'][0]['workspace']['facts'][0]
    if mutation=='span_hash':fact['source_span']['receipt']['source_sha256']='b'*64
    elif mutation=='span_address':fact['source_span']['locator']['span_start_byte']=0
    elif mutation=='span_id':fact['source_span']['span_id']='/private/raw-source'
    elif mutation=='document_id':
        fact['source_span']['document_id']='/private/raw-source'
        inputs['revisions'][0]['workspace']['sources'][0]['document_id']='/private/raw-source'
    elif mutation=='period':fact['period']='private prose instead of a fiscal period'
    elif mutation=='fact_event':fact['event_id']=fact['event_id'].replace('2026q3','2026q2')
    code='workspace_fact_period_mismatch' if mutation=='period' else 'workspace_fact_(lineage|identity)_invalid'
    with pytest.raises(q.EarningsQualificationError,match='^'+code+'$'):
        q.qualify_candidate_workspace(**inputs)


def test_actual_owner_builder_release_shape_is_projectable_without_new_rights_export():
    # Existing corpus is a fixture, never a retained/live candidate proof.
    from tests.test_company_intelligence_event_workspace import _build_flagship
    native=_build_flagship()
    observation=q._source_fact(native,datetime(2026,10,7,tzinfo=timezone.utc))
    assert observation['unit'] in {'USD','usd_millions'}
    assert observation['lineage_state']=='owner_byte_replay_receipt'
    assert observation['locally_replayed'] is False


@pytest.mark.parametrize('field,value', [('basis',{}),('unit',[]),('value',None)])
def test_invalid_scalar_shapes_return_only_typed_refusal(inputs,field,value):
    inputs['revisions'][0]['workspace']['facts'][0][field]=value
    with pytest.raises(q.EarningsQualificationError,match='^workspace_fact_unqualified$'):
        q.qualify_candidate_workspace(**inputs)


def test_source_revisions_and_identity_must_be_injected_no_fallback_read(inputs,monkeypatch):
    import engine.neuralweb.company_intelligence_reader as reader
    def forbidden(*args,**kwargs):
        raise AssertionError('qualification must not perform source I/O')
    monkeypatch.setattr(reader,'read_event_source_revisions',forbidden)
    assert q.qualify_candidate_workspace(**inputs)['state']=='qualified_context'
