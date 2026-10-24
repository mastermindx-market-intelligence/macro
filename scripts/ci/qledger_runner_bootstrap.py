"""Trusted outside-checkout loading for the inactive QLedger owner invocation.

Configuration pins bytes and original inputs; it never grants admission. The
pinned owner entry module must construct real live evidence for HostGate. This
module provides no production provider, reservation, installer or routing effect.
Run each entry with python3 -I in a fresh process from an owner-controlled installation.
"""
from __future__ import annotations

import sys

# Reject before importing even standard-library names that an unsafe search
# path could resolve to checkout files. The incumbent launcher must use -I.
if not sys.flags.isolated:
    raise SystemExit('UNCONFIGURED: trusted bootstrap requires python3 -I')

import _imp
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time


class BootstrapRefusal(RuntimeError):
    pass


def _require(value, message):
    if not value:
        raise BootstrapRefusal(message)


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _hash(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _absolute(value):
    path = Path(value)
    _require(path.is_absolute() and '..' not in path.parts, 'explicit absolute lexical path required')
    return path


def _directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for name in path.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        _require(info.st_uid == os.geteuid() and not info.st_mode & 0o022, 'unsafe owner directory')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _read(path, maximum, deadline, *, expected=None, retain=True):
    """Stream exact original bytes with bounded memory and stable file custody."""
    parent = _directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                 and before.st_uid == os.geteuid() and not before.st_mode & 0o022
                 and before.st_size <= maximum, 'unsafe or oversized pinned input')
        h, chunks, count = sha256(), [], 0
        while True:
            deadline.check()
            chunk = os.read(fd, min(65536, maximum + 1 - count))
            if not chunk:
                break
            count += len(chunk)
            _require(count <= maximum, 'pinned input exceeded bound')
            h.update(chunk)
            if retain:
                chunks.append(chunk)
        _require(count == before.st_size and _identity(before) == _identity(os.fstat(fd))
                 == _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)), 'pinned input changed')
        if expected is not None:
            _require(_hash(expected) and h.hexdigest() == expected, 'pinned input digest differs')
        deadline.check()
        return b''.join(chunks) if retain else count
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


BUNDLE_RESOURCES = frozenset(('templates/shared_shell_bridge.js', 'templates/shared_shell.css'))


class OriginalDeadline:
    """The caller's unchanged endpoint, with sticky expiry/clock failure."""
    def __init__(self, endpoint):
        _require(type(endpoint) is int and 0 < endpoint < 2**63, 'original absolute deadline required')
        self._endpoint, self.last, self.failed = endpoint, time.monotonic_ns(), False
        self.check()

    @property
    def endpoint(self):
        return self._endpoint

    def check(self):
        now = time.monotonic_ns()
        self.failed = self.failed or now < self.last or now >= self.endpoint
        self.last = max(now, self.last)
        _require(not self.failed, 'original budget expired or clock unproven')


