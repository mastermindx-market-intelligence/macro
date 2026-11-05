"""Pure source fence only; fixture receipt syntax is not origin authority."""
import hashlib
import os
from pathlib import Path
import subprocess
import time

import pytest

from scripts.ci import govrev_candidate_proof as proof


def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True).stdout.decode().strip()


def commit(root,path,body):
    file=root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(body)
    git(root,'add','.');git(root,'commit','-qm','fixture')
    return git(root,'rev-parse','HEAD')


@pytest.fixture
def generation(tmp_path):
    git(tmp_path,'init','-q','-b','main');git(tmp_path,'config','user.name','fixture');git(tmp_path,'config','user.email','fixture@example.invalid')
    commit(tmp_path,'scripts/selected.py','original code')
    base=commit(tmp_path,'data/government_revenue/candidate_queue.json','old')
    candidate=commit(tmp_path,'data/government_revenue/candidate_queue.json','new')
    receipt={'contract':proof.RECEIPT_CONTRACT,'conclusion':'passed','prover_version':proof.PROVER_VERSION,
        'proved_at':'fixture only','source_checkout':base,'generation':{},'inputs':{},
        'outputs':{'data/government_revenue/candidate_queue.json':hashlib.sha256(b'new').hexdigest()},
        'source_dependencies':{'scripts/selected.py':hashlib.sha256(b'original code').hexdigest()},
        'suite':{},'pytest_exit':0,'pytest_summary':'fixture passed',
        'execution_evidence':{'nodeids':['fixture::test'],'junit_sha256':'a'*64,
                              'artifacts':{'log':{},'collection':{},'junit':{}}}}
    receipt['identity']=proof.receipt_identity(receipt)
    return tmp_path,base,candidate,receipt


def test_unrelated_group_base_preserves_same_original_sealed_generation(generation):
    root,base,candidate,receipt=generation;git(root,'checkout','-qb','selected',base)
    group_base=commit(root,'unrelated','new main');git(root,'merge','--no-ff','--no-edit',candidate)
    group=git(root,'rev-parse','HEAD')
    result=proof.validate_native_group(root,candidate,group_base,group,receipt)
    assert result['proof_identity']==receipt['identity'] and result['candidate']==candidate


@pytest.mark.parametrize('path',['scripts/selected.py','data/government_revenue/fms_observations.jsonl',
                                 'data/company_intelligence/event_workspaces/manifest.json'])
def test_changed_input_cannot_be_waved_through_by_successful_group_merge(generation,path):
    root,base,candidate,receipt=generation;git(root,'checkout','-qb','selected',base)
    group_base=commit(root,path,'new input');git(root,'merge','--no-ff','--no-edit',candidate)
    group=git(root,'rev-parse','HEAD')
    with pytest.raises(ValueError,match='advanced_while_queued'):
        proof.validate_native_group(root,candidate,group_base,group,receipt)


def test_integration_cannot_introduce_an_unsealed_output(generation):
    root,base,candidate,receipt=generation
    group=commit(root,'site/government-revenue-data/unsealed.json','not proved')
    with pytest.raises(ValueError,match='not_in_original_receipt'):
        proof.validate_native_group(root,candidate,base,group,receipt)


def test_partial_tampered_receipt_and_missing_original_budget_do_not_read_git(generation):
    root,base,candidate,receipt=generation;calls=[]
    def reader(*args,**kwargs):calls.append(args);raise RuntimeError('original read budget exhausted')
    for modified in ({},dict(receipt,identity='0'*64)):
        with pytest.raises(ValueError,match='receipt_unqualified'):
            proof.validate_native_group(root,candidate,base,candidate,modified,git_read=reader,deadline=time.monotonic()+1)
    with pytest.raises(ValueError,match='deadline_required'):
        proof.validate_native_group(root,candidate,base,candidate,receipt,git_read=reader)
    with pytest.raises(ValueError,match='deadline_expired'):
        proof.validate_native_group(root,candidate,base,candidate,receipt,git_read=reader,deadline=time.monotonic()-1)
    assert not calls
    with pytest.raises(RuntimeError,match='original read budget exhausted'):
        proof.validate_native_group(root,candidate,base,candidate,receipt,git_read=reader,deadline=time.monotonic()+1)
    assert len(calls)==1
