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
import sqlite3
import threading
from typing import Any, Callable

from engine.research_vault import catalog, corpus, producer_generation as generation


class SelectedReadUnavailable(RuntimeError):
    """No body may be delivered from this selection."""


@dataclass(frozen=True)
class GuardedRead:
    value: Any
    delivery_guard: Callable[[], None]


class _LimitedStore:
    def __init__(self, store, byte_budget):
        self.store, self.byte_budget = store, byte_budget

    def get_bytes_strict_bounded(self, key, bound):
        if key == generation.CORPUS_KEY:
            bound = min(bound, self.byte_budget)
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


class QualifiedReadProvider:
    """One prepared generation with per-operation catalog/SQLite binding.

    Image budgets bound raw/serialized image admission, not total process RSS or
    SQLite query overhead. The deployment must separately qualify actual memory
    use. A moved fence, expired selection or withdrawn writer policy invalidates
    reuse permanently; only a fresh explicit prepare can replace that selection.
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
        self._lock = threading.RLock()
        self._prepare_lock = threading.Lock()
        self._inflight_bytes = 0
        self._active = 0
        self._current = contextvars.ContextVar("research_selected_operation", default=None)

    def prepare(self):
        """Full qualification once, explicitly outside the hot request path."""
        if not self._prepare_lock.acquire(blocking=False):
            raise SelectedReadUnavailable("preparation_in_progress")
        try:
            with self._lock:
                if self._active:
                    raise SelectedReadUnavailable("operation_in_progress")
                self._selected = None
            selected, reason = generation.explained_selection(
                _LimitedStore(self.store, self.corpus_byte_budget),
                expected_producer_commit=self.expected_producer_commit,
                now=self.clock(), max_age_seconds=self.max_age_seconds,
                writer_protocol_qualified=self.writer_policy())
            if selected is None:
                raise SelectedReadUnavailable(reason["code"])
            if len(selected.catalog_bytes) + 4 * len(selected.corpus_bytes) > self.image_admission_bytes:
                raise SelectedReadUnavailable("image_admission_exceeded")
            # Check SQLite capability and byte parity before admitting any reads.
            conn = _open_image(selected)
            conn.close()
            with self._lock:
                self._selected = selected
            self._check(selected)
        finally:
            self._prepare_lock.release()

    def _check(self, selected):
        try:
            current = self.clock()
            if (self.writer_policy() is not True or type(current) is not int
                    or current < selected.qualified_at or current < selected.completed_at
                    or current - selected.completed_at > self.max_age_seconds
                    or current - selected.qualified_at > self.max_reuse_seconds):
                raise SelectedReadUnavailable("selection_policy_or_age_refused")
            observed = self.store.get_bytes_strict_bounded_versioned(
                catalog.CATALOG_KEY, generation.CATALOG_MAX_BYTES)
            with self._lock:
                if (self._selected is not selected or observed is None
                        or observed.data != selected.catalog_bytes
                        or observed.version != selected.catalog_version):
                    raise SelectedReadUnavailable("selection_fence_moved")
            # The fence read can block. Recheck custody and time after that I/O,
            # including the final delivery guard after the last auth await.
            latest = self.clock()
            if (self.writer_policy() is not True or type(latest) is not int
                    or latest < current or latest < selected.qualified_at
                    or latest - selected.completed_at > self.max_age_seconds
                    or latest - selected.qualified_at > self.max_reuse_seconds):
                raise SelectedReadUnavailable("selection_policy_or_age_refused")
        except Exception as exc:
            with self._lock:
                if self._selected is selected:
                    self._selected = None
            if isinstance(exc, SelectedReadUnavailable):
                raise
            raise SelectedReadUnavailable("selection_fence_unavailable") from None

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
            selected = self._selected
        if selected is None or self._key(selected) != key:
            raise SelectedReadUnavailable("selection_replaced")
        self._check(selected)

    @staticmethod
    def _key(selected):
        return (selected.epoch, selected.catalog_version, selected.catalog_sha256,
                selected.qualified_at)

    def run(self, operation: Callable[[], Any]) -> GuardedRead:
        if self._current.get() is not None:
            raise SelectedReadUnavailable("nested_selected_operation")
        with self._lock:
            selected = self._selected
            if selected is None:
                raise SelectedReadUnavailable("selection_not_prepared")
            charge = 3 * len(selected.corpus_bytes)
            retained = len(selected.corpus_bytes) + len(selected.catalog_bytes)
            if self._active >= 4 or retained + self._inflight_bytes + charge > self.image_admission_bytes:
                raise SelectedReadUnavailable("image_admission_exceeded")
            self._active += 1
            self._inflight_bytes += charge
        state = [selected, None]
        token = self._current.set(state)
        try:
            self._check(selected)
            value = operation()
            if state[1] is not None and state[1].serialize() != selected.corpus_bytes:
                raise SelectedReadUnavailable("selected_image_changed")
            self._check(selected)
            key = self._key(selected)
            return GuardedRead(value, lambda: self._guard(key))
        finally:
            try:
                if state[1] is not None:
                    state[1].close()
            finally:
                self._current.reset(token)
                with self._lock:
                    self._active -= 1
                    self._inflight_bytes -= charge
