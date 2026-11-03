"""Incumbent controller custody, including closed PR and label-indexing gaps."""
import pytest
from scripts import merge_on_green as mog


@pytest.fixture(autouse=True)
def no_http(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError('unstubbed HTTP')
    monkeypatch.setattr(mog, '_request', refuse)


def issue(n, state='open', labeled=True):
    return {'number':n,'state':state,'pull_request':{},
            'labels':[{'name':mog.REFRESH_LEASE_LABEL}] if labeled else []}


def test_v2_discovery_keeps_closed_disarmed_and_multiple_prs(monkeypatch):
    calls=[]
    def request(method,url,token,*args):
        calls.append(url)
        if '/labels/' in url:
            return 200, {'description':'a2 idle'}
        assert 'state=all' in url and 'labels=merge-refresh-in-flight' in url
        return 200,[issue(1),issue(2,'closed')]
    monkeypatch.setattr(mog,'_request',request)
    inventory=mog.shared_admission_inventory('acme/widgets','read')
    assert inventory.mode == 'shared'
    assert inventory.complete is True
    assert [i['number'] for i in inventory.issues] == [1,2]
    assert inventory.launch is None


def test_v2_launch_pointer_recovers_missing_label_index_without_releasing(monkeypatch):
    def request(method,url,token,*args):
        if '/labels/' in url:
            return 200, {'description':'a2 p=7 g=aaaaaaaaaaaa s=prepared'}
        if '/issues?' in url:
            return 200,[]
        assert url.endswith('/issues/7')
        return 200,issue(7,'closed',labeled=False)
    monkeypatch.setattr(mog,'_request',request)
    inventory=mog.shared_admission_inventory('acme/widgets','read')
    assert inventory.complete
    assert inventory.launch == (7,'a'*12)
    assert inventory.issues[0]['number'] == 7


def test_live_legacy_generation_is_not_reinterpreted_or_cleaned(monkeypatch):
    calls=[]
    def request(method,url,token,*args):
        calls.append((method,url))
        return 200,{'description':mog.refresh_lease_record(7,'a'*40)}
    monkeypatch.setattr(mog,'_request',request)
    inventory=mog.shared_admission_inventory('acme/widgets','read')
    assert inventory.mode == 'legacy'
    assert not inventory.complete
    assert len(calls)==1 and calls[0][0]=='GET'


@pytest.mark.parametrize('description', ['a2 p=7 g=short', 'a2 idle extra',
    'a2 p=0 g=aaaaaaaaaaaa', 'a2 p=7 g=aaaaaaaaaaaa p=8'])
def test_bad_register_never_becomes_empty_inventory(monkeypatch,description):
    monkeypatch.setattr(mog,'_request',lambda *a:(200,{'description':description}))
    assert not mog.shared_admission_inventory('acme/widgets','read').complete


def test_missing_direct_launch_issue_preserves_unknown_capacity(monkeypatch):
    def request(method,url,token,*args):
        if '/labels/' in url:
            return 200,{'description':'a2 p=7 g=aaaaaaaaaaaa s=prepared'}
        if '/issues?' in url:
            return 200,[]
        return 404,{}
    monkeypatch.setattr(mog,'_request',request)
    inventory=mog.shared_admission_inventory('acme/widgets','read')
    assert not inventory.complete
    assert inventory.launch == (7,'a'*12)


def test_reference_loader_extracts_only_actual_server_bound_archive(monkeypatch):
    import hashlib,io,json,zipfile
    from dataclasses import asdict
    from scripts.ci_proof_admission import Admission
    a=Admission('a'*12,7,'1'*40,'2'*40,'3'*40,'4'*40)
    raw=json.dumps({'schema':'mastermind.ci-proof-admission.v1','repository_id':17,
                    'controller_run_id':70,'controller_run_attempt':1,
                    'admission':asdict(a)}).encode()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr('ci-proof-admission.json',raw)
    archive=stream.getvalue()
    reference={'artifact_id':80,'controller_run_id':70,'controller_attempt':1,
               'controller_sha':'c'*40,'payload_sha256':hashlib.sha256(raw).hexdigest()}
    def request(method,url,token,*args):
        assert method=='GET' and token=='read'
        if url.endswith('/actions/artifacts/80'):
            return 200,{'id':80,'name':'ci-proof-admission-70-1-aaaaaaaaaaaa-prepared','expired':False,
                'digest':'sha256:'+hashlib.sha256(archive).hexdigest(),
                'workflow_run':{'id':70,'repository_id':17,'head_sha':'c'*40}}
        assert url.endswith('/actions/runs/70/attempts/1')
        return 200,{'id':70,'run_attempt':1,'repository':{'id':17},
            'path':'.github/workflows/merge-on-green.yml','head_branch':'main',
            'head_sha':'c'*40,'event':'schedule'}
    def download(url,token):
        assert url=='https://api.github.com/repos/acme/widgets/actions/artifacts/80/zip'
        assert token=='read'
        return archive
    monkeypatch.setattr(mog,'_request',request)
    monkeypatch.setattr(mog,'_download_semantic_artifact',download)
    assert mog.authenticated_admission_from_ref('acme/widgets','read',reference,
        repository_id=17,protected_controller_sha='c'*40)==a
    with pytest.raises(ValueError):
        mog.authenticated_admission_from_ref('acme/widgets','read',{
            **reference,'payload':{'pr_number':8}},repository_id=17,protected_controller_sha='c'*40)
    with pytest.raises(ValueError):
        mog.authenticated_admission_from_ref('acme/widgets','read',reference,
            repository_id=17,protected_controller_sha='d'*40)


def dispatch_harness(monkeypatch, outcome=(200, {'workflow_run_id':99}), lose_start=False):
    from scripts.ci_proof_admission import Admission
    a=Admission('a'*12,7,'1'*40,'2'*40,'3'*40,'4'*40)
    state={'description':'a2 p=7 g=aaaaaaaaaaaa s=prepared','posts':[],'patches':0}
    monkeypatch.setattr(mog,'serialized_refresh_authority',lambda *a:True)
    # These historical cases exercise original dispatch custody, not bootstrap.
    monkeypatch.setattr(mog,'installed_admitted_dispatch_ready',lambda *a:True, raising=False)
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *a,**k:a_record)
    a_record=a
    monkeypatch.setattr(mog,"shared_proof_workload",lambda *a,**k:mog.SharedProofWorkload(True,(),(a_record,)))
    def request(method,url,token,payload=None):
        if method=='GET' and url.endswith('/actions/runs/70'):
            return 200,{'id':70,'run_attempt':1,'head_sha':'4'*40,'repository':{'id':17}}
        if method=='GET' and '/labels/' in url:
            return 200,{'description':state['description']}
        if method=='GET' and '/pulls/' in url:
            return 200,{'number':7,'state':'open','head':{'sha':'1'*40},
                        'base':{'sha':'2'*40,'ref':'main'},'merge_commit_sha':'3'*40}
        if method=='PATCH' and '/labels/' in url:
            state['patches']+=1
            state['description']=payload['description']
            if lose_start:raise OSError('lost start write response')
            return 200,{'description':state['description']}
        if method=='POST' and url.endswith('/actions/workflows/ci.yml/dispatches'):
            state['posts'].append(payload)
            if isinstance(outcome,Exception):raise outcome
            return outcome
        raise AssertionError((method,url))
    monkeypatch.setattr(mog,'_request',request)
    reference={'controller_run_id':70,'controller_attempt':1,'artifact_id':80,'payload_sha256':'d'*64}
    kwargs=dict(repository_id=17,protected_controller_sha='4'*40,
                current_run_id='70',current_run_attempt=1)
    return state,reference,kwargs


