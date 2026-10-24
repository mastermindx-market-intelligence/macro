"""Future native daily preparation with real normalizers and test-owned evidence."""
from dataclasses import replace
from types import SimpleNamespace
from hashlib import sha256
import time
import os
import stat

import pytest

from tests.test_qledger_conversion_candidate import fixture as base_fixture, native_fixture, prepare_native, git  # noqa:F401
from tests.test_qledger_original_result import original  # noqa:F401
from tests.test_qledger_causal_originals import causal  # noqa:F401
from tests.test_qledger_engine_finalizer import setup, SOURCE
from tests.test_qledger_engine_producer import invoke
from tests.test_commodity_publication import page
from scripts.ci import qledger_engine_publication as engine
from scripts.ci.qledger_host_gate import CodePin
from engine import qledger_store_protocol as p


@pytest.fixture
def alias_kind():return None


@pytest.fixture(name='fixture')
def normalizer_fixture(tmp_path,request,alias_kind):
    value=base_fixture.__wrapped__(tmp_path,request)
    repo,_,blob,raw,limits=value
    files={
        'config.yml':'storage:\n  data_dir: data\n  site_dir: site\ncommodities:\n  china_gold_premium: {}\n',
        '.gitignore':'data/qledger/control_evidence_clock_start/\n',
        'site/commodities.html':page(),  # ci-trigger-closure: data — temporary fixture destination, never a repository read
        'site/start.html':'<html><head>'+''.join('<script src="'+name+'"></script>' for name in  # ci-trigger-closure: data — temporary fixture destination, never a repository read
            ('globe-deck.js','sky.js','hub-welcome.js','live_config.js','live.js','wh_banner.js'))+'</head></html>',
        'site/prophet/accepted.html':'accepted Prophet page',
        'data/prophet/ledger.jsonl':'accepted Prophet ledger',
        'data/prophet/ledger_quarantine.json':'{}',
        'data/prophet/origination_receipts/accepted.json':'{}',
        'data/prophet/legacy_shadow/accepted.json':'{}',
        'data/prophet_arena/accepted.json':'{}',
        'data/prophet_stage_shadow/accepted.json':'{}',
        'site/anticipationdata/us_leader_pullback.json':'accepted leader source',  # ci-trigger-closure: data — temporary fixture destination, never a repository read
        'data/options_signal_episode/accepted.json':'accepted narrow episode',
        'data/options_signal_campaign/accepted.json':'accepted narrow campaign',
        'data/hk/accepted.json':'accepted Asia source',
        'reports/keep.json':'complete engine report',
        'site/skin.css':'body {color: #123456;}',
    }
    pair='<!doctype html><html><head><link href="skin.css" rel="stylesheet"></head><body>accepted pair</body></html>'
    files.update({'site/index.html':pair,'templates/index.html':pair})  # ci-trigger-closure: data — temporary fixture path, never a repository read
    for rel,payload in files.items():
        target=repo/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(payload)
    for name in ('shared_shell_bridge.js','shared_shell.css','data_base.js'):
        (repo/'templates'/name).write_bytes((SOURCE/'templates'/name).read_bytes())
    if alias_kind=='accepted-restore':
        (repo/'site/restored.html').symlink_to('../data/qledger/claims.root.json')
    git(repo,'add','.');git(repo,'commit','-qm','test-owned accepted complete renderer')
    tip=git(repo,'rev-parse','HEAD').decode();git(repo,'update-ref','refs/remotes/origin/main',tip)
    # Test-owned original profile before conversion; no production bound changes.
    return repo,tip,blob,raw,replace(limits,git_blob_bytes=262144)


pytestmark=pytest.mark.parametrize('fixture',[{'raw':b'{"claim_id":"x","status":"open"}\n<<<<<<< accepted opaque\n>>>>>>> accepted opaque\n','part_bytes':256}],indirect=True)


