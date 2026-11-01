"""Focused fixtures for the same-process producer preflight gate."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import os
import stat
import sys

import pytest

from engine.company_intelligence import issuer_disclosure_owner as o
from engine.company_intelligence import issuer_disclosure_preflight as preflight
from engine.company_intelligence import issuer_disclosures as n
from engine.company_intelligence import issuer_disclosure_publication as p
from scripts import publish_company_disclosure as cli


class FixtureSource:
    def __init__(self, snapshot, git):
        self.value = snapshot
        self.git = git
        self.calls = 0
        self.action = None

    def snapshot(self):
        self.calls += 1
        if self.action:
            self.action()
        return self.value


class GitStub:
    def __init__(self, repo, head, blobs=None):
        self.repo = Path(repo)
        self.head = head
        self.blobs = dict(blobs or {})

    def _head(self):
        return self.head

    def _objects(self, commit, paths):
        n._require(commit == self.head, 'PREFLIGHT_PRODUCER_HEAD')
        result = {}
        for path in paths:
            data = self.blobs[path]
            result[path] = ('b' * 40, len(data))
        return result

    def _read(self, objects):
        return {path: self.blobs[path] for path in objects}

    def _git(self, *args):
        raise n.DisclosureError('PREFLIGHT_PRODUCER_HEAD')


def _stat(pid, comm, starttime):
    rest = ['S'] + ['0'] * 18 + [str(starttime)]
    assert len(rest) == 20
    return f'{pid} ({comm}) ' + ' '.join(rest)


def _now(offset=0):
    moment = datetime.now(timezone.utc) + timedelta(seconds=offset)
    return moment.isoformat().replace('+00:00', 'Z')


def make_snapshot(code='a' * 40, status='PROPOSED'):
    edition = {
        'schema': n.EDITION_SCHEMA,
        'disclosure_id': n.disclosure_id('issuer:mu', 'src-1'),
        'issuer_id': 'issuer:mu', 'source_key': 'src-1', 'revision': 1, 'previous': None,
        'source_sha256': '0' * 64, 'source_byte_length': 12,
        'published_date': '2024-02-26', 'published_at': None, 'publication_precision': 'date',
        'known_at': '2024-02-27T00:00:00Z',
    }
    fact = {
        'schema': n.FACT_SCHEMA,
        'fact_id': n.fact_id(edition['disclosure_id'], 'claim-1'),
        'claim_key': 'claim-1', 'disclosure_id': edition['disclosure_id'],
        'edition': n.validate_edition(edition).payload(), 'revision': 1, 'previous': None,
        'review_revision': '1' * 64, 'subject_id': 'issuer:mu', 'object_id': 'issuer:nvda',
        'subject_identity': '2' * 64, 'object_identity': '3' * 64,
        'kind': 'product_integration', 'lifecycle': 'planned', 'product': 'widget',
        'platform': 'gpu', 'amount': None, 'economic_share': None,
        'span': {'start_byte': 0, 'end_byte': 12, 'text_sha256': '4' * 64},
        'known_at': '2024-02-27T00:00:00Z',
    }
    n.validate_fact(fact)
    spec = {'schema': 'company_intelligence.native_owner_decision/v1', 'case_id': 'fixture-case',
            'ruling_reference': {'sha256': '5' * 64, 'byte_length': 2}, 'edition': edition,
            'fact': fact, 'identities': {}, 'temporal_decision': {},
            'correction_decision': {}, 'semantic_review': {}}
    return o.OwnerSnapshot(code, n._canonical(spec), '6' * 64, '7' * 64, status)


def make_census(code='a' * 40, **changes):
    census = {
        'schema': preflight.CENSUS_SCHEMA,
        'captured_at': _now(-5),
        'pid': 4242,
        'starttime': 99,
        'mountnamespace': 'mnt:[999999]',
        'cgroup': '/system.slice/macro-api.service',
        'unit': 'macro-api.service',
        'invocation_id': 'a' * 32,
        'qualified_runtime_source': {
            'code_version': code, 'repo': '/opt/macro', 'attestation_sha256': 'b' * 64,
        },
        'digests': {'census_sha256': '0' * 64},
    }
    census.update(changes)
    if 'qualified_runtime_source' in changes:
        census['qualified_runtime_source'] = dict(census['qualified_runtime_source'])
    census['digests'] = {'census_sha256': preflight.census_digest(census)}
    return census


def make_expected(repo, code='a' * 40, uid=None, **changes):
    expected = {
        'schema': preflight.EXPECTED_SCHEMA,
        'code_version': code,
        'mode': 'STAGE_MEMBERS',
        'root': str(preflight.PRODUCTION_ROOT),
        'producer': {'uid': os.geteuid() if uid is None else uid, 'repo': str(Path(repo))},
        'api_census': make_census(code),
        'census_max_age_seconds': 300,
    }
    expected.update(changes)
    if 'api_census' not in changes:
        expected['api_census'] = make_census(code)
    return expected


def provenance_for(git, modules=None):
    return {
        'kind': 'on_disk_provenance',
        'premises': ['fresh_trusted_interpreter', 'qualified_deployment'],
        'attestation': 'on_disk_source_hashes_match_committed_blobs',
        'not_claimed': 'exhaustive_loaded_code_attestation',
        'head': git._head(),
        'modules': [{'module': 'engine.company_intelligence.issuer_disclosures',
                     'path': 'engine/company_intelligence/issuer_disclosures.py',
                     'sha256': 'c' * 64, 'blob_sha256': 'c' * 64}],
    }


def provision(root):
    for key in preflight.ROOT_KEYS:
        path = Path(root) / key
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o700)


def write_expected(path, expected):
    path.write_bytes(json.dumps(expected, sort_keys=True, allow_nan=False).encode() + b'\n')
    os.chmod(path, 0o600)


def api_ok(census):
    return {
        'pid': census['pid'], 'starttime': census['starttime'],
        'mountnamespace': census['mountnamespace'], 'cgroup': census['cgroup'],
        'unit': census['unit'], 'invocation_id': census['invocation_id'],
        'qualified_runtime_source': census['qualified_runtime_source'],
    }


def stub_linux_collectors(monkeypatch):
    """Synthetic Linux identity; fixtures never inspect the host's real API."""
    monkeypatch.setattr(preflight, 'read_process_identity', lambda pid='self': {
        'pid': os.getpid(), 'starttime': 12345, 'uid': os.geteuid(),
        'exe': '/fixture/python', 'cwd': '/fixture', 'mountnamespace': 'mnt:[12345]'})
    monkeypatch.setattr(preflight, 'descriptor_mount_id', lambda fd: '1')
    monkeypatch.setattr(preflight, 'read_mountinfo', lambda text=None:
        preflight.parse_mountinfo(text or '1 0 8:0 / / rw - ext4 /dev/fixture rw\n'))