def test_one_shot_dispatch_binds_exact_returned_run_without_release(monkeypatch):
    state,reference,kwargs=dispatch_harness(monkeypatch)
    result=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert result.disposition=='bound'
    assert result.admission.run_id==99
    assert state['description']=='a2 p=7 g=aaaaaaaaaaaa s=started'
    assert len(state['posts'])==1
    body=state['posts'][0]
    assert body['return_run_details'] is True
    assert body['ref']=='main'
    assert body['inputs']['subject_head_sha']=='1'*40
    assert body['inputs']['tested_merge_sha']=='3'*40
    assert body['inputs']['proof_role']=='pr_head'
    again=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert again.disposition=='held'
    assert len(state['posts'])==1


@pytest.mark.parametrize('outcome', [OSError('lost response'),(204,None),(503,{}),(200,{'workflow_run_id':True})])
def test_ambiguous_dispatch_keeps_same_generation_and_never_retries(monkeypatch,outcome):
    state,reference,kwargs=dispatch_harness(monkeypatch,outcome=outcome)
    first=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert first.disposition=='unknown'
    assert first.admission.run_id is None
    again=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert again.disposition=='held'
    assert len(state['posts'])==1


def test_unknown_start_write_never_reaches_dispatch(monkeypatch):
    state,reference,kwargs=dispatch_harness(monkeypatch,lose_start=True)
    result=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert result.disposition=='unknown'
    assert state['posts']==[]


