"""Synthetic committed-generation qualification; no production/source admission."""
import copy
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from app import company_disclosures as api
from engine.company_intelligence.current_context_runtime import CommittedCompanyContextOwner
from engine.company_intelligence import current_context_runtime as runtime
from tests.test_company_disclosures_api import boundary, context_fixture, context_get
from tests.test_company_issuer_disclosures import sample


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()


def commit(repo):
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'synthetic generation')
    git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    return git(repo, 'rev-parse', 'HEAD')


@pytest.fixture
def installed(tmp_path, context_fixture):
    repo = tmp_path / 'repo'; repo.mkdir()
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'user.email', 'synthetic@example.invalid')
    git(repo, 'config', 'user.name', 'Synthetic fixture')
    records = copy.deepcopy(context_fixture[2])
    records['issuer_master'][0]['n_securities'] = 2
    bundle = context_fixture[3](records)
    for name, path in runtime._ARTIFACTS.items():
        target = repo / path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(getattr(bundle, name))
    receipt = dict(producer=runtime._PRODUCER, notes=[], generated_at='2026-01-01T00:00:00',
        dataset_ids=[f'reference.{n}' for n in records],
        authority=dict(identity_authority='canonical_exact_identity', signal_authority='none',
            ranking_authority='none', trade_authority='none', consumers=['gmi.identity_resolution/v1']),
        row_counts={**{n: len(v) for n,v in records.items()}, 'vendor_alias_rows_readable': 2})
    (repo / runtime._RECEIPT).write_text(json.dumps(receipt))
    contracts = []
    for name, path in runtime._ARTIFACTS.items():
        key = 'security_id' if name == 'security_master' else 'issuer_id' if name == 'issuer_master' else 'vendor_symbol'
        contracts.append(dict(dataset_id=f'reference.{name}', layer='L2', status='PRODUCED',
            owner='macro-dashboard', producer=runtime._PRODUCER, storage=path, format='parquet',
            grain=[key], temporal_profile='SNAPSHOT_SERIES', timezone='UTC', frequency='on_demand',
            conflict_policy='DOMAIN_AUTHORITY', version='0.1.0'))
    (repo / 'config').mkdir()
    (repo / runtime._REGISTRY).write_text(yaml.safe_dump({'datasets': contracts}))
    head = commit(repo)
    return repo, CommittedCompanyContextOwner(repo), head, records


def resolve(installed):
    return installed[1].current_identity_bundle(api.PURPOSE, api.AUDIENCE)


def test_context_runtime_real_git_reads_only_committed_bundle(installed, context_fixture, boundary):
    repo, owner, head, _ = installed
    context_fixture[0].app.state.company_context_owner = owner
    del context_fixture[0].app.state.company_disclosure_reader
    (repo / runtime._ARTIFACTS['issuer_master']).write_bytes(b'uncommitted producer intermediate')
    result = context_get(context_fixture)
    assert result.status_code == 200, result.text
    assert result.json()['identity_receipt']['source_commit'] == head
    assert 'private_store' not in boundary[3] and boundary[4].calls == 0
    assert git(repo, 'status', '--porcelain').endswith('data/reference/issuer_master.parquet')


def test_generation_is_stable_across_unrelated_install_and_tracks_receipt_change(installed):
    repo, owner, head, _ = installed
    assert resolve(installed).source_commit == head
    (repo / 'README.md').write_text('unrelated deployment')
    commit(repo)
    assert resolve(installed).source_commit == head
    receipt = json.loads((repo / runtime._RECEIPT).read_text())
    receipt['code_version'] = 'new producer metadata'
    (repo / runtime._RECEIPT).write_text(json.dumps(receipt))
    new = commit(repo)
    assert resolve(installed).source_commit == new


def test_current_registry_revocation_invalidates_cached_positive(installed):
    repo, *_ = installed
    assert resolve(installed) is not None
    path = repo / runtime._REGISTRY; value = yaml.safe_load(path.read_text())
    value['datasets'][0]['status'] = 'PROPOSED'; path.write_text(yaml.safe_dump(value))
    commit(repo)
    assert resolve(installed) is None


