"""Transactional qbus-owned store for low-latency news revisions.

This module is production-inert until an existing runtime owner selects it. It does
not replace or dual-write the legacy qbus parquet on import. The store persists
immutable provider revisions, delivery receipts, current reduced state, canonical
security routing, a change log, and one compare-and-swap provider cursor in the
same SQLite transaction.

No network, provider credential, scheduler, auth policy, or ambient clock is owned
here. Caller-supplied NewsReadRights are capabilities from the eventual API owner,
not rights decisions made by this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from collections.abc import Mapping
from typing import Iterable, Sequence

from engine.qbus_news_contract import NewsRevision
from engine.qbus_news_cluster import (
    ClusterCandidate,
    ClusterItem,
    ClusterPolicy,
    cluster_candidates,
)
from engine.qbus_news_reducer import NewsState, reduce_revision

SCHEMA = "qbus.news_store.v1"


class NewsStoreError(RuntimeError):
    pass


class StoreSchemaError(NewsStoreError):
    pass


class CursorConflict(NewsStoreError):
    def __init__(self, expected: str | None, actual: str | None) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__("qbus_news_store:cursor_conflict")


class RevisionCollision(NewsStoreError):
    pass


class StoreValidationError(NewsStoreError):
    pass


class LegacySchemaError(NewsStoreError):
    pass


class LegacyCollision(NewsStoreError):
    pass


@dataclass(frozen=True, slots=True)
class LegacyImportReceipt:
    schema: str
    imported_rows: int
    duplicate_rows: int
    total_rows: int


@dataclass(frozen=True, slots=True)
class RoutedRevision:
    revision: NewsRevision
    security_ids: tuple[str, ...]
    universe_revision: str
    restoration_qualified: bool = False


@dataclass(frozen=True, slots=True)
class NewsReadRights:
    allowed_sources: frozenset[str]
    allow_title: bool = True
    allow_url: bool = True
    allow_teaser: bool = True

    @classmethod
    def all_internal(cls) -> "NewsReadRights":
        return cls(allowed_sources=frozenset({"benzinga"}))


@dataclass(frozen=True, slots=True)
class CommitReceipt:
    schema: str
    source_key: str
    cursor: str | None
    inserted_revisions: int
    duplicate_revisions: int
    stale_revisions: int
    conflict_revisions: int
    applied_states: int
    withdrawn_states: int
    first_sequence: int | None
    last_sequence: int | None


@dataclass(frozen=True, slots=True)
class StoryRow:
    sequence: int
    source: str
    source_item_id: str
    story_id: str
    source_count: int
    item_count: int
    title: str
    url: str
    teaser: str
    published_at: datetime | None
    updated_at: datetime | None
    received_at: datetime
    universe_revision: str


@dataclass(frozen=True, slots=True)
class NewsSnapshot:
    schema: str
    security_id: str
    rows: tuple[StoryRow, ...]
    next_cursor: int | None
    has_more: bool


@dataclass(frozen=True, slots=True)
class ChangeRow:
    sequence: int
    kind: str
    source: str
    source_item_id: str
    story_id: str
    title: str
    url: str
    teaser: str
    security_ids: tuple[str, ...]
    universe_revision: str
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class ChangePage:
    schema: str
    rows: tuple[ChangeRow, ...]
    next_sequence: int
    has_more: bool


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS qbus_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_revisions (
    revision_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    identity_json TEXT NOT NULL,
    revision_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_revisions_item
ON news_revisions(source, source_item_id);

CREATE TABLE IF NOT EXISTS news_deliveries (
    delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id TEXT NOT NULL,
    transport TEXT NOT NULL,
    message_id TEXT NOT NULL,
    received_at TEXT NOT NULL,
    delivery_json TEXT NOT NULL,
    UNIQUE(revision_id, transport, message_id, received_at),
    FOREIGN KEY(revision_id) REFERENCES news_revisions(revision_id)
);

CREATE TABLE IF NOT EXISTS news_states (
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    current_revision_id TEXT NOT NULL,
    status TEXT NOT NULL,
    state_json TEXT NOT NULL,
    last_sequence INTEGER,
    universe_revision TEXT NOT NULL,
    PRIMARY KEY(source, source_item_id),
    FOREIGN KEY(current_revision_id) REFERENCES news_revisions(revision_id)
);

CREATE TABLE IF NOT EXISTS news_security_index (
    security_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    PRIMARY KEY(security_id, source, source_item_id),
    FOREIGN KEY(source, source_item_id)
        REFERENCES news_states(source, source_item_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_news_security_lookup
ON news_security_index(security_id);

CREATE TABLE IF NOT EXISTS news_clusters (
    cluster_id TEXT PRIMARY KEY,
    anchor_story_id TEXT NOT NULL,
    anchor_title TEXT NOT NULL,
    anchor_observed_at TEXT NOT NULL,
    subject_ids_json TEXT NOT NULL,
    event_family TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_cluster_members (
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    story_id TEXT NOT NULL,
    PRIMARY KEY(source, source_item_id),
    FOREIGN KEY(cluster_id) REFERENCES news_clusters(cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_news_cluster_members_cluster
ON news_cluster_members(cluster_id);

CREATE TABLE IF NOT EXISTS news_changes (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK(kind IN ('upsert', 'remove')),
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    security_ids_json TEXT NOT NULL,
    universe_revision TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    FOREIGN KEY(revision_id) REFERENCES news_revisions(revision_id)
);

CREATE INDEX IF NOT EXISTS idx_news_changes_item
ON news_changes(source, source_item_id, sequence);

CREATE TABLE IF NOT EXISTS news_cursors (
    source_key TEXT PRIMARY KEY,
    cursor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS legacy_items (
    item_id TEXT PRIMARY KEY,
    ordinal INTEGER NOT NULL UNIQUE,
    row_json TEXT NOT NULL
);
"""


