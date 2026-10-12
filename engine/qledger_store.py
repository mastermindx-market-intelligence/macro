"""Claims-owner bindings with an unconditional legacy production selection.

Legacy transports preserve their original parser and I/O contracts. The native
binding is available only through explicit private in-process construction for
synthetic integration; there is no discovery, environment switch or activation.
"""

from __future__ import annotations

import io
import json
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


_SYNTHETIC_BINDINGS: ContextVar[tuple[tuple[Path, Any], ...]] = ContextVar(
    "qledger_synthetic_bindings", default=(),
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
    if not _SYNTHETIC_BINDINGS.get() and not _READ_SCOPES.get():
        return legacy_reader(root, relative_path)
    try:
        path = Path(root) / relative_path
    except TypeError:
        return legacy_reader(root, relative_path)
    binding = _read_claims_binding(path)
    if isinstance(binding, LegacyClaimsBinding):
        return legacy_reader(root, relative_path)
    snapshot = _retained_snapshot(path, binding)
    with _snapshot_text(snapshot) as handle:
        value = handle.read()
    return value, "qledger-native:" + snapshot.receipt.source_id + ":" + snapshot.receipt.root_digest


class _NativeClaimsBinding:
    """Explicit inactive integration binding carrying an existing native intent."""

    def __init__(
        self, explicit_claims_path: Path, *, intent, limits,
        lock_timeout: float = 30, session_factory=None,
    ):
        path = Path(explicit_claims_path)
        if not path.is_absolute() or path.parts[-3:] != ("data", "qledger", "claims.jsonl"):
            raise ValueError("native binding requires an absolute canonical claims path")
        self.claims_path = path
        self.repo_root = path.parent.parent.parent
        self.intent = intent
        self.limits = limits
        self.lock_timeout = lock_timeout
        self._session_factory = session_factory
        # One current operation receipt per task, never a history/clock ledger.
        self._last_outcome: ContextVar[Any] = ContextVar("qledger_native_last_outcome", default=None)

    @property
    def last_outcome(self):
        return self._last_outcome.get()

    def _new_session(self):
        factory = self._session_factory
        if factory is None:
            from engine.qledger_store_native import NativeClaimsSession

            factory = NativeClaimsSession
        return factory(
            self.repo_root, intent=self.intent, limits=self.limits,
            lock_timeout=self.lock_timeout,
        )

    def read_snapshot(self):
        with self._new_session() as session:
            return session.read_snapshot()

    @contextmanager
    def mutation(self):
        from engine.qledger_store_native import ClaimsStorageError

        self._last_outcome.set(None)
        writer = None
        try:
            with self._new_session() as session:
                writer = _NativeClaimsWriter(self, session)
                yield writer
        except ClaimsStorageError as exc:
            outcome = exc.outcome
            if writer is not None and writer.clock_attempted:
                outcome = replace(outcome, clock_status="uncertain")
            self._last_outcome.set(outcome)
            if outcome is not exc.outcome:
                raise ClaimsStorageError(outcome) from exc
            raise


class _NativeClaimsWriter:
    def __init__(self, binding: _NativeClaimsBinding, session):
        self.binding = binding
        self.session = session
        self.snapshot = session.read_snapshot()
        self.outcome = None
        self.clock_attempted = False

    def read_rows(self) -> list[Any]:
        return _legacy_rows_from_lines(_snapshot_lines(self.snapshot))

    def _record(self, outcome):
        self.outcome = outcome
        self.binding._last_outcome.set(outcome)
        return outcome

    def append_serialized_rows(self, rows):
        return self._record(self.session.append_serialized_rows(rows))

    def replace_serialized_rows(self, rows, *, expected_view_digest: str):
        return self._record(self.session.replace_serialized_rows(
            rows, expected_view_digest=expected_view_digest,
        ))

    def mark_clock_attempt(self) -> None:
        if self.outcome is None or self.outcome.status != "materialized":
            raise RuntimeError("a clock attempt requires new materialization")
        self.clock_attempted = True
        self._record(replace(self.outcome, clock_status="uncertain"))


@contextmanager
def _claims_mutation(path: Path):
    # Deliberately ignore every ClaimsReadScope: native writer construction
    # acquires a fresh exclusive session before preparation, dedupe or planning.
    binding = _selected_claims_binding(path)
    if isinstance(binding, LegacyClaimsBinding):
        yield None
    else:
        with binding.mutation() as writer:
            yield writer
