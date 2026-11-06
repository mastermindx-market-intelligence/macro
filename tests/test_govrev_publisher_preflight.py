from pathlib import Path
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import time
import zipfile
import pytest
import yaml

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'scripts/ci'))
import govrev_publisher_preflight as pre
import govrev_candidate_proof as proof

SOURCES={p:'a'*64 for p in pre.SOURCE_PATHS}
CURRENT={'run_id':10,'run_attempt':1,'job_id':100,'started_at':'2026-10-13T06:00:00Z','created_at':'2026-10-13T05:00:00Z'}
BASELINE={'contract':'government_revenue.publisher_recovery_baseline.v1','repository':pre.REPOSITORY,
          'families':pre.FAMILIES,'source_closure':SOURCES,'scan_created_after':'2026-10-13T00:00:00Z',
          'legacy_effects_reconciled_at':'2026-10-12T23:59:00Z','legacy_census_complete':True,
          'legacy_census_evidence_sha256':'b'*64,'reconciled_legacy_operations':[
              {'run_id':1,'run_attempt':1,'disposition':'no_publication_effect','evidence_sha256':'c'*64,
               'operation_scope':'govrev_publisher','publisher_job_id':10,'publisher_job_name':'refresh',
               'workflow_path':'.github/workflows/government-revenue-live.yml'}]}


def record(run_id=9,family='government-revenue-live.yml',step=True):
    return {'run_id':run_id,'run_attempt':1,'job_id':run_id*10,'workflow_path':'.github/workflows/'+family,
            'created_at':'2026-10-13T01:00:00Z','started_at':'2026-10-13T02:00:00Z',
            'steps':[{'name':pre.STEP_NAME}] if step else [],'expected_source_closure':SOURCES,
            'publisher_job_name':pre.FAMILIES[family]}


def casefiles(r):
    case={'contract':'government_revenue.publisher_run_case.v1','repository':pre.REPOSITORY,
          **{k:r[k] for k in ('run_id','run_attempt','job_id','workflow_path')},
          'phase':'preflight_passed_before_effect','source_closure':SOURCES,'checkout_commit':'a'*40}
    return {pre.CASE:json.dumps(case).encode()}


class Fake:
    def __init__(self, records, files=None):
        self.records=records;self.files=files or {};self.deadline=time.monotonic()+180
        self.reads=[]
    def json(self,path):
        self.reads.append(path)
        if path.startswith('actions/workflows/'):
            family=path.split('/')[2]
            return {'workflow_runs':[{'id':r['run_id'],'run_attempt':r['run_attempt'],
                'created_at':r['created_at'],'status':'completed','path':r['workflow_path']}
                for r in self.records if Path(r['workflow_path']).name==family]}
        run_id=int(path.split('/')[2])
        attempt=int(path.split('/')[4])
        return {'total_count':1,'jobs':[{'id':r['job_id'],'name':pre.FAMILIES[Path(r['workflow_path']).name],
            'started_at':r['started_at'],'status':'completed','steps':r['steps']}
            for r in self.records if r['run_id']==run_id and r['run_attempt']==attempt]}
    def archive(self,run_id,attempt):
        key=(run_id,attempt)
        if key not in self.files:raise pre.Refused('required_retained_artifact_missing_or_expired')
        return self.files[key],{'artifact_id':run_id,'archive_sha256':'d'*64}


def test_empty_first_epoch_requires_reviewed_baseline_and_writes_checkpoint(tmp_path):
    api=Fake([])
    result=pre.preflight(tmp_path,tmp_path,api,BASELINE,CURRENT)
    assert result['conclusion']=='passed'
    assert result['issuance_authority'] is False
    assert set(p.split('/')[2] for p in api.reads if p.startswith('actions/workflows/'))==set(pre.FAMILIES)
    assert json.loads((tmp_path/pre.CHECKPOINT).read_text())==result


@pytest.mark.parametrize('family',list(pre.FAMILIES))
def test_existing_three_family_missing_required_artifact_freezes(tmp_path,family):
    r=record(family=family)
    with pytest.raises(pre.Refused,match='missing_or_expired'):
        pre.preflight(tmp_path,tmp_path,Fake([r]),BASELINE,CURRENT)
    assert not (tmp_path/pre.CHECKPOINT).exists()


