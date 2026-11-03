"""Actual controller upload boundaries and no-replay/fairness regressions."""
from dataclasses import asdict, replace
import base64
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest
from scripts import ci_admission_stages as stages
from scripts import merge_on_green as mog
from scripts import ci_proof_admission as pa

CTX = dict(repository_id=17, protected_controller_sha='4'*40, current_run_id='70', current_run_attempt=1)


def pull(n=7, *, head='1'*40):
    return dict(number=n, state='open', draft=True, head={'sha':head},
                base={'ref':'main','sha':'4'*40,'repo':{'id':17}}, labels=[],
                merge_commit_sha='3'*40, mergeable=True)


@pytest.fixture
def controller(monkeypatch, tmp_path):
    s=stages.Stages('acme/widgets','read','write','checks',CTX,tmp_path)
    def refuse(*args,**kwargs): raise AssertionError('unexpected live API')
    monkeypatch.setattr(mog,'_request',refuse)
    monkeypatch.setattr(s,'authority',lambda:None)
    monkeypatch.setattr(mog,'installed_admitted_dispatch_ready',lambda *a:True)
    monkeypatch.setattr(s,'initialize_empty_register',lambda:None)
    monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(True,(),()))
    monkeypatch.setattr(mog,'open_pulls',lambda *a:[pull()])
    monkeypatch.setattr(s,'history',lambda p,*_:([],[]))
    monkeypatch.setattr(mog,'shared_admission_inventory',lambda *a:mog.SharedAdmissionInventory('shared',True))
    def facts(pulls):
        return {p['number']:dict(comments=[],ci_present=bool(mog.head_check_runs('acme/widgets',p['head']['sha'],'read')),native=s.candidate_native_entrypoint(p)) for p in pulls}
    monkeypatch.setattr(stages,'BulkReader',lambda *a,**k:SimpleNamespace(facts=facts))
    monkeypatch.setattr(s,'candidate_native_entrypoint',lambda p:False)
    monkeypatch.setattr(mog,'head_check_runs',lambda *a:[])
    monkeypatch.setattr(mog.SweepBudget,'preflight',lambda *a,**k:(True,''))
    monkeypatch.setattr(mog.SweepBudget,'may_continue',lambda *a,**k:(True,''))
    return s


def test_real_isolated_entry_uses_controller_canonical_contract():
    root=Path(__file__).resolve().parents[1]
    code=f"import runpy;d=runpy.run_path({str(root/'scripts/ci_admission_stages.py')!r});assert d['contract'] is d['mog'].proof_admission"
    done=subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True)
    assert done.returncode==0,done.stderr


def test_installed_bridge_accepts_cutover_candidate_despite_main_native(controller):
    result=controller.prepare(native_pr_enabled=True,freshness=None)
    assert result=={'ready':True,'changed':True,'count':1}
    d=controller.load('census')['demands'][0]
    assert d['purpose']=='authored' and d['head_sha']=='1'*40
    pa.ordered_demands([pa.Demand(**d)])


def test_cutover_main_does_not_duplicate_candidate_native_index_gap(controller,monkeypatch):
    monkeypatch.setattr(controller,'candidate_native_entrypoint',lambda p:True)
    assert controller.prepare(native_pr_enabled=False,freshness=None)['count']==0
    assert not (controller.directory/'demands-digest.json').exists()


@pytest.mark.parametrize('settled', [True,False])
def test_terminal_incomplete_or_active_original_never_mints_same_source(controller,monkeypatch,settled):
    a=pa.Admission('a'*12,7,'1'*40,'4'*40,'3'*40,'4'*40,99,1,settled)
    monkeypatch.setattr(mog,'shared_proof_workload',lambda *x,**k:mog.SharedProofWorkload(True,(),(a,)))
    assert controller.prepare(native_pr_enabled=False,freshness=None)['count']==0


def test_incomplete_census_has_no_receipt_or_reservation(controller,monkeypatch):
    monkeypatch.setattr(mog,'open_pulls',lambda *a:[pull(7),pull(8)])
    def checks(repo,head,token):
        checks.count+=1
        if checks.count==2:raise ValueError('truncated original check inventory')
        return []
    checks.count=0
    monkeypatch.setattr(mog,'head_check_runs',checks)
    with pytest.raises(ValueError,match='truncated'):controller.prepare(native_pr_enabled=False,freshness=None)
    assert list(controller.directory.iterdir())==[]


def test_pending_head_replacement_keeps_old_refresh_age(controller,monkeypatch):
    old=pa.Demand(7,'2'*40,'refresh','2026-10-01T00:00:00Z','a'*12)
    monkeypatch.setattr(controller,'history',lambda p,*_:([],[old]))
    controller.prepare(native_pr_enabled=False,freshness=None)
    d=pa.Demand(**controller.load('census')['demands'][0])
    assert d==replace(old,head_sha='1'*40)


def census(s):
    old=pa.Demand(7,'1'*40,'refresh','2026-10-01T00:00:00Z','a'*12)
    new=pa.Demand(8,'2'*40,'authored','2026-10-02T00:00:00Z','b'*12)
    s.save('census',{'context':CTX,'pulls':[],'demands':[asdict(new),asdict(old)]})
    return old,new


def test_global_held_does_not_skip_older_refresh(controller,monkeypatch):
    census(controller);seen=[]
    def reserve(repo,read,write,d,**kw):
        seen.append(d.pr_number);return mog.AdmissionDispatchResult('held',detail='unknown inventory')
    monkeypatch.setattr(mog,'reserve_shared_admission',reserve)
    assert controller.reserve()['disposition']=='held'
    assert seen==[7]


def test_only_affirmatively_ineligible_may_skip_older_demand(controller,monkeypatch):
    census(controller);seen=[]
    def reserve(repo,read,write,d,**kw):
        seen.append(d.pr_number)
        return mog.AdmissionDispatchResult('ineligible' if d.pr_number==7 else 'held')
    monkeypatch.setattr(mog,'reserve_shared_admission',reserve)
    controller.reserve();assert seen==[7,8]


def test_unknown_reservation_never_advances_to_next_demand(controller,monkeypatch):
    census(controller);seen=[]
    def reserve(repo,read,write,d,**kw):
        seen.append(d.pr_number);return mog.AdmissionDispatchResult('unknown')
    monkeypatch.setattr(mog,'reserve_shared_admission',reserve)
    with pytest.raises(RuntimeError,match='UNKNOWN'):controller.reserve()
    assert seen==[7]


def test_stage_files_are_original_once_no_overwrite(controller):
    controller.save('same',{'original':1})
    with pytest.raises(FileExistsError):controller.save('same',{'replacement':1})
    assert controller.load('same')=={'original':1}


def test_candidate_entrypoint_binds_exact_ordered_merge(controller,monkeypatch):
    raw=b'on:\n  workflow_dispatch:\njobs: {}\n'
    calls=[]
    def request(method,url,token):
        calls.append(url)
        if '/git/commits/' in url:return 200,{'sha':'3'*40,'parents':[{'sha':'4'*40},{'sha':'1'*40}]}
        assert url.endswith('?ref='+'3'*40)
        return 200,{'type':'file','encoding':'base64','size':len(raw),'content':base64.b64encode(raw).decode()}
    monkeypatch.setattr(mog,'_request',request)
    # Invoke the real method, rather than this fixture's cheap discovery stub.
    assert stages.Stages.candidate_native_entrypoint(controller,pull()) is False
    assert len(calls)==2


def test_forged_or_reversed_merge_never_reads_candidate_workflow(controller,monkeypatch):
    calls=[]
    def request(*args):
        calls.append(args);return 200,{'sha':'3'*40,'parents':[{'sha':'1'*40},{'sha':'4'*40}]}
    monkeypatch.setattr(mog,'_request',request)
    assert stages.Stages.candidate_native_entrypoint(controller,pull()) is None
    assert len(calls)==1


def test_authenticated_tested_base_replaces_dispatch_control_sha(monkeypatch):
    checks=[{'name':'ci-gate','external_id':mog.ADMITTED_SUBJECT_CHECK_PREFIX+'anything'}]
    monkeypatch.setattr(mog,'admitted_semantic_evidence_for_head',lambda *a,**k:SimpleNamespace(evidence={'base_sha':'2'*40}))
    f=mog.ProofFreshness('acme/widgets','read',[],[])
    assert f.exact_proof_base(pull(),checks)[0]=='2'*40


def test_unavailable_admitted_base_never_falls_back_to_head_ancestry(monkeypatch):
    checks=[{'name':'ci-gate','external_id':mog.ADMITTED_SUBJECT_CHECK_PREFIX+'anything'}]
    def bad(*a,**k):raise ValueError('partial original')
    monkeypatch.setattr(mog,'admitted_semantic_evidence_for_head',bad)
    f=mog.ProofFreshness('acme/widgets','read',[],[])
    monkeypatch.setattr(f,'included_main_base',lambda *a:pytest.fail('forbidden fallback'))
    assert f.stale_for(pull(),checks)[0] is None


