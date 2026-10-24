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

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import urllib.parse
from collections.abc import Mapping
from typing import Iterable, Sequence

from engine.qbus_news_quality import (EDITORIAL_POLICY_VERSION, curated_source, curated_sql_clause, display_text, publisher_identity, register_curated_reader, representatives_in_display_order, reporting_state)
from engine.qbus_news_contract import NewsRevision
from engine.qbus_news_editorial import NewsEditorialView
from engine.qbus_news_cluster import (
    UNKNOWN_CLUSTER_POLICY_VERSION,
    ClusterCandidate,
    ClusterItem,
    ClusterPolicy,
    cluster_candidates,
    cluster_policy_version,
)
from engine.qbus_news_retrieval import (
    RETRIEVAL_POLICY_VERSION,
    RetrievalEvidence,
    index_cluster_backfill,
    index_new_anchor,
    index_subject_expansion,
    retrieve_candidates,
)
from engine.qbus_news_reducer import NewsState, reduce_revision
from engine.qbus_news_velocity import (
    FLOW_COMPARE_RULE,
    METHOD,
    SCHEMA as VELOCITY_SCHEMA,
    compare_to_typical,
    compute_news_velocity,
)

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


class StoreUnavailable(NewsStoreError):
    pass


class ReadOnlyStore(NewsStoreError):
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
class SourceReadRights:
    source: str
    allow_title: bool
    allow_url: bool
    allow_teaser: bool


@dataclass(frozen=True, slots=True)
class NewsReadRights:
    allowed_sources: frozenset[str]
    allow_title: bool = True
    allow_url: bool = True
    allow_teaser: bool = True
    source_fields: tuple[SourceReadRights, ...] = ()

    def allows(self, source: str, field: str) -> bool:
        if source not in self.allowed_sources or field not in {"title", "url", "teaser"}:
            return False
        if self.source_fields:
            matches = [grant for grant in self.source_fields if grant.source == source]
            # Duplicate receipts may only narrow a field, never broaden it.
            return bool(matches) and all(getattr(grant, "allow_" + field) for grant in matches)
        return bool(getattr(self, "allow_" + field))

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
    reporting_state: str = "not_compared"
    reporting_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NewsSnapshot:
    schema: str
    security_id: str
    rows: tuple[StoryRow, ...]
    next_cursor: int | None
    has_more: bool
    change_sequence: int = 0


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
    source_count: int | None = None
    item_count: int | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    received_at: datetime | None = None
    reporting_state: str = "not_compared"
    reporting_sources: tuple[str, ...] = ()
    projection_sequence: int | None = None


@dataclass(frozen=True, slots=True)
class ChangePage:
    schema: str
    rows: tuple[ChangeRow, ...]
    next_sequence: int
    has_more: bool


@dataclass(frozen=True, slots=True)
class StoryDetail:
    schema: str
    story_id: str
    source_count: int
    item_count: int
    members: tuple[StoryRow, ...]
    reporting_state: str = "not_compared"


# qbus_meta key naming the cluster policy version of the most recent
# writer; a read-only open with no policy passed reads it to know the
# policy in force. Absent only in stores written before it existed.
_META_CLUSTER_POLICY_KEY = "cluster_policy_version"

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

