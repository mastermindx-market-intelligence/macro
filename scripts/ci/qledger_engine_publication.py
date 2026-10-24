"""Inactive complete engine-tree composition for explicitly ordered settled native originals.

Only a process-local original binding/write and its existing retained result are
accepted. Preparation writes unreferenced Git objects; it neither runs a producer
nor changes refs, index, checkout, budgets, selection or publication admission.
"""
from dataclasses import dataclass
from hashlib import sha256
import os
import selectors
import shlex
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from threading import Lock
from types import MappingProxyType

# Ordinary file-path imports pin this source tree. In a qualified bootstrap,
# __file__ belongs to the verified outside-checkout bundle; the finite finder
# still refuses every unqualified first-party import.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.qledger_original_result import OriginalResultClaimsBinding
from engine.qledger_store_protocol import SnapshotIntegrityError
from scripts.ci import qledger_conversion_candidate as candidate


def _require(value, message):
    if not value:
        raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', message)


@dataclass(frozen=True)
class CompleteEnginePublication:
    source_candidate_oid: str
    tree_oid: str
    candidate_oid: str
    accepted_tip_oid: str
    accepted_ref: str
    original_manifest_digest: str
    _owner: object
    effect: str = 'unreferenced_git_objects_only'
    eligible_for_cutover: bool = False


class EnginePublicationInvocation:
    """Join actual full engine output to the existing native continuity API.

    An initial-conversion result, serialized admission or another process's
    binding is not this interface. The assigning bootstrap/controller must still
    qualify the process, original resources and ordinary same-origin push.
    """
    def __init__(self, binding, write, *, retained_original=None, original_writes=None):
        _require(type(binding) is OriginalResultClaimsBinding,
                 'exact process-local retained-original producer binding required')
        self.binding, self.write, self.retained = binding, write, retained_original
        self.writes = (write,) if original_writes is None else original_writes
        _require(type(self.writes) is tuple and self.writes and self.writes[-1] is write,
                 "explicit ordered chain must end with this original write")
        self.pid = binding.original_process_id
        checked = self._original()
        self.manifest_digest = checked.manifest_digest

    def _original(self):
        b = self.binding
        _require(os.getpid() == self.pid == b.original_process_id,
                 'original producer process differs; inherited evidence cannot transfer')
        _require(b.pre_attempt_failure is None, 'native producer has an unresolved pre-attempt failure')
        checked = b.read_original_write_chain(self.writes, retained_original=self.retained)
        _require(not hasattr(self, 'manifest_digest') or checked.manifest_digest == self.manifest_digest,
                 'original native retained result changed')
        return checked

    def _source(self, source, tree, tip, ref):
        p = candidate.publication
        for value in (source, tree, tip):
            p._oid(value)
        candidate._ref_matches(self.binding.repo_root, ref, tip)
        _require(p._commit_tree(self.binding.repo_root, source, limits=self.binding.limits) == tree,
                 'actual complete frozen engine tree differs')
        p._git(self.binding.repo_root, ['merge-base', '--is-ancestor', tip, source], output_limit=128)

    def prepare(self, *, source_candidate_oid, expected_tree_oid, accepted_tip_oid, accepted_ref):
        checked = self._original()
        self._source(source_candidate_oid, expected_tree_oid, accepted_tip_oid, accepted_ref)
        # Preserve EVERY entry in the incumbent's final tree, including its
        # render-sync output. This is a new private publication object, not a
        # rewrite of the source candidate or a claims-only substitute.
        payload = candidate._native_commit_bytes(expected_tree_oid, accepted_tip_oid,
            self.binding.operation_id, self.binding.lane_id, checked.commit_metadata)
        oid = candidate._write_git_object(self.binding.repo_root,
            ['hash-object', '-t', 'commit', '-w', '--stdin'], payload)
        _require(oid == candidate._commit_identity(payload, accepted_tip_oid), 'engine commit identity differs')
        prepared = CompleteEnginePublication(source_candidate_oid, expected_tree_oid, oid,
            accepted_tip_oid, accepted_ref, checked.manifest_digest, self)
        self.check(prepared)
        return prepared

    def check(self, prepared, *, push_args=None):
        _require(type(prepared) is CompleteEnginePublication and prepared._owner is self
                 and prepared.original_manifest_digest == self.manifest_digest,
                 'exact same-process complete engine preparation required')
        checked = self._original()
        self._source(prepared.source_candidate_oid, prepared.tree_oid,
                     prepared.accepted_tip_oid, prepared.accepted_ref)
        if push_args is not None:
            _require(tuple(push_args) == ('origin', prepared.candidate_oid + ':refs/heads/main'),
                     'engine push must name the immutable complete publication candidate')
        payload = candidate._native_commit_bytes(prepared.tree_oid, prepared.accepted_tip_oid,
            self.binding.operation_id, self.binding.lane_id, checked.commit_metadata)
        actual, _ = candidate.publication._git(self.binding.repo_root,
            ['cat-file', 'commit', prepared.candidate_oid], output_limit=4096)
        _require(actual == payload, 'engine publication metadata or full tree changed')
        binding, witness = self.binding.check_publication_candidate(self.write,
            candidate_oid=prepared.candidate_oid, expected_tree_oid=prepared.tree_oid,
            accepted_tip_oid=prepared.accepted_tip_oid, accepted_ref=prepared.accepted_ref,
            retained_original=self.retained)
        self._original()
        candidate._ref_matches(self.binding.repo_root, prepared.accepted_ref, prepared.accepted_tip_oid)
        return binding, witness