def test_another_controller_attempt_cannot_replay_prepared_receipt(monkeypatch):
    state,reference,kwargs=dispatch_harness(monkeypatch)
    kwargs['current_run_attempt']=2
    result=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert result.disposition=='held'
    assert state['posts']==[] and state['patches']==0


@pytest.mark.parametrize('changed', [
    {'run_attempt':2}, {'head_sha':'e'*40}, {'repository':{'id':18}}, {'id':True},
])
def test_dispatch_rejects_mismatched_actual_controller_before_start(monkeypatch, changed):
    state,reference,kwargs=dispatch_harness(monkeypatch)
    original=mog._request
    def mismatched(method,url,token,payload=None):
        status,value=original(method,url,token,payload)
        if url.endswith('/actions/runs/70'):
            value={**value,**changed}
        return status,value
    monkeypatch.setattr(mog,'_request',mismatched)
    result=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert result.disposition=='held'
    assert state['posts']==[] and state['patches']==0


def test_dispatch_rechecks_real_workload_after_preparation(monkeypatch):
    state,reference,kwargs=dispatch_harness(monkeypatch)
    from scripts.ci_proof_admission import Run,Admission
    reserved=Admission('a'*12,7,'1'*40,'2'*40,'3'*40,'4'*40)
    monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(
        True,tuple(Run(i,1,'in_progress','pr_head') for i in range(1,9)),(reserved,)))
    result=mog.dispatch_admitted_pr_proof('acme/widgets','read','write',reference,**kwargs)
    assert result.disposition=='held'
    assert not state['posts'] and not state['patches']


def test_missing_closed_pr_receipt_cannot_free_capacity(monkeypatch):
    monkeypatch.setattr(mog,'shared_admission_inventory',lambda *a:mog.SharedAdmissionInventory(
        'shared',True,(issue(7,'closed'),)))
    monkeypatch.setattr(mog,'indexed_active_ci_runs',lambda *a:[])
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[])
    assert not mog.shared_proof_workload('acme/widgets','read',repository_id=17,
                                        protected_controller_sha='c'*40).complete


def custody_harness(monkeypatch, *, fail_at=None):
    from scripts.ci_proof_admission import Admission, Demand
    a=Admission('a'*12,7,'1'*40,'4'*40,'3'*40,'4'*40)
    state={'description':'a2 idle','writes':[], 'labels':[], 'comments':[], 'failed':False}
    monkeypatch.setattr(mog,'serialized_refresh_authority',lambda *a:True)
    # Bootstrap is independently discriminated below; retain the custody cases.
    monkeypatch.setattr(mog,'installed_admitted_dispatch_ready',lambda *a:True, raising=False)
    monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(True,(),()))
    def request(method,url,token,payload=None):
        if method!='GET':
            state['writes'].append((method,url,payload))
            if fail_at==len(state['writes']):
                state['failed']=True
                raise OSError('lost original write response')
        if url.endswith('/actions/runs/70'):
            return 200,{'id':70,'run_attempt':1,'status':'in_progress','head_sha':'4'*40,
                'repository':{'id':17},'head_branch':'main','event':'schedule',
                'path':'.github/workflows/merge-on-green.yml'}
        if '/labels/' in url:
            if method=='PATCH':state['description']=payload['description']
            return 200,{'description':state['description']}
        if '/pulls/' in url:
            return 200,{'number':7,'state':'open','draft':True,'head':{'sha':'1'*40},
                        'base':{'sha':'4'*40,'ref':'main','repo':{'id':17}},
                        'merge_commit_sha':'3'*40,'mergeable':True}
        if '/git/commits/' in url:
            return 200,{'sha':'3'*40,'parents':[{'sha':'4'*40},{'sha':'1'*40}]}
        if url.endswith('/branches/main'):
            return 200,{'commit':{'sha':'4'*40}}
        if url.endswith('/comments') and method=='POST':
            c={'id':100+len(state['comments']), 'body':payload['body'], 'user':{'id':41898282,'login':'github-actions[bot]','type':'Bot'}}
            state['comments'].append(c)
            return 201,c
        if '/issues/comments/' in url:
            return 200,state['comments'][-1]
        if url.endswith('/labels'):
            if method=='POST':state['labels']=[{'name':n} for n in payload['labels']]
            return 200,state['labels']
        if '/actions/runs/99' in url:
            return 200,{'id':99,'run_attempt':1,'path':'.github/workflows/ci.yml@main',
                'event':'workflow_dispatch','head_branch':'main','head_sha':'4'*40,
                'repository':{'id':17},'status':'queued'}
        raise AssertionError((method,url))
    monkeypatch.setattr(mog,'_request',request)
    kw=dict(repository_id=17,protected_controller_sha='4'*40,current_run_id='70',current_run_attempt=1)
    d=Demand(7,'1'*40,'authored','2026-11-03T00:00:00Z','a'*12)
    return state,a,d,kw