def pins(gate):
    extra=('scripts/ci/daily_engine_commit_outputs.sh','scripts/ci/push_retry.sh','scripts/ci/strip_conflict_markers.sh','templates/shared_shell_bridge.js','templates/shared_shell.css')
    gate.owner_code+=tuple(CodePin(SOURCE/name,sha256((SOURCE/name).read_bytes()).hexdigest()) for name in extra)


def dirty(repo):
    text='<!doctype html><html><head><link href="skin.css" rel="stylesheet"></head><body>current paired render</body></html>'
    (repo/'templates/index.html').write_text(text)  # ci-trigger-closure: data — temporary fixture path, never a repository read
    (repo/'site/index.html').write_text('stale site pair')  # ci-trigger-closure: data — temporary fixture path, never a repository read
    # Non-pair must really pass through CSS externalization, not a spy.
    (repo/'site/native-normalizer.html').write_text('<!doctype html><html><head><style>'+('p{color:red;}\n'*120)+'</style></head><body>new full render</body></html>')
    for rel in ('data/options_signal_episode/accepted.json','data/prophet/ledger.jsonl','data/hk/accepted.json'):
        (repo/rel).write_text('unpublished sibling output')
    (repo/'data/prophet/untracked-correction.json').write_text('preserve original correction input')
    (repo/'data/qledger/control_evidence_clock_start').mkdir(exist_ok=True)
    (repo/'data/qledger/control_evidence_clock_start/test-owned.json').write_text('never broad-stage ignored clock')


def test_real_daily_normalizers_stage_complete_native_tree_without_installing_or_borrowing(causal,monkeypatch):
    from scripts import inject_data_base
    real_inject=inject_data_base.inject
    calls=[]
    def warn_once(site):
        result=real_inject(site);calls.append(site)
        if len(calls)==1:raise OSError('test-owned lane-local normalizer warning')
        return result
    monkeypatch.setattr(inject_data_base,'inject',warn_once)
    state={}
    def finalize(checked):
        dirty(binding.repo_root)
        state['refs']=git(binding.repo_root,'show-ref')
        return engine.finalize_daily_engine_outputs(checked)
    binding,callback,gate=setup(causal,monkeypatch,finalize);pins(gate)
    # The real installed checkout has its accepted index, unlike the raw conversion fixture.
    git(binding.repo_root,'read-tree',next(iter(binding.original_result_targets.values())).accepted_tip_oid)
    legacy=(SOURCE/'scripts/ci/daily_engine_commit_outputs.sh').read_bytes()
    value=invoke(binding,callback,gate)
    assert value.status=='candidate_verified' and not gate.held
    assert git(binding.repo_root,'show-ref')==state['refs']
    assert (SOURCE/'scripts/ci/daily_engine_commit_outputs.sh').read_bytes()==legacy
    oid=value.publication.candidate_oid
    index=git(binding.repo_root,'show',oid+':site/index.html')
    template=git(binding.repo_root,'show',oid+':templates/index.html')
    assert index==template and b'current paired render' in index and b'?v=' in index
    assert b'data-dbase' in index and len(calls)==2
    transformed=git(binding.repo_root,'show',oid+':site/native-normalizer.html')
    assert b'assets/css/' in transformed and b'<style>' not in transformed
    assert git(binding.repo_root,'show',oid+':reports/keep.json')==b'complete engine report'
    assert b'render_mismatch' in git(binding.repo_root,'show',oid+':data/quality/china_gold_premium.json')
    assert git(binding.repo_root,'show',oid+':data/prophet/ledger.jsonl')==b'accepted Prophet ledger'
    assert git(binding.repo_root,'show',oid+':data/hk/accepted.json')==b'accepted Asia source'
    assert git(binding.repo_root,'show',oid+':data/options_signal_episode/accepted.json')==b'accepted narrow episode'
    assert (binding.repo_root/'data/prophet/untracked-correction.json').read_text()=='preserve original correction input'
    assert (binding.repo_root/'data/hk/accepted.json').read_text()=='unpublished sibling output'
    assert not git(binding.repo_root,'ls-tree','-r','--name-only',oid,'--','data/qledger/control_evidence_clock_start')
    assert not (binding.repo_root/'.git/index.lock').exists()
    assert binding.read_original_write_chain(value.original_writes).write.plan.snapshot.root_bytes==(binding.repo_root/p.ROOT_PATH).read_bytes()


