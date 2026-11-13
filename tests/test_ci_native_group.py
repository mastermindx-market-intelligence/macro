"""Offline native pilot membership and semantic identity discriminators."""
import copy
from pathlib import Path
import pytest
from scripts import ci_authority as authority
from scripts import ci_semantic_proof as proof

REPO = 'mastermindx-market-intelligence/macro'
BASE, HEAD, SOURCE, TREE = (c * 40 for c in '1234')
TARGET = 'codex/merge-queue-pilot'
REF = 'refs/heads/gh-readonly-queue/' + TARGET + '/pr-7-test'

def fixture():
    event = {'action': 'checks_requested', 'repository': {'full_name': REPO},
             'merge_group': {'head_sha': HEAD, 'base_sha': BASE,
                 'head_ref': REF, 'base_ref': 'refs/heads/' + TARGET}}
    row = {'id': 'MQE_7', 'position': 1, 'baseCommit': {'oid': BASE},
        'headCommit': {'oid': HEAD, 'tree': {'oid': TREE}, 'parents': {'nodes': [{'oid': BASE}]}},
        'pullRequest': {'number': 7, 'state': 'OPEN', 'isDraft': False,
            'baseRefName': TARGET, 'headRefOid': SOURCE, 'headRefName': 'metabolism/native-fixture',
            'baseRepository': {'nameWithOwner': REPO}, 'headRepository': {'nameWithOwner': REPO},
            'potentialMergeCommit': {'tree': {'oid': TREE}, 'parents': {'nodes': [{'oid': BASE}, {'oid': SOURCE}]}}}}
    snapshot = {'repository': {'nameWithOwner': REPO,
        'ref': {'name': TARGET, 'target': {'oid': BASE}},
        'mergeQueue': {'configuration': {'mergeMethod': 'SQUASH', 'maximumEntriesToBuild': 1,
            'maximumEntriesToMerge': 1, 'minimumEntriesToMerge': 1},
            'entries': {'totalCount': 1, 'pageInfo': {'hasNextPage': False}, 'nodes': [row]}}}}
    return snapshot, event

def validate(snapshot, event):
    return authority.validate_native_queue_snapshot(snapshot, event, REPO,
        execution_sha=HEAD, execution_ref=REF)

def test_pilot_exact_original_membership():
    group = validate(*fixture())
    assert group == dict(target_ref=TARGET, queue_entry_id='MQE_7', pr_number=7,
        source_head_sha=SOURCE, group_head_sha=HEAD, base_sha=BASE, tree_sha=TREE)

@pytest.mark.parametrize('mutation', [
    'missing_target','missing_queue','pagination','count','duplicate','moved','wrong_base',
    'group_parents','source_parents','tree','fork','closed','draft','wrong_target',
    'wrong_head','wrong_repo','parallel','minimum','boolean_config','main','execution',
])
def test_native_membership_refuses_uncertain_or_changed_identity(mutation):
    data, event = fixture(); repo=data['repository']; queue=repo['mergeQueue']; entries=queue['entries']
    row=entries['nodes'][0]; pr=row['pullRequest']
    if mutation == 'missing_target': repo['ref']=None
    elif mutation == 'missing_queue': repo['mergeQueue']=None
    elif mutation == 'pagination': entries['pageInfo']['hasNextPage']=True
    elif mutation == 'count': entries['totalCount']=2
    elif mutation == 'duplicate': entries['nodes'].append(copy.deepcopy(row)); entries['totalCount']=2
    elif mutation == 'moved': row['position']=2
    elif mutation == 'wrong_base': repo['ref']['target']['oid']='a'*40
    elif mutation == 'group_parents': row['headCommit']['parents']['nodes'].append({'oid': SOURCE})
    elif mutation == 'source_parents': pr['potentialMergeCommit']['parents']['nodes'].reverse()
    elif mutation == 'tree': pr['potentialMergeCommit']['tree']['oid']='b'*40
    elif mutation == 'fork': pr['headRepository']['nameWithOwner']='outsider/macro'
    elif mutation == 'closed': pr['state']='CLOSED'
    elif mutation == 'draft': pr['isDraft']=True
    elif mutation == 'wrong_target': pr['baseRefName']='main'
    elif mutation == 'wrong_head': pr['headRefOid']='c'*40
    elif mutation == 'wrong_repo': repo['nameWithOwner']='outsider/macro'
    elif mutation == 'parallel': queue['configuration']['maximumEntriesToBuild']=2
    elif mutation == 'minimum': queue['configuration']['minimumEntriesToMerge']=2
    elif mutation == 'boolean_config': queue['configuration']['maximumEntriesToMerge']=True
    elif mutation == 'main': event['merge_group']['base_ref']='refs/heads/main'
    elif mutation == 'execution': event['merge_group']['head_sha']='d'*40
    with pytest.raises(authority.AuthorityContractError): validate(data,event)

def legacy_helpers():
    from tests import test_ci_semantic_proof
    return test_ci_semantic_proof

def group_plan():
    old=legacy_helpers(); plan=old._plan(); group=validate(*fixture())
    plan.update(role='merge_group',event='merge_group',admission_generation='a'*12,
        native_group=group, tested_tree_sha=HEAD,subject_head_sha=SOURCE,base_sha=BASE,changed_from=BASE)
    plan['plan_sha256']=proof.authoritative_plan_sha256(plan)
    fragment=old._fragment(plan=plan)
    fragment.update(admission_generation='a'*12,native_group=copy.deepcopy(group))
    return plan,fragment

def test_group_roundtrip_is_original_bound_and_legacy_shapes_unchanged():
    plan,fragment=group_plan(); evidence=proof.reconcile_evidence(plan,[fragment])
    assert evidence['status']=='clear' and evidence['role']=='merge_group'
    loaded=proof.load_semantic_evidence(evidence,advertised=True,expected_native_group=plan['native_group'],
        expected_run_id=plan['workflow_run_id'],expected_event='merge_group',expected_role='merge_group')
    assert loaded.mode=='semantic'
    for role in ('main','pr_head'):
        old=legacy_helpers()._plan(role=role)
        assert 'native_group' not in proof.plan_hash_payload_from_document(old)

@pytest.mark.parametrize('field,value', [('queue_entry_id','MQE_other'),('pr_number',8),('tree_sha','9'*40)])
def test_group_member_identity_changes_hash_and_cannot_cross_fragments(field,value):
    plan,fragment=group_plan(); changed=copy.deepcopy(plan); changed['native_group'][field]=value
    changed['plan_sha256']=proof.authoritative_plan_sha256(changed)
    assert changed['plan_sha256']!=plan['plan_sha256']
    with pytest.raises(proof.SemanticProofError): proof.reconcile_evidence(changed,[fragment])

@pytest.mark.parametrize('field,value', [('role','main'),('role','pr_head'),('event','pull_request'),
    ('admission_generation',None),('native_group',None),('subject_head_sha','f'*40)])
def test_group_alias_or_missing_receipt_identity_refused(field,value):
    plan,_=group_plan(); plan[field]=value
    with pytest.raises(proof.SemanticProofError): proof.authoritative_plan_sha256(plan)

def test_group_failed_unit_never_inherits_other_original_green():
    plan,fragment=group_plan(); fragment['jobs'][0]['steps'][0]['outcome']='failed'
    evidence=proof.reconcile_evidence(plan,[fragment])
    assert evidence['status']=='failure'
    assert evidence['jobs'][0]['steps'][0]['classification']=='unknown'
    proof.load_semantic_evidence(evidence,advertised=True)

def test_runner_roundtrips_native_identity_without_replanning(tmp_path):
    import json
    from scripts import run_ci_pack as pack
    group=validate(*fixture())
    definition={'if':'${{ false }}', 'runs-on':'ubuntu-latest', 'timeout-minutes': 5, 'steps':[{'name':'current original proof','run':'true'}]}
    manifest=tmp_path/'fixture.yml'
    import yaml
    manifest.write_text(yaml.safe_dump({'jobs':{'fixture':definition}}))
    jobs=pack.load_legacy_jobs(manifest)
    plan=pack.build_plan(jobs, ['engine/fixture.py'],changed_from=BASE,scope_mode='off',pack_count=1,
        workflow_run_id='9',workflow='ci',event='merge_group',role='merge_group',
        tested_tree_sha=HEAD,subject_head_sha=SOURCE,base_sha=BASE,
        admission_generation='a'*12,native_group=group)
    assert plan.to_dict()['native_group']==group
    assert proof.authoritative_plan_sha256(plan.to_dict())==plan.plan_sha256
    file=tmp_path/'plan.json';file.write_text(json.dumps(plan.to_dict()))
    loaded=pack.load_authoritative_plan(file,workflow=manifest,expect_native_group=group)
    assert loaded.to_dict()==plan.to_dict()
    assert pack._fragment_admission_fields(loaded)['native_group']==group
    wrong={**group,'queue_entry_id':'wrong'}
    with pytest.raises(pack.ManifestError,match='native_group mismatch'):
        pack.load_authoritative_plan(file,workflow=manifest,expect_native_group=wrong)

def native_admission():
    from scripts import ci_proof_admission as contract
    return contract.NativeAdmission('a'*12,7,SOURCE,BASE,'5'*40,'6'*40,tree_sha=TREE)

def test_native_capacity_retains_unindexed_floor_and_counts_original_group_once():
    from scripts import ci_proof_admission as c
    a=native_admission(); runs=[c.Run(i,1,'in_progress','pr_head') for i in range(1,8)]
    assert c.capacity(runs,[a],census_complete=True,records_complete=True)==0
    queued=c.bind_native_entry(a,'MQE_7')
    bound=c.bind_native_execution(queued,validate(*fixture()),8,1)
    assert c.capacity(runs+[c.Run(8,1,'in_progress','merge_group')],[bound],
        census_complete=True,records_complete=True)==0
    assert c.native_execution_identity(bound)==validate(*fixture())
    settled=c.settle_run(bound,c.Run(8,1,'completed','merge_group'))
    assert c.capacity(runs+[c.Run(8,1,'completed','merge_group')],[settled],
        census_complete=True,records_complete=True)==1

@pytest.mark.parametrize('case',['entry','source','base','tree','group','attempt','run','pr_alias'])
def test_native_admission_original_cannot_be_replaced_or_relabeled(case):
    from scripts import ci_proof_admission as c
    a=c.bind_native_entry(native_admission(),'MQE_7'); group=validate(*fixture())
    bound=c.bind_native_execution(a,group,8,1)
    with pytest.raises(ValueError):
        if case=='entry': c.bind_native_entry(bound,'other')
        elif case in {'source','base','tree','group'}:
            key={'source':'source_head_sha','base':'base_sha','tree':'tree_sha','group':'group_head_sha'}[case]
            c.bind_native_execution(bound,{**group,key:'f'*40},8,1)
        elif case=='attempt': c.bind_native_execution(bound,group,8,2)
        elif case=='run': c.bind_native_execution(bound,group,9,1)
        else: c.validate_execution(bound,subject_head=SOURCE,base=BASE,merge='5'*40,
            parents=[BASE,SOURCE],workflow='6'*40)

def rules_fixture():
    return [dict(type='merge_queue',parameters=dict(merge_method='SQUASH',grouping_strategy='ALLGREEN',
        max_entries_to_build=1,max_entries_to_merge=1,min_entries_to_merge=1)),
        dict(type='workflows',parameters=dict(do_not_enforce_on_create=False,workflows=[
            dict(repository_id=42,path=path,ref='refs/heads/main',sha='6'*40)
            for path in ('.github/workflows/ci.yml','.github/workflows/fences.yml','.github/workflows/ci-authority.yml')]))]