def test_preparation_reserves_before_artifact_and_draft_is_not_release(monkeypatch):
    state,a,d,kw=custody_harness(monkeypatch)
    result=mog.reserve_shared_admission('acme/widgets','read','write',d,**kw)
    assert result.disposition=='prepared' and result.admission==a
    assert state['description']=='a2 p=7 g=aaaaaaaaaaaa s=prepared'
    assert len(state['writes'])==1
    assert '/labels/' in state['writes'][0][1]
    # No branch PUT, dispatch, check, label arm or release occurs in preparation.
    assert all('/update-branch' not in url and '/dispatches' not in url for _,url,_ in state['writes'])


@pytest.mark.parametrize('kind',['saturated','unknown','occupied','bad_merge'])
def test_preparation_has_no_effect_without_exact_capacity_and_merge(monkeypatch,kind):
    from scripts.ci_proof_admission import Run
    state,a,d,kw=custody_harness(monkeypatch)
    if kind=='saturated':
        monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(True,
            tuple(Run(n,1,'in_progress','pr_head') for n in range(1,9)),()))
    elif kind=='unknown':
        monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(False))
    elif kind=='occupied':state['description']='a2 p=8 g=bbbbbbbbbbbb s=started'
    else:
        original=mog._request
        def wrong(method,url,token,payload=None):
            if '/git/commits/' in url:return 200,{'sha':'3'*40,'parents':[{'sha':'1'*40},{'sha':'4'*40}]}
            return original(method,url,token,payload)
        monkeypatch.setattr(mog,'_request',wrong)
    result=mog.reserve_shared_admission('acme/widgets','read','write',d,**kw)
    assert result.disposition=='held'
    assert state['writes']==[]


def test_lost_reservation_response_cannot_dispatch_or_release(monkeypatch):
    state,a,d,kw=custody_harness(monkeypatch,fail_at=1)
    result=mog.reserve_shared_admission('acme/widgets','read','write',d,**kw)
    assert result.disposition=='unknown'
    assert len(state['writes'])==1


def bound_reference():
    return {'controller_run_id':70,'controller_attempt':1,'controller_sha':'4'*40,
            'artifact_id':81,'payload_sha256':'b'*64}


def test_prepared_index_is_published_before_dispatch_without_releasing_pointer(monkeypatch):
    state,a,d,kw=custody_harness(monkeypatch)
    state['description']='a2 p=7 g=aaaaaaaaaaaa s=prepared'
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *args,**k:a)
    result=mog.publish_prepared_shared_admission('acme/widgets','read','write',bound_reference(),**kw)
    assert result.disposition=='indexed' and result.admission==a
    assert state['description']=='a2 p=7 g=aaaaaaaaaaaa s=prepared'
    assert [method for method,_,_ in state['writes']]==['POST','POST']
    assert state['writes'][0][1].endswith('/comments')
    assert state['writes'][1][1].endswith('/labels')


@pytest.mark.parametrize('fail_at',[1,2])
def test_prepared_index_unknown_retains_reservation_without_dispatch(monkeypatch,fail_at):
    state,a,d,kw=custody_harness(monkeypatch,fail_at=fail_at)
    state['description']='a2 p=7 g=aaaaaaaaaaaa s=prepared'
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *args,**k:a)
    result=mog.publish_prepared_shared_admission('acme/widgets','read','write',bound_reference(),**kw)
    assert result.disposition=='unknown'
    assert len(state['writes'])==fail_at
    assert state['description'].endswith('s=prepared')
    assert all('/dispatches' not in url for _,url,_ in state['writes'])


def test_bound_publication_is_indexed_and_associated_before_pointer_release(monkeypatch):
    from dataclasses import replace
    state,a,d,kw=custody_harness(monkeypatch)
    state['description']='a2 p=7 g=aaaaaaaaaaaa s=started'
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *a,**k:replace(a_record,run_id=99))
    a_record=a
    result=mog.finalize_shared_admission('acme/widgets','read','write',bound_reference(),**kw)
    assert result.disposition=='finalized'
    assert state['description']=='a2 idle'
    writes=state['writes']
    assert writes[0][1].endswith('/comments')
    assert writes[1][1].endswith('/labels')
    assert writes[2][0]=='PATCH' and '/labels/' in writes[2][1]
    assert mog.REFRESH_LEASE_LABEL in [l['name'] for l in state['labels']]
    assert state['comments'][0]['body'].startswith(mog.ADMISSION_COMMENT_PREFIX)