def test_native_integrity_failure_precedes_all_normalization_and_cleanup(causal,monkeypatch):
    from scripts import inject_data_base
    monkeypatch.setattr(inject_data_base,'inject',lambda *a:pytest.fail('corrupt original reached normalization'))
    state={}
    def finalize(checked):
        dirty(binding.repo_root)
        target=binding.repo_root/p.ROOT_PATH
        target.write_bytes(b'<<<<<<< original unknown\n>>>>>>> original unknown\n')
        state['bytes']={str(p.relative_to(binding.repo_root)):p.read_bytes() for p in binding.repo_root.rglob('*') if p.is_file() and '.git' not in p.parts}
        state['index']=(binding.repo_root/'.git/index').read_bytes()
        return engine.finalize_daily_engine_outputs(checked)
    binding,callback,gate=setup(causal,monkeypatch,finalize);pins(gate)
    # The real installed checkout has its accepted index, unlike the raw conversion fixture.
    git(binding.repo_root,'read-tree',next(iter(binding.original_result_targets.values())).accepted_tip_oid)
    with pytest.raises(p.SnapshotIntegrityError):invoke(binding,callback,gate)
    assert gate.held
    assert state['bytes']=={str(p.relative_to(binding.repo_root)):p.read_bytes() for p in binding.repo_root.rglob('*') if p.is_file() and '.git' not in p.parts}
    assert (binding.repo_root/'.git/index').read_bytes()==state['index']
    assert len(binding.attempts)==1 and (causal[3]/'one'/'manifest.json').exists()


@pytest.mark.parametrize('fault',['missing-pin','accepted-source-changed','expired-original'])
def test_preparation_refuses_missing_or_changed_original_before_transform(causal,monkeypatch,fault):
    from scripts import inject_data_base
    monkeypatch.setattr(inject_data_base,'inject',lambda *a:pytest.fail('unqualified original reached normalizer'))
    state={}
    def finalize(checked):
        dirty(binding.repo_root)
        if fault=='missing-pin':
            gate.owner_code=tuple(p for p in gate.owner_code if p.path.name!='daily_engine_commit_outputs.sh')
        elif fault=='accepted-source-changed':
            tip=next(iter(binding.original_result_targets.values())).accepted_tip_oid
            other=git(binding.repo_root,'commit-tree',tip+'^{tree}','-p',tip,input=b'test-owned accepted-source race\n').decode()
            git(binding.repo_root,'update-ref','refs/remotes/origin/main',other)
        else:
            checked.original_deadline=time.monotonic_ns()-1
        state['bytes']={str(p.relative_to(binding.repo_root)):p.read_bytes() for p in binding.repo_root.rglob('*') if p.is_file() and '.git' not in p.parts}
        state['index']=(binding.repo_root/'.git/index').read_bytes()
        return engine.finalize_daily_engine_outputs(checked)
    binding,callback,gate=setup(causal,monkeypatch,finalize);pins(gate)
    git(binding.repo_root,'read-tree',next(iter(binding.original_result_targets.values())).accepted_tip_oid)
    with pytest.raises(p.SnapshotIntegrityError):invoke(binding,callback,gate)
    assert gate.held
    assert state['bytes']=={str(p.relative_to(binding.repo_root)):p.read_bytes() for p in binding.repo_root.rglob('*') if p.is_file() and '.git' not in p.parts}
    assert state['index']==(binding.repo_root/'.git/index').read_bytes()