class _Bundle(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    _qledger_bootstrap_active = True

    def __init__(self, root, repo, sources):
        self.root, self.repo, self.sources = root, repo, sources
        self.modules, self.namespaces, self.failure = {}, set(), None
        for rel, payload in sources.items():
            if rel in BUNDLE_RESOURCES:
                continue  # pinned resource bytes never become importable modules
            pieces = PurePosixPath(rel).parts
            package = pieces[-1] == '__init__.py'
            names = pieces[:-1] if package else (*pieces[:-1], pieces[-1][:-3])
            _require(names and all(x.isidentifier() for x in names), 'invalid qualified module path')
            name = '.'.join(names)
            _require(name not in self.modules, 'duplicate qualified module')
            self.modules[name] = (rel, payload, package)
            self.namespaces.update('.'.join(names[:i]) for i in range(1, len(names)))
        for name in self.namespaces - self.modules.keys():
            init = Path(*name.split('.')) / '__init__.py'
            _require(not (root / init).exists() and not (repo / init).exists(),
                     'regular package initializer omitted from qualified bundle')
        self.roots = {x.split('.')[0] for x in self.modules} | {'engine', 'scripts', 'lib'}

    def reject(self, message):
        self.failure = self.failure or message
        raise BootstrapRefusal(self.failure)

    def check(self):
        _require(self.failure is None, self.failure or 'unqualified import')

    def owns(self, name):
        return name.split('.')[0] in self.roots

    def find_spec(self, fullname, path=None, target=None):
        if self.owns(fullname):
            self.check()
        if fullname in self.modules:
            rel, _, package = self.modules[fullname]
            return importlib.util.spec_from_loader(fullname, self, origin=str(self.root / rel), is_package=package)
        if fullname in self.namespaces:
            return importlib.util.spec_from_loader(fullname, self, is_package=True)
        if self.owns(fullname):
            self.reject('unqualified first-party import: ' + fullname)
        # A repo-root pin in qualified code must not expose an omitted bundle
        # module or a mutable checkout through the ordinary path finder.
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        locations = [] if spec is None else list(spec.submodule_search_locations or ())
        if spec is not None and spec.origin and spec.origin not in ('built-in', 'frozen'):
            locations.append(spec.origin)
        if any(_absolute(x).is_relative_to(self.repo) or _absolute(x).is_relative_to(self.root) for x in locations):
            self.reject('unqualified path import: ' + fullname)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        item = self.modules.get(module.__name__)
        if item is None:
            module.__path__ = [str(self.root.joinpath(*module.__name__.split('.')))]
            return
        rel, payload, package = item
        filename = str(self.root / rel)
        module.__file__, module.__cached__ = filename, None
        if package:
            module.__path__ = [str((self.root / rel).parent)]
        exec(compile(payload, filename, 'exec', dont_inherit=True), module.__dict__)

    def runtime_root(self, module_name):
        """Actual qualified checkout root before config import-time reads."""
        self.check()
        module = sys.modules.get(module_name)
        _require(module_name == 'lib.config' and module_name in self.modules
                 and module is not None and module.__loader__ is self, 'unqualified runtime root request')
        return self.repo

    def config_digest(self):
        """Existing runtime CodePin identifies bytes, never resource admission."""
        self.runtime_root('lib.config')
        digest = getattr(self, 'runtime_config_pin', None)
        if not _hash(digest):
            self.reject('qualified original config pin unavailable')
        return digest

    def runtime_config(self, module_name):
        self.runtime_root(module_name)
        try:
            digest = self.config_digest()
            raw = _read(self.repo/'config.yml', 16 * 1024 * 1024, self.deadline, expected=digest)
            return raw, digest
        except Exception:
            # A caught unqualified read cannot be erased by restoring the file
            # or clearing a cache: other imported values could already depend
            # on it. This loader stays poisoned through its original lifetime.
            self.failure = self.failure or 'unqualified original configuration read'
            raise

    def callable(self, value):
        self.check()
        name = getattr(value, '__module__', '')
        module = sys.modules.get(name)
        _require(callable(value) and name in self.modules and module is not None
                 and module.__loader__ is self, 'entry callable is not from the qualified bundle')
        return value


@dataclass(frozen=True)
class BootstrapContext:
    repo: Path
    owner_root: Path
    result_path: Path
    manifest_digest: str
    original_deadline_monotonic_ns: int
    candidate_oid: str
    operation_id: str
    budget_id: str
    retention_id: str


class _DeadlineEvidence:
    """Bind live assertions to the original endpoint/result and current PID.

    The qualified owner provider must consult its existing host, reservation and
    retention authorities. These values identify the request, not admission.
    Every assertion receives the unchanged HostGate context plus these bindings.
    """
    def __init__(self, provider, bundle, deadline, context):
        _require(provider is not None and type(provider) not in (bool, dict), 'live evidence provider required')
        self.provider, self.bundle, self.deadline, self.context = provider, bundle, deadline, context
        module = sys.modules.get(type(provider).__module__)
        _require(module is not None and module.__loader__ is bundle, 'provider is not qualified owner code')
        for name in ('assert_bootstrap_exclusion', 'assert_launcher_coverage', 'assert_resources',
                     'assert_publication_readback', 'assert_descendants_settled', 'assert_process_version'):
            _require(callable(getattr(provider, name, None)), 'live evidence provider incomplete')

    def _call(self, name, **context):
        self.deadline.check()
        self.bundle.check()
        _require(getattr(self.provider, name)(**context,
            original_deadline_monotonic_ns=self.context.original_deadline_monotonic_ns,
            conversion_result_path=self.context.result_path,
            conversion_manifest_digest=self.context.manifest_digest,
            bootstrap_pid=os.getpid()) is None, 'evidence assertion returned an admission flag')
        self.deadline.check()
        self.bundle.check()

    def __getattr__(self, name):
        if name.startswith('assert_') and callable(getattr(self.provider, name, None)):
            return lambda **context: self._call(name, **context)
        raise AttributeError(name)


def _entries(fd, maximum, deadline):
    names = set()
    with os.scandir(fd) as entries:
        for entry in entries:
            deadline.check()
            _require(len(names) < maximum, 'retained inventory exceeds bound')
            names.add(entry.name)
    return names


def _retained_bytes(path, digest, repo, owner, deadline):
    # This is pre-import byte/inventory qualification, not a second protocol
    # validator. The accepted native owner performs full canonical readback next.
    raw = _read(path / 'manifest.json', 65536 * 512, deadline, expected=digest)
    doc = json.loads(raw)
    _require(_json(doc)[:-1] == raw and doc['claims_path'] == str(repo / 'data/qledger/claims.jsonl')
             and doc['target']['owner_root'] == str(owner) and doc['target']['result_path'] == str(path),
             'retained conversion binding differs')
    refs = {doc['source']['object'], doc['snapshot']['root'], doc['git']['commit'],
            *doc['snapshot']['members'].values()}
    _require(len(refs) <= 65536 and all(_hash(x) for x in refs), 'retained object inventory malformed')
    result_fd, members_fd = _directory(path), _directory(path / 'members')
    try:
        _require(_entries(result_fd, 2, deadline) == {'manifest.json', 'members'}
                 and _entries(members_fd, 65536, deadline) == refs, 'retained original inventory differs')
        total = len(raw)
        for name in sorted(refs):
            total += _read(path / 'members' / name, 512 * 1024 * 1024 - total, deadline,
                           expected=name, retain=False)
        _require(_entries(members_fd, 65536, deadline) == refs, 'retained inventory changed')
    finally:
        os.close(members_fd)
        os.close(result_fd)
    return doc


class LoadedBootstrap:
    def __init__(self, gate, entry, bundle, deadline, context, config):
        self.gate, self.entry, self.bundle, self.deadline = gate, entry, bundle, deadline
        self.context, self.config = context, config

    def job_started(self, environ):
        self.deadline.check()
        self.bundle.check()
        return self.gate.job_started(environ)

    def reader(self):
        callback = self.bundle.callable(self.entry.reader)
        return self.gate.invoke_reader(lambda: callback(self.context))

    def producer(self, *, owner_binding=None, regions=None, native_intents=None, call=None, publication=None):
        original = self.config['producer_context']
        _require(type(original) is dict and set(original) == {'operation_id', 'lane_id', 'budget_id', 'retention_id'},
                 'explicit original producer context required')
        context = dict(repo=self.context.repo, commit_oid=self.gate.candidate_oid, phase='producer-build', **original)
        with self.gate.lease('entry'):
            self.gate.assert_valid(**context)
            builder = self.bundle.callable(self.entry.build_producer)
            if any(x is not None for x in (owner_binding, regions, native_intents, call, publication)):
                _require(owner_binding is not None and regions is not None and native_intents is not None,
                         'complete explicit same-process producer inputs required')
                options = {} if publication is None else {'publication': publication}
                binding, callback = builder(self.context, owner_binding=owner_binding, regions=regions,
                                            native_intents=native_intents, call=call, **options)
            else:
                binding, callback = builder(self.context)
            _require((binding.operation_id, binding.lane_id) == (original['operation_id'], original['lane_id']),
                     'producer binding differs from original context')
            self.bundle.callable(callback)
            value = self.gate.invocation.invoke_producer(binding, gate=self.gate,
                installed_commit_oid=self.gate.candidate_oid, budget_id=original['budget_id'],
                retention_id=original['retention_id'], producer=callback)
            self.gate.evidence.assert_descendants_settled(gate=self.gate, **context)
            return value


class _FactsClock:
    """Monotonic inspection only; no operation deadline or native admission."""
    def __init__(self):
        self.last = time.monotonic_ns()
    def check(self):
        now = time.monotonic_ns()
        _require(now >= self.last, 'facts inspection clock regressed')
        self.last = now


@contextmanager
def _qualified_invocation(*, owner_root, repo, config_path, config_digest, facts_only=False):
    """Qualify outside-checkout original/code bytes, then import only that bundle."""
    owner, repo, config_path = map(_absolute, (owner_root, repo, config_path))
    _require(not owner.is_relative_to(repo) and config_path.parent == owner, 'outside-checkout owner config required')
    owner_fd = _directory(owner)
    try:
        _require(stat.S_IMODE(os.fstat(owner_fd).st_mode) == 0o700, 'owner-only bootstrap root required')
    finally:
        os.close(owner_fd)
    # The original endpoint is input, never minted here. Reading one bounded
    # config does not issue authority; every operational assertion checks it.
    class _ConfigRead:
        def check(self):
            pass
    raw = _read(config_path, 131072, _ConfigRead(), expected=config_digest)
    config = json.loads(raw)
    _require(_json(config) == raw and config['schema'] == 1 and config['repo'] == str(repo)
             and config['owner_root'] == str(owner), 'bootstrap config binding differs')
    deadline = _FactsClock() if facts_only else OriginalDeadline(config['original_deadline_monotonic_ns'])
    installed = _absolute(__file__)
    _require(installed.is_relative_to(owner) and not installed.is_relative_to(repo), 'bootstrap executed from mutable checkout')
    _read(installed, 16 * 1024 * 1024, deadline, expected=config['bootstrap_sha256'])
    root, result = _absolute(config['bundle_root']), _absolute(config['result_path'])
    _require(root.parent == owner and result.parent == owner and root != result, 'explicit distinct bundle/result children required')
    doc = _retained_bytes(result, config['manifest_digest'], repo, owner, deadline)
    pins = config['bundle_files']
    _require(type(pins) is dict and 0 < len(pins) <= 126, 'finite exact bundle required')
    sources, total = {}, 0
    for name, digest in pins.items():
        rel = PurePosixPath(name)
        _require(not rel.is_absolute() and '..' not in rel.parts
                 and (rel.suffix == '.py' or name in BUNDLE_RESOURCES), 'unsafe bundle path')
        payload = _read(root / rel, min(16 * 1024 * 1024, 64 * 1024 * 1024 - total), deadline, expected=digest)
        sources[name], total = payload, total + len(payload)
    if 'scripts/ci/qledger_daily_entry.py' in sources:
        _require(BUNDLE_RESOURCES <= sources.keys(), 'daily entry canonical resources missing before import')
    bundle = _Bundle(root, repo, sources)
    bundle.deadline = deadline
    bundle.runtime_config_pin = config['gate']['runtime_code'].get(str(repo/'config.yml'))
    if 'scripts/ci/qledger_daily_entry.py' in sources:
        _require(_hash(bundle.runtime_config_pin), 'daily entry qualified config pin missing before import')
    admitted = False
    _imp.acquire_lock()
    try:
        _require(not any(bundle.owns(n) or
            (getattr(m, '__file__', None) and Path(m.__file__).is_absolute() and
             (Path(m.__file__).is_relative_to(repo) or Path(m.__file__).is_relative_to(root)))
            for n, m in list(sys.modules.items())), 'first-party module imported before qualification')
        _require(not any(getattr(x, '_qledger_bootstrap_active', False) for x in sys.meta_path), 'bootstrap already active')
        # python -I must arrive without a mutable checkout search path. Do not
        # silently repair a contaminated launcher or reorder global resolution.
        _require(not any(Path(p or os.getcwd()).resolve().is_relative_to(repo) for p in sys.path),
                 'mutable checkout import path is active')
        sys.meta_path.insert(0, bundle)
        admitted = True
    finally:
        _imp.release_lock()
    try:
        deadline.check()
        _require(config['entry_module'] in bundle.modules, 'qualified owner entry required')
        invocation_module = importlib.import_module('scripts.ci.qledger_owner_invocation')
        gate_module = importlib.import_module('scripts.ci.qledger_host_gate')
        invocation = invocation_module.load_conversion(repo, result_path=result, manifest_digest=config['manifest_digest'])
        bundle.check()
        deadline.check()
        yield invocation, bundle, config, deadline, root, installed, owner, repo, result, gate_module, doc
    finally:
        if admitted:
            bundle.failure = bundle.failure or 'trusted bootstrap scope is closed'
            _imp.acquire_lock()
            try:
                # A fresh-entry process never reopens mutable checkout imports.
                # Keep its closed finder until process exit, including when a
                # callback retained a reference or a descendant is unproven.
                for name in list(sys.modules):
                    if bundle.owns(name):
                        del sys.modules[name]
            finally:
                _imp.release_lock()


@contextmanager
def trusted_bootstrap(*, owner_root, repo, config_path, config_digest):
    """Operational entries retain their original deadline and complete gate."""
    with _qualified_invocation(owner_root=owner_root,repo=repo,config_path=config_path,
                               config_digest=config_digest) as qualified:
        invocation,bundle,config,deadline,root,installed,owner,repo,result,gate_module,doc = qualified
        context = BootstrapContext(repo, owner, result, config['manifest_digest'], deadline.endpoint,
            config['gate']['candidate_oid'], doc['intent']['operation_id'], doc['target']['budget_id'], doc['target']['retention_id'])
        entry = importlib.import_module(config['entry_module'])
        provider = bundle.callable(entry.build_evidence)(context)
        evidence = _DeadlineEvidence(provider, bundle, deadline, context)
        bundle.check()
        args = dict(config['gate'])
        args['runtime_code'] = tuple(gate_module.CodePin(_absolute(p), h) for p, h in args['runtime_code'].items())
        args['producers'] = {(x['operation_id'], x['lane_id']): (x['budget_id'], x['retention_id']) for x in args['producers']}
        args['owner_code'] = tuple(gate_module.CodePin(root / p, h) for p, h in config['bundle_files'].items()) + (
            gate_module.CodePin(installed, config['bootstrap_sha256']), gate_module.CodePin(config_path, config_digest))
        gate = gate_module.HostGate(invocation, evidence=evidence, **args)
        yield LoadedBootstrap(gate, entry, bundle, deadline, context, config)


def main():
    parser = argparse.ArgumentParser()
    for name in ('owner-root', 'repo', 'config-path', 'config-digest'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--entry', choices=('job-started', 'reader', 'producer',
                        'capture-push-original', 'inspect-push-original'), required=True)
    for name in ('owner-pid','retry-deadline','retry-budget-secs','max-attempts','push-alarm','attempt'):
        parser.add_argument('--'+name, type=int)
    parser.add_argument('--original-sha256')
    parser.add_argument('--original-binding', nargs=5)
    args = parser.parse_args()
    if args.entry in ('capture-push-original','inspect-push-original'):
        # Facts are captured before a provider exists, solving the origin/budget
        # construction dependency. This path cannot construct a gate, install,
        # enter ClaimsBindingScope or return an operational deadline capability.
        with _qualified_invocation(owner_root=args.owner_root,repo=args.repo,
                config_path=args.config_path,config_digest=args.config_digest,facts_only=True) as q:
            invocation,bundle,*_ = q
            module = importlib.import_module('scripts.ci.qledger_push_original')
            inputs=dict(owner_pid=args.owner_pid,deadline=args.retry_deadline,budget=args.retry_budget_secs,
                        max_attempts=args.max_attempts,alarm=args.push_alarm,attempt=args.attempt,
                        binding=args.original_binding)
            if args.entry=='capture-push-original':
                result=module.capture(invocation,**inputs)
            else:
                result=module.inspect(invocation,**inputs,digest=args.original_sha256)
            bundle.check()
            print(result)
        return

    with trusted_bootstrap(owner_root=args.owner_root, repo=args.repo,
                           config_path=args.config_path, config_digest=args.config_digest) as loaded:
        if args.entry == 'job-started':
            loaded.job_started(os.environ)
        elif args.entry == 'reader':
            loaded.reader()
        else:
            loaded.producer()


if __name__ == '__main__':
    main()