def test_native_entry_may_use_stale_base_exact_head_only_with_integrated_protection():
    old=legacy_helpers(); plan=old._plan(); evidence=proof.reconcile_evidence(plan,[old._fragment(plan=plan)])
    loaded=proof.load_semantic_evidence(evidence,advertised=True)
    protection=authority.native_protection_contract(rules_fixture(),repository_id=42,protected_source_sha='6'*40)
    # Original base is unrelated to the selected target's newer tip. Entry is
    # intentionally not current-base final acceptance.
    assert evidence['base_sha'] != BASE
    authority.native_source_entry_qualification(loaded,expected_head_sha=plan['subject_head_sha'],protection=protection)
    with pytest.raises(authority.AuthorityContractError):
        authority.native_source_entry_qualification(loaded,expected_head_sha=plan['subject_head_sha'],protection={})
    with pytest.raises(proof.SemanticProofError):
        authority.native_source_entry_qualification(loaded,expected_head_sha='f'*40,protection=protection)
    group,_=group_plan()
    with pytest.raises(proof.SemanticProofError):
        proof.load_semantic_evidence(evidence,advertised=True,expected_role='merge_group',expected_native_group=group['native_group'])

@pytest.mark.parametrize('case',['missing','missing_ci','foreign','moving_ref','wrong_source','duplicate','bypass_creation','parallel','missing_queue'])
def test_native_entry_protection_requires_actual_pinned_integrated_workflows(case):
    rules=rules_fixture(); workflows=rules[1]['parameters']['workflows']
    if case=='missing': rules=[]
    elif case=='missing_ci': workflows.pop(0)
    elif case=='foreign': workflows[0]['repository_id']=99
    elif case=='moving_ref': workflows[0]['ref']='refs/heads/candidate'
    elif case=='wrong_source': workflows[0]['sha']='f'*40
    elif case=='duplicate': workflows.append(copy.deepcopy(workflows[0]))
    elif case=='bypass_creation': rules[1]['parameters']['do_not_enforce_on_create']=True
    elif case=='parallel': rules[0]['parameters']['max_entries_to_build']=2
    elif case=='missing_queue': rules.pop(0)
    with pytest.raises(authority.AuthorityContractError):
        authority.native_protection_contract(rules,repository_id=42,protected_source_sha='6'*40)

def test_native_history_and_checkpoint_conserve_queue_run_identity():
    from scripts import ci_proof_admission as c
    a=native_admission();q=c.bind_native_entry(a,'MQE_7');b=c.bind_native_execution(q,validate(*fixture()),8,1)
    assert c.merge_records([a,q,b,a])==[b]
    before=c.compact_pr_records(7,10,[a],[],[],records_complete=True)
    after=c.compact_pr_records(7,11,[a,q,b],[],[],records_complete=True)
    c.validate_checkpoint_transition(before,after)
    with pytest.raises(ValueError): c.validate_checkpoint_transition(after,before)

def authorization_fixture():
    group=validate(*fixture())
    pull=dict(number=7,state='open',merged=False,draft=False,title='source change',body='',
        head=dict(sha=SOURCE,repo=dict(full_name=REPO)),base=dict(ref=TARGET,repo=dict(full_name=REPO)),
        user=dict(login='author'),labels=[dict(name='merge-on-green')])
    reviews=[dict(id=1,state='APPROVED',commit_id=SOURCE,user=dict(login='reviewer',type='User'))]
    return dict(pull=pull,comments=[],reviews=reviews,group=group,review_decision='APPROVED',
        issuer_permission='write',comments_complete=True,reviews_complete=True,expected_repository=REPO,
        review_policy=dict(disposition='QUALIFIED',origin='AUTOMATIC_POLICY',repository=REPO,
            pull_number=7,head_sha=SOURCE,target_ref=TARGET,native_review_decision_required=True,
            required_independent_assessments=1,required_formal_non_author_approvals=1,
            accepted_independent_assessments=1,accepted_formal_non_author_approvals=1,
            qualifying_reviewer_logins=['reviewer'],source_contributors=['author','coauthor']),
        issuer_login='issuer')

def test_current_native_release_allows_exact_source_then_refuses_new_hold():
    args=authorization_fixture();authority.native_release_authorization(**args)
    args['comments']=[dict(id=1,body='HOLD: preserve source',user=dict(login='reviewer',type='User'),created_at='2026-11-05T10:00:00Z')]
    with pytest.raises(authority.AuthorityContractError,match='recorded hold'):
        authority.native_release_authorization(**args)

@pytest.mark.parametrize('case',['draft','head','target','fork','disarmed','blocked','issuer','comments','review','selfreview','oldreview','changes'])
def test_current_native_release_does_not_reuse_enqueue_authorization(case):
    args=authorization_fixture();p=args['pull']
    if case=='draft':p['draft']=True
    elif case=='head':p['head']['sha']='f'*40
    elif case=='target':p['base']['ref']='main'
    elif case=='fork':p['head']['repo']['full_name']='outsider/macro'
    elif case=='disarmed':p['labels']=[]
    elif case=='blocked':p['labels'].append(dict(name='merge-blocked'))
    elif case=='issuer':args['issuer_permission']='read'
    elif case=='comments':args['comments_complete']=False
    elif case=='review':args['review_decision']='REVIEW_REQUIRED'
    elif case=='selfreview':args['review_policy']['qualifying_reviewer_logins']=['author']
    elif case=='oldreview':args['review_policy']['head_sha']='f'*40
    elif case=='changes':args['reviews'].append(dict(id=2,state='CHANGES_REQUESTED',commit_id=SOURCE,user=dict(login='another',type='User')))
    with pytest.raises(authority.AuthorityContractError):authority.native_release_authorization(**args)

def test_native_real_archive_authenticates_typed_original_and_refuses_legacy_relabel():
    from scripts import ci_proof_admission as c
    from dataclasses import asdict
    import hashlib,io,json,zipfile
    a=c.bind_native_execution(c.bind_native_entry(native_admission(),'MQE_7'),validate(*fixture()),8,1)
    def context(schema):
        raw=json.dumps(dict(schema=schema,repository_id=42,controller_run_id=9,controller_run_attempt=1,
            admission=asdict(a)),sort_keys=True,separators=(',',':')).encode()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:z.writestr('ci-proof-admission.json',raw)
        archive=stream.getvalue()
        return dict(archive=archive,payload_sha256=hashlib.sha256(raw).hexdigest(),repository_id=42,
            artifact_id=10,controller_run_id=9,controller_attempt=1,controller_sha='6'*40,
            artifact=dict(id=10,name='ci-proof-admission-9-1-'+a.generation+'-native-bound',expired=False,
                digest='sha256:'+hashlib.sha256(archive).hexdigest(),workflow_run=dict(id=9,repository_id=42,head_sha='6'*40)),
            controller=dict(id=9,run_attempt=1,repository=dict(id=42),path='.github/workflows/merge-on-green.yml',
                head_branch='main',head_sha='6'*40,event='workflow_run'))
    ctx=context('mastermind.ci-proof-native-admission.v1')
    assert c.authenticate_receipt(**ctx)==a
    with pytest.raises(ValueError):c.authenticate_receipt(**context('mastermind.ci-proof-admission.v1'))
    ctx['artifact']['expired']=True
    with pytest.raises(ValueError):c.authenticate_receipt(**ctx)


def test_main_and_pilot_membership_and_proof_are_not_transferable():
    data,event=fixture(); repo=data['repository']; row=repo['mergeQueue']['entries']['nodes'][0]
    event['merge_group']['base_ref']='refs/heads/main'; event['merge_group']['head_ref']='refs/heads/gh-readonly-queue/main/pr-7-test'
    repo['ref']['name']='main';row['pullRequest']['baseRefName']='main'
    group=authority.validate_native_queue_snapshot(data,event,REPO,execution_sha=HEAD,execution_ref=event['merge_group']['head_ref'])
    assert group['target_ref']=='main'
    plan,fragment=group_plan();plan['native_group']=group;plan['plan_sha256']=proof.authoritative_plan_sha256(plan)
    with pytest.raises(proof.SemanticProofError):proof.reconcile_evidence(plan,[fragment])
    with pytest.raises(authority.AuthorityContractError):
        authority.native_protection_contract([],repository_id=42,protected_source_sha='6'*40,selected_target='main')

def test_native_server_run_reader_keeps_original_attempt_and_role(monkeypatch):
    from scripts import ci_proof_admission as c, merge_on_green as mog
    a=c.bind_native_execution(c.bind_native_entry(native_admission(),'MQE_7'),validate(*fixture()),8,1)
    response=dict(id=8,run_attempt=1,event='merge_group',head_sha=HEAD,
        head_branch=REF.removeprefix('refs/heads/'),path='.github/workflows/ci.yml',repository=dict(id=42),status='in_progress')
    monkeypatch.setattr(mog,'_request',lambda *a,**k:(200,response))
    assert mog._read_admitted_run(REPO,'test-token',a,42)==c.Run(8,1,'in_progress','merge_group')
    response['run_attempt']=2
    with pytest.raises(ValueError):mog._read_admitted_run(REPO,'test-token',a,42)

def test_active_index_counts_native_original_without_relabeling_pr(monkeypatch):
    from scripts import merge_on_green as mog
    def get(method,url,token):
        return 200,dict(total_count=1,workflow_runs=[dict(id=8,run_attempt=1,event='merge_group',status='in_progress')])
    monkeypatch.setattr(mog,'_request',get)
    rows=mog.indexed_active_ci_runs(REPO,'test-token')
    assert len(rows)==1 and rows[0].role=='merge_group'

@pytest.mark.parametrize("branch", [None, "", "../main", "bad\nbranch", "branch@{1}", "x"*1025])
def test_native_membership_requires_source_branch_for_loop_fence(branch):
    data,event=fixture()
    data['repository']['mergeQueue']['entries']['nodes'][0]['pullRequest']['headRefName']=branch
    with pytest.raises(authority.AuthorityContractError):validate(data,event)

def resolver_provider(monkeypatch, *, workflow='ci.yml', mutation=None):
    from scripts import resolve_ci_pr_admission as resolver
    from scripts import ci_proof_admission as c
    data,event=fixture();calls=[]
    group=validate(data,event)
    bound=c.bind_native_execution(c.bind_native_entry(native_admission(),'MQE_7'),group,8,1)
    run=dict(id=8,run_attempt=1,status='in_progress',event='merge_group',head_sha=HEAD,
        head_branch=REF.removeprefix('refs/heads/'),repository={'id':42},path='.github/workflows/'+workflow)
    def request(method,url,token,body=None):
        assert token=='fixture-token';calls.append((method,url))
        if url.endswith('/branches/main'):return 200,{'commit':{'sha':'6'*40}}
        if url.endswith('/actions/runs/8'):return 200,copy.deepcopy(run)
        if '/rules/branches/' in url:return 200,rules_fixture()
        if url.endswith('/graphql'):
            assert method=='POST' and body['query']==authority.NATIVE_QUEUE_QUERY
            result=copy.deepcopy(data)
            if mutation=='changed_branch' and sum(u.endswith('/graphql') for _,u in calls)>1:
                result['repository']['mergeQueue']['entries']['nodes'][0]['pullRequest']['headRefName']='other/source'
            return 200,{'data':result}
        raise AssertionError((method,url))
    monkeypatch.setattr(resolver.mog,'_request',request)
    monkeypatch.setattr(resolver.mog,'fetch_issue_comments',lambda *a,**k: [])
    monkeypatch.setattr(resolver.mog,'pr_admission_history',lambda *a,**k: ([bound],[]))
    context=dict(repository=REPO,repository_id=42,run_id=8,run_attempt=1,
        workflow_sha='6'*40,workflow_ref=REPO+'/.github/workflows/'+workflow+'@refs/heads/main',
        event_sha=HEAD,event_name='merge_group',ref=REF,token='fixture-token')
    return resolver,event,context,calls

