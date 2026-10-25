"""Isolated entry join with explicitly test-owned authorities and native writes.

The fixture allocation adapter owns no real AI effect. Accepted thematic/clock
checks remain separate; this tests the actual loader/factory/finalizer join.
"""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import yaml
import pytest

from tests.test_qledger_daily_normalizer import alias_kind  # noqa:F401
from tests import test_qledger_daily_normalizer as base_daily
from tests.test_qledger_conversion_candidate import conversion_invocation, git  # noqa:F401
from tests.test_qledger_runner_bootstrap import BUNDLE_FILES,ENTRY,canonical,put,SOURCE


@pytest.fixture(name='fixture')
def entry_fixture(tmp_path,request,alias_kind):
    repo,_,blob,raw,limits=base_daily.normalizer_fixture.__wrapped__(tmp_path,request,alias_kind)
    for name in ('daily_engine_commit_outputs.sh','push_retry.sh','strip_conflict_markers.sh','options_signal_nightly.sh'):
        target=repo/'scripts/ci'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((SOURCE/'scripts/ci'/name).read_bytes())
    git(repo,'add','.');git(repo,'commit','-qm','test-owned original installed programs')
    tip=git(repo,'rev-parse','HEAD').decode();git(repo,'update-ref','refs/remotes/origin/main',tip)
    return repo,tip,blob,raw,limits


ALLOCATION='''
from lib import config
from engine import qledger_store as store

def main(regions,*,run_ai):
    assert run_ai is False
    assert config.ROOT == config.site_dir().parent
    (config.ROOT/'templates/index.html').write_text('<!doctype html><html><head><link href="skin.css" rel="stylesheet"></head><body>fresh original full candidate</body></html>')
    (config.site_dir()/'index.html').write_text('stale fixture render')
    (config.ROOT/'reports/keep.json').write_text('all original non-QL output')
    return False

def run_native_thematic_owner(regions,*,native_intents,root,owner_binding,call):
    assert root == config.ROOT
    for region in regions:
        with store._claims_mutation(owner_binding.claims_path,native_intent=native_intents[region]) as writer:
            writer.append_serialized_rows([b'{"fresh_fixture_original":1}\\n'])
    return {r:'test-owned native original' for r in regions}
'''


def bundle_files():
    # Exact finite runtime imports; no source rewrite/lazy-import bypass. An
    # unexpected first-party import is still refused by the real finite finder.
    seeds=[*BUNDLE_FILES,'scripts/ci/qledger_engine_publication.py','scripts/ci/qledger_daily_entry.py',
        'scripts/ci/options_index_lock_identity.py','scripts/inject_data_base.py',
        'scripts/externalize_css.py','scripts/optimize_assets.py','scripts/check_template_site_sync.py',
        'scripts/check_start_runtime.py','scripts/check_ms_board_coherence.py',
        'scripts/check_commodity_publication.py','scripts/check_conflict_markers.py',
        'scripts/audit_china_gold_premium.py','lib/site_assets.py']
    seen=set();queue=list(seeds)
    def imports(node):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):return
        if isinstance(node,(ast.Import,ast.ImportFrom)):yield node
        for child in ast.iter_child_nodes(node):yield from imports(child)
    while queue:
        name=queue.pop()
        if name in seen or name=='scripts/build_allocation.py':continue
        seen.add(name)
        for node in imports(ast.parse((SOURCE/name).read_text())):
            names=[n.name for n in node.names] if isinstance(node,ast.Import) else (
                [node.module,*[node.module+'.'+n.name for n in node.names if n.name!='*']]
                if node.module and not node.level else [])
            for mod in names:
                parts=mod.split('.')
                if parts[0] not in ('engine','scripts','lib'):continue
                candidates=[Path(*parts).with_suffix('.py'),*[Path(*parts[:i])/'__init__.py' for i in range(1,len(parts)+1)]]
                queue.extend(str(p) for p in candidates if (SOURCE/p).is_file())
    return sorted(seen)


