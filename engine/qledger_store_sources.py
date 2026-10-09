"""Inactive, explicit QLedger snapshot transports; no production selection.

Git reads one local tree, never a worktree or a fetched/promised fallback.
Local reads require a process-bound cooperative lease for the declared root's
stable lock. Only verify_source_snapshot returns verified claims history.
These adapters retain the protocol's finite in-memory profile; they do not
repair memory use, authorize a migration, or fence non-cooperating old writers.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import wraps
from hashlib import sha1, sha256
import math
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import time
from types import MappingProxyType

try:
    import fcntl
except ImportError:  # Explicitly unsupported; never a thread-lock substitute.
    fcntl = None

from engine.qledger_store_protocol import (
    BASE_PATH, ROOT_PATH, PART_PREFIX, PAGE_PREFIX, MemberRef, PinnedSource,
    ProtocolLimits, SnapshotIntegrityError, VerifiedSnapshot,
    decode_root, verify_snapshot,
)

LOCK_RELATIVE_PATH = "data/qledger/claims.store.lock"
MAX_LOCK_TIMEOUT_SECONDS = 30.0
SOURCE_TIMEOUT_SECONDS = 30.0
_LEASE_SEAL = object()
_PATH_TYPE = type(Path())
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def _fail(code, message):
    raise SnapshotIntegrityError(code, message)


def _typed(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except SnapshotIntegrityError:
            raise
        except FileNotFoundError as exc:
            raise SnapshotIntegrityError("MISSING", function.__name__) from exc
        except Exception as exc:
            raise SnapshotIntegrityError(
                "MALFORMED", f"{function.__name__}: {type(exc).__name__}"
            ) from exc
    return checked


def _limits(value):
    if type(value) is not ProtocolLimits:
        _fail("MALFORMED", "an exact ProtocolLimits value is required")
    # Revalidate even an object whose frozen fields were bypassed by a caller.
    return ProtocolLimits(**asdict(value))


def _absolute(value):
    if type(value) is not _PATH_TYPE or not value.is_absolute():
        _fail("MALFORMED", "an explicit absolute Path is required")
    if ".." in value.parts or "\x00" in str(value):
        _fail("MALFORMED", "unsafe path")
    return value


def _member_limit(path, limits):
    if type(path) is not str:
        _fail("MALFORMED", "member path must be an exact string")
    if path == BASE_PATH:
        return limits.base_bytes
    if path == ROOT_PATH:
        return limits.root_bytes
    for prefix, suffix, ceiling in (
        (PART_PREFIX, ".jsonl", limits.part_bytes),
        (PAGE_PREFIX, ".json", limits.page_bytes),
    ):
        if path.startswith(prefix) and path.endswith(suffix):
            token = path[len(prefix):-len(suffix)]
            if _HEX.fullmatch(token):
                return ceiling
    _fail("MALFORMED", "path is outside the declared claims namespace")


def _size(path, value, limits):
    ceiling = _member_limit(path, limits)
    minimum = 0 if path == BASE_PATH else 1
    if type(value) is not int or not minimum <= value <= ceiling:
        _fail("LIMIT", "member size is outside its profile")


def _identity(value):
    return (value.st_dev, value.st_ino)


def _file_identity(value):
    return (_identity(value), value.st_mode, value.st_nlink, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def _directory_flags():
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        _fail("UNSUPPORTED", "no-follow directory descriptors are required")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _open_directory(path):
    path = _absolute(path)
    fd = os.open(path.anchor, _directory_flags())
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, _directory_flags(), dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _parent_fd(root_fd, relative):
    parts = relative.split("/")
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, _directory_flags(), dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


@dataclass(frozen=True, init=False)
class ClaimsLockLease:
    """Opaque lease for exactly one root, stable lock inode and process."""

    _root: Path
    _root_fd: int
    _lock_fd: int
    _root_identity: tuple
    _lock_identity: tuple
    _pid: int
    _mode: str
    _active: bool
    _seal: object

    def __init__(self, *args, **kwargs):
        _fail("MALFORMED", "claims_lock must create leases")

    @property
    def root(self):
        self._check()
        return self._root

    @property
    def mode(self):
        self._check()
        return self._mode

    @_typed
    def assert_valid(self, root: Path, *, exclusive: bool = False) -> None:
        _lease_for(root, self)
        if type(exclusive) is not bool:
            _fail("MALFORMED", "exclusive requirement must be an exact bool")
        if exclusive and self._mode != "exclusive":
            _fail("MALFORMED", "an exclusive claims lease is required")

    @_typed
    def open_root_fd(self, root: Path, *, exclusive: bool = False) -> int:
        """Return a caller-owned duplicate; never expose the lock descriptor."""
        self.assert_valid(root, exclusive=exclusive)
        return os.dup(self._root_fd)

    @_typed
    def _check(self):
        if (self._seal is not _LEASE_SEAL or not self._active
                or self._pid != os.getpid()):
            _fail("SOURCE_CLOSED", "lease is inactive or belongs to another process")
        root_fd = _open_directory(self._root)
        try:
            if _identity(os.fstat(root_fd)) != self._root_identity:
                _fail("SOURCE_CHANGED", "declared root identity changed")
        finally:
            os.close(root_fd)
        if _identity(os.fstat(self._root_fd)) != self._root_identity:
            _fail("SOURCE_CHANGED", "root descriptor changed")
        parent, name = _parent_fd(self._root_fd, LOCK_RELATIVE_PATH)
        try:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        finally:
            os.close(parent)
        held = os.fstat(self._lock_fd)
        for info in (current, held):
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or _identity(info) != self._lock_identity):
                _fail("SOURCE_CHANGED", "stable lock identity changed")


@_typed
def _acquire_lock(lock_path, mode, timeout):
    lock_path = _absolute(lock_path)
    expected_parts = Path(LOCK_RELATIVE_PATH).parts
    if lock_path.parts[-len(expected_parts):] != expected_parts:
        _fail("MALFORMED", "lock must be the declared root's claims lock")
    if type(mode) is not str or mode not in {"shared", "exclusive"}:
        _fail("MALFORMED", "unknown lock mode")
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 <= timeout <= MAX_LOCK_TIMEOUT_SECONDS):
        _fail("LIMIT", "invalid lock timeout")
    if fcntl is None:
        _fail("UNSUPPORTED", "cross-process POSIX locking is required")
    root = lock_path.parents[len(expected_parts) - 1]
    root_fd = _open_directory(root)
    lock_fd = None
    try:
        parent, name = _parent_fd(root_fd, LOCK_RELATIVE_PATH)
        try:
            lock_fd = os.open(
                name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                0o600, dir_fd=parent,
            )
        finally:
            os.close(parent)
        info = os.fstat(lock_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            _fail("MALFORMED", "lock must be a singly linked regular file")
        action = fcntl.LOCK_SH if mode == "shared" else fcntl.LOCK_EX
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(lock_fd, action | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    _fail("LOCK_TIMEOUT", "claims lock is busy")
                time.sleep(min(0.01, remaining))
        lease = object.__new__(ClaimsLockLease)
        values = dict(_root=root, _root_fd=root_fd, _lock_fd=lock_fd,
                      _root_identity=_identity(os.fstat(root_fd)),
                      _lock_identity=_identity(info), _pid=os.getpid(),
                      _mode=mode, _active=True, _seal=_LEASE_SEAL)
        for name, value in values.items():
            object.__setattr__(lease, name, value)
        lease._check()
        return lease
    except BaseException:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(root_fd)
        raise


@contextmanager
def claims_lock(lock_path: Path, *, mode: str, timeout: float):
    """Acquire the fixed root-relative lock; never unlink or steal its inode."""
    lease = _acquire_lock(lock_path, mode, timeout)
    try:
        yield lease
    finally:
        # A fork must never explicitly unlock the parent's inherited open-file
        # description. Closing the child's own descriptors is safe.
        object.__setattr__(lease, "_active", False)
        try:
            if os.getpid() == lease._pid:
                fcntl.flock(lease._lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lease._lock_fd)
            os.close(lease._root_fd)


def _lease_for(root, lease):
    root = _absolute(root)
    if type(lease) is not ClaimsLockLease:
        _fail("MALFORMED", "an opaque claims lease is required")
    lease._check()
    if lease._root != root:
        _fail("MALFORMED", "lease does not qualify this declared root")
    return root


class _Budget:
    def __init__(self, limits):
        self.deadline = time.monotonic() + SOURCE_TIMEOUT_SECONDS
        # Finite cumulative I/O, including repeated reads and orphan hashing.
        # This is an I/O allowance, not a larger retained-snapshot ceiling.
        self.remaining = 3 * limits.snapshot_bytes

    def check(self):
        if time.monotonic() >= self.deadline:
            _fail("LIMIT", "source deadline exhausted")

    def charge(self, count):
        self.check()
        if type(count) is not int or count < 0 or count > self.remaining:
            _fail("LIMIT", "source I/O budget exhausted")
        self.remaining -= count


def _inventory_bound(entries, limits):
    if len(entries) > limits.snapshot_members:
        _fail("LIMIT", "claims inventory member limit exceeded")
    if sum(item[1] for item in entries.values()) > limits.snapshot_bytes:
        _fail("LIMIT", "claims inventory bytes exceed snapshot profile")


def _read_local(root_fd, path, limits, budget, expected=None):
    _member_limit(path, limits)
    parent, name = _parent_fd(root_fd, path)
    try:
        before_open = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before_open.st_mode) or before_open.st_nlink != 1:
            _fail("MALFORMED", "member is not a singly linked regular file")
        _size(path, before_open.st_size, limits)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                     dir_fd=parent)
    finally:
        os.close(parent)
    try:
        before = os.fstat(fd)
        if _file_identity(before) != _file_identity(before_open):
            _fail("SOURCE_CHANGED", "member changed while opening")
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("MALFORMED", "member is not a singly linked regular file")
        _size(path, before.st_size, limits)
        if expected is not None and _file_identity(before) != expected:
            _fail("SOURCE_CHANGED", "local member identity changed")
        chunks = []
        count = 0
        while True:
            budget.check()
            chunk = os.read(fd, min(65536, before.st_size + 1 - count))
            if type(chunk) is not bytes:
                _fail("MALFORMED", "local provider must return exact bytes")
            if not chunk:
                break
            budget.charge(len(chunk))
            count += len(chunk)
            if count > before.st_size:
                _fail("SOURCE_CHANGED", "member grew during read")
            chunks.append(chunk)
        if count != before.st_size or _file_identity(os.fstat(fd)) != _file_identity(before):
            _fail("SOURCE_CHANGED", "member changed during read")
        return b"".join(chunks), _file_identity(before)
    finally:
        os.close(fd)


@_typed
def pin_local_root(root: Path, *, lease: ClaimsLockLease,
                   limits: ProtocolLimits) -> str:
    """Obtain an expected root digest only while holding the qualified lease."""
    limits = _limits(limits)
    _lease_for(root, lease)
    payload, _ = _read_local(lease._root_fd, ROOT_PATH, limits, _Budget(limits))
    decode_root(payload, limits=limits)
    lease._check()
    return sha256(payload).hexdigest()


@dataclass(frozen=True, init=False)
class LockedLocalSource:
    _root: Path
    _lease: ClaimsLockLease
    _limits: ProtocolLimits
    _entries: object
    _root_digest: str
    _budget: _Budget
    _source_id: str
    _directories: object

    @_typed
    def __init__(self, root: Path, *, lease: ClaimsLockLease,
                 expected_root_digest: str, limits: ProtocolLimits):
        root = _lease_for(root, lease)
        limits = _limits(limits)
        if type(expected_root_digest) is not str or not _HEX.fullmatch(expected_root_digest):
            _fail("MALFORMED", "expected root digest must be a SHA256 string")
        budget = _Budget(limits)
        entries = {}
        directories = {}
        paths = [BASE_PATH, ROOT_PATH]
        for prefix in (PART_PREFIX, PAGE_PREFIX):
            parent, name = _parent_fd(lease._root_fd, prefix.rstrip("/"))
            directory_fd = None
            try:
                try:
                    directory_fd = os.open(name, _directory_flags(), dir_fd=parent)
                except FileNotFoundError:
                    directories[prefix] = None
                    continue
                directories[prefix] = _file_identity(os.fstat(directory_fd))
                with os.scandir(directory_fd) as iterator:
                    for entry in iterator:
                        budget.check()
                        path = prefix + entry.name
                        _member_limit(path, limits)
                        paths.append(path)
                        if len(paths) > limits.snapshot_members:
                            _fail("LIMIT", "claims inventory member limit exceeded")
                if _file_identity(os.fstat(directory_fd)) != directories[prefix]:
                    _fail("SOURCE_CHANGED", "claims directory changed during inventory")
            finally:
                if directory_fd is not None:
                    os.close(directory_fd)
                os.close(parent)
        total_bytes = 0
        for path in sorted(paths):
            parent, name = _parent_fd(lease._root_fd, path)
            try:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            finally:
                os.close(parent)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                _fail("MALFORMED", "inventory member must be a regular file")
            _size(path, info.st_size, limits)
            entries[path] = (_file_identity(info), info.st_size)
            total_bytes += info.st_size
            if len(entries) > limits.snapshot_members or total_bytes > limits.snapshot_bytes:
                _fail("LIMIT", "claims inventory exceeds snapshot profile")
        payload, _ = _read_local(lease._root_fd, ROOT_PATH, limits, budget, entries[ROOT_PATH][0])
        if sha256(payload).hexdigest() != expected_root_digest:
            _fail("SOURCE_CHANGED", "root does not match supplied pin")
        lease._check()
        identity = sha256(repr((str(root), lease._root_identity,
                              lease._lock_identity, expected_root_digest)).encode()).hexdigest()
        for name, value in dict(_root=root, _lease=lease, _limits=limits,
                                _entries=MappingProxyType(entries),
                                _directories=MappingProxyType(directories),
                                _root_digest=expected_root_digest, _budget=budget,
                                _source_id="locked-local:" + identity).items():
            object.__setattr__(self, name, value)
        self._check()

    def _check(self):
        self._lease._check()
        self._budget.check()
        # Re-check fixed anchors at the final source-identity check as well as
        # when reading them: an old writer may have changed the base after its
        # bytes were captured, or swapped the root while later parts were read.
        for path in (BASE_PATH, ROOT_PATH):
            parent, name = _parent_fd(self._lease._root_fd, path)
            try:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            finally:
                os.close(parent)
            if _file_identity(info) != self._entries[path][0]:
                _fail("SOURCE_CHANGED", "fixed root or base changed after pinning")
        for prefix, expected in self._directories.items():
            parent, name = _parent_fd(self._lease._root_fd, prefix.rstrip("/"))
            directory_fd = None
            try:
                try:
                    directory_fd = os.open(name, _directory_flags(), dir_fd=parent)
                    actual = _file_identity(os.fstat(directory_fd))
                except FileNotFoundError:
                    actual = None
                if actual != expected:
                    _fail("SOURCE_CHANGED", "claims namespace inventory changed")
            finally:
                if directory_fd is not None:
                    os.close(directory_fd)
                os.close(parent)

    @property
    @_typed
    def snapshot_id(self):
        self._check()
        return self._source_id

    @_typed
    def read_member(self, path: str) -> bytes:
        self._check()
        _member_limit(path, self._limits)
        if path not in self._entries:
            _fail("MISSING", "member absent from pinned inventory")
        payload, _ = _read_local(self._lease._root_fd, path, self._limits,
                                 self._budget, self._entries[path][0])
        self._check()
        return payload

    @_typed
    def iter_members(self):
        refs = []
        for path in self._entries:
            payload = self.read_member(path)
            if type(payload) is not bytes:
                _fail("MALFORMED", "inventory provider must return exact bytes")
            refs.append(MemberRef(path, sha256(payload).hexdigest(), len(payload)))
        self._check()
        return tuple(refs)


class _GitRunner:
    def __init__(self, repo, limits):
        self.repo = repo
        self.budget = _Budget(limits)
        self.identity = _identity(repo.stat())

    def check(self):
        self.budget.check()
        fd = _open_directory(self.repo)
        try:
            if _identity(os.fstat(fd)) != self.identity:
                _fail("SOURCE_CHANGED", "repository directory changed")
        finally:
            os.close(fd)

    def run(self, arguments, *, maximum, input_bytes=b""):
        self.check()
        if type(input_bytes) is not bytes:
            _fail("MALFORMED", "Git input must be exact bytes")
        if type(maximum) is not int or maximum < 0:
            _fail("MALFORMED", "Git output allowance must be a nonnegative integer")
        if maximum > self.budget.remaining:
            _fail("LIMIT", "Git output allowance exceeds remaining I/O budget")
        # Do not inherit repository overrides, lazy-fetch credentials, replacement
        # refs, external configuration or permitted transports from the caller.
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0",
                   GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1",
                   GIT_ALLOW_PROTOCOL="", GIT_CONFIG_COUNT="0")
        command = ["git", "-C", str(self.repo), "-c", "protocol.allow=never", *arguments]
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, env=env)
        chunks = []
        count = sent = 0
        try:
            with selectors.DefaultSelector() as selector:
                os.set_blocking(proc.stdout.fileno(), False)
                selector.register(proc.stdout, selectors.EVENT_READ)
                if input_bytes:
                    os.set_blocking(proc.stdin.fileno(), False)
                    selector.register(proc.stdin, selectors.EVENT_WRITE)
                else:
                    proc.stdin.close()
                while selector.get_map():
                    self.budget.check()
                    for key, _ in selector.select(timeout=0.05):
                        if key.fileobj is proc.stdin:
                            try:
                                n = os.write(proc.stdin.fileno(), input_bytes[sent:sent + 65536])
                                sent += n
                            except BrokenPipeError:
                                sent = len(input_bytes)
                            if sent == len(input_bytes):
                                selector.unregister(proc.stdin)
                                proc.stdin.close()
                        else:
                            chunk = os.read(proc.stdout.fileno(), min(65536, maximum + 1 - count))
                            if not chunk:
                                selector.unregister(proc.stdout)
                            else:
                                count += len(chunk)
                                if count > maximum:
                                    _fail("LIMIT", "Git output budget exceeded")
                                self.budget.charge(len(chunk))
                                chunks.append(chunk)
            remaining = max(0.001, self.budget.deadline - time.monotonic())
            if proc.wait(timeout=remaining) != 0:
                _fail("MISSING", "required local Git object or inventory is unavailable")
        finally:
            if proc.poll() is None:
                # These built-in local reads launch no shell or permitted
                # transport. Terminate our exact child, never a process group.
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                proc.wait(timeout=1)
            if not proc.stdin.closed:
                proc.stdin.close()
            proc.stdout.close()
        self.check()
        return b"".join(chunks)


def _check_git_hash(kind, payload, oid):
    if type(payload) is not bytes:
        _fail("MALFORMED", "Git object payload must be exact bytes")
    hasher = sha1() if len(oid) == 40 else sha256()
    hasher.update(kind.encode("ascii") + b" " + str(len(payload)).encode("ascii") + b"\x00")
    hasher.update(payload)
    if hasher.hexdigest() != oid:
        _fail("HASH", "Git object bytes do not match their pinned object ID")


def _git_tree(runner, oid, maximum, entry_limit):
    """Decode only verified raw tree objects; ls-tree output alone is no pin."""
    size_raw = runner.run(["cat-file", "-s", oid], maximum=32)
    if type(size_raw) is not bytes or not re.fullmatch(rb"(?:0|[1-9][0-9]{0,19})\n", size_raw):
        _fail("MALFORMED", "invalid Git tree size")
    size = int(size_raw)
    if size > maximum:
        _fail("LIMIT", "Git tree metadata limit exceeded")
    raw = runner.run(["cat-file", "tree", oid], maximum=size)
    _check_git_hash("tree", raw, oid)
    if len(raw) != size:
        _fail("INCOMPLETE", "Git tree object size mismatch")
    width = len(oid) // 2
    offset = 0
    entries = {}
    while offset < len(raw):
        zero = raw.find(b"\x00", offset)
        if zero == -1 or zero + 1 + width > len(raw):
            _fail("MALFORMED", "truncated raw Git tree")
        header = raw[offset:zero]
        if b" " not in header:
            _fail("MALFORMED", "malformed raw Git tree entry")
        mode, name = header.split(b" ", 1)
        if (not re.fullmatch(rb"[0-7]{5,6}", mode) or not name
                or b"/" in name or name in (b".", b"..") or name in entries):
            _fail("MALFORMED", "unsafe or duplicate Git tree entry")
        child_oid = raw[zero + 1:zero + 1 + width].hex()
        entries[name] = (mode, child_oid)
        if len(entries) > entry_limit:
            _fail("LIMIT", "Git tree entry limit exceeded")
        offset = zero + 1 + width
    return entries


@dataclass(frozen=True, init=False)
class GitTreeSource:
    _repo: Path
    _tree_oid: str
    _limits: ProtocolLimits
    _entries: object
    _runner: _GitRunner
    _source_id: str

    @_typed
    def __init__(self, repo: Path, *, tree_oid: str, limits: ProtocolLimits):
        repo = _absolute(repo)
        limits = _limits(limits)
        if type(tree_oid) is not str or not _OID.fullmatch(tree_oid):
            _fail("MALFORMED", "an explicit full tree object ID is required")
        fd = _open_directory(repo)
        os.close(fd)
        runner = _GitRunner(repo, limits)
        tree_type = runner.run(["cat-file", "-t", tree_oid], maximum=32)
        if type(tree_type) is not bytes or tree_type != b"tree\n":
            _fail("MALFORMED", "object is not an exact Git tree")
        maximum = min(limits.snapshot_bytes, limits.snapshot_members * 256)
        current = _git_tree(runner, tree_oid, maximum, limits.snapshot_members)
        for component in (b"data", b"qledger"):
            if component not in current:
                _fail("MISSING", "claims namespace absent from pinned Git tree")
            mode, oid = current[component]
            if mode != b"40000":
                _fail("MALFORMED", "claims ancestor is not a Git directory")
            current = _git_tree(runner, oid, maximum, limits.snapshot_members)
        paths = {}

        def add(path, mode, oid):
            _member_limit(path, limits)
            if mode not in (b"100644", b"100755") or not _OID.fullmatch(oid):
                _fail("MALFORMED", "non-regular Git member")
            if path in paths:
                _fail("MALFORMED", "duplicate Git inventory path")
            paths[path] = oid
            if len(paths) > limits.snapshot_members:
                _fail("LIMIT", "Git member inventory limit exceeded")

        for path in (BASE_PATH, ROOT_PATH):
            name = path.rsplit("/", 1)[-1].encode("ascii")
            if name not in current:
                _fail("MISSING", "root/base missing from explicit Git tree")
            add(path, *current[name])
        for prefix in (PART_PREFIX, PAGE_PREFIX):
            name = prefix.rstrip("/").rsplit("/", 1)[-1].encode("ascii")
            if name not in current:
                continue
            mode, oid = current[name]
            if mode != b"40000":
                _fail("MALFORMED", "claims namespace is not a Git directory")
            for leaf, (leaf_mode, leaf_oid) in _git_tree(
                    runner, oid, maximum, limits.snapshot_members).items():
                add(prefix + leaf.decode("ascii"), leaf_mode, leaf_oid)
        if ROOT_PATH not in paths or BASE_PATH not in paths:
            _fail("MISSING", "root/base missing from explicit Git tree")
        oids = sorted(set(paths.values()))
        request = ("\n".join(oids) + "\n").encode("ascii")
        checked = runner.run(["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                             maximum=len(oids) * 128, input_bytes=request)
        if type(checked) is not bytes:
            _fail("MALFORMED", "Git metadata must be exact bytes")
        records = checked.splitlines()
        if len(records) != len(oids):
            _fail("INCOMPLETE", "incomplete Git object metadata")
        sizes = {}
        for expected_oid, record in zip(oids, records):
            fields = record.split(b" ")
            if len(fields) != 3 or fields[0] != expected_oid.encode() or fields[1] != b"blob":
                _fail("MISSING", "local Git blob missing or wrong type")
            if not re.fullmatch(rb"(?:0|[1-9][0-9]{0,19})", fields[2]):
                _fail("MALFORMED", "invalid Git object size")
            sizes[expected_oid] = int(fields[2])
        entries = {}
        for path, oid in sorted(paths.items()):
            _size(path, sizes[oid], limits)
            entries[path] = (oid, sizes[oid])
        _inventory_bound(entries, limits)
        identity = sha256(repr((str(repo), runner.identity, tree_oid)).encode()).hexdigest()
        for name, value in dict(_repo=repo, _tree_oid=tree_oid, _limits=limits,
                                _entries=MappingProxyType(entries), _runner=runner,
                                _source_id="git-tree:" + identity).items():
            object.__setattr__(self, name, value)

    @property
    @_typed
    def snapshot_id(self):
        self._runner.check()
        return self._source_id

    @_typed
    def read_member(self, path: str) -> bytes:
        _member_limit(path, self._limits)
        if path not in self._entries:
            _fail("MISSING", "member absent from pinned Git inventory")
        oid, size = self._entries[path]
        payload = self._runner.run(["cat-file", "blob", oid], maximum=size)
        if type(payload) is not bytes:
            _fail("MALFORMED", "Git member must be exact bytes")
        _check_git_hash("blob", payload, oid)
        if len(payload) != size:
            _fail("SOURCE_CHANGED", "Git blob size differs from pinned inventory")
        return payload

    @_typed
    def iter_members(self):
        refs = []
        for path in self._entries:
            payload = self.read_member(path)
            if type(payload) is not bytes:
                _fail("MALFORMED", "inventory provider must return exact bytes")
            refs.append(MemberRef(path, sha256(payload).hexdigest(), len(payload)))
        return tuple(refs)


@_typed
def verify_source_snapshot(source: PinnedSource, *, limits: ProtocolLimits) -> VerifiedSnapshot:
    """Verify explicit root and complete referenced history before success."""
    limits = _limits(limits)
    identity = source.snapshot_id
    if type(identity) is not str or not identity:
        _fail("MALFORMED", "source identity must be an exact nonempty string")
    payload = source.read_member(ROOT_PATH)
    if type(payload) is not bytes:
        _fail("MALFORMED", "root must be exact bytes")
    _size(ROOT_PATH, len(payload), limits)
    root = decode_root(payload, limits=limits)
    snapshot = verify_snapshot(source, root, limits=limits)
    final_identity = source.snapshot_id
    if type(final_identity) is not str or final_identity != identity:
        _fail("SOURCE_CHANGED", "source identity changed during verification")
    if snapshot.root_bytes != payload:
        _fail("SOURCE_CHANGED", "verified root differs from supplied bytes")
    return snapshot