@dataclass(frozen=True)
class NativeEngineRun:
    regions: object
    original_writes: tuple
    publication: CompleteEnginePublication | None
    # Verifying a candidate is distinct from ordinary authenticated publication.
    status: str
    eligible_for_cutover: bool = False


class _LiveFinalCandidate:
    """Call existing native continuity in its creator, under the live gate.

    The incumbent finalizer calls this with its actual complete frozen tree.
    It receives an immutable object to check/use, never the native binding or a
    serialized receipt authorizing another process to adopt original outcomes.
    """
    def __init__(self, invocation, live, original_deadline=None):
        self.invocation, self.live = invocation, live
        self.prepared, self.failure, self.active = None, None, True
        self.original_deadline = original_deadline
        self._claims_context = self._locked_source = self._index_lock = None
        self._claims_entered = False
        self._index_path = self._index_before = None
        self._prepare_started = self._prepare_uncertain = False
        self.unsettled_preparation = None

    def _deadline(self):
        _require(type(self.original_deadline) is int and time.monotonic_ns() < self.original_deadline,
                 'unchanged original finalizer endpoint absent or expired')
        return (self.original_deadline - time.monotonic_ns()) / 1_000_000_000

    def _index_fingerprint(self):
        try:
            fd = os.open(self._index_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return None
        try:
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                     and before.st_size <= self.invocation.binding.limits.snapshot_bytes,
                     'unsafe or unbounded authoritative index')
            h, count = sha256(), 0
            while True:
                self._deadline()
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                count += len(chunk)
                _require(count <= before.st_size, 'authoritative index grew')
                h.update(chunk)
            identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
            _require(count == before.st_size and identity(before) == identity(os.fstat(fd))
                     == identity(os.stat(self._index_path, follow_symlinks=False)), 'authoritative index changed')
            return identity(before), h.hexdigest()
        finally:
            os.close(fd)

    def _assert_index(self):
        self._deadline()
        try:
            self._index_lock.assert_valid()
        except OSError as exc:
            raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', 'original index lock changed; preserved') from exc
        _require(self._index_fingerprint() == self._index_before, 'authoritative index changed after freeze')
        b = self.invocation.binding
        target = b._target_for(self.invocation.write.intent)
        candidate._ref_matches(b.repo_root, 'refs/heads/main', target.accepted_tip_oid)
        candidate._ref_matches(b.repo_root, target.accepted_ref, target.accepted_tip_oid)

    def _program(self, path=None, *, name=None):
        from scripts.ci.qledger_host_gate import CodePin
        pins = (*getattr(self.live.gate, 'owner_code', ()), *getattr(self.live.gate, 'runtime_code', ()))
        matches = [p for p in pins if type(p) is CodePin and
                   (p.path == path if path is not None else p.path.name == name)]
        _require(matches and len({(p.path, p.digest) for p in matches}) == 1,
                 'exact qualified finalizer program pin absent or ambiguous')
        pin = matches[0]
        pin.check()
        fd = os.open(pin.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            payload = os.read(fd, 16 * 1024 * 1024 + 1)
        finally:
            os.close(fd)
        _require(len(payload) <= 16 * 1024 * 1024 and sha256(payload).hexdigest() == pin.digest,
                 'qualified finalizer program bytes differ')
        pin.check()
        return payload

    def _run_prepare(self, program, args):
        """Bounded same-carrier local preparation; never kill/retry on lost response."""
        env = {k:v for k,v in os.environ.items() if not k.startswith('BASH_FUNC_') and k not in (
            'BASH_ENV','ENV','SHELLOPTS','BASHOPTS','GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR',
            'GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES')}
        env.update(GITHUB_WORKSPACE=str(self.invocation.binding.repo_root), GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
        with tempfile.TemporaryFile() as supplied:
            supplied.write(program); supplied.seek(0)
            child = subprocess.Popen(['/bin/bash','-s','--',*args], cwd=self.invocation.binding.repo_root,
                env=env, stdin=supplied, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.unsettled_preparation = child
        buffers = {child.stdout:bytearray(), child.stderr:bytearray()}
        with selectors.DefaultSelector() as selector:
            for stream in buffers:
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                ready = selector.select(max(0, self._deadline()))
                _require(ready, 'original finalizer response deadline exhausted; index lock preserved')
                for key, _ in ready:
                    data = os.read(key.fd, min(65536, 16385-len(buffers[key.fileobj])))
                    _require(len(buffers[key.fileobj])+len(data) <= 16384,
                             'unbounded finalizer response; original process/index lock preserved')
                    if data:
                        buffers[key.fileobj].extend(data)
                    else:
                        selector.unregister(key.fileobj)
            try:
                rc = child.wait(timeout=max(0,self._deadline()))
            except subprocess.TimeoutExpired as exc:
                raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', 'original finalizer completion unknown; index lock preserved') from exc
        self.unsettled_preparation = None
        for stream in buffers:
            stream.close()
        if rc:
            # The frozen object-only program settled without any install path.
            # Its known empty index resource can still be released by its owner.
            self._prepare_uncertain = False
            _require(False, 'original prepare-only finalizer refused: '+bytes(buffers[child.stderr]).decode('utf-8','replace'))
        return bytes(buffers[child.stdout])

    def prepare_engine_tree(self, message):
        """Freeze the incumbent's already-normalized/staged COMPLETE final tree.

        No normalizer is skipped or asserted by this method. The qualified
        incumbent must run its actual guards before this freeze; no rebase or
        installing render-sync operation is supported under this source version.
        """
        try:
            self._check()
            _require(not self._prepare_started, 'original finalizer preparation already entered; no replay')
            self._prepare_started = True
            self._deadline()
            _require(type(message) is str and 0 < len(message.encode()) <= 4096 and '\x00' not in message,
                     'finite original finalizer message required')
            from engine.qledger_store_sources import claims_lock, LockedLocalSource, LOCK_RELATIVE_PATH
            from scripts.ci import options_index_lock_identity as index_owner
            b = self.invocation.binding
            target = b._target_for(self.invocation.write.intent)
            _require(target.accepted_ref == 'refs/remotes/origin/main' and target.accepted_tip_oid == self.live.installed,
                     'ordinary original source/accepted anchor differs; no rebase equivalence')
            program = self._program(name='options_signal_nightly.sh')
            helper = self._program(Path(index_owner.__file__).resolve())
            self._claims_context = claims_lock(b.repo_root / LOCK_RELATIVE_PATH, mode='shared', timeout=0)
            lease = self._claims_context.__enter__()
            self._claims_entered = True
            self._locked_source = LockedLocalSource(b.repo_root, lease=lease,
                expected_root_digest=self.invocation.write.plan.snapshot.receipt.root_digest, limits=b.limits)
            self._check()  # existing lease is reused; acquire no claims lock below
            raw, _ = candidate.publication._git(b.repo_root, ['rev-parse','--git-path','index'], output_limit=4096)
            index = Path(raw.strip().decode())
            self._index_path = index if index.is_absolute() else b.repo_root / index
            self._index_lock = index_owner.OwnedEmptyIndexLock(str(self._index_path)+'.lock')
            self._index_before = self._index_fingerprint()
            self._assert_index()
            # Execute frozen qualified bytes, including the stdlib-only checker;
            # the object-only shell does not source checkout Python/retry code.
            prefix = ('OIP_NATIVE_PYTHON='+shlex.quote(sys.executable)+'\nOIP_NATIVE_INDEX_HELPER_CODE='
                      +shlex.quote(helper.decode())+'\n').encode()
            self._prepare_uncertain = True
            raw = self._run_prepare(prefix+program, ['prepare-broad-candidate', message,
                target.accepted_tip_oid, target.accepted_ref, self._index_lock.identity])
            values = raw.decode('ascii').splitlines()
            _require(len(values) == 4, 'original finalizer response missing; index lock preserved')
            for oid in values:
                candidate.publication._oid(oid)
            source, tree, parent, accepted = values
            _require(parent == accepted == target.accepted_tip_oid, 'original accepted source changed')
            self._assert_index()
            self._prepare_uncertain = False
            return self(source_candidate_oid=source, expected_tree_oid=tree,
                        accepted_tip_oid=accepted, accepted_ref=target.accepted_ref)
        except BaseException as exc:
            self.failure = exc
            raise

    def close(self):
        self.active = False
        try:
            if self._index_lock is not None:
                try:
                    self._index_lock.close(preserve=self._prepare_uncertain or self.unsettled_preparation is not None)
                except OSError as exc:
                    raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', 'index lock custody changed; foreign lock preserved') from exc
        finally:
            if self._claims_entered:
                self._claims_entered = False
                self._claims_context.__exit__(None,None,None)

    def _check(self):
        _require(self.active and self.failure is None, 'final-candidate callback closed or unresolved')
        self.live.check('engine-final-candidate')
        if self._index_lock is not None:
            self._assert_index()
        # Retained originals and a Git tree do not prove that an intervening
        # local native transaction/tail has not changed the producer's root.
        # Use the existing bounded locked reader, never a raw ROOT observation.
        if self._locked_source is None:
            current = self.invocation.binding.read_snapshot()
        else:
            from engine.qledger_store_sources import verify_source_snapshot
            current = verify_source_snapshot(self._locked_source, limits=self.invocation.binding.limits)
        _require(current.receipt.root_digest == self.invocation.write.plan.snapshot.receipt.root_digest,
                 'current native root differs from complete original sequence')
        self.live.check('engine-final-candidate')

    def __call__(self, **actual_final_candidate):
        try:
            self._check()
            prepared = self.invocation.prepare(**actual_final_candidate)
            self.invocation.check(prepared)
            self._check()
            self.prepared = prepared
            return prepared
        except BaseException as exc:
            # A finalizer catching an earlier failure cannot return an older
            # good object as if every required boundary had succeeded.
            self.failure = exc
            raise

    def check_push(self, prepared, *, push_args):
        try:
            self._check()
            _require(prepared is self.prepared, 'latest exact final candidate required')
            result = self.invocation.check(prepared, push_args=push_args)
            self._check()
            return result
        except BaseException as exc:
            self.failure = exc
            raise

    def finish(self, returned):
        self._check()
        _require(returned is self.prepared and returned is not None,
                 'incumbent must return its actual checked final candidate')
        self.invocation.check(returned)
        self._check()
        return returned

    def __reduce__(self):
        raise TypeError('live final-candidate callback cannot transfer')


class _NativeEngineProducer:
    def __init__(self, context, binding, regions, intents, finalizer, call):
        _require(type(binding) is OriginalResultClaimsBinding and binding.repo_root == context.repo
                 and os.getpid() == binding.original_process_id, 'fresh exact original engine binding required')
        _require(callable(finalizer), 'qualified incumbent finalizer callback is required before production')
        loader = globals().get('__loader__')
        if getattr(loader, '_qledger_bootstrap_active', False):
            # Reusing this qualified factory must not launder a checkout-loaded
            # finalizer through our qualified callable's module identity.
            loader.callable(finalizer)
        from engine.qledger_store_native import NativeClaimsIntent
        _require(type(regions) in (tuple, list) and regions and len(regions) <= 4
                 and len(set(regions)) == len(regions) and type(intents) is dict
                 and set(regions) == set(intents)
                 and all(type(x) is NativeClaimsIntent for x in intents.values())
                 and len(set(intents.values())) == len(regions), 'finite distinct declared engine regions/intents required')
        for intent in intents.values():
            binding._check_intent(intent)
            binding._target_for(intent)
        _require(not binding.attempts and not binding.prepared_original_results
                 and binding.pre_attempt_failure is None, 'fresh original invocation cannot borrow earlier producer outcomes')
        self.binding, self.regions, self.intents = binding, tuple(regions), dict(intents)
        self.finalizer, self.call, self.started = finalizer, call, False
        self.original_deadline = getattr(context, 'original_deadline_monotonic_ns', None)
        self.finalization = None  # retain same original local handle on unknown preparation
        self.guard = Lock()

    def __call__(self):
        from scripts.ci.qledger_owner_invocation import require_live_producer
        live = require_live_producer(self.binding)
        with self.guard:
            _require(not self.started, 'original engine producer already entered; reconcile without replay')
            self.started = True
        # Constructor-time checks cannot bind future originals. Revalidate and
        # own the actual binding before any deterministic/native/finalizer work.
        with self.binding._fresh_original_invocation():
            return self._run(live)

    def _run(self, live):
        from scripts import build_allocation as allocation
        _require(allocation.config.ROOT == self.binding.repo_root,
                 'deterministic allocation root differs from admitted producer root')
        live.check('engine-deterministic-build')
        _require(not allocation.main(self.regions, run_ai=False), 'deterministic engine build failed')
        live.check('engine-native-producer')
        results = allocation.run_native_thematic_owner(self.regions, native_intents=self.intents,
            root=self.binding.repo_root, owner_binding=self.binding, call=self.call)
        live.check('engine-native-returned')
        writes = tuple(w for w, _ in self.binding.prepared_original_results)
        _require(self.binding.pre_attempt_failure is None, 'engine returned after an unresolved native admission')
        if not writes:
            _require(not self.binding.attempts, 'native attempts exist without original retained results')
            # Legitimate skipped/no-write owners remain successful producers.
            # They do not manufacture a native publication or invoke a finalizer
            # that could mistake no write for a retained original result.
            return NativeEngineRun(MappingProxyType(dict(results)), (), None, 'no_native_write')
        _require(all(w.intent in self.intents.values() for w in writes), 'engine produced an undeclared original')
        native = EnginePublicationInvocation(self.binding, writes[-1], original_writes=writes)
        final = self.finalization = _LiveFinalCandidate(native, live, self.original_deadline)
        try:
            prepared = final.finish(self.finalizer(final))
            return NativeEngineRun(MappingProxyType(dict(results)), writes, prepared, 'candidate_verified')
        finally:
            final.close()

    def __reduce__(self):
        raise TypeError('original engine producer cannot transfer')


def build_native_engine_producer(context, *, owner_binding, regions, native_intents, finalizer, call=None):
    """Compose an outside-checkout entry's existing ``build_producer(context)``.

    The qualified owner supplies its genuine original binding and incumbent
    finalizer. No policy/provider/IDs/deadline are created here. LoadedBootstrap
    retains its gate lease while invoking this callback. The finalizer prepares
    unreferenced full-tree objects under the unchanged installed checkout;
    ordinary Bash rebase/checkout is NOT qualified by this interface and still
    fails the existing HostGate installed-version checks. Native clocks/outcomes
    never cross to the fresh initial-conversion CLI.
    """
    return owner_binding, _NativeEngineProducer(context, owner_binding, regions,
        native_intents, finalizer, call)