def stub_gate(monkeypatch, source):
    stub_linux_collectors(monkeypatch)
    monkeypatch.setattr(preflight, 'collect_on_disk_provenance', provenance_for)
    monkeypatch.setattr(preflight, 'revalidate_api_census', lambda census, **k: api_ok(census))
    monkeypatch.setattr(cli.owner, 'CommittedDisclosureSource', lambda repo: source)
    monkeypatch.setattr(cli, 'publish_generation',
                        lambda *a, **k: {'status': 'MEMBERS_OBSERVED_NOT_ADOPTED'})
    class Dummy:
        def __init__(self, root):
            self.root = Path(root)
    monkeypatch.setattr(cli, 'LocalStore', Dummy)


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / 'root'
    repo = tmp_path / 'repo'
    repo.mkdir()
    monkeypatch.setattr(preflight, 'PRODUCTION_ROOT', root)
    provision(root)
    snapshot = make_snapshot()
    git = GitStub(repo, snapshot.code_version)
    source = FixtureSource(snapshot, git)
    expected = make_expected(repo)
    expected_path = tmp_path / 'expected.json'
    write_expected(expected_path, expected)
    stub_gate(monkeypatch, source)
    return type('Env', (), dict(root=root, repo=repo, source=source, expected=expected,
                                expected_path=expected_path, tmp=tmp_path))()


