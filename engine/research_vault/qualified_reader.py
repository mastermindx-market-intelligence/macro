"""Opt-in reader for the exact SQLite image from a qualified producer sweep.

Qualification is an explicit preparation act, never a health/request resweep.
The incumbent async adapter still owns concurrency and cancellation. This module
adds non-waiting image admission, not an executor or a scheduler. No default
runtime is enabled here; writer custody/nonrestoration must be qualified outside.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass
import json
import math
import sqlite3
import threading
import time
from typing import Any, Callable

from engine.research_vault import catalog, corpus, producer_generation as generation


class SelectedReadUnavailable(RuntimeError):
    """No body may be delivered from this selection."""


@dataclass(frozen=True)
class GuardedRead:
    value: Any
    delivery_guard: Callable[[], None]
    selection_identity: tuple[str, str, str, int]


class _LimitedStore:
    def __init__(self, store, byte_budget, *, before_corpus_read=None):
        self.store, self.byte_budget = store, byte_budget
        self.before_corpus_read = before_corpus_read

    def get_bytes_strict_bounded(self, key, bound):
        if key == generation.CORPUS_KEY:
            bound = min(bound, self.byte_budget)
            if self.before_corpus_read is not None:
                self.before_corpus_read()
        raw = self.store.get_bytes_strict_bounded(key, bound)
        if raw is not None and (type(raw) is not bytes or len(raw) > bound):
            raise SelectedReadUnavailable("bounded_store_contract_failed")
        return raw

    def get_bytes_strict_bounded_versioned(self, key, bound):
        return self.store.get_bytes_strict_bounded_versioned(key, bound)


class _SelectedStore:
    def __init__(self, owner):
        self.owner = owner

    def get_bytes_strict(self, key):
        if key == catalog.CATALOG_KEY:
            return self.owner._operation()[0].catalog_bytes
        return self.owner.store.get_bytes_strict(key)

    def __getattr__(self, name):
        return getattr(self.owner.store, name)


class _BorrowedConnection:
    """ReadService may close its borrow; the operation owns the actual image."""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, *args, **kwargs):
        return self._conn.execute(*args, **kwargs)

    def close(self):
        pass


def _open_image(selected):
    conn = sqlite3.connect(":memory:")
    try:
        conn.deserialize(selected.corpus_bytes)
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(False)
        conn.execute("PRAGMA query_only=ON")

        def authorize(action, arg1, arg2, db, trigger):
            if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ}:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and arg2 != "load_extension":
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_PRAGMA:
                if arg1 == "table_info" and arg2 == "documents":
                    return sqlite3.SQLITE_OK
                if arg1 in {"query_only", "data_version"} and arg2 is None:
                    return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        conn.set_authorizer(authorize)
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None or row[0] != str(corpus.SCHEMA_VERSION):
            raise SelectedReadUnavailable("selected_schema_unsupported")
        if conn.serialize() != selected.corpus_bytes:
            raise SelectedReadUnavailable("selected_image_changed")
        return conn
    except BaseException:
        conn.close()
        raise
    finally:
        selected = None  # an exception traceback must not pin a retired image


class QualifiedReadProvider:
    """One prepared generation with per-operation catalog/SQLite binding.

    Image budgets bound raw/serialized image admission, not total process RSS or
    SQLite query overhead. The deployment must separately qualify actual memory
    use. A moved fence, expired selection or withdrawn writer policy invalidates
    reuse permanently; only a fresh explicit prepare can replace that selection.
    The reuse window starts after the real sweep and SQLite qualification finish;
    producer completion time and the maximum source age are never reset.
    """
    def __init__(self, store, *, expected_producer_commit: str, clock: Callable[[], int],
                 writer_policy: Callable[[], bool] = lambda: False,
                 max_age_seconds: int = 3600, max_reuse_seconds: int = 300,
                 corpus_byte_budget: int = 32 * 1024 * 1024,
                 image_admission_bytes: int = 256 * 1024 * 1024):
        if not callable(clock) or not callable(writer_policy):
            raise ValueError("explicit clock and policy callbacks required")
        for value in (max_age_seconds, max_reuse_seconds, corpus_byte_budget, image_admission_bytes):
            if type(value) is not int or value <= 0:
                raise ValueError("finite positive integer bounds required")
        if corpus_byte_budget > generation.CORPUS_MAX_BYTES:
            raise ValueError("corpus bound exceeds canonical object bound")
        self.store = store
        self.expected_producer_commit, self.clock = expected_producer_commit, clock
        self.writer_policy = writer_policy
        self.max_age_seconds, self.max_reuse_seconds = max_age_seconds, max_reuse_seconds
        self.corpus_byte_budget, self.image_admission_bytes = corpus_byte_budget, image_admission_bytes
        self.catalog_store = _SelectedStore(self)
        self._selected = None
        self._prepared_at = None
        self._lock = threading.RLock()
        self._drained = threading.Condition(self._lock)
        self._prepare_lock = threading.Lock()
        self._inflight_bytes = 0
        self._active = 0
        self._guard_active = 0
        self._live_retained_bytes = 0
        self._refresh_reserved = 0
        self._refresh_exclusive = False
        self._policy_revision = 0
        self._current = contextvars.ContextVar("research_selected_operation", default=None)

    def _writer_qualified(self):
        try:
            qualified = self.writer_policy() is True
        except Exception:
            qualified = False
        if not qualified:
            with self._lock:
                self._policy_revision += 1
        return qualified

    def prepare(self):
        """Full qualification once, explicitly outside the hot request path."""
        if not self._prepare_lock.acquire(blocking=False):
            raise SelectedReadUnavailable("preparation_in_progress")
        try:
            with self._lock:
                if self._active or self._guard_active:
                    raise SelectedReadUnavailable("operation_in_progress")
                self._selected = None
                self._prepared_at = None
            selected, reason = generation.explained_selection(
                _LimitedStore(self.store, self.corpus_byte_budget),
                expected_producer_commit=self.expected_producer_commit,
                now=self.clock(), max_age_seconds=self.max_age_seconds,
                writer_protocol_qualified=self._writer_qualified())
            if selected is None:
                raise SelectedReadUnavailable(reason["code"])
            if len(selected.catalog_bytes) + 4 * len(selected.corpus_bytes) > self.image_admission_bytes:
                raise SelectedReadUnavailable("image_admission_exceeded")
            # Check SQLite capability and byte parity before admitting any reads.
            conn = _open_image(selected)
            conn.close()
            prepared_at = self.clock()
            if type(prepared_at) is not int or prepared_at < selected.qualified_at:
                raise SelectedReadUnavailable("preparation_clock_refused")
            with self._lock:
                self._selected = selected
                self._prepared_at = prepared_at
            self._check(selected)
        finally:
            # A retained exception must not keep a rejected candidate image
            # alive through this frame after its admission has been released.
            selected = conn = None
            self._prepare_lock.release()

    def refresh(self, *, drain_timeout_seconds=5.0):
        """Full owner-driven requalification, preserving a still-valid old cut.

        The metadata census can overlap reads. Corpus acquisition and SQLite
        verification need an accounted, bounded transition with readers drained.
        No request, readiness check or delivery guard initiates this operation.
        """
        if self._current.get() is not None:
            raise SelectedReadUnavailable("nested_selected_operation")
        if (type(drain_timeout_seconds) not in (int, float)
                or not math.isfinite(drain_timeout_seconds)
                or not 0 < drain_timeout_seconds <= 5):
            raise SelectedReadUnavailable("invalid_refresh_drain_bound")
        if not self._prepare_lock.acquire(blocking=False):
            raise SelectedReadUnavailable("preparation_in_progress")
        previous = selected = None
        catalog_reserve = 2 * generation.CATALOG_MAX_BYTES
        corpus_budget = self.corpus_byte_budget
        corpus_started = False
        corpus_refusal = None
        try:
            with self._lock:
                previous = self._selected
                policy_revision = self._policy_revision
                old_retained = max(self._live_retained_bytes,
                    0 if previous is None else len(previous.catalog_bytes) + len(previous.corpus_bytes))
                if old_retained + self._inflight_bytes + catalog_reserve > self.image_admission_bytes:
                    raise SelectedReadUnavailable("image_admission_exceeded")
                self._refresh_reserved = catalog_reserve

            def before_corpus_read():
                nonlocal corpus_started, corpus_refusal
                if corpus_started:
                    corpus_refusal = "duplicate_candidate_corpus_read"
                    raise SelectedReadUnavailable(corpus_refusal)
                corpus_started = True
                deadline = time.monotonic() + drain_timeout_seconds
                with self._drained:
                    self._refresh_exclusive = True
                    self._drained.notify_all()
                    while self._active or self._guard_active:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            corpus_refusal = "refresh_drain_timeout"
                            raise SelectedReadUnavailable(corpus_refusal)
                        self._drained.wait(remaining)
                    charge = catalog_reserve + corpus_budget
                    if old_retained + charge > self.image_admission_bytes:
                        corpus_refusal = "image_admission_exceeded"
                        raise SelectedReadUnavailable(corpus_refusal)
                    self._refresh_reserved = charge

            selected, reason = generation.explained_selection(
                _LimitedStore(self.store, corpus_budget,
                              before_corpus_read=before_corpus_read),
                expected_producer_commit=self.expected_producer_commit,
                now=self.clock(), max_age_seconds=self.max_age_seconds,
                writer_protocol_qualified=self._writer_qualified())
            if selected is None:
                # The generic corpus reader deliberately hides storage errors;
                # preserve our own pre-read refusal without leaking diagnostics.
                raise SelectedReadUnavailable(corpus_refusal or reason["code"])
            if not corpus_started:
                raise SelectedReadUnavailable("candidate_corpus_not_admitted")
            with self._lock:
                charge = catalog_reserve + 4 * len(selected.corpus_bytes)
                if old_retained + charge > self.image_admission_bytes:
                    raise SelectedReadUnavailable("image_admission_exceeded")
                self._refresh_reserved = charge
            conn = _open_image(selected)
            conn.close()
            conn = None
            # A fresh exact fence read follows the full sweep and SQLite check.
            stamp = self._verify_selection(selected, self.clock(), require_current=False)
            with self._drained:
                if self._policy_revision != policy_revision:
                    raise SelectedReadUnavailable("refresh_policy_changed")
                self._selected, self._prepared_at = selected, stamp
                previous = selected = None
                self._refresh_reserved = 0
                self._refresh_exclusive = False
                self._drained.notify_all()
        except SelectedReadUnavailable:
            raise
        except Exception:
            raise SelectedReadUnavailable("refresh_unavailable") from None
        finally:
            previous = selected = None
            conn = None
            with self._drained:
                self._refresh_reserved = 0
                self._refresh_exclusive = False
                self._drained.notify_all()
            self._prepare_lock.release()

    def _check(self, selected):
        try:
            with self._lock:
                prepared_at = self._prepared_at
            self._verify_selection(selected, prepared_at, require_current=True)
        except Exception as exc:
            with self._lock:
                if self._selected is selected:
                    self._selected = None
                    self._prepared_at = None
            if isinstance(exc, SelectedReadUnavailable):
                raise
            raise SelectedReadUnavailable("selection_fence_unavailable") from None
        finally:
            selected = None

    def _verify_selection(self, selected, prepared_at, *, require_current):
        try:
            current = self.clock()
            if (self._writer_qualified() is not True or type(current) is not int
                    or type(prepared_at) is not int or current < prepared_at
                    or current < selected.qualified_at or current < selected.completed_at
                    or current - selected.completed_at > self.max_age_seconds
                    or current - prepared_at > self.max_reuse_seconds):
                raise SelectedReadUnavailable("selection_policy_or_age_refused")
            observed = self.store.get_bytes_strict_bounded_versioned(
                catalog.CATALOG_KEY, generation.CATALOG_MAX_BYTES)
            with self._lock:
                if ((require_current and self._selected is not selected) or observed is None
                        or observed.data != selected.catalog_bytes
                        or observed.version != selected.catalog_version):
                    raise SelectedReadUnavailable("selection_fence_moved")
            # The fence read can block. Recheck custody and time after that I/O,
            # including the final delivery guard after the last auth await.
            latest = self.clock()
            if (self._writer_qualified() is not True or type(latest) is not int
                    or latest < current or latest < selected.qualified_at
                    or latest - selected.completed_at > self.max_age_seconds
                    or latest - prepared_at > self.max_reuse_seconds):
                raise SelectedReadUnavailable("selection_policy_or_age_refused")
            return latest
        finally:
            selected = None
            observed = None

    def _operation(self):
        state = self._current.get()
        if state is None:
            raise SelectedReadUnavailable("no_selected_operation")
        return state

    def connection(self):
        state = self._operation()
        if state[1] is None:
            state[1] = _open_image(state[0])
        return _BorrowedConnection(state[1])

    def full_text_inventory(self):
        document = json.loads(self._operation()[0].catalog_bytes)
        return tuple(member["report_id"] for member in document[generation.GENERATION_FIELD]["members"]
                     if member["layer"] == "full")

    def _guard(self, key):
        with self._lock:
            if self._refresh_exclusive:
                raise SelectedReadUnavailable("refresh_image_transition")
            selected = self._selected
            if selected is None or self._key(selected) != key:
                selected = None
                raise SelectedReadUnavailable("selection_replaced")
            self._guard_active += 1
            self._live_retained_bytes = len(selected.corpus_bytes) + len(selected.catalog_bytes)
        try:
            self._check(selected)
        finally:
            selected = None
            with self._drained:
                self._guard_active -= 1
                if not self._active and not self._guard_active:
                    self._live_retained_bytes = 0
                self._drained.notify_all()

    @staticmethod
    def _key(selected):
        return (selected.epoch, selected.catalog_version, selected.catalog_sha256,
                selected.qualified_at)

    def run(self, operation: Callable[[], Any]) -> GuardedRead:
        if self._current.get() is not None:
            raise SelectedReadUnavailable("nested_selected_operation")
        with self._lock:
            if self._refresh_exclusive:
                raise SelectedReadUnavailable("refresh_image_transition")
            selected = self._selected
            if selected is None:
                raise SelectedReadUnavailable("selection_not_prepared")
            charge = 3 * len(selected.corpus_bytes)
            retained = len(selected.corpus_bytes) + len(selected.catalog_bytes)
            if (self._active >= 4 or retained + self._inflight_bytes + charge
                    + self._refresh_reserved > self.image_admission_bytes):
                selected = None
                raise SelectedReadUnavailable("image_admission_exceeded")
            self._active += 1
            self._inflight_bytes += charge
            self._live_retained_bytes = retained
        state = [selected, None]
        token = self._current.set(state)
        try:
            self._check(selected)
            value = operation()
            if state[1] is not None and state[1].serialize() != selected.corpus_bytes:
                raise SelectedReadUnavailable("selected_image_changed")
            self._check(selected)
            key = self._key(selected)
            return GuardedRead(value, lambda: self._guard(key), key)
        finally:
            try:
                if state[1] is not None:
                    state[1].close()
            finally:
                self._current.reset(token)
                selected = None
                state.clear()
                with self._drained:
                    self._active -= 1
                    self._inflight_bytes -= charge
                    if not self._active and not self._guard_active:
                        self._live_retained_bytes = 0
                    self._drained.notify_all()