@pytest.mark.parametrize('mutation', ['wrong_producer', 'missing_consumer', 'authority', 'notes',
                                     'row_count', 'future', 'missing_dataset'])
def test_mismatched_producer_receipt_is_not_qualified(installed, mutation):
    repo, *_ = installed; path = repo / runtime._RECEIPT; data = json.loads(path.read_text())
    if mutation == 'wrong_producer': data['producer'] = 'another.py'
    elif mutation == 'missing_consumer': data['authority']['consumers'] = []
    elif mutation == 'authority': data['authority']['trade_authority'] = 'yes'
    elif mutation == 'notes': data['notes'] = ['partial producer output']
    elif mutation == 'row_count': data['row_counts']['security_master'] = 3
    elif mutation == 'future': data['generated_at'] = '2999-01-01T00:00:00'
    elif mutation == 'missing_dataset': data['dataset_ids'].remove('reference.issuer_master')
    path.write_text(json.dumps(data)); commit(repo)
    assert resolve(installed) is None


@pytest.mark.parametrize('mutation', ['dangling_alias', 'issuer_census', 'issuer_cik', 'duplicate_registry'])
def test_incompatible_committed_bytes_are_not_a_generation(installed, context_fixture, mutation):
    repo, _, _, records = installed
    if mutation == 'duplicate_registry':
        path = repo / runtime._REGISTRY; data = yaml.safe_load(path.read_text())
        data['datasets'].append(data['datasets'][0]); path.write_text(yaml.safe_dump(data))
    else:
        if mutation == 'dangling_alias': records['vendor_aliases'][0]['security_id'] = 'SEC:US-XNAS-LOST'
        elif mutation == 'issuer_census': records['issuer_master'][0]['n_securities'] = 3
        elif mutation == 'issuer_cik': records['issuer_master'][0]['cik'] = '0000000002'
        bundle = context_fixture[3](records)
        for name, path in runtime._ARTIFACTS.items(): (repo / path).write_bytes(getattr(bundle, name))
    commit(repo)
    assert resolve(installed) is None


def test_unprotected_head_and_missing_protected_ref_refuse(installed):
    repo, _, head, _ = installed
    (repo / 'unlanded.txt').write_text('not landed')
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'not protected')
    assert resolve(installed) is None
    git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    assert resolve(installed) is not None
    git(repo, 'update-ref', '-d', 'refs/remotes/origin/main')
    assert resolve(installed) is None


def test_detached_protected_install_is_supported(installed):
    repo, _, head, _ = installed
    git(repo, 'checkout', '--detach', head)
    assert resolve(installed).source_commit == head


@pytest.mark.parametrize('kind', ['oversized', 'symlink', 'missing'])
def test_unbounded_or_nonregular_objects_refuse(installed, kind):
    repo, *_ = installed; path = repo / runtime._ARTIFACTS['vendor_aliases']
    if kind == 'oversized': path.write_bytes(b'x' * (runtime._MAX_BYTES + 1))
    elif kind == 'symlink': path.unlink(); path.symlink_to('security_master.parquet')
    else: path.unlink()
    commit(repo)
    assert resolve(installed) is None


def test_git_never_lazy_fetches_and_missing_objects_refuse(installed, monkeypatch):
    calls = []; real = runtime.subprocess.run
    def guarded(command, **kwargs):
        calls.append(command)
        assert command[:2] == ['git', '--no-replace-objects']
        assert kwargs['env']['GIT_ALLOW_PROTOCOL'] == ''
        assert kwargs['env']['GIT_NO_LAZY_FETCH'] == '1'
        assert kwargs['env']['GIT_OPTIONAL_LOCKS'] == '0'
        assert kwargs['timeout'] == 3
        if 'cat-file' in command: raise subprocess.CalledProcessError(1, command)
        return real(command, **kwargs)
    monkeypatch.setattr(runtime.subprocess, 'run', guarded)
    assert resolve(installed) is None and any('cat-file' in c for c in calls)