def test_native_resolver_reads_bound_original_and_keeps_group_event(monkeypatch):
    resolver,event,context,calls=resolver_provider(monkeypatch)
    result=resolver.resolve_native(event,**context)
    assert result['semantic_role']=='merge_group' and result['subject_head']==SOURCE
    assert result['tested_commit']==HEAD and result['admission_generation']=='a'*12
    assert all(method=='GET' or url.endswith('/graphql') for method,url in calls)

def test_native_membership_sidecar_binds_real_source_branch(monkeypatch):
    resolver,event,context,calls=resolver_provider(monkeypatch,workflow='fences.yml')
    result=resolver.resolve_native(event,**context,membership_only=True,workflow_file='fences.yml',include_source_branch=True)
    assert result==dict(group=validate(*fixture()),source_branch='metabolism/native-fixture')
    assert len(calls)==6

def test_native_membership_sidecar_refuses_branch_changed_during_reads(monkeypatch):
    resolver,event,context,calls=resolver_provider(monkeypatch,workflow='fences.yml',mutation='changed_branch')
    with pytest.raises(resolver.ResolutionError):
        resolver.resolve_native(event,**context,membership_only=True,workflow_file='fences.yml',include_source_branch=True)

@pytest.mark.parametrize('case',['candidate_source','attempt','unreserved','foreign_original','expired_read'])
def test_native_resolver_refuses_untrusted_or_incomplete_original(monkeypatch,case):
    resolver,event,context,calls=resolver_provider(monkeypatch)
    if case=='candidate_source':context['workflow_ref']=REPO+'/.github/workflows/ci.yml@'+REF
    if case=='attempt':context['run_attempt']=2
    if case=='unreserved':monkeypatch.setattr(resolver.mog,'pr_admission_history',lambda *a,**k:([],[]))
    if case=='foreign_original':context['run_id']=9
    if case=='expired_read':
        original=resolver.mog._request;clock=[0]
        def request(*a,**k):
            result=original(*a,**k);clock[0]=121;return result
        monkeypatch.setattr(resolver.mog,'_request',request);context['clock']=lambda:clock[0]
    with pytest.raises(resolver.ResolutionError):resolver.resolve_native(event,**context)

@pytest.mark.parametrize('case',['missing','contributor','coauthor'])
def test_native_exact_head_review_requires_source_and_issuer_independence(case):
    args=authorization_fixture()
    if case=='missing':args['review_policy']['source_contributors']=None
    elif case=='contributor':args['review_policy']['source_contributors'].append('reviewer')
    elif case=='coauthor':args['review_policy']['qualifying_reviewer_logins']=['coauthor']
    else:args['reviews'][0]['user']['login']='issuer'
    with pytest.raises(authority.AuthorityContractError):authority.native_release_authorization(**args)

def test_native_independent_reviewer_may_be_lawful_issuer():
    args=authorization_fixture();args['issuer_login']='reviewer'
    authority.native_release_authorization(**args)

@pytest.mark.parametrize('target,inactive,active',[('main','ci-authority/codex/merge-queue-pilot','ci-authority/main'),('codex/merge-queue-pilot','ci-authority/main','ci-authority/codex/merge-queue-pilot')])
def test_native_inactive_check_is_target_symmetric(target,inactive,active):
    from scripts import merge_on_green as mog
    assert mog.is_non_binding_check(inactive,base_ref=target)
    assert not mog.is_non_binding_check(active,base_ref=target)
    assert not mog.is_non_binding_check(inactive,base_ref='unqualified')

@pytest.mark.parametrize('issuer_case',['stable','changed_before_reserve'])
def test_two_ready_native_sources_reserve_sequential_actual_target_snapshots(monkeypatch,issuer_case):
    from scripts import merge_on_green as mog
    from scripts import ci_proof_admission as c
    from dataclasses import replace
    state={'base':BASE,'number':7,'head':SOURCE,'records':[],'register':'a2 idle r=10','queue':[],'issuer_reads':0}
    active=tuple(c.Run(100+i,1,'in_progress','pr_head') for i in range(7))
    monkeypatch.setattr(mog,'_shared_controller_authority',lambda *a,**k:True)
    protection=authority.native_protection_contract(rules_fixture(),repository_id=42,protected_source_sha='6'*40)
    monkeypatch.setattr(mog,'native_target_protection',lambda *a,**k:protection)
    monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(True,active,tuple(state['records'])))
    monkeypatch.setattr(mog,'migration_register_is_idle',lambda *a,**k:True)
    monkeypatch.setattr(mog,'native_current_release',lambda *a,**k:{'checks':[]})
    monkeypatch.setattr(mog,'semantic_evidence_for_head',lambda *a,**k:object())
    monkeypatch.setattr(authority,'native_source_entry_qualification',lambda *a,**k:None)
    def request(method,url,token,body=None):
        assert method in {'GET','POST'}
        if url==mog.GITHUB_API+'/user':
            assert token=='existing-pat';state['issuer_reads']+=1
            return 200,{'id':999 if issuer_case=='changed_before_reserve' and state['issuer_reads']==2 else 123,'login':'native-issuer','type':'User'}
        if url==mog.GITHUB_API+'/repos/'+REPO:
            assert token=='existing-pat';return 200,{'id':42,'full_name':REPO,'permissions':{'push':True}}
        if '/labels/' in url:return 200,{'description':state['register']}
        if '/pulls/' in url:return 200,dict(number=state['number'],state='open',mergeable=True,
            head={'sha':state['head']},base={'ref':TARGET,'sha':state['base'],'repo':{'id':42}},merge_commit_sha='5'*40)
        if '/git/commits/' in url:return 200,dict(sha='5'*40,parents=[{'sha':state['base']},{'sha':state['head']}],tree={'sha':TREE})
        if url.endswith('/branches/main'):return 200,{'commit':{'sha':'6'*40}}
        if '/branches/' in url:return 200,{'commit':{'sha':state['base']}}
        if url.endswith('/graphql'):
            data,_=fixture();repo=data['repository'];repo['ref']['target']['oid']=state['base']
            repo['mergeQueue']['entries']['nodes']=list(state['queue']);repo['mergeQueue']['entries']['totalCount']=len(state['queue'])
            return 200,{'data':data}
        raise AssertionError((method,url))
    effects=[]
    def effect(method,url,token,body):
        assert method=='PATCH';effects.append(body);state['register']=body['description'];return 200,{}
    monkeypatch.setattr(mog,'_request',request);monkeypatch.setattr(mog,'_shared_admission_effect',effect)
    context=dict(repository_id=42,protected_controller_sha='6'*40,current_run_id='9',current_run_attempt=1,native_target=TARGET,native_enqueue_token="existing-pat")
    first=mog.reserve_shared_admission(REPO,'read','write',c.Demand(7,SOURCE,'refresh','2026-11-05T00:00:00+00:00','a'*12),**context)
    if issuer_case=='changed_before_reserve':
        assert first.disposition=='held' and effects==[]
        return
    assert first.disposition=='prepared' and first.admission.base_sha==BASE and len(effects)==1
    state['records']=[first.admission];state['number']=8;state['head']='f'*40
    second_demand=c.Demand(8,'f'*40,'refresh','2026-11-05T00:00:01+00:00','b'*12)
    held=mog.reserve_shared_admission(REPO,'read','write',second_demand,**context)
    assert held.disposition=='held' and len(effects)==1
    # Test-owned original1 lands; its exact terminal observation settles capacity.
    bound=c.bind_native_execution(c.bind_native_entry(first.admission,'MQE_7'),validate(*fixture()),8,1)
    state['records']=[c.settle_run(bound,c.Run(8,1,'completed','merge_group'))]
    state['base']=HEAD;state['register']='a2 idle r=10'
    second=mog.reserve_shared_admission(REPO,'read','write',second_demand,**context)
    assert second.disposition=='prepared' and second.admission.base_sha==HEAD
    assert second.admission.head_sha=='f'*40 and second.admission.generation=='b'*12 and len(effects)==2
    assert second_demand.requested_at=='2026-11-05T00:00:01+00:00'

@pytest.mark.parametrize('case',['occupied','incomplete','changed_base'])
def test_native_queue_actual_emptiness_is_required_not_inferred_from_build_one(monkeypatch,case):
    from scripts import merge_on_green as mog
    data,_=fixture();entries=data['repository']['mergeQueue']['entries']
    if case!='occupied':entries.update(nodes=[],totalCount=0)
    if case=='incomplete':entries['pageInfo']['hasNextPage']=True
    if case=='changed_base':data['repository']['ref']['target']['oid']='f'*40
    monkeypatch.setattr(mog,'_request',lambda *a,**k:(200,{'data':data}))
    with pytest.raises(ValueError):mog.native_empty_target(REPO,'fixture',TARGET,BASE)

@pytest.mark.parametrize('role',['merge_group','pr_head'])
def test_native_active_checkpoint_uses_actual_admission_role(monkeypatch,role):
    from scripts import merge_on_green as mog
    from scripts import ci_proof_admission as c
    bound=c.bind_native_execution(c.bind_native_entry(native_admission(),'MQE_7'),validate(*fixture()),8,1)
    monkeypatch.setattr(mog,'_shared_controller_authority',lambda *a,**k:True)
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[{'id':1}])
    monkeypatch.setattr(mog,'pr_admission_history',lambda *a,**k:([bound],[]))
    monkeypatch.setattr(mog,'indexed_active_ci_runs',lambda *a,**k:[c.Run(8,1,'in_progress',role)])
    monkeypatch.setattr(mog,'_read_admitted_run',lambda *a,**k:c.Run(8,1,'in_progress','merge_group'))
    kwargs=dict(repository_id=42,protected_controller_sha='6'*40,current_run_id='9',current_run_attempt=1)
    if role=='pr_head':
        with pytest.raises(ValueError,match='identity changed'):mog.prepare_shared_checkpoint(REPO,'read',7,**kwargs)
    else:
        checkpoint=mog.prepare_shared_checkpoint(REPO,'read',7,**kwargs)
        assert checkpoint.admissions==(bound,)


def source_admission():
    from scripts import ci_proof_admission as c
    from dataclasses import asdict
    base=native_admission()
    fields={k:v for k,v in asdict(base).items() if k in c.Admission.__dataclass_fields__}
    return c.SourceAdmission(**fields,target_ref=TARGET)


def test_native_source_first_proof_has_distinct_receipt_and_pr_role():
    from scripts import ci_proof_admission as c
    from dataclasses import asdict,replace
    import hashlib,io,json,zipfile
    a=replace(source_admission(),run_id=8)
    raw=json.dumps(dict(schema='mastermind.ci-proof-source-admission.v1',repository_id=42,
        controller_run_id=9,controller_run_attempt=1,admission=asdict(a)),sort_keys=True,separators=(',',':')).encode()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr('ci-proof-admission.json',raw)
    archive=stream.getvalue()
    kwargs=dict(archive=archive,payload_sha256=hashlib.sha256(raw).hexdigest(),repository_id=42,
        artifact_id=10,controller_run_id=9,controller_attempt=1,controller_sha='6'*40,
        artifact=dict(id=10,name='ci-proof-admission-9-1-'+a.generation+'-source-bound',expired=False,
            digest='sha256:'+hashlib.sha256(archive).hexdigest(),workflow_run=dict(id=9,repository_id=42,head_sha='6'*40)),
        controller=dict(id=9,run_attempt=1,repository=dict(id=42),path='.github/workflows/merge-on-green.yml',
            head_branch='main',head_sha='6'*40,event='workflow_run'))
    assert c.authenticate_receipt(**kwargs)==a
    assert c.admission_role(a)=='pr_head'
    assert c.settle_run(a,c.Run(8,1,'completed','pr_head')).settled
    with pytest.raises(ValueError):c.settle_run(a,c.Run(8,1,'completed','merge_group'))
    kwargs['artifact']['name']=kwargs['artifact']['name'].replace('source-bound','native-bound')
    with pytest.raises(ValueError):c.authenticate_receipt(**kwargs)