_DATETIME_REVISION_FIELDS = (
    "published_at",
    "updated_at",
    "source_event_at",
    "received_at",
    "version_at",
)
_DATETIME_STATE_FIELDS = (
    "published_at",
    "updated_at",
    "source_event_at",
    "version_at",
    "first_received_at",
    "last_received_at",
)
_TUPLE_REVISION_FIELDS = (
    "provider_tickers",
    "channels",
    "tags",
    "clock_anomalies",
)
_TUPLE_STATE_FIELDS = (
    "provider_tickers",
    "channels",
    "tags",
)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _stable_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _revision_dict(revision: NewsRevision) -> dict:
    out = asdict(revision)
    for field in _DATETIME_REVISION_FIELDS:
        out[field] = _iso(out[field])
    for field in _TUPLE_REVISION_FIELDS:
        out[field] = list(out[field])
    return out


def _revision_from_json(raw: str) -> NewsRevision:
    obj = json.loads(raw)
    for field in _DATETIME_REVISION_FIELDS:
        if obj.get(field) is not None:
            obj[field] = datetime.fromisoformat(obj[field])
    for field in _TUPLE_REVISION_FIELDS:
        obj[field] = tuple(obj.get(field) or ())
    return NewsRevision(**obj)


def _state_dict(state: NewsState) -> dict:
    out = asdict(state)
    for field in _DATETIME_STATE_FIELDS:
        out[field] = _iso(out[field])
    for field in _TUPLE_STATE_FIELDS:
        out[field] = list(out[field])
    return out


def _state_from_json(raw: str) -> NewsState:
    obj = json.loads(raw)
    for field in _DATETIME_STATE_FIELDS:
        if obj.get(field) is not None:
            obj[field] = datetime.fromisoformat(obj[field])
    for field in _TUPLE_STATE_FIELDS:
        obj[field] = tuple(obj.get(field) or ())
    return NewsState(**obj)


def _content_hash(revision: NewsRevision) -> str:
    payload = {
        "body_sha256": revision.body_sha256,
        "channels": revision.channels,
        "tags": revision.tags,
        "teaser": revision.teaser,
        "tickers": revision.provider_tickers,
        "title": revision.title,
        "url": revision.url,
    }
    return hashlib.sha256(
        _stable_json(payload).encode("utf-8")
    ).hexdigest()