@pytest.mark.parametrize('fail_at',[1,2,3])
def test_finalization_unknown_stops_at_original_effect(monkeypatch,fail_at):
    from dataclasses import replace
    state,a,d,kw=custody_harness(monkeypatch,fail_at=fail_at)
    state['description']='a2 p=7 g=aaaaaaaaaaaa s=started'
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *a,**k:replace(a_record,run_id=99))
    a_record=a
    result=mog.finalize_shared_admission('acme/widgets','read','write',bound_reference(),**kw)
    assert result.disposition=='unknown'
    assert len(state['writes'])==fail_at
    assert state['description']!='a2 idle'


def test_prepared_receipt_cannot_release_started_pointer(monkeypatch):
    state,a,d,kw=custody_harness(monkeypatch)
    state['description']='a2 p=7 g=aaaaaaaaaaaa s=started'
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *args,**k:a)
    result=mog.finalize_shared_admission('acme/widgets','read','write',bound_reference(),**kw)
    assert result.disposition=='held' and not state['writes']


def history_comment(n, prefix, artifact):
    import json
    return {'id':n,'user':{'id':41898282,'login':'github-actions[bot]','type':'Bot'},
        'performed_via_github_app':{'id':15368},'body':prefix+json.dumps({'artifact_id':artifact,'controller_run_id':70,
        'controller_attempt':1,'controller_sha':'4'*40,'payload_sha256':'b'*64})}


def test_pr_history_covered_by_authenticated_checkpoint_does_not_reopen_expired_refs(monkeypatch):
    from scripts import ci_proof_admission as pa
    a=pa.Admission('a'*12,7,'1'*40,'2'*40,'3'*40,'4'*40)
    checkpoint=pa.Checkpoint(7,19,(a,),(),())
    comments=[history_comment(10,mog.ADMISSION_COMMENT_PREFIX,10),
        history_comment(15,mog.CHECKPOINT_COMMENT_PREFIX,15),
        history_comment(20,mog.CHECKPOINT_COMMENT_PREFIX,20),
        history_comment(21,mog.ADMISSION_COMMENT_PREFIX,21)]
    calls=[]
    def cp(*args,**kw):
        calls.append(args[2]['artifact_id']);assert args[2]['artifact_id']==20
        return checkpoint
    def receipt(*args,**kw):
        calls.append(args[2]['artifact_id']);assert args[2]['artifact_id']==21
        return pa.bind_run(a,99,1)
    monkeypatch.setattr(mog,'authenticated_checkpoint_from_ref',cp)
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',receipt)
    records,demands=mog.pr_admission_history('acme/widgets','read',7,comments,
        repository_id=17,protected_controller_sha='4'*40)
    assert records==[pa.bind_run(a,99,1)] and demands==[]
    assert calls==[20,21]


def test_unreadable_new_checkpoint_does_not_fall_back_to_old_history(monkeypatch):
    comments=[history_comment(20,mog.CHECKPOINT_COMMENT_PREFIX,20)]
    def refuse(*a,**k):raise ValueError('expired')
    monkeypatch.setattr(mog,'authenticated_checkpoint_from_ref',refuse)
    with pytest.raises(ValueError):
        mog.pr_admission_history('acme/widgets','read',7,comments,
            repository_id=17,protected_controller_sha='4'*40)


def test_checkpoint_cannot_cover_its_own_or_future_comment(monkeypatch):
    from scripts import ci_proof_admission as pa
    comments=[history_comment(20,mog.CHECKPOINT_COMMENT_PREFIX,20)]
    monkeypatch.setattr(mog,'authenticated_checkpoint_from_ref',lambda *a,**k:pa.Checkpoint(7,20,(),(),()))
    with pytest.raises(ValueError):
        mog.pr_admission_history('acme/widgets','read',7,comments,
            repository_id=17,protected_controller_sha='4'*40)


