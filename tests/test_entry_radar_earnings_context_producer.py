"""Synthetic owner-byte fixtures; no provider, live writer or network invocation."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from engine.company_intelligence import research_generation as rg
from engine.company_intelligence.event_workspace import write_workspace_generation
from engine.company_intelligence.opportunity_context import compose_earnings_candidate_case
from engine.entry_radar import earnings_context as ec, quote_context as qc, live_pack as lp
from lib import evidence_foundation as ef
from lib.dataos.identity import ReferenceReadReceipt
from tests.test_earnings_opportunity_qualification import inputs, workspace
from tests.test_entry_radar_quote_context import native

COMPOSED='2026-10-07T14:01:00Z'


@pytest.fixture
def generation(tmp_path,monkeypatch):
    body=workspace();event=body['event_id']
    directory=write_workspace_generation(tmp_path/'owner',{event:body})
    raw=(directory/'manifest.json').read_bytes();manifest=json.loads(raw)
    native_body=(directory/'workspaces'/f'{event}.json').read_bytes()
    calls=[]
    def get_manifest(generation_id,**kw):
        calls.append(('manifest',generation_id));assert generation_id==manifest['generation_id'];return raw,deepcopy(manifest)
    def get_body(event_id,generation_id,**kw):
        calls.append(('workspace',event_id,generation_id));assert event_id==event and generation_id==manifest['generation_id'];return native_body
    monkeypatch.setattr(rg.owner,'fetch_current_workspace_marker_raw',lambda **kw:(raw,deepcopy(manifest)))
    monkeypatch.setattr(rg.owner,'_fetch_generation_manifest_raw',get_manifest)
    monkeypatch.setattr(rg.owner,'_fetch_raw_workspace_bytes',get_body)
    monkeypatch.setattr(rg,'_now',lambda:datetime(2026,10,6,23,tzinfo=timezone.utc))
    pointer=rg.capture_generation_pointer();calls.clear()
    return pointer,manifest,native_body,calls


def test_immutable_generation_wrapper_one_manifest_one_workspace(generation):
    pointer,manifest,raw,calls=generation
    out=rg.read_pinned_generation(pointer,['cik:0000723125','cik:0000320193'])
    assert out['cik:0000320193'] is None
    revision=out['cik:0000723125']['revisions'][0]
    assert revision['workspace_receipt']=={'sha256':sha256(raw).hexdigest(),'bytes':len(raw)}
    assert revision['generation_id']==pointer['generation_id']
    assert len(calls)==2 and calls[0][0]=='manifest' and calls[1][0]=='workspace'
    assert set(pointer)=={'schema','generation_id','manifest_sha256','manifest_bytes','captured_at','owner_generated_at','sha256'}


@pytest.mark.parametrize('mutation',['pointer_hash','manifest_bytes','workspace_bytes','wrong_generation','marker_disagrees'])
def test_owner_verification_not_replaced_by_declared_pointers(generation,monkeypatch,mutation):
    pointer,manifest,raw,calls=generation
    if mutation=='pointer_hash':pointer['sha256']='0'*64
    elif mutation=='manifest_bytes':monkeypatch.setattr(rg.owner,'_fetch_generation_manifest_raw',lambda *a,**k:(b'wrong',manifest))
    elif mutation=='workspace_bytes':monkeypatch.setattr(rg.owner,'_fetch_raw_workspace_bytes',lambda *a,**k:raw+b' ')
    elif mutation=='wrong_generation':
        bad=deepcopy(manifest);bad['generation_id']='0'*24
        monkeypatch.setattr(rg.owner,'_fetch_generation_manifest_raw',lambda *a,**k:(ef.canonical_json_bytes(bad),bad))
    else:
        bad=deepcopy(manifest);bad['generated_at']='2026-10-06T21:00:00Z'
        monkeypatch.setattr(rg.owner,'fetch_current_workspace_marker_raw',lambda **k:(ef.canonical_json_bytes(bad),bad))
        with pytest.raises(rg.EarningsGenerationUnavailable):rg.capture_generation_pointer()
        return
    with pytest.raises(rg.EarningsGenerationUnavailable):rg.read_pinned_generation(pointer,['cik:0000723125'])


@pytest.fixture
def prepared(native,inputs,generation,monkeypatch):
    pointer,manifest,raw,calls=generation
    pack=replace(qc.retain_pack_identity(native['pack'],inputs['identity_read']),earnings_generation=pointer)
    rr=inputs['identity_read'].receipt.as_record();ns=int(datetime.fromisoformat(COMPOSED.replace('Z','+00:00')).timestamp()*1e9)
    rr.update(read_started_at_utc_ns=str(ns),read_completed_at_utc_ns=str(ns+1))
    late=replace(inputs['identity_read'],receipt=ReferenceReadReceipt.from_record(rr))
    import engine.entry_radar.replay.identity_observation_snapshot as reader
    monkeypatch.setattr(reader,'read_identity_snapshot',lambda _:late)
    monkeypatch.setattr(ec,'_now',lambda:datetime.fromisoformat(COMPOSED.replace('Z','+00:00')))
    payload={'schema':'entry_radar.live/v1','asof':inputs['episode']['candidate_at'],
             'episodes':[deepcopy(inputs['episode'])],'events':[{'immutable':'event'}],
             'transitions':[{'immutable':'transition'}],'research_priority':{'immutable':'priority'},'health':{'state':'live'}}
    return payload,pack,calls


def test_post_commit_native_context_real_build_time_and_immutable_lifecycle(prepared):
    payload,pack,calls=prepared;before=deepcopy(payload)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory=Path('/synthetic/reference'),committed=True)
    assert report['attached']==1,report
    context=payload['episodes'][0].pop('research_context')
    assert payload==before
    assert context['schema']=='entry_radar.research_context/v1'
    assert context['projection_kind']=='retrospective_earnings_context'
    assert context['composed_at']==COMPOSED and context['evidence_cutoff']==before['asof']
    assert context['composed_at']!=context['evidence_cutoff']
    assert context['live_projection_eligible'] is False and context['candidate_quote_security_join']=='not_established'
    assert context['observation']['value']==1234
    assert context['observation']['locally_replayed'] is False
    assert context['candidate_context_binding']['scope']=='episode_symbol_context'
    assert 'source_document.v1' not in json.dumps(context)
    assert all(v is False for v in context['authority'].values())
    assert len(calls)==2


@pytest.mark.parametrize('mutation',['not_committed','legacy_pack','late_pointer','bad_candidate','terminal','generation_changed','owner_failure','wrong_period'])
def test_optional_failure_never_changes_native_payload(prepared,monkeypatch,mutation):
    payload,pack,calls=prepared
    committed=True
    if mutation=='not_committed':committed=False
    elif mutation=='legacy_pack':pack=replace(pack,identity_observation=None)
    elif mutation=='late_pointer':
        pack.earnings_generation['captured_at']='2026-10-07T14:00:01Z'
        pack.earnings_generation['sha256']=sha256(ef.canonical_json_bytes({k:v for k,v in pack.earnings_generation.items() if k!='sha256'})).hexdigest()
    elif mutation=='bad_candidate':payload['episodes'][0]['episode_id']='invented'
    elif mutation=='terminal':payload['episodes'][0]['state']='RESOLVED'
    elif mutation=='generation_changed':pack.earnings_generation['manifest_sha256']='0'*64
    elif mutation=='owner_failure':monkeypatch.setattr(ec,'read_pinned_generation',lambda *a:(_ for _ in ()).throw(RuntimeError('PRIVATE BODY')))
    elif mutation=='wrong_period':
        original=ec.read_pinned_generation
        def bad(*args):
            result=original(*args);result['cik:0000723125']['revisions'][0]['workspace']['facts'][0]['period']='2026Q2';return result
        monkeypatch.setattr(ec,'read_pinned_generation',bad)
    before=deepcopy(payload)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory=Path('/synthetic'),committed=committed)
    assert payload==before and report['attached']==0
    assert 'PRIVATE BODY' not in json.dumps(report)
    if mutation in {'not_committed','legacy_pack','late_pointer','bad_candidate','terminal','generation_changed'}:assert calls==[]


def test_native_pack_retains_only_pointer_without_moving_firing_hash(prepared,tmp_path):
    payload,pack,calls=prepared
    assert pack.with_proof({'pass':True}).earnings_generation==pack.earnings_generation
    lp.save_pack(pack,tmp_path)
    restored=lp.load_pack(tmp_path)
    assert restored.earnings_generation==pack.earnings_generation
    assert restored.pack_hash==pack.pack_hash


def test_candidate_bound_is_eight_in_native_identity_order(prepared,monkeypatch):
    payload,pack,calls=prepared
    payload['episodes']=[{**payload['episodes'][0],'episode_id':str(n)} for n in range(12)]
    selected=[]
    def inspect(raw):selected.append(raw['episode_id']);raise ValueError()
    monkeypatch.setattr(ec,'_candidate',inspect)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory=Path('/synthetic'),committed=True)
    assert report['selected']==8 and selected==sorted(str(n) for n in range(12))[:8]
    assert calls==[]


@pytest.mark.parametrize('mutation',['episode','native_generation','snapshot_binding','nested_body','nested_scalar','authority','live','composition_before_cutoff'])
def test_rehashed_context_envelopes_do_not_escape_native_scope(prepared,inputs,mutation):
    payload,pack,calls=prepared
    from engine.company_intelligence.opportunity_context import compose_earnings_candidate_case
    from engine.entry_radar.live_ledger import LiveEpisode
    native=rg.read_pinned_generation(pack.earnings_generation,['cik:0000723125'])['cik:0000723125']
    envelope=compose_earnings_candidate_case(episode=inputs['episode'],identity_read=inputs['identity_read'],vendor='polygon',
        event_id=native['event_id'],revisions=native['revisions'],composed_at=COMPOSED)
    bind=envelope['candidate_context_binding']
    if mutation=='episode':bind['episode_id']='other'
    elif mutation=='native_generation':bind['workspace_native_identity']['generation_id']='0'*24
    elif mutation=='snapshot_binding':bind['identity']['cik']='0000320193'
    elif mutation=='nested_body':bind['identity']['source_body']='PRIVATE'
    elif mutation=='nested_scalar':bind['identity']['vendor']={'private_body':'PRIVATE'}
    elif mutation=='authority':envelope['case']['authority']['can_rank']=True
    elif mutation=='live':envelope['live_projection_eligible']=True
    else:
        from engine.company_intelligence.opportunity_qualification import EarningsQualificationError
        with pytest.raises(EarningsQualificationError):compose_earnings_candidate_case(episode=inputs['episode'],identity_read=inputs['identity_read'],vendor='polygon',
            event_id=native['event_id'],revisions=native['revisions'],composed_at='2026-10-07T13:59:59Z')
        return
    bind['sha256']=sha256(ef.canonical_json_bytes({k:v for k,v in bind.items() if k!='sha256'})).hexdigest()
    with pytest.raises(Exception):ec.project_context(envelope,LiveEpisode.from_dict(inputs['episode']),pack.earnings_generation)


def test_repeated_episode_identity_refuses_without_owner_reads(prepared):
    payload,pack,calls=prepared
    payload['episodes'].append(deepcopy(payload['episodes'][0]))
    before=deepcopy(payload)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory=Path('/synthetic'),committed=True)
    assert report['attached']==0 and payload==before and calls==[]


@pytest.mark.parametrize('companies',[[{}],['cik:bad'],['cik:0000723125']*2,['cik:0000723125']*9])
def test_generation_bound_rejects_bad_issuer_inputs_before_io(generation,companies):
    pointer,manifest,raw,calls=generation
    with pytest.raises(rg.EarningsGenerationUnavailable):rg.read_pinned_generation(pointer,companies)
    assert calls==[]


def test_resource_deadline_stops_before_workspace_and_preserves_committed_payload(prepared,monkeypatch):
    payload,pack,calls=prepared;before=deepcopy(payload)
    clock=[0.0]
    monkeypatch.setattr(rg.owner.time,'monotonic',lambda:clock[0])
    original=rg.owner._fetch_generation_manifest_raw
    def slow(*args,**kwargs):
        result=original(*args,**kwargs);clock[0]=17.0;return result
    monkeypatch.setattr(rg.owner,'_fetch_generation_manifest_raw',slow)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory=Path('/synthetic'),committed=True)
    assert report['refusals']=={'optional_resource_budget':1}
    assert payload==before and len(calls)==1 and calls[0][0]=='manifest'
    # Scoped deadline cannot leak to ordinary/native readers.
    assert rg.owner.check_read_budget()==rg.owner._REQUEST_TIMEOUT_SECONDS


def test_no_pass_headroom_means_no_context_reads(prepared):
    payload,pack,calls=prepared;before=deepcopy(payload)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory=Path('/synthetic'),committed=True,budget_seconds=0)
    assert report['refusals']=={'optional_resource_budget':1} and payload==before and calls==[]


def test_owner_transport_budget_preserves_native_timeout_and_rejects_trickle(monkeypatch):
    owner=rg.owner;clock=[0.0];timeouts=[];sizes=[]
    monkeypatch.setattr(owner.time,'monotonic',lambda:clock[0])
    class Response:
        url='https://example.test/native';headers={};status_code=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_content(self,*,chunk_size):
            sizes.append(chunk_size)
            yield b'a'
            clock[0]=3
            yield b'b'
    def fake_get(*args,**kwargs):timeouts.append(kwargs['timeout']);return Response()
    monkeypatch.setattr(owner.requests,'get',fake_get)
    with pytest.raises(owner.CompanyIntelligenceReadBudgetExceeded):
        with owner.bounded_read_budget(2):owner._fetch_bytes(Response.url,limit=100)
    assert timeouts==[2] and sizes==[65536]
    clock[0]=0
    with owner.bounded_read_budget(16):assert owner._fetch_bytes(Response.url,limit=100)==b'ab'
    assert timeouts[-1]==8
    owner._fetch_bytes(Response.url,limit=100)
    assert sizes[-1]==65536 and timeouts[-1]==8


@pytest.mark.parametrize('mode',['normal','optional_failure','dry_run','not_committed','no_headroom'])
def test_script_only_attaches_after_save_and_optional_failure_preserves_publishing(prepared,monkeypatch,tmp_path,mode):
    from types import SimpleNamespace
    import scripts.entry_radar_live as script
    payload,pack,_=prepared;calls=[];before=deepcopy(payload)
    health={'state':'live','pass':{'at':before['asof']},'inputs':{},'reasons':[]}
    payload['health']=health
    result=SimpleNamespace(health=health,payload=payload,committed=mode!='not_committed',timings={},exit_code=0)
    ledger=SimpleNamespace(save=lambda:calls.append('save'))
    monkeypatch.setattr(script.LP,'assert_published_spec_hashes',lambda:None)
    monkeypatch.setattr(script.LP,'load_pack',lambda _:pack)
    monkeypatch.setattr(script.LL.LiveEpisodeLedger,'load',lambda _:ledger)
    monkeypatch.setattr(script.LL,'EventSpool',lambda:None)
    monkeypatch.setattr(script,'load_quotes',lambda _:{'source':'synthetic'})
    monkeypatch.setattr(script,'_reader',lambda _:None)
    monkeypatch.setattr(script.LE,'run_pass',lambda **_:result)
    monkeypatch.setattr(script,'publish',lambda p,x:calls.append('publish') or True)
    if mode=='no_headroom':
        times=iter([0]+[550]*30)
        monkeypatch.setattr(script.time,'perf_counter',lambda:next(times))
    def attach(value,**kwargs):
        assert calls==['save'] and value is payload
        assert kwargs['committed']==result.committed
        assert kwargs['budget_seconds']==(0 if mode=='no_headroom' else 16)
        calls.append('context')
        if mode=='optional_failure':raise RuntimeError('PRIVATE BODY')
        return {'state':'unavailable','selected':0,'attached':0,'refusals':{}}
    monkeypatch.setattr(ec,'attach_retrospective_earnings_context',attach)
    assert script.run(tmp_path,now=datetime.fromisoformat(COMPOSED.replace('Z','+00:00')),dry_run=mode=='dry_run',
                      state_override=str(tmp_path/'state'),live_override=str(tmp_path/'live'))==0
    assert calls==([] if mode=='dry_run' else ['save','context','publish'])
    assert payload['episodes']==before['episodes'] and payload['events']==before['events']
    assert 'PRIVATE BODY' not in json.dumps(payload)



def test_explicit_research_namespace_has_no_other_vendor_fallback(prepared,monkeypatch):
    payload,pack,calls=prepared;before=deepcopy(payload);vendors=[]
    def unavailable(row,read,vendor):
        vendors.append(vendor)
        raise ValueError('namespace unavailable')
    monkeypatch.setattr(ec,'_identity',unavailable)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory=Path('/synthetic'),committed=True)
    assert vendors==['polygon'] and report['attached']==0 and calls==[] and payload==before



def test_wall_budget_interrupts_inside_transport_and_restores_process_state(monkeypatch):
    owner=rg.owner
    previous=owner.signal.getsignal(owner.signal.SIGALRM)
    def stalled_get(*args,**kwargs):
        # Exercise the installed handler during requests.get, BEFORE any
        # response/stream checkpoint. No sleep, socket or writer is invoked.
        handler=owner.signal.getsignal(owner.signal.SIGALRM)
        assert handler is not previous
        handler(owner.signal.SIGALRM,None)
    monkeypatch.setattr(owner.requests,'get',stalled_get)
    with pytest.raises(owner.CompanyIntelligenceReadBudgetExceeded):
        with owner.bounded_read_budget(16):owner._fetch_bytes('https://example.test/native',limit=100)
    assert owner.signal.getsignal(owner.signal.SIGALRM) is previous
    assert owner.signal.getitimer(owner.signal.ITIMER_REAL)==(0.0,0.0)
    assert owner.check_read_budget()==8


@pytest.mark.parametrize('constraint',['existing_alarm','not_main_thread'])
def test_optional_budget_never_replaces_an_existing_timer_or_uses_a_worker(monkeypatch,constraint):
    owner=rg.owner;writes=[]
    monkeypatch.setattr(owner.signal,'setitimer',lambda *args:writes.append(args))
    if constraint=='existing_alarm':monkeypatch.setattr(owner.signal,'getitimer',lambda *_:(5.0,1.0))
    else:monkeypatch.setattr(owner.threading,'current_thread',lambda:object())
    with pytest.raises(owner.CompanyIntelligenceReadBudgetExceeded):
        with owner.bounded_read_budget(16):raise AssertionError('must not enter')
    assert writes==[]


def test_optional_wall_budget_actually_interrupts_a_blocking_transport(monkeypatch):
    owner=rg.owner;completed=[]
    def blocking_get(*args,**kwargs):
        owner.time.sleep(0.05)  # Local synthetic stall, no network/worker.
        completed.append(True)
        raise AssertionError('budget did not interrupt transport')
    monkeypatch.setattr(owner.requests,'get',blocking_get)
    with pytest.raises(owner.CompanyIntelligenceReadBudgetExceeded):
        with owner.bounded_read_budget(0.005):owner._fetch_bytes('https://example.test/native',limit=100)
    assert completed==[] and owner.signal.getitimer(owner.signal.ITIMER_REAL)==(0.0,0.0)