class OriginalServer:
    """Test-owned GitHub endpoints; real stage and receipt authentication code."""
    def __init__(self):
        self.description='a2 idle';self.comments=[];self.labels=[]
        self.artifacts={};self.archives={};self.runs={};self.writes=[]
        self.control=dict(id=70,run_attempt=1,status='in_progress',head_sha='4'*40,
            repository={'id':17,'full_name':'acme/widgets'},head_branch='main',event='schedule',
            path='.github/workflows/merge-on-green.yml')

    def upload(self,s,suffix,name):
        import io,zipfile,hashlib
        payload=(s.directory/suffix/'ci-proof-admission.json').read_bytes()
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('ci-proof-admission.json',payload)
        ident=80+len(self.artifacts)
        self.archives[ident]=out.getvalue()
        self.artifacts[ident]=dict(id=ident,name=name,expired=False,
            digest='sha256:'+hashlib.sha256(out.getvalue()).hexdigest(),
            workflow_run={'id':70,'repository_id':17,'head_sha':'4'*40})
        return ident

    def request(self,method,url,token,payload=None):
        from urllib.parse import urlparse,parse_qs
        path=urlparse(url).path.removeprefix('/repos/acme/widgets')
        query=parse_qs(urlparse(url).query)
        if method!='GET':self.writes.append((method,path,payload))
        if path in {'/actions/runs/70','/actions/runs/70/attempts/1'}:return 200,self.control
        if path.startswith('/actions/artifacts/'):
            return 200,self.artifacts[int(path.split('/')[3])]
        if path.startswith('/labels/'):
            if method=='PATCH':self.description=payload['description']
            return 200,{'description':self.description}
        if path=='/issues':
            return 200,([dict(number=7,state='open',pull_request={},labels=self.labels)] if self.labels else [])
        if path=='/pulls':return 200,[pull()]
        if path=='/pulls/7':return 200,pull()
        if path=='/issues/7/comments':
            if method=='POST':
                assert token=='read'  # protected job token, never mutable PAT identity
                c=dict(id=100+len(self.comments),body=payload['body'],user={'id':41898282,'login':'github-actions[bot]','type':'Bot'},performed_via_github_app={'id':15368});self.comments.append(c);return 201,c
            return 200,self.comments
        if path.startswith('/issues/comments/'):
            return 200,next(c for c in self.comments if c['id']==int(path.rsplit('/',1)[-1]))
        if path=='/issues/7/labels':
            if method=='POST':self.labels=[{'name':n} for n in payload['labels']]
            return 200,self.labels
        if path.startswith('/git/commits/'):return 200,{'sha':'3'*40,'parents':[{'sha':'4'*40},{'sha':'1'*40}]}
        if path.startswith('/contents/'):
            raw=b'on:\n  workflow_dispatch:\njobs: {}\n'
            return 200,{'type':'file','encoding':'base64','size':len(raw),'content':base64.b64encode(raw).decode()}
        if path=='/branches/main':return 200,{'commit':{'sha':'4'*40}}
        if path=='/actions/workflows/ci.yml/runs':
            rows=[r for r in self.runs.values() if r['status']==query['status'][0]]
            return 200,{'total_count':len(rows),'workflow_runs':rows}
        if path=='/actions/workflows/ci.yml/dispatches':
            assert self.description.endswith('s=started')
            assert any(c['body'].startswith(mog.ADMISSION_COMMENT_PREFIX) for c in self.comments)
            self.runs[99]=dict(id=99,run_attempt=1,status='queued',head_sha='4'*40,
                repository={'id':17},head_branch='main',event='workflow_dispatch',path='.github/workflows/ci.yml')
            return 200,{'workflow_run_id':99}
        if path.startswith('/actions/runs/'):
            return 200,self.runs[int(path.rsplit('/',1)[-1])]
        raise AssertionError((method,path,query))


def original_server(monkeypatch,tmp_path):
    monkeypatch.setattr(mog,'installed_admitted_dispatch_ready',lambda *a:True)
    server=OriginalServer()
    monkeypatch.setattr(mog,'_request',server.request)
    monkeypatch.setattr(mog,'_download_semantic_artifact',lambda url,token:server.archives[int(url.split('/')[-2])])
    monkeypatch.setattr(mog,'head_check_runs',lambda *args:[])
    monkeypatch.setattr(mog.SweepBudget,'preflight',lambda *a,**k:(True,''))
    monkeypatch.setattr(mog.SweepBudget,'may_continue',lambda *a,**k:(True,''))
    s=stages.Stages('acme/widgets','read','write','checks',CTX,tmp_path)
    monkeypatch.setattr(stages,'BulkReader',lambda *a,**k:SimpleNamespace(facts=lambda pulls:{p['number']:dict(comments=server.comments,ci_present=False,native=False) for p in pulls}))
    clock=[1800000000]
    def sleep(seconds):clock[0]+=seconds
    monkeypatch.setattr(s,'anchor_indexer',lambda:stages.AnchorIndexer(mog,s.repo,s.read,CTX,deadline=clock[0]+240,clock=lambda:clock[0],sleep=sleep))
    return s,server


def test_real_controller_upload_dispatch_binding_chain_with_seven_active(monkeypatch,tmp_path):
    s,server=original_server(monkeypatch,tmp_path)
    for n in range(201,208):server.runs[n]=dict(id=n,run_attempt=1,status='queued',event='pull_request')
    assert s.prepare(native_pr_enabled=True,freshness=None)['count']==1
    demands=server.upload(s,'demands','ci-proof-demands-70-1')
    result=s.reserve(demands);assert result['prepared'] is True
    generation=result['generation']
    # One labeled anchor now retains the whole immutable age batch, but no
    # demand row is counted as an admission/reservation.
    assert mog.REFRESH_LEASE_LABEL in {row['name'] for row in server.labels}
    records,pending=s.history(pull())
    assert records == [] and len(pending) == 1
    assert pending[0].demand_id == generation
    prepared=server.upload(s,'prepared',f'ci-proof-admission-70-1-{generation}-prepared')
    checkpoint=server.upload(s,'checkpoint','ci-proof-checkpoint-70-1-7')
    assert s.dispatch(prepared,checkpoint)==dict(bound=True,generation=generation)
    # Once the protected admission is actually indexed, the original lease
    # association remains present for outstanding capacity and recovery.
    assert mog.REFRESH_LEASE_LABEL in {row['name'] for row in server.labels}
    bound=server.upload(s,'bound',f'ci-proof-admission-70-1-{generation}-bound')
    assert s.finalize(bound)==dict(finalized=True)
    assert server.description=='a2 idle'
    workload=mog.shared_proof_workload('acme/widgets','read',repository_id=17,protected_controller_sha='4'*40)
    assert workload.complete
    assert pa.capacity(workload.runs,workload.admissions,census_complete=True,records_complete=True)==0
    dispatches=[x for x in server.writes if x[1].endswith('/dispatches')]
    assert len(dispatches)==1
    assert dispatches[0][2]['inputs']['subject_head_sha']=='1'*40
    assert dispatches[0][2]['inputs']['tested_merge_sha']=='3'*40
    assert not any('update-branch' in path or '/merges' in path or 'check-runs' in path for _,path,_ in server.writes)


def test_eighth_arrival_between_upload_and_dispatch_closes_actual_stage(monkeypatch,tmp_path):
    s,server=original_server(monkeypatch,tmp_path)
    s.prepare(native_pr_enabled=True,freshness=None)
    result=s.reserve(server.upload(s,'demands','ci-proof-demands-70-1'))
    g=result['generation']
    prepared=server.upload(s,'prepared',f'ci-proof-admission-70-1-{g}-prepared')
    checkpoint=server.upload(s,'checkpoint','ci-proof-checkpoint-70-1-7')
    for n in range(201,209):server.runs[n]=dict(id=n,run_attempt=1,status='queued',event='pull_request')
    with pytest.raises(RuntimeError,match='did not bind: held'):s.dispatch(prepared,checkpoint)
    assert not any(path.endswith('/dispatches') for _,path,_ in server.writes)
    assert server.description.endswith('s=prepared')


def completion_fixture(controller,monkeypatch,result):
    a=pa.Admission('a'*12,7,'1'*40,'4'*40,'3'*40,'4'*40,99,1)
    ref=dict(artifact_id=81,controller_run_id=70,controller_attempt=1,controller_sha='4'*40,payload_sha256='b'*64)
    state={'description':'a2 idle','publisher_calls':0,'writes':[],'checks':[]}
    monkeypatch.setattr(mog,'shared_admission_inventory',lambda *a:mog.SharedAdmissionInventory('shared',True,({'number':7,'state':'open'},),None))
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[])
    def history(*args,reference_catalog,**kw):
        reference_catalog[(a.generation,a.run_id)]=ref
        return [a],[]
    monkeypatch.setattr(mog,'pr_admission_history',history)
    monkeypatch.setattr(mog,'_admitted_reads',lambda *a:(None,None))
    monkeypatch.setattr(mog,'_admitted_check_inventory',lambda *a:state['checks'])
    monkeypatch.setattr(mog,'_read_admitted_run',lambda *args:pa.Run(99,1,'completed','pr_head'))
    monkeypatch.setattr(mog,'admitted_completion_proof',lambda *a,**k:{})
    def publish(*args,**kwargs):
        assert state['description'].endswith('s=completing')
        state['publisher_calls']+=1;return {'disposition':result}
    monkeypatch.setattr(mog,'publish_admitted_subject_checks',publish)
    def request(method,url,token,payload=None):
        if method!='GET':state['writes'].append((method,url,payload))
        if '/pulls/' in url:return 200,pull()
        if method=='PATCH':state['description']=payload['description']
        return 200,{'description':state['description']}
    monkeypatch.setattr(mog,'_request',request)
    return state,ref