def test_unlisted_legacy_effect_cannot_silently_pass(tmp_path):
    r=record(step=False)
    with pytest.raises(pre.Refused,match='legacy_effect_not_in_reviewed_census'):
        pre.preflight(tmp_path,tmp_path,Fake([r]),BASELINE,CURRENT)
    r=record(run_id=1,step=False)
    result=pre.preflight(tmp_path,tmp_path,Fake([r]),BASELINE,CURRENT)
    assert result['checked_operations'][0]['explicit_reviewed_disposition']['evidence_sha256']=='c'*64


@pytest.mark.parametrize('field,value',[('repository','other/repo'),('run_attempt',2),('job_id',999),('phase','fabricated'),('source_closure',{})])
def test_retained_case_exact_owner_and_source_are_required(field,value):
    r=record();files=casefiles(r);case=json.loads(files[pre.CASE]);case[field]=value;files[pre.CASE]=json.dumps(case).encode()
    with pytest.raises(pre.Refused):pre.load_case(files,r)


def test_complete_before_push_case_proves_no_push_effect(tmp_path):
    r=record();files=casefiles(r)
    result=pre.reconcile_record(tmp_path,files,r,tmp_path)
    assert result['disposition']=='no_push_identity_no_push_effect'
    checkpoint=pre.preflight(tmp_path,tmp_path,Fake([r],{(9,1):files}),BASELINE,CURRENT)
    assert checkpoint['checked_operations'][0]['run_id']==9


def test_prior_checkpoint_cannot_forge_future_coverage(tmp_path):
    r=record();files=casefiles(r)
    cp={'contract':'government_revenue.publisher_preflight.v1','conclusion':'passed','repository':pre.REPOSITORY,
        'run_id':9,'run_attempt':1,'baseline_sha256':pre.digest(proof._canonical(BASELINE).encode()),
        'covered_before_started_at':'2099-01-01T00:00:00Z','next_created_scan_floor':r['created_at']}
    files[pre.CHECKPOINT]=json.dumps(cp).encode()
    with pytest.raises(pre.Refused,match='checkpoint_not_qualified'):
        pre.preflight(tmp_path,tmp_path,Fake([r],{(9,1):files}),BASELINE,CURRENT)


def test_archive_duplicate_or_symlink_refuses_before_any_effect():
    for kind in ('duplicate','symlink','nested'):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:
            if kind=='duplicate':
                archive.writestr(pre.CASE,b'one');archive.writestr(pre.CASE,b'two')
            elif kind=='nested':archive.writestr('nested/'+pre.CASE,b'body')
            else:
                info=zipfile.ZipInfo(pre.CASE);info.external_attr=(0o120777<<16);archive.writestr(info,b'target')
        with pytest.raises(pre.Refused):pre.unpack(out.getvalue())


def test_baseline_requires_actual_current_source_and_legacy_evidence(tmp_path):
    for relative in pre.SOURCE_PATHS:
        p=tmp_path/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(relative)
    path=tmp_path/pre.BASELINE;path.parent.mkdir(parents=True)
    baseline=copy.deepcopy(BASELINE);baseline['source_closure']=pre.source_closure(tmp_path)
    path.write_text(json.dumps(baseline));assert pre.read_baseline(tmp_path)==baseline
    baseline['legacy_census_complete']=False;path.write_text(json.dumps(baseline))
    with pytest.raises(pre.Refused):pre.read_baseline(tmp_path)
    baseline['legacy_census_complete']=True;baseline['reconciled_legacy_operations']=[];path.write_text(json.dumps(baseline))
    with pytest.raises(pre.Refused):pre.read_baseline(tmp_path)


def test_fms_persistence_helper_drift_invalidates_publisher_baseline(tmp_path):
    assert 'scripts/ci/fms_persist.py' in pre.SOURCE_PATHS
    for relative in pre.SOURCE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative)
    baseline = copy.deepcopy(BASELINE)
    baseline['source_closure'] = pre.source_closure(tmp_path)
    path = tmp_path / pre.BASELINE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(baseline))
    assert pre.read_baseline(tmp_path) == baseline
    (tmp_path / 'scripts/ci/fms_persist.py').write_text('unqualified persistence change')
    with pytest.raises(pre.Refused, match='baseline_source_or_owner_not_qualified'):
        pre.read_baseline(tmp_path)


