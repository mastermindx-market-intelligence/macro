"""Claims-owner bindings with an unconditional legacy production selection.

Legacy transports preserve their original parser and I/O contracts. The native
binding is available through an explicit context-local owner scope; default
selection remains legacy, with no discovery, environment switch or enrollment.
A native ROOT refuses unbound legacy I/O rather than reading an empty base.
"""

from __future__ import annotations

import io
import json
import os
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, TextIO


@dataclass(frozen=True)
class LegacyClaimsBinding:
    claims_path: Path


def _production_claims_binding(explicit_claims_path: Path) -> LegacyClaimsBinding:
    """Production always uses the incumbent explicit legacy path."""
    return LegacyClaimsBinding(explicit_claims_path)


def _require_legacy_namespace(path):
    """Refuse native ROOT at legacy I/O, never auto-select another format.

    This check is not a checkout/old-descriptor synchronization fence. Actual
    consumers must be bound before converted files become visible.
    """
    from engine.qledger_store_protocol import ROOT_PATH, SnapshotIntegrityError
    key = _claims_key(path)
    if key is None or key.parts[-3:] != ("data", "qledger", "claims.jsonl"):
        return
    try:
        os.lstat(key.parents[2] / ROOT_PATH)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise SnapshotIntegrityError("SOURCE_UNPROVEN", "legacy namespace cannot be qualified") from exc
    raise SnapshotIntegrityError("NATIVE_BINDING_REQUIRED", "native ROOT requires an explicit owner or immutable read binding")


_SYNTHETIC_BINDINGS: ContextVar[tuple[tuple[Path, Any], ...]] = ContextVar(
    "qledger_synthetic_bindings", default=(),
)
_OWNER_BINDINGS: ContextVar[tuple[tuple[Path, Any], ...]] = ContextVar(
    "qledger_explicit_owner_bindings", default=(),
)
_READ_SCOPES: ContextVar[tuple[tuple[Path, Any, Any], ...]] = ContextVar(
    "qledger_claims_read_scopes", default=(),
)


def _claims_key(path: Path) -> Path | None:
    # Lexical only: no resolve, stat, discovery or filesystem read. Preserve
    # legacy duck-typed transport specimens that are not filesystem paths.
    try:
        return Path(path).absolute()
    except TypeError:
        return None


def _selected_claims_binding(path: Path):
    key = _claims_key(path)
    for candidate, binding in reversed(_OWNER_BINDINGS.get()):
        if candidate == key:
            return binding
    overrides = _SYNTHETIC_BINDINGS.get()
    if overrides:
        key = _claims_key(path)
        for candidate, binding in reversed(overrides):
            if candidate == key:
                return binding
    return _production_claims_binding(path)


def _scoped_entry(path: Path):
    scopes = _READ_SCOPES.get()
    if scopes:
        key = _claims_key(path)
        for entry in reversed(scopes):
            if entry[0] == key:
                return entry
    return None


def _read_claims_binding(path: Path):
    entry = _scoped_entry(path)
    return entry[1] if entry is not None else _selected_claims_binding(path)


def uses_native_claims(path: Path) -> bool:
    """Inspect explicit binding selection only; perform no file/source read."""
    return not isinstance(_read_claims_binding(path), LegacyClaimsBinding)


@contextmanager
def _synthetic_claims_binding(explicit_claims_path: Path, binding) -> Iterator[Any]:
    """Private task-local fixture injection, never persistent configuration."""
    key = _claims_key(explicit_claims_path)
    if key is None or _claims_key(binding.claims_path) != key:
        raise ValueError("synthetic claims binding requires its exact explicit path")
    token = _SYNTHETIC_BINDINGS.set(_SYNTHETIC_BINDINGS.get() + ((key, binding),))
    try:
        yield binding
    finally:
        _SYNTHETIC_BINDINGS.reset(token)