def test_coalesced_terminal_completion_is_reconciled_without_trigger(controller,monkeypatch):
    state,_=completion_fixture(controller,monkeypatch,'published')
    assert controller.complete()=={'disposition':'reconciled','count':1,'held':0}
    assert state['publisher_calls']==1 and state['description']=='a2 idle'
    assert [p['description'] for _,_,p in state['writes']]==['a2 p=7 g=aaaaaaaaaaaa s=completing','a2 idle']


def test_unknown_completion_retains_custody_and_never_reposts(controller,monkeypatch):
    state,_=completion_fixture(controller,monkeypatch,'unknown')
    assert controller.complete()['disposition']=='unknown'
    assert state['description'].endswith('s=completing')
    def absent(*a,**kw):raise ValueError('missing original triplet')
    monkeypatch.setattr(mog,'admitted_semantic_evidence_for_head',absent)
    assert controller.complete()['disposition']=='unknown'
    assert state['publisher_calls']==1 and len(state['writes'])==1


@pytest.mark.parametrize('launch_started,issues', [
    (False, ({'number':7,'state':'closed'},)),
    (True, ({'number':8,'state':'open'},{'number':7,'state':'closed'})),
])
def test_closed_original_launch_cannot_claim_reconciled_or_touch_other_effects(
        controller,monkeypatch,launch_started,issues):
    # Preserve the original prepared/started/completing custody; no read or
    # publication on a different OPEN PR may precede the closed-owner refusal.
    inventory=mog.SharedAdmissionInventory('shared',True,issues,(7,'a'*12),launch_started)
    monkeypatch.setattr(mog,'shared_admission_inventory',lambda *a:inventory)
    monkeypatch.setattr(mog,'fetch_issue_comments',
                        lambda *a,**k:pytest.fail('closed original blocks other completion'))
    assert controller.complete()=={
        'disposition':'held',
        'detail':'closed original PR retains launch custody; no completion effect',
    }


def test_missing_original_launch_association_is_unknown_not_clean(controller,monkeypatch):
    inventory=mog.SharedAdmissionInventory('shared',True,({'number':8,'state':'open'},),(7,'a'*12))
    monkeypatch.setattr(mog,'shared_admission_inventory',lambda *a:inventory)
    monkeypatch.setattr(mog,'fetch_issue_comments',
                        lambda *a,**k:pytest.fail('missing original blocks completion'))
    assert controller.complete()=={
        'disposition':'unknown',
        'detail':'original launch owner missing from complete inventory',
    }


def test_legacy_cleanup_cannot_erase_shared_association(monkeypatch):
    p=pull();p['labels']=[{'name':mog.REFRESH_LEASE_LABEL}]
    lease=mog.RefreshLease('acme/widgets','read','write',readable=False)
    monkeypatch.setattr(mog,'_remove_refresh_lease_label',lambda *a:pytest.fail('shared association delete'))
    assert lease.release(p,'merged') is False
    assert mog.REFRESH_LEASE_LABEL in mog.label_names(p)


def test_rejected_terminal_proof_before_intent_does_not_write_or_replay(controller,monkeypatch):
    state,_=completion_fixture(controller,monkeypatch,'published')
    def absent(*a,**kw):raise ValueError('missing original semantic artifact')
    monkeypatch.setattr(mog,'admitted_completion_proof',absent)
    assert controller.complete()=={'disposition':'reconciled','count':0,'held':1}
    assert state['publisher_calls']==0 and state['writes']==[]


@pytest.mark.parametrize('prefix', [mog.DEMAND_COMMENT_PREFIX,mog.ADMISSION_COMMENT_PREFIX,mog.CHECKPOINT_COMMENT_PREFIX])
def test_untrusted_comment_namespace_cannot_poison_complete_census(controller,monkeypatch,prefix):
    comment={'id':71,'user':{'id':42,'login':'untrusted-pr-author','type':'User'},'body':prefix+'{'}
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[comment])
    monkeypatch.setattr(controller,'history',lambda p,*_:stages.Stages.history(controller,p))
    monkeypatch.setattr(mog,'_request',lambda *a:pytest.fail('outsider requires no artifact/permission GET'))
    assert controller.prepare(native_pr_enabled=False,freshness=None)['count']==1



@pytest.mark.parametrize('author', [None,{'id':41898282,'login':'github-actions[bot]','type':'Bot'}])
def test_genuine_or_unknown_index_provenance_never_becomes_empty(controller,monkeypatch,author):
    comment={'id':71,'user':author,'body':mog.DEMAND_COMMENT_PREFIX+'{'}
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[comment])
    monkeypatch.setattr(controller,'history',lambda p,*_:stages.Stages.history(controller,p))
    with pytest.raises(ValueError):controller.prepare(native_pr_enabled=False,freshness=None)
    assert not (controller.directory/'census.json').exists()


def test_associated_pr_with_only_untrusted_comments_stays_unknown(controller,monkeypatch):
    p=pull();p['labels']=[{'name':mog.REFRESH_LEASE_LABEL}]
    comment={'id':71,'user':{'id':42,'login':'outsider','type':'User'},'body':mog.DEMAND_COMMENT_PREFIX+'{'}
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[comment])
    monkeypatch.setattr(mog,'_request',lambda *a:(200,{'permission':'read','user':{'id':42}}))
    with pytest.raises(ValueError,match='lacks authenticated'):
        stages.Stages.history(controller,p)


def test_preintent_missing_proof_does_not_starve_later_original(controller,monkeypatch):
    state,ref=completion_fixture(controller,monkeypatch,'published')
    monkeypatch.setattr(mog,'shared_admission_inventory',lambda *a:mog.SharedAdmissionInventory(
        'shared',True,({'number':7,'state':'open'},{'number':8,'state':'open'}),None))
    def history(repo,token,number,comments,*,reference_catalog,**kw):
        a=pa.Admission(('a' if number==7 else 'b')*12,number,'1'*40,'4'*40,'3'*40,'4'*40,99 if number==7 else 100,1)
        reference_catalog[(a.generation,a.run_id)]=ref
        return [a],[]
    monkeypatch.setattr(mog,'pr_admission_history',history)
    monkeypatch.setattr(mog,'_read_admitted_run',lambda repo,token,a,*rest:pa.Run(a.run_id,1,'completed','pr_head'))
    seen=[]
    def proof(*a,expected_run_id,**kw):
        seen.append(expected_run_id)
        if expected_run_id==99:raise ValueError('missing original evidence')
        return {}
    monkeypatch.setattr(mog,'admitted_completion_proof',proof)
    assert controller.complete()=={'disposition':'reconciled','count':1,'held':1}
    assert seen==[99,100] and state['publisher_calls']==1
    assert state['description']=='a2 idle'
    assert state['writes'][0][2]['description']=='a2 p=8 g=bbbbbbbbbbbb s=completing'


@pytest.mark.parametrize('wrong_phase', ['POST','GET'])
def test_stage_index_unknown_author_never_advances_to_association(controller,monkeypatch,wrong_phase):
    calls=[];saved={}
    bot={'id':41898282,'login':'github-actions[bot]','type':'Bot'}
    def request(method,url,token,payload=None):
        calls.append((method,url));assert '/comments' in url
        if method=='POST':
            assert token=='read';saved['body']=payload['body']
        return (201 if method=='POST' else 200),dict(id=71,body=saved['body'],
            user={'id':42,'login':'pat-owner','type':'User'} if method==wrong_phase else bot)
    monkeypatch.setattr(mog,'_request',request)
    with pytest.raises(RuntimeError,match='UNKNOWN'):
        controller.index(7,mog.DEMAND_COMMENT_PREFIX,{})
    assert sum(method=='POST' for method,_ in calls)==1


def test_foundation_has_no_register_migration_or_demand_effect(controller, monkeypatch):
    seen = []
    monkeypatch.setattr(mog, 'installed_admitted_dispatch_ready',
                        lambda repo, sha: seen.append((repo, sha)) or False)
    def forbidden(*a, **k):
        pytest.fail('uninstalled bridge must not migrate, census, or create demand')
    monkeypatch.setattr(controller, 'initialize_empty_register', forbidden)
    monkeypatch.setattr(mog, 'shared_proof_workload', forbidden)
    monkeypatch.setattr(mog, 'open_pulls', forbidden)
    assert controller.prepare(native_pr_enabled=False, freshness=None) == {
        'ready': False, 'changed': False, 'count': 0}
    assert seen == [('acme/widgets', '4'*40)]
    assert list(controller.directory.iterdir()) == []