def test_native_source_first_checkpoint_preserves_target_without_group_identity():
    from scripts import ci_proof_admission as c
    a=source_admission()
    # A source proof remains ordinary PR evidence, never a queue membership grant.
    assert c._admission_valid(a)
    assert not isinstance(a,c.NativeAdmission)
    assert c.merge_records([a,a])==[a]
    from dataclasses import replace
    with pytest.raises(ValueError):c.merge_records([a,replace(a,target_ref='main')])


def stage_binding_fixture(monkeypatch,tmp_path):
    from scripts import ci_admission_stages as stages,ci_proof_admission as c,merge_on_green as mog
    queued=c.bind_native_entry(native_admission(),'MQE_7')
    bound=c.bind_native_execution(queued,validate(*fixture()),8,1)
    context=dict(repository_id=42,protected_controller_sha='6'*40,current_run_id='9',current_run_attempt=1)
    s=stages.Stages(REPO,'fixture-read','fixture-write','fixture-checks',context,tmp_path)
    monkeypatch.setattr(s,'authority',lambda:None)
    monkeypatch.setattr(s,'reference',lambda *a:dict(artifact_id=10,controller_run_id=9,controller_attempt=1,controller_sha='6'*40,payload_sha256='a'*64))
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *a,**k:queued)
    monkeypatch.setattr(mog,'authenticated_migration_root',lambda *a,**k:10)
    return stages,mog,s,queued,bound


@pytest.mark.parametrize('case',['exact','different_generation','different_root','unreadable','refence_changed','lost_post'])
def test_native_queued_index_preserves_current_original_root(monkeypatch,tmp_path,case):
    stages,mog,s,queued,bound=stage_binding_fixture(monkeypatch,tmp_path)
    started=mog.shared_register_text(f'a2 p=7 g={queued.generation} s=started',10)
    calls=[];effects=[]
    def get(*args,**kwargs):
        calls.append(args)
        if case=='unreadable':return 503,{}
        text=started
        if case=='different_generation':text=text.replace(queued.generation,'b'*12)
        if case=='different_root':text=text.replace('r=10','r=11')
        if case=='refence_changed' and len(calls)>1:text='a2 idle r=10'
        return 200,{'description':text}
    monkeypatch.setattr(mog,'_request',get)
    monkeypatch.setattr(mog,'_publish_admission_reference',lambda *a,**k:effects.append(a) or case!='lost_post')
    if case in {'exact','lost_post'}:
        result=stages.Stages.finalize.__wrapped__(s,10)
        assert result==dict(finalized=False,disposition='queued' if case=='exact' else 'unknown')
        assert len(effects)==1 and len(calls)==2
    else:
        with pytest.raises(ValueError):stages.Stages.finalize.__wrapped__(s,10)
        assert effects==[]


def test_native_actual_provider_entry_and_run_bind_without_guessing_id(monkeypatch):
    from scripts import ci_proof_admission as c,merge_on_green as mog
    queued=c.bind_native_entry(native_admission(),'MQE_7')
    snapshot,_=fixture();calls=[]
    run=dict(id=817,run_attempt=1,event='merge_group',head_sha=HEAD,
        head_branch=REF.removeprefix('refs/heads/'),path='.github/workflows/ci.yml',repository={'id':42},status='queued')
    def request(method,url,token,body=None):
        calls.append((method,url))
        if url.endswith('/graphql'):return 200,{'data':snapshot}
        if '/actions/workflows/ci.yml/runs?' in url:return 200,{'total_count':1,'workflow_runs':[run]}
        if url.endswith('/actions/runs/817'):return 200,run
        raise AssertionError((method,url))
    monkeypatch.setattr(mog,'_request',request)
    actual=mog.native_bound_original(REPO,'fixture',queued,42)
    assert actual.run_id==817 and actual.group_head_sha==HEAD and actual.queue_entry_id=='MQE_7'
    assert len(calls)==3 and all(method=='GET' or url.endswith('/graphql') for method,url in calls)


@pytest.mark.parametrize('case',['multiple_runs','new_attempt','changed_group','missing_entry','incomplete'])
def test_native_original_binding_never_selects_replacement(monkeypatch,case):
    from scripts import ci_proof_admission as c,merge_on_green as mog
    queued=c.bind_native_entry(native_admission(),'MQE_7');snapshot,_=fixture()
    run=dict(id=817,run_attempt=1,event='merge_group',head_sha=HEAD,
        head_branch=REF.removeprefix('refs/heads/'),path='.github/workflows/ci.yml',repository={'id':42},status='queued')
    entries=snapshot['repository']['mergeQueue']['entries']
    if case=='missing_entry':entries.update(nodes=[],totalCount=0)
    if case=='incomplete':entries['pageInfo']['hasNextPage']=True
    if case=='changed_group':entries['nodes'][0]['headCommit']['tree']['oid']='f'*40
    if case=='new_attempt':run['run_attempt']=2
    def request(method,url,token,body=None):
        if url.endswith('/graphql'):return 200,{'data':snapshot}
        if '/actions/workflows/ci.yml/runs?' in url:
            rows=[run,dict(run,id=818)] if case=='multiple_runs' else [run]
            return 200,dict(total_count=len(rows),workflow_runs=rows)
        if url.endswith('/actions/runs/817'):return 200,run
        raise AssertionError((method,url))
    monkeypatch.setattr(mog,'_request',request)
    with pytest.raises(ValueError):mog.native_bound_original(REPO,'fixture',queued,42)


def native_workflow(name):
    import yaml
    return yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows'/name).read_text())


def test_native_controller_static_graph_preserves_original_migration_and_immutable_uploads():
    from scripts import check_runner_policy as policy
    document=native_workflow('merge-on-green.yml')
    assert policy._shared_admission_controller_r2_findings('.github/workflows/merge-on-green.yml',document)==[]
    assert policy._admitted_caller_graph_exact(native_workflow('ci.yml'))
    assert policy._trusted_call_is_exact(native_workflow('ci.yml')['jobs']['trusted-ci'])


@pytest.mark.parametrize('case',['container','job_continue','step_continue','resolver_ref','identity_tree','identity_parent','pc_group','missing_output'])
def test_native_static_resolver_graph_rejects_execution_and_identity_bypass(case):
    from scripts import check_runner_policy as policy
    document=native_workflow('ci.yml');job=document['jobs']['ci-admission']
    if case=='container':job['container']='untrusted/image:latest'
    elif case=='job_continue':job['continue-on-error']=True
    elif case=='step_continue':job['steps'][1]['continue-on-error']=True
    elif case=='resolver_ref':job['steps'][0]['with']['ref']='${{ github.sha }}'
    elif case=='missing_output':del job['outputs']['native_group_json']
    elif case=='pc_group':
        document['jobs']['trusted-ci']['if']=document['jobs']['trusted-ci']['if'].replace("github.event_name != 'merge_group' && ",'')
        assert not policy._trusted_call_is_exact(document['jobs']['trusted-ci']);return
    else:
        identity=next(x for x in document['jobs']['ci-plan']['steps'] if x.get('id')=='identity')
        match='assert git("rev-parse", "HEAD^{tree}") == group["tree_sha"]' if case=='identity_tree' else 'assert git("rev-list", "--parents", "-n", "1", "HEAD").split() == [group["group_head_sha"], group["base_sha"]]'
        assert match in identity['run'];identity['run']=identity['run'].replace(match,'pass')
    assert not policy._admitted_caller_graph_exact(document)


@pytest.mark.parametrize('case',['unreserved_bind','missing_refence_stage','mutable_checkout','cancel','upload_overwrite','wrong_original_artifact','parallel_group','lost_root_stage'])
def test_native_static_controller_graph_rejects_added_effect_shortcuts(case):
    from scripts import check_runner_policy as policy
    document=native_workflow('merge-on-green.yml');job=document['jobs']['sweep'];steps=job['steps']
    byid={x.get('id'):x for x in steps}
    if case=='unreserved_bind':byid['native_same_original']['if']='always()'
    elif case=='missing_refence_stage':steps.remove(byid['native_bind'])
    elif case=='mutable_checkout':steps[0]['with']['ref']='main'
    elif case=='cancel':job['concurrency']['cancel-in-progress']=True
    elif case=='upload_overwrite':byid['native_bound']['with']['overwrite']=True
    elif case=='wrong_original_artifact':byid['native_same_bound']['with']['name']='native-latest'
    elif case=='parallel_group':job['concurrency']['group']='merge-on-green-${{ github.run_id }}'
    elif case=='lost_root_stage':byid['migration_apply']['run']='echo bypass'
    assert policy._shared_admission_controller_r2_findings('.github/workflows/merge-on-green.yml',document)


def test_native_landing_has_natural_fence_push_wake_for_both_targets():
    fences=native_workflow('fences.yml');mog=native_workflow('merge-on-green.yml')
    event=fences.get('on',fences.get(True));controller=mog['jobs']['sweep']
    assert event['push']['branches']==['main',TARGET]
    assert 'paths' not in event['push'] and 'paths-ignore' not in event['push']
    assert "github.event.workflow_run.event == 'push'" in controller['if']
    assert "github.event.workflow_run.event != 'push'" in controller['concurrency']['group']
    assert controller['concurrency']['cancel-in-progress'] is False
    assert mog.get('on',mog.get(True))['workflow_run']['types']==['requested','completed']


@pytest.mark.parametrize('event,target,expected',[
    ({'branches':['main']},TARGET,False),({'branches':['main']},'main',True),
    ({'branches':['main',TARGET]},TARGET,True),(None,TARGET,True),
    ({'paths':['only-one-file']},TARGET,True),({'branches':['*']},TARGET,None),
    ({'branches-ignore':['main']},TARGET,None),({'branches':[]},TARGET,None),
])
def test_native_source_first_uses_actual_target_trigger_not_main_alias(event,target,expected):
    from scripts.ci_admission_stages import candidate_pr_trigger_for_target
    assert candidate_pr_trigger_for_target({'on':{'pull_request':event}},target) is expected


def test_native_source_first_no_trigger_is_distinct_from_unknown_bot_absence():
    from scripts.ci_admission_stages import candidate_pr_trigger_for_target
    assert candidate_pr_trigger_for_target({'on':{'workflow_dispatch':None}},TARGET) is False
    assert candidate_pr_trigger_for_target({'on':'pull_request'},TARGET) is True
    assert candidate_pr_trigger_for_target({'on':['pull_request','push']},TARGET) is True
    assert candidate_pr_trigger_for_target({'on':{'pull_request':None}},'other') is None


def test_native_source_readiness_accepts_composed_hosted_graph_without_activating_target():
    from scripts import merge_on_green as mog
    ci=native_workflow('ci.yml');executor=native_workflow('trusted-ci-executor.yml')
    assert mog.native_dispatch_source_ready(REPO,ci,executor)
    assert mog.admitted_dispatch_source_ready(REPO,ci,executor)
    assert not mog.native_dispatch_source_ready('other/repo',ci,executor)
    # Source capability grants no rules or synthetic membership.
    with pytest.raises(authority.AuthorityContractError):authority.native_protection_contract([],repository_id=42,protected_source_sha='6'*40)