@dataclass(frozen=True, init=False)
class NativeGitClaimsBinding:
    """Complete immutable Git generation; read-only, never an apply grant."""

    claims_path: Path
    repo_root: Path
    commit_oid: str
    tree_oid: str
    limits: Any
    _snapshot: Any

    def __init__(self, repo_root, *, commit_oid, expected_root_digest, limits):
        from scripts.ci import qledger_publication as publication
        from engine.qledger_store_sources import GitTreeSource, verify_source_snapshot
        publication._profile(limits)
        publication._repo(repo_root)
        publication._oid(commit_oid)
        if type(expected_root_digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", expected_root_digest):
            raise ValueError("explicit immutable claims root digest required")
        tree = publication._commit_tree(repo_root, commit_oid, limits=limits)
        snapshot = verify_source_snapshot(GitTreeSource(repo_root, tree_oid=tree, limits=limits), limits=limits)
        if snapshot.receipt.root_digest != expected_root_digest:
            from engine.qledger_store_protocol import SnapshotIntegrityError
            raise SnapshotIntegrityError("CONFLICT", "immutable Git generation differs from explicit root")
        for name, value in dict(claims_path=repo_root / "data/qledger/claims.jsonl", repo_root=repo_root,
            commit_oid=commit_oid, tree_oid=tree, limits=limits, _snapshot=snapshot).items():
            object.__setattr__(self, name, value)

    def read_snapshot(self):
        return self._snapshot

    @contextmanager
    def mutation(self, *, native_intent=None):
        from engine.qledger_store_protocol import SnapshotIntegrityError
        raise SnapshotIntegrityError("READ_ONLY", "immutable Git read binding cannot authorize native mutation")
        yield  # contextmanager protocol; no mutation is ever yielded


class ClaimsBindingScope:
    """Explicit caller selection, not runtime enrollment or a host admission.

    Only a verified immutable Git reader or the retained-original owner may be
    selected. No synthetic hook, environment discovery or mutable global pointer.
    """

    def __init__(self, binding):
        self.binding, self._token = binding, None

    def __enter__(self):
        from engine.qledger_original_result import OriginalResultClaimsBinding
        from engine.qledger_store_protocol import SnapshotIntegrityError
        binding = self.binding
        if self._token is not None or type(binding) not in (OriginalResultClaimsBinding, NativeGitClaimsBinding):
            raise SnapshotIntegrityError("CONFLICT", "an exact explicit claims owner/read binding is required")
        key = _claims_key(binding.claims_path)
        if key is None or key != binding.repo_root / "data/qledger/claims.jsonl" or not key.is_absolute():
            raise SnapshotIntegrityError("CONFLICT", "owner binding differs from exact claims root")
        for path, previous in _OWNER_BINDINGS.get():
            if path == key and previous is not binding:
                raise SnapshotIntegrityError("CONFLICT", "another explicit binding owns this claims root")
        scoped = _scoped_entry(key)
        if scoped is not None and scoped[1] is not binding:
            raise SnapshotIntegrityError("CONFLICT", "active read scope belongs to another claims generation")
        self._token = _OWNER_BINDINGS.set(_OWNER_BINDINGS.get() + ((key, binding),))
        return binding

    def __exit__(self, exc_type, exc, traceback):
        token, self._token = self._token, None
        if token is not None:
            _OWNER_BINDINGS.reset(token)
        return False


class ClaimsReadScope:
    """Retain one complete snapshot per explicit root for a composed read.

    Same-root nested scopes reuse the captured binding and snapshot. Another
    root gets a distinct entry. Immutable ContextVar state is restored on all
    exits; there is no process-wide snapshot cache or held read lease.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.claims_path = self.root / "data" / "qledger" / "claims.jsonl"
        self._token = None
        self.snapshot = None

    def __enter__(self):
        if self._token is not None:
            raise RuntimeError("ClaimsReadScope is already active")
        entry = _scoped_entry(self.claims_path)
        if entry is None:
            binding = _selected_claims_binding(self.claims_path)
            snapshot = None if isinstance(binding, LegacyClaimsBinding) else _read_verified_snapshot(binding)
            entry = (_claims_key(self.claims_path), binding, snapshot)
        self.snapshot = entry[2]
        self._token = _READ_SCOPES.set(_READ_SCOPES.get() + (entry,))
        return self

    def __exit__(self, exc_type, exc, traceback):
        token, self._token = self._token, None
        if token is not None:
            _READ_SCOPES.reset(token)
        self.snapshot = None
        return False


def _read_verified_snapshot(binding):
    from engine.qledger_store_protocol import open_logical_bytes

    snapshot = binding.read_snapshot()
    # Public provenance check before a scope can retain a value. Verification
    # and immutable retention themselves belong to the explicit source/session.
    with open_logical_bytes(snapshot):
        pass
    return snapshot


def _retained_snapshot(path: Path, binding):
    entry = _scoped_entry(path)
    return entry[2] if entry is not None else _read_verified_snapshot(binding)


@contextmanager
def _snapshot_text(snapshot, *, encoding: str | None = "utf-8") -> Iterator[TextIO]:
    from engine.qledger_store_protocol import open_logical_bytes

    with io.TextIOWrapper(open_logical_bytes(snapshot), encoding=encoding) as handle:
        yield handle


def _snapshot_lines(snapshot, *, encoding: str | None = "utf-8") -> list[str]:
    with _snapshot_text(snapshot, encoding=encoding) as handle:
        return handle.read().splitlines()


def read_raw_lines(
    path: Path, *, missing_ok: bool = True, encoding: str | None = "utf-8"
) -> list[str]:
    """Eager text transport; a native snapshot is fully verified before values."""
    binding = _read_claims_binding(path)
    if isinstance(binding, LegacyClaimsBinding):
        _require_legacy_namespace(path)
        if missing_ok and not path.exists():
            return []
        return path.read_text(encoding=encoding).splitlines()
    return _snapshot_lines(_retained_snapshot(path, binding), encoding=encoding)


@contextmanager
def open_raw_lines(
    path: Path, *, encoding: str | None = "utf-8"
) -> Iterator[TextIO]:
    """Preserve physical lines, incremental decoding and stream closure."""
    binding = _read_claims_binding(path)
    if isinstance(binding, LegacyClaimsBinding):
        _require_legacy_namespace(path)
        with path.open(encoding=encoding) as handle:
            yield handle
    else:
        snapshot = _retained_snapshot(path, binding)
        with _snapshot_text(snapshot, encoding=encoding) as handle:
            yield handle


def _legacy_rows_from_lines(lines: list[str]) -> list[Any]:
    rows: list[Any] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001 — match the existing legacy reader
            continue
    return rows


def read_legacy_rows(path: Path) -> list[Any]:
    """Keep scalars, nulls, unknown fields and every parsed duplicate occurrence."""
    return _legacy_rows_from_lines(read_raw_lines(path))


def read_tracked_claims_text(
    root: Path,
    relative_path: Path,
    *,
    legacy_reader: Callable[[Path, Path], tuple[str | None, str]],
) -> tuple[str | None, str]:
    """Keep the incumbent callback/cache on legacy; never use it for native."""
    try:
        path = Path(root) / relative_path
    except TypeError:
        return legacy_reader(root, relative_path)
    binding = _read_claims_binding(path)
    if isinstance(binding, LegacyClaimsBinding):
        _require_legacy_namespace(path)
        return legacy_reader(root, relative_path)
    snapshot = _retained_snapshot(path, binding)
    with _snapshot_text(snapshot) as handle:
        value = handle.read()
    return value, "qledger-native:" + snapshot.receipt.source_id + ":" + snapshot.receipt.root_digest


@dataclass(frozen=True)
class NativeClaimsWrite:
    """Caller-retained original inputs, not a durable/restart or custody receipt."""

    intent: Any
    plan: Any
    claims_path: Path


@dataclass(frozen=True)
class NativeClaimsAttempt:
    """Task-local facts only. A missing outcome is an unsettled local attempt."""

    write: NativeClaimsWrite
    outcome: Any = None


class _NativeClaimsBinding:
    """Inactive explicit owner binding; callers supply every causal write intent.

    Attempts are bounded task-local handoff inputs, NOT a journal, durability
    promise, restart store, publication receipt or runtime admission. The owner
    must retain original inputs/outcomes on its existing durable result path.
    """

    def __init__(
        self, explicit_claims_path: Path, *, operation_id: str, lane_id: str, limits,
        lock_timeout: float = 30, session_factory=None,
    ):
        path = Path(explicit_claims_path)
        if not path.is_absolute() or path.parts[-3:] != ("data", "qledger", "claims.jsonl"):
            raise ValueError("native binding requires an absolute canonical claims path")
        for tag in (operation_id, lane_id):
            if type(tag) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", tag):
                raise ValueError("native binding requires explicit owner identity")
        self.claims_path = path
        self.repo_root = path.parent.parent.parent
        self.operation_id, self.lane_id = operation_id, lane_id
        self.limits = limits
        self.lock_timeout = lock_timeout
        self._session_factory = session_factory
        self._last_outcome: ContextVar[Any] = ContextVar("qledger_native_last_outcome", default=None)
        self._attempts: ContextVar[tuple[NativeClaimsAttempt, ...]] = ContextVar(
            "qledger_native_attempts", default=(),
        )
        self._unresolved: ContextVar[Any] = ContextVar("qledger_native_unresolved", default=None)

    @property
    def last_outcome(self):
        return self._last_outcome.get()

    @property
    def attempts(self) -> tuple[NativeClaimsAttempt, ...]:
        return self._attempts.get()

    def _new_session(self, intent=None):
        factory = self._session_factory
        if factory is None:
            from engine.qledger_store_native import NativeClaimsSession

            factory = NativeClaimsSession
        return factory(
            self.repo_root, intent=intent, limits=self.limits,
            lock_timeout=self.lock_timeout,
        )

    def _check_intent(self, intent):
        from engine.qledger_store_native import NativeClaimsIntent
        from engine.qledger_store_protocol import SnapshotIntegrityError

        if type(intent) is not NativeClaimsIntent:
            raise SnapshotIntegrityError("MALFORMED", "an explicit per-write native intent is required")
        intent.__post_init__()
        if (intent.operation_id, intent.lane_id) != (self.operation_id, self.lane_id):
            raise SnapshotIntegrityError("CONFLICT", "write intent differs from explicit binding owner")

    @staticmethod
    def _same_original_write(left, right):
        # Callers validate retained plans before this comparison. Artifact
        # readback truthfully has a new source receipt; match exact original
        # bytes/transactions, never assert that it is the old live source.
        return (
            type(left) is NativeClaimsWrite and type(right) is NativeClaimsWrite
            and left.intent == right.intent and left.claims_path == right.claims_path
            and left.plan._before.root_bytes == right.plan._before.root_bytes
            and left.plan._before._members == right.plan._before._members
            and left.plan.snapshot.root_bytes == right.plan.snapshot.root_bytes
            and left.plan.snapshot._members == right.plan.snapshot._members
            and left.plan.transaction == right.plan.transaction
        )

    def _admit(self, intent, *, original=None):
        from engine.qledger_store_protocol import SnapshotIntegrityError

        self._check_intent(intent)
        unresolved = self._unresolved.get()
        if unresolved is not None and not self._same_original_write(original, unresolved):
            raise SnapshotIntegrityError("CONFLICT", "original native write remains unsettled; reconcile its exact inputs")
        if original is None and len(self.attempts) >= self.limits.history_operations:
            raise SnapshotIntegrityError("LIMIT", "task-local native attempt budget")
        if original is None and any(
            a.write.intent.transaction_id == intent.transaction_id for a in self.attempts
        ):
            raise SnapshotIntegrityError("CONFLICT", "reused write intent requires original-input reconciliation")

    def _begin(self, write):
        from engine.qledger_store_protocol import SnapshotIntegrityError

        # Conservative retained-byte admission, not a peak-RAM estimate. Never
        # discard earlier original inputs to make a later write fit. Repeated
        # reconciliation can retain the same plan, so charge that object once.
        seen = set()
        charge = 0
        for attempt in self.attempts + (NativeClaimsAttempt(write),):
            item = attempt.write
            if id(item.plan) not in seen:
                seen.add(id(item.plan))
                charge += item.plan._before.receipt.retained_bytes + item.plan.snapshot.receipt.retained_bytes
        if charge > self.limits.snapshot_bytes:
            raise SnapshotIntegrityError("LIMIT", "task-local original-input retention budget")
        self._attempts.set(self.attempts + (NativeClaimsAttempt(write),))
        # Set BEFORE entering the effectful apply. An unexpected response loss
        # must not become permission for a fresh write through this binding.
        self._unresolved.set(write)
        self._last_outcome.set(None)

    def _record(self, write, outcome):
        attempts = self.attempts
        if not attempts or attempts[-1].write is not write:
            raise RuntimeError("native outcome has no current original attempt")
        self._attempts.set(attempts[:-1] + (NativeClaimsAttempt(write, outcome),))
        self._last_outcome.set(outcome)
        self._unresolved.set(write if outcome.status == "root_effect_uncertain" else None)
        return outcome

    def _apply_original_write(self, session, write):
        # Inactive synthetic binding. An actual owner uses the explicit
        # OriginalResultClaimsBinding retention boundary, never this fixture
        # path as production enrollment.
        return session.apply_prepared(write.plan)

    def read_snapshot(self):
        with self._new_session() as session:
            return session.read_snapshot()

    @contextmanager
    def mutation(self, *, native_intent=None):
        from engine.qledger_store_native import ClaimsStorageError

        writer = None
        try:
            with self._new_session(native_intent) as session:
                writer = _NativeClaimsWriter(self, session, native_intent)
                yield writer
        except ClaimsStorageError as exc:
            outcome = exc.outcome
            if writer is not None and writer.clock_attempted:
                outcome = replace(outcome, clock_status="uncertain")
            if writer is not None and writer.write is not None:
                self._record(writer.write, outcome)
            else:
                self._last_outcome.set(outcome)
            if outcome is not exc.outcome:
                raise ClaimsStorageError(outcome) from exc
            raise

    def reconcile_original_write(self, write: NativeClaimsWrite):
        """Reconcile retained exact inputs; never call registrar preparation/clocks.

        Restored inputs need the owner's real durable retention and custody.
        Supplying this task-local object alone does not establish either fact.
        """
        from engine.qledger_store_native import ClaimsStorageError
        from engine.qledger_store_protocol import SnapshotIntegrityError, validate_plan

        if type(write) is not NativeClaimsWrite:
            raise SnapshotIntegrityError("MALFORMED", "an original native write is required")
        if not isinstance(write.claims_path, Path) or write.claims_path != self.claims_path:
            raise SnapshotIntegrityError("CONFLICT", "original write belongs to another explicit claims path")
        self._check_intent(write.intent)
        validate_plan(write.plan, limits=self.limits)
        self._admit(write.intent, original=write)
        if write.plan.transaction is None or write.plan.transaction.transaction_id != write.intent.transaction_id:
            raise SnapshotIntegrityError("CONFLICT", "original plan differs from native intent")
        begun = inspection_only = False

        def settle_inspection(outcome):
            # One latest observation, not a new attempt or durable recovery
            # receipt. Keep the original uncertain attempt unchanged.
            self._last_outcome.set(outcome)
            if outcome.status == "already_applied":
                self._unresolved.set(None)
            return outcome

        try:
            with self._new_session(write.intent) as session:
                plan = session.prepare_reconciliation(write.plan)
                if len(self.attempts) >= self.limits.history_operations:
                    if not plan.is_noop or plan.reason != "already_applied":
                        raise SnapshotIntegrityError("LIMIT", "effectful original reconciliation exceeds task-local attempt budget")
                    # Proven no-op through the incumbent native checks. Never
                    # reset the binding or discard original inputs at its cap.
                    inspection_only = True
                    return settle_inspection(session.apply_prepared(plan))
                self._begin(write)
                begun = True
                return self._record(write, session.apply_prepared(plan))
        except ClaimsStorageError as exc:
            if begun:
                self._record(write, exc.outcome)
            elif inspection_only:
                settle_inspection(exc.outcome)
            raise


class _NativeClaimsWriter:
    def __init__(self, binding: _NativeClaimsBinding, session, intent):
        self.binding = binding
        self.session = session
        self.intent = intent
        self.write = None
        self.snapshot = session.read_snapshot()
        self.outcome = None
        self.clock_attempted = False

    def read_rows(self) -> list[Any]:
        return _legacy_rows_from_lines(_snapshot_lines(self.snapshot))

    def _record(self, outcome):
        self.outcome = outcome
        return self.binding._record(self.write, outcome)

    def _execute(self, plan):
        from engine.qledger_store_protocol import SnapshotIntegrityError

        if plan.is_noop:
            raise SnapshotIntegrityError("CONFLICT", "existing transaction requires original-input reconciliation")
        self.write = NativeClaimsWrite(self.intent, plan, self.binding.claims_path)
        self.binding._begin(self.write)
        return self._record(self.binding._apply_original_write(self.session, self.write))

    def append_serialized_rows(self, rows):
        self.binding._admit(self.intent)
        return self._execute(self.session.prepare_append(rows))

    def replace_serialized_rows(self, rows, *, expected_view_digest: str):
        self.binding._admit(self.intent)
        return self._execute(self.session.prepare_replace(rows, expected_view_digest=expected_view_digest))

    def mark_clock_attempt(self) -> None:
        if self.outcome is None or self.outcome.status != "materialized":
            raise RuntimeError("a clock attempt requires new materialization")
        self.clock_attempted = True
        self._record(replace(self.outcome, clock_status="uncertain"))


@contextmanager
def _claims_mutation(path: Path, *, native_intent=None):
    # Deliberately ignore every ClaimsReadScope: native writer construction
    # acquires a fresh exclusive session before preparation, dedupe or planning.
    binding = _selected_claims_binding(path)
    if isinstance(binding, LegacyClaimsBinding):
        _require_legacy_namespace(path)
        if native_intent is not None:
            from engine.qledger_store_protocol import SnapshotIntegrityError

            raise SnapshotIntegrityError("CONFLICT", "native intent requires an explicit native owner binding")
        yield None
    else:
        with binding.mutation(native_intent=native_intent) as writer:
            yield writer