def test_missing_baseline_records_case_and_refuses_before_effect(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY',pre.REPOSITORY);monkeypatch.setenv('GITHUB_RUN_ID','10');monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1');monkeypatch.setenv('GITHUB_TOKEN','synthetic-unused')
    root=tmp_path/'root';root.mkdir();out=tmp_path/'out'
    assert pre.main(['--root',str(root),'--out-dir',str(out)])==75
    case=json.loads((out/pre.CASE).read_text());assert case['phase']=='preflight_refused_before_effect'
    assert case['run_id']==10
    assert not (out/pre.CHECKPOINT).exists()


def test_rerun_attempt_cannot_start_new_publication(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY',pre.REPOSITORY);monkeypatch.setenv('GITHUB_RUN_ID','10');monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2')
    root=tmp_path/'root';root.mkdir();out=tmp_path/'out'
    assert pre.main(['--root',str(root),'--out-dir',str(out)])==75
    assert json.loads((out/pre.CASE).read_text())['phase']=='preflight_refused_before_effect'


def test_preflight_precedes_builds_and_permissions_only_existing_owners():
    workflow=yaml.safe_load((BASE/'.github/workflows/government-revenue-live.yml').read_text())
    steps=workflow['jobs']['refresh']['steps'];index=next(i for i,s in enumerate(steps) if s.get('name')==pre.STEP_NAME)
    assert index==3
    assert steps[0]['with']['ref']=='${{ github.sha }}'
    assert steps[1]['id']=='source_binding'
    assert steps[2]['with']['ref']=='${{ steps.source_binding.outputs.source_sha }}'
    assert workflow['permissions']['actions']=='read'
    assert all('build_government_revenue' not in s.get('run','') for s in steps[:index])
    daily=yaml.safe_load((BASE/'.github/workflows/daily.yml').read_text())
    assert daily['jobs']['government_revenue_projection']['permissions']['actions']=='read'
    fms=yaml.safe_load((BASE/'.github/workflows/fms-acquire.yml').read_text())
    assert fms['jobs']['publish']['permissions']['actions']=='read'
    commit=next(s['run'] for s in steps if 'commit complete' in s.get('name',''))
    assert len(commit)<=20563
    for s in steps:
        if 'run' in s:
            assert subprocess.run(['/bin/bash','-n'],input=s['run'],text=True,capture_output=True).returncode==0


