"""GovRev original stage/receipt/witness wire; syntax is not admission."""
import json
import os
from pathlib import Path

import pytest
import yaml

from scripts.ci import govrev_native_settle as settle
from scripts.ci import govrev_publisher_preflight as preflight
from scripts.ci import native_queue_push as native
from scripts.workflow_run_source import resolve_run_source

ROOT=Path(__file__).resolve().parents[1]


def test_current_recovery_baseline_matches_executed_publisher_source_without_clearing_old_operations():
    # A source upgrade must not silently make every natural preflight refuse.
    # This checks source readiness only, not runtime legacy/effect reconciliation.
    baseline=preflight.read_baseline(ROOT)
    assert baseline['source_closure']==preflight.source_closure(ROOT)
    assert baseline['reconciled_legacy_operations'] and baseline['legacy_census_complete'] is True


def test_private_preflight_records_actual_original_code_not_newer_data_checkout(tmp_path,monkeypatch):
    private=tmp_path/'native-publication-code-123-1-refresh';data=tmp_path/'data-checkout'
    for name in preflight.SOURCE_PATHS:
        for directory,body in ((private,b'original protected code'),(data,b'newer DATA code')):
            p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
    monkeypatch.setattr(preflight,'__file__',str(private/'scripts/ci/govrev_publisher_preflight.py'))
    import hashlib
    assert set(preflight.source_closure(data).values())=={hashlib.sha256(b'original protected code').hexdigest()}


@pytest.mark.parametrize('caller',['daily.yml','fms-acquire.yml','government-revenue-live.yml'])
def test_origin_keeps_real_caller_path_and_callee_job_without_new_schema(monkeypatch,caller):
    env={'GITHUB_REPOSITORY':native.REPOSITORY,'GITHUB_REF':'refs/heads/main',
        'GITHUB_WORKFLOW_REF':native.REPOSITORY+'/.github/workflows/'+caller+'@refs/heads/main',
        'GITHUB_WORKFLOW_SHA':'1'*40,'GITHUB_SHA':'1'*40,'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1',
        'GITHUB_JOB':'refresh','NATIVE_PUBLICATION_TOKEN_ORIGIN':'GITHUB_TOKEN',
        'NATIVE_PUBLICATION_PUBLISHING_STEP':'native_publication_stage',
        'GOVREV_CALL_SOURCE_SHA':'' if caller=='government-revenue-live.yml' else '2'*40}
    for k,v in env.items():monkeypatch.setenv(k,v)
    locator,workflow,sha=native.producer_identity('3'*40,'4'*64)
    assert workflow=='.github/workflows/'+caller and sha=='1'*40 and locator['job']=='refresh'
    monkeypatch.setenv('GITHUB_WORKFLOW_REF',native.REPOSITORY+'/.github/workflows/other.yml@refs/heads/main')
    with pytest.raises(native.PublicationHeld):native.producer_identity('3'*40,'4'*64)


@pytest.mark.parametrize('status',[77,75,76])
def test_unsettled_original_intent_never_runs_witness_or_emits_consumer_success(tmp_path,monkeypatch,status):
    monkeypatch.setenv('GITHUB_OUTPUT',str(tmp_path/'output'))
    def pending(api,root,record,deadline,*,on_published):return status
    monkeypatch.setattr(native,'settle',pending)
    monkeypatch.setattr(settle.proof,'command_publication_witness',lambda args:pytest.fail('unsettled witness'))
    assert settle.settle_original(None,tmp_path,'original',123,'proof','identity',tmp_path/'witness')==status
    assert not (tmp_path/'output').exists() and not (tmp_path/'witness').exists()


@pytest.mark.parametrize('witness_state',['retained','missing','wrong-release','wrong-source'])
def test_final_success_requires_actual_same_original_retained_witness(tmp_path,monkeypatch,witness_state):
    release={'source_head':'1'*40,'merge_sha':'2'*40,'observed_target_sha':'2'*40,'projection_sha256':'3'*64,'pr_number':7}
    monkeypatch.setenv('GITHUB_OUTPUT',str(tmp_path/'output'))
    monkeypatch.setattr(settle.proof,'_head_commit',lambda root:'9'*40 if witness_state=='wrong-source' else release['source_head'])
    def landed(api,root,record,deadline,*,on_published):on_published(release);return 0
    monkeypatch.setattr(native,'settle',landed)
    def witness(args):
        assert args.commit==release['source_head'] and args.push_identity=='identity'
        assert args.native_release is release
        if witness_state!='missing':
            (tmp_path/'witness').write_text(json.dumps({'contract':'government_revenue.publication_witness.v1',
                'native_publication':release if witness_state!='wrong-release' else {},
                'issuance_authority':False,'serving_generation_authority':False}))
        return 0
    monkeypatch.setattr(settle.proof,'command_publication_witness',witness)
    if witness_state=='retained':
        assert settle.settle_original(None,tmp_path,'original',123,'proof','identity',tmp_path/'witness')==0
        assert (tmp_path/'output').read_text()=='published=true\nsource_sha='+'2'*40+'\n'
    else:
        with pytest.raises((native.PublicationHeld,OSError)):
            settle.settle_original(None,tmp_path,'original',123,'proof','identity',tmp_path/'witness')
        assert not (tmp_path/'output').exists()


def test_original_source_proof_and_origin_upload_before_settlement_final_witness_archive_after():
    doc=yaml.safe_load((ROOT/'.github/workflows/government-revenue-live.yml').read_text())
    steps=doc['jobs']['refresh']['steps'];byid={s['id']:s for s in steps if s.get('id')}
    ids=['native_publication_stage','native_publication_proof','native_publication_origin','native_publication']
    indices=[steps.index(byid[i]) for i in ids]
    assert indices==list(range(indices[0],indices[0]+4))
    assert steps[-1]['name']=='retain bounded candidate proof failure evidence'
    for id in ids[1:3]:
        assert byid[id]['uses']=='actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
        assert byid[id]['with']['overwrite'] is False
        assert byid[id]['with']['if-no-files-found']=='error'
    assert 'native_publication_proof.outcome' in byid['native_publication']['if']
    assert 'native_publication_origin.outcome' in byid['native_publication']['if']
    stage=resolve_run_source(byid['native_publication_stage']['run'],ROOT)
    assert stage.index('verify --committed')<stage.index('push_native_do')<stage.index('publication=pending')
    assert stage.index('publication=pending')<stage.index('while push_attempt')
    assert 'PUSH_BUDGET_SECS=2700' in stage and 'PUSH_MAX_ATTEMPTS=2' in stage
    assert 'continue-on-error' not in byid['native_publication']