@pytest.mark.parametrize('original_result', ['published', 'unknown'])
def test_readiness_loss_keeps_original_completion_and_unknown_custody(
        controller, monkeypatch, original_result):
    state, _ = completion_fixture(controller, monkeypatch, original_result)
    def no_new_work(*a):
        pytest.fail('existing completion must not consult the new-dispatch gate')
    monkeypatch.setattr(mog, 'installed_admitted_dispatch_ready', no_new_work)
    result = controller.complete()
    if original_result == 'published':
        assert result == {'disposition': 'reconciled', 'count': 1, 'held': 0}
        assert state['description'] == 'a2 idle'
    else:
        assert result['disposition'] == 'unknown'
        assert state['description'].endswith('s=completing')


# Decision observation: no new authority, reads, admission or retry.

def admission(g='a'*12, pr=7, run_id=None):
    return pa.Admission(g, pr, '1'*40, '4'*40, '3'*40, '4'*40, run_id)


def runs(n):
    return tuple(pa.Run(i+1, 1, 'in_progress', 'pr_head') for i in range(n))


def demand(pr=7, g='a'*12, purpose='refresh', age='2026-10-01T00:00:00Z'):
    return pa.Demand(pr, '1'*40, purpose, age, g)


def test_capacity_observes_deduplication_and_unindexed_floor():
    rows = runs(5) + (runs(5)[0], pa.Run(80, 1, 'waiting', 'main'))
    records = (admission(run_id=1), admission('b'*12, 8, 90), admission('c'*12, 9))
    decision = {}
    plain = pa.capacity(rows, records, census_complete=True, records_complete=True)
    observed = pa.capacity(rows, records, census_complete=True, records_complete=True, decision=decision)
    assert observed == plain == 1
    assert decision == dict(evaluated=True, cap=8, census_complete=True,
        records_complete=True, validated=True, free_slots=1,
        counted_run_ids=[1,2,3,4,5,90], indexed_active_run_ids=[1,2,3,4,5],
        bound_floor_run_ids=[90], unindexed_generations=['c'*12],
        counted_run_count=6, unindexed_count=1, legacy_reservations=0, used_slots=7)


@pytest.mark.parametrize('census,records', [(False,True),(True,False),(False,False)])
def test_incomplete_capacity_does_not_publish_validated_count(census, records):
    decision={}
    assert pa.capacity(runs(1), (), census_complete=census, records_complete=records, decision=decision)==0
    assert decision['validated'] is False
    assert decision['census_complete'] is census and decision['records_complete'] is records
    assert 'used_slots' not in decision and 'counted_run_ids' not in decision


def test_invalid_identity_is_not_logged_as_validated_input():
    decision={}
    assert pa.capacity((pa.Run('secret-like-invalid-value',1,'queued','pr_head'),),(),
        census_complete=True,records_complete=True,decision=decision)==0
    assert decision['validated'] is False
    assert 'secret-like' not in json.dumps(decision)


def test_existing_inventory_is_not_silently_truncated():
    decision={}
    assert pa.capacity(runs(101), (), census_complete=True, records_complete=True, decision=decision)==0
    assert decision['counted_run_ids']==list(range(1,102))
    assert decision['used_slots']==101


@pytest.mark.parametrize('n,allowed',[(7,True),(8,False)])
def test_dispatch_recheck_records_reservation_exclusion(n,allowed):
    original=admission(); decision={}
    assert pa.reserved_dispatch_allowed(runs(n),(original,),original,
        census_complete=True,records_complete=True,decision=decision) is allowed
    assert decision['allowed'] is allowed and decision['evaluated'] is True
    assert decision['reserved_generation']==original.generation
    assert decision['capacity_excludes_reserved_generation'] is True
    assert decision['capacity']['used_slots']==n
    assert decision['capacity']['unindexed_generations']==[]


def test_missing_reservation_never_claims_capacity_evaluation():
    decision={}
    assert pa.reserved_dispatch_allowed(runs(1),(),admission(),
        census_complete=True,records_complete=True,decision=decision) is False
    assert decision==dict(evaluated=True,allowed=False,reservation_validated=False,capacity={'evaluated':False})


@pytest.fixture
def backend(monkeypatch):
    state=dict(register='a2 idle', calls=[], n=7, records=(), complete=True, post='bound')
    monkeypatch.setattr(mog,'_shared_controller_authority',lambda *a,**k:True)
    monkeypatch.setattr(mog,'installed_admitted_dispatch_ready',lambda *a,**k:True)
    monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(state['complete'],runs(state['n']),state['records']))
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *a,**k:admission())
    def request(method,url,token,payload=None):
        state['calls'].append((method,url,payload))
        if '/labels/' in url:
            if method=='PATCH': state['register']=payload['description']
            return 200,{'description':state['register']}
        # Decision-output fixture: complete empty age history, including the
        # direct owner read required once the original launch pointer is set.
        if '/issues?' in url: return 200,[]
        if '/issues/7/comments?' in url: return 200,[]
        if url.endswith('/issues/7'):
            return 200,dict(number=7,state='open',pull_request={},labels=[])
        if '/pulls/' in url:
            return 200,dict(number=7,state='open',mergeable=True,head={'sha':'1'*40},
                base={'ref':'main','sha':'4'*40,'repo':{'id':17}},merge_commit_sha='3'*40)
        if '/git/commits/' in url:
            return 200,dict(sha='3'*40,parents=[{'sha':'4'*40},{'sha':'1'*40}])
        if url.endswith('/branches/main'): return 200,{'commit':{'sha':'4'*40}}
        if url.endswith('/dispatches'):
            if state['post']=='unknown': raise TimeoutError('private transport detail')
            if state['post']=='refused': return 403,{}
            return 200,{'workflow_run_id':99}
        raise AssertionError((method,url))
    monkeypatch.setattr(mog,'_request',request)
    return state


def test_reserve_log_input_does_not_change_result_or_requests(backend):
    plain=mog.reserve_shared_admission('acme/widgets','READ_SECRET','WRITE_SECRET',demand(),**CTX)
    calls=list(backend['calls']);backend.update(register='a2 idle',calls=[])
    decision={}
    observed=mog.reserve_shared_admission('acme/widgets','READ_SECRET','WRITE_SECRET',demand(),decision=decision,**CTX)
    assert observed==plain and backend['calls']==calls
    assert observed.disposition=='prepared' and observed.admission.run_id is None
    assert decision['capacity']['used_slots']==7


def test_existing_generation_preserves_capacity_short_circuit(backend):
    backend['records']=(admission(),)
    decision={}
    result=mog.reserve_shared_admission('acme/widgets','r','w',demand(),decision=decision,**CTX)
    assert result.disposition=='held' and backend['calls']==[]
    assert decision=={'capacity':{'evaluated':False}}


@pytest.mark.parametrize('n,post,expected',[(7,'bound','bound'),(8,'bound','held'),(7,'unknown','unknown'),(7,'refused','refused')])
def test_dispatch_evidence_preserves_result_and_exact_requests(backend,n,post,expected):
    backend.update(n=n,post=post,records=(admission(),),register='a2 p=7 g=aaaaaaaaaaaa s=prepared')
    ref=dict(controller_run_id=70,controller_attempt=1,artifact_id=55,payload_sha256='f'*64)
    plain=mog.dispatch_admitted_pr_proof('acme/widgets','r','w',ref,**CTX)
    calls=list(backend['calls']);backend.update(calls=[],register='a2 p=7 g=aaaaaaaaaaaa s=prepared')
    decision={}
    observed=mog.dispatch_admitted_pr_proof('acme/widgets','r','w',ref,decision=decision,**CTX)
    assert observed==plain and observed.disposition==expected
    assert backend['calls']==calls
    assert decision['capacity_recheck']['allowed'] is (n==7)
    assert decision['capacity_recheck']['capacity']['used_slots']==n
    assert sum(method=='POST' for method,_,_ in calls)==(n==7)


