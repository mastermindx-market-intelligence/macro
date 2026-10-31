"""Inactive complete engine-tree composition for explicitly ordered settled native originals.

Only a process-local original binding/write and its existing retained result are
accepted. The native daily finalizer normalizes/stages through incumbent APIs;
its final freeze writes unreferenced Git objects without installing refs/index.
No budgets, selection or publication admission are created here.
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
from scripts.ci import qledger_engine_publisher as native_publisher


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
        self.publication_guard = Lock()
        self.publication_attempt = None
        self._finish_completed = self._close_completed = False

    def _record_failure(self, exc):
        if self.failure is None:
            self.failure = exc
        if self.publication_attempt is not None:
            self.publication_attempt.uncertain = True

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

    def _data_tip(self):
        gate=self.live.gate
        if getattr(gate,'_native_transition',False):
            return gate.native_data_tip(self.invocation.binding,original_deadline_monotonic_ns=self.original_deadline)
        return self.live.installed

    def _assert_index(self):
        self._deadline()
        try:
            self._index_lock.assert_valid()
        except OSError as exc:
            raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', 'original index lock changed; preserved') from exc
        _require(self._index_fingerprint() == self._index_before, 'authoritative index changed after freeze')
        b = self.invocation.binding
        target = b._target_for(self.invocation.write.intent)
        candidate._ref_matches(b.repo_root, 'refs/heads/main', self.live.installed)
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

    def _run_prepare(self, program, args, *, stream_output=False):
        """Bounded same-carrier preparation; streaming logs are never object responses.

        Never kill/retry on lost response. Object-response capture keeps its
        original finite limit; incumbent staging logs stream to the owner only.
        """
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
                    data = os.read(key.fd, 65536 if stream_output else min(65536, 16385-len(buffers[key.fileobj])))
                    _require(stream_output or len(buffers[key.fileobj])+len(data) <= 16384,
                             'unbounded finalizer response; original process/index lock preserved')
                    if data:
                        if stream_output:
                            # Existing owner log, bounded chunks, no retained second store.
                            sys.stderr.write(data.decode('utf-8', 'replace')); sys.stderr.flush()
                        else:
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
            _require(target.accepted_ref == 'refs/remotes/origin/main' and target.accepted_tip_oid == self._data_tip(),
                     'ordinary original accepted data anchor differs; no rebase equivalence')
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
                target.accepted_tip_oid, target.accepted_ref, self._index_lock.identity, self.live.installed])
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
            if self.publication_attempt is not None:
                try:self.publication_attempt.close_known()
                except BaseException as exc:
                    self._record_failure(exc)
                    raise
            if self._index_lock is not None:
                try:
                    self._index_lock.close(preserve=self._prepare_uncertain or self.unsettled_preparation is not None
                        or (self.publication_attempt is not None and self.publication_attempt.uncertain))
                except OSError as exc:
                    raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', 'index lock custody changed; foreign lock preserved') from exc
        finally:
            if self._claims_entered:
                self._claims_entered = False
                self._claims_context.__exit__(None,None,None)
        self._close_completed = (self.failure is None and not self._prepare_uncertain
            and self.unsettled_preparation is None
            and (self.publication_attempt is None or not self.publication_attempt.uncertain))

    def _check(self):
        _require(self.active and self.failure is None, 'final-candidate callback closed or unresolved')
        self.live.check('engine-final-candidate')
        target=self.invocation.binding._target_for(self.invocation.write.intent)
        _require(target.accepted_tip_oid==self._data_tip(), 'original accepted data anchor changed')
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
        try:
            self._check()
            _require(returned is self.prepared and returned is not None,
                     'incumbent must return its actual checked final candidate')
            self.invocation.check(returned)
            self._check()
            self._finish_completed = True
            return returned
        except BaseException as exc:
            self._record_failure(exc)
            raise

    def __reduce__(self):
        raise TypeError('live final-candidate callback cannot transfer')



def _qualify_daily_destinations(checked, *, accepted_tip_oid):
    """Metadata-only qualification of the WHOLE incumbent mutation scope.

    Normalizers write existing HTML/pairs, copy fixed assets, create/prune hash
    assets and write the Gold receipt. Git helpers restore/delete arbitrary
    dirty members of the same four roots. Qualify all those roots, not a list
    of currently known filenames; reject aliases in restoration sources too.
    The actual live controller still owns exclusion of concurrent mutators.
    """
    from engine.qledger_store_sources import _open_directory
    b = checked.invocation.binding
    roots = ('data', 'site', 'templates', 'reports')
    remaining = b.limits.reference_visits
    raw, _ = candidate.publication._git(b.repo_root,
        ['ls-tree', '-r', '-z', accepted_tip_oid, '--', *roots],
        output_limit=b.limits.snapshot_bytes)
    checked._deadline()
    _require(not raw or raw.endswith(b'\0'), 'incomplete accepted restoration inventory')
    for entry in raw.split(b'\0')[:-1]:
        remaining -= 1
        checked._deadline()
        _require(remaining >= 0, 'daily destination inventory exceeds original visit bound')
        meta, path = entry.split(b'\t', 1)
        fields = meta.split()
        _require(len(fields) == 3 and fields[0] in (b'100644', b'100755')
                 and fields[1] == b'blob' and path.split(b'/')[0] in {r.encode() for r in roots},
                 'accepted restoration source contains an alias or non-file')

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
    seen = set()
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_mtime_ns, info.st_ctime_ns)
    def walk(fd, depth):
        nonlocal remaining
        checked._deadline()
        before = os.fstat(fd)
        _require(depth <= 128 and stat.S_ISDIR(before.st_mode)
                 and (before.st_dev, before.st_ino) not in seen,
                 'daily destination directory is aliased or unbounded')
        seen.add((before.st_dev, before.st_ino))
        with os.scandir(fd) as entries:
            for entry in entries:
                remaining -= 1
                checked._deadline()
                _require(remaining >= 0, 'daily destination inventory exceeds original visit bound')
                info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(entry.name, flags, dir_fd=fd)
                    try:
                        _require(identity(os.fstat(child)) == identity(info), 'daily destination directory changed')
                        walk(child, depth+1)
                    finally:
                        os.close(child)
                else:
                    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                             'daily destination contains a symbolic, hard or special-file alias')
                _require(identity(os.stat(entry.name, dir_fd=fd, follow_symlinks=False)) == identity(info),
                         'daily destination changed during qualification')
        _require(identity(os.fstat(fd)) == identity(before), 'daily directory changed during qualification')

    parent = _open_directory(b.repo_root)
    try:
        seen.add((os.fstat(parent).st_dev, os.fstat(parent).st_ino))
        for name in roots:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            _require(stat.S_ISDIR(info.st_mode), 'actual daily root is aliased or absent')
            fd = os.open(name, flags, dir_fd=parent)
            try:
                _require(identity(os.fstat(fd)) == identity(info), 'daily root changed')
                walk(fd, 1)
            finally:
                os.close(fd)
            _require(identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == identity(info), 'daily root changed')
    except OSError as exc:
        raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', 'daily destination qualification failed before effects') from exc
    finally:
        os.close(parent)
    checked._deadline()


def finalize_daily_engine_outputs(checked):
    """Native-only daily normalization/staging, then one object-only freeze.

    The ordinary installing shell remains unchanged. Its pinned staging body is
    reused verbatim except for the QLedger exclusion on restorative helpers.
    No retry initialization, rebase, ref/index installation or push runs here.
    """
    _require(type(checked) is _LiveFinalCandidate, 'live original finalizer required')
    try:
        checked._check()  # BEFORE imports, normalization, restoration or deletion
        _require(not getattr(checked, '_daily_started', False), 'daily finalizer already entered; no replay')
        checked._daily_started = True
        b = checked.invocation.binding
        repo = b.repo_root
        target = b._target_for(checked.invocation.write.intent)

        def check():
            checked._deadline()
            checked._check()
            _require(target.accepted_tip_oid == checked._data_tip()
                     and target.accepted_ref == 'refs/remotes/origin/main',
                     'unchanged ordinary accepted source required')
            candidate._ref_matches(repo, 'refs/heads/main', checked.live.installed)
            candidate._ref_matches(repo, target.accepted_ref, target.accepted_tip_oid)

        check()
        daily = checked._program(name='daily_engine_commit_outputs.sh').decode()
        retry = checked._program(name='push_retry.sh')
        strip = checked._program(name='strip_conflict_markers.sh')
        options = checked._program(name='options_signal_nightly.sh').decode()
        # Exact markers fail closed on a future incumbent policy change. Never
        # import/source mutable checkout Python or a checkout shell dispatcher.
        begin = 'git add data/ site/ reports/\n'
        end = 'bash scripts/ci/options_signal_nightly.sh commit-broad-candidate \\\n'
        _require(daily.count(begin) == daily.count(end) == 1, 'incumbent daily staging seam changed')
        stage = daily.split(begin)[1].split(end)[0]
        narrow = 'bash scripts/ci/options_signal_nightly.sh exclude-broad'
        heal = 'push_staged_heal data/ site/ reports/ templates/'
        _require(stage.count(narrow) == stage.count(heal) == 1, 'incumbent daily exclusions changed')
        stage = (begin + stage).replace(narrow, 'exclude_broad').replace(
            heal, heal + " ':(exclude)data/qledger/**'")
        declaration = 'readonly -a OIP_EPISODE_CORE_PATHS=('
        dispatch = 'if [ "${BASH_SOURCE[0]:-}" = "$0" ] || [ -z "${BASH_SOURCE[0]:-}" ]; then'
        _require(options.count(declaration) == options.count(dispatch) == 1, 'incumbent Options library seam changed')
        functions = declaration + options.split(declaration)[1].split(dispatch)[0]
        if target.accepted_tip_oid != checked.live.installed:
            # Only the qualified native snippets change baseline; the ordinary
            # shell files/installing wrappers retain their exact HEAD behavior.
            tip=target.accepted_tip_oid
            def replace_exact(text,old,new,count):
                _require(text.count(old)==count,'incumbent accepted-data restoration seam changed')
                return text.replace(old,new)
            stage=replace_exact(stage,'git checkout HEAD --','git checkout '+tip+' --',2)
            stage=replace_exact(stage,'git reset -q --','git reset -q '+tip+' --',3)
            stage=replace_exact(stage,'git diff --cached --quiet','git diff --cached '+tip+' --quiet',2)
            functions=replace_exact(functions,'git cat-file -e "HEAD:$root"','git cat-file -e "'+tip+':$root"',1)
            functions=replace_exact(functions,'git checkout HEAD -- "$root"','git checkout '+tip+' -- "$root"',1)
            functions=replace_exact(functions,'git reset -q -- "${OIP_NARROW_ROOTS[@]}"','git reset -q '+tip+' -- "${OIP_NARROW_ROOTS[@]}"',1)
            # Only the broad publisher compares its staged snapshot with the
            # accepted DATA generation. The narrow checkpoint clean-index
            # guard has the same diff spelling and retains its HEAD contract.
            broad_start='oip_require_clean_broad_start() {\n  if ! git diff --cached --quiet; then\n'
            functions=replace_exact(functions,broad_start,
                broad_start.replace('git diff --cached --quiet','git diff --cached '+tip+' --quiet'),1)
            retry=replace_exact(retry.decode(),'git checkout HEAD -- "$f"','git checkout '+tip+' -- "$f"',1)
            retry=replace_exact(retry,'diff --cached --name-only --diff-filter=d --','diff --cached '+tip+' --name-only --diff-filter=d --',1).encode()
            strip=replace_exact(strip.decode(),'git checkout HEAD -- "$f"','git checkout '+tip+' -- "$f"',1)
            strip=replace_exact(strip,'git diff HEAD --name-only -z','git diff '+tip+' --name-only -z',1).encode()
        library = retry + b'\n' + functions.encode() + b'\nset -e\n'
        prefix = ('REPO_ROOT=' + shlex.quote(str(repo)) + '\n').encode()
        _require((repo/'site').is_dir() and not (repo/'site').is_symlink()
                 and (repo/'templates').is_dir() and not (repo/'templates').is_symlink(),
                 'actual complete render roots required')

        from lib import config, shared_shell
        from scripts import (inject_data_base, externalize_css, optimize_assets,
                             check_template_site_sync, check_start_runtime,
                             check_ms_board_coherence, check_commodity_publication,
                             check_conflict_markers, audit_china_gold_premium)
        _require(config.ROOT == repo, 'normalizers require actual original ROOT')
        _require(config.data_dir() == repo/'data' and config.site_dir() == repo/'site',
                 'normalizer configuration redirects actual mutation roots')
        _qualify_daily_destinations(checked, accepted_tip_oid=target.accepted_tip_oid)
        check()
        # optimize_assets reads these canonical bundle assets through its native
        # Shared Shell API. Qualify the real bytes and their checkout projection.
        for name in (shared_shell.ASSET_NAME, shared_shell.STYLESHEET_NAME):
            frozen = checked._program(shared_shell.ROOT/'templates'/name)
            local = repo/'templates'/name
            _require(not local.is_symlink() and local.is_file()
                     and local.stat().st_size == len(frozen)
                     and local.read_bytes() == frozen, 'qualified Shared Shell asset differs from original render source')

        def warn_run(label, operation):
            check()
            try:
                rc = operation()
                if isinstance(rc, int) and rc < 0:
                    print('::warning::'+label+' failed; retaining incumbent lane-local semantics', file=sys.stderr)
            except Exception as exc:
                print('::warning::'+label+' failed: '+str(exc), file=sys.stderr)
            check()

        def normalize():
            warn_run('data-base normalization', lambda: inject_data_base.inject(repo/'site'))
            warn_run('CSS externalization', lambda: externalize_css.externalize(repo/'site'))
            warn_run('asset optimization', lambda: optimize_assets.optimize(repo/'site'))
            warn_run('template synchronization', lambda: check_template_site_sync.check(repo, fix=True))

        def start_guard():
            check()
            page = repo/'site/start.html'
            _require(not check_conflict_markers.scan_file(str(page)), 'start page conflict markers')
            if check_start_runtime.check_page(page):
                _require(check_start_runtime.heal_from(target.accepted_tip_oid, page)
                         and not check_start_runtime.check_page(page), 'start runtime restore failed')
            check()

        def sweep():
            check()
            # A subshell preserves the incumbent helper's own exit semantics.
            program = (b'(\n' + strip + b'\n)\n')
            checked._run_prepare(program, ['site/', 'templates/', 'data/', 'reports/',
                                          ':(exclude)data/qledger/**'], stream_output=True)
            check()

        normalize()
        start_guard()
        sweep()
        checked._run_prepare(prefix+library+b'exclude_broad\noip_require_clean_broad_start\n', [], stream_output=True)
        check()
        # Match the incumbent final loop without pretending a rebase/install.
        check_commodity_publication.verify_publication(repo, target.accepted_tip_oid, heal=True)
        normalize()
        for page in sorted((repo/'site').glob('*.html')):
            check()
            if check_ms_board_coherence.check_page(page):
                if (not check_ms_board_coherence.heal_from(target.accepted_tip_oid, page)
                        or check_ms_board_coherence.check_page(page)):
                    print('::warning::MS board coherence incomplete after accepted restore', file=sys.stderr)
        sweep()
        start_guard()
        warn_run('China gold premium final render audit', lambda: audit_china_gold_premium.run(strict_render=True))
        check()
        checked._run_prepare(prefix+library+stage.encode(), [], stream_output=True)
        check()
        prepared = checked.prepare_engine_tree('engine: original complete normalized output')
        check_commodity_publication.verify_publication(repo, target.accepted_tip_oid,
                                                       candidate_ref=prepared.candidate_oid)
        check()
        return prepared
    except BaseException as exc:
        checked.failure = exc
        raise


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
            _require(final._finish_completed and final.failure is None,
                     'actual original finalizer completion is unavailable')
            status = 'publication_confirmed' if native_publisher.confirmed(final) else 'candidate_verified'
            return NativeEngineRun(MappingProxyType(dict(results)), writes, prepared, status)
        except BaseException as exc:
            # Record before close: an outer wrapper cannot hide the failure or
            # cause uncertain original handles to be disposed as known success.
            final._record_failure(exc)
            raise
        finally:
            try:
                final.close()
            except BaseException as exc:
                final._record_failure(exc)
                raise

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


def publish_native_engine(checked, prepared, *, reader=None, **original_push):
    """Opt-in original effect/readback; no default production transport/admission."""
    return native_publisher.publish(checked, prepared, reader=reader, **original_push)