@pytest.mark.parametrize('case',['resolver_skip','plan_skip','final_swallow','final_guard','gate_skip','pc_identity_input','group_contract_optional'])
def test_native_source_readiness_refuses_untrusted_or_skippable_graph(case):
    from scripts import merge_on_green as mog
    ci=native_workflow('ci.yml');executor=native_workflow('trusted-ci-executor.yml');j=ci['jobs']
    if case=='resolver_skip':j['ci-admission']['if']='false'
    elif case=='plan_skip':j['ci-plan']['if']='always()'
    elif case=='gate_skip':j['ci-gate']['if']='false'
    elif case=='pc_identity_input':j['trusted-ci']['with']={'admitted_head':'${{ inputs.head }}'}
    elif case=='group_contract_optional':j['contract-delta']['if']="needs.ci-plan.outputs.semantic_role == 'pr_head'"
    else:
        final=next(s for s in j['ci-gate']['steps'] if '--native-final' in s.get('run',''))
        if case=='final_swallow':final['run']+=' || true'
        else:final['if']='false'
    assert not mog.native_dispatch_source_ready(REPO,ci,executor)
    assert not mog.admitted_dispatch_source_ready(REPO,ci,executor)


@pytest.mark.parametrize('case',['same_original','expires_during_original_read','lost_pointer_patch','changed_root'])
def test_native_same_original_bind_keeps_deadline_and_sticky_custody(monkeypatch,tmp_path,case):
    from types import SimpleNamespace
    stages,mog,s,queued,bound=stage_binding_fixture(monkeypatch,tmp_path)
    now=[1000.0];effects=[];receipts=[]
    monkeypatch.setattr(mog.time,'time',lambda:now[0])
    # Real MigrationBudget/SweepBudget paths; only provider quota and time stubbed.
    monkeypatch.setattr(mog.SweepBudget,'_poll',lambda self:(1000,1000))
    started=mog.shared_register_text(f'a2 p=7 g={queued.generation} s=started',10)
    state={'description':started};reads=[]
    monkeypatch.setattr(mog,'shared_admission_inventory',lambda *a:SimpleNamespace(
        complete=True,mode='shared',launch=(7,queued.generation)))
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[])
    monkeypatch.setattr(mog,'pr_admission_history',lambda *a,**k:([queued],[]))
    def original(*args):
        now[0]+=241 if case=='expires_during_original_read' else 5
        return bound
    monkeypatch.setattr(mog,'native_bound_original',original)
    def request(method,url,token,body=None):
        if method=='PATCH':
            effects.append(body)
            if case=='lost_pointer_patch':return 503,{}
            state['description']=body['description'];return 200,dict(state)
        assert method=='GET';reads.append(url)
        if case=='changed_root' and len(reads)==2:return 200,{'description':started.replace('r=10','r=11')}
        return 200,dict(state)
    monkeypatch.setattr(mog,'_request',request)
    monkeypatch.setattr(s,'receipt',lambda *a,**k:receipts.append(a))
    with mog.migration_read_scope(REPO,'fixture-read',identity={'test':'original'},directory=tmp_path) as scope:
        budget=scope.require_budget()
        assert budget.deadline==1240
        if case=='expires_during_original_read':
            with pytest.raises(ValueError,match='deadline'):stages.Stages.bind_native.__wrapped__(s,wait=True)
        else:
            result=stages.Stages.bind_native.__wrapped__(s,wait=True)
            assert result['bound'] is (case=='same_original')
        assert budget.deadline==1240
    if case=='same_original':
        assert len(effects)==1 and len(receipts)==1
        assert 's=binding' in state['description'] and state['description'].endswith('r=10')
        assert receipts[0][1]['run_id']==8 and receipts[0][2]=='native-execution'
    elif case=='lost_pointer_patch':
        assert len(effects)==1 and receipts==[] and result['disposition']=='unknown'
    else:assert effects==[] and receipts==[]


def producer_fixture():
    import hashlib,io,json,zipfile
    origin=dict(producer_run_id=41,producer_run_attempt=1,workflow_path='.github/workflows/commodity-sentinel.yml',
        workflow_ref=REPO+'/.github/workflows/commodity-sentinel.yml@refs/heads/main',workflow_sha='6'*40,
        publishing_job='shock',publishing_step='native_publication_stage',credential_origin='GITHUB_TOKEN',pr_number=7,
        published_source_head=SOURCE,selected_target=TARGET,original_generation='a'*12,candidate_tree=TREE,
        projection_sha256='b'*64,pr_creation_user_id=41898282,pr_creation_login='github-actions[bot]')
    raw=json.dumps(dict(schema='mastermind.ci-proof-producer-origin.v1',repository_id=42,producer_origin=origin)).encode()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr('ci-proof-admission.json',raw)
    archive=stream.getvalue()
    return dict(archive=archive,repository_id=42,protected_producer_sha='6'*40,repository=REPO,
        artifact=dict(id=10,name='ci-proof-producer-origin-41-1-shock-native_publication_stage-'+'a'*12,expired=False,
            digest='sha256:'+hashlib.sha256(archive).hexdigest(),workflow_run=dict(id=41,repository_id=42,head_sha='6'*40)),
        producer_run=dict(id=41,run_attempt=1,path=origin['workflow_path'],head_sha='6'*40,head_branch='main',
            event='schedule',repository=dict(id=42,full_name=REPO)),
        pull=dict(number=7,state='open',head=dict(sha=SOURCE,repo=dict(id=42,full_name=REPO)),
            base=dict(ref=TARGET,repo=dict(id=42,full_name=REPO)),user=dict(id=41898282,login='github-actions[bot]')),
        source_commit=dict(sha=SOURCE,tree=dict(sha=TREE)))


def test_producer_archive_is_source_hint_not_admission():
    from scripts import ci_proof_admission as c
    origin=c.authenticate_producer_origin(**producer_fixture())
    assert origin['published_source_head']==SOURCE and origin['candidate_tree']==TREE
    assert 'admission_generation' not in origin and 'run_id' not in origin
    assert not isinstance(origin,c.Admission)


@pytest.mark.parametrize('case',['digest','expired','artifact_name','archive_duplicate','foreign_repo','candidate_workflow',
    'changed_attempt','changed_head','retarget','foreign_pr','creation_actor','source_tree','wrong_protected_pin'])
def test_producer_original_archive_refuses_unbound_or_changed_origin(case):
    from scripts import ci_proof_admission as c
    import hashlib,io,zipfile
    data=producer_fixture()
    if case=='digest':data['artifact']['digest']='sha256:'+'0'*64
    elif case=='expired':data['artifact']['expired']=True
    elif case=='artifact_name':data['artifact']['name']='ci-proof-producer-origin-latest'
    elif case=='foreign_repo':data['producer_run']['repository']['id']=99
    elif case=='candidate_workflow':data['producer_run']['head_branch']='candidate'
    elif case=='changed_attempt':data['producer_run']['run_attempt']=2
    elif case=='changed_head':data['pull']['head']['sha']='f'*40
    elif case=='retarget':data['pull']['base']['ref']='main'
    elif case=='foreign_pr':data['pull']['number']=8
    elif case=='creation_actor':data['pull']['user']['id']=123
    elif case=='source_tree':data['source_commit']['tree']['sha']='f'*40
    elif case=='wrong_protected_pin':data['protected_producer_sha']='f'*40
    else:
        raw=zipfile.ZipFile(io.BytesIO(data['archive'])).read('ci-proof-admission.json')
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            z.writestr('ci-proof-admission.json',raw);z.writestr('extra.json',raw)
        data['archive']=buf.getvalue();data['artifact']['digest']='sha256:'+hashlib.sha256(data['archive']).hexdigest()
    with pytest.raises(ValueError):c.authenticate_producer_origin(**data)


def producer_pointer(**changes):
    import json
    row=dict(run_id=41,run_attempt=1,job='shock',step='native_publication_stage',generation='a'*12)
    row.update(changes)
    return '<!-- mastermind-native-publication-origin:v1 '+json.dumps(row,separators=(',',':'))+' -->'


@pytest.mark.parametrize('case',['duplicate','extra_key','bool_id','wrong_step','newline','invalid_json'])
def test_producer_untrusted_pointer_is_unique_bounded_original_locator(case):
    from scripts import merge_on_green as mog
    text=producer_pointer()
    if case=='duplicate':text+='\n'+text
    elif case=='extra_key':text=producer_pointer(artifact_id=10)
    elif case=='bool_id':text=producer_pointer(run_id=True)
    elif case=='wrong_step':text=producer_pointer(step='other')
    elif case=='newline':text=text.replace('"job"','\n"job"')
    else:text=text.replace('"run_id":41','"run_id":')
    with pytest.raises(ValueError):mog.producer_origin_pointer({'body':text})


def test_producer_absence_never_becomes_bot_origin_evidence(monkeypatch):
    from scripts import merge_on_green as mog
    monkeypatch.setattr(mog,'_request',lambda *a,**k:pytest.fail('absent pointer must not probe replacement original'))
    assert mog.authenticated_producer_origin(REPO,'fixture',{'body':'','user':{'login':'github-actions[bot]'}},
        repository_id=42,protected_controller_sha='6'*40) is None


def producer_reader_provider(monkeypatch,case=None):
    from scripts import merge_on_green as mog
    import base64,hashlib,yaml
    ctx=producer_fixture();ctx['pull']['body']=producer_pointer();ctx['producer_run']['status']='in_progress'
    doc={'on':{'schedule':[{'cron':'*/30 * * * *'}]},'jobs':{'shock':{'steps':[
        {'uses':'actions/checkout@v4'},
        {'id':'native_publication_stage','env':{'GITHUB_TOKEN':'${{ secrets.GITHUB_TOKEN }}'},'run':'scripts/ci/push_retry.sh'},
        {'id':'origin_upload','uses':'./.github/actions/native-publication-origin','if':'always()'},
    ]}}}
    if case=='admin_source':doc['jobs']['shock']['steps'][1]['env']['GITHUB_TOKEN']='${{ secrets.ADMIN_GH_TOKEN }}'
    if case=='candidate_source':doc['jobs']['shock']['steps'][0]['with']={'ref':'${{ inputs.candidate }}'}
    raw=yaml.safe_dump(doc).encode();calls=[]
    def request(method,url,token,body=None):
        assert method=='GET' and token=='fixture'
        calls.append(url)
        if url.endswith('/actions/runs/41'):return 200,copy.deepcopy(ctx['producer_run'])
        if '/artifacts?per_page=' in url:
            rows=[] if case=='missing_upload' else [ctx['artifact']]
            if case=='duplicate_upload':rows=rows*2
            return 200,dict(total_count=len(rows),artifacts=rows)
        if url.endswith('/actions/artifacts/10'):return 200,ctx['artifact']
        if url.endswith('/pulls/7'):
            row=copy.deepcopy(ctx['pull'])
            if case=='changed_head':row['head']['sha']='f'*40
            return 200,row
        if '/git/commits/' in url:return 200,ctx['source_commit']
        if '/contents/.github/workflows/commodity-sentinel.yml?ref=' in url:
            return 200,dict(path='.github/workflows/commodity-sentinel.yml',type='file',encoding='base64',size=len(raw),
                sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),content=base64.b64encode(raw).decode())
        if '/attempts/1/jobs?' in url:
            status='in_progress' if case=='unsettled_step' else 'completed'
            return 200,dict(total_count=1,jobs=[dict(id=23,name='shock',run_id=41,run_attempt=1,head_sha='6'*40,
                steps=[dict(name='native_publication_stage',status=status,conclusion='failure' if case=='failed_stage' else 'success'),
                       dict(name='origin_upload',status='completed',conclusion='success')])])
        raise AssertionError(url)
    monkeypatch.setattr(mog,'_request',request)
    def download(url,token):
        assert url==mog.GITHUB_API+'/repos/'+REPO+'/actions/artifacts/10/zip' and token=='fixture'
        return ctx['archive']
    monkeypatch.setattr(mog,'_download_semantic_artifact',download)
    return mog,ctx,calls


