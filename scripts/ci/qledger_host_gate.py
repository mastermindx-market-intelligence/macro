"""Inert host-backed entry/install gate for the retained conversion caller.

Install this trusted module/hook outside the mutable checkout. No environment,
receipt, identifier or file alone issues admission. The existing host controller
must supply live bootstrap, launcher, original resource and publication evidence.
This module neither stops a runner nor discovers writers or provisions an owner.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import fcntl
import json
import os
from pathlib import Path
import stat
from threading import Lock, get_ident


class GateRefusal(RuntimeError):
    pass


def _require(condition, message):
    if not condition:
        raise GateRefusal(message)


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _directory(path):
    """Pin every ancestor; never follow a symlink or create an owner directory."""
    _require(type(path) is Path or isinstance(path, Path), "explicit owner path required")
    _require(path.is_absolute() and '..' not in path.parts, "absolute lexical owner path required")
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for name in path.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _regular(info):
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
             and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600,
             "gate file requires one owner-only regular inode")


@dataclass(frozen=True)
class CodePin:
    path: Path
    digest: str

    def check(self):
        _require(self.path.is_absolute() and '..' not in self.path.parts,
                 "absolute pinned code path required")
        parent = _directory(self.path.parent)
        fd = None
        try:
            fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                         dir_fd=parent)
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                     and before.st_uid == os.geteuid() and not before.st_mode & 0o022,
                     "pinned code is not owner-controlled")
            _require(before.st_size <= 16 * 1024 * 1024, "pinned code bound exceeded")
            h = sha256()
            for _ in range(257):
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                h.update(chunk)
            else:
                raise GateRefusal('pinned code grew during read')
            after = os.fstat(fd)
            _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                     == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                     "pinned code changed during read")
            current = os.stat(self.path.name, dir_fd=parent, follow_symlinks=False)
            _require((current.st_dev, current.st_ino) == (before.st_dev, before.st_ino)
                     and h.hexdigest() == self.digest, "installed code differs from admitted bytes")
        finally:
            if fd is not None:
                os.close(fd)
            os.close(parent)


class HostGate:
    """One stable cooperative barrier and sticky hold, not runtime enrollment.

    evidence assertions must consult actual existing host/resource authorities and
    return None or raise. In particular bootstrap proves uninstrumented entrants
    excluded and old descriptors settled; lock acquisition does not prove this.
    No serialized evidence implementation or permissive default is provided.
    The assigning owner must also pin this loaded module/installation bundle;
    checking disk bytes alone does not identify already-loaded Python code.
    assert_process_version must qualify the current PID's actual loaded bundle
    and each native process binding; no expected-version string proves it.
    assert_publication_readback must bind this exact candidate/tree/target ref
    to the actual normal publication result, not a local object or cached ref.
    """

    LOCK = 'qledger-entry.lock'
    HOLD = 'qledger-install.hold'
    READY = 'qledger-installed.json'
    MAX_STATE = 32768

    def __init__(self, invocation, *, candidate_oid, tree_oid, accepted_tip_oid,
                 owner_code, runtime_code, workflow_oids, producers, runner_name, repository, agent_id, evidence):
        self.invocation = invocation
        self.owner = invocation.owner
        self.repo = self.owner.repo
        self.root = self.owner.target.owner_root
        self.candidate_oid, self.tree_oid, self.accepted_tip_oid = candidate_oid, tree_oid, accepted_tip_oid
        self.owner_code, self.runtime_code = tuple(owner_code), tuple(runtime_code)
        self.workflow_oids = tuple(workflow_oids)
        self.producers = dict(producers)  # (operation,lane) -> original (budget,retention)
        self.evidence = evidence
        _require(type(runner_name) is str and 0 < len(runner_name) <= 128
                 and type(repository) is str and repository.count('/') == 1
                 and 0 < len(repository) <= 256 and type(agent_id) is int and agent_id > 0,
                 "exact existing runner/repository/agent binding required")
        self.runner_name, self.repository, self.agent_id = runner_name, repository, agent_id
        root_fd = _directory(self.root)
        try:
            root_info = os.fstat(root_fd)
            self._root_identity = root_info.st_dev, root_info.st_ino
        finally:
            os.close(root_fd)
        _require(0 < len(self.owner_code) <= 128 and 0 < len(self.runtime_code) <= 128,
                 "finite explicit launcher/runtime code pins required")
        _require(0 < len(self.workflow_oids) <= 32 and len(self.producers) <= 128,
                 "finite exact workflow/producer bindings required")
        for oid in (candidate_oid, tree_oid, accepted_tip_oid, *self.workflow_oids):
            _require(type(oid) is str and len(oid) == 40 and all(c in '0123456789abcdef' for c in oid),
                     "exact Git object required")
        for pin in self.owner_code:
            _require(type(pin) is CodePin and pin.path.is_relative_to(self.root)
                     and not pin.path.is_relative_to(self.repo), "trusted hook must be outside checkout in owner area")
        for pin in self.runtime_code:
            _require(type(pin) is CodePin and pin.path.is_relative_to(self.repo), "exact checkout runtime pin required")
        for name in ('assert_bootstrap_exclusion', 'assert_launcher_coverage', 'assert_resources',
                     'assert_publication_readback', 'assert_descendants_settled', 'assert_process_version'):
            _require(callable(getattr(evidence, name, None)), "actual live host evidence is incomplete")
        self._pid = os.getpid()
        self._dir_fd = self._lock_fd = None
        self._mode = None
        self._lease_guard = Lock()
        self._lease_owner = None
        self._hold_identity = None
        self._installing = False
        binding = dict(repo=str(self.repo), owner_inode=self._root_identity, runner=runner_name,
            repository=repository, agent_id=agent_id, result=str(self.owner.target.result_path),
            manifest=invocation.manifest_digest, operation=self.owner.intent.operation_id,
            budget=self.owner.target.budget_id, retention=self.owner.target.retention_id,
            candidate=candidate_oid, tree=tree_oid, accepted_tip=accepted_tip_oid,
            workflows=self.workflow_oids,
            producers=sorted((op, lane, budget, retention) for (op, lane), (budget, retention) in self.producers.items()),
            owner_code=[(str(p.path), p.digest) for p in self.owner_code],
            runtime_code=[(str(p.path), p.digest) for p in self.runtime_code])
        self._binding = sha256(_json(binding)).hexdigest()
        self._held = _json(dict(schema=1, binding=self._binding, status='held'))
        self._ready = None  # Bound to the actual stable lock inode when leased.

    def _assert(self, name, **context):
        _require(getattr(self.evidence, name)(gate=self, **context) is None,
                 "live evidence must assert facts, not return an admission flag")

    def _check(self):
        _require(os.getpid() == self._pid and self._lease_owner == get_ident()
                 and self._lock_fd is not None,
                 "a live same-process entry/install lease owned by this thread is required")
        root = _directory(self.root)
        try:
            actual, pinned = os.fstat(root), os.fstat(self._dir_fd)
            _require(actual.st_uid == os.geteuid() and stat.S_IMODE(actual.st_mode) == 0o700,
                     "owner directory permissions changed")
            _require((actual.st_dev, actual.st_ino) == (pinned.st_dev, pinned.st_ino) == self._root_identity,
                     "owner directory changed")
        finally:
            os.close(root)
        info = os.stat(self.LOCK, dir_fd=self._dir_fd, follow_symlinks=False)
        pinned = os.fstat(self._lock_fd)
        _regular(info)
        _require((info.st_dev, info.st_ino) == (pinned.st_dev, pinned.st_ino), "stable entry lock was replaced")

    def _read(self, name):
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=self._dir_fd)
        except FileNotFoundError:
            return None
        try:
            _regular(os.fstat(fd))
            payload = os.read(fd, self.MAX_STATE + 1)
            _require(len(payload) <= self.MAX_STATE and not os.read(fd, 1), "gate state exceeds bound")
            return payload
        finally:
            os.close(fd)

    def _create(self, name, payload):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self._dir_fd)
        try:
            _require(os.write(fd, payload) == len(payload), "partial gate state; preserve hold")
            os.fsync(fd)
            info = os.fstat(fd)
            return info.st_dev, info.st_ino
        finally:
            os.close(fd)
            os.fsync(self._dir_fd)

    @contextmanager
    def lease(self, mode):
        _require(mode in ('install', 'entry') and os.getpid() == self._pid,
                 "fresh same-process gate lease required")
        # Admit atomically before opening or changing any shared descriptor
        # state. A rejected caller owns nothing and must perform no cleanup.
        _require(self._lease_guard.acquire(blocking=False),
                 "nested or concurrent lease on this gate instance refused")
        self._lease_owner = get_ident()
        try:
            with self._owned_lease(mode) as gate:
                yield gate
        finally:
            # Keep ownership until hold/error handling and FD cleanup finish.
            self._lease_owner = None
            self._lease_guard.release()

    @contextmanager
    def _owned_lease(self, mode):
        _require(self._mode is None, "gate descriptor state is already owned")
        directory = _directory(self.root)
        lock = None
        try:
            info = os.fstat(directory)
            _require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700
                     and (info.st_dev, info.st_ino) == self._root_identity,
                     "preprovisioned stable owner-only gate root required")
            lock = os.open(self.LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                           0o600, dir_fd=directory)
            _regular(os.fstat(lock))
            fcntl.flock(lock, (fcntl.LOCK_EX if mode == 'install' else fcntl.LOCK_SH) | fcntl.LOCK_NB)
            os.fsync(directory)
            os.fsync(lock)
            self._dir_fd, self._lock_fd, self._mode = directory, lock, mode
            lock_info = os.fstat(lock)
            self._ready = _json(dict(schema=1, binding=self._binding, status='installed',
                                    lock_inode=(lock_info.st_dev, lock_info.st_ino)))
            self._check()
            try:
                yield self
            except BaseException:
                self.hold()
                raise
        finally:
            self._dir_fd = self._lock_fd = self._mode = None
            self._hold_identity = None
            if lock is not None:
                os.close(lock)
            os.close(directory)

    def assert_valid(self, *, repo, operation_id, budget_id, retention_id, commit_oid, phase, lane_id=None):
        self._check()
        _require(repo == self.repo and commit_oid == self.candidate_oid, "wrong checkout or installed version")
        if lane_id is None:
            _require((operation_id, budget_id, retention_id) == (self.owner.intent.operation_id,
                self.owner.target.budget_id, self.owner.target.retention_id), "different original conversion inputs")
        else:
            _require(self.producers.get((operation_id, lane_id)) == (budget_id, retention_id),
                     "producer original resource binding was not admitted")
        context = dict(repo=repo, operation_id=operation_id, lane_id=lane_id,
                       budget_id=budget_id, retention_id=retention_id, commit_oid=commit_oid, phase=phase)
        for pin in self.owner_code:
            pin.check()
        self._assert('assert_launcher_coverage', **context)
        self._assert('assert_process_version', **context)
        self._assert('assert_resources', **context)
        held = self._read(self.HOLD)
        if self._mode == 'install':
            self._assert('assert_bootstrap_exclusion', **context)
            if self._hold_identity is None:
                _require(held is None and self._read(self.READY) is None, "installation already has original state; reconcile it")
            else:
                info = os.stat(self.HOLD, dir_fd=self._dir_fd, follow_symlinks=False)
                _require(held == self._held and (info.st_dev, info.st_ino) == self._hold_identity,
                         "original install hold changed")
        else:
            _require(held is None and self._read(self.READY) == self._ready,
                     "durable install admission is absent or held")
        if self._mode == 'entry' or phase in ('verify-installation', 'before-process-release'):
            _require(self.invocation._git_oid('HEAD') == self.candidate_oid, "running checkout version differs")
            for pin in self.runtime_code:
                pin.check()

    def begin_install(self, **context):
        _require(self._installing and self._mode == 'install' and self._hold_identity is None,
                 "incumbent checkout under exclusive fresh install lease required")
        self.assert_valid(**context)
        self.invocation.preflight(boundary='pre-rebase', candidate_oid=self.candidate_oid,
            tree_oid=self.tree_oid, accepted_tip_oid=self.accepted_tip_oid)
        self._hold_identity = self._create(self.HOLD, self._held)
        # If durability acknowledgement is lost, the original file stays held.
        self._check()

    def hold(self, **context):
        self._check()
        if self._read(self.HOLD) is None:
            try:
                self._create(self.HOLD, self._held)
            except FileExistsError:
                pass  # Concurrent failure holds the same root; never remove it.
        _require(self._read(self.HOLD) is not None, "durable hold could not be established")
        os.fsync(self._dir_fd)

    def confirm_install(self, **context):
        self.assert_valid(**dict(context, phase='before-process-release'))
        _require(self._installing and self._mode == 'install' and self._hold_identity is not None,
                 "same incumbent installation must own its durable hold")
        # The incumbent already checked the exact immutable candidate/full tree
        # before checkout and verified tracked output + native filesystem after
        # checkout. Publication may now advance its tracking ref legitimately;
        # require exact remote readback below, never an old mutable ref value.
        self.invocation.owner.read_binding(expected_manifest_digest=self.invocation.manifest_digest,
                                           commit_oid=self.candidate_oid)
        self._assert('assert_publication_readback', **context)
        self._assert('assert_descendants_settled', **context)
        self._create(self.READY, self._ready)
        self._check()
        info = os.stat(self.HOLD, dir_fd=self._dir_fd, follow_symlinks=False)
        _require((info.st_dev, info.st_ino) == self._hold_identity, "original hold replaced before release")
        os.unlink(self.HOLD, dir_fd=self._dir_fd)
        os.fsync(self._dir_fd)
        self._hold_identity = None

    def initial_checkout(self, checkout):
        with self.lease('install'):
            self._installing = True
            try:
                return self.invocation.initial_checkout(gate=self, checkout=checkout,
                    candidate_oid=self.candidate_oid, expected_tree_oid=self.tree_oid,
                    accepted_tip_oid=self.accepted_tip_oid)
            finally:
                self._installing = False

    def _conversion_context(self, phase):
        return dict(repo=self.repo, operation_id=self.owner.intent.operation_id,
            budget_id=self.owner.target.budget_id, retention_id=self.owner.target.retention_id,
            commit_oid=self.candidate_oid, phase=phase)

    def job_started(self, environ):
        """Existing runner pre-checkout hook; its short lease is not a job lease."""
        _require(environ.get('RUNNER_NAME') == self.runner_name
                 and environ.get('GITHUB_REPOSITORY') == self.repository
                 and environ.get('GITHUB_WORKSPACE') == str(self.repo)
                 and environ.get('GITHUB_SHA') in self.workflow_oids,
                 "unknown workspace/workflow revision before checkout")
        with self.lease('entry'):
            self.assert_valid(**self._conversion_context('job-started'))

    def invoke_reader(self, consumer, *args, **kwargs):
        with self.lease('entry'):
            context = self._conversion_context('reader')
            self.assert_valid(**context)
            value = self.invocation.invoke_reader(self.candidate_oid, consumer, *args, **kwargs)
            self.assert_valid(**context)
            self._assert('assert_descendants_settled', **context)
            return value

    def invoke_producer(self, binding, *, budget_id, retention_id, producer, args=(), kwargs=None):
        with self.lease('entry'):
            value = self.invocation.invoke_producer(binding, gate=self, installed_commit_oid=self.candidate_oid,
                budget_id=budget_id, retention_id=retention_id, producer=producer, args=args, kwargs=kwargs)
            self._assert('assert_descendants_settled', **dict(self._conversion_context('producer-return'),
                operation_id=binding.operation_id, lane_id=binding.lane_id,
                budget_id=budget_id, retention_id=retention_id))
            return value


if __name__ == '__main__':
    raise SystemExit('UNCONFIGURED: use the owner-installed hook with actual live evidence; no admission issued')