DRIVER='''
import importlib.util,json,os,sys,subprocess
from pathlib import Path
boot,cfg,digest,action,deps=sys.argv[1:]
# Test-owned dependency exposure only. -I stays set and no checkout/bundle path
# is added. This is not an installed production environment/admission claim.
sys.path.append(deps)
spec=importlib.util.spec_from_file_location('test_owned_bootstrap',boot)
b=importlib.util.module_from_spec(spec);sys.modules[spec.name]=b;spec.loader.exec_module(b)
doc=json.loads(Path(cfg).read_bytes());repo=Path(doc['repo']);owner=Path(doc['owner_root'])
preimport=action in ('missing-resource','changed-resource','symlink-resource','other-resource','unallowlisted-css','missing-config-pin')
before=(repo/'data/qledger/claims.jsonl').read_bytes()
try:
 with b.trusted_bootstrap(owner_root=owner,repo=repo,config_path=Path(cfg),config_digest=digest) as loaded:
    if action=='resource-module':__import__('templates.shared_shell_bridge')
    if action in ('same-root-cache','caught-same-root-cache','qualified-cache-positive'):
        from lib import config as early_config
        source=repo/'config.yml';original=source.read_bytes()
        if action!='qualified-cache-positive':source.write_bytes(original+b'\\nreview_stale_config: preinstallation\\n')
        try:
            early_config.load()
        except Exception:
            if action!='caught-same-root-cache':raise
        finally:
            source.write_bytes(original)
        if action=='caught-same-root-cache':early_config.load.cache_clear()
    loaded.gate.initial_checkout(lambda oid:subprocess.check_call(['git','-C',str(repo),'checkout','--quiet','-B','main',oid]))
    subprocess.check_call(['git','-C',str(repo),'update-ref','refs/remotes/origin/main',loaded.gate.candidate_oid])
    from engine.qledger_original_result import OriginalResultClaimsBinding,OriginalResultTarget
    from engine.qledger_store_native import NativeClaimsIntent
    from scripts.ci.qledger_conversion_candidate import CandidateCommitMetadata
    from lib import config
    root=owner/'producer-evidence'
    intent=NativeClaimsIntent('producer-original','producer-lane','write-one')
    target=OriginalResultTarget(root,root/'write-one','write-one',loaded.gate.candidate_oid,
        'refs/remotes/origin/main','refs/heads/main',CandidateCommitMetadata('Test original','fixture@example.invalid',1700000099))
    binding=OriginalResultClaimsBinding(repo/'data/qledger/claims.jsonl',operation_id=intent.operation_id,
        lane_id=intent.lane_id,limits=loaded.gate.owner.limits,original_result_targets={intent:target})
    kwargs=dict(owner_binding=binding,regions=('us',),native_intents={'us':intent})
    if action=='foreign-cache':
        foreign=owner/'foreign';foreign.mkdir();(foreign/'config.yml').write_text('{"storage":{"data_dir":"data","site_dir":"site"}}')
        config.ROOT=foreign;config.load();config.ROOT=repo
    if action=='wrong-root':config.ROOT=owner
    if action=='missing-inputs':kwargs={}
    if action=='partial-inputs':del kwargs['native_intents']
    if action=='serialized-inputs':kwargs['owner_binding']={'operation_id':intent.operation_id,'lane_id':intent.lane_id}
    if action=='missing-retention':loaded.gate.evidence.provider.missing='retention'
    if action=='transfer':
        native_before=(repo/'data/qledger/claims.root.json').read_bytes()
        pid=os.fork()
        if pid==0:
            try:loaded.entry.build_producer(loaded.context,**kwargs)
            except Exception as exc:
                os._exit(0 if 'transferred' in str(exc) else 4)
            os._exit(5)
        _,status=os.waitpid(pid,0);assert status==0
        assert (repo/'data/qledger/claims.root.json').read_bytes()==native_before
        assert not (root/'write-one').exists()
        print('TEST_OWNED_TRANSFER_REFUSED')
    else:
        if action=='publication-positive':
            from hashlib import sha256
            from scripts.ci.qledger_engine_publisher import NativePublicationFinalizer
            origin=owner/'test-owned-original.git'
            subprocess.check_call(['git','init','--bare','--quiet',str(origin)])
            subprocess.check_call(['git','-C',str(repo),'remote','add','origin',str(origin)])
            subprocess.check_call(['git','-C',str(repo),'push','--quiet','origin',loaded.gate.candidate_oid+':refs/heads/main'])
            info=origin.stat()
            kwargs['publication']=NativePublicationFinalizer(origin_binding_sha256=sha256(str(origin).encode()).hexdigest(),
                original_origin_inode=(info.st_dev,info.st_ino),original_attempt=1,original_max_attempts=20,original_alarm_seconds=420)
        refs=subprocess.check_output(['git','-C',str(repo),'show-ref'])
        result=loaded.producer(**kwargs)
        assert result.status==('publication_confirmed' if action=='publication-positive' else 'candidate_verified')
        if action=='publication-positive':
            assert subprocess.check_output(['git','-C',str(origin),'rev-parse','refs/heads/main']).strip().decode()==result.publication.candidate_oid
        assert config.ROOT==repo and config._LOAD_ROOT==repo
        assert subprocess.check_output(['git','-C',str(repo),'show-ref'])==refs
        assert len(result.original_writes)==1 and (root/'write-one/manifest.json').is_file()
        oid=result.publication.candidate_oid
        text=subprocess.check_output(['git','-C',str(repo),'show',oid+':site/index.html'])
        assert b'fresh original full candidate' in text and b'?v=' in text
        assert subprocess.check_output(['git','-C',str(repo),'show',oid+':reports/keep.json'])==b'all original non-QL output'
        assert not (repo/'.git/index.lock').exists()
        assert action in ('positive','qualified-cache-positive','publication-positive')
        print('TEST_OWNED_FULL_CANDIDATE')
except Exception as exc:
 if action in ('positive','qualified-cache-positive','publication-positive','transfer'):raise
 reasons={'unallowlisted-css':'unsafe bundle path','missing-resource':'canonical resources missing before import',
          'changed-resource':'pinned input digest differs','other-resource':'unsafe bundle path',
          'resource-module':'unqualified path import','missing-inputs':'missing or transferred exact original producer binding',
          'wrong-root':'actual original ROOT or cached configuration differs','foreign-cache':'actual original ROOT or cached configuration differs',
          'partial-inputs':'complete explicit same-process producer inputs required','missing-retention':'fixture actual evidence missing: retention',
          'serialized-inputs':'missing or transferred exact original producer binding',
          'same-root-cache':'pinned input digest differs','caught-same-root-cache':'unqualified original configuration read',
          'missing-config-pin':'daily entry qualified config pin missing before import'}
 if action=='symlink-resource':assert isinstance(exc,OSError)
 else:assert reasons[action] in str(exc),(action,type(exc),str(exc))
 if preimport:
    assert not (owner/'bundle/IMPORT_OCCURRED').exists()
    assert (repo/'data/qledger/claims.jsonl').read_bytes()==before
 elif action!='resource-module':
    if action not in ('same-root-cache','foreign-cache'):assert (owner/'qledger-install.hold').is_file()
    else:assert loaded.bundle.failure is not None
    if action in ('same-root-cache','caught-same-root-cache'):
        assert (repo/'data/qledger/claims.jsonl').read_bytes()==before
        assert not (repo/'data/qledger/claims.root.json').exists()
    assert not (owner/'producer-evidence/write-one').exists()
 print('TEST_OWNED_REFUSAL',type(exc).__name__,str(exc))
else:
 assert action in ('positive','qualified-cache-positive','publication-positive','transfer')
'''