@pytest.mark.parametrize('missing',['none','comments','history','active','run'])
def test_checkpoint_producer_preserves_unknown_from_complete_original_history(monkeypatch,missing):
    from dataclasses import replace
    from scripts import ci_proof_admission as pa
    state,a,d,kw=custody_harness(monkeypatch)
    bound=replace(a,generation='b'*12,run_id=99)
    # Closed/superseded source is immaterial: these two original effects remain.
    comments=[{'id':20,'body':'original index'}]
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *args,**kwargs:None if missing=='comments' else comments)
    def history(*args,**kwargs):
        if missing=='history':raise ValueError('expired uncovered original')
        assert args[2]==7 and args[3] is comments
        return [a,bound],[d]
    monkeypatch.setattr(mog,'pr_admission_history',history)
    monkeypatch.setattr(mog,'indexed_active_ci_runs',lambda *args:None if missing=='active' else [])
    original=mog._request
    def observed(method,url,token,payload=None):
        status,value=original(method,url,token,payload)
        if url.endswith('/actions/runs/99'):
            if missing=='run':return 404,{}
            value={**value,'status':'completed'}
        return status,value
    monkeypatch.setattr(mog,'_request',observed)
    if missing!='none':
        with pytest.raises(ValueError):mog.prepare_shared_checkpoint('acme/widgets','read',7,**kw)
    else:
        checkpoint=mog.prepare_shared_checkpoint('acme/widgets','read',7,**kw)
        assert checkpoint.covered_through_comment_id==20
        assert checkpoint.admissions==(a,)  # unbound UNKNOWN cannot disappear
        assert checkpoint.settled==(replace(bound,settled=True),)
        assert checkpoint.demands==()  # its exact generation already reserved
    assert state['writes']==[]


def test_checkpoint_producer_checks_conservation_before_returning_replacement(monkeypatch):
    from dataclasses import replace
    from scripts import ci_proof_admission as pa
    state,a,d,kw=custody_harness(monkeypatch)
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *args,**kwargs:[{'id':20,'body':'index'}])
    monkeypatch.setattr(mog,'pr_admission_history',lambda *args,**kwargs:([a],[]))
    monkeypatch.setattr(mog,'indexed_active_ci_runs',lambda *args:[pa.Run(200,1,'in_progress','pr_head')])
    compact=pa.compact_pr_records
    def corrupt(*args,**kwargs):
        cp=compact(*args,**kwargs)
        return replace(cp,admissions=()) if args[4] else cp
    monkeypatch.setattr(pa,'compact_pr_records',corrupt)
    with pytest.raises(ValueError,match='outstanding admission omitted'):
        mog.prepare_shared_checkpoint('acme/widgets','read',7,**kw)
    assert state['writes']==[]


def test_admission_comment_read_does_not_filter_malformed_original_rows(monkeypatch):
    monkeypatch.setattr(mog,'_request',lambda *args:(200,[None,{'id':20,'body':'ordinary'}]))
    assert mog.fetch_issue_comments('acme/widgets',7,'read',strict=True) is None


def test_open_census_keeps_draft_and_unarmed_source_demands(monkeypatch):
    pulls=[{'number':1,'draft':True,'labels':[]},{'number':2,'draft':False,'labels':[{'name':mog.MERGE_ON_GREEN_LABEL}]}]
    monkeypatch.setattr(mog,'_request',lambda *args:(200,pulls))
    assert mog.open_pulls('acme/widgets','read')==pulls
    assert mog.labeled_pulls('acme/widgets','read')==pulls[1:]


@pytest.mark.parametrize('rows',[[None,{'number':1}],[{'number':1},{'number':1}],[{'number':True}]])
def test_open_census_refuses_malformed_or_duplicate_rows(monkeypatch,rows):
    monkeypatch.setattr(mog,'_request',lambda *args:(200,rows))
    with pytest.raises(RuntimeError):mog.open_pulls('acme/widgets','read')


def test_open_census_cap_is_not_partial_eligibility(monkeypatch):
    monkeypatch.setattr(mog,'OPEN_PULL_PAGE_CAP',1)
    monkeypatch.setattr(mog,'_request',lambda *args:(200,[{'number':n} for n in range(1,101)]))
    with pytest.raises(RuntimeError,match='truncated'):mog.open_pulls('acme/widgets','read')


def test_original_index_acknowledgement_requires_server_bot_provenance(monkeypatch):
    from types import SimpleNamespace
    writes=[]
    def api(method,url,token,payload=None):
        if method=='POST':writes.append(payload)
        return (201 if method=='POST' else 200),dict(id=8,body=writes[0]['body'],user=dict(id=42,login='pat-owner',type='User'))
    monkeypatch.setattr(mog,'_request',api)
    assert mog._publish_admission_reference('acme/widgets','read','write',SimpleNamespace(pr_number=7),{}) is False
    assert len(writes)==1