def test_staging_logs_stream_without_widening_captured_object_response(tmp_path,capsys,fixture):
    # Test-owned local log emitter only; this does not grant a live owner scope.
    def owner():
        return SimpleNamespace(invocation=SimpleNamespace(binding=SimpleNamespace(repo_root=tmp_path)),
                               _deadline=lambda:10,unsettled_preparation=None)
    program=b"printf '%20000s' x\n"
    streamed=owner()
    assert engine._LiveFinalCandidate._run_prepare(streamed,program,[],stream_output=True)==b''
    assert len(capsys.readouterr().err)==20000 and streamed.unsettled_preparation is None
    captured=owner()
    with pytest.raises(p.SnapshotIntegrityError,match='unbounded finalizer response'):
        engine._LiveFinalCandidate._run_prepare(captured,program,[])
    original=captured.unsettled_preparation
    assert original is not None
    # Reconcile this exact test emitter; no replacement/kill/guessed settlement.
    original.communicate(timeout=10)
    assert original.returncode==0


@pytest.mark.parametrize('alias_kind',['data-base-copy','html-write','template-write','asset-parent','quality-parent','hardlink','accepted-restore','configured-site'])
def test_native_alias_is_untouched_before_any_normalizer_or_cleanup(causal,monkeypatch,alias_kind):
    from scripts import inject_data_base
    from lib import config
    real_inject=inject_data_base.inject
    touched=[]
    def observed_inject(*args):
        touched.append(True)
        return real_inject(*args)
    monkeypatch.setattr(inject_data_base,'inject',observed_inject)
    def image(repo):
        result={}
        for path in repo.rglob('*'):
            if '.git' in path.relative_to(repo).parts:continue
            info=path.lstat()
            payload=os.readlink(path) if stat.S_ISLNK(info.st_mode) else path.read_bytes() if stat.S_ISREG(info.st_mode) else None
            result[str(path.relative_to(repo))]=(info.st_mode,info.st_nlink,payload)
        return result
    state={}
    def finalize(checked):
        repo=binding.repo_root
        native=repo/p.ROOT_PATH
        if alias_kind=='configured-site':
            source=repo/'config.yml'
            source.write_text(source.read_text().replace('site_dir: site','site_dir: data/qledger'))
            config.load.cache_clear()
        elif alias_kind=='accepted-restore':
            alias=repo/'site/restored.html';alias.unlink();alias.write_text('current regular page')
        elif alias_kind in ('asset-parent','quality-parent'):
            alias=repo/('site/assets' if alias_kind=='asset-parent' else 'data/quality')
            alias.parent.mkdir(parents=True,exist_ok=True)
            alias.symlink_to(repo/'data/qledger',target_is_directory=True)
        else:
            rel={'data-base-copy':'site/data_base.js','html-write':'site/alias.html',  # ci-trigger-closure: data — temporary fixture destination, never a repository read
                 'template-write':'templates/index.html','hardlink':'site/native-alias.html'}[alias_kind]  # ci-trigger-closure: data — temporary fixture path, never a repository read
            alias=repo/rel;alias.unlink(missing_ok=True)
            if alias_kind=='hardlink':os.link(native,alias)
            else:alias.symlink_to(native)
        state['before']=native.read_bytes()
        state['image']=image(repo)
        state['index']=(repo/'.git/index').read_bytes()
        return engine.finalize_daily_engine_outputs(checked)
    binding,callback,gate=setup(causal,monkeypatch,finalize);pins(gate)
    git(binding.repo_root,'read-tree',next(iter(binding.original_result_targets.values())).accepted_tip_oid)
    with pytest.raises(p.SnapshotIntegrityError):invoke(binding,callback,gate)
    assert gate.held
    assert (binding.repo_root/p.ROOT_PATH).read_bytes()==state['before'], 'normalizer changed verified native ROOT through alias before refusing'
    assert not touched and image(binding.repo_root)==state['image']
    assert (binding.repo_root/'.git/index').read_bytes()==state['index']
    config.load.cache_clear()