def run_cli(env, operation='op1', extra=None):
    argv = ['publisher', '--repo', str(env.repo), '--root', str(env.root),
            '--operation-id', operation, '--expected-deployment-json', str(env.expected_path),
            '--expect-empty']
    if extra:
        argv.extend(extra)
    old = os.umask(0o077)
    try:
        sys.argv = argv
        return cli.main()
    finally:
        os.umask(old)


def test_stat_starttime_survives_spaces_and_parentheses():
    text = _stat(12, 'python3 (main)', 12345)
    assert preflight.parse_stat_starttime(text) == 12345
    messy = '99 (py (x) y) R 1 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 777 0 0 0'
    assert preflight.parse_stat_starttime(messy) == 777


def test_mountinfo_unescape_and_deepest_rw():
    text = (
        '1 0 8:0 / / rw - ext4 /dev/sda rw\n'
        '2 1 8:1 / /tmp rw,nosuid - ext4 /dev/sdb rw\n'
        '3 2 8:2 / /tmp/my\\040data rw - ext4 /dev/sdc rw\n'
        '4 2 8:3 / /tmp/my\\040data/root ro - ext4 /dev/sdd ro\n'
    )
    mounts = preflight.parse_mountinfo(text)
    point = preflight.unescape_mount('/tmp/my\\040data')
    assert point == '/tmp/my data'
    deepest = preflight.covering_mount(mounts, '/tmp/my data/root/state')
    assert deepest['mountpoint'] == '/tmp/my data/root'
    assert 'ro' in deepest['options'].split(',')
    writer = preflight.covering_mount(mounts, '/tmp/my data/other')
    assert writer['mountpoint'] == '/tmp/my data'
    preflight._write_options(writer['options'])


def test_expected_deployment_rejects_duplicate_keys_and_nonfinite(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, 'PRODUCTION_ROOT', tmp_path)
    good = make_expected(tmp_path / 'repo')
    (tmp_path / 'repo').mkdir()
    path = tmp_path / 'dup.json'
    path.write_bytes(b'{"schema":"company_intelligence.expected_deployment/v1","schema":"x"}\n')
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_JSON_INVALID'):
        preflight.load_expected_deployment(path)
    path.write_bytes(b'{"schema":"x","n":NaN}\n')
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_JSON_INVALID'):
        preflight.load_expected_deployment(path)
    write_expected(path, good)
    loaded = preflight.load_expected_deployment(path)
    assert loaded['code_version'] == good['code_version']


def test_census_old_future_and_after_invocation():
    expected = make_expected('/repo')
    now = datetime.now(timezone.utc)
    expected['api_census']['captured_at'] = (now - timedelta(seconds=301)).isoformat().replace('+00:00', 'Z')
    expected['api_census']['digests'] = {'census_sha256': preflight.census_digest(expected['api_census'])}
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_CENSUS_STALE'):
        preflight.evaluate_census_time(expected, now.isoformat(), now.isoformat())
    expected['api_census']['captured_at'] = (now + timedelta(seconds=30)).isoformat().replace('+00:00', 'Z')
    expected['api_census']['digests'] = {'census_sha256': preflight.census_digest(expected['api_census'])}
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_CENSUS_FUTURE'):
        preflight.evaluate_census_time(expected, now.isoformat(), now.isoformat())
    expected['api_census']['captured_at'] = now.isoformat().replace('+00:00', 'Z')
    expected['api_census']['digests'] = {'census_sha256': preflight.census_digest(expected['api_census'])}
    invoked = (now - timedelta(seconds=10)).isoformat()
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_CENSUS_AFTER_INVOCATION'):
        preflight.evaluate_census_time(expected, invoked, now.isoformat())


