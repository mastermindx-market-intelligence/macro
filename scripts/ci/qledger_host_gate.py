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
        self.producers = dict(producers)  # Existing original (operation,lane)->(budget,retention), including explicit readers.
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
        self._native_transition = self._native_confirmed = False
        self._native_expected = self._native_reader_call = self._native_owner_binding = None
        self._native_old_ready = self._native_old_identity = None
        self._native_ready_started = self._native_ready_replaced = False
        self._native_ready_fd = None
        self._native_checked = None
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
            if self._native_transition:
                if self._hold_identity is None:
                    _require(held is None and self._read(self.READY) == self._expected_native_ready(self._native_expected),
                             'native cycle previous READY is absent or held')
                else:
                    _require(held == self._held and (os.stat(self.HOLD,dir_fd=self._dir_fd,follow_symlinks=False).st_dev,
                             os.stat(self.HOLD,dir_fd=self._dir_fd,follow_symlinks=False).st_ino) == self._hold_identity
                             and self._read(self.READY) == (self._expected_native_ready(self._native_expected) if self._native_confirmed
                                 else self._native_old_ready), 'native cycle original state changed')
            elif self._hold_identity is None:
                _require(held is None and self._read(self.READY) is None, "installation already has original state; reconcile it")
            else:
                info = os.stat(self.HOLD, dir_fd=self._dir_fd, follow_symlinks=False)
                _require(held == self._held and (info.st_dev, info.st_ino) == self._hold_identity,
                         "original install hold changed")
        else:
            _require(held is None and self._read(self.READY) == self._expected_native_ready(self._native_expected),
                     "durable install admission is absent or held")
        if self._mode == 'entry' or self._native_transition or phase in ('verify-installation', 'before-process-release'):
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

    def _native_selection(self, selection, *, verify=False):
        from engine import qledger_original_result as originals
        from engine.qledger_store import NativeGitClaimsBinding
        from scripts.ci import qledger_publication as publication
        from scripts.ci import qledger_conversion_candidate as candidate
        _require(type(selection) is tuple and len(selection) == 5, 'explicit immutable native selection required')
        oid, tree, source, retained, publication_pin = selection
        for value in (oid, tree, source):publication._oid(value)
        _require(type(publication_pin) is dict and set(publication_pin) == {'origin','transport','layout'}
                 and type(publication_pin['origin']) is str and len(publication_pin['origin']) == 64
                 and all(c in '0123456789abcdef' for c in publication_pin['origin'])
                 and publication_pin['transport'] in ('local_objects_and_loose_ref_cas','checkout_https'),
                 'explicit actual publication carrier binding required')
        layout=publication_pin['layout']
        _require((publication_pin['transport'] == 'checkout_https' and layout is None) or
                 (publication_pin['transport'] == 'local_objects_and_loose_ref_cas'
                  and type(layout) in (tuple,list) and len(layout)==3
                  and all(type(x) in (tuple,list) and len(x)==2 and all(type(v) is int and v>=0 for v in x) for x in layout)),
                 'actual original publication namespace binding required')
        _require(type(retained) is originals.RetainedOriginalResult and retained._seal is originals._SEAL
                 and retained.write.claims_path == self.repo/'data/qledger/claims.jsonl'
                 and retained.limits == self.owner.limits and retained.target_ref == 'refs/heads/main',
                 'exact retained native generation/profile required')
        if verify:
            retained = originals.require_retained_original(retained.write, retained)
            binding = publication.NativePublicationBinding(retained.write.intent.operation_id,
                retained.write.intent.lane_id, retained.target_ref, retained.accepted_tip_oid,
                retained.write.plan.snapshot.receipt.root_digest)
            witness = publication.check_native_operation_candidate(self.repo, candidate_oid=oid,
                accepted_baseline_oids=(retained.accepted_tip_oid,), target_ref=retained.target_ref,
                binding=binding, native_operation_receipt=retained.native_operation_receipt, limits=retained.limits)
            _require(witness.publication.tree_oid == tree, 'native reader full tree differs')
            raw, _ = publication._git(self.repo, ['cat-file','commit',oid], output_limit=4096)
            expected = candidate._native_commit_bytes(tree, retained.accepted_tip_oid,
                retained.write.intent.operation_id, retained.write.intent.lane_id, retained.commit_metadata)
            _require(raw == expected, 'native reader immutable commit metadata differs')
        record = dict(candidate=oid, tree=tree, source=source, accepted_tip=retained.accepted_tip_oid,
            publication=json.loads(_json(publication_pin)),
            root=retained.write.plan.snapshot.receipt.root_digest,
            operation=retained.write.intent.operation_id, lane=retained.write.intent.lane_id,
            original=dict(owner_root=str(retained.owner_root), result_path=str(retained.result_path),
                result_id=retained.result_id, manifest=retained.manifest_digest))
        immutable = None if not verify else NativeGitClaimsBinding(self.repo, commit_oid=oid,
            expected_root_digest=record['root'], limits=retained.limits)
        return record, immutable

    def _expected_native_ready(self, record):
        if record is None:return self._ready
        value = json.loads(self._ready)
        value['native_generation'] = record
        payload = _json(value)
        _require(len(payload) <= self.MAX_STATE, 'native ready descriptor exceeds existing bound')
        return payload

    @staticmethod
    def _state_identity(info):
        _regular(info)
        return (info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns)

    @contextmanager
    def native_cycle(self, binding, *, budget_id, retention_id, current_generation=None):
        """Existing EX barrier BEFORE the original producer; no nested upgrade."""
        from engine.qledger_original_result import OriginalResultClaimsBinding
        _require(type(binding) is OriginalResultClaimsBinding and binding.repo_root == self.repo
                 and binding.original_process_id == os.getpid() and not binding.attempts
                 and binding.pre_attempt_failure is None, 'fresh exact original native producer required')
        with self.lease('install'):
            _require(self._native_ready_fd is None and self._native_checked is None,
                     'original native READY/completion operation remains unresolved')
            self._native_ready_started = self._native_ready_replaced = False
            self._native_transition = True
            self._native_owner_binding = binding
            self._native_confirmed = False
            try:
                record = None if current_generation is None else self._native_selection(current_generation)[0]
                self._native_expected = record
                context = dict(repo=self.repo, operation_id=binding.operation_id,lane_id=binding.lane_id,
                    budget_id=budget_id,retention_id=retention_id,commit_oid=self.candidate_oid,phase='before-native-generation')
                self.assert_valid(**context)
                expected_tip = self.candidate_oid if record is None else record['candidate']
                _require(all(t.accepted_tip_oid == expected_tip for t in binding.original_result_targets.values()),
                         'native original accepted data anchor differs from installed generation')
                if current_generation is not None:self._native_selection(current_generation, verify=True)
                old_root = (self.owner.readback(self.invocation.manifest_digest).snapshot.receipt.root_digest
                            if record is None else record['root'])
                _require(binding.read_snapshot().receipt.root_digest == old_root,
                         'current native root differs before production')
                self._native_old_ready = self._read(self.READY)
                self._native_old_identity = self._state_identity(os.stat(self.READY,dir_fd=self._dir_fd,follow_symlinks=False))
                _require(self._native_old_ready == self._expected_native_ready(record), 'native old READY differs')
                self._hold_identity = self._create(self.HOLD,self._held)
                self._check()
                yield self
                _require(self._native_confirmed and self._read(self.HOLD) == self._held
                         and self._read(self.READY) == self._expected_native_ready(self._native_expected),
                         'native generation was not durably confirmed; retain hold')
                checked = self._native_checked
                _require(checked is not None and checked.live.binding is binding
                         and checked.live.gate is self and checked.live.invocation is self.invocation
                         and checked.live.pid == os.getpid() and not checked.live.active
                         and checked.live.completed and checked.live.failure is None
                         and checked._finish_completed and checked._close_completed
                         and not checked.active and checked.failure is None,
                         'original native completion remains unresolved; retain hold')
                self.assert_valid(**dict(context,phase='after-native-generation'))
                self._assert('assert_descendants_settled',**context)
                info=os.stat(self.HOLD,dir_fd=self._dir_fd,follow_symlinks=False)
                _require((info.st_dev,info.st_ino) == self._hold_identity, 'original native HOLD changed before release')
                os.unlink(self.HOLD,dir_fd=self._dir_fd)
                os.fsync(self._dir_fd)
                self._hold_identity=None
                os.close(self._native_ready_fd)
                self._native_ready_fd=None
                self._native_checked=None
            finally:
                self._native_transition = False
                self._native_owner_binding = None
                self._native_expected = None

    def _replace_native_ready(self,payload):
        _require(not self._native_ready_started, 'native READY update already entered; no replay')
        self._native_ready_started = True
        _require(len(payload) <= self.MAX_STATE, 'native READY exceeds existing bound')
        _require(self._read(self.READY) == self._native_old_ready
                 and self._state_identity(os.stat(self.READY,dir_fd=self._dir_fd,follow_symlinks=False)) == self._native_old_identity,
                 'old READY bytes/inode changed; preserve foreign state')
        name = self.READY+'.lock'
        fd = os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=self._dir_fd)
        self._native_ready_fd = fd
        identity = self._state_identity(os.fstat(fd))[:2]
        _require(os.write(fd,payload) == len(payload), 'partial native READY write; preserve original handle')
        os.fsync(fd)
        self._check()
        _require(self._read(self.READY) == self._native_old_ready
                 and self._state_identity(os.stat(self.READY,dir_fd=self._dir_fd,follow_symlinks=False)) == self._native_old_identity,
                 'old READY changed before CAS; preserve foreign state')
        _require(self._state_identity(os.stat(name,dir_fd=self._dir_fd,follow_symlinks=False))[:2] == identity,
                 'owned native READY lock replaced; preserve foreign state')
        os.replace(name,self.READY,src_dir_fd=self._dir_fd,dst_dir_fd=self._dir_fd)
        self._native_ready_replaced = True
        os.fsync(self._dir_fd)
        _require(self._read(self.READY) == payload
                 and self._state_identity(os.stat(self.READY,dir_fd=self._dir_fd,follow_symlinks=False))[:2] == identity,
                 'native READY acknowledgement unavailable')

    def confirm_native_generation(self, checked, generation):
        from scripts.ci import qledger_engine_publication as engine
        from scripts.ci import qledger_engine_publisher as publisher
        _require(self._native_transition and self._mode == 'install' and self._hold_identity is not None,
                 'same exclusive native cycle must own durable HOLD')
        _require(type(checked) is engine._LiveFinalCandidate and type(generation) is publisher.NativePublishedGeneration
                 and checked.live.gate is self and checked.live.binding is self._native_owner_binding
                 and generation._attempt is checked.publication_attempt,
                 'actual live native publication generation required')
        attempt = generation._attempt
        try:
            self._native_checked = checked  # Preserve this actual original on failure.
            _require(publisher.confirmed(checked) and attempt.remote_confirmed and not attempt.uncertain
                     and checked._claims_entered and checked._index_lock is not None,
                     'known original publication and live claims/index/auth lifetime required')
            checked._check()
            prepared = checked.prepared
            retained = checked.invocation._original()
            network=type(attempt) is publisher._HTTPSPublicationAttempt
            pin=dict(origin=attempt.origin_digest,transport='checkout_https' if network else 'local_objects_and_loose_ref_cas',
                layout=None if network else [[os.fstat(fd).st_dev,os.fstat(fd).st_ino] for fd in
                    (attempt.origin_fd,attempt.origin_refs_fd,attempt.origin_heads_fd)])
            record = self._native_selection((prepared.candidate_oid,prepared.tree_oid,prepared.source_candidate_oid,retained,pin))[0]
            attempt.readback(prepared.candidate_oid)
            checked._check()
            context = dict(repo=self.repo,operation_id=checked.live.binding.operation_id,lane_id=checked.live.binding.lane_id,
                budget_id=checked.live.budget,retention_id=checked.live.retention,commit_oid=self.candidate_oid,phase='confirm-native-generation')
            self.assert_valid(**context)
            self._assert('assert_descendants_settled',**context)
            self._replace_native_ready(self._expected_native_ready(record))
            self._native_expected = record
            self._native_confirmed = True
        except BaseException as exc:
            if checked.failure is None:checked.failure = exc
            attempt.uncertain = True
            self.hold()
            raise

    def invoke_native_reader(self, selection, consumer, *, operation_id,lane_id,budget_id,retention_id,
                             original_deadline_monotonic_ns):
        from engine.qledger_store import ClaimsBindingScope,ClaimsReadScope,has_process_local_claims_selection
        from scripts.ci.qledger_owner_invocation import NativeReaderInvocation,reader_assertion_scope
        import time
        first = time.monotonic_ns()
        _require(all(type(value) is str and value for value in (operation_id,lane_id,budget_id,retention_id))
                 and self.producers.get((operation_id,lane_id)) == (budget_id,retention_id),
                 'actual separate native reader operation/resources required')
        _require(type(original_deadline_monotonic_ns) is int and first < original_deadline_monotonic_ns,
                 'actual original reader endpoint absent or expired')
        _require(not has_process_local_claims_selection(), 'inherited/conflicting reader selection cannot transfer')
        with self.lease('entry'):
            _require(self._native_reader_call is None, 'original native reader outcome remains unresolved')
            try:
                record,_ = self._native_selection(selection)
                self._native_expected = record
                context = dict(repo=self.repo,operation_id=operation_id,lane_id=lane_id,budget_id=budget_id,
                    retention_id=retention_id,commit_oid=self.candidate_oid,phase='native-reader')
                self.assert_valid(**context)
                self._assert('assert_resources',**context,original_reader_pid=os.getpid(),
                    original_reader_deadline_monotonic_ns=original_deadline_monotonic_ns,native_generation=record)
                record,immutable = self._native_selection(selection,verify=True)
                call = NativeReaderInvocation(self,immutable,record,context,original_deadline_monotonic_ns,first)
                self._native_reader_call = call
                call.check()
                with reader_assertion_scope(call):
                    self._assert('assert_publication_readback',**context,native_reader=call)
                call.check()
                with ClaimsBindingScope(immutable),ClaimsReadScope(self.repo):
                    result = consumer()
                call.check()
                self.assert_valid(**context)
                self._assert('assert_descendants_settled',**context,native_reader=call)
                call.check()
                return result
            except BaseException as exc:
                if self._native_reader_call is not None:
                    if self._native_reader_call.failure is None:self._native_reader_call.failure=exc
                    self._native_reader_call.uncertain=True
                raise
            finally:
                if self._native_reader_call is not None:self._native_reader_call.active = False
                if (self._native_reader_call is not None and self._native_reader_call.failure is None
                        and not self._native_reader_call.uncertain):self._native_reader_call = None
                self._native_expected = None



if __name__ == '__main__':
    raise SystemExit('UNCONFIGURED: use the owner-installed hook with actual live evidence; no admission issued')