def test_head_change_during_resolution_refuses(installed, monkeypatch):
    owner = installed[1]; calls = 0; real = owner._head
    def changing():
        nonlocal calls
        calls += 1
        return real() if calls == 1 else 'b' * 40
    monkeypatch.setattr(owner, '_head', changing)
    assert resolve(installed) is None


def test_wrong_purpose_never_opens_repo(installed, monkeypatch):
    monkeypatch.setattr(installed[1], '_git', lambda *a, **k: pytest.fail('Git opened for unadopted purpose'))
    assert installed[1].current_identity_bundle('public', api.AUDIENCE) is None


def test_main_mount_keeps_identity_independent_and_disclosure_readonly(boundary):
    from engine.company_intelligence.issuer_disclosure_owner import CurrentDisclosureOwner, ReadOnlyLocalObjects
    main = boundary[-1]
    assert type(main.app.state.company_context_owner) is CommittedCompanyContextOwner
    assert main.app.state.company_context_owner.repo == main.REPO
    reader = main.app.state.company_disclosure_reader
    assert type(reader.authority) is CurrentDisclosureOwner
    assert reader.authority.source.identity_owner is main.app.state.company_context_owner
    assert type(reader.authority.state) is ReadOnlyLocalObjects
    assert str(reader.authority.state.root) == '/var/lib/macro-company-intelligence/state'
    store = reader.store_factory()
    assert type(store) is ReadOnlyLocalObjects
    assert str(store.root) == '/var/lib/macro-company-intelligence/artifacts'
    assert not hasattr(store, 'put_bytes_strict_conditional')


def rewrite_records(installed, context_fixture, records):
    repo = installed[0]; bundle = context_fixture[3](records)
    for name, path in runtime._ARTIFACTS.items(): (repo / path).write_bytes(getattr(bundle, name))
    path = repo / runtime._RECEIPT; receipt = json.loads(path.read_text())
    for name, rows in records.items(): receipt['row_counts'][name] = len(rows)
    path.write_text(json.dumps(receipt)); return commit(repo)


def test_review_git_environment_cannot_redirect_installed_source(installed, tmp_path, monkeypatch):
    repo, _, head, _ = installed; alternate = tmp_path / 'alternate'
    git(tmp_path, 'clone', '-q', '--no-hardlinks', str(repo), str(alternate))
    git(alternate, 'config', 'user.email', 'synthetic@example.invalid')
    git(alternate, 'config', 'user.name', 'Synthetic fixture')
    path = alternate / runtime._RECEIPT; receipt = json.loads(path.read_text())
    receipt['code_version'] = 'wrong source'; path.write_text(json.dumps(receipt)); commit(alternate)
    monkeypatch.setenv('GIT_DIR', str(alternate / '.git'))
    assert resolve(installed).source_commit == head


@pytest.mark.parametrize('case', ['retired_member', 'unresolved_member'])
def test_review_producer_permitted_members_do_not_block_generation(installed, context_fixture, case):
    records = installed[3]
    if case == 'retired_member':
        records['security_master'].append(dict(records['security_master'][0],
            security_id='SEC:US-XNAS-OLD', listing_key='US-XNAS-OLD',
            issuer_id='ISS:US-XNAS-OLD', security_state='SUPERSEDED', superseded_by='SEC:US-XNAS-AAA'))
    else:
        records['security_master'][1].update(issuer_state='NO_ISSUER_EVIDENCE', issuer_cik=None)
    rewrite_records(installed, context_fixture, records)
    assert resolve(installed) is not None


