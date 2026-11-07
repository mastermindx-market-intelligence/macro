"""Leases (§26.4): one child holds a handle at a time, and a crash cannot wedge it.

Every store instance carries an owner token minted at construction, so "who
holds this" is answerable after the fact from the row itself. Acquisition is a
single upsert whose DO UPDATE only fires when the incumbent row is already
expired — the loser of a race sees no row back and returns False, which is the
whole crash-safety story: a killed process stops renewing and its lease lapses
on TTL with no cleanup path to get wrong.

One connection per call, WAL on, no long-lived handles.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS leases (
    handle      TEXT PRIMARY KEY,
    owner       TEXT NOT NULL,
    acquired_at REAL NOT NULL,
    expires_at  REAL NOT NULL,
    meta        TEXT
);
CREATE INDEX IF NOT EXISTS leases_expiry ON leases(expires_at);
"""

# The WHERE on DO UPDATE is the mutex: it is evaluated against the stored row,
# so only an expired incumbent can be displaced. RETURNING yields a row only
# when the insert or the update actually landed.
ACQUIRE = """
INSERT INTO leases (handle, owner, acquired_at, expires_at, meta)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT (handle) DO UPDATE SET
    owner       = excluded.owner,
    acquired_at = excluded.acquired_at,
    expires_at  = excluded.expires_at,
    meta        = excluded.meta
WHERE leases.expires_at <= excluded.acquired_at
RETURNING owner
"""


class LeaseStore:
    def __init__(self, db_path, *, clock=time.time):
        self.db_path = str(db_path)
        self.owner = uuid.uuid4().hex
        self._clock = clock
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
        finally:
            conn.close()

    def acquire(self, handle: str, ttl_s: float, meta: dict | None = None) -> bool:
        """Take the handle if free or expired. True only if this caller now holds it."""
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        now = self._clock()
        payload = json.dumps(meta, sort_keys=True) if meta is not None else None
        with self._conn() as conn:
            row = conn.execute(
                ACQUIRE, (handle, self.owner, now, now + float(ttl_s), payload)
            ).fetchone()
        return bool(row) and row[0] == self.owner

    def release(self, handle: str) -> bool:
        """Drop the lease, but only if this store is still the owner."""
        with self._conn() as conn:
            n = conn.execute(
                "DELETE FROM leases WHERE handle = ? AND owner = ?", (handle, self.owner)
            ).rowcount
        return n > 0

    def held_by(self, handle: str) -> str | None:
        """Owner token of the live lease, or None when free/expired."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT owner FROM leases WHERE handle = ? AND expires_at > ?",
                (handle, self._clock()),
            ).fetchone()
        return row[0] if row else None

    def sweep(self) -> int:
        """Delete expired rows. Expiry already frees the handle; this is hygiene."""
        with self._conn() as conn:
            n = conn.execute("DELETE FROM leases WHERE expires_at <= ?", (self._clock(),)).rowcount
        return n

    def renew(self, handle: str, ttl_s: float) -> bool:
        """Extend a lease this store still owns and that has not yet lapsed."""
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        now = self._clock()
        with self._conn() as conn:
            n = conn.execute(
                "UPDATE leases SET expires_at = ? "
                "WHERE handle = ? AND owner = ? AND expires_at > ?",
                (now + float(ttl_s), handle, self.owner, now),
            ).rowcount
        return n == 1

    def meta(self, handle: str) -> dict | None:
        """The metadata the current holder attached, if the lease is live."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT meta FROM leases WHERE handle = ? AND expires_at > ?",
                (handle, self._clock()),
            ).fetchone()
        return json.loads(row[0]) if row and row[0] else None