def _identity_json(revision: NewsRevision) -> str:
    if _content_hash(revision) != revision.content_hash:
        raise RevisionCollision("qbus_news_store:content_hash_mismatch")
    removed = revision.action == "removed"
    basis = "|".join(
        (
            revision.source,
            revision.source_item_id,
            "removed" if removed else "article",
            revision.content_hash,
            revision.version_clock_domain,
            revision.version_at.isoformat(),
        )
    )
    expected = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]
    if expected != revision.revision_id:
        raise RevisionCollision("qbus_news_store:revision_id_mismatch")
    return _stable_json(
        {
            "source": revision.source,
            "source_item_id": revision.source_item_id,
            "removed": removed,
            "content_hash": revision.content_hash,
            "version_at": revision.version_at.isoformat(),
            "version_clock_domain": revision.version_clock_domain,
        }
    )


def _validate_token(value: str, field: str, maximum: int = 512) -> str:
    if not isinstance(value, str):
        raise StoreValidationError(f"qbus_news_store:invalid_{field}")
    out = value.strip()
    if not out or len(out) > maximum or "\x00" in out:
        raise StoreValidationError(f"qbus_news_store:invalid_{field}")
    return out


def _legacy_columns() -> tuple[str, ...]:
    # Deferred import avoids making the new store a prerequisite of qbus.v1.
    from engine import qbus
    return tuple(qbus.COLUMNS)


def _python_scalar(value: object) -> object:
    # pandas/numpy scalar values expose .item(); qbus v1 rows otherwise contain
    # only JSON-native scalars after normalize_row.
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def validate_legacy_rows(rows: Iterable[Mapping[str, object]]) -> tuple[dict, ...]:
    """Validate a qbus.v1 snapshot without rewriting or normalizing its semantics."""
    columns = _legacy_columns()
    expected = set(columns)
    out: list[dict] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise LegacySchemaError("qbus_news_store:legacy_row_not_mapping")
        if set(raw.keys()) != expected:
            raise LegacySchemaError("qbus_news_store:legacy_schema_mismatch")
        row = {name: _python_scalar(raw[name]) for name in columns}
        item_id = row["item_id"]
        if not isinstance(item_id, str) or not item_id or "\x00" in item_id:
            raise LegacySchemaError("qbus_news_store:legacy_item_id_invalid")
        # Prove every value can round-trip through the exact durable encoding.
        try:
            encoded = _stable_json(row)
            decoded = json.loads(encoded)
        except (TypeError, ValueError) as exc:
            raise LegacySchemaError("qbus_news_store:legacy_row_not_json_safe") from exc
        if set(decoded.keys()) != expected:
            raise LegacySchemaError("qbus_news_store:legacy_roundtrip_failed")
        out.append(row)
    return tuple(out)


def _validate_routed(item: RoutedRevision) -> RoutedRevision:
    if not isinstance(item, RoutedRevision):
        raise StoreValidationError("qbus_news_store:invalid_routed_revision")
    universe_revision = _validate_token(
        item.universe_revision, "universe_revision", 1024
    )
    security_ids: list[str] = []
    seen: set[str] = set()
    for raw in item.security_ids:
        token = _validate_token(raw, "security_id", 1024)
        if token not in seen:
            seen.add(token)
            security_ids.append(token)
    return RoutedRevision(
        revision=item.revision,
        security_ids=tuple(security_ids),
        universe_revision=universe_revision,
        restoration_qualified=bool(item.restoration_qualified),
    )


def _redact_story(
    *,
    sequence: int,
    state: NewsState,
    story_id: str,
    source_count: int,
    item_count: int,
    universe_revision: str,
    rights: NewsReadRights,
) -> StoryRow:
    return StoryRow(
        sequence=sequence,
        source=state.source,
        source_item_id=state.source_item_id,
        story_id=story_id,
        source_count=source_count,
        item_count=item_count,
        title=state.title if rights.allow_title else "",
        url=state.url if rights.allow_url else "",
        teaser=state.teaser if rights.allow_teaser else "",
        published_at=state.published_at,
        updated_at=state.updated_at,
        received_at=state.last_received_at,
        universe_revision=universe_revision,
    )