@pytest.mark.parametrize('case', ['wrong_issuer_kind', 'malformed_unaliased_security'])
def test_review_all_stored_ids_are_canonical(installed, context_fixture, case):
    records = installed[3]
    if case == 'wrong_issuer_kind':
        records['security_master'][1]['issuer_id'] = 'SEC:US-XNAS-OTHER'
        records['issuer_master'][0]['n_securities'] = 1
        records['issuer_master'].append(dict(records['issuer_master'][0], issuer_id='SEC:US-XNAS-OTHER'))
    else:
        records['security_master'].append(dict(records['security_master'][0], security_id='BROKEN'))
        records['issuer_master'][0]['n_securities'] = 3
    rewrite_records(installed, context_fixture, records)
    assert resolve(installed) is None


def test_review_resolved_member_requires_positive_evidence(installed, context_fixture):
    records = installed[3]
    records['security_master'][1].update(issuer_id='ISS:US-XNAS-OTHER', issuer_cik=None)
    records['issuer_master'][0]['n_securities'] = 1
    records['issuer_master'].append(dict(records['issuer_master'][0],
        issuer_id='ISS:US-XNAS-OTHER', cik=None))
    rewrite_records(installed, context_fixture, records)
    assert resolve(installed) is None


def test_git243_command_compatibility(installed, monkeypatch):
    real = runtime.subprocess.run
    def old_git(command, **kwargs):
        if '--no-lazy-fetch' in command:
            raise subprocess.CalledProcessError(129, command, stderr=b'unknown option: --no-lazy-fetch')
        return real(command, **kwargs)
    monkeypatch.setattr(runtime.subprocess, 'run', old_git)
    assert resolve(installed) is not None


@pytest.mark.parametrize('protocol', ['file', 'synthetic'])
def test_missing_promisor_fallback_cannot_start_transport_or_mutate_source(installed, tmp_path, monkeypatch, protocol):
    import hashlib
    repo, owner, _, _ = installed
    remote = tmp_path / 'remote.git'
    git(tmp_path, 'clone', '-q', '--bare', str(repo), str(remote))
    sentinel = tmp_path / 'helper-started'
    bindir = tmp_path / 'bin'; bindir.mkdir()
    helper = bindir / 'git-remote-synthetic'
    helper.write_text('#!/bin/sh\ntouch "'+str(sentinel)+'"\nexit 1\n'); helper.chmod(0o755)
    monkeypatch.setenv('PATH', str(bindir)+':'+runtime.os.environ['PATH'])
    git(repo, 'config', 'remote.origin.url', str(remote) if protocol == 'file' else 'synthetic::unused')
    git(repo, 'config', 'remote.origin.promisor', 'true')
    git(repo, 'config', 'remote.origin.partialclonefilter', 'blob:none')
    git(repo, 'config', 'protocol.'+protocol+'.allow', 'always')
    oid = git(repo, 'rev-parse', 'HEAD:'+runtime._ARTIFACTS['security_master'])
    missing = repo / '.git' / 'objects' / oid[:2] / oid[2:]
    assert missing.is_file(); missing.unlink()
    def snapshot():
        return {str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in repo.rglob('*') if p.is_file()}
    before = snapshot(); real = runtime.subprocess.run; errors = []
    def without_lazy_suppression(command, **kwargs):
        assert kwargs['env']['GIT_ALLOW_PROTOCOL'] == ''
        # Exercise the actual fallback, as on Git2.43, independently of the
        # newer Git environment variable's ability to suppress lazy fetching.
        kwargs['env'].pop('GIT_NO_LAZY_FETCH', None)
        try:
            return real(command, **kwargs)
        except subprocess.CalledProcessError as exc:
            errors.append(exc.stderr.decode())
            raise
    monkeypatch.setattr(runtime.subprocess, 'run', without_lazy_suppression)
    assert resolve(installed) is None
    with pytest.raises(subprocess.CalledProcessError):
        owner._git('cat-file', '-p', oid)
    assert any("transport '"+protocol+"' not allowed" in error for error in errors)
    assert not sentinel.exists() and not missing.exists()
    assert snapshot() == before
