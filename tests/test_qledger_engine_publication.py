"""Complete future engine output from one test-owned settled native original."""
from dataclasses import replace

import pytest

from tests.test_qledger_conversion_candidate import fixture, native_fixture, prepare_native, git  # noqa: F401
from tests.test_qledger_original_result import original, owner_bridge  # noqa: F401
from engine import qledger_store_protocol as p
from scripts.ci import qledger_conversion_candidate as c
from scripts.ci.qledger_engine_publication import EnginePublicationInvocation

pytestmark=pytest.mark.parametrize('fixture', [{'raw':b'{"claim_id":"x","status":"open"}\n','part_bytes':256}],indirect=True)


@pytest.fixture
def engine(original,monkeypatch):
    _,store,binding,identities,root,_=owner_bridge(original,monkeypatch)
    # Explicit test-owned no-clock producer. Real registrar clock uncertainty
    # remains a refusal; a successful callback cannot manufacture settlement.
    with store.ClaimsBindingScope(binding):
        with store._claims_mutation(binding.claims_path,native_intent=identities[0]) as writer:
            writer.append_serialized_rows([b'{"claim_id":"future-engine"}\n'])
    write,_=binding.prepared_original_results[0]
    retained=binding.read_original_write_result(write)
    tip=retained.accepted_tip_oid;ref='refs/remotes/origin/main'
    native=binding.prepare_publication_candidate(write,accepted_tip_oid=tip,accepted_ref=ref,
                                                commit_metadata=retained.commit_metadata)
    blob=git(binding.repo_root,'hash-object','-w','--stdin',input=b'complete engine data\n').decode()
    broad_tree=c._tree_with_members(binding.repo_root,native.tree_oid,{(b'engine-data',):blob},binding.limits)
    broad=git(binding.repo_root,'commit-tree',broad_tree,'-p',tip,input=b'fixture broad output\n').decode()
    page=git(binding.repo_root,'hash-object','-w','--stdin',input=b'final render-sync page\n').decode()
    full=c._tree_with_members(binding.repo_root,broad_tree,{(b'engine-page',):page},binding.limits)
    final=git(binding.repo_root,'commit-tree',full,'-p',broad,input=b'fixture render sync\n').decode()
    args=dict(source_candidate_oid=final,expected_tree_oid=full,accepted_tip_oid=tip,accepted_ref=ref)
    return binding,write,retained,args,root


def test_complete_final_tree_preserves_broad_and_render_sync_without_rewriting_source(engine):
    b,w,retained,args,root=engine
    repo=b.repo_root
    before=((repo/p.ROOT_PATH).read_bytes(),(repo/'.git/index').read_bytes(),git(repo,'show-ref'),
            (retained.result_path/'manifest.json').read_bytes())
    # Before composition the actual render-sync descendant is correctly
    # rejected: the direct-parent invariant remains unchanged.
    with pytest.raises(p.SnapshotIntegrityError,match='sole parent'):
        b.check_publication_candidate(w,candidate_oid=args['source_candidate_oid'],
            expected_tree_oid=args['expected_tree_oid'],accepted_tip_oid=args['accepted_tip_oid'],
            accepted_ref=args['accepted_ref'])
    owner=EnginePublicationInvocation(b,w)
    prepared=owner.prepare(**args)
    assert prepared.source_candidate_oid==args['source_candidate_oid']
    assert prepared.tree_oid==args['expected_tree_oid']
    assert git(repo,'rev-parse',prepared.candidate_oid+'^{tree}').decode()==args['expected_tree_oid']
    assert git(repo,'show',prepared.candidate_oid+':engine-data')==b'complete engine data'
    assert git(repo,'show',prepared.candidate_oid+':engine-page')==b'final render-sync page'
    assert git(repo,'show','-s','--format=%P',prepared.candidate_oid).decode()==args['accepted_tip_oid']
    assert prepared.candidate_oid!=args['source_candidate_oid'] and prepared.eligible_for_cutover is False
    bound,witness=owner.check(prepared,push_args=('origin',prepared.candidate_oid+':refs/heads/main'))
    assert witness.status=='NATIVE_OPERATION_VERIFIED' and bound.operation_id==w.intent.operation_id
    assert ((repo/p.ROOT_PATH).read_bytes(),(repo/'.git/index').read_bytes(),git(repo,'show-ref'),
            (retained.result_path/'manifest.json').read_bytes())==before
    assert git(repo,'cat-file','-t',args['source_candidate_oid'])==b'commit'


@pytest.mark.parametrize('fault',['manifest','tree','tip','tail','unknown','pid','push-source'])
def test_final_engine_join_refuses_unproven_original_or_changed_boundary(engine,fault):
    b,w,retained,args,_=engine
    owner=EnginePublicationInvocation(b,w)
    if fault=='manifest':
        (retained.result_path/'manifest.json').unlink()
    elif fault=='tree':
        args['expected_tree_oid']=git(b.repo_root,'rev-parse',args['accepted_tip_oid']+'^{tree}').decode()
    elif fault=='tip':
        git(b.repo_root,'update-ref',args['accepted_ref'],args['source_candidate_oid'])
    elif fault=='tail':
        extra=p.plan_append(w.plan.snapshot,transaction_id='not-this-original',serialized_rows=[b'unknown-tail\n'],limits=b.limits)
        members={**extra.snapshot._members,p.ROOT_PATH:extra.snapshot.root_bytes}
        changes={tuple(part.encode() for part in path.split('/')):
                 git(b.repo_root,'hash-object','-w','--stdin',input=payload).decode()
                 for path,payload in members.items()}
        args['expected_tree_oid']=c._tree_with_members(b.repo_root,args['expected_tree_oid'],changes,b.limits)
        args['source_candidate_oid']=git(b.repo_root,'commit-tree',args['expected_tree_oid'],'-p',args['accepted_tip_oid'],input=b'fixture undeclared tail\n').decode()
    elif fault=='unknown':
        b._record(w,replace(b.attempts[-1].outcome,clock_status='uncertain'))
    elif fault=='pid':
        owner.pid+=1
    with pytest.raises(p.SnapshotIntegrityError):
        prepared=owner.prepare(**args)
        if fault=='push-source':
            owner.check(prepared,push_args=('origin',args['source_candidate_oid']+':refs/heads/main'))


def test_fork_after_native_write_before_invocation_refuses_inherited_original(engine):
    import os
    b,w,_,args,_=engine
    read_fd,write_fd=os.pipe()
    child=os.fork()
    if child==0:
        os.close(read_fd)
        def no_preparation(*a,**k):
            raise AssertionError('candidate preparation reached inherited original')
        c._write_git_object=no_preparation
        try:
            EnginePublicationInvocation(b,w).prepare(**args)
        except p.SnapshotIntegrityError as exc:
            message=('REFUSED '+str(exc)).encode()
        except BaseException as exc:
            message=('WRONG '+str(exc)).encode()
        else:
            message=b'WRONG inherited original accepted'
        os.write(write_fd,message)
        os.close(write_fd)
        os._exit(0)
    os.close(write_fd)
    try:
        message=os.read(read_fd,4096).decode()
    finally:
        os.close(read_fd)
        _,status=os.waitpid(child,0)
    assert os.waitstatus_to_exitcode(status)==0
    assert message.startswith('REFUSED ') and 'original producer process' in message, message