def test_api_pid_reuse_start_change_ns_cgroup_invocation():
    census = make_census()
    unit = (
        f"MainPID={census['pid']}\nInvocationID={census['invocation_id']}\n"
        f"ControlGroup={census['cgroup']}\nId={census['unit']}\n"
    )
    preflight.revalidate_api_census(
        census, stat_text=_stat(census['pid'], 'api', census['starttime']),
        mountnamespace=census['mountnamespace'],
        cgroup_text=f"0::{census['cgroup']}\n", unit_properties=unit)
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_API_STARTTIME'):
        preflight.revalidate_api_census(
            census, stat_text=_stat(census['pid'], 'api', census['starttime'] + 1),
            mountnamespace=census['mountnamespace'],
            cgroup_text=f"0::{census['cgroup']}\n", unit_properties=unit)
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_API_NAMESPACE'):
        preflight.revalidate_api_census(
            census, stat_text=_stat(census['pid'], 'api', census['starttime']),
            mountnamespace='mnt:[1]',
            cgroup_text=f"0::{census['cgroup']}\n", unit_properties=unit)
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_API_CGROUP'):
        preflight.revalidate_api_census(
            census, stat_text=_stat(census['pid'], 'api', census['starttime']),
            mountnamespace=census['mountnamespace'],
            cgroup_text='0::/other.slice/other.service\n', unit_properties=unit)
    drifted = unit.replace(census['invocation_id'], 'b' * 32)
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_API_INVOCATION'):
        preflight.revalidate_api_census(
            census, stat_text=_stat(census['pid'], 'api', census['starttime']),
            mountnamespace=census['mountnamespace'],
            cgroup_text=f"0::{census['cgroup']}\n", unit_properties=drifted)
    reused = unit.replace(f"MainPID={census['pid']}", 'MainPID=7')
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_API_PID'):
        preflight.revalidate_api_census(
            census, stat_text=_stat(census['pid'], 'api', census['starttime']),
            mountnamespace=census['mountnamespace'],
            cgroup_text=f"0::{census['cgroup']}\n", unit_properties=reused)


def test_producer_namespace_change_and_equal_api(env):
    capture = {'process': preflight.read_process_identity('self'),
               'captured_at': _now(-1),
               'provenance': provenance_for(env.source.git)}
    intent = p.prepare_publication(env.source, o.ReadOnlyLocalObjects(env.root / 'state'),
                                   expected_current_version=None)
    env.source.calls = 0
    live = dict(capture['process'])
    live['mountnamespace'] = env.expected['api_census']['mountnamespace']
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_NAMESPACE_CHANGED'):
        preflight.finalize_gate(env.expected, capture, env.source, intent, preflight.read_mountinfo(),
                                now=_now(), process=live, api=api_ok(env.expected['api_census']),
                                provenance=capture['provenance'], modules={})
    capture['process'] = dict(capture['process'])
    capture['process']['mountnamespace'] = env.expected['api_census']['mountnamespace']
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_NAMESPACE_SHARED'):
        preflight.finalize_gate(env.expected, capture, env.source, intent, preflight.read_mountinfo(),
                                now=_now(), process=capture['process'],
                                api=api_ok(env.expected['api_census']),
                                provenance=capture['provenance'], modules={})


def test_module_origin_mismatch_and_head_mismatch(tmp_path):
    repo = tmp_path / 'repo'
    from types import SimpleNamespace
    modules, blobs = {}, {}
    for name in preflight.MODULE_NAMES:
        rel = name.replace('.', '/') + '.py'
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'def fixture():\n    return 1\n')
        blobs[rel] = path.read_bytes()
        modules[name] = SimpleNamespace(__file__=str(path))
    git = GitStub(repo, 'a' * 40, blobs)
    Mod = modules['scripts.publish_company_disclosure']
    # Exercise the actual python -m module identity, rather than requiring an
    # import alias that the documented production invocation does not create.
    Mod.__spec__ = SimpleNamespace(name='scripts.publish_company_disclosure')
    modules['__main__'] = modules.pop('scripts.publish_company_disclosure')
    record = preflight.collect_on_disk_provenance(git, modules)
    assert record['not_claimed'] == 'exhaustive_loaded_code_attestation'
    assert record['head'] == 'a' * 40
    git.blobs[rel] = b'different'
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_MODULE_ORIGIN'):
        preflight.collect_on_disk_provenance(git, modules)
    outside = tmp_path / 'outside.py'
    outside.write_bytes(path.read_bytes())
    Mod.__file__ = str(outside)
    git.blobs[rel] = path.read_bytes()
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_MODULE_ORIGIN'):
        preflight.collect_on_disk_provenance(git, modules)
    git.head = 'not-a-commit'
    Mod.__file__ = str(path)
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_PRODUCER_HEAD'):
        preflight.collect_on_disk_provenance(git, modules)