@pytest.fixture
def entry_join(conversion_invocation,tmp_path):
    invocation,prepared=conversion_invocation;owner=invocation.owner.target.owner_root;repo=invocation.owner.repo
    owner.chmod(0o700);(owner/'producer-evidence').mkdir(mode=0o700)
    bundle=owner/'bundle';files=bundle_files()
    pins={name:put(bundle/name,(SOURCE/name).read_bytes()) for name in files}
    pins['scripts/build_allocation.py']=put(bundle/'scripts/build_allocation.py',ALLOCATION.encode())
    pins['owner_entry.py']=put(bundle/'owner_entry.py',(ENTRY+'\nfrom scripts.ci.qledger_daily_entry import build_producer\n').encode())
    for name in ('templates/shared_shell_bridge.js','templates/shared_shell.css'):
        pins[name]=put(bundle/name,(SOURCE/name).read_bytes())
    assert len(pins)<=126
    script=owner/'bootstrap.py';digest=put(script,(SOURCE/'scripts/ci/qledger_runner_bootstrap.py').read_bytes())
    producer=dict(operation_id='producer-original',lane_id='producer-lane',budget_id='original-producer-budget',retention_id='original-producer-retention')
    runtime={str(repo/'scripts/ci'/name):sha256((repo/'scripts/ci'/name).read_bytes()).hexdigest() for name in
        ('daily_engine_commit_outputs.sh','push_retry.sh','strip_conflict_markers.sh','options_signal_nightly.sh')}
    runtime[str(repo/'config.yml')]=sha256((repo/'config.yml').read_bytes()).hexdigest()
    cfg=dict(schema=1,repo=str(repo),owner_root=str(owner),bundle_root=str(bundle),result_path=str(invocation.owner.target.result_path),
        manifest_digest=prepared.manifest_digest,bootstrap_sha256=digest,original_deadline_monotonic_ns=time.monotonic_ns()+120_000_000_000,
        bundle_files=pins,entry_module='owner_entry',producer_context=producer,
        gate=dict(candidate_oid=prepared.candidate.candidate_oid,tree_oid=prepared.candidate.tree_oid,
            accepted_tip_oid=invocation.owner.target.accepted_tip_oid,runtime_code=runtime,
            workflow_oids=[prepared.candidate.candidate_oid],producers=[producer],runner_name='fixture-runner',repository='fixture/macro',agent_id=28))
    driver=tmp_path/'driver.py';driver.write_text(DRIVER)
    def run(action):
        if action=='unallowlisted-css':
            # Deterministic current negative: only the two canonical pinned
            # SharedShell resources are admitted. Never load a mutable HEAD.
            name='templates/qledger-unallowlisted.css'  # ci-trigger-closure: data — test-owned bundle member, never a repository read
            cfg['bundle_files'][name]=put(bundle/name,b'body { display: none; }\n')
        if action=='missing-resource':del cfg['bundle_files']['templates/shared_shell.css']
        if action=='missing-config-pin':del cfg['gate']['runtime_code'][str(repo/'config.yml')]
        if action=='changed-resource':(bundle/'templates/shared_shell.css').write_text('altered')
        if action=='symlink-resource':
            p=bundle/'templates/shared_shell.css';p.unlink();p.symlink_to(repo/'templates/shared_shell.css')
        if action=='other-resource':cfg['bundle_files']['templates/other.js']=put(bundle/'templates/other.js',b'other')
        config=owner/'bootstrap.json';hash_=put(config,canonical(cfg))
        r=subprocess.run([sys.executable,'-I',str(driver),str(script),str(config),hash_,action,str(Path(yaml.__file__).parent.parent)],capture_output=True,text=True,timeout=140,cwd=repo)
        assert r.returncode==0,r.stdout+r.stderr
        return r.stdout
    return run