def logs(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def stage(tmp_path,monkeypatch):
    s=stages.Stages('acme/widgets','READ_SECRET','WRITE_SECRET','CHECK_SECRET',CTX,tmp_path)
    monkeypatch.setattr(s,'authority',lambda:None)
    return s


def test_stage_logs_stable_order_and_live_skip_without_granting_later_priority(tmp_path,monkeypatch,capsys):
    s=stage(tmp_path,monkeypatch)
    old=demand(); new=demand(8,'b'*12,'authored','2026-10-02T00:00:00Z')
    s.save('census',dict(context=CTX,demands=[asdict(new),asdict(old)]))
    def reserve(*args,decision,**kwargs):
        d=args[3];decision['capacity']={'evaluated':True,'validated':True,'used_slots':7,'free_slots':1}
        return mog.AdmissionDispatchResult('ineligible' if d.pr_number==7 else 'held',detail='fixed diagnostic')
    monkeypatch.setattr(mog,'reserve_shared_admission',reserve)
    assert s.reserve()['disposition']=='held'
    rows=logs(capsys)
    assert rows[0]['census_complete'] is True
    assert rows[0]['eligibility_phase']=='prepare' and rows[0]['live_eligibility_recheck_required'] is True
    assert [d['demand_id'] for d in rows[0]['ordered_demands']]==['a'*12,'b'*12]
    assert [r['disposition'] for r in rows[1:]]==['ineligible','held']
    assert all(r['selected'] is None for r in rows[1:])
    assert 'SECRET' not in json.dumps(rows)


def test_stage_prepared_selection_is_not_a_bound_run(tmp_path,monkeypatch,capsys,backend):
    s=stage(tmp_path,monkeypatch)
    s.save('census',dict(context=CTX,demands=[asdict(demand())]))
    monkeypatch.setattr(mog,'prepare_shared_checkpoint',lambda *a,**k:pa.Checkpoint(7,1,(),(),()))
    assert s.reserve()==dict(prepared=True,generation='a'*12,pr_number=7)
    rows=logs(capsys)
    assert rows[-1]['disposition']=='prepared'
    assert rows[-1]['selected']==dict(pr_number=7,generation='a'*12)
    assert rows[-1]['decision']['capacity']['used_slots']==7
    receipt=json.loads((tmp_path/'prepared/ci-proof-admission.json').read_text())
    assert receipt['admission']['run_id'] is None and receipt['admission']['settled'] is False


@pytest.mark.parametrize('post,expected',[('bound','bound'),('unknown','unknown'),('refused','refused')])
def test_stage_dispatch_logs_before_unknown_or_refusal_raise(tmp_path,monkeypatch,capsys,backend,post,expected):
    s=stage(tmp_path,monkeypatch)
    s.save('checkpoint-digest','e'*64);s.save('prepared-digest','f'*64)
    monkeypatch.setattr(mog,'authenticated_checkpoint_from_ref',lambda *a,**k:pa.Checkpoint(7,1,(),(),()))
    monkeypatch.setattr(s,'index',lambda *a:None)
    monkeypatch.setattr(mog,'publish_prepared_shared_admission',lambda *a,**k:mog.AdmissionDispatchResult('indexed',admission()))
    backend.update(records=(admission(),),register='a2 p=7 g=aaaaaaaaaaaa s=prepared',post=post)
    if post=='bound': assert s.dispatch(55,56)==dict(bound=True,generation='a'*12)
    else:
        with pytest.raises(RuntimeError,match='original dispatch did not bind'):s.dispatch(55,56)
    row=logs(capsys)[0]
    assert row['admission_decision']=='dispatch' and row['disposition']==expected
    assert row['admission']['run_id']==(99 if post=='bound' else None)
    assert row['admission']['settled'] is False
    assert row['decision']['capacity_recheck']['allowed'] is True
    assert 'SECRET' not in json.dumps(row) and 'private transport' not in json.dumps(row)
    assert sum(method=='POST' for method,_,_ in backend['calls'])==1
    assert backend['register']=='a2 p=7 g=aaaaaaaaaaaa s=started'


def test_reused_observation_cannot_retain_stale_count_on_incomplete_input():
    decision={}
    pa.capacity(runs(7),(),census_complete=True,records_complete=True,decision=decision)
    assert decision['used_slots']==7
    pa.capacity((),(),census_complete=False,records_complete=False,decision=decision)
    assert decision['validated'] is False and 'used_slots' not in decision


@pytest.mark.parametrize('operation',['reserve','dispatch'])
def test_original_incomplete_workload_retains_refusal_without_effect(backend,operation):
    backend.update(complete=False,records=(admission(),) if operation=='dispatch' else ())
    decision={}
    if operation=='reserve':
        result=mog.reserve_shared_admission('acme/widgets','r','w',demand(),decision=decision,**CTX)
        capacity=decision['capacity']
    else:
        ref=dict(controller_run_id=70,controller_attempt=1,artifact_id=55,payload_sha256='f'*64)
        result=mog.dispatch_admitted_pr_proof('acme/widgets','r','w',ref,decision=decision,**CTX)
        capacity=decision['capacity_recheck']['capacity']
    assert result.disposition=='held' and backend['calls']==[]
    assert capacity['census_complete'] is False and capacity['records_complete'] is False
    assert capacity['validated'] is False and 'used_slots' not in capacity


def test_order_log_preserves_every_existing_candidate_without_new_cap(tmp_path,monkeypatch,capsys):
    s=stage(tmp_path,monkeypatch)
    candidates=[demand(i+1,f'{i+1:012x}') for i in range(101)]
    s.save('census',dict(context=CTX,demands=[asdict(d) for d in reversed(candidates)]))
    monkeypatch.setattr(mog,'reserve_shared_admission',lambda *a,**k:mog.AdmissionDispatchResult('held'))
    assert s.reserve()['disposition']=='held'
    order=logs(capsys)[0]
    assert order['ordered_demands']==[asdict(d) for d in candidates]


def test_foreign_or_invalid_census_never_emits_complete_order(tmp_path,monkeypatch,capsys):
    s=stage(tmp_path,monkeypatch)
    s.save('census',dict(context={},demands=[asdict(demand())]))
    with pytest.raises(ValueError,match='foreign'):s.reserve()
    assert logs(capsys)==[]


class BulkProvider:
    """Only provider/time are synthetic; real stage, budget and receipt code."""
    def __init__(self, count=900):
        self.pulls={n:pull(n,head=f'{n:040x}') for n in range(1,count+1)}
        for n,p in self.pulls.items():p['merge_commit_sha']=f'{10000+n:040x}'
        self.comments={n:[] for n in self.pulls};self.labels={n:[] for n in self.pulls}
        self.description='a2 idle';self.core=1000;self.points=1000;self.calls=[];self.queries=[]
        self.artifacts={};self.archives={};self.now=1800000000;self.lose_post=False;self.deliver_lost=True
        self.control=dict(id=70,run_attempt=1,status='in_progress',head_sha='4'*40,
            repository={'id':17,'full_name':'acme/widgets'},head_branch='main',event='schedule',
            path='.github/workflows/merge-on-green.yml')
    def sleep(self,seconds):self.now+=seconds
    def connection(self,rows):return dict(totalCount=len(rows),nodes=rows,pageInfo={'hasNextPage':False,'endCursor':None})
    def upload(self,s):
        import io,zipfile,hashlib
        payload=(s.directory/'demands/ci-proof-admission.json').read_bytes();out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('ci-proof-admission.json',payload)
        aid=80+len(self.artifacts);archive=out.getvalue();self.archives[aid]=archive
        self.artifacts[aid]=dict(id=aid,name='ci-proof-demands-70-1',expired=False,
            digest='sha256:'+hashlib.sha256(archive).hexdigest(),
            workflow_run={'id':70,'repository_id':17,'head_sha':'4'*40})
        return aid
    def gql_comment(self,c,n):
        return dict(id='C'+str(c['id']),fullDatabaseId=str(c['id']),body=c['body'],createdAt=c['created_at'],
            repository={'nameWithOwner':'acme/widgets'},pullRequest={'number':n},
            author={'__typename':c['user']['type'],'login':c['user']['login'],'databaseId':c['user']['id']})
    def gql(self,query):
        import re,hashlib
        self.queries.append(query);self.points-=2;out={}
        raw='on:\n  workflow_dispatch:\njobs: {}\n';oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw.encode()).hexdigest()
        for match in re.finditer(r'p([0-9]+):pullRequest\(number:([0-9]+)\)',query):
            n=int(match[1]);p=self.pulls[n]
            out['p'+str(n)]=dict(number=n,state=p['state'].upper(),isDraft=p['draft'],headRefOid=p['head']['sha'],baseRefOid=p['base']['sha'],baseRefName='main',repository={'nameWithOwner':'acme/widgets'},
                comments=self.connection([self.gql_comment(c,n) for c in self.comments[n]]),
                potentialMergeCommit=dict(oid=p['merge_commit_sha'],parents=self.connection([{'oid':p['base']['sha']},{'oid':p['head']['sha']}]),file=dict(path='.github/workflows/ci.yml',type='blob',oid=oid,object=dict(__typename='Blob',oid=oid,byteSize=len(raw),isBinary=False,isTruncated=False,text=raw))))
            out['h'+str(n)]=dict(__typename='Commit',oid=p['head']['sha'],checkSuites=self.connection([]))
        return {'data':{'repository':out,'rateLimit':{'cost':2,'remaining':self.points,'limit':1000,'resetAt':'2026-11-03T16:00:00Z'}}}
    def request(self,method,url,token,payload=None):
        from urllib.parse import urlparse,parse_qs
        path=urlparse(url).path.removeprefix('/repos/acme/widgets');q=parse_qs(urlparse(url).query)
        self.calls.append((method,path,payload,self.now))
        if path=='/rate_limit':return 200,{'resources':{'core':{'limit':1000,'remaining':self.core},'graphql':{'limit':1000,'remaining':self.points}}}
        if path=='/graphql':return 200,self.gql(payload['query'])
        self.core-=1
        assert self.core>=0,'real REST allowance exhausted'
        if path.startswith('/actions/runs/70'):return 200,self.control
        if path.startswith('/actions/artifacts/'):return 200,self.artifacts[int(path.split('/')[3])]
        if path.startswith('/labels/'):
            if method=='PATCH':self.description=payload['description']
            return 200,{'description':self.description}
        if path=='/issues':return 200,[dict(number=n,state=self.pulls[n]['state'],pull_request={},labels=ls) for n,ls in self.labels.items() if ls]
        if path=='/pulls':
            page=int(q['page'][0]);rows=[p for p in self.pulls.values() if p['state']=='open'];return 200,rows[(page-1)*100:page*100]
        if path.startswith('/pulls/'):return 200,self.pulls[int(path.rsplit('/',1)[1])]
        if path=='/actions/workflows/ci.yml/runs':return 200,{'total_count':0,'workflow_runs':[]}
        if path.startswith('/issues/comments/'):
            ident=int(path.rsplit('/',1)[1]);return 200,next(c for cs in self.comments.values() for c in cs if c['id']==ident)
        if path.startswith('/issues/'):
            n=int(path.split('/')[2])
            if path.endswith('/comments'):
                if method=='POST':
                    assert token=='read'
                    c=dict(id=10000+sum(map(len,self.comments.values())),body=payload['body'],created_at='2026-11-03T14:00:00Z',issue_url='https://api.github.com/repos/acme/widgets/issues/'+str(n),user={'id':41898282,'login':'github-actions[bot]','type':'Bot'})
                    if not self.lose_post or self.deliver_lost:self.comments[n].append(c)
                    if self.lose_post:raise TimeoutError('original response lost')
                    return 201,c
                return 200,self.comments[n]
            if path.endswith('/labels'):
                if method=='POST':self.labels[n]=[{'name':name} for name in payload['labels']]
                return 200,self.labels[n]
            return 200,dict(number=n,state=self.pulls[n]['state'],pull_request={},labels=self.labels[n])
        raise AssertionError((method,path,payload))