CREATE TABLE IF NOT EXISTS news_state_projection (
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    teaser TEXT NOT NULL,
    published_at TEXT,
    updated_at TEXT,
    received_at TEXT NOT NULL,
    PRIMARY KEY(source, source_item_id),
    FOREIGN KEY(source, source_item_id)
        REFERENCES news_states(source, source_item_id)
        ON DELETE CASCADE
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
    event_family TEXT NOT NULL,
    cluster_policy_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_news_clusters_observed
ON news_clusters(anchor_observed_at);

CREATE TABLE IF NOT EXISTS news_cluster_members (
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    story_id TEXT NOT NULL,
    retrieval_json TEXT,
    PRIMARY KEY(source, source_item_id),
    FOREIGN KEY(cluster_id) REFERENCES news_clusters(cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_news_cluster_members_cluster
ON news_cluster_members(cluster_id);

-- Derived candidate-retrieval index (engine/qbus_news_retrieval.py). Pure
-- optimization state for immutable anchors: written in the same transaction
-- that mints a cluster or expands its retained subject union, never rewritten
-- on member corrections, and rebuilt writer-only by the open-time backfill.
-- A cluster is indexed iff it has a fingerprint row.
CREATE TABLE IF NOT EXISTS news_cluster_fingerprints (
    cluster_id TEXT PRIMARY KEY,
    shingle_count INTEGER NOT NULL,
    shingles_json TEXT NOT NULL,
    indexed_policy TEXT NOT NULL,
    FOREIGN KEY(cluster_id) REFERENCES news_clusters(cluster_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS news_cluster_postings (
    security_id TEXT NOT NULL,
    shingle TEXT NOT NULL,
    anchor_observed_us INTEGER NOT NULL,
    cluster_id TEXT NOT NULL,
    PRIMARY KEY(security_id, shingle, anchor_observed_us, cluster_id),
    FOREIGN KEY(cluster_id) REFERENCES news_clusters(cluster_id)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_news_cluster_postings_cluster
ON news_cluster_postings(cluster_id);

CREATE TABLE IF NOT EXISTS news_shingle_df (
    security_id TEXT NOT NULL,
    shingle TEXT NOT NULL,
    df INTEGER NOT NULL,
    PRIMARY KEY(security_id, shingle)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_news_clusters_anchor_story
ON news_clusters(anchor_story_id);

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

CREATE TABLE IF NOT EXISTS news_change_targets (
    sequence INTEGER NOT NULL,
    security_id TEXT NOT NULL,
    PRIMARY KEY(sequence, security_id),
    FOREIGN KEY(sequence) REFERENCES news_changes(sequence)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_news_change_targets_security
ON news_change_targets(security_id, sequence);

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


def _projection_dt(value: object, *, required: bool = False) -> datetime | None:
    if value is None or value == "":
        if required:
            raise StoreSchemaError("qbus_news_store:projection_clock_missing")
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        raise StoreSchemaError("qbus_news_store:projection_clock_invalid") from None


def _projection_story(
    *,
    sequence: int,
    row: sqlite3.Row,
    story_id: str,
    source_count: int,
    item_count: int,
    universe_revision: str,
    rights: NewsReadRights,
    comparison: str = "not_compared",
    comparison_sources: tuple[str, ...] = (),
) -> StoryRow:
    received_at = _projection_dt(row["received_at"], required=True)
    assert received_at is not None
    return StoryRow(
        sequence=sequence,
        source=str(row["source"]),
        source_item_id=str(row["source_item_id"]),
        story_id=story_id,
        source_count=source_count,
        item_count=item_count,
        title=display_text(row["title"]) if rights.allows(str(row["source"]), "title") else "",
        url=str(row["url"]) if rights.allows(str(row["source"]), "url") else "",
        teaser=display_text(row["teaser"]) if rights.allows(str(row["source"]), "teaser") else "",
        published_at=_projection_dt(row["published_at"]),
        updated_at=_projection_dt(row["updated_at"]),
        received_at=received_at,
        universe_revision=universe_revision,
        reporting_state=comparison,
        reporting_sources=comparison_sources,
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
        title=display_text(state.title) if rights.allows(state.source, "title") else "",
        url=state.url if rights.allows(state.source, "url") else "",
        teaser=display_text(state.teaser) if rights.allows(state.source, "teaser") else "",
        published_at=state.published_at,
        updated_at=state.updated_at,
        received_at=state.last_received_at,
        universe_revision=universe_revision,
    )


def _cluster_policy_label(versions: list[str], in_force: str) -> str:
    """One string naming every policy that minted the 24h cluster stories.

    An empty list means no stored cluster contributed to stories_24h, so the
    policy in force is named: ``in_force`` is the open's passed policy
    stamp, or — when no policy was passed — the version the most recent
    writer recorded in ``qbus_meta`` (``UNKNOWN_CLUSTER_POLICY_VERSION``
    only for stores written before that key existed).
    """
    if not versions:
        return in_force
    if len(versions) == 1:
        return versions[0]
    return " + ".join(sorted(versions))


def _read_snapshot(method):
    """Keep a multi-query projection and its journal watermark on one DB view."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        own_transaction = not self._conn.in_transaction
        if own_transaction:
            self._conn.execute("BEGIN")
        try:
            return method(self, *args, **kwargs)
        finally:
            if own_transaction:
                self._conn.execute("ROLLBACK")
    return wrapped


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
        # A writer's policy is in force by construction (and is recorded
        # in qbus_meta by _initialize), passed or not.
        self._cluster_policy_passed = True
        self._read_only = False
        self._curated = False
        self._editorial_view = None
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

    @classmethod
    def open_readonly(
        cls,
        path: Path | str,
        *,
        source_key: str,
        cluster_policy: ClusterPolicy | None = None,
        curated: bool = False,
        editorial_view: NewsEditorialView | None = None,
    ) -> "NewsStore":
        if not isinstance(curated, bool) or (
            editorial_view is not None and
            (not curated or not isinstance(editorial_view, NewsEditorialView))
        ):
            raise StoreValidationError("qbus_news_store:invalid_editorial_view")
        db = Path(path)
        if not db.exists() or not db.is_file():
            raise StoreUnavailable("qbus_news_store:unavailable")
        obj = cls.__new__(cls)
        obj.path = db
        obj.source_key = _validate_token(source_key, "source_key", 256)
        obj.cluster_policy = cluster_policy or ClusterPolicy()
        obj._cluster_policy_passed = cluster_policy is not None
        obj._read_only = True
        obj._curated = curated
        obj._editorial_view = editorial_view
        try:
            obj._conn = sqlite3.connect(
                f"file:{urllib.parse.quote(str(db))}?mode=ro",
                uri=True,
                timeout=5.0,
                isolation_level=None,
            )
            obj._conn.row_factory = sqlite3.Row
            if curated:
                register_curated_reader(obj._conn, editorial_view)
            obj._conn.execute("PRAGMA query_only=ON")
            row = obj._conn.execute(
                "SELECT value FROM qbus_meta WHERE key='schema'"
            ).fetchone()
        except sqlite3.Error as exc:
            try:
                obj._conn.close()
            except Exception:
                pass
            raise StoreUnavailable("qbus_news_store:unavailable") from exc
        if row is None or str(row["value"]) != SCHEMA:
            obj._conn.close()
            raise StoreSchemaError("qbus_news_store:schema_mismatch")
        return obj

    def _curated_clause(self, rights: NewsReadRights) -> tuple[str, tuple[str, ...]]:
        if not self._curated:
            return "", ()
        return curated_sql_clause(
            tuple(source for source in self._read_sources(rights) if rights.allows(source, "url")),
            tuple(source for source in self._read_sources(rights) if rights.allows(source, "teaser")),
            editorial_view=self._editorial_view,
        )

    def _check_editorial_security(self, security_id: str) -> None:
        company = self._editorial_view.company if self._editorial_view else None
        if company is not None and company.security_id != security_id:
            raise StoreValidationError("qbus_news_store:editorial_security_mismatch")

    def _read_sources(self, rights: NewsReadRights) -> frozenset[str]:
        # Editorial eligibility narrows this read; the rights object and raw
        # retained reports remain unchanged. Unreadable titles cannot be used
        # to infer private content through the editorial predicate.
        if not self._curated:
            return rights.allowed_sources
        return frozenset(
            source for source in rights.allowed_sources
            if rights.allows(source, "title") and curated_source(source)
        )

    def _require_write(self) -> None:
        if self._read_only:
            raise ReadOnlyStore("qbus_news_store:read_only")

    def __enter__(self) -> "NewsStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def _in_force_cluster_policy_version(self) -> str:
        """Return the cluster policy version in force for this open.

        The policy is KNOWN iff a policy was passed to this open or the
        most recent writer recorded its ``cluster_policy_version`` in
        ``qbus_meta``; otherwise it is ``UNKNOWN_CLUSTER_POLICY_VERSION``
        — never the default ``ClusterPolicy()`` label for an unpassed
        policy.
        """
        if self._cluster_policy_passed:
            return cluster_policy_version(self.cluster_policy)
        row = self._conn.execute(
            "SELECT value FROM qbus_meta WHERE key=?", (_META_CLUSTER_POLICY_KEY,)
        ).fetchone()
        if row is None:
            return UNKNOWN_CLUSTER_POLICY_VERSION
        return str(row["value"])

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
        # Additive column for stores created before the policy stamp existed.
        # Only a writable open runs here; a wrong-schema store was already
        # refused above. Pre-existing rows stay NULL (never backfilled), so a
        # reader labels them "unknown (pre-column)".
        #
        # The same additive, no-SCHEMA-bump treatment records this writer's
        # policy version in qbus_meta, so a read-only open with no policy
        # passed knows the version in force. The upsert names the most
        # recent writer's policy (a different policy overwrites the key)
        # and writes nothing when the value is unchanged; a store written
        # before the key existed keeps reporting "unknown (pre-column)".
        columns = self._conn.execute(
            "PRAGMA table_info(news_clusters)"
        ).fetchall()
        if not any(str(col[1]) == "cluster_policy_version" for col in columns):
            # A second concurrent writable open of the same legacy store can
            # add this column between our PRAGMA and our ALTER; only that race.
            try:
                self._conn.execute(
                    "ALTER TABLE news_clusters"
                    " ADD COLUMN cluster_policy_version TEXT"
                )
            except sqlite3.OperationalError as exc:
                recheck = self._conn.execute(
                    "PRAGMA table_info(news_clusters)"
                ).fetchall()
                if (
                    "duplicate column name" not in str(exc).lower()
                    or not any(
                        str(col[1]) == "cluster_policy_version"
                        for col in recheck
                    )
                ):
                    raise
        # Additive column recording per-assignment candidate-retrieval evidence
        # (engine/qbus_news_retrieval.py). Pre-existing rows stay NULL and read
        # as "assigned before retrieval evidence existed", like the policy stamp
        # above.
        member_columns = self._conn.execute(
            "PRAGMA table_info(news_cluster_members)"
        ).fetchall()
        if not any(str(col[1]) == "retrieval_json" for col in member_columns):
            try:
                self._conn.execute(
                    "ALTER TABLE news_cluster_members"
                    " ADD COLUMN retrieval_json TEXT"
                )
            except sqlite3.OperationalError as exc:
                recheck = self._conn.execute(
                    "PRAGMA table_info(news_cluster_members)"
                ).fetchall()
                if (
                    "duplicate column name" not in str(exc).lower()
                    or not any(
                        str(col[1]) == "retrieval_json" for col in recheck
                    )
                ):
                    raise
        self._conn.execute(
            "INSERT INTO qbus_meta(key,value) VALUES(?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value"
            " WHERE qbus_meta.value IS NOT excluded.value",
            (
                _META_CLUSTER_POLICY_KEY,
                cluster_policy_version(self.cluster_policy),
            ),
        )
        self._backfill_read_projection()
        self._backfill_cluster_index()

    def _backfill_cluster_index(self) -> None:
        """Writer-only, deterministic derived-index migration.

        Indexes clusters that predate the retrieval index (or were interrupted
        mid-migration) in cluster_id order, in one transaction, so the next
        open resumes instead of duplicating. Read-only opens never run this.
        """
        columns = {str(row[1]) for row in self._conn.execute(
            "PRAGMA table_info(news_cluster_postings)"
        ).fetchall()}
        if "anchor_observed_us" not in columns:
            raise StoreSchemaError("qbus_news_store:retrieval_index_layout_mismatch")
        pending = self._conn.execute(
            """
            SELECT 1 FROM news_clusters c
            LEFT JOIN news_cluster_fingerprints f
              ON f.cluster_id = c.cluster_id
            WHERE f.cluster_id IS NULL OR f.indexed_policy <> ?
            LIMIT 1
            """,
            (RETRIEVAL_POLICY_VERSION,),
        ).fetchone()
        if pending is None:
            return
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            index_cluster_backfill(self._conn)
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def _backfill_read_projection(self) -> None:
        rows = self._conn.execute(
            """
            SELECT s.state_json
            FROM news_states s
            LEFT JOIN news_state_projection p
              ON p.source=s.source AND p.source_item_id=s.source_item_id
            WHERE p.source IS NULL
            ORDER BY s.source, s.source_item_id
            """
        ).fetchall()
        if not rows:
            return
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            for row in rows:
                self._write_projection_state(
                    _state_from_json(str(row["state_json"]))
                )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

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
        self._require_write()
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

    def _write_projection_state(self, state: NewsState) -> None:
        self._conn.execute(
            """
            INSERT INTO news_state_projection(
                source, source_item_id, title, url, teaser,
                published_at, updated_at, received_at
            ) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(source,source_item_id) DO UPDATE SET
                title=excluded.title,
                url=excluded.url,
                teaser=excluded.teaser,
                published_at=excluded.published_at,
                updated_at=excluded.updated_at,
                received_at=excluded.received_at
            """,
            (
                state.source,
                state.source_item_id,
                state.title,
                state.url,
                state.teaser,
                _iso(state.published_at),
                _iso(state.updated_at),
                state.last_received_at.isoformat(),
            ),
        )

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
        self._write_projection_state(state)

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

    def _cluster_candidates(
        self, incoming: ClusterItem
    ) -> tuple[tuple[ClusterCandidate, ...], "RetrievalEvidence"]:
        """Bounded candidate anchors plus retrieval evidence for one assignment.

        Delegates to the derived shingle index (engine/qbus_news_retrieval.py).
        The same hard relevance/window constraints the pure matcher applies are
        applied through indexed time bounds before candidate materialization.
        Posting and fingerprint limits remain explicit incomplete-retrieval
        conditions. The cluster's retained subject union — including
        corrected/withdrawn members — is what the index covers, so this stays a
        query optimization rather than a new matching policy: the pure matcher
        remains the final judge of every candidate it is handed.
        """
        candidates, evidence = retrieve_candidates(
            self._conn, incoming, policy=self.cluster_policy
        )
        if incoming.published_at is not None:
            candidates = tuple(
                replace(candidate, anchor_published_at=self._anchor_publication_at(candidate))
                for candidate in candidates
            )
        return candidates, evidence

    def _anchor_publication_at(self, candidate: ClusterCandidate) -> datetime | None:
        """Read at most the first accepted journal row for one immutable anchor.

        The item index bounds this lookup independently of correction history.
        Never derive an old anchor's publication clock from mutable current state,
        or scan forward past a mismatching legacy row to invent an anchor binding.
        """
        source, separator, source_item_id = candidate.anchor_story_id.partition(":")
        if source == "massive":
            publisher, separator, source_item_id = source_item_id.partition(":")
            source = f"massive:{publisher}"
        if not separator or not source_item_id:
            return None
        row = self._conn.execute(
            """
            SELECT first_change.kind, first_change.cluster_id,
                   revision.revision_json,
                   member.cluster_id AS member_cluster_id, member.story_id
            FROM (
                SELECT kind, source, source_item_id, revision_id, cluster_id
                FROM news_changes
                WHERE source=? AND source_item_id=?
                ORDER BY sequence LIMIT 1
            ) AS first_change
            JOIN news_revisions AS revision
              ON revision.revision_id=first_change.revision_id
             AND revision.source=first_change.source
             AND revision.source_item_id=first_change.source_item_id
            JOIN news_cluster_members AS member
              ON member.source=first_change.source
             AND member.source_item_id=first_change.source_item_id
            """,
            (source, source_item_id),
        ).fetchone()
        if (
            row is None or row["kind"] != "upsert"
            or row["cluster_id"] != candidate.cluster_id
            or row["member_cluster_id"] != candidate.cluster_id
            or row["story_id"] != candidate.anchor_story_id
        ):
            return None
        try:
            revision = _revision_from_json(row["revision_json"])
        except (KeyError, TypeError, ValueError):
            return None
        if (
            revision.source != source or revision.source_item_id != source_item_id
            or revision.title != candidate.anchor_title
            or revision.received_at != candidate.anchor_observed_at
        ):
            return None
        return revision.published_at

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
                added = set(security_ids) - current
                if added:
                    merged = tuple(sorted(current | set(security_ids)))
                    self._conn.execute(
                        """
                        UPDATE news_clusters SET subject_ids_json=?
                        WHERE cluster_id=?
                        """,
                        (_stable_json(list(merged)), existing),
                    )
                    self._expand_cluster_index(
                        cluster_id=existing,
                        added_security_ids=added,
                    )
            return existing

        incoming = ClusterItem(
            source=state.source,
            source_item_id=state.source_item_id,
            title=state.title,
            observed_at=state.first_received_at,
            published_at=state.published_at,
            subject_ids=tuple(security_ids),
            event_family="",
        )
        candidates, retrieval_evidence = self._cluster_candidates(incoming)
        decision = cluster_candidates(
            incoming,
            candidates,
            policy=self.cluster_policy,
        )
        retrieval_payload = retrieval_evidence.payload(decision=decision)
        cluster_id = decision.cluster_id
        if decision.action == "new":
            self._conn.execute(
                """
                INSERT INTO news_clusters(
                    cluster_id, anchor_story_id, anchor_title,
                    anchor_observed_at, subject_ids_json, event_family,
                    cluster_policy_version
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    cluster_id,
                    incoming.story_id,
                    incoming.title,
                    incoming.observed_at.isoformat(),
                    _stable_json(list(incoming.subject_ids)),
                    incoming.event_family,
                    cluster_policy_version(self.cluster_policy),
                ),
            )
            # Derived index for the fresh immutable anchor, same transaction.
            index_new_anchor(
                self._conn,
                cluster_id=cluster_id,
                title=incoming.title,
                security_ids=incoming.subject_ids,
                anchor_observed_at=incoming.observed_at,
            )
        if decision.action != "new":
            row = self._conn.execute(
                "SELECT subject_ids_json, anchor_title FROM news_clusters"
                " WHERE cluster_id=?",
                (cluster_id,),
            ).fetchone()
            current = (
                set(json.loads(row["subject_ids_json"])) if row else set()
            )
            subjects = current | set(security_ids)
            self._conn.execute(
                "UPDATE news_clusters SET subject_ids_json=? WHERE cluster_id=?",
                (_stable_json(sorted(subjects)), cluster_id),
            )
            self._expand_cluster_index(
                cluster_id=cluster_id,
                added_security_ids=set(security_ids) - current,
                anchor_title=None if row is None else str(row["anchor_title"]),
            )
        self._conn.execute(
            """
            INSERT INTO news_cluster_members(
                source, source_item_id, cluster_id, story_id, retrieval_json
            ) VALUES(?,?,?,?,?)
            """,
            (
                state.source,
                state.source_item_id,
                cluster_id,
                incoming.story_id,
                _stable_json(retrieval_payload),
            ),
        )
        return cluster_id

    def _expand_cluster_index(
        self,
        *,
        cluster_id: str,
        added_security_ids,
        anchor_title: str | None = None,
    ) -> None:
        """Postings for securities newly retained by a cluster's subject union.

        Same transaction as the union update. The anchor title is immutable;
        when the caller did not pass it, it is read from the cluster row.
        """
        added = set(added_security_ids)
        if not added:
            return
        row = self._conn.execute(
            "SELECT anchor_title, anchor_observed_at FROM news_clusters WHERE cluster_id=?",
            (cluster_id,),
        ).fetchone()
        title = anchor_title if anchor_title is not None else str(row["anchor_title"])
        index_subject_expansion(
            self._conn,
            cluster_id=cluster_id,
            title=title,
            added_security_ids=added,
            anchor_observed_at=datetime.fromisoformat(str(row["anchor_observed_at"])),
        )

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

    def _security_ids_for_item(
        self, source: str, source_item_id: str
    ) -> tuple[str, ...]:
        rows = self._conn.execute(
            """
            SELECT security_id
            FROM news_security_index
            WHERE source=? AND source_item_id=?
            ORDER BY security_id
            """,
            (source, source_item_id),
        ).fetchall()
        return tuple(str(row["security_id"]) for row in rows)

    def _active_cluster_projection(
        self, cluster_id: str
    ) -> tuple[NewsRevision, tuple[str, ...], str] | None:
        """Latest active cluster representative plus all current target securities.

        Used only after current state/index mutation inside the same transaction.
        It prevents a withdrawal of one syndication member from projecting that
        withdrawn member's blank fields as the still-live cluster update.
        """
        rows = self._conn.execute(
            """
            SELECT s.source, s.source_item_id, s.current_revision_id,
                   s.last_sequence, s.universe_revision, r.revision_json
            FROM news_cluster_members m
            JOIN news_states s
              ON s.source=m.source AND s.source_item_id=m.source_item_id
            JOIN news_revisions r
              ON r.revision_id=s.current_revision_id
            WHERE m.cluster_id=? AND s.status='active'
            ORDER BY COALESCE(s.last_sequence, -1) DESC,
                     s.source, s.source_item_id
            """,
            (cluster_id,),
        ).fetchall()
        if not rows:
            return None
        representative = rows[0]
        security_rows = self._conn.execute(
            """
            SELECT DISTINCT i.security_id
            FROM news_cluster_members m
            JOIN news_states s
              ON s.source=m.source AND s.source_item_id=m.source_item_id
            JOIN news_security_index i
              ON i.source=s.source AND i.source_item_id=s.source_item_id
            WHERE m.cluster_id=? AND s.status='active'
            ORDER BY i.security_id
            """,
            (cluster_id,),
        ).fetchall()
        return (
            _revision_from_json(str(representative["revision_json"])),
            tuple(str(row["security_id"]) for row in security_rows),
            str(representative["universe_revision"]),
        )

    def _write_change(
        self,
        *,
        kind: str,
        revision: NewsRevision,
        cluster_id: str,
        security_ids: Sequence[str],
        universe_revision: str,
        observed_at: datetime | None = None,
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
                (observed_at or revision.received_at).isoformat(),
            ),
        )
        sequence = int(cur.lastrowid)
        for security_id in tuple(dict.fromkeys(security_ids)):
            self._conn.execute(
                """
                INSERT INTO news_change_targets(sequence, security_id)
                VALUES(?,?)
                """,
                (sequence, security_id),
            )
        return sequence

    def commit(
        self,
        revisions: Sequence[RoutedRevision],
        *,
        expected_cursor: str | None,
        next_cursor: str | None,
    ) -> CommitReceipt:
        self._require_write()
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

                previous_security_ids = self._security_ids_for_item(
                    revision.source, revision.source_item_id
                )
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

                projection_revision = revision
                projection_universe = item.universe_revision
                affected_security_ids = tuple(
                    sorted(set(previous_security_ids) | set(security_ids))
                )
                active_members = self._active_cluster_members(cluster_id)
                if (
                    reduction.disposition == "withdrawn"
                    and active_members > 0
                ):
                    projection = self._active_cluster_projection(cluster_id)
                    if projection is None:
                        raise NewsStoreError(
                            "qbus_news_store:active_cluster_projection_missing"
                        )
                    (
                        projection_revision,
                        current_cluster_security_ids,
                        projection_universe,
                    ) = projection
                    affected_security_ids = tuple(
                        sorted(
                            set(affected_security_ids)
                            | set(current_cluster_security_ids)
                        )
                    )
                    kind = "upsert"
                elif reduction.disposition == "withdrawn":
                    kind = "remove"
                else:
                    kind = "upsert"

                sequence = self._write_change(
                    kind=kind,
                    revision=projection_revision,
                    cluster_id=cluster_id,
                    security_ids=affected_security_ids,
                    universe_revision=projection_universe,
                    observed_at=revision.received_at,
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

    @_read_snapshot
    def snapshot(
        self,
        security_id: str,
        *,
        limit: int,
        cursor: int | None,
        rights: NewsReadRights,
    ) -> NewsSnapshot:
        security_id = _validate_token(security_id, "security_id", 1024)
        self._check_editorial_security(security_id)
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
        # This first SELECT fixes the SQLite read view used by cluster selection
        # and member projection. It is an opaque delivery cursor, independent of
        # the visible page's group ordering and pagination boundary.
        change_sequence = int(self._conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM news_changes"
        ).fetchone()[0])
        if not self._read_sources(rights):
            return NewsSnapshot(SCHEMA, security_id, (), cursor, False, change_sequence)

        placeholders = ",".join("?" for _ in self._read_sources(rights))
        curated_clause, curated_params = self._curated_clause(rights)
        params: list[object] = [
            security_id,
            *sorted(self._read_sources(rights)),
            security_id,
            *curated_params,
            *sorted(self._read_sources(rights)),
        ]
        having_cursor = ""
        if cursor is not None:
            having_cursor = " HAVING cluster_sequence < ?"
            params.append(cursor)
        params.append(limit + 1)
        # The cluster watermark is the latest change sequence addressed to THIS
        # security for that cluster, not MAX over the surviving members.  A
        # partial withdrawal deletes the withdrawn member's index rows, so a
        # member-only aggregate would fall back to the survivors and move the
        # watermark DOWN, re-feeding an already-paged cluster and reporting a
        # row sequence below the withdrawal upsert the security just received.
        # The change log is append-only, so the feed watermark can only move
        # forward, exactly like a correction.  Visibility stays member-based:
        # the FROM/WHERE still requires at least one active member indexed to
        # this security, so a fully withdrawn cluster stays invisible.  The
        # COALESCE fallback to the member aggregate keeps a hand-migrated
        # store readable if a visible cluster predates its change targets.
        clusters = self._conn.execute(
            f"""
            SELECT m.cluster_id,
                   COALESCE(MAX(w.change_sequence), MAX(s.last_sequence))
                       AS cluster_sequence
            FROM news_security_index i
            JOIN news_states s
              ON s.source=i.source AND s.source_item_id=i.source_item_id
            JOIN news_cluster_members m
              ON m.source=s.source AND m.source_item_id=s.source_item_id
            JOIN news_state_projection p
              ON p.source=s.source AND p.source_item_id=s.source_item_id
            LEFT JOIN (
                SELECT c.cluster_id, MAX(c.sequence) AS change_sequence
                FROM news_change_targets t
                JOIN news_changes c ON c.sequence=t.sequence
                WHERE t.security_id=?
                  AND c.source IN ({placeholders})
                GROUP BY c.cluster_id
            ) w ON w.cluster_id=m.cluster_id
            WHERE i.security_id=?
              AND s.status='active'
                  {curated_clause}
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

        # Fetch every selected cluster's active members in one query.  The old
        # implementation issued one SELECT per story (N+1), which made 100-reader
        # bursts spend ~1s in SQLite even though the index lookup itself was fast.
        # Keep cluster selection/order above unchanged; this query only materializes
        # the already-selected members.
        members_by_cluster: dict[str, list[sqlite3.Row]] = {}
        if selected:
            selected_ids = [str(cluster["cluster_id"]) for cluster in selected]
            cluster_placeholders = ",".join("?" for _ in selected_ids)
            member_rows = self._conn.execute(
                f"""
                SELECT m.cluster_id, s.last_sequence, s.universe_revision,
                       s.source, s.source_item_id,
                       p.title, p.url, p.teaser,
                       p.published_at, p.updated_at, p.received_at
                FROM news_cluster_members m
                JOIN news_states s
                  ON s.source=m.source AND s.source_item_id=m.source_item_id
                JOIN news_state_projection p
                  ON p.source=s.source AND p.source_item_id=s.source_item_id
                JOIN news_security_index i
                  ON i.source=s.source AND i.source_item_id=s.source_item_id
                WHERE i.security_id=?
                  AND s.status='active'
                  {curated_clause}
                  AND s.source IN ({placeholders})
                  AND m.cluster_id IN ({cluster_placeholders})
                ORDER BY m.cluster_id, s.last_sequence DESC,
                         s.source, s.source_item_id
                """,
                (
                    security_id,
                    *curated_params,
                    *sorted(self._read_sources(rights)),
                    *selected_ids,
                ),
            ).fetchall()
            for row in member_rows:
                members_by_cluster.setdefault(
                    str(row["cluster_id"]), []
                ).append(row)

        for cluster in selected:
            cluster_id = str(cluster["cluster_id"])
            members = members_by_cluster.get(cluster_id, [])
            if not members:
                continue
            comparison = reporting_state(members, rights)
            comparison_sources = tuple(sorted({
                str(member["source"]) for member in members
                if rights.allows(str(member["source"]), "title") and member["title"]
            }))
            representative = representatives_in_display_order(members, rights, comparison=comparison)[0]
            out.append(
                _projection_story(
                    sequence=int(cluster["cluster_sequence"]),
                    row=representative,
                    story_id=cluster_id,
                    source_count=len(
                        {publisher_identity(str(member["source"]), str(member["url"])) for member in members}
                    ),
                    item_count=len(members),
                    universe_revision=str(
                        representative["universe_revision"]
                    ),
                    rights=rights,
                    comparison=comparison,
                    comparison_sources=comparison_sources,
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
            change_sequence=change_sequence,
        )


    def evidence_for_security(self, security_id: str, *, limit: int, rights: NewsReadRights) -> dict:
        """Bounded permitted text with exact current revisions for downstream use.

        Caller owns audience/use admission. The transaction binds the selected
        stories, field projection and revision references to one read snapshot.
        """
        own_transaction = not self._conn.in_transaction
        if own_transaction:
            self._conn.execute("BEGIN")
        try:
            snapshot = self.snapshot(security_id, limit=limit, cursor=None, rights=rights)
            stories = []
            remaining_text = 32000
            text_limited = False
            for item in snapshot.rows:
                detail = self.story(item.story_id, rights=rights, security_id=security_id)
                if detail is None:
                    continue
                reports = []
                for member in detail.members[:10]:
                    state = self._load_state(member.source, member.source_item_id)
                    if state is None or state.status != "active":
                        continue
                    if len(member.title) > remaining_text:
                        text_limited = True
                        break
                    teaser = member.teaser[:min(2000, remaining_text-len(member.title))]
                    remaining_text -= len(member.title) + len(teaser)
                    reports.append({
                        "source": member.source, "source_item_id": member.source_item_id,
                        "revision_id": state.current_revision_id,
                        "member_sequence": member.sequence, "title": member.title,
                        "url": member.url, "teaser": teaser,
                        "teaser_truncated": len(member.teaser) > len(teaser),
                        "published_at": member.published_at.isoformat() if member.published_at else None,
                        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
                        "source_event_at": state.source_event_at.isoformat() if state.source_event_at else None,
                        "received_at": member.received_at.isoformat(),
                        "version_clock_domain": state.version_clock_domain,
                    })
                if not reports:
                    break
                stories.append({
                    "story_id": item.story_id, "story_sequence": item.sequence,
                    "source_count": detail.source_count, "item_count": detail.item_count,
                    "reporting_state": detail.reporting_state,
                    "reports_truncated": detail.item_count > len(reports), "reports": reports,
                })
            return {"stories": stories, "has_more": snapshot.has_more or text_limited}
        finally:
            if own_transaction:
                self._conn.execute("ROLLBACK")

    def news_flow(
        self,
        security_id: str,
        *,
        now: datetime,
        rights: NewsReadRights,
    ) -> dict:
        """Return one security's complete ``ticker_news.flow.v1`` dict.

        Counts are computed on a dedicated read-only connection, never on
        ``self._conn``, so a store opened writable still serves flow without
        touching its write path. Failures raise; the API layer maps them.
        """
        security_id = _validate_token(security_id, "security_id", 1024)
        self._check_editorial_security(security_id)
        if not isinstance(rights, NewsReadRights):
            raise StoreValidationError("qbus_news_store:invalid_rights")
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("now must be a timezone-aware datetime")
        if not self._read_sources(rights):
            flow: dict = {
                "schema": "ticker_news.flow.v1",
                "state": "unavailable",
                "reason": "no_accessible_sources",
                "coverage": "complete",
                "as_of": None,
                "reports_24h": None,
                "reports_7d": None,
                "stories_24h": None,
                "median_daily_28d": None,
                "daily_counts_28d": None,
                "history_days_observed": None,
                "comparison": None,
                "provenance": None,
            }
            return flow

        as_of = now.astimezone(timezone.utc).replace(microsecond=0)
        conn = self._open_flow_connection()
        try:
            velocity = compute_news_velocity(
                conn,
                security_id=security_id,
                now=as_of,
                allowed_sources=self._read_sources(rights),
                curated=self._curated,
                allowed_url_sources=tuple(
                    source for source in self._read_sources(rights) if rights.allows(source, "url")
                ),
                allowed_teaser_sources=tuple(
                    source for source in self._read_sources(rights) if rights.allows(source, "teaser")
                ),
                editorial_view=self._editorial_view,
            )
        finally:
            conn.close()

        sufficient = bool(velocity["sufficient_history"])
        median = velocity["median_daily_28d"]
        as_of_date = as_of.date()
        provenance = {
            "velocity_schema": VELOCITY_SCHEMA,
            **({"editorial_policy": EDITORIAL_POLICY_VERSION} if self._curated else {}),
            **({"editorial_view": self._editorial_view.metadata()} if self._editorial_view else {}),
            "sources_counted": velocity["sources_counted"],
            "status_counted": "active",
            "distinct_by": "source + source_item_id",
            "story_grouping": (
                "news_cluster_members.cluster_id; "
                "a report in no cluster is its own story"
            ),
            "cluster_policy_version": _cluster_policy_label(
                velocity["cluster_policy_versions_24h"],
                self._in_force_cluster_policy_version(),
            ),
            "windows": {
                "reports_24h": (
                    "rolling, closed at both ends: [as_of - 24h, as_of]"
                ),
                "reports_7d": (
                    "rolling, closed at both ends: [as_of - 7d, as_of]"
                ),
                "daily_28d": {
                    "start_date": (as_of_date - timedelta(days=28)).isoformat(),
                    "end_date": (as_of_date - timedelta(days=1)).isoformat(),
                    "unit": "UTC calendar day",
                    "excludes": "the current UTC day",
                    "order": "oldest first",
                },
            },
            "calculation": {
                "method": METHOD,
                "comparison_rule": FLOW_COMPARE_RULE,
            },
            "time_basis_counts_24h": velocity["basis_counts_24h"],
        }
        return {
            "schema": "ticker_news.flow.v1",
            "state": "ok" if sufficient else "thin_history",
            "reason": None,
            "coverage": "complete",
            "as_of": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reports_24h": velocity["count_24h"],
            "reports_7d": velocity["count_7d"],
            "stories_24h": velocity["stories_24h"],
            "median_daily_28d": median,
            "daily_counts_28d": velocity["daily_counts_28d"],
            "history_days_observed": velocity["history_days_observed"],
            "comparison": compare_to_typical(
                velocity["count_24h"], median, sufficient, "complete"
            ),
            "provenance": provenance,
        }

    def _open_flow_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            f"file:{urllib.parse.quote(str(self.path))}?mode=ro",
            uri=True,
            timeout=5.0,
            isolation_level=None,
        )
        conn.execute("PRAGMA query_only=ON")
        return conn

    def story(
        self,
        story_id: str,
        *,
        rights: NewsReadRights,
        security_id: str | None = None,
    ) -> StoryDetail | None:
        story_id = _validate_token(story_id, "story_id", 1024)
        company = self._editorial_view.company if self._editorial_view else None
        if company is not None:
            security_id = security_id or company.security_id
            self._check_editorial_security(security_id)
        if not isinstance(rights, NewsReadRights):
            raise StoreValidationError("qbus_news_store:invalid_rights")
        if not self._read_sources(rights):
            return None
        security_filter = ""
        curated_clause, curated_params = self._curated_clause(rights)
        params = [story_id, *curated_params, *sorted(self._read_sources(rights))]
        if security_id is not None:
            security_id = _validate_token(security_id, "security_id", 1024)
            self._check_editorial_security(security_id)
            security_filter = """AND EXISTS (
                SELECT 1 FROM news_security_index i
                WHERE i.source=s.source AND i.source_item_id=s.source_item_id
                  AND i.security_id=?
            )"""
            params.append(security_id)
        placeholders = ",".join("?" for _ in self._read_sources(rights))
        rows = self._conn.execute(
            f"""
            SELECT s.source, s.source_item_id, s.last_sequence,
                   s.universe_revision, p.title, p.url, p.teaser,
                   p.published_at, p.updated_at, p.received_at
            FROM news_cluster_members m
            JOIN news_states s
              ON s.source=m.source AND s.source_item_id=m.source_item_id
            JOIN news_state_projection p
              ON p.source=s.source AND p.source_item_id=s.source_item_id
            WHERE m.cluster_id=?
              AND s.status='active'
                  {curated_clause}
              AND s.source IN ({placeholders})
              {security_filter}
            ORDER BY s.last_sequence DESC, s.source, s.source_item_id
            """,
            tuple(params),
        ).fetchall()
        if not rows:
            return None
        comparison = reporting_state(rows, rights)
        comparison_sources = tuple(sorted({
            str(row["source"]) for row in rows
            if rights.allows(str(row["source"]), "title") and row["title"]
        }))
        rows = representatives_in_display_order(rows, rights, comparison=comparison)
        source_count = len({publisher_identity(str(row["source"]), str(row["url"])) for row in rows})
        item_count = len(rows)
        members = tuple(
            _projection_story(
                sequence=int(row["last_sequence"] or 0),
                row=row,
                story_id=story_id,
                source_count=source_count,
                item_count=item_count,
                universe_revision=str(row["universe_revision"]),
                rights=rights,
                comparison=comparison,
                comparison_sources=comparison_sources,
            )
            for row in rows
        )
        return StoryDetail(
            schema=SCHEMA,
            story_id=story_id,
            source_count=source_count,
            item_count=item_count,
            members=members,
            reporting_state=comparison,
        )

    def changes_for_security(
        self,
        security_id: str,
        *,
        after_sequence: int,
        limit: int,
        rights: NewsReadRights,
    ) -> ChangePage:
        security_id = _validate_token(security_id, "security_id", 1024)
        self._check_editorial_security(security_id)
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
        if not self._read_sources(rights):
            return ChangePage(SCHEMA, (), after_sequence, False)

        placeholders = ",".join("?" for _ in self._read_sources(rights))
        rows = self._conn.execute(
            f"""
            SELECT c.*, r.revision_json
            FROM news_change_targets t
            JOIN news_changes c ON c.sequence=t.sequence
            JOIN news_revisions r ON r.revision_id=c.revision_id
            WHERE t.security_id=?
              AND c.sequence > ?
              AND c.source IN ({placeholders})
            ORDER BY c.sequence ASC
            LIMIT ?
            """,
            (
                security_id,
                after_sequence,
                *sorted(self._read_sources(rights)),
                limit + 1,
            ),
        ).fetchall()
        return self._change_page(rows, after_sequence=after_sequence, limit=limit, rights=rights)

    def projected_changes_for_security(
        self, security_id: str, *, after_sequence: int, limit: int,
        rights: NewsReadRights,
    ) -> ChangePage:
        """Project live invalidations through the same audience view as snapshots.

        The immutable change journal remains available for audits. UI consumers
        receive the current eligible representative, never the raw last-arriving
        report. Coalesce within this bounded page; cursor advancement still covers
        every consumed journal row, including several updates of one story.
        """
        # Keep journal invalidations and current rows in one SQLite read snapshot.
        own_transaction = not self._conn.in_transaction
        if own_transaction:
            self._conn.execute("BEGIN")
        try:
            page = self.changes_for_security(
                security_id, after_sequence=after_sequence, limit=limit, rights=rights,
            )
            latest = {row.story_id: row for row in page.rows}
            # Match snapshot's per-security, allowed-source group ordering.
            # The consumed journal row can precede this current projection.
            group_sequences = {}
            if latest:
                source_marks = ",".join("?" for _ in self._read_sources(rights))
                group_marks = ",".join("?" for _ in latest)
                group_sequences = {
                    str(item["cluster_id"]): int(item["sequence"])
                    for item in self._conn.execute(
                        f"""
                        SELECT c.cluster_id, MAX(c.sequence) AS sequence
                        FROM news_change_targets t
                        JOIN news_changes c ON c.sequence=t.sequence
                        WHERE t.security_id=?
                          AND c.source IN ({source_marks})
                          AND c.cluster_id IN ({group_marks})
                        GROUP BY c.cluster_id
                        """,
                        (security_id, *sorted(self._read_sources(rights)), *latest),
                    ).fetchall()
                }
            projected = []
            for row in sorted(latest.values(), key=lambda item: item.sequence):
                detail = self.story(row.story_id, rights=rights, security_id=security_id)
                if detail is None:
                    projected.append(replace(row, kind="remove", title="", url="", teaser="", projection_sequence=None))
                    continue
                best = detail.members[0]
                projected.append(replace(
                    row, kind="upsert", source=best.source, source_item_id=best.source_item_id,
                    projection_sequence=group_sequences.get(
                        row.story_id, max(member.sequence for member in detail.members),
                    ),
                    title=best.title, url=best.url, teaser=best.teaser,
                    source_count=detail.source_count, item_count=detail.item_count,
                    published_at=best.published_at, updated_at=best.updated_at,
                    received_at=best.received_at, universe_revision=best.universe_revision,
                    reporting_state=detail.reporting_state,
                    reporting_sources=best.reporting_sources,
                ))
            return ChangePage(page.schema, tuple(projected), page.next_sequence, page.has_more)
        finally:
            if own_transaction:
                self._conn.execute("ROLLBACK")

    def _change_page(
        self,
        rows,
        *,
        after_sequence: int,
        limit: int,
        rights: NewsReadRights,
    ) -> ChangePage:
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
                    title="" if removed or not rights.allows(revision.source, "title") else display_text(revision.title),
                    url="" if removed or not rights.allows(revision.source, "url") else revision.url,
                    teaser="" if removed or not rights.allows(revision.source, "teaser") else display_text(revision.teaser),
                    security_ids=tuple(json.loads(row["security_ids_json"])),
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
        return self._change_page(
            rows,
            after_sequence=after_sequence,
            limit=limit,
            rights=rights,
        )