def test_nofollow_missing_root_ro_producer(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, 'PRODUCTION_ROOT', tmp_path)
    uid = os.geteuid()
    monkeypatch.setattr(preflight, 'descriptor_mount_id', lambda fd: '1')
    mounts = preflight.parse_mountinfo('1 0 8:0 / / rw - ext4 /dev/fixture rw\n')
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_ROOT_MISSING'):
        preflight.qualify_roots(tmp_path, uid, mounts)
    provision(tmp_path)
    preflight.qualify_roots(tmp_path, uid, mounts)
    target = tmp_path / 'real-state'
    target.mkdir()
    os.chmod(target, 0o700)
    state = tmp_path / 'state'
    os.rename(state, tmp_path / 'state-orig')
    state.symlink_to(target)
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_ROOT_SYMLINK'):
        preflight.qualify_roots(tmp_path, uid, mounts)
    os.remove(state)
    os.rename(tmp_path / 'state-orig', state)
    ro = (
        '1 0 8:0 / / rw - ext4 /dev/sda rw\n'
        f'2 1 8:1 / {tmp_path} ro - ext4 /dev/sdb ro\n'
    )
    monkeypatch.setattr(preflight, 'descriptor_mount_id', lambda fd: '2')
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_MOUNT_RO'):
        preflight.qualify_roots(tmp_path, uid, preflight.parse_mountinfo(ro))


def test_passing_gate_keeps_exact_intent_and_stores_evidence(env, monkeypatch):
    prepared = []
    original = cli.prepare_publication

    def once(*args, **kwargs):
        intent = original(*args, **kwargs)
        prepared.append(deepcopy(intent))
        return intent

    monkeypatch.setattr(cli, 'prepare_publication', once)
    stores = []

    class Watch:
        def __init__(self, root):
            stores.append(Path(root))
            self.root = Path(root)

    monkeypatch.setattr(cli, 'LocalStore', Watch)
    assert run_cli(env) == 0
    assert len(prepared) == 1
    receipt = json.loads((env.root / 'publisher/operations/op1.json').read_text())
    assert receipt['intent'] == prepared[0]
    assert set(receipt['intent']) == {
        'schema', 'manifest', 'manifest_reference', 'expected_current_version',
        'expected_current_sha256', 'mode'}
    assert receipt['producer_preflight_sha256'] == preflight.evidence_digest(receipt['producer_preflight'])
    assert receipt['producer_preflight']['schema'] == preflight.EVIDENCE_SCHEMA
    assert receipt['producer_preflight']['not_claimed'] == 'exhaustive_loaded_code_attestation'
    assert receipt['producer_preflight']['intent_binding']['mode'] == 'STAGE_MEMBERS'
    assert receipt['state'] == 'STARTED'
    assert env.source.calls == 2
    assert len(stores) == 2
    assert (env.root / 'publisher/operations/op1.result.json').is_file()
    assert not (env.root / 'state/current.json').exists()
    assert list((env.root / 'state').glob('**/*')) == [] or all(
        p.is_dir() for p in (env.root / 'state').rglob('*'))