def bulk_stage(monkeypatch,tmp_path,count=900):
    provider=BulkProvider(count)
    monkeypatch.setattr(mog,'_request',provider.request)
    monkeypatch.setattr(mog,'_download_semantic_artifact',lambda url,token:provider.archives[int(url.split('/')[-2])])
    # Installed-source capability is independently tested; no budget/history or
    # census method is replaced here. This fixture models the qualified bridge.
    monkeypatch.setattr(mog,'installed_admitted_dispatch_ready',lambda *args:True)
    s=stages.Stages('acme/widgets','read','write','checks',CTX,tmp_path/'first')
    def indexer():return stages.AnchorIndexer(mog,s.repo,s.read,CTX,deadline=provider.now+240,clock=lambda:provider.now,sleep=provider.sleep)
    monkeypatch.setattr(s,'anchor_indexer',indexer)
    return s,provider,indexer


def test_bulk_900_complete_prepare_one_anchor_preserves_every_age(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path)
    result=s.prepare(native_pr_enabled=True,freshness=None)
    assert result['count']==900 and result['changed'] is True
    assert len(p.queries)==36 and p.points==928 and p.core>950
    before=json.loads((s.directory/'demands/ci-proof-admission.json').read_text())['demands']
    artifact=p.upload(s);i=indexer();i.start(artifact,1);assert i.advance()['disposition']=='indexed'
    assert sum(map(len,p.comments.values()))==1 and len(p.labels[1])==1
    assert mog.shared_proof_workload(s.repo,s.read,repository_id=17,protected_controller_sha='4'*40).admissions==()
    p.pulls[1]['state']='closed'  # Closed anchor still carries every other age.
    p.pulls[900]['head']['sha']='e'*40
    s.directory=tmp_path/'second'
    again=s.prepare(native_pr_enabled=True,freshness=None)
    assert again['count']==899
    after=json.loads((s.directory/'census.json').read_text())['demands']
    old={d['pr_number']:d for d in before}
    for d in after:
        assert (d['requested_at'],d['demand_id'],d['purpose'])==(old[d['pr_number']]['requested_at'],old[d['pr_number']]['demand_id'],old[d['pr_number']]['purpose'])
    assert next(d for d in after if d['pr_number']==900)['head_sha']=='e'*40
    assert p.core>850 and p.points>800
    writes=[c for c in p.calls if c[0] in {'POST','PATCH','DELETE'} and c[1]!='/graphql']
    assert len(writes)==6  # 4 singleton writes +1 original comment +1 association
    assert all(b[3]-a[3]>=10 for a,b in zip(writes,writes[1:]))


@pytest.mark.parametrize('delivered',[True,False])
def test_bulk_anchor_lost_response_never_reposts(monkeypatch,tmp_path,delivered):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,3);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s);i=indexer();i.start(aid,1);p.lose_post=True;p.deliver_lost=delivered
    assert i.advance()['disposition']=='unknown'
    p.lose_post=False;p.pulls[1]['state']='closed'
    result=indexer().advance()
    assert result['disposition']==('indexed' if delivered else 'unknown')
    assert len([x for x in p.calls if x[0]=='POST' and x[1].endswith('/comments')])==1
    if not delivered:
        assert stages.IndexState.parse(p.description).intent==1
        assert s.complete()['disposition']=='held'
        inventory=mog.shared_admission_inventory(s.repo,s.read)
        assert inventory.launch is None and inventory.indexing is not None


def test_bulk_anchor_budget_stop_before_intent_is_resumable(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,3);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s);i=indexer();i.start(aid,1);i.deadline=p.now+15
    assert i.advance()['disposition']=='partial'
    assert stages.IndexState.parse(p.description).intent==0
    assert indexer().advance()['disposition']=='indexed'
    assert sum(map(len,p.comments.values()))==1


def test_bulk_crash_after_comment_intent_is_unknown_not_retry(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,3);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s);i=indexer();i.start(aid,1)
    state=stages.IndexState.parse(p.description)
    i.store(replace(state,intent=1))  # original process died before a response
    assert indexer().advance()['disposition']=='unknown'
    assert sum(map(len,p.comments.values()))==0


def test_bulk_foreign_comment_cannot_clear_original_intent(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,3);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s);i=indexer();i.start(aid,1);ref,_=i.authenticate(stages.IndexState.parse(p.description))
    body=mog.DEMAND_COMMENT_PREFIX+json.dumps(ref,sort_keys=True,separators=(',',':'))
    p.comments[1].append(dict(id=999,body=body,created_at='2026-11-03T14:00:00Z',user={'id':42,'login':'outsider','type':'User'}))
    i.store(replace(stages.IndexState.parse(p.description),intent=1))
    assert indexer().advance()['disposition']=='unknown'


@pytest.mark.parametrize('mutation',['graphql-error','hidden-comments','wrong-head','wrong-parent','truncated-blob','foreign-comment','low-quota'])
def test_bulk_census_refuses_partial_or_foreign_inputs(monkeypatch,tmp_path,mutation):
    s,p,_=bulk_stage(monkeypatch,tmp_path,1);original=p.gql
    def bad(query):
        data=original(query);row=data['data']['repository']['p1']
        if mutation=='graphql-error':data['errors']=[{'message':'partial resource failure'}]
        elif mutation=='hidden-comments':row['comments']['totalCount']=1
        elif mutation=='wrong-head':row['headRefOid']='e'*40
        elif mutation=='wrong-parent':row['potentialMergeCommit']['parents']['nodes'].reverse()
        elif mutation=='truncated-blob':row['potentialMergeCommit']['file']['object']['isTruncated']=True
        elif mutation=='foreign-comment':
            row['comments']=p.connection([dict(id='C1',fullDatabaseId='1',body='x',createdAt='x',repository={'nameWithOwner':'evil/repo'},pullRequest={'number':1},author={'__typename':'User','databaseId':42,'login':'x'})])
        else:data['data']['rateLimit']['remaining']=0
        return data
    p.gql=bad
    if mutation=='wrong-parent':
        assert s.prepare(native_pr_enabled=False,freshness=None)['count']==0
    else:
        with pytest.raises(ValueError):s.prepare(native_pr_enabled=False,freshness=None)
        assert not (s.directory/'census.json').exists()


def test_bulk_replacement_conservation_never_resets_age_or_hides_unserved():
    old=pa.Demand(7,'1'*40,'refresh','2026-11-01T00:00:00Z','abcdefabcdef')
    p=pull(7,head='2'*40);updated=replace(old,head_sha='2'*40)
    stages.conserve_age_witnesses([old],[updated],[p],[])
    for wrong in ([],[replace(updated,requested_at='2026-11-03T00:00:00Z')],[replace(updated,demand_id='123456abcdef')]):
        with pytest.raises(ValueError):stages.conserve_age_witnesses([old],wrong,[p],[])


