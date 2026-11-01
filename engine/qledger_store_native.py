"""Inactive native QLedger sessions and local materialization.

Nothing imports this module from the production claims call graph. A caller must
supply an explicit native location, operation/lane/transaction identity and the
accepted protocol profile. Identity tags identify an existing native operation;
they are not permission to select a format, transform claims, or recover a tail.

An exclusive C1 lease encloses the caller's read/dedupe/plan/materialize phase.
The fixed-root compare-and-replace is atomic for cooperating lease users; it
does not fence legacy binaries or writers that ignore that lease. This module
never obtains a Git index lock, publishes a commit, deletes history/orphans, or
runs a business/control-clock hook.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import errno
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Iterable, Mapping

from engine.qledger_store_protocol import (
    PAGE_PREFIX,
    PART_PREFIX,
    ROOT_PATH,
    MemberRef,
    ProtocolLimits,
    PublicationPlan,
    SnapshotIntegrityError,
    VerifiedSnapshot,
    plan_append,
    plan_replace_view,
    validate_plan,
    validate_publication,
)
from engine.qledger_store_sources import (
    LOCK_RELATIVE_PATH,
    ClaimsLockLease,
    LockedLocalSource,
    claims_lock,
    pin_local_root,
    verify_source_snapshot,
)


_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_PARENT = "data/qledger"
_ROOT_NAME = ROOT_PATH.rsplit("/", 1)[1]


@dataclass(frozen=True)
class NativeClaimsIntent:
    """Explicit stable native identity, never a storage activation/authority grant."""

    operation_id: str
    lane_id: str
    transaction_id: str

    def __post_init__(self) -> None:
        for name in ("operation_id", "lane_id", "transaction_id"):
            value = getattr(self, name)
            if type(value) is not str or not _ID.fullmatch(value):
                raise SnapshotIntegrityError("MALFORMED", f"invalid native {name}")


class StorageStatus(str, Enum):
    MATERIALIZED = "materialized"
    NOOP = "noop"
    ALREADY_APPLIED = "already_applied"
    FAILED_BEFORE_ROOT = "failed_before_root"
    ROOT_EFFECT_UNCERTAIN = "root_effect_uncertain"


@dataclass(frozen=True)
class ClaimsStorageOutcome:
    """Local effect receipt; neither a Git publication nor a clock receipt.

    Before-root failure can leave immutable members and owned temporaries.
    A replacement syscall that raises is conservatively uncertain, even if its
    visibility cannot be observed. An already-applied transaction is visible in
    verified history; its former durability/clock effect is not reconstructed.
    """

    intent: NativeClaimsIntent
    status: StorageStatus
    reason: str
    expected_root_digest: str
    candidate_root_digest: str | None
    observed_root_digest: str | None
    transaction_digest: str | None
    root_visibility: str
    durability_status: str
    clock_status: str
    written_members: tuple[str, ...] = ()
    reused_members: tuple[str, ...] = ()
    retained_temporaries: tuple[str, ...] = ()
    uncertain_temporaries: tuple[str, ...] = ()
    created_directories: tuple[str, ...] = ()
    local_candidate_verified: bool = False
    candidate_validation: str = "not_attempted"
    publication_status: str = "not_attempted"
    failure_code: str | None = None
    failure_message: str | None = None


class ClaimsStorageError(SnapshotIntegrityError):
    """Storage failure carrying an honest before/uncertain-root effect receipt."""

    def __init__(self, outcome: ClaimsStorageOutcome):
        self.outcome = outcome
        super().__init__(outcome.failure_code or "IO", outcome.failure_message or outcome.reason)


def _fail(code: str, message: str) -> None:
    raise SnapshotIntegrityError(code, message)


def _identity(intent: NativeClaimsIntent) -> None:
    if type(intent) is not NativeClaimsIntent:
        _fail("MALFORMED", "an explicit native operation/lane/transaction intent is required")
    # Frozen objects can still be maliciously manufactured; do not trust a tag
    # merely because it has the public dataclass type.
    intent.__post_init__()


def _hash(value: str, label: str) -> None:
    if type(value) is not str or not _DIGEST.fullmatch(value):
        _fail("MALFORMED", f"invalid {label}")


def _member_path(path: str) -> tuple[str, str]:
    """The protocol permits only flat content-addressed part/catalog names."""
    if type(path) is not str:
        _fail("MALFORMED", "immutable member path must be a string")
    if path.startswith(PART_PREFIX):
        name, suffix, directory = path[len(PART_PREFIX):], ".jsonl", "claims.parts"
    elif path.startswith(PAGE_PREFIX):
        name, suffix, directory = path[len(PAGE_PREFIX):], ".json", "claims.catalog"
    else:
        _fail("MALFORMED", "materialization may only install part/catalog members")
    digest = name[:-len(suffix)] if name.endswith(suffix) else ""
    if not _DIGEST.fullmatch(digest) or name != digest + suffix:
        _fail("MALFORMED", "unsafe or noncanonical immutable member path")
    return directory, name


def _open_dir(parent: int, name: str) -> int:
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        _fail("UNSAFE_PATH", "native member ancestor is not a directory")
    return fd


def _open_parent(root_fd: int) -> int:
    data_fd = _open_dir(root_fd, "data")
    try:
        return _open_dir(data_fd, "qledger")
    finally:
        os.close(data_fd)


def _same_dir(parent: int, name: str, fd: int) -> None:
    actual = os.stat(name, dir_fd=parent, follow_symlinks=False)
    held = os.fstat(fd)
    if not stat.S_ISDIR(actual.st_mode) or (actual.st_dev, actual.st_ino) != (
        held.st_dev, held.st_ino
    ):
        _fail("SOURCE_CHANGED", "native member directory changed during the lease")


def _read_file(parent: int, name: str, maximum: int) -> tuple[bytes, int]:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            _fail("UNSAFE_PATH", "native member is not a regular file")
        if info.st_size > maximum:
            _fail("LIMIT", "native member exceeds its prevalidated bound")
        chunks = bytearray()
        while len(chunks) <= maximum:
            block = os.read(fd, min(1024 * 1024, maximum + 1 - len(chunks)))
            if not block:
                break
            chunks.extend(block)
        after = os.fstat(fd)
        if len(chunks) > maximum:
            _fail("LIMIT", "native member grew beyond its bound")
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ) or len(chunks) != info.st_size:
            _fail("SOURCE_CHANGED", "native member changed while reading")
        return bytes(chunks), stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)


def _sync_file(fd: int) -> None:
    os.fsync(fd)
    # Darwin's explicit device-cache barrier supplements fsync for regular files.
    # A rejected barrier is a storage failure, never silently treated as durable.
    if sys.platform == "darwin":
        if not hasattr(fcntl, "F_FULLFSYNC"):
            _fail("DURABILITY", "Darwin full-file durability barrier is unavailable")
        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


def _sync_dir(fd: int) -> None:
    # Unsupported directory durability is an honest failure/uncertainty.
    os.fsync(fd)


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise OSError(errno.EIO, "short native materialization write")
        offset += written


def _new_temp(
    parent_fd: int, payload: bytes, retained: list[str], *,
    mode: int = 0o644, preserve_mode: bool = False,
) -> tuple[str, int]:
    # This name is not a protocol member and is never an authority/restart ledger.
    # No prior file is reused or removed. Failed owned temporaries remain visible
    # in the outcome for the native owner; there is no orphan cleanup pass.
    name = ".qledger-native-" + secrets.token_hex(16) + ".tmp"
    fd = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode, dir_fd=parent_fd,
    )
    retained.append(_PARENT + "/" + name)
    try:
        if preserve_mode:
            os.fchmod(fd, mode)
        _write_all(fd, payload)
        _sync_file(fd)
        return name, fd
    except BaseException:
        os.close(fd)
        raise


def _remove_owned_temp(parent_fd: int, name: str, fd: int, retained: list[str]) -> None:
    # Only this invocation's still-open, identity-checked temporary is removable.
    # Never reset/drop/reconcile any prior member or unknown temporary.
    current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    owned = os.fstat(fd)
    if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != (
        owned.st_dev, owned.st_ino
    ):
        _fail("SOURCE_CHANGED", "owned temporary identity changed")
    os.unlink(name, dir_fd=parent_fd)
    retained.remove(_PARENT + "/" + name)


class _CandidateSource:
    """Bounded public transport overlay; never inspects protocol private state."""

    def __init__(
        self, source: LockedLocalSource, members: Mapping[str, bytes],
        root_bytes: bytes, *, limits: ProtocolLimits,
    ):
        self._source = source
        self._overrides = dict(members)
        self._overrides[ROOT_PATH] = root_bytes
        self._source_id = source.snapshot_id
        self._snapshot_id = "native-candidate:" + sha256(
            self._source_id.encode("utf-8") + b"\0" + root_bytes
        ).hexdigest()
        inventory = {}
        for ref in source.iter_members():
            if ref.path in inventory:
                _fail("CONFLICT", "duplicate local member inventory path")
            inventory[ref.path] = ref
        for path, payload in self._overrides.items():
            if type(payload) is not bytes:
                _fail("MALFORMED", "candidate payloads must be immutable bytes")
            prior = inventory.get(path)
            if path != ROOT_PATH and prior is not None:
                actual = source.read_member(path)
                if actual != payload:
                    _fail("IMMUTABLE_CONFLICT", "existing immutable member differs from the plan")
            inventory[path] = MemberRef(path, sha256(payload).hexdigest(), len(payload))
        if len(inventory) > limits.snapshot_members:
            _fail("LIMIT", "complete candidate inventory exceeds its member budget")
        if sum(ref.size for ref in inventory.values()) > limits.snapshot_bytes:
            _fail("LIMIT", "complete candidate inventory exceeds its byte budget")
        self._inventory = tuple(inventory.values())

    @property
    def snapshot_id(self) -> str:
        if self._source.snapshot_id != self._source_id:
            _fail("SOURCE_CHANGED", "candidate backing source changed")
        return self._snapshot_id

    def read_member(self, path: str) -> bytes:
        self.snapshot_id
        if path in self._overrides:
            return self._overrides[path]
        return self._source.read_member(path)

    def iter_members(self) -> Iterable[MemberRef]:
        self.snapshot_id
        return self._inventory


def materialize_plan(
    plan: PublicationPlan, *, root: Path, lease: ClaimsLockLease,
    intent: NativeClaimsIntent, expected_root_digest: str, limits: ProtocolLimits,
) -> ClaimsStorageOutcome:
    """Validate all capacity, install immutable members, then replace the root.

    Returns only a materialized/no-op/already-applied outcome. Every ordinary
    failure raises ClaimsStorageError with a typed effect outcome. The caller
    owns the supplied exclusive lease and must keep it through read/dedupe/plan.
    No automatic retry, root rollback or prior orphan/history deletion occurs.
    """
    _identity(intent)
    written: list[str] = []
    reused: list[str] = []
    retained: list[str] = []
    created: list[str] = []
    root_fd = parent_fd = None
    directories: dict[str, int] = {}
    root_attempted = root_visible = root_durable = verified = False
    completed: ClaimsStorageOutcome | None = None
    pending_error: BaseException | None = None
    observed = candidate = transaction_digest = None
    replacing_temporary = None
    reason = "preflight"

    def outcome(status: StorageStatus, *, error: Exception | None = None) -> ClaimsStorageOutcome:
        uncertain = status is StorageStatus.ROOT_EFFECT_UNCERTAIN
        applied_retry = status is StorageStatus.ALREADY_APPLIED
        return ClaimsStorageOutcome(
            intent=intent, status=status, reason=reason,
            expected_root_digest=expected_root_digest,
            candidate_root_digest=candidate,
            observed_root_digest=observed,
            transaction_digest=transaction_digest,
            root_visibility="visible" if root_visible else ("unknown" if root_attempted else "unchanged"),
            durability_status="confirmed" if root_durable or status is StorageStatus.MATERIALIZED else (
                "uncertain" if uncertain or applied_retry else "not_attempted"
            ),
            clock_status="uncertain" if uncertain or applied_retry else "not_attempted",
            written_members=tuple(written), reused_members=tuple(reused),
            retained_temporaries=tuple(path for path in retained if path != replacing_temporary),
            uncertain_temporaries=(replacing_temporary,) if replacing_temporary else (),
            created_directories=tuple(created),
            local_candidate_verified=verified,
            failure_code=(error.code if isinstance(error, SnapshotIntegrityError) else "IO") if error else None,
            failure_message=str(error) if error else None,
        )

    try:
        _hash(expected_root_digest, "expected root digest")
        validate_plan(plan, limits=limits)
        if expected_root_digest != plan.expected_root_digest:
            _fail("CONFLICT", "materializer expected root differs from its plan")
        if plan.transaction is not None:
            if plan.transaction.transaction_id != intent.transaction_id:
                _fail("CONFLICT", "plan transaction differs from the native intent")
            transaction_digest = plan.transaction.digest
        candidate = plan.snapshot.receipt.root_digest
        _hash(candidate, "candidate root digest")
        lease.assert_valid(root, exclusive=True)
        observed = pin_local_root(root, lease=lease, limits=limits)
        if observed != expected_root_digest:
            _fail("CONFLICT", "fixed root changed before native materialization")
        source = LockedLocalSource(
            root, lease=lease, expected_root_digest=expected_root_digest, limits=limits,
        )
        candidate_source = _CandidateSource(source, plan.members, plan.root_bytes, limits=limits)
        validate_publication(candidate_source, plan.snapshot.root, (), limits=limits)
        verified = True
        # Check every planned pathname and existing ancestor before any file or
        # directory creation. The public protocol validation owns byte grammar.
        paths = {path: _member_path(path) for path in plan.members}
        root_fd = lease.open_root_fd(root, exclusive=True)
        parent_fd = _open_parent(root_fd)
        for directory in sorted({pair[0] for pair in paths.values()}):
            try:
                directories[directory] = _open_dir(parent_fd, directory)
            except FileNotFoundError:
                pass
        if plan.is_noop:
            reason = plan.reason
            if candidate != observed:
                _fail("CONFLICT", "a no-op cannot change the fixed root")
            completed = outcome(
                StorageStatus.ALREADY_APPLIED if plan.reason == "already_applied" else StorageStatus.NOOP
            )
            return completed

        reason = "installing_members"
        for directory in sorted({pair[0] for pair in paths.values()}):
            if directory not in directories:
                lease.assert_valid(root, exclusive=True)
                try:
                    os.mkdir(directory, 0o755, dir_fd=parent_fd)
                    created.append(_PARENT + "/" + directory)
                except FileExistsError:
                    pass
                directories[directory] = _open_dir(parent_fd, directory)
                _sync_dir(parent_fd)

        for path, payload in plan.members.items():
            lease.assert_valid(root, exclusive=True)
            directory, name = paths[path]
            fd = directories[directory]
            _same_dir(parent_fd, directory, fd)
            try:
                actual, _ = _read_file(fd, name, len(payload))
            except FileNotFoundError:
                actual = None
            if actual is not None:
                if actual != payload:
                    _fail("IMMUTABLE_CONFLICT", "immutable member changed after preflight")
                existing_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    if not stat.S_ISREG(os.fstat(existing_fd).st_mode):
                        _fail("UNSAFE_PATH", "immutable member changed type")
                    _sync_file(existing_fd)
                finally:
                    os.close(existing_fd)
                reused.append(path)
                _sync_dir(fd)
                continue
            temporary, temporary_fd = _new_temp(parent_fd, payload, retained)
            try:
                try:
                    os.link(
                        temporary, name, src_dir_fd=parent_fd, dst_dir_fd=fd,
                        follow_symlinks=False,
                    )
                    written.append(path)
                except FileExistsError:
                    actual, _ = _read_file(fd, name, len(payload))
                    if actual != payload:
                        _fail("IMMUTABLE_CONFLICT", "immutable path appeared with different bytes")
                    existing_fd = os.open(
                        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd,
                    )
                    try:
                        if not stat.S_ISREG(os.fstat(existing_fd).st_mode):
                            _fail("UNSAFE_PATH", "immutable collision changed type")
                        _sync_file(existing_fd)
                    finally:
                        os.close(existing_fd)
                    reused.append(path)
                _sync_dir(fd)
                _remove_owned_temp(parent_fd, temporary, temporary_fd, retained)
                # The installed inode must also durably lose its temporary
                # alias before a root can reference C1's single-link member.
                _sync_file(temporary_fd)
                _sync_dir(parent_fd)
            finally:
                os.close(temporary_fd)

        # Verify the actual installed namespace, overriding only the not-yet-
        # visible root. Plan payloads cannot mask a missing/changed installation.
        reason = "verifying_installed_members"
        lease.assert_valid(root, exclusive=True)
        installed = LockedLocalSource(
            root, lease=lease, expected_root_digest=expected_root_digest, limits=limits,
        )
        installed_candidate = _CandidateSource(installed, {}, plan.root_bytes, limits=limits)
        validate_publication(installed_candidate, plan.snapshot.root, (), limits=limits)
        for directory, fd in directories.items():
            _same_dir(parent_fd, directory, fd)
            _sync_dir(fd)
        _sync_dir(parent_fd)

        reason = "replacing_root"
        current, mode = _read_file(parent_fd, _ROOT_NAME, limits.root_bytes)
        if sha256(current).hexdigest() != expected_root_digest:
            _fail("CONFLICT", "fixed root changed before compare-and-replace")
        temporary, temporary_fd = _new_temp(
            parent_fd, plan.root_bytes, retained, mode=mode, preserve_mode=True,
        )
        try:
            lease.assert_valid(root, exclusive=True)
            for directory, fd in directories.items():
                _same_dir(parent_fd, directory, fd)
            current, _ = _read_file(parent_fd, _ROOT_NAME, limits.root_bytes)
            if sha256(current).hexdigest() != expected_root_digest:
                _fail("CONFLICT", "fixed root changed at compare-and-replace")
            # An exception from replacement can be ambiguous. Never label it
            # pre-effect or retry/restore an earlier root behind the owner's back.
            root_attempted = True
            replacing_temporary = _PARENT + "/" + temporary
            os.replace(temporary, _ROOT_NAME, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            root_visible = True
            observed = candidate
            retained.remove(_PARENT + "/" + temporary)
            replacing_temporary = None
            _sync_dir(parent_fd)
            lease.assert_valid(root, exclusive=True)
            current, _ = _read_file(parent_fd, _ROOT_NAME, limits.root_bytes)
            if sha256(current).hexdigest() != candidate:
                _fail("SOURCE_CHANGED", "materialized root changed before acknowledgement")
            root_durable = True
        finally:
            os.close(temporary_fd)
        reason = "materialized"
        completed = outcome(StorageStatus.MATERIALIZED)
        return completed
    except Exception as exc:
        status = StorageStatus.ROOT_EFFECT_UNCERTAIN if root_attempted else StorageStatus.FAILED_BEFORE_ROOT
        pending_error = ClaimsStorageError(outcome(status, error=exc))
        raise pending_error from exc
    except BaseException as exc:
        pending_error = exc
        raise
    finally:
        # A close error can mean its acknowledgement was lost. Attempt every
        # remaining owned descriptor once; never retry or guess whether an fd
        # number now belongs to an unrelated allocation.
        cleanup_errors: list[tuple[int, Exception]] = []
        for fd in (*directories.values(), parent_fd, root_fd):
            if fd is None:
                continue
            try:
                os.close(fd)
            except Exception as cleanup_error:
                cleanup_errors.append((fd, cleanup_error))
        if cleanup_errors:
            notes = [
                f"owned descriptor {fd} close failed (not retried): "
                f"{type(error).__name__}: {error}"
                for fd, error in cleanup_errors
            ]
            if pending_error is not None:
                # Keep the original error, effect receipt and cause; cleanup
                # diagnostics supplement them instead of replacing them.
                for note in notes:
                    pending_error.add_note(note)
            else:
                assert completed is not None
                first_error = cleanup_errors[0][1]
                cleanup_outcome = replace(
                    completed,
                    status=(
                        StorageStatus.ROOT_EFFECT_UNCERTAIN if root_attempted
                        else StorageStatus.FAILED_BEFORE_ROOT
                    ),
                    reason="descriptor_cleanup_failed",
                    failure_code=(
                        first_error.code if isinstance(first_error, SnapshotIntegrityError) else "IO"
                    ),
                    failure_message=str(first_error),
                )
                # replace() retains confirmed visibility/durability and known
                # clock status even when releasing descriptors is uncertain.
                cleanup_failure = ClaimsStorageError(cleanup_outcome)
                for note in notes:
                    cleanup_failure.add_note(note)
                raise cleanup_failure from first_error


class NativeClaimsSession:
    """One explicit exclusive read/dedupe/plan/materialize lifetime.

    The caller may inspect read_snapshot() and perform its unchanged dedupe or
    domain transformation while this context remains open. Serialized bytes are
    passed unchanged to the existing pure planners. Failed materialization stops
    this session; a retry requires a new explicit session with the same intent.
    """

    def __init__(
        self, location: Path, *, intent: NativeClaimsIntent, limits: ProtocolLimits,
        lock_timeout: float = 30.0,
    ):
        _identity(intent)
        if not isinstance(location, Path) or not location.is_absolute() or ".." in location.parts:
            _fail("UNSAFE_PATH", "native location requires an explicit absolute repository root")
        self.location = location
        self.intent = intent
        self.limits = limits
        self.lock_timeout = lock_timeout
        self._context = None
        self._lease = None
        self._snapshot = None
        self._entered = False
        self._stopped = False
        self._last_outcome: ClaimsStorageOutcome | None = None

    @property
    def last_outcome(self) -> ClaimsStorageOutcome | None:
        return self._last_outcome

    def __enter__(self) -> NativeClaimsSession:
        if self._entered:
            _fail("SESSION", "a native session cannot be entered twice")
        self._entered = True
        self._context = claims_lock(
            self.location / LOCK_RELATIVE_PATH, mode="exclusive", timeout=self.lock_timeout,
        )
        self._lease = self._context.__enter__()
        try:
            self._snapshot = self._capture()
            return self
        except BaseException:
            self._context.__exit__(*sys.exc_info())
            self._lease = None
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._stopped = True
        try:
            if self._context is not None and self._lease is not None:
                self._context.__exit__(exc_type, exc, traceback)
        except Exception as release_error:
            if self._last_outcome is None:
                raise
            previous = self._last_outcome
            status = (
                StorageStatus.ROOT_EFFECT_UNCERTAIN
                if previous.status in {StorageStatus.MATERIALIZED, StorageStatus.ROOT_EFFECT_UNCERTAIN}
                else previous.status
            )
            self._last_outcome = replace(
                previous, status=status, reason="lease_release_failed",
                failure_code=(release_error.code if isinstance(release_error, SnapshotIntegrityError) else "IO"),
                failure_message=str(release_error),
            )
            raise ClaimsStorageError(self._last_outcome) from release_error
        finally:
            self._lease = None

    def _require_open(self) -> ClaimsLockLease:
        if self._lease is None or self._stopped:
            _fail("SESSION", "native session is closed or stopped")
        self._lease.assert_valid(self.location, exclusive=True)
        return self._lease

    def _capture(self) -> VerifiedSnapshot:
        lease = self._require_open()
        digest = pin_local_root(self.location, lease=lease, limits=self.limits)
        source = LockedLocalSource(
            self.location, lease=lease, expected_root_digest=digest, limits=self.limits,
        )
        return verify_source_snapshot(source, limits=self.limits)

    def read_snapshot(self) -> VerifiedSnapshot:
        self._require_open()
        assert self._snapshot is not None
        return self._snapshot

    def _apply(self, plan: PublicationPlan) -> ClaimsStorageOutcome:
        lease = self._require_open()
        try:
            result = materialize_plan(
                plan, root=self.location, lease=lease, intent=self.intent,
                expected_root_digest=plan.expected_root_digest, limits=self.limits,
            )
        except BaseException as exc:
            if isinstance(exc, ClaimsStorageError):
                self._last_outcome = exc.outcome
            self._stopped = True
            raise
        self._last_outcome = result
        self._snapshot = plan.snapshot
        return result

    def _planning_error(
        self, snapshot: VerifiedSnapshot, error: Exception,
    ) -> ClaimsStorageError:
        # The session and cached snapshot are already bound. Pure planning may
        # consume caller serialization iterators, but cannot have storage effects.
        digest = snapshot.receipt.root_digest
        self._last_outcome = ClaimsStorageOutcome(
            intent=self.intent, status=StorageStatus.FAILED_BEFORE_ROOT,
            reason="planning_failed", expected_root_digest=digest,
            candidate_root_digest=None, observed_root_digest=digest,
            transaction_digest=None, root_visibility="unchanged",
            durability_status="not_attempted", clock_status="not_attempted",
            failure_code=(error.code if isinstance(error, SnapshotIntegrityError) else "IO"),
            failure_message=str(error),
        )
        self._stopped = True
        return ClaimsStorageError(self._last_outcome)

    def append_serialized_rows(self, rows: Iterable[bytes]) -> ClaimsStorageOutcome:
        self._require_open()
        snapshot = self.read_snapshot()
        try:
            plan = plan_append(
                snapshot, transaction_id=self.intent.transaction_id,
                serialized_rows=rows, limits=self.limits,
            )
        except Exception as exc:
            raise self._planning_error(snapshot, exc) from exc
        return self._apply(plan)

    def replace_serialized_rows(
        self, rows: Iterable[bytes], *, expected_view_digest: str,
    ) -> ClaimsStorageOutcome:
        self._require_open()
        snapshot = self.read_snapshot()
        try:
            plan = plan_replace_view(
                snapshot, transaction_id=self.intent.transaction_id,
                expected_view_digest=expected_view_digest,
                replacement_rows=rows, limits=self.limits,
            )
        except Exception as exc:
            raise self._planning_error(snapshot, exc) from exc
        return self._apply(plan)