@pytest.mark.parametrize('action',['publication-positive','positive','unallowlisted-css','missing-resource','changed-resource','symlink-resource','other-resource','resource-module','missing-inputs','partial-inputs','serialized-inputs','wrong-root','foreign-cache','missing-retention','transfer','same-root-cache','caught-same-root-cache','qualified-cache-positive','missing-config-pin'])
def test_actual_isolated_daily_entry_join_or_exact_refusal(entry_join,action):
    result=entry_join(action)
    assert ('TEST_OWNED_FULL_CANDIDATE' if action in ('positive','qualified-cache-positive','publication-positive') else 'TEST_OWNED_TRANSFER_REFUSED' if action=='transfer' else 'TEST_OWNED_REFUSAL') in result


def test_ordinary_root_and_config_loading_behavior_is_preserved(tmp_path,monkeypatch):
    from lib import config
    assert config.ROOT==SOURCE
    (tmp_path/'config.yml').write_text('storage: {data_dir: data, site_dir: site}\n')
    monkeypatch.setattr(config,'ROOT',tmp_path)
    config.load.cache_clear()
    try:
        assert config.load()=={'storage':{'data_dir':'data','site_dir':'site'}}
        assert config.data_dir()==tmp_path/'data' and config.site_dir()==tmp_path/'site'
        assert config._LOAD_ROOT==tmp_path and config.load.cache_info().currsize==1
    finally:
        config.load.cache_clear()