def test_bulk_paginates_hidden_comment_suite_and_check_run_tails(monkeypatch,tmp_path):
    s,p,_=bulk_stage(monkeypatch,tmp_path,1)
    original=p.gql
    def comment(n):
        return dict(id='C'+str(n),fullDatabaseId=str(n),body='ordinary',createdAt='2026-11-03T14:00:00Z',repository={'nameWithOwner':'acme/widgets'},pullRequest={'number':1},author={'__typename':'User','login':'user','databaseId':42})
    def page(rows,total,cursor):return dict(nodes=rows,totalCount=total,pageInfo={'hasNextPage':cursor is not None,'endCursor':cursor})
    app={'databaseId':15368,'slug':'github-actions'}
    meta=dict(number=1,state='OPEN',isDraft=True,headRefOid=p.pulls[1]['head']['sha'],baseRefOid='4'*40,baseRefName='main',repository={'nameWithOwner':'acme/widgets'})
    def paged(query):
        data=original(query)
        repo=data['data']['repository']
        if 'p1:pullRequest' in query:
            repo['p1']['comments']=page([comment(n) for n in range(1,101)],101,'C100')
            repo['h1']['checkSuites']=page([dict(id='S1',repository={'nameWithOwner':'acme/widgets'},commit={'oid':p.pulls[1]['head']['sha']},app=app,checkRuns=page([dict(id='R'+str(n),name='ordinary',status='COMPLETED') for n in range(1,101)],101,'R100'))],2,'S1')
        elif 'p:pullRequest' in query:
            repo['p']={**meta,'comments':page([comment(101)],101,None)}
        elif 'h:object' in query:
            repo['h']={'checkSuites':page([dict(id='S2',repository={'nameWithOwner':'acme/widgets'},commit={'oid':p.pulls[1]['head']['sha']},app=app,checkRuns=p.connection([]))],2,None)}
        elif 'nodes(ids:' in query:
            data['data'].pop('repository')
            data['data']['nodes']=[dict(id='S1',checkRuns=page([dict(id='R101',name='ci-gate',status='COMPLETED')],101,None))]
        else:raise AssertionError(query)
        return data
    p.gql=paged
    reader=stages.BulkReader(mog,s.repo,s.read,deadline=stages.time.monotonic()+60)
    facts=reader.facts(list(p.pulls.values()))
    assert len(facts[1]['comments'])==101 and facts[1]['ci_present'] is True
    assert len(p.queries)==4


def test_bulk_expired_anchor_never_drops_original_ages(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,3);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s);i=indexer();i.start(aid,1);assert i.advance()['disposition']=='indexed'
    p.artifacts[aid]['expired']=True;s.directory=tmp_path/'next'
    with pytest.raises(ValueError):s.prepare(native_pr_enabled=False,freshness=None)
    assert not (s.directory/'census.json').exists()


@pytest.mark.parametrize('count,armed,expected',[(871,110,110),(875,875,None)])
def test_bulk_mixed_native_refresh_uses_actual_freshness_budget(monkeypatch,tmp_path,count,armed,expected):
    s,p,_=bulk_stage(monkeypatch,tmp_path,count)
    selected=(set(range(601,711)) if count==871 else set(p.pulls))
    for number,row in p.pulls.items():
        row['draft']=number<=600 if count==871 else False
        row['labels']=([{'name':'merge-on-green'}] if number in selected or count==871 and number<=4 else [])
        if number in sorted(selected)[:86]:row['labels'].append({'name':'merge-blocked'})
    if count==871:
        assert sum(row['draft'] for row in p.pulls.values())==600
        assert sum(mog.is_sweep_candidate(row) for row in p.pulls.values())==110
    original=p.gql
    def with_ci(query):
        data=original(query)
        for key,row in data['data']['repository'].items():
            if key.startswith('h'):
                row['checkSuites']=p.connection([dict(id='S'+key,repository={'nameWithOwner':'acme/widgets'},commit={'oid':row['oid']},app={'databaseId':15368,'slug':'github-actions'},checkRuns=p.connection([dict(id='R'+key,name='ci-gate',status='COMPLETED')]))])
        return data
    p.gql=with_ci
    request=p.request
    def rest(method,url,token,payload=None):
        from urllib.parse import urlparse
        path=urlparse(url).path.removeprefix('/repos/acme/widgets')
        if '/check-runs' in path:
            p.core-=1;p.calls.append((method,path,payload,p.now));head=path.split('/')[2];n=int(head,16)
            return 200,{'total_count':1,'check_runs':[dict(id=n,name='ci-gate',status='completed',conclusion='success',app={'id':15368,'slug':'github-actions'},pull_requests=[{'number':n,'head':{'sha':head},'base':{'sha':'b'*40}}])]}
        if path=='/commits/'+'4'*40:
            p.core-=1;p.calls.append((method,path,payload,p.now));return 200,{'files':[{'filename':'engine/a.py'}]}
        if path.startswith('/pulls/') and path.endswith('/files'):
            p.core-=1;p.calls.append((method,path,payload,p.now));return 200,[{'filename':'engine/a.py'}]
        return request(method,url,token,payload)
    monkeypatch.setattr(mog,'_request',rest)
    freshness=mog.ProofFreshness(s.repo,s.read,[{'workflow':'ci.yml','patterns':['engine/**']}],
        [{'sha':'4'*40,'message':'source change'},{'sha':'b'*40,'message':'old proof base'}])
    if expected is None:
        with pytest.raises(ValueError,match='incomplete demand census at budget boundary'):
            s.prepare(native_pr_enabled=False,freshness=freshness)
        assert not (s.directory/'census.json').exists()
    else:
        result=s.prepare(native_pr_enabled=False,freshness=freshness)
        assert result['count']==expected
        assert all(d['purpose']=='refresh' for d in s.load('census')['demands'])
        assert p.core>700 and p.points>900
    # One main commit classification is shared across every actual stale_for.
    assert freshness.commit_file_reads==1


def test_bulk_v2_successor_covers_expired_original_without_resetting_age(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,3)
    s.prepare(native_pr_enabled=False,freshness=None);first=p.upload(s);i=indexer();i.start(first,1);i.advance()
    original=s.load('census')['demands']
    p.pulls[3]['head']['sha']='e'*40;s.directory=tmp_path/'successor'
    s.prepare(native_pr_enabled=False,freshness=None)
    data=json.loads((s.directory/'demands/ci-proof-admission.json').read_text())
    assert data['schema']=='mastermind.ci-proof-demands.v2'
    assert data['covered_comments']==[{'pr_number':1,'through_comment_id':10000}]
    second=p.upload(s);i=indexer();i.start(second,1);assert i.advance()['disposition']=='indexed'
    p.artifacts[first]['expired']=True;s.directory=tmp_path/'after-expiry'
    assert s.prepare(native_pr_enabled=False,freshness=None)['count']==3
    current=s.load('census')['demands']
    assert [d['requested_at'] for d in current]==[d['requested_at'] for d in original]
    assert [d['demand_id'] for d in current]==[d['demand_id'] for d in original]
    assert not (s.directory/'demands-digest.json').exists()


def test_bulk_unpublished_successor_does_not_cover_original(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,2)
    s.prepare(native_pr_enabled=False,freshness=None);first=p.upload(s);i=indexer();i.start(first,1);i.advance()
    p.pulls[2]['head']['sha']='e'*40;s.directory=tmp_path/'unpublished'
    s.prepare(native_pr_enabled=False,freshness=None);p.upload(s)
    p.artifacts[first]['expired']=True;s.directory=tmp_path/'next'
    with pytest.raises(ValueError):s.prepare(native_pr_enabled=False,freshness=None)


def age_snapshot(pr=7, *, coverage=(), version=2, requested='2026-11-01T00:00:00Z',generation='a'*12):
    return pa.AgeSnapshot((pa.Demand(pr,'1'*40,'refresh',requested,generation),),coverage,version)


@pytest.mark.parametrize('coverage',[((7,20),),((8,21),),((7,10),(8,30))])
def test_bulk_age_coverage_rejects_self_future_or_cycle(coverage):
    snapshots={'new':age_snapshot(coverage=coverage),'old':age_snapshot(coverage=((7,20),))}
    with pytest.raises(ValueError,match='future'):
        pa.fold_age_snapshots([(7,20,'new'),(8,10,'old')],snapshots.__getitem__)


def test_bulk_age_uncovered_conflicting_successors_are_not_newest_wins():
    snapshots={'a':age_snapshot(coverage=((9,5),)),'b':age_snapshot(coverage=((9,5),))}
    with pytest.raises(ValueError,match='conflicting'):
        pa.fold_age_snapshots([(7,20,'a'),(8,19,'b')],snapshots.__getitem__)


def test_bulk_age_later_uncovered_v1_demand_is_preserved():
    snapshots={'current':age_snapshot(coverage=((7,10),)),
        'later':age_snapshot(8,version=1,generation='b'*12)}
    def load(ref):
        assert ref!='expired'
        return snapshots[ref]
    result=pa.fold_age_snapshots([(7,10,'expired'),(7,20,'current'),(8,21,'later')],load)
    assert {d.pr_number for d in result.demands}=={7,8}