def test_source_mode_drift_during_prepare(env, monkeypatch, capsys):
    def drift():
        if env.source.calls > 1:
            env.source.value = replace(env.source.value, dataset_status='PRODUCED')

    env.source.action = drift
    stores = []

    class Boom:
        def __init__(self, root):
            stores.append(root)
            raise AssertionError('LocalStore constructed')

    monkeypatch.setattr(cli, 'LocalStore', Boom)
    called = []
    monkeypatch.setattr(cli, 'publish_generation', lambda *a, **k: called.append(1))
    assert run_cli(env) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {'automatic_retry_permitted': False, 'error_code': 'PREFLIGHT_MODE_DRIFT',
                       'state': 'REFUSED'}
    assert not (env.root / 'publisher/operations/op1.json').exists()
    assert stores == [] and called == []
    assert env.source.calls == 2


def test_source_code_version_drift_during_prepare(env, monkeypatch):
    def drift():
        if env.source.calls > 1:
            env.source.value = replace(env.source.value, code_version='b' * 40)

    env.source.action = drift
    monkeypatch.setattr(cli, 'LocalStore', lambda root: (_ for _ in ()).throw(AssertionError('store')))
    assert run_cli(env) == 1
    assert not list((env.root / 'publisher/operations').glob('*'))


def test_changed_api_binding_refuses_before_reserve(env, monkeypatch):
    monkeypatch.setattr(preflight, 'revalidate_api_census',
                        lambda census, **k: (_ for _ in ()).throw(n.DisclosureError('PREFLIGHT_API_PID')))
    monkeypatch.setattr(cli, 'LocalStore', lambda root: (_ for _ in ()).throw(AssertionError('store')))
    assert run_cli(env) == 1
    assert not (env.root / 'publisher/operations/op1.json').exists()


@pytest.mark.parametrize('kind', ['intent', 'outcome'])
def test_existing_intent_or_outcome_refuses_without_store(env, monkeypatch, kind):
    name = 'op1.json' if kind == 'intent' else 'op1.result.json'
    target = env.root / 'publisher/operations' / name
    target.write_bytes(b'{"existing":true}\n')
    before = target.read_bytes()
    stores = []

    class Boom:
        def __init__(self, root):
            stores.append(root)
            raise AssertionError('LocalStore constructed')

    monkeypatch.setattr(cli, 'LocalStore', Boom)
    snaps = env.source.calls
    assert run_cli(env) == 1
    assert target.read_bytes() == before
    if kind == 'outcome':
        assert not (env.root / 'publisher/operations/op1.json').exists()
    else:
        assert list((env.root / 'publisher/operations').iterdir()) == [target]
    assert stores == []
    assert env.source.calls == snaps


def test_reserve_eexist_does_not_create(tmp_path):
    ops = tmp_path / 'ops'
    ops.mkdir()
    fd = preflight.open_directory(ops)
    try:
        cli._reserve(fd, 'x.json', {'a': 1})
        original = (ops / 'x.json').read_bytes()
        with pytest.raises(n.DisclosureError, match='RESERVATION_EXISTS') as error:
            cli._reserve(fd, 'x.json', {'a': 2})
        assert error.value.effect_unknown is False
        assert (ops / 'x.json').read_bytes() == original
    finally:
        os.close(fd)


