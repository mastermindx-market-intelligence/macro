"""Fresh subprocesses with test-owned evidence; never production admission."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from tests.test_qledger_conversion_candidate import fixture, conversion_invocation  # noqa: F401


SOURCE = Path(__file__).resolve().parents[1]
BUNDLE_FILES = (
    'engine/__init__.py', 'scripts/__init__.py',
    'engine/qledger_original_conversion.py', 'engine/qledger_original_result.py',
    'engine/qledger_store.py', 'engine/qledger_store_conversion.py',
    'engine/qledger_store_native.py', 'engine/qledger_store_protocol.py',
    'engine/qledger_store_sources.py', 'scripts/ci/qledger_conversion_candidate.py',
    'scripts/ci/qledger_owner_invocation.py', 'scripts/ci/qledger_publication.py',
    'scripts/ci/qledger_host_gate.py',
)

# This provider belongs exclusively to these temporary tests. No such provider
# ships in the bootstrap, and none of these assertions is a runtime receipt.
ENTRY = '''
from pathlib import Path
import os
from scripts.ci.qledger_host_gate import GateRefusal
Path(__file__).with_name('IMPORT_OCCURRED').write_text('test-owned import\\n')

class FixtureEvidence:
    def __init__(self, context):
        self.original = context
        self.missing = None
        self.boolean = False
        self.calls = []
    def check(self, name, **context):
        self.calls.append(name)
        if (context['original_deadline_monotonic_ns'] != self.original.original_deadline_monotonic_ns
                or context['bootstrap_pid'] != os.getpid()
                or context['conversion_result_path'] != self.original.result_path
                or context['conversion_manifest_digest'] != self.original.manifest_digest):
            raise GateRefusal('fixture original binding differs')
        expected = ('original-producer-budget', 'original-producer-retention') if context.get('lane_id') else (
            self.original.budget_id, self.original.retention_id)
        if (context['budget_id'], context['retention_id']) != expected:
            raise GateRefusal('fixture original resources differ')
        if self.missing == name:
            raise GateRefusal('fixture actual evidence missing: ' + name)
        if self.boolean:
            return True
    def assert_bootstrap_exclusion(self, **context): return self.check('bootstrap-old-fds', **context)
    def assert_launcher_coverage(self, **context): return self.check('new-entrants', **context)
    def assert_resources(self, **context):
        if self.missing in ('reservation', 'retention'):
            raise GateRefusal('fixture actual evidence missing: ' + self.missing)
        return self.check('resources', **context)
    def assert_publication_readback(self, **context): return self.check('publication', **context)
    def assert_descendants_settled(self, **context): return self.check('descendants', **context)
    def assert_process_version(self, **context): return self.check('process-version', **context)

def build_evidence(context): return FixtureEvidence(context)

def reader(context):
    from engine.qledger_store import uses_native_claims
    assert uses_native_claims(context.repo / 'data/qledger/claims.jsonl')
    return 'fixture-reader'

def build_producer(context):
    from scripts.ci.qledger_owner_invocation import load_conversion
    from scripts.ci.qledger_conversion_candidate import CandidateCommitMetadata
    from engine.qledger_original_result import OriginalResultClaimsBinding, OriginalResultTarget
    from engine.qledger_store_native import NativeClaimsIntent
    from engine import qledger_store as store
    invocation = load_conversion(context.repo, result_path=context.result_path,
                                 manifest_digest=context.manifest_digest)
    root = context.owner_root / 'producer-evidence'
    intent = NativeClaimsIntent('producer-original', 'producer-lane', 'producer-write')
    target = OriginalResultTarget(root, root / 'write-one', 'write-one', context.candidate_oid,
        'refs/remotes/origin/main', 'refs/heads/main',
        CandidateCommitMetadata('Producer fixture', 'fixture@example.invalid', 1700000010))
    binding = OriginalResultClaimsBinding(context.repo / 'data/qledger/claims.jsonl',
        operation_id=intent.operation_id, lane_id=intent.lane_id, limits=invocation.owner.limits,
        original_result_targets={intent: target})
    def produce():
        with store._claims_mutation(binding.claims_path, native_intent=intent) as writer:
            writer.append_serialized_rows([b'{"bootstrap":1}\\n'])
        return 'fixture-producer'
    return binding, produce
'''

DRIVER = '''
import importlib.util,json,os,subprocess,sys,types
from pathlib import Path
bootstrap_file,config_file,config_digest,action,expected=sys.argv[1:]
spec=importlib.util.spec_from_file_location('isolated_owner_bootstrap',bootstrap_file)
b=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=b
spec.loader.exec_module(b)
config=json.loads(Path(config_file).read_bytes())
repo=Path(config['repo']); owner=Path(config['owner_root'])
if action=='preloaded':
    poison=types.ModuleType('engine'); poison.__file__=str(repo/'engine/__init__.py')
    sys.modules['engine']=poison
if action=='preloaded-other':
    poison=types.ModuleType('unlisted'); poison.__file__=str(repo/'unlisted.py')
    sys.modules['unlisted']=poison
operational=False
try:
    with b.trusted_bootstrap(owner_root=owner,repo=repo,config_path=Path(config_file),
                             config_digest=config_digest) as loaded:
        if action=='no-provider': raise AssertionError('unconfigured bootstrap returned')
        if action=='not-installed':
            operational=True
            loaded.reader()
        else:
            # OFFLINE FIXTURE ONLY. The production CLI contains no checkout or
            # install dispatch. This test provider is the sole fixture authority.
            if action=='bootstrap-old-fds':
                loaded.gate.evidence.provider.missing=action
                operational=True
            loaded.gate.initial_checkout(lambda oid: subprocess.check_call(
                ['git','-C',str(repo),'checkout','--quiet','--detach',oid]))
            operational=True
            provider=loaded.gate.evidence.provider
            if action in ('reservation','retention','new-entrants','process-version','publication','descendants'):
                provider.missing=action
            if action=='boolean': provider.boolean=True
            if action=='expire': b.time.monotonic_ns=lambda: loaded.context.original_deadline_monotonic_ns+1
            if action=='changed-code':
                loaded.gate.owner_code[0].path.write_bytes(b'# changed trusted source\\n')
            if action=='job-started':
                loaded.job_started({'RUNNER_NAME':loaded.gate.runner_name,
                    'GITHUB_REPOSITORY':loaded.gate.repository,'GITHUB_WORKSPACE':str(repo),
                    'GITHUB_SHA':loaded.gate.candidate_oid})
            elif action=='producer':
                subprocess.check_call(['git','-C',str(repo),'update-ref','refs/remotes/origin/main',loaded.gate.candidate_oid])
                assert loaded.producer()=='fixture-producer'
                assert (owner/'producer-evidence/write-one/manifest.json').is_file()
            else:
                assert loaded.reader()=='fixture-reader'
            if action in ('reader','job-started','producer'):
                from engine.qledger_store import uses_native_claims
                assert not uses_native_claims(repo/'data/qledger/claims.jsonl')
            if action=='deadline-readonly':
                try: loaded.deadline.endpoint=loaded.deadline.endpoint+1000000
                except AttributeError: pass
                else: raise AssertionError('original endpoint reset')
    if action=='closed-scope':
        loaded.job_started({})
    if action=='closed-import':
        sys.path.insert(0,str(repo))
        import engine.evil
except BaseException as exc:
    if not expected or expected not in str(exc):
        raise
    if operational and action not in ('closed-scope','closed-import'):
        assert (owner/'qledger-install.hold').is_file(), 'operational refusal lost durable HOLD'
    print('EXPECTED_REFUSAL')
else:
    assert not expected, 'expected refusal did not occur'
    assert not (owner/'qledger-install.hold').exists()
    print('OFFLINE_FIXTURE_SUCCESS')
'''


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def put(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(payload)
    path.chmod(0o600)
    return sha256(payload).hexdigest()


@pytest.fixture
def bootstrap(conversion_invocation, tmp_path):
    invocation, prepared = conversion_invocation
    owner, repo = invocation.owner.target.owner_root, invocation.owner.repo
    owner.chmod(0o700)
    (owner/'producer-evidence').mkdir(mode=0o700)
    installed = owner/'bootstrap.py'
    script_hash = put(installed, (SOURCE/'scripts/ci/qledger_runner_bootstrap.py').read_bytes())
    bundle = owner/'bundle'
    pins = {name: put(bundle/name, (SOURCE/name).read_bytes()) for name in BUNDLE_FILES}
    pins['owner_entry.py'] = put(bundle/'owner_entry.py', ENTRY.encode())
    producer = dict(operation_id='producer-original', lane_id='producer-lane',
                    budget_id='original-producer-budget', retention_id='original-producer-retention')
    config = dict(schema=1, repo=str(repo), owner_root=str(owner), bundle_root=str(bundle),
        result_path=str(invocation.owner.target.result_path), manifest_digest=prepared.manifest_digest,
        bootstrap_sha256=script_hash, original_deadline_monotonic_ns=time.monotonic_ns()+60_000_000_000,
        bundle_files=pins, entry_module='owner_entry', producer_context=producer,
        gate=dict(candidate_oid=prepared.candidate.candidate_oid, tree_oid=prepared.candidate.tree_oid,
            accepted_tip_oid=invocation.owner.target.accepted_tip_oid,
            runtime_code={str(repo/'unrelated'):sha256(b'accepted\n').hexdigest()},
            workflow_oids=[prepared.candidate.candidate_oid], producers=[producer],
            runner_name='fixture-runner', repository='fixture/macro', agent_id=28))
    driver = tmp_path/'driver.py'
    driver.write_text(DRIVER)
    def run(action, expected='', change=None, script=None):
        if change:
            change(config)
        config_path=owner/'bootstrap.json'
        digest=put(config_path, canonical(config))
        result=subprocess.run([sys.executable,'-I',str(driver),str(script or installed),str(config_path),
            digest,action,expected],capture_output=True,text=True,timeout=60,cwd=repo)
        assert result.returncode == 0, result.stderr + result.stdout
        return result.stdout
    return run, config, owner, repo


@pytest.mark.parametrize('entry', ['reader','job-started','producer','deadline-readonly'])
def test_only_test_owned_evidence_runs_coherent_native_entries(bootstrap, entry):
    run, _, _, _ = bootstrap
    assert 'OFFLINE_FIXTURE_SUCCESS' in run(entry)


@pytest.mark.parametrize('missing', ['reservation','retention','new-entrants','process-version','descendants','bootstrap-old-fds'])
def test_actual_evidence_absence_holds_before_release(bootstrap, missing):
    run, _, _, _ = bootstrap
    assert 'EXPECTED_REFUSAL' in run(missing, 'fixture actual evidence missing: '+missing)


@pytest.mark.parametrize('action,expected', [
    ('not-installed','durable install admission is absent or held'),
    ('boolean','admission flag'), ('expire','original budget expired'),
    ('changed-code','installed code differs from admitted bytes'),
])
def test_unchanged_gate_and_original_budget_cannot_be_bypassed(bootstrap, action, expected):
    run, _, _, _ = bootstrap
    run(action, expected)


@pytest.mark.parametrize('attack', ['preloaded','preloaded-other','expired','manifest','code','missing-member','missing-binding','mutable-bootstrap'])
def test_preimport_qualification_refuses_before_owner_module_runs(bootstrap, attack):
    run, config, owner, repo = bootstrap
    expected='first-party module imported before qualification'
    action=attack
    script=None
    if attack=='expired':
        config['original_deadline_monotonic_ns']=time.monotonic_ns()-1
        expected='original budget expired'
    elif attack=='manifest':
        config['manifest_digest']='0'*64
        expected='pinned input digest differs'
    elif attack=='code':
        (owner/'bundle/owner_entry.py').write_bytes(b'raise AssertionError("unqualified code executed")\n')
        expected='pinned input digest differs'
    elif attack=='missing-member':
        next((Path(config['result_path'])/'members').iterdir()).unlink()
        expected='retained original inventory differs'
    elif attack=='missing-binding':
        del config['original_deadline_monotonic_ns']
        expected='original_deadline_monotonic_ns'
    elif attack=='mutable-bootstrap':
        script=repo/'bootstrap.py'
        put(script,(owner/'bootstrap.py').read_bytes())
        expected='bootstrap executed from mutable checkout'
    run(action, expected, script=script)
    assert not (owner/'bundle/IMPORT_OCCURRED').exists()


def test_caught_unqualified_import_cannot_fall_through_to_checkout(bootstrap):
    run, config, owner, repo = bootstrap
    poison=repo/'engine/evil.py'
    put(poison,b'raise AssertionError("mutable checkout executed")\n')
    entry=(owner/'bundle/owner_entry.py')
    payload=entry.read_bytes()+b'\ntry:\n import engine.evil\nexcept RuntimeError:\n pass\n'
    config['bundle_files']['owner_entry.py']=put(entry,payload)
    run('caught-import','unqualified first-party import: engine.evil')


def test_no_permissive_provider_or_serialized_admission_fallback(bootstrap):
    run, config, owner, _ = bootstrap
    entry=owner/'bundle/owner_entry.py'
    payload=entry.read_bytes()+b'\ndef build_evidence(context): return {"admitted":True}\n'
    config['bundle_files']['owner_entry.py']=put(entry,payload)
    run('no-provider','live evidence provider required')


def test_regular_package_initializer_cannot_be_silently_skipped(bootstrap):
    run, config, owner, _ = bootstrap
    del config['bundle_files']['engine/__init__.py']
    run('omitted-init', 'regular package initializer omitted')
    assert not (owner/'bundle/IMPORT_OCCURRED').exists()


def test_closed_loader_scope_cannot_reuse_an_admitted_entry(bootstrap):
    run, _, _, _ = bootstrap
    run('closed-scope', 'trusted bootstrap scope is closed')


def test_closed_scope_does_not_restore_mutable_checkout_imports(bootstrap):
    run, _, owner, repo = bootstrap
    put(repo/'engine/evil.py', b'raise AssertionError("mutable code executed after close")\n')
    run('closed-import', 'trusted bootstrap scope is closed')


def test_unisolated_interpreter_refuses_before_bundle_loading(bootstrap):
    _, _, owner, repo = bootstrap
    result = subprocess.run([sys.executable, str(owner/'bootstrap.py'), '--help'],
        capture_output=True, text=True, cwd=repo, timeout=10)
    assert result.returncode != 0
    assert 'requires python3 -I' in result.stderr
    assert not (owner/'bundle/IMPORT_OCCURRED').exists()