class NewsStore:
    """One local transactional store bound to one provider cursor namespace."""

    def __init__(
        self,
        path: Path | str,
        *,
        source_key: str,
        cluster_policy: ClusterPolicy | None = None,
    ) -> None:
        self.path = Path(path)
        self.source_key = _validate_token(source_key, "source_key", 256)
        self.cluster_policy = cluster_policy or ClusterPolicy()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.path),
            timeout=5.0,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._configure()
        self._initialize()
        os.chmod(self.path, 0o600)

    def __enter__(self) -> "NewsStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def _configure(self) -> None:
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            raise NewsStoreError("qbus_news_store:wal_unavailable")

    def _initialize(self) -> None:
        self._conn.executescript(_SCHEMA_SQL)
        row = self._conn.execute(
            "SELECT value FROM qbus_meta WHERE key='schema'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO qbus_meta(key,value) VALUES('schema',?)",
                (SCHEMA,),
            )
        elif row["value"] != SCHEMA:
            raise StoreSchemaError("qbus_news_store:schema_mismatch")

    def current_cursor(self) -> str | None:
        row = self._conn.execute(
            "SELECT cursor FROM news_cursors WHERE source_key=?",
            (self.source_key,),
        ).fetchone()
        return None if row is None else str(row["cursor"])

    def counts(self) -> dict[str, int]:
        mapping = {
            "revisions": "news_revisions",
            "states": "news_states",
            "security_index": "news_security_index",
            "changes": "news_changes",
            "legacy_items": "legacy_items",
        }
        return {
            key: int(
                self._conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            )
            for key, table in mapping.items()
        }

    def import_legacy_rows(
        self, rows: Iterable[Mapping[str, object]]
    ) -> LegacyImportReceipt:
        """Import qbus.v1 rows losslessly without activating a dual writer.

        Exact existing rows are idempotent. A same-item-id byte/field conflict
        refuses and rolls back the whole batch.
        """
        validated = validate_legacy_rows(rows)
        imported = duplicate = 0
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(ordinal), -1) FROM legacy_items"
            ).fetchone()
            next_ordinal = int(row[0]) + 1
            for legacy in validated:
                item_id = str(legacy["item_id"])
                payload = _stable_json(legacy)
                existing = self._conn.execute(
                    "SELECT row_json FROM legacy_items WHERE item_id=?",
                    (item_id,),
                ).fetchone()
                if existing is not None:
                    if str(existing["row_json"]) != payload:
                        raise LegacyCollision(
                            "qbus_news_store:legacy_item_collision"
                        )
                    duplicate += 1
                    continue
                self._conn.execute(
                    """
                    INSERT INTO legacy_items(item_id, ordinal, row_json)
                    VALUES(?,?,?)
                    """,
                    (item_id, next_ordinal, payload),
                )
                next_ordinal += 1
                imported += 1
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        total = int(
            self._conn.execute(
                "SELECT count(*) FROM legacy_items"
            ).fetchone()[0]
        )
        return LegacyImportReceipt(
            schema=SCHEMA,
            imported_rows=imported,
            duplicate_rows=duplicate,
            total_rows=total,
        )

    def legacy_rows(self) -> tuple[dict, ...]:
        """Return imported qbus.v1 rows in their original first-import order."""
        rows = self._conn.execute(
            "SELECT row_json FROM legacy_items ORDER BY ordinal ASC"
        ).fetchall()
        return tuple(json.loads(str(row["row_json"])) for row in rows)

    def _load_state(self, source: str, source_item_id: str) -> NewsState | None:
        row = self._conn.execute(
            """
            SELECT state_json FROM news_states
            WHERE source=? AND source_item_id=?
            """,
            (source, source_item_id),
        ).fetchone()
        return None if row is None else _state_from_json(row["state_json"])

    def _persist_revision(self, revision: NewsRevision) -> bool:
        identity = _identity_json(revision)
        row = self._conn.execute(
            """
            SELECT identity_json FROM news_revisions
            WHERE revision_id=?
            """,
            (revision.revision_id,),
        ).fetchone()
        if row is not None:
            if row["identity_json"] != identity:
                raise RevisionCollision(
                    "qbus_news_store:revision_identity_collision"
                )
            inserted = False
        else:
            self._conn.execute(
                """
                INSERT INTO news_revisions(
                    revision_id, source, source_item_id,
                    identity_json, revision_json
                ) VALUES(?,?,?,?,?)
                """,
                (
                    revision.revision_id,
                    revision.source,
                    revision.source_item_id,
                    identity,
                    _stable_json(_revision_dict(revision)),
                ),
            )
            inserted = True

        delivery = _stable_json(
            {
                "transport": revision.transport,
                "message_id": revision.message_id,
                "received_at": revision.received_at.isoformat(),
            }
        )
        self._conn.execute(
            """
            INSERT OR IGNORE INTO news_deliveries(
                revision_id, transport, message_id, received_at, delivery_json
            ) VALUES(?,?,?,?,?)
            """,
            (
                revision.revision_id,
                revision.transport,
                revision.message_id or "",
                revision.received_at.isoformat(),
                delivery,
            ),
        )
        return inserted

    def _write_state(
        self,
        state: NewsState,
        *,
        sequence: int | None,
        universe_revision: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO news_states(
                source, source_item_id, current_revision_id, status,
                state_json, last_sequence, universe_revision
            ) VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(source,source_item_id) DO UPDATE SET
                current_revision_id=excluded.current_revision_id,
                status=excluded.status,
                state_json=excluded.state_json,
                last_sequence=excluded.last_sequence,
                universe_revision=excluded.universe_revision
            """,
            (
                state.source,
                state.source_item_id,
                state.current_revision_id,
                state.status,
                _stable_json(_state_dict(state)),
                sequence,
                universe_revision,
            ),
        )

    def _replace_security_index(
        self,
        *,
        state: NewsState,
        security_ids: Sequence[str],
    ) -> None:
        self._conn.execute(
            """
            DELETE FROM news_security_index
            WHERE source=? AND source_item_id=?
            """,
            (state.source, state.source_item_id),
        )
        if state.status != "active":
            return
        for security_id in security_ids:
            self._conn.execute(
                """
                INSERT INTO news_security_index(
                    security_id, source, source_item_id
                ) VALUES(?,?,?)
                """,
                (security_id, state.source, state.source_item_id),
            )

    def _existing_cluster_id(self, source: str, source_item_id: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT cluster_id FROM news_cluster_members
            WHERE source=? AND source_item_id=?
            """,
            (source, source_item_id),
        ).fetchone()
        return None if row is None else str(row["cluster_id"])

    def _cluster_candidates(self) -> tuple[ClusterCandidate, ...]:
        rows = self._conn.execute(
            """
            SELECT cluster_id, anchor_story_id, anchor_title,
                   anchor_observed_at, subject_ids_json, event_family
            FROM news_clusters
            ORDER BY anchor_observed_at DESC, cluster_id
            LIMIT ?
            """,
            (self.cluster_policy.max_candidates + 1,),
        ).fetchall()
        return tuple(
            ClusterCandidate(
                cluster_id=str(row["cluster_id"]),
                anchor_story_id=str(row["anchor_story_id"]),
                anchor_title=str(row["anchor_title"]),
                anchor_observed_at=datetime.fromisoformat(
                    str(row["anchor_observed_at"])
                ),
                subject_ids=tuple(json.loads(row["subject_ids_json"])),
                event_family=str(row["event_family"]),
            )
            for row in rows
        )

    def _ensure_cluster_membership(
        self,
        *,
        state: NewsState,
        security_ids: Sequence[str],
    ) -> str:
        existing = self._existing_cluster_id(
            state.source, state.source_item_id
        )
        if existing is not None:
            if security_ids:
                row = self._conn.execute(
                    "SELECT subject_ids_json FROM news_clusters WHERE cluster_id=?",
                    (existing,),
                ).fetchone()
                current = set(json.loads(row["subject_ids_json"])) if row else set()
                merged = tuple(sorted(current | set(security_ids)))
                self._conn.execute(
                    """
                    UPDATE news_clusters SET subject_ids_json=?
                    WHERE cluster_id=?
                    """,
                    (_stable_json(list(merged)), existing),
                )
            return existing

        incoming = ClusterItem(
            source=state.source,
            source_item_id=state.source_item_id,
            title=state.title,
            observed_at=state.first_received_at,
            subject_ids=tuple(security_ids),
            event_family="",
        )
        decision = cluster_candidates(
            incoming,
            self._cluster_candidates(),
            policy=self.cluster_policy,
        )
        cluster_id = decision.cluster_id
        if decision.action == "new":
            self._conn.execute(
                """
                INSERT INTO news_clusters(
                    cluster_id, anchor_story_id, anchor_title,
                    anchor_observed_at, subject_ids_json, event_family
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    cluster_id,
                    incoming.story_id,
                    incoming.title,
                    incoming.observed_at.isoformat(),
                    _stable_json(list(incoming.subject_ids)),
                    incoming.event_family,
                ),
            )
        self._conn.execute(
            """
            INSERT INTO news_cluster_members(
                source, source_item_id, cluster_id, story_id
            ) VALUES(?,?,?,?)
            """,
            (
                state.source,
                state.source_item_id,
                cluster_id,
                incoming.story_id,
            ),
        )
        return cluster_id

    def _active_cluster_members(self, cluster_id: str) -> int:
        return int(
            self._conn.execute(
                """
                SELECT count(*)
                FROM news_cluster_members m
                JOIN news_states s
                  ON s.source=m.source AND s.source_item_id=m.source_item_id
                WHERE m.cluster_id=? AND s.status='active'
                """,
                (cluster_id,),
            ).fetchone()[0]
        )

    def _write_change(
        self,
        *,
        kind: str,
        revision: NewsRevision,
        cluster_id: str,
        security_ids: Sequence[str],
        universe_revision: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO news_changes(
                kind, source, source_item_id, revision_id, cluster_id,
                security_ids_json, universe_revision, observed_at
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                kind,
                revision.source,
                revision.source_item_id,
                revision.revision_id,
                cluster_id,
                _stable_json(list(security_ids)),
                universe_revision,
                revision.received_at.isoformat(),
            ),
        )
        return int(cur.lastrowid)

    def commit(
        self,
        revisions: Sequence[RoutedRevision],
        *,
        expected_cursor: str | None,
        next_cursor: str | None,
    ) -> CommitReceipt:
        routed = tuple(_validate_routed(item) for item in revisions)
        if next_cursor is not None:
            next_cursor = _validate_token(next_cursor, "next_cursor", 4096)
        if expected_cursor is not None:
            expected_cursor = _validate_token(
                expected_cursor, "expected_cursor", 4096
            )

        inserted = duplicate = stale = conflict = applied = withdrawn = 0
        sequences: list[int] = []
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            actual = self.current_cursor()
            if actual != expected_cursor:
                raise CursorConflict(expected_cursor, actual)

            for item in routed:
                revision = item.revision
                is_new = self._persist_revision(revision)
                if is_new:
                    inserted += 1
                previous = self._load_state(
                    revision.source, revision.source_item_id
                )
                reduction = reduce_revision(
                    previous,
                    revision,
                    restoration_qualified=item.restoration_qualified,
                )
                if reduction.disposition == "duplicate":
                    duplicate += 1
                    if previous is not None and reduction.state != previous:
                        row = self._conn.execute(
                            """
                            SELECT last_sequence, universe_revision
                            FROM news_states
                            WHERE source=? AND source_item_id=?
                            """,
                            (revision.source, revision.source_item_id),
                        ).fetchone()
                        self._write_state(
                            reduction.state,
                            sequence=None if row is None else row["last_sequence"],
                            universe_revision=(
                                item.universe_revision
                                if row is None
                                else row["universe_revision"]
                            ),
                        )
                    continue
                if reduction.disposition == "stale":
                    stale += 1
                    continue
                if reduction.disposition == "conflict":
                    conflict += 1
                    continue

                security_ids = (
                    ()
                    if reduction.state.status != "active"
                    else item.security_ids
                )
                cluster_id = self._ensure_cluster_membership(
                    state=reduction.state,
                    security_ids=security_ids,
                )
                # Materialize the new state/index before deciding whether a
                # withdrawal removes the whole cluster or only one source item.
                self._write_state(
                    reduction.state,
                    sequence=None,
                    universe_revision=item.universe_revision,
                )
                self._replace_security_index(
                    state=reduction.state,
                    security_ids=security_ids,
                )
                kind = (
                    "remove"
                    if reduction.disposition == "withdrawn"
                    and self._active_cluster_members(cluster_id) == 0
                    else "upsert"
                )
                sequence = self._write_change(
                    kind=kind,
                    revision=revision,
                    cluster_id=cluster_id,
                    security_ids=security_ids,
                    universe_revision=item.universe_revision,
                )
                sequences.append(sequence)
                self._write_state(
                    reduction.state,
                    sequence=sequence,
                    universe_revision=item.universe_revision,
                )
                if reduction.disposition == "withdrawn":
                    withdrawn += 1
                else:
                    applied += 1

            if next_cursor is not None:
                self._conn.execute(
                    """
                    INSERT INTO news_cursors(source_key,cursor) VALUES(?,?)
                    ON CONFLICT(source_key) DO UPDATE SET cursor=excluded.cursor
                    """,
                    (self.source_key, next_cursor),
                )
            elif expected_cursor is not None:
                self._conn.execute(
                    "DELETE FROM news_cursors WHERE source_key=?",
                    (self.source_key,),
                )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

        return CommitReceipt(
            schema=SCHEMA,
            source_key=self.source_key,
            cursor=self.current_cursor(),
            inserted_revisions=inserted,
            duplicate_revisions=duplicate,
            stale_revisions=stale,
            conflict_revisions=conflict,
            applied_states=applied,
            withdrawn_states=withdrawn,
            first_sequence=min(sequences) if sequences else None,
            last_sequence=max(sequences) if sequences else None,
        )

    def commit_observations(
        self, revisions: Sequence[RoutedRevision]
    ) -> CommitReceipt:
        """Commit stream observations without advancing the REST delta cursor.

        The live service owns one serialized writer. Keeping the existing cursor as
        both expected and next value makes any accidental concurrent cursor move
        fail before revisions are applied rather than silently rewinding it.
        """
        cursor = self.current_cursor()
        return self.commit(
            revisions,
            expected_cursor=cursor,
            next_cursor=cursor,
        )

    def snapshot(
        self,
        security_id: str,
        *,
        limit: int,
        cursor: int | None,
        rights: NewsReadRights,
    ) -> NewsSnapshot:
        security_id = _validate_token(security_id, "security_id", 1024)
        if not isinstance(rights, NewsReadRights):
            raise StoreValidationError("qbus_news_store:invalid_rights")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise StoreValidationError("qbus_news_store:invalid_limit")
        if cursor is not None and (
            not isinstance(cursor, int)
            or isinstance(cursor, bool)
            or cursor < 1
        ):
            raise StoreValidationError("qbus_news_store:invalid_cursor")
        if not rights.allowed_sources:
            return NewsSnapshot(SCHEMA, security_id, (), cursor, False)

        placeholders = ",".join("?" for _ in rights.allowed_sources)
        params: list[object] = [security_id, *sorted(rights.allowed_sources)]
        having_cursor = ""
        if cursor is not None:
            having_cursor = " HAVING MAX(s.last_sequence) < ?"
            params.append(cursor)
        params.append(limit + 1)
        clusters = self._conn.execute(
            f"""
            SELECT m.cluster_id, MAX(s.last_sequence) AS cluster_sequence
            FROM news_security_index i
            JOIN news_states s
              ON s.source=i.source AND s.source_item_id=i.source_item_id
            JOIN news_cluster_members m
              ON m.source=s.source AND m.source_item_id=s.source_item_id
            WHERE i.security_id=?
              AND s.status='active'
              AND s.source IN ({placeholders})
            GROUP BY m.cluster_id
            {having_cursor}
            ORDER BY cluster_sequence DESC, m.cluster_id
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        has_more = len(clusters) > limit
        selected = clusters[:limit]
        out: list[StoryRow] = []
        for cluster in selected:
            cluster_id = str(cluster["cluster_id"])
            member_params: list[object] = [
                cluster_id,
                security_id,
                *sorted(rights.allowed_sources),
            ]
            members = self._conn.execute(
                f"""
                SELECT s.state_json, s.last_sequence, s.universe_revision
                FROM news_cluster_members m
                JOIN news_states s
                  ON s.source=m.source AND s.source_item_id=m.source_item_id
                JOIN news_security_index i
                  ON i.source=s.source AND i.source_item_id=s.source_item_id
                WHERE m.cluster_id=?
                  AND i.security_id=?
                  AND s.status='active'
                  AND s.source IN ({placeholders})
                ORDER BY s.last_sequence DESC, s.source, s.source_item_id
                """,
                tuple(member_params),
            ).fetchall()
            if not members:
                continue
            representative = members[0]
            states = [
                _state_from_json(row["state_json"]) for row in members
            ]
            out.append(
                _redact_story(
                    sequence=int(cluster["cluster_sequence"]),
                    state=states[0],
                    story_id=cluster_id,
                    source_count=len({state.source for state in states}),
                    item_count=len(states),
                    universe_revision=str(
                        representative["universe_revision"]
                    ),
                    rights=rights,
                )
            )
        rows = tuple(out)
        next_cursor = rows[-1].sequence if rows else cursor
        return NewsSnapshot(
            schema=SCHEMA,
            security_id=security_id,
            rows=rows,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def changes(
        self,
        *,
        after_sequence: int,
        limit: int,
        rights: NewsReadRights,
    ) -> ChangePage:
        if (
            not isinstance(after_sequence, int)
            or isinstance(after_sequence, bool)
            or after_sequence < 0
        ):
            raise StoreValidationError("qbus_news_store:invalid_sequence")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise StoreValidationError("qbus_news_store:invalid_limit")
        if not isinstance(rights, NewsReadRights):
            raise StoreValidationError("qbus_news_store:invalid_rights")
        if not rights.allowed_sources:
            return ChangePage(SCHEMA, (), after_sequence, False)

        placeholders = ",".join("?" for _ in rights.allowed_sources)
        rows = self._conn.execute(
            f"""
            SELECT c.*, r.revision_json
            FROM news_changes c
            JOIN news_revisions r ON r.revision_id=c.revision_id
            WHERE c.sequence > ?
              AND c.source IN ({placeholders})
            ORDER BY c.sequence ASC
            LIMIT ?
            """,
            (
                after_sequence,
                *sorted(rights.allowed_sources),
                limit + 1,
            ),
        ).fetchall()
        has_more = len(rows) > limit
        selected = rows[:limit]
        out: list[ChangeRow] = []
        for row in selected:
            revision = _revision_from_json(row["revision_json"])
            removed = row["kind"] == "remove"
            out.append(
                ChangeRow(
                    sequence=int(row["sequence"]),
                    kind=str(row["kind"]),
                    source=str(row["source"]),
                    source_item_id=str(row["source_item_id"]),
                    story_id=str(row["cluster_id"]),
                    title=(
                        ""
                        if removed or not rights.allow_title
                        else revision.title
                    ),
                    url=(
                        ""
                        if removed or not rights.allow_url
                        else revision.url
                    ),
                    teaser=(
                        ""
                        if removed or not rights.allow_teaser
                        else revision.teaser
                    ),
                    security_ids=tuple(
                        json.loads(row["security_ids_json"])
                    ),
                    universe_revision=str(row["universe_revision"]),
                    observed_at=datetime.fromisoformat(row["observed_at"]),
                )
            )
        next_sequence = out[-1].sequence if out else after_sequence
        return ChangePage(
            schema=SCHEMA,
            rows=tuple(out),
            next_sequence=next_sequence,
            has_more=has_more,
        )