def test_producer_original_in_progress_can_qualify_only_first_source_hint(monkeypatch):
    mog,ctx,calls=producer_reader_provider(monkeypatch)
    result=mog.authenticated_producer_origin(REPO,'fixture',ctx['pull'],repository_id=42,protected_controller_sha='6'*40)
    assert result['producer_run_id']==41 and result['published_source_head']==SOURCE
    assert len(calls)==8 and all('/repos/'+REPO+'/' in u for u in calls)


@pytest.mark.parametrize('case',['missing_upload','duplicate_upload','changed_head','admin_source','candidate_source','unsettled_step','failed_stage'])
def test_producer_reader_refuses_unknown_source_or_original_without_retry(monkeypatch,case):
    mog,ctx,calls=producer_reader_provider(monkeypatch,case)
    with pytest.raises(ValueError):mog.authenticated_producer_origin(REPO,'fixture',ctx['pull'],
        repository_id=42,protected_controller_sha='6'*40)
    assert len(calls)==len(set(calls))  # refusal ends before final re-fence


def review_facts_fixture():
    rules=rules_fixture()
    rules.append({'type':'pull_request','parameters':{
        'required_approving_review_count':1,'require_code_owner_review':False,'require_last_push_approval':False}})
    protection=authority.native_protection_contract(rules,repository_id=42,protected_source_sha='6'*40)
    group=dict(pr_number=7,source_head_sha=SOURCE,target_ref=TARGET)
    row=dict(number=7,headRefOid=SOURCE,baseRefName=TARGET,reviewDecision='APPROVED',
        baseRef={'name':TARGET,'branchProtectionRule':{
            'requiresApprovingReviews':True,'requiredApprovingReviewCount':2,
            'requiresCodeOwnerReviews':True}})
    return protection,row,group


def test_native_review_facts_maxima_use_same_current_snapshot_without_admin_rest():
    protection,row,group=review_facts_fixture()
    facts=authority.native_review_facts(protection,row,repository=REPO,group=group)
    assert facts['required_formal_approvals']==2
    assert facts['requires_code_owner_reviews'] is True
    assert facts['head_sha']==SOURCE and facts['target_ref']==TARGET
    assert facts['native_enforcement_qualified'] is True
    assert 'branchProtectionRule' in authority.NATIVE_PR_RELEASE_QUERY
    # Explicit server null differs from a missing/error field. No native review
    # requirement is inferred merely from a null reviewDecision.
    protection['required_formal_approvals']=0
    protection['review_decision_required']=False
    row['baseRef']['branchProtectionRule']=None;row['reviewDecision']=None
    facts=authority.native_review_facts(protection,row,repository=REPO,group=group)
    assert facts['required_formal_approvals']==0
    assert facts['requires_code_owner_reviews'] is False


@pytest.mark.parametrize('case',[
    'missing_classic','missing_base','wrong_base','boolean_count','missing_count',
    'contradictory_classic','missing_decision','required','changes','unknown_decision',
    'null_required','wrong_head','wrong_target','missing_rules_count','missing_workflows',
])
def test_native_review_facts_unknown_or_misbound_protection_refuses(case):
    protection,row,group=review_facts_fixture()
    if case=='missing_classic':row['baseRef'].pop('branchProtectionRule')
    elif case=='missing_base':row.pop('baseRef')
    elif case=='wrong_base':row['baseRef']['name']='main'
    elif case=='boolean_count':row['baseRef']['branchProtectionRule']['requiredApprovingReviewCount']=True
    elif case=='missing_count':row['baseRef']['branchProtectionRule'].pop('requiredApprovingReviewCount')
    elif case=='contradictory_classic':row['baseRef']['branchProtectionRule']['requiresApprovingReviews']=False
    elif case=='missing_decision':row.pop('reviewDecision')
    elif case=='required':row['reviewDecision']='REVIEW_REQUIRED'
    elif case=='changes':row['reviewDecision']='CHANGES_REQUESTED'
    elif case=='unknown_decision':row['reviewDecision']='UNAVAILABLE'
    elif case=='null_required':row['reviewDecision']=None
    elif case=='wrong_head':row['headRefOid']='f'*40
    elif case=='wrong_target':protection['target_ref']='main'
    elif case=='missing_rules_count':protection.pop('required_formal_approvals')
    elif case=='missing_workflows':protection.pop('required_workflows')
    with pytest.raises(authority.AuthorityContractError):
        authority.native_review_facts(protection,row,repository=REPO,group=group)


@pytest.mark.parametrize('params',[
    {},{'required_approving_review_count':True,'require_code_owner_review':False},
    {'required_approving_review_count':0},
])
def test_native_rules_review_minima_cannot_be_defaulted_from_partial_rows(params):
    rules=rules_fixture()+[{'type':'pull_request','parameters':params}]
    with pytest.raises(authority.AuthorityContractError):
        authority.native_protection_contract(rules,repository_id=42,protected_source_sha='6'*40)


def test_native_final_policy_read_surface_is_exact_same_origin_source_only():
    from scripts import resolve_ci_pr_admission as resolver
    prefix=resolver.mog.GITHUB_API+'/repos/mastermindx-market-intelligence/Mastermind/'
    assert resolver._native_policy_read_url(prefix+'branches/master')
    for name in ('policy','source','dispatch'):
        assert resolver._native_policy_read_url(prefix+'contents/control_plane/github_review_risk_'+name+'.py?ref='+'a'*40)
    for path in ('branches/master/protection','branches/main',
                 'contents/control_plane/github_review_risk_policy.py?ref=master',
                 'contents/control_plane/github_review_risk_policy.py?ref='+'a'*40+'&other=1',
                 'contents/control_plane/packet_gate.py?ref='+'a'*40):
        assert not resolver._native_policy_read_url(prefix+path)
    assert not resolver._native_policy_read_url(prefix.replace('Mastermind/','outsider/')+'branches/master')
    assert not resolver._native_policy_read_url('https://alternate.invalid/'+prefix+'branches/master')


def test_native_zero_review_policy_needs_no_irrelevant_contributor_mappings():
    args=authorization_fixture();policy=args['review_policy']
    for kind in ('independent_assessments','formal_non_author_approvals'):
        policy['required_'+kind]=policy['accepted_'+kind]=0
    policy['native_review_decision_required']=False
    policy.pop('source_contributors');policy['qualifying_reviewer_logins']=[]
    args['reviews']=[];args['review_decision']=None
    authority.native_release_authorization(**args)
    args['review_decision']='REVIEW_REQUIRED'
    with pytest.raises(authority.AuthorityContractError):authority.native_release_authorization(**args)


@pytest.mark.parametrize('field,value',[
    ('disposition','ADVISORY'),('origin','ATTENDED'),('repository','other/repo'),
    ('head_sha','f'*40),('target_ref','main'),('pull_number',True),
    ('required_independent_assessments',True),('accepted_independent_assessments',0),
    ('native_review_decision_required',None),
])
def test_native_policy_result_cannot_be_missing_or_relabelled(field,value):
    args=authorization_fixture();args['review_policy'][field]=value
    with pytest.raises(authority.AuthorityContractError):authority.native_release_authorization(**args)


@pytest.mark.parametrize('case',['qualified','classic_admin_path','foreign_path','canonical_403'])
def test_native_current_release_supplies_same_read_facts_without_admin_or_zero_review_ancestry(monkeypatch,case):
    """Caller integration only; supplier tests qualify the real policy engine."""
    import sys,types
    from scripts import merge_on_green as mog
    protection,row,group=review_facts_fixture()
    protection['required_formal_approvals']=0
    protection['review_decision_required']=False
    row['baseRef']['branchProtectionRule']=None;row['reviewDecision']=None
    row.update(id='PR_7',state='OPEN',isDraft=False)
    pull=authorization_fixture()['pull'];calls=[];seen={}
    class ReadError(Exception):pass
    def qualify(repository,current,reviews,issuer,*,get,now,native_facts):
        seen.update(native_facts)
        assert repository==REPO and current==pull and reviews==[] and issuer=='issuer'
        assert callable(now)
        if case=='classic_admin_path':get('/repos/'+REPO+'/branches/main/protection')
        if case=='foreign_path':get('/repos/outsider/private/pulls/7')
        assert get('/repos/mastermindx-market-intelligence/Mastermind/branches/master')=={'name':'master'}
        result=authorization_fixture()['review_policy']
        result.update(native_review_decision_required=False,source_contributors=[],qualifying_reviewer_logins=[])
        for kind in ('independent_assessments','formal_non_author_approvals'):
            result['required_'+kind]=result['accepted_'+kind]=0
        return result
    module=types.SimpleNamespace(qualify_native_review=qualify,NativeReviewReadError=ReadError)
    monkeypatch.setitem(sys.modules,'scripts.ci_native_review_policy',module)
    def request(method,url,token,body=None):
        assert token=='fixture';calls.append((method,url))
        if method=='POST':
            assert url==mog.GITHUB_API+'/graphql' and body['query']==authority.NATIVE_PR_RELEASE_QUERY
            return 200,{'data':{'repository':{'nameWithOwner':REPO,'pullRequest':copy.deepcopy(row)}}}
        if url.endswith('/pulls/7'):return 200,copy.deepcopy(pull)
        if '/reviews?' in url:return 200,[]
        if '/events?' in url:return 200,[{'id':1,'event':'labeled','label':{'name':'merge-on-green'},'actor':{'login':'issuer'}}]
        if url.endswith('/collaborators/issuer/permission'):return 200,{'permission':'write'}
        if url==mog.GITHUB_API+'/repos/mastermindx-market-intelligence/Mastermind/branches/master':
            return (403,{'message':'Resource not accessible by integration'}) if case=='canonical_403' else (200,{'name':'master'})
        raise AssertionError(url)
    monkeypatch.setattr(mog,'_request',request)
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[])
    monkeypatch.setattr(mog,'head_check_runs',lambda *a,**k:[{'name':'ci-gate','status':'completed','conclusion':'success'}])
    if case=='qualified':
        assert mog.native_current_release(REPO,'fixture',group,protection=protection)['node_id']=='PR_7'
    else:
        with pytest.raises(ReadError if case=='canonical_403' else ValueError):
            mog.native_current_release(REPO,'fixture',group,protection=protection)
    assert seen['head_sha']==SOURCE and seen['required_formal_approvals']==0
    assert not any('/commits' in u or '/protection' in u or '/outsider/' in u for _,u in calls)
    assert sum(u.endswith('/pulls/7') for _,u in calls)==(2 if case=='qualified' else 1)


@pytest.mark.parametrize('kind',['rules_last_push','classic_review'])
def test_native_zero_numeric_count_does_not_clear_actual_review_requirement(kind):
    rules=rules_fixture()
    if kind=='rules_last_push':rules.append({'type':'pull_request','parameters':{
        'required_approving_review_count':0,'require_code_owner_review':False,'require_last_push_approval':True}})
    protection=authority.native_protection_contract(rules,repository_id=42,protected_source_sha='6'*40)
    _,row,group=review_facts_fixture()
    row['baseRef']['branchProtectionRule']=None if kind=='rules_last_push' else {
        'requiresApprovingReviews':True,'requiredApprovingReviewCount':0,'requiresCodeOwnerReviews':False}
    row['reviewDecision']=None
    with pytest.raises(authority.AuthorityContractError):authority.native_review_facts(protection,row,repository=REPO,group=group)
    row['reviewDecision']='APPROVED'
    result=authority.native_review_facts(protection,row,repository=REPO,group=group)
    assert result['required_formal_approvals']==0 and result['review_decision_required'] is True