def test_contradictory_immutable_bot_identity_is_unknown():
    with pytest.raises(ValueError):
        mog.admission_index_writer({'user':{'id':41898282,'login':'github-actions[bot]','type':'User'}})


def bridge_documents():
    """Actual staged source plus the exact caller wiring owed by the bridge."""
    import yaml
    ci = yaml.safe_load((mog._ROOT / '.github/workflows/ci.yml').read_text())
    executor = yaml.safe_load((mog._ROOT / '.github/workflows/trusted-ci-executor.yml').read_text())
    ci['jobs']['trusted-ci']['with'] = {
        'admitted_merge': "${{ needs.ci-plan.outputs.admission_generation != '' && needs.ci-plan.outputs.tested_tree_sha || '' }}",
        'admitted_head': "${{ needs.ci-plan.outputs.admission_generation != '' && needs.ci-plan.outputs.subject_head_sha || '' }}",
        'admitted_base': "${{ needs.ci-plan.outputs.admission_generation != '' && needs.ci-plan.outputs.tested_base_sha || '' }}",
        'admitted_pr': '${{ needs.ci-plan.outputs.admitted_pr }}',
        'admitted_repository_id': '${{ needs.ci-plan.outputs.admitted_repository_id }}',
        'admission_generation': '${{ needs.ci-plan.outputs.admission_generation }}',
    }
    return ci, executor


def test_bootstrap_bridge_ready_but_foundation_and_old_callee_not_ready():
    import copy
    ci, executor = bridge_documents()
    repo = 'mastermindx-market-intelligence/macro'
    assert mog.admitted_dispatch_source_ready(repo, ci, executor)
    foundation = copy.deepcopy(ci)
    foundation['jobs']['trusted-ci'].pop('with')
    assert not mog.admitted_dispatch_source_ready(repo, foundation, executor)
    old_executor = copy.deepcopy(executor)
    old_executor.get('on', old_executor.get(True))['workflow_call']['inputs'] = {}
    assert not mog.admitted_dispatch_source_ready(repo, ci, old_executor)
    ci.get('on', ci.get(True)).pop('pull_request')
    assert mog.admitted_dispatch_source_ready(repo, ci, executor)  # cutover keeps capability


@pytest.mark.parametrize('mutation', [
    'raw-head', 'empty-generation', 'missing-field', 'extra-field', 'candidate-callee',
    'wrong-plan-dependency', 'failed-resolver-allowed', 'raw-plan-output',
    'raw-identity-input', 'raw-resolver-output', 'candidate-checkout', 'candidate-resolver',
    'missing-dispatch-input', 'required-callee-input', 'nonempty-callee-default', 'wrong-callee-type',
    'extra-required-callee-input', 'extra-required-dispatch-input',
])
def test_bootstrap_rejects_unbound_or_incompatible_source(mutation):
    ci, executor = bridge_documents()
    jobs = ci['jobs']
    call = jobs['trusted-ci']
    callee = executor.get('on', executor.get(True))['workflow_call']['inputs']
    if mutation == 'raw-head': call['with']['admitted_head'] = '${{ inputs.subject_head_sha }}'
    elif mutation == 'empty-generation': call['with']['admission_generation'] = ''
    elif mutation == 'missing-field': call['with'].pop('admitted_base')
    elif mutation == 'extra-field': call['with']['raw_authority'] = '${{ inputs }}'
    elif mutation == 'candidate-callee': call['uses'] = './.github/workflows/trusted-ci-executor.yml'
    elif mutation == 'wrong-plan-dependency': jobs['ci-plan']['needs'] = []
    elif mutation == 'failed-resolver-allowed': jobs['ci-plan']['if'] = 'always()'
    elif mutation == 'raw-plan-output': jobs['ci-plan']['outputs']['admitted_pr'] = '${{ inputs.pr_number }}'
    elif mutation == 'raw-identity-input':
        next(s for s in jobs['ci-plan']['steps'] if s.get('id') == 'identity')['env']['ADMITTED_HEAD'] = '${{ inputs.subject_head_sha }}'
    elif mutation == 'raw-resolver-output': jobs['ci-admission']['outputs']['subject_head'] = '${{ inputs.subject_head_sha }}'
    elif mutation == 'candidate-checkout': jobs['ci-admission']['steps'][0]['with']['ref'] = '${{ inputs.subject_head_sha }}'
    elif mutation == 'candidate-resolver': jobs['ci-admission']['steps'][1]['run'] = 'python3 scripts/author.py'
    elif mutation == 'missing-dispatch-input': ci.get('on', ci.get(True))['workflow_dispatch']['inputs'].pop('proof_role')
    elif mutation == 'required-callee-input': callee['admitted_head']['required'] = True
    elif mutation == 'nonempty-callee-default': callee['admitted_head']['default'] = 'author-supplied'
    elif mutation == 'wrong-callee-type': callee['admitted_pr']['type'] = 'number'
    elif mutation == 'extra-required-callee-input': callee['extra'] = dict(type='string', required=True)
    elif mutation == 'extra-required-dispatch-input': ci.get('on', ci.get(True))['workflow_dispatch']['inputs']['extra'] = dict(type='string', required=True)
    assert not mog.admitted_dispatch_source_ready('mastermindx-market-intelligence/macro', ci, executor)