def gate_fixtures():
    spec=importlib.util.spec_from_file_location('preflight_gate_fixture',BASE/'tests/test_govrev_candidate_proof_gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    return gate


@pytest.mark.parametrize('state',['confirmed','unknown','proof_seal_lost','commit_bytes_wrong','refused'])
def test_actual_prior_sealed_generation_reconciles_before_new_effect(tmp_path,monkeypatch,state):
    gate=gate_fixtures();root=gate._proof_tree(tmp_path)
    remote=tmp_path/'origin.git';subprocess.run(['git','init','--bare','-q',str(remote)],check=True)
    gate._git(root,'remote','add','origin',str(remote));gate._git(root,'push','-q','origin','HEAD:main')
    (root/'README').write_text('candidate publication');gate._git(root,'add','-A');gate._git(root,'commit','-qm','new sealed generation')
    assert gate._prove(root,tmp_path).returncode==0
    monkeypatch.setenv('GITHUB_RUN_ID','9');monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    identity=tmp_path/'identity.json'
    result=gate._run_gate(root,'push-identity','--root',str(root),'--receipt',str(gate._receipt_path(tmp_path)),
        '--attempt','1','--out',str(identity))
    assert result.returncode==0,result.stderr+result.stdout
    r=record();files=casefiles(r)
    files['govrev-candidate-proof.push-1.identity.json']=identity.read_bytes()
    raw=gate._receipt_path(tmp_path).read_bytes();files['govrev-candidate-proof.receipt.json']=raw
    receipt=json.loads(raw)
    for item in receipt['execution_evidence']['artifacts'].values():
        files[item['filename']]=(gate._receipt_path(tmp_path).parent/item['filename']).read_bytes()
    if state!='unknown':gate._git(root,'push','-q','origin','HEAD:main')
    if state=='proof_seal_lost':files.pop(receipt['execution_evidence']['artifacts']['junit']['filename'])
    if state=='refused':files['govrev-candidate-proof.push-1.outcome.json']=json.dumps({'outcome':'refused'}).encode()
    if state=='commit_bytes_wrong':
        # A structurally valid rehashed proof claiming different bytes still cannot match the committed blob.
        receipt['outputs']['data/government_revenue/candidate_queue.json']='e'*64
        receipt['identity']=proof.receipt_identity(receipt);new_raw=(proof._canonical(receipt)+'\n').encode()
        files['govrev-candidate-proof.receipt.json']=new_raw
        changed=json.loads(identity.read_text());changed['proof_receipt_sha256']=pre.digest(new_raw);changed['proof_identity']=receipt['identity']
        changed.pop('identity');changed['identity']=pre.digest(proof._canonical(changed).encode())
        files['govrev-candidate-proof.push-1.identity.json']=json.dumps(changed).encode()
    # Move the new run checkout forward independently; historical observation must still use the old identity.
    (root/'README').write_text('current run checkout');gate._git(root,'add','-A');gate._git(root,'commit','-qm','next source checkout')
    out=tmp_path/'preflight';out.mkdir()
    if state=='confirmed':
        result=pre.reconcile_record(root,files,r,out)
        assert result['pushes'][0]['disposition']=='original_effect_confirmed'
        assert result['pushes'][0]['expected_commit']!=gate._git(root,'rev-parse','HEAD').strip()
    else:
        with pytest.raises((pre.Refused,KeyError)):
            pre.reconcile_record(root,files,r,out)
        assert not (out/pre.CHECKPOINT).exists()


@pytest.mark.parametrize('path',['.github/workflows/daily.yml','.github/workflows/fms-acquire.yml'])
def test_reusable_caller_source_drift_invalidates_proof(tmp_path,path):
    gate=gate_fixtures();root=gate._proof_tree(tmp_path)
    caller=root/path;caller.parent.mkdir(parents=True);caller.write_text('permissions: {actions: read}')
    assert gate._prove(root,tmp_path).returncode==0
    caller.write_text('permissions: {actions: none}')
    result=gate._run_gate(root,'verify','--root',str(root),'--suite','tests/test_proof_gate_suite.py','--receipt',str(gate._receipt_path(tmp_path)))
    assert result.returncode!=0,result.stdout


def test_rolling_checkpoint_preserves_coverage_but_rechecks_its_own_push(tmp_path):
    old=record(run_id=8,step=False);old['started_at']='2026-10-13T00:30:00Z'
    prior=record();files=casefiles(prior)
    cp={'contract':'government_revenue.publisher_preflight.v1','conclusion':'passed','repository':pre.REPOSITORY,
        'run_id':9,'run_attempt':1,'baseline_sha256':pre.digest(proof._canonical(BASELINE).encode()),
        'covered_before_started_at':prior['started_at'],'next_created_scan_floor':BASELINE['scan_created_after'],
        'checked_operations':[{'run_id':8,'disposition':'original_effect_confirmed'}]}
    files[pre.CHECKPOINT]=json.dumps(cp).encode()
    api=Fake([old,prior],{(9,1):files})
    result=pre.preflight(tmp_path,tmp_path,api,BASELINE,CURRENT)
    assert len(result['checked_operations'])==1
    assert result['checked_operations'][0]['run_id']==9
    assert result['previous_checkpoint']['artifact_id']==9
    # The checkpoint is written before that run's own push: losing its later identity/outcome is not inherited success.
    files.pop(pre.CASE)
    with pytest.raises(KeyError):pre.preflight(tmp_path,tmp_path,api,BASELINE,CURRENT)


def test_artifact_redirect_never_forwards_actions_token(monkeypatch):
    import urllib.error
    calls=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'archive'
    class Opener:
        def open(self,request,timeout):
            calls.append((request.full_url,request.get_header('Authorization')))
            if len(calls)==1:
                raise urllib.error.HTTPError(request.full_url,302,'redirect',
                    {'Location':'https://example.blob.core.windows.net/artifact?synthetic-signature'},None)
            return Response()
    monkeypatch.setattr(pre.urllib.request,'build_opener',lambda *args:Opener())
    assert pre.GitHub('synthetic-actions-token').read('https://api.github.com/repos/'+pre.REPOSITORY+'/actions/artifacts/123/zip',redirect=True)==b'archive'
    assert calls[0][1]=='Bearer synthetic-actions-token'
    assert calls[1][1] is None


def test_preflight_deadline_refuses_instead_of_unbounded_scan(tmp_path):
    api=Fake([]);api.deadline=time.monotonic()-1
    with pytest.raises(pre.Refused,match='budget_exhausted'):
        pre.preflight(tmp_path,tmp_path,api,BASELINE,CURRENT)
    assert not (tmp_path/pre.CHECKPOINT).exists()


def test_shallow_new_run_can_only_confirm_original_commit_by_bounded_same_origin_history(tmp_path,monkeypatch):
    gate=gate_fixtures();root=gate._proof_tree(tmp_path)
    remote=tmp_path/'origin.git';subprocess.run(['git','init','--bare','-q',str(remote)],check=True)
    gate._git(root,'remote','add','origin',remote.as_uri())
    assert gate._prove(root,tmp_path).returncode==0
    identity=tmp_path/'identity.json'
    assert gate._run_gate(root,'push-identity','--root',str(root),'--receipt',str(gate._receipt_path(tmp_path)),
        '--attempt','1','--out',str(identity)).returncode==0
    gate._git(root,'push','-q','origin','HEAD:main')
    (root/'README').write_text('later main');gate._git(root,'add','-A');gate._git(root,'commit','-qm','later');gate._git(root,'push','-q','origin','HEAD:main')
    current=tmp_path/'shallow'
    subprocess.run(['git','clone','-q','--depth=1','-b','main',remote.as_uri(),str(current)],check=True)
    assert gate._git(current,'rev-parse','--is-shallow-repository').strip()=='true'
    observation=tmp_path/'observation.json'
    result=gate._run_gate(current,'observe-push','--root',str(current),'--identity',str(identity),
        '--out',str(observation),'--historical')
    assert result.returncode==0,result.stderr+result.stdout
    receipt=json.loads(observation.read_text())
    assert receipt['outcome']=='original_effect_confirmed' and receipt['current_ref_equals_expected'] is False
    assert receipt['serving_generation_authority'] is False


def test_known_contention_first_attempt_does_not_require_later_replaced_proof(tmp_path):
    r=record();files=casefiles(r)
    identity={'expected_commit':'a'*40,'proof_identity':'old-proof','proof_receipt_sha256':'old-replaced-proof',
              'origin_binding_sha256':'b'*64,'run_id':'9','run_attempt':'1','push_attempt':'1'}
    identity['identity']=pre.digest(proof._canonical(identity).encode())
    files['govrev-candidate-proof.push-1.identity.json']=json.dumps(identity).encode()
    files['govrev-candidate-proof.push-1.outcome.json']=json.dumps({'outcome':'definite_contention_rejection'}).encode()
    result=pre.reconcile_record(tmp_path,files,r,tmp_path)
    assert result['pushes'][0]['disposition']=='definite_no_write_rejection'


def test_explicit_reviewed_retirement_can_resolve_missing_prior_artifact(tmp_path):
    r=record(run_id=1)
    result=pre.preflight(tmp_path,tmp_path,Fake([r]),BASELINE,CURRENT)
    assert result['checked_operations'][0]['explicit_reviewed_disposition']['run_id']==1


def test_old_created_pending_caller_is_seen_before_scan_floor(tmp_path):
    class Pending(Fake):
        def json(self,path):
            if path.startswith('actions/workflows/'):
                family=path.split('/')[2]
                if family=='daily.yml' and 'status=in_progress' in path:
                    return {'workflow_runs':[{'id':4,'run_attempt':1,'created_at':'2026-10-11T00:00:00Z',
                        'status':'in_progress','path':'.github/workflows/daily.yml'}]}
                return {'workflow_runs':[]}
            return {'total_count':1,'jobs':[{'id':40,'name':'collect','status':'in_progress'}]}
    records,pending=pre.qualified_records(Pending([]),BASELINE['scan_created_after'],(10,1))
    assert records==[] and pending==['2026-10-11T00:00:00Z']


def test_active_daily_with_authenticated_skipped_govrev_does_not_retire_unrelated_engine(tmp_path):
    class Skipped(Fake):
        def json(self,path):
            if path.startswith('actions/workflows/'):
                family=path.split('/')[2]
                if family=='daily.yml' and 'status=queued' in path:
                    return {'workflow_runs':[{'id':4,'run_attempt':1,'created_at':'2026-10-11T00:00:00Z',
                        'status':'queued','path':'.github/workflows/daily.yml'}]}
                return {'workflow_runs':[]}
            return {'total_count':2,'jobs':[{'id':40,'name':'government_revenue_projection','status':'completed',
                'conclusion':'skipped','steps':[],'started_at':'2026-10-13T04:00:00Z'},
                {'id':41,'name':'engine','status':'in_progress'}]}
    records,pending=pre.qualified_records(Skipped([]),BASELINE['scan_created_after'],(10,1))
    assert len(records)==1 and records[0]['publisher_never_started'] is True
    assert pending==[]
    result=pre.preflight(tmp_path,tmp_path,Skipped([]),BASELINE,CURRENT)
    assert result['checked_operations'][0]['disposition']=='authenticated_publisher_job_skipped_without_steps'


def legacy_fixture(family='government-revenue-live.yml'):
    definition='f'*40;runtime='e'*40
    gov=b'jobs:\n  refresh:\n    steps:\n      - name: commit complete evidence projection\n        run: push_do origin HEAD:main\n'
    def identity(body):
        return {'git_blob_sha':pre.hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest(),
                'sha256':pre.digest(body),'bytes':len(body)}
    deps={p:('inspected:'+p).encode() for p in ('scripts/build_government_revenue.py','scripts/collect.py',
           'scripts/ci/push_retry.sh','collectors/sam_gov.py','collectors/base.py')}
    parent='government_revenue_projection' if family=='daily.yml' else 'publish'
    caller=('jobs:\n  '+parent+':\n    uses: ./.github/workflows/government-revenue-live.yml\n    with:\n      projection_only: true\n').encode()
    entry={'workflow':{'workflow_path':'.github/workflows/government-revenue-live.yml',**identity(gov)},
           'audit_evidence_sha256':'a'*64,'publisher_job_id':'refresh',
           'sole_repository_publication_step_name':'commit complete evidence projection',
           'timestamp_policy':'authenticated_completed_skipped_is_nonexecution',
           'dependency_source_identities':{p:identity(body) for p,body in deps.items()},
           'callers':{family:{'caller_job_id':parent,'exact_uses':'./.github/workflows/government-revenue-live.yml',
                             'caller_job_block_sha256':pre.digest(pre._caller_job_block(caller,parent))}}}
    sources={(definition,'.github/workflows/government-revenue-live.yml'):gov,
             (definition,'.github/workflows/'+family):caller,**{(runtime,p):body for p,body in deps.items()}}
    if family=='government-revenue-live.yml':sources[(definition,'.github/workflows/government-revenue-live.yml')]=gov
    class SourceAPI:
        def __init__(self):self.reads=[];self.sources=sources
        def source_file(self,path,commit):
            self.reads.append(('source',commit,path));body=self.sources[(commit,path)]
            return body,identity(body)
        def read(self,url,redirect=False):
            self.reads.append(('log',url))
            return ('2026-10-13T06:30:01Z ##[command]/usr/bin/git log -1 --format=\'%H\'\n'
                    '2026-10-13T06:30:01Z '+runtime+'\n').encode()
    r=record(family=family);r.update({'workflow_head_sha':definition,'publisher_job_status':'completed',
        'steps':[{'name':'commit complete evidence projection','status':'completed','conclusion':'skipped',
                  'started_at':'2026-10-13T06:30:00Z','completed_at':'2026-10-13T06:30:00Z'}]})
    baseline=copy.deepcopy(BASELINE);baseline['legacy_never_started_workflow_whitelist']=[entry]
    return SourceAPI(),r,baseline


@pytest.mark.parametrize('family',list(pre.FAMILIES))
def test_legacy_exact_audit_and_skipped_step_close_cutover_race_only_for_publisher(family):
    api,r,baseline=legacy_fixture(family)
    result=pre.classify_legacy_never_published(api,r,baseline)
    assert result['disposition']=='authenticated_audited_publication_step_skipped'
    assert result['unrelated_parent_effects_retired'] is False
    assert result['scheduler_clocks_are_execution_evidence'] is False
    assert result['publication_step']['scheduler_started_at']=='2026-10-13T06:30:00Z'
    assert result['runtime_checkout_commit'] != result['workflow_head_sha']
    assert all(call[1]==r['workflow_head_sha'] for call in api.reads if call[0]=='source' and '.github/workflows/' in call[2])


@pytest.mark.parametrize('failure',['begun','failed','unknown','duplicate','missing_step','workflow_drift',
                                    'caller_link','caller_other_commit','runtime_drift','runtime_missing','missing_log','unaudited'])
def test_legacy_cutover_missing_drift_or_begun_effect_is_held(failure):
    api,r,baseline=legacy_fixture('daily.yml')
    if failure in ('begun','failed','unknown'):
        r['steps'][0]['conclusion']={'begun':'success','failed':'failure','unknown':None}[failure]
    elif failure=='duplicate':r['steps'].append(dict(r['steps'][0]))
    elif failure=='missing_step':r['steps']=[]
    elif failure=='workflow_drift':api.sources[(r['workflow_head_sha'],'.github/workflows/government-revenue-live.yml')]=b'drift'
    elif failure=='caller_link':api.sources[(r['workflow_head_sha'],'.github/workflows/daily.yml')]=b'jobs:\n  government_revenue_projection:\n    uses: attacker/workflow@main\n'
    elif failure=='caller_other_commit':api.sources.pop((r['workflow_head_sha'],'.github/workflows/daily.yml'))
    elif failure=='runtime_drift':api.sources[('e'*40,'scripts/build_government_revenue.py')]=b'changed executable'
    elif failure=='runtime_missing':api.sources.pop(('e'*40,'scripts/collect.py'))
    elif failure=='missing_log':api.read=lambda *args,**kwargs:b'no authenticated checkout command'
    elif failure=='unaudited':baseline['legacy_never_started_workflow_whitelist']=[]
    with pytest.raises((pre.Refused,KeyError)):
        pre.classify_legacy_never_published(api,r,baseline)


def test_authenticated_source_file_checks_git_object_and_body_identity(monkeypatch):
    api=pre.GitHub('synthetic-unused-token');body=b'known source'
    obj={'type':'file','path':'scripts/collect.py','encoding':'base64','size':len(body),
         'content':pre.base64.b64encode(body).decode(),
         'sha':pre.hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()}
    monkeypatch.setattr(api,'json',lambda *args:obj)
    raw,identity=api.source_file('scripts/collect.py','f'*40)
    assert raw==body and identity['sha256']==pre.digest(body)
    obj['sha']='a'*40
    with pytest.raises(pre.Refused):api.source_file('scripts/collect.py','f'*40)


def test_legacy_caller_block_can_preserve_unrelated_parent_source_without_retiring_it():
    api,r,baseline=legacy_fixture('daily.yml')
    path=(r['workflow_head_sha'],r['workflow_path'])
    api.sources[path]=b'# unrelated reviewed parent context\n'+api.sources[path]
    assert pre.classify_legacy_never_published(api,r,baseline)['unrelated_parent_effects_retired'] is False


def test_late_qualified_legacy_run_enters_existing_checkpoint_without_baseline_rewrite(tmp_path):
    source,r,baseline=legacy_fixture()
    old_api=Fake([r])
    original_json=old_api.json
    def json_api(path):
        value=original_json(path)
        if path.startswith('actions/workflows/'):
            for run in value['workflow_runs']:run['head_sha']=r['workflow_head_sha']
        else:
            for job in value['jobs']:job['steps']=r['steps']
        return value
    old_api.json=json_api;old_api.source_file=source.source_file;old_api.read=source.read
    result=pre.preflight(tmp_path,tmp_path,old_api,baseline,CURRENT)
    assert result['checked_operations'][0]['disposition']=='authenticated_audited_publication_step_skipped'
    assert result['checked_operations'][0]['unrelated_parent_effects_retired'] is False


def test_legacy_checkout_parser_matches_actual_actions_log_command_format():
    body=("2026-10-11T16:31:16.6808590Z [command]/usr/bin/git log -1 --format=%H\n"
          "2026-10-11T16:31:16.6947720Z b8568e3f33a6ab7209e52493f93638910586980e\n").encode()
    assert pre._legacy_checkout_commit(body)=="b8568e3f33a6ab7209e52493f93638910586980e"