@pytest.mark.parametrize('fault', ['write', 'fsync'])
def test_post_create_write_fsync_uncertainty(tmp_path, monkeypatch, fault):
    ops = tmp_path / 'ops'
    ops.mkdir()
    journal = []
    real_open = os.open

    def tracked(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if flags & os.O_EXCL:
            journal.append(fd)
        return fd

    monkeypatch.setattr(os, 'open', tracked)
    if fault == 'write':
        real_write = os.write

        def boom(fd, data):
            if fd in journal:
                raise OSError('journal short write')
            return real_write(fd, data)

        monkeypatch.setattr(os, 'write', boom)
    else:
        real_fsync = os.fsync

        def boom(fd):
            if fd in journal:
                raise OSError('fsync failed')
            return real_fsync(fd)

        monkeypatch.setattr(os, 'fsync', boom)
    fd = preflight.open_directory(ops)
    try:
        with pytest.raises(n.DisclosureError) as error:
            cli._reserve(fd, 'y.json', {'k': 'v'})
        assert error.value.effect_unknown is True
        assert error.value.code == 'RECONCILIATION_REQUIRED'
        assert (ops / 'y.json').exists()
        assert error.value.automatic_retry_permitted is False
    finally:
        os.close(fd)


def test_cli_post_create_uncertainty_does_not_publish(env, monkeypatch):
    journal = []
    real_open = os.open

    def tracked(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if flags & os.O_EXCL:
            journal.append(fd)
        return fd

    monkeypatch.setattr(os, 'open', tracked)
    real_write = os.write

    def boom(fd, data):
        if fd in journal:
            raise OSError('journal short write')
        return real_write(fd, data)

    monkeypatch.setattr(os, 'write', boom)
    published = []
    monkeypatch.setattr(cli, 'publish_generation', lambda *a, **k: published.append(1))
    stores = []

    class BoomStore:
        def __init__(self, root):
            stores.append(root)
            raise AssertionError('LocalStore constructed')

    monkeypatch.setattr(cli, 'LocalStore', BoomStore)
    assert run_cli(env) == 2
    assert published == [] and stores == []
    assert (env.root / 'publisher/operations/op1.json').exists()
    assert not (env.root / 'publisher/operations/op1.result.json').exists()


def test_preflight_refusal_zero_store_body_member_manifest_pointer(env, monkeypatch):
    env.expected['producer']['uid'] = env.expected['producer']['uid'] + 1
    write_expected(env.expected_path, env.expected)
    stores = []

    class Boom:
        def __init__(self, root):
            stores.append(root)
            raise AssertionError('LocalStore constructed')

    monkeypatch.setattr(cli, 'LocalStore', Boom)
    bodies = []
    monkeypatch.setattr(o, 'bounded_file', lambda *a, **k: bodies.append(a) or b'html')
    assert run_cli(env) == 1
    assert stores == [] and bodies == []
    assert list((env.root / 'publisher/operations').iterdir()) == []
    assert not (env.root / 'state/current.json').exists()
    assert not list((env.root / 'state').glob('generations/*'))
    assert not list((env.root / 'artifacts').rglob('*'))
    assert env.source.calls == 0


@pytest.mark.parametrize('mode', [[], {}])
def test_malformed_deployment_mode_is_a_sanitized_no_effect_refusal(env, capsys, mode):
    env.expected['mode'] = mode
    write_expected(env.expected_path, env.expected)
    assert run_cli(env) == 1
    output = capsys.readouterr()
    assert json.loads(output.out)['state'] == 'REFUSED'
    assert 'Traceback' not in output.err
    assert not list((env.root / 'publisher/operations').iterdir())


def test_ro_mount_change_during_prepare_refuses_before_reservation(env, monkeypatch):
    original = cli.prepare_publication
    def prepare_then_readonly(*args, **kwargs):
        intent = original(*args, **kwargs)
        monkeypatch.setattr(preflight, 'read_mountinfo', lambda: preflight.parse_mountinfo(
            '1 0 8:0 / / ro - ext4 /dev/fixture ro\n'))
        return intent
    monkeypatch.setattr(cli, 'prepare_publication', prepare_then_readonly)
    assert run_cli(env) == 1
    assert not list((env.root / 'publisher/operations').iterdir())


def test_provenance_missing_required_entrypoint_is_refused(tmp_path):
    repo = tmp_path / 'repo'
    modules = {}
    blobs = {}
    from types import SimpleNamespace
    for name in preflight.MODULE_NAMES:
        if name == 'scripts.publish_company_disclosure':
            continue
        rel = name.replace('.', '/') + '.py'
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'# synthetic source\n')
        blobs[rel] = path.read_bytes()
        modules[name] = SimpleNamespace(__file__=str(path))
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_MODULE_ORIGIN'):
        preflight.collect_on_disk_provenance(GitStub(repo, 'a' * 40, blobs), modules)


def test_stacked_visible_ro_mount_is_bound_to_actual_descriptor_before_effects(env, monkeypatch):
    ops = env.root / 'publisher/operations'
    inode = ops.stat().st_ino
    mounts = preflight.parse_mountinfo(
        '1 0 8:0 / / rw - ext4 /dev/fixture rw\n'
        f'2 1 8:0 / {ops} rw - ext4 /dev/fixture rw\n'
        f'3 2 8:0 / {ops} ro - ext4 /dev/fixture rw\n')
    # Both mount views expose the same directory inode, mode, and owner.
    monkeypatch.setattr(preflight, 'read_mountinfo', lambda: mounts)
    monkeypatch.setattr(preflight, 'descriptor_mount_id',
                        lambda fd: '3' if os.fstat(fd).st_ino == inode else '1')
    def forbidden(*args, **kwargs):
        pytest.fail('effect before visible read-only mount refusal')
    monkeypatch.setattr(cli, '_reserve', forbidden)
    monkeypatch.setattr(cli, 'LocalStore', forbidden)
    monkeypatch.setattr(cli, 'RetainedFileSource', forbidden)
    assert run_cli(env) == 1
    assert not list(ops.iterdir())


def test_final_journal_descriptor_mount_must_equal_qualified_mount(env, monkeypatch):
    finalize = preflight.finalize_gate
    def change_after_gate(*args, **kwargs):
        evidence = finalize(*args, **kwargs)
        monkeypatch.setattr(preflight, 'descriptor_mount_id', lambda fd: '99')
        return evidence
    monkeypatch.setattr(preflight, 'finalize_gate', change_after_gate)
    assert run_cli(env) == 1
    assert not list((env.root / 'publisher/operations').iterdir())


def test_descriptor_mount_id_rejects_missing_duplicate_or_unknown(monkeypatch):
    monkeypatch.setattr(preflight, 'read_proc_text', lambda path: 'pos: 0\nmnt_id:\t17\n')
    assert preflight.descriptor_mount_id(12) == '17'
    for text in ['pos: 0\n', 'mnt_id: 17\nmnt_id: 18\n']:
        monkeypatch.setattr(preflight, 'read_proc_text', lambda path, text=text: text)
        with pytest.raises(n.DisclosureError, match='PREFLIGHT_MOUNT_ID'):
            preflight.descriptor_mount_id(12)
    with pytest.raises(n.DisclosureError, match='PREFLIGHT_MOUNT_ID'):
        preflight.exact_mount([], '17')


def test_readonly_filesystem_refuses_despite_rw_mount_option(env, monkeypatch):
    monkeypatch.setattr(preflight, 'read_mountinfo', lambda: preflight.parse_mountinfo(
        '1 0 8:0 / / rw - ext4 /dev/fixture ro\n'))
    assert run_cli(env) == 1
    assert not list((env.root / 'publisher/operations').iterdir())


@pytest.mark.parametrize('failure_point', ['expected_file', 'process', 'operations_open'])
def test_pre_effect_oserror_is_sanitized_and_creates_nothing(env, monkeypatch, capsys, failure_point):
    def fail(*args, **kwargs):
        raise FileNotFoundError('private observation detail')
    if failure_point == 'expected_file':
        env.expected_path.unlink()
    elif failure_point == 'process':
        monkeypatch.setattr(preflight, 'read_process_identity', fail)
    else:
        monkeypatch.setattr(cli, '_directory', fail)
    def forbidden(*args, **kwargs):
        pytest.fail('publication effect after observation failure')
    monkeypatch.setattr(cli, '_reserve', forbidden)
    monkeypatch.setattr(cli, 'LocalStore', forbidden)
    monkeypatch.setattr(cli, 'RetainedFileSource', forbidden)
    assert run_cli(env) == 1
    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert payload['state'] == 'REFUSED'
    assert payload['automatic_retry_permitted'] is False
    assert 'Traceback' not in output.err
    assert 'private observation detail' not in output.out + output.err
    assert not list((env.root / 'publisher/operations').iterdir())