def test_bootstrap_refusal_has_no_reservation_or_dispatch_effect(monkeypatch):
    state, _, demand, context = custody_harness(monkeypatch)
    monkeypatch.setattr(mog, 'installed_admitted_dispatch_ready', lambda *a: False)
    assert mog.reserve_shared_admission('acme/widgets', 'read', 'write', demand, **context).disposition == 'held'
    assert state['writes'] == [] and state['description'] == 'a2 idle'
    state, reference, context = dispatch_harness(monkeypatch)
    monkeypatch.setattr(mog, 'installed_admitted_dispatch_ready', lambda *a: False)
    assert mog.dispatch_admitted_pr_proof('acme/widgets', 'read', 'write', reference, **context).disposition == 'held'
    assert state['patches'] == 0 and state['posts'] == []


def git_source_stub(monkeypatch, *, head='4'*40, duplicate=False, oversized=False):
    import subprocess
    from types import SimpleNamespace
    import yaml
    ci, executor = bridge_documents()
    blobs = {'.github/workflows/ci.yml': yaml.safe_dump(ci).encode(),
             '.github/workflows/trusted-ci-executor.yml': yaml.safe_dump(executor).encode()}
    if duplicate: blobs['.github/workflows/ci.yml'] += b'jobs: {}\n'
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        assert kwargs['cwd'] == mog._ROOT
        assert 0 < kwargs['timeout'] <= 10
        assert kwargs['env']['GIT_NO_LAZY_FETCH'] == '1'
        assert kwargs['env']['GIT_NO_REPLACE_OBJECTS'] == '1'
        if 'rev-parse' in args: return SimpleNamespace(returncode=0, stdout=(head+'\n').encode())
        assert args[-1].startswith('4'*40 + ':.github/workflows/')
        raw = blobs[args[-1].split(':', 1)[1]]
        if 'cat-file' in args: return SimpleNamespace(returncode=0, stdout=str(10**9 if oversized else len(raw)).encode())
        assert 'show' in args
        return SimpleNamespace(returncode=0, stdout=raw)
    monkeypatch.setattr(subprocess, 'run', run)
    return calls


def test_bootstrap_reads_only_exact_checked_out_objects_without_lazy_fetch(monkeypatch):
    calls = git_source_stub(monkeypatch)
    assert mog.installed_admitted_dispatch_ready('mastermindx-market-intelligence/macro', '4'*40)
    assert len(calls) == 5


@pytest.mark.parametrize('case', ['wrong-head', 'duplicate-yaml', 'oversized', 'invalid-sha', 'timeout'])
def test_bootstrap_unknown_source_fails_closed(monkeypatch, case):
    import subprocess
    calls = git_source_stub(monkeypatch, head='5'*40 if case == 'wrong-head' else '4'*40,
                            duplicate=case == 'duplicate-yaml', oversized=case == 'oversized')
    if case == 'timeout':
        def timeout(*a, **kw): raise subprocess.TimeoutExpired(a[0], 5)
        monkeypatch.setattr(subprocess, 'run', timeout)
    assert not mog.installed_admitted_dispatch_ready('mastermindx-market-intelligence/macro',
                                                     'main' if case == 'invalid-sha' else '4'*40)
    if case == 'invalid-sha': assert calls == []
    if case == 'wrong-head': assert len(calls) == 1


def test_bootstrap_missing_yaml_dependency_is_not_readiness(monkeypatch):
    import builtins
    original = builtins.__import__
    def without_yaml(name, *args, **kwargs):
        if name == 'yaml': raise ImportError('unavailable local parser')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', without_yaml)
    assert not mog.installed_admitted_dispatch_ready('acme/widgets', '4'*40)