def app_intent_provider(monkeypatch,case='qualified'):
    from scripts import merge_on_green as mog
    from scripts import ci_proof_admission as receipt
    ctx=producer_fixture();pull=ctx['pull'];pull['body']=producer_pointer()
    group=dict(pr_number=7,source_head_sha=SOURCE,target_ref=TARGET)
    event=dict(id=81,event='labeled',label={'name':'merge-on-green'},
        actor={'id':41898282,'login':'github-actions[bot]','type':'Bot'},
        performed_via_github_app={'id':777,'slug':'github-actions'})
    events=[event]
    if case=='withdrawn':events.append({**event,'id':82,'event':'unlabeled'})
    if case=='relabelled':events.extend([{**event,'id':82,'event':'unlabeled'},{**event,'id':83}])
    if case=='no_app':event.pop('performed_via_github_app')
    if case=='foreign_app':event['performed_via_github_app']['id']=778
    if case=='wrong_actor':event['actor']['id']=999
    if case=='changed_head':group['source_head_sha']='f'*40
    calls=[];origin_calls=[]
    def origin_reader(repo,token,current,*,repository_id,protected_controller_sha,require_queue_intent=False):
        # The immutable supplier publishing/readback implementation is still
        # pending. This stub models that specific postcondition, not App-name
        # authority; the real codec/archive/tuple verifier is exercised below.
        origin_calls.append(require_queue_intent)
        assert require_queue_intent is True
        if case in {'hint_only','candidate_source'}:
            raise ValueError('protected queue-intent postcondition unavailable')
        return receipt.authenticate_producer_origin(**ctx)
    monkeypatch.setattr(mog,'authenticated_producer_origin',origin_reader)
    monkeypatch.setattr(mog,'_migration_control_ancestor',lambda *a:None)
    def request(method,url,token,body=None):
        assert method=='GET' and token=='fixture' and body is None
        calls.append(url)
        if url.endswith('/branches/main'):
            sha='5'*40 if case=='main_moved' and sum(u.endswith('/branches/main') for u in calls)>1 else '6'*40
            return 200,{'name':'main','protected':True,'commit':{'sha':sha}}
        if url.endswith('/actions/runs/41'):
            row={**ctx['producer_run'],'check_suite_id':33}
            if case=='changed_attempt':row['run_attempt']=2
            return 200,row
        if url.endswith('/check-suites/33'):
            if case=='missing_suite':return 404,{}
            return 200,{'id':33,'head_sha':'6'*40,'repository':{'id':42},'app':{'id':777,'slug':'github-actions'}}
        raise AssertionError(url)
    monkeypatch.setattr(mog,'_request',request)
    protection=authority.native_protection_contract(rules_fixture(),repository_id=42,protected_source_sha='6'*40)
    return mog,pull,group,events,protection,calls,origin_calls


def test_producer_origin_source_proof_then_app_intent_does_not_require_human_collaborator_role(monkeypatch):
    import sys,types
    mog,pull,group,events,protection,calls,origin_calls=app_intent_provider(monkeypatch)
    pull.update(merged=False,draft=False,title='source change',labels=[{'name':'merge-on-green'}])
    original=mog._request
    def request(method,url,token,body=None):
        if method=='POST':
            calls.append(url)
            assert url==mog.GITHUB_API+'/graphql' and body['query']==authority.NATIVE_PR_RELEASE_QUERY
            row=dict(id='PR_7',number=7,state='OPEN',isDraft=False,headRefOid=SOURCE,
                baseRefName=TARGET,reviewDecision='APPROVED',baseRef={'name':TARGET,'branchProtectionRule':None})
            return 200,{'data':{'repository':{'nameWithOwner':REPO,'pullRequest':row}}}
        if url.endswith('/pulls/7'):
            calls.append(url);return 200,copy.deepcopy(pull)
        if '/reviews?' in url:
            calls.append(url);return 200,authorization_fixture()['reviews']
        if '/events?' in url:
            calls.append(url);return 200,copy.deepcopy(events)
        return original(method,url,token,body)
    monkeypatch.setattr(mog,'_request',request)
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[])
    monkeypatch.setattr(mog,'head_check_runs',lambda *a,**k:[{'name':'ci-gate','status':'completed','conclusion':'success'}])
    def qualify(repository,current,reviews,issuer,*,get,now,native_facts):
        # Actual canonical adapter is a separate supplier qualification. This
        # join case keeps its exact typed boundary visible, not a fake review.
        assert issuer=='github-actions[bot]' and current==pull
        assert native_facts['head_sha']==SOURCE and native_facts['native_enforcement_qualified'] is True
        return authorization_fixture()['review_policy']
    monkeypatch.setitem(sys.modules,'scripts.ci_native_review_policy',types.SimpleNamespace(
        qualify_native_review=qualify,NativeReviewReadError=ValueError))
    release=mog.native_current_release(REPO,'fixture',group,protection=protection)
    assert release['node_id']=='PR_7' and release['issuer']=='github-actions[bot]'
    assert origin_calls==[True]
    old=legacy_helpers();plan=old._plan();plan['subject_head_sha']=SOURCE
    plan['plan_sha256']=proof.authoritative_plan_sha256(plan)
    evidence=proof.reconcile_evidence(plan,[old._fragment(plan=plan)])
    loaded=proof.load_semantic_evidence(evidence,advertised=True)
    authority.native_source_entry_qualification(loaded,expected_head_sha=SOURCE,protection=protection)
    assert not any('/collaborators/' in u for u in calls)
    assert sum('/events?' in u for u in calls)==2  # current original opt-in re-fence
    # The already-clear source proof never substitutes for integrated group proof.
    with pytest.raises(proof.SemanticProofError):
        proof.load_semantic_evidence(evidence,advertised=True,expected_role='merge_group')


@pytest.mark.parametrize('case',['withdrawn','relabelled','no_app','foreign_app','wrong_actor',
    'changed_head','hint_only','candidate_source','changed_attempt','missing_suite','main_moved'])
def test_app_issuer_never_promotes_bot_name_or_old_hint_to_current_intent(monkeypatch,case):
    mog,pull,group,events,protection,calls,origin_calls=app_intent_provider(monkeypatch,case)
    with pytest.raises(ValueError):mog.native_producer_intent(REPO,'fixture',pull,group,events,protection=protection)
    assert not any('/collaborators/' in u for u in calls)
    assert len(calls)<=4


def test_existing_source_hint_reader_cannot_claim_queue_intent_before_supplier_postcondition(monkeypatch):
    mog,ctx,calls=producer_reader_provider(monkeypatch)
    with pytest.raises(ValueError,match='queue-intent postcondition not yet qualified'):
        mog.authenticated_producer_origin(REPO,'fixture',ctx['pull'],repository_id=42,
            protected_controller_sha='6'*40,require_queue_intent=True)


@pytest.mark.parametrize('permission',[None,'write'])
def test_native_final_original_check_reads_require_only_read_permission(permission):
    import yaml
    from scripts import merge_on_green as mog
    root=Path(__file__).resolve().parents[1]
    ci=yaml.safe_load((root/'.github/workflows/ci.yml').read_text())
    executor=yaml.safe_load((root/'.github/workflows/trusted-ci-executor.yml').read_text())
    assert ci['jobs']['ci-gate']['permissions']['checks']=='read'
    assert mog.native_dispatch_source_ready(REPO,ci,executor)
    if permission is None:ci['jobs']['ci-gate']['permissions'].pop('checks')
    else:ci['jobs']['ci-gate']['permissions']['checks']=permission
    assert not mog.native_dispatch_source_ready(REPO,ci,executor)


@pytest.mark.parametrize('risk,review_count',[('fast',0),('standard',1),('critical',2)])
def test_real_policy_adapter_joins_authenticated_app_intent_and_original_source_proof(monkeypatch,risk,review_count):
    from tests import test_ci_native_review_policy as pf
    from scripts import ci_native_review_policy as policy
    mog,pull,group,events,protection,calls,origin_calls=app_intent_provider(monkeypatch)
    pull.update(merged=False,draft=False,title='source change',labels=[{'name':'merge-on-green'}],
        additions=1 if risk=='fast' else 5 if risk=='standard' else 3,
        deletions=0 if risk=='fast' else 2 if risk=='standard' else 1,changed_files=1,commits=1)
    pull['head']['ref']='producer/source';pull['base']['sha']=BASE
    reviews=[]
    for index in range(review_count):
        row=pf.review(index+1,login='independent'+str(index))
        row['commit_id']=SOURCE;row['pull_request_url']='https://api.github.com/repos/'+REPO+'/pulls/7'
        reviews.append(row)
    files={'fast':pf.fast_files,'standard':pf.standard_files,'critical':pf.critical_files}[risk]()
    shim=pf.FakeGitHub(pf._BASELINE_REF,files_pages=files,final_pull=pull,
        commits_pages=pf.commits_pages(logins=('github-actions[bot]',)) if review_count else None)
    original=mog._request
    def request(method,url,token,body=None):
        if method=='POST':
            calls.append(url)
            assert url==mog.GITHUB_API+'/graphql' and body['query']==authority.NATIVE_PR_RELEASE_QUERY
            row=dict(id='PR_7',number=7,state='OPEN',isDraft=False,headRefOid=SOURCE,
                baseRefName=TARGET,reviewDecision=None,baseRef={'name':TARGET,'branchProtectionRule':None})
            return 200,{'data':{'repository':{'nameWithOwner':REPO,'pullRequest':row}}}
        if url.endswith('/pulls/7'):
            calls.append(url);return 200,copy.deepcopy(pull)
        if '/reviews?' in url:
            calls.append(url);return 200,copy.deepcopy(reviews)
        if '/events?' in url:
            calls.append(url);return 200,copy.deepcopy(events)
        if '/Mastermind/' in url or '/files?' in url or '/commits?' in url:
            calls.append(url)
            # Reuse exact supplier source bytes/provider fixtures; only its test
            # PR number is translated. Real caller requests retain actual 7.
            return shim._response(url.removeprefix(mog.GITHUB_API).replace('/pulls/7/','/pulls/4100/'))
        return original(method,url,token,body)
    monkeypatch.setattr(mog,'_request',request)
    monkeypatch.setattr(mog,'fetch_issue_comments',lambda *a,**k:[])
    monkeypatch.setattr(mog,'head_check_runs',lambda *a,**k:[{'name':'ci-gate','status':'completed','conclusion':'success'}])
    # Do not stub/replace the supplied canonical policy engine or its isolated
    # child. Only the pending publisher source postcondition remains modeled.
    assert policy.qualify_native_review.__module__=='scripts.ci_native_review_policy'
    release=mog.native_current_release(REPO,'fixture',group,protection=protection)
    assert release['issuer']=='github-actions[bot]' and release['node_id']=='PR_7'
    assert origin_calls==[True]
    assert any('/commits?' in u for u in calls) is bool(review_count)
    assert not any('/collaborators/' in u or '/protection' in u for u in calls)
    old=legacy_helpers();plan=old._plan();plan['subject_head_sha']=SOURCE
    plan['plan_sha256']=proof.authoritative_plan_sha256(plan)
    evidence=proof.reconcile_evidence(plan,[old._fragment(plan=plan)])
    authority.native_source_entry_qualification(proof.load_semantic_evidence(evidence,advertised=True),
        expected_head_sha=SOURCE,protection=protection)

# Native queue creation must use the existing event-generating user credential,
# independently of producer-origin proof and the legacy job-token fallback.
def _native_issuer_provider(monkeypatch, *, user=None, repository=None, status=200):
    from scripts import merge_on_green as mog
    calls=[]
    user={'id':123,'login':'native-issuer','type':'User'} if user is None else user
    repository={'id':42,'full_name':REPO,'permissions':{'push':True}} if repository is None else repository
    def request(method,url,token,body=None,**kwargs):
        calls.append((method,url,token))
        assert method=='GET' and token=='existing-pat'
        if url==mog.GITHUB_API+'/user':return status,user
        assert url==mog.GITHUB_API+'/repos/'+REPO
        return status,repository
    monkeypatch.setattr(mog,'_request',request)
    return calls

