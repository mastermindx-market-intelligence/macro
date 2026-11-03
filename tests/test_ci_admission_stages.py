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
    monkeypatch.setattr(s,'history',lambda p:([],[]))
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
    monkeypatch.setattr(controller,'history',lambda p:([],[old]))
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
    return s,server


def test_real_controller_upload_dispatch_binding_chain_with_seven_active(monkeypatch,tmp_path):
    s,server=original_server(monkeypatch,tmp_path)
    for n in range(201,208):server.runs[n]=dict(id=n,run_attempt=1,status='queued',event='pull_request')
    assert s.prepare(native_pr_enabled=True,freshness=None)['count']==1
    demands=server.upload(s,'demands','ci-proof-demands-70-1')
    result=s.reserve(demands);assert result['prepared'] is True
    generation=result['generation']
    prepared=server.upload(s,'prepared',f'ci-proof-admission-70-1-{generation}-prepared')
    checkpoint=server.upload(s,'checkpoint','ci-proof-checkpoint-70-1-7')
    assert s.dispatch(prepared,checkpoint)==dict(bound=True,generation=generation)
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
    monkeypatch.setattr(controller,'history',lambda p:stages.Stages.history(controller,p))
    monkeypatch.setattr(mog,'_request',lambda *a:pytest.fail('outsider requires no artifact/permission GET'))
    assert controller.prepare(native_pr_enabled=False,freshness=None)['count']==1



@pytest.mark.parametrize('author', [None,{'id':41898282,'login':'github-actions[bot]','type':'Bot'}])
def test_genuine_or_unknown_index_provenance_never_becomes_empty(controller,monkeypatch,author):
    comment={'id':71,'user':author,'body':mog.DEMAND_COMMENT_PREFIX+'{'}
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[comment])
    monkeypatch.setattr(controller,'history',lambda p:stages.Stages.history(controller,p))
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