@pytest.mark.parametrize('mutation',['repository','controller','archive-digest','foreign-reference'])
def test_bulk_age_v2_provenance_is_not_comment_authority(monkeypatch,tmp_path,mutation):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,2);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s)
    if mutation=='repository':p.artifacts[aid]['workflow_run']['repository_id']=99
    elif mutation=='controller':p.control['head_branch']='candidate'
    elif mutation=='archive-digest':p.artifacts[aid]['digest']='sha256:'+'0'*64
    else:p.artifacts[aid]['workflow_run']['head_sha']='f'*40
    with pytest.raises((ValueError,AssertionError)):indexer().start(aid,1)
    assert p.description=='a2 idle' and sum(map(len,p.comments.values()))==0


def test_bulk_snapshot_producer_catches_omitted_still_open_witness(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,2);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s);i=indexer();i.start(aid,1);i.advance()
    p.pulls[2]['head']['sha']='e'*40;s.directory=tmp_path/'omitted'
    original=pa.ordered_demands
    # Simulate a compactor omission without changing source authentication or
    # the independent original-age conservation check.
    def omit(rows):return [d for d in original(rows) if d.pr_number!=1]
    monkeypatch.setattr(pa,'ordered_demands',omit)
    with pytest.raises(ValueError):s.prepare(native_pr_enabled=False,freshness=None)
    assert not (s.directory/'demands-digest.json').exists()


@pytest.mark.parametrize('lost_delete',[False,True])
def test_bulk_closed_anchor_retirement_requires_exact_successor_and_readback(monkeypatch,tmp_path,lost_delete):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,3)
    s.prepare(native_pr_enabled=False,freshness=None);first=p.upload(s);i=indexer();i.start(first,1);i.advance()
    p.pulls[1]['state']='closed';p.pulls[3]['head']['sha']='e'*40;s.directory=tmp_path/'next'
    s.prepare(native_pr_enabled=False,freshness=None);second=p.upload(s);i=indexer();i.start(second,2);i.advance()
    ref,_=i.authenticate(stages.IndexState(second,2))
    request=p.request
    def remove(method,url,token,payload=None):
        if method=='DELETE':
            p.calls.append((method,url,payload,p.now));p.core-=1;p.labels[1]=[]
            if lost_delete:raise TimeoutError('response lost')
            return 204,None
        return request(method,url,token,payload)
    monkeypatch.setattr(mog,'_request',remove)
    result=i.retire_covered_anchor(ref)
    if lost_delete:
        assert result['disposition']=='unknown'
        assert stages.IndexState.parse(p.description).intent==3
        assert s.complete()['disposition']=='held'
        assert indexer().advance()['disposition']=='indexed'
    else:assert result['disposition']=='indexed'
    assert p.description=='a2 idle' and p.labels[1]==[] and p.labels[2]
    assert len([c for c in p.calls if c[0]=='DELETE'])==1
    p.artifacts[first]['expired']=True;s.directory=tmp_path/'after-retirement'
    assert s.prepare(native_pr_enabled=False,freshness=None)['count']==2


def test_bulk_compaction_never_waives_an_uncovered_original_admission(monkeypatch,tmp_path):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,2);s.prepare(native_pr_enabled=False,freshness=None)
    aid=p.upload(s);i=indexer();i.start(aid,1);i.advance()
    # A valid age successor cannot cover the admission namespace, even if an
    # original admission comment's numeric ID is beneath its age cutoff.
    ref,_=i.authenticate(stages.IndexState(aid,1))
    p.comments[1].append(dict(id=9999,body=mog.ADMISSION_COMMENT_PREFIX+json.dumps(ref),user={'id':41898282,'login':'github-actions[bot]','type':'Bot'}))
    snapshot=pa.AgeSnapshot(tuple(pa.Demand(**d) for d in s.load('census')['demands']),((1,10000),),2)
    with pytest.raises(ValueError):
        mog.pr_admission_history(s.repo,s.read,1,p.comments[1],repository_id=17,protected_controller_sha='4'*40,age_snapshot=snapshot)


def test_bulk_blob_identity_is_recomputed_from_exact_text(monkeypatch,tmp_path):
    s,p,_=bulk_stage(monkeypatch,tmp_path,1);original=p.gql
    def substituted(query):
        data=original(query);blob=data['data']['repository']['p1']['potentialMergeCommit']['file']['object']
        blob['text']=blob['text'].replace('jobs: {}','jobs: []')
        return data
    p.gql=substituted
    with pytest.raises(ValueError,match='workflow bytes incomplete'):
        s.prepare(native_pr_enabled=False,freshness=None)


def test_bulk_v1_rows_remain_changed_rows_not_snapshot_coverage():
    older=age_snapshot(7,version=1)
    later=age_snapshot(8,version=1,generation='b'*12)
    result=pa.fold_age_snapshots([(7,10,'old'),(8,20,'new')],{'old':older,'new':later}.__getitem__)
    assert result.covered_comments==() and {d.pr_number for d in result.demands}=={7,8}


def test_bulk_rejects_foreign_suite_even_with_actions_name(monkeypatch,tmp_path):
    s,p,_=bulk_stage(monkeypatch,tmp_path,1);original=p.gql
    def foreign(query):
        data=original(query)
        data['data']['repository']['h1']['checkSuites']=p.connection([dict(id='S',repository={'nameWithOwner':'foreign/repo'},commit={'oid':p.pulls[1]['head']['sha']},app={'databaseId':15368,'slug':'github-actions'},checkRuns=p.connection([dict(id='R',name='ci-gate',status='COMPLETED')]))])
        return data
    p.gql=foreign
    with pytest.raises(ValueError,match='foreign check suite'):s.prepare(native_pr_enabled=False,freshness=None)


@pytest.mark.parametrize('version,coverage,valid',[(1,None,True),(1,[],False),(2,None,False),(2,[{'pr_number':n,'through_comment_id':n} for n in range(1,1002)],False)])
def test_bulk_age_envelope_preserves_v1_and_existing_bound(monkeypatch,tmp_path,version,coverage,valid):
    s,p,indexer=bulk_stage(monkeypatch,tmp_path,1);s.prepare(native_pr_enabled=False,freshness=None)
    file=s.directory/'demands/ci-proof-admission.json';data=json.loads(file.read_text());data['schema']=f'mastermind.ci-proof-demands.v{version}'
    if coverage is None:data.pop('covered_comments',None)
    else:data['covered_comments']=coverage
    file.write_text(json.dumps(data))
    artifact=p.upload(s)
    if valid:assert indexer().start(artifact,1)['disposition']=='indexing'
    else:
        with pytest.raises(ValueError):indexer().start(artifact,1)
        assert p.description=='a2 idle'


def test_bulk_authoritative_graphql_quota_header_cannot_be_overridden(monkeypatch,tmp_path):
    s,p,_=bulk_stage(monkeypatch,tmp_path,1)
    monkeypatch.setattr(mog,'last_response_headers',lambda:{'x-ratelimit-resource':'graphql','x-ratelimit-remaining':'0','x-ratelimit-limit':'1000'})
    with pytest.raises(ValueError,match='budget/deadline'):s.prepare(native_pr_enabled=False,freshness=None)
    assert not (s.directory/'census.json').exists()


@pytest.mark.parametrize('failure', ['age_inventory', 'checkpoint'])
def test_post_reservation_read_failure_retains_original_custody(tmp_path,monkeypatch,capsys,backend,failure):
    s=stage(tmp_path/'original',monkeypatch)
    s.save('census',dict(context=CTX,demands=[asdict(demand()),
        asdict(demand(8,'b'*12,'authored','2026-10-02T00:00:00Z'))]))
    original_request=mog._request
    def request(method,url,token,payload=None):
        if failure=='age_inventory' and '/issues?' in url:
            backend['calls'].append((method,url,payload))
            return 503,{}
        return original_request(method,url,token,payload)
    monkeypatch.setattr(mog,'_request',request)
    def checkpoint(*a,**k):
        raise ValueError('original checkpoint history unavailable')
    monkeypatch.setattr(mog,'prepare_shared_checkpoint',checkpoint)
    with pytest.raises(ValueError,match='age inventory incomplete|checkpoint history unavailable'):
        s.reserve()
    assert backend['register']=='a2 p=7 g=aaaaaaaaaaaa s=prepared'
    assert s.load('reservation')['disposition']=='prepared'
    receipt=json.loads((s.directory/'prepared/ci-proof-admission.json').read_text())
    assert receipt['admission']['run_id'] is None
    assert receipt['admission']['settled'] is False
    assert not (s.directory/'checkpoint-digest.json').exists()
    assert not any(method in {'POST','DELETE'} for method,_,_ in backend['calls'])
    assert not any('/pulls/8' in url for _,url,_ in backend['calls'])
    before=list(backend['calls'])
    later=stage(tmp_path/'later',monkeypatch)
    later.save('census',dict(context=CTX,demands=[asdict(demand())]))
    assert later.reserve()['disposition']=='held'
    assert backend['register']=='a2 p=7 g=aaaaaaaaaaaa s=prepared'
    assert all(method=='GET' for method,_,_ in backend['calls'][len(before):])
    assert not (later.directory/'prepared').exists()