def test_native_enqueue_actual_user_credential_qualification(monkeypatch):
    from scripts import merge_on_green as mog
    calls=_native_issuer_provider(monkeypatch)
    expected={'repository_id':42,'issuer_id':123,'issuer_login':'native-issuer'}
    assert mog.native_enqueue_issuer(REPO,'job-token','existing-pat',repository_id=42)==expected
    assert mog.native_enqueue_issuer(REPO,'job-token','existing-pat',repository_id=42,expected=expected)==expected
    assert len(calls)==4

@pytest.mark.parametrize('case',['missing','job_token','bot','boolean_id','wrong_repo','wrong_id','no_push','unknown','changed_user','changed_login','missing_expected_field'])
def test_native_enqueue_issuer_refuses_fallback_and_ambiguous_identity(monkeypatch,case):
    from scripts import merge_on_green as mog
    user={'id':123,'login':'native-issuer','type':'User'}
    repository={'id':42,'full_name':REPO,'permissions':{'push':True}}
    expected={'repository_id':42,'issuer_id':123,'issuer_login':'native-issuer'}
    token='existing-pat';status=200
    if case=='missing':token=''
    if case=='job_token':token='job-token'
    if case=='bot':user.update(type='Bot',login='github-actions[bot]')
    if case=='boolean_id':user['id']=True
    if case=='wrong_repo':repository['full_name']='outsider/macro'
    if case=='wrong_id':repository['id']=43
    if case=='no_push':repository['permissions']['push']=False
    if case=='unknown':status=403
    if case=='changed_user':expected['issuer_id']=999
    if case=='changed_login':expected['issuer_login']='different-user'
    if case=='missing_expected_field':expected.pop('issuer_id')
    calls=_native_issuer_provider(monkeypatch,user=user,repository=repository,status=status)
    with pytest.raises(ValueError):
        mog.native_enqueue_issuer(REPO,'job-token',token,repository_id=42,expected=expected)
    if case in ('missing','job_token'):assert calls==[]

@pytest.mark.parametrize('boundary',['reserve','enqueue'])
def test_native_missing_event_issuer_prevents_original_mutations(monkeypatch,boundary):
    from scripts import merge_on_green as mog
    from scripts import ci_proof_admission as c
    monkeypatch.setattr(mog,'_shared_controller_authority',lambda *a,**k:True)
    mutations=[]
    monkeypatch.setattr(mog,'_shared_admission_effect',lambda *a,**k:mutations.append(a))
    monkeypatch.setattr(mog,'_request',lambda *a,**k:pytest.fail('missing issuer must refuse before provider reads'))
    context=dict(repository_id=42,protected_controller_sha='6'*40,current_run_id='9',current_run_attempt=1)
    if boundary=='reserve':
        result=mog.reserve_shared_admission(REPO,'job-token','job-token',c.Demand(7,SOURCE,'refresh','2026-11-05T00:00:00+00:00','a'*12),native_target=TARGET,**context)
    else:
        result=mog.enqueue_native_admission(REPO,'job-token','job-token',{'controller_run_id':9,'controller_attempt':1},**context)
    assert result.disposition=='held' and mutations==[]

def test_native_workflow_credential_is_separate_without_fallback():
    import yaml
    root=Path(__file__).resolve().parents[1]
    doc=yaml.safe_load((root/'.github/workflows/merge-on-green.yml').read_text())
    stages={step.get('run','').split()[-1]:step for job in doc['jobs'].values() for step in job.get('steps',[])
            if 'python3 -I scripts/ci_admission_stages.py ' in step.get('run','')}
    for name in ('reserve','dispatch'):
        assert stages[name]['env']['NATIVE_ENQUEUE_TOKEN']=='${{ secrets.ADMIN_GH_TOKEN }}'
        assert stages[name]['env']['MERGE_TOKEN']=='${{ secrets.ADMIN_GH_TOKEN || secrets.GITHUB_TOKEN }}'

@pytest.mark.parametrize('case',['positive','changed_principal','read_failure','expiry','lost_enqueue'])
def test_native_original_enqueue_uses_qualified_issuer_without_retry(monkeypatch,case):
    from scripts import merge_on_green as mog
    from scripts import ci_proof_admission as c
    from types import SimpleNamespace
    admitted=c.NativeAdmission('a'*12,7,SOURCE,BASE,'5'*40,'6'*40,target_ref=TARGET,tree_sha=TREE)
    expected={'repository_id':42,'issuer_id':123,'issuer_login':'native-issuer'}
    state={'register':'a2 p=7 g='+admitted.generation+' s=prepared r=10','users':0,'effects':[]}
    monkeypatch.setattr(mog,'_shared_controller_authority',lambda *a,**k:True)
    monkeypatch.setattr(mog,'authenticated_admission_from_ref',lambda *a,**k:admitted)
    monkeypatch.setattr(mog,'native_target_protection',lambda *a,**k:{'protected_source_sha':'6'*40})
    monkeypatch.setattr(mog,'shared_proof_workload',lambda *a,**k:mog.SharedProofWorkload(True,(),(admitted,)))
    monkeypatch.setattr(mog,'native_empty_target',lambda *a,**k:None)
    monkeypatch.setattr(mog,'native_current_release',lambda *a,**k:{'pull':{'base':{'sha':BASE},'merge_commit_sha':'5'*40},'checks':[],'node_id':'PR_7'})
    monkeypatch.setattr(mog,'semantic_evidence_for_head',lambda *a,**k:object())
    monkeypatch.setattr(authority,'native_source_entry_qualification',lambda *a,**k:None)
    monkeypatch.setattr(mog,'authenticated_migration_root',lambda *a,**k:10)
    def request(method,url,token,body=None):
        assert method=='GET'
        if url==mog.GITHUB_API+'/user':
            assert token=='existing-pat';state['users']+=1
            if state['users']==2 and case=='read_failure':return 503,{}
            return 200,{'id':999 if state['users']==2 and case=='changed_principal' else 123,'login':'native-issuer','type':'User'}
        if url==mog.GITHUB_API+'/repos/'+REPO:
            assert token=='existing-pat';return 200,{'id':42,'full_name':REPO,'permissions':{'push':True}}
        assert '/labels/' in url and token=='job-token'
        return 200,{'description':state['register']}
    def effect(method,url,token,body):
        state['effects'].append((method,token))
        if method=='PATCH':
            assert token=='legacy-write';state['register']=body['description'];return 200,{}
        assert method=='POST' and url==mog.GITHUB_API+'/graphql' and token=='existing-pat'
        assert body['variables']['input']=={'pullRequestId':'PR_7','expectedHeadOid':SOURCE,'jump':False}
        if case=='lost_enqueue':raise TimeoutError('test-owned lost response')
        return 200,{'data':{'enqueuePullRequest':{'mergeQueueEntry':{'id':'MQE_original','position':1}}}}
    monkeypatch.setattr(mog,'_request',request);monkeypatch.setattr(mog,'_shared_admission_effect',effect)
    scope=SimpleNamespace(require_budget=lambda:SimpleNamespace(deadline=mog.time.time()+(10 if case=='expiry' else 500)))
    slot=mog._MIGRATION_READ_SCOPE.set(scope)
    try:
        result=mog.enqueue_native_admission(REPO,'job-token','legacy-write',{'controller_run_id':9,'controller_attempt':1},repository_id=42,protected_controller_sha='6'*40,current_run_id='9',current_run_attempt=1,native_enqueue_token='existing-pat',expected_issuer=expected)
    finally:mog._MIGRATION_READ_SCOPE.reset(slot)
    if case=='positive':
        assert result.disposition=='queued' and result.admission.queue_entry_id=='MQE_original'
        assert state['effects']==[('PATCH','legacy-write'),('POST','existing-pat')]
    elif case=='expiry':assert result.disposition=='held' and state['effects']==[]
    else:
        assert result.disposition=='unknown' and 's=started' in state['register']
        assert state['effects']==([('PATCH','legacy-write'),('POST','existing-pat')] if case=='lost_enqueue' else [('PATCH','legacy-write')])

@pytest.mark.parametrize('case',['same_original','missing','changed_context','changed_generation'])
def test_native_stage_dispatch_conserves_original_public_issuer_binding(tmp_path,monkeypatch,case):
    from scripts import ci_admission_stages as stages
    from scripts import merge_on_green as mog
    from scripts import ci_proof_admission as c
    from types import SimpleNamespace
    admitted=c.NativeAdmission('a'*12,7,SOURCE,BASE,'5'*40,'6'*40,target_ref=TARGET,tree_sha=TREE)
    context=dict(repository_id=42,protected_controller_sha='6'*40,current_run_id='9',current_run_attempt=1)
    instance=stages.Stages(REPO,'job-token','legacy-write','',context,tmp_path,native_enqueue_token='existing-pat')
    monkeypatch.setattr(instance,'authority',lambda:None)
    monkeypatch.setattr(instance,'reference',lambda *a:{})
    monkeypatch.setattr(instance,'index',lambda *a:None)
    monkeypatch.setattr(instance,'receipt',lambda *a:None)
    monkeypatch.setattr(instance,'emit_decision',lambda *a,**k:None)
    monkeypatch.setattr(mog,'authenticated_checkpoint_from_ref',lambda *a,**k:SimpleNamespace(pr_number=7))
    monkeypatch.setattr(mog,'publish_prepared_shared_admission',lambda *a,**k:mog.AdmissionDispatchResult('indexed',admitted))
    expected={'repository_id':42,'issuer_id':123,'issuer_login':'native-issuer'}
    binding=dict(context=dict(context),generation=admitted.generation,issuer=expected)
    if case=='changed_context':binding['context']['current_run_id']='10'
    if case=='changed_generation':binding['generation']='b'*12
    if case!='missing':instance.save('native-issuer',binding)
    calls=[]
    def enqueue(*a,**k):
        calls.append(k)
        assert k['native_enqueue_token']=='existing-pat' and k['expected_issuer']==expected
        return mog.AdmissionDispatchResult('queued',c.bind_native_entry(admitted,'MQE_original'))
    monkeypatch.setattr(mog,'enqueue_native_admission',enqueue)
    if case=='same_original':
        result=stages.Stages.dispatch.__wrapped__(instance,1,2)
        assert result['bound'] is True and result['receipt_suffix']=='native-queued' and len(calls)==1
        assert 'existing-pat' not in (tmp_path/'native-issuer.json').read_text()
    else:
        with pytest.raises((ValueError,FileNotFoundError)):stages.Stages.dispatch.__wrapped__(instance,1,2)
        assert calls==[]

@pytest.mark.parametrize('stage',['reserve','dispatch'])
@pytest.mark.parametrize('replacement',[None,'${{ secrets.GITHUB_TOKEN }}','${{ secrets.ADMIN_GH_TOKEN || secrets.GITHUB_TOKEN }}'])
def test_runner_policy_refuses_native_enqueue_fallback_or_missing_binding(stage,replacement):
    import yaml
    from scripts import check_runner_policy as policy
    document=yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows/merge-on-green.yml').read_text())
    assert policy._shared_admission_controller_r2_findings('.github/workflows/merge-on-green.yml',copy.deepcopy(document))==[]
    step=next(s for job in document['jobs'].values() for s in job.get('steps',[]) if s.get('run')=='python3 -I scripts/ci_admission_stages.py '+stage)
    if replacement is None:step['env'].pop('NATIVE_ENQUEUE_TOKEN')
    else:step['env']['NATIVE_ENQUEUE_TOKEN']=replacement
    assert policy._shared_admission_controller_r2_findings('.github/workflows/merge-on-green.yml',document)
