"""SQLite state store — the pipeline's memory + dedup index.

Functional style: every function takes an open ``sqlite3.Connection`` as its first
argument so it is trivial to unit-test against a temp/in-memory DB.

Dedup keys (all enforced UNIQUE at the DB level): ``article_url``, ``blob_url``,
``blob_id``, ``sha256``. SQLite treats NULLs as distinct, so pre-download rows (sha256
NULL) coexist fine.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime as _datetime, timedelta as _timedelta, timezone as _timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from .schemas import ArticleMeta, Status

if TYPE_CHECKING:
    from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    article_url           TEXT UNIQUE,
    blob_url              TEXT UNIQUE,
    blob_id               TEXT UNIQUE,
    title                 TEXT,
    institution           TEXT,
    published_at          TEXT,
    marketdesk_age_text   TEXT,
    marketdesk_summary    TEXT,
    local_priority_score  INTEGER,
    sha256                TEXT UNIQUE,
    page_count            INTEGER,
    parser                TEXT,
    pdf_filename          TEXT,
    markdown_filename     TEXT,
    metadata_filename     TEXT,
    r2_pdf_key            TEXT,
    r2_markdown_key       TEXT,
    r2_metadata_key       TEXT,
    dropbox_pdf_path      TEXT,
    vault_key             TEXT,
    vaulted_at            TEXT,
    status                TEXT,
    error_message         TEXT,
    discovered_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    downloaded_at         TEXT,
    parsed_at             TEXT,
    uploaded_at           TEXT,
    updated_at            TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_papers_status       ON papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_published_at ON papers(published_at);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# columns callers may update via update_fields()
_UPDATABLE = {
    "title", "institution", "published_at", "marketdesk_age_text",
    "marketdesk_summary", "local_priority_score", "sha256", "page_count", "parser",
    "pdf_filename", "markdown_filename", "metadata_filename", "r2_pdf_key",
    "r2_markdown_key", "r2_metadata_key", "dropbox_pdf_path", "vault_key",
    "vaulted_at", "status", "account",
    "error_message", "downloaded_at", "parsed_at", "uploaded_at",
}

# Columns added after the initial schema shipped. `CREATE TABLE IF NOT EXISTS`
# will NOT add columns to a pre-existing DB, so init_db() applies these additively
# (idempotent — guarded against the current PRAGMA table_info).
_MIGRATION_COLUMNS: dict[str, str] = {
    "vault_key": "TEXT",   # Research Vault sidecar id (marketdesk-<blob_id>) once published
    "vaulted_at": "TEXT",  # ISO timestamp of the successful vault publish
    "account": "TEXT",     # which trickle account downloaded this paper (rolling-ledger key)
}


def connect(database_url: str | Path) -> sqlite3.Connection:
    path = Path(database_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate_columns(conn)
    conn.commit()


def _migrate_columns(conn: sqlite3.Connection) -> None:
    """Add post-initial-schema columns to a pre-existing ``papers`` table.

    Idempotent: only adds a column that is not already present (checked via
    ``PRAGMA table_info``). New DBs already have the columns from SCHEMA, so this
    is a no-op there.
    """
    have = {r["name"] for r in conn.execute("PRAGMA table_info(papers)").fetchall()}
    for col, decl in _MIGRATION_COLUMNS.items():
        if col not in have:
            conn.execute(f"ALTER TABLE papers ADD COLUMN {col} {decl}")


# --- meta KV (last_successful_run, etc.) -----------------------------------
def get_meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


# --- dedup lookups ---------------------------------------------------------
def get_by_blob_id(conn: sqlite3.Connection, blob_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM papers WHERE blob_id=?", (blob_id,)).fetchone()


def exists_blob_id(conn: sqlite3.Connection, blob_id: str) -> bool:
    return get_by_blob_id(conn, blob_id) is not None


def exists_article_url(conn: sqlite3.Connection, article_url: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM papers WHERE article_url=? LIMIT 1", (article_url,)
    ).fetchone() is not None


def find_sha256_owner(
    conn: sqlite3.Connection, sha256: str, exclude_blob_id: str | None = None
) -> sqlite3.Row | None:
    """Return an existing row with this sha256 (optionally excluding one blob_id)."""
    if exclude_blob_id:
        return conn.execute(
            "SELECT * FROM papers WHERE sha256=? AND blob_id<>? LIMIT 1",
            (sha256, exclude_blob_id),
        ).fetchone()
    return conn.execute(
        "SELECT * FROM papers WHERE sha256=? LIMIT 1", (sha256,)
    ).fetchone()


# --- writes ----------------------------------------------------------------
def upsert_discovered(conn: sqlite3.Connection, meta: ArticleMeta) -> tuple[int, bool]:
    """Insert a freshly discovered paper. Returns ``(row_id, is_new)``.

    Idempotent: re-discovering an existing paper refreshes light metadata
    (title/summary/age/score) but never regresses its ``status``.
    """
    existing = get_by_blob_id(conn, meta.blob_id)
    if existing is not None:
        conn.execute(
            "UPDATE papers SET title=?, institution=?, marketdesk_age_text=?, "
            "marketdesk_summary=COALESCE(?, marketdesk_summary), "
            "local_priority_score=COALESCE(?, local_priority_score), "
            "updated_at=CURRENT_TIMESTAMP WHERE blob_id=?",
            (
                meta.title, meta.institution, meta.marketdesk_age_text,
                meta.marketdesk_summary, meta.local_priority_score, meta.blob_id,
            ),
        )
        conn.commit()
        return int(existing["id"]), False

    published = meta.published_at.isoformat() if meta.published_at else None
    cur = conn.execute(
        "INSERT INTO papers (article_url, blob_url, blob_id, title, institution, "
        "published_at, marketdesk_age_text, marketdesk_summary, local_priority_score, "
        "status, discovered_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
        (
            meta.article_url, meta.blob_url, meta.blob_id, meta.title, meta.institution,
            published, meta.marketdesk_age_text, meta.marketdesk_summary,
            meta.local_priority_score, Status.DISCOVERED.value,
        ),
    )
    conn.commit()
    return int(cur.lastrowid), True


def update_fields(conn: sqlite3.Connection, blob_id: str, **fields: Any) -> None:
    """Update whitelisted columns for a paper; always bumps ``updated_at``."""
    cols = {k: v for k, v in fields.items() if k in _UPDATABLE}
    if not cols:
        return
    if isinstance(cols.get("status"), Status):
        cols["status"] = cols["status"].value
    sets = ", ".join(f"{k}=?" for k in cols) + ", updated_at=CURRENT_TIMESTAMP"
    conn.execute(
        f"UPDATE papers SET {sets} WHERE blob_id=?", (*cols.values(), blob_id)
    )
    conn.commit()


def set_status(
    conn: sqlite3.Connection, blob_id: str, status: Status | str,
    error_message: str | None = None,
) -> None:
    update_fields(
        conn, blob_id,
        status=status.value if isinstance(status, Status) else status,
        error_message=error_message,
    )


# --- queries ---------------------------------------------------------------
def get_by_status(
    conn: sqlite3.Connection, statuses: Iterable[Status | str]
) -> list[sqlite3.Row]:
    vals = [s.value if isinstance(s, Status) else s for s in statuses]
    q = ",".join("?" for _ in vals)
    return conn.execute(
        f"SELECT * FROM papers WHERE status IN ({q}) ORDER BY published_at DESC", vals
    ).fetchall()


def get_for_manifest_date(conn: sqlite3.Connection, date_str: str) -> list[sqlite3.Row]:
    """Rows whose published date (UTC) matches YYYY-MM-DD, most-recent first."""
    return conn.execute(
        "SELECT * FROM papers WHERE substr(published_at,1,10)=? "
        "ORDER BY published_at DESC",
        (date_str,),
    ).fetchall()


def counts_by_status(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT status, COUNT(*) c FROM papers GROUP BY status"
    ).fetchall()
    return {r["status"]: r["c"] for r in rows}


# --- Research Vault publishing ---------------------------------------------
def get_vault_pending(
    conn: sqlite3.Connection, limit: int | None = None
) -> list[sqlite3.Row]:
    """COMPLETE papers not yet published to the Research Vault (resumable).

    A paper is eligible once it has finished the pipeline (``status == COMPLETE``)
    and has not already been vaulted (``vaulted_at IS NULL``). Newest first.
    """
    q = (
        "SELECT * FROM papers WHERE status=? AND vaulted_at IS NULL "
        "ORDER BY published_at DESC"
    )
    params: tuple = (Status.COMPLETE.value,)
    if limit:
        q += " LIMIT ?"
        params = (Status.COMPLETE.value, limit)
    return conn.execute(q, params).fetchall()


def mark_vaulted(
    conn: sqlite3.Connection, blob_id: str, vault_key: str, vaulted_at: str
) -> None:
    """Record a successful vault publish (id + timestamp) for a paper."""
    update_fields(conn, blob_id, vault_key=vault_key, vaulted_at=vaulted_at)


# --- per-account rolling 24h download ledger (trickle allocator) -----------
# MarketDesk throttles downloads to a rolling 24h window PER ACCOUNT. Every
# successful download records BOTH ``downloaded_at`` (existing) and ``account``
# (which profile pulled it), so a plain COUNT over the trailing window is the
# live quota gauge. ``downloaded_at`` is written as ``utc_now().isoformat()``
# (tz-aware ISO-8601, always ``+00:00``), so an ISO cutoff string built the same
# way compares correctly with a lexicographic ``>=``.

def _iso_cutoff(now: "datetime", hours: float) -> str:
    return (now - _timedelta(hours=hours)).isoformat()


def trailing_24h_count(
    conn: sqlite3.Connection, account: str, now: "datetime", *, window_hours: float = 24.0
) -> int:
    """Downloads by ``account`` whose ``downloaded_at`` is within the trailing window.

    This is exactly what MarketDesk's rolling cap counts: a slot frees ~24h after
    each download ages out. ``window_hours`` is overridable only for testing.
    """
    cutoff = _iso_cutoff(now, window_hours)
    row = conn.execute(
        "SELECT COUNT(*) c FROM papers "
        "WHERE account=? AND downloaded_at IS NOT NULL AND downloaded_at >= ?",
        (account, cutoff),
    ).fetchone()
    return int(row["c"]) if row else 0


def available_quota(
    conn: sqlite3.Connection, account: str, cap: int, now: "datetime",
    *, window_hours: float = 24.0,
) -> int:
    """Remaining downloads for ``account`` before the rolling cap is re-tripped."""
    return max(0, cap - trailing_24h_count(conn, account, now, window_hours=window_hours))


def next_free_at(
    conn: sqlite3.Connection, account: str, now: "datetime", *, window_hours: float = 24.0
) -> "datetime | None":
    """When the account's OLDEST in-window download ages out — i.e. when the next
    slot frees. ``None`` if there are no in-window downloads (nothing to wait on).

    Used to set a self-calibrating cooldown when a download bounces on the cap:
    even if the configured cap is wrong, waiting until the oldest trailing-window
    download expires guarantees at least one freed slot.
    """
    cutoff = _iso_cutoff(now, window_hours)
    row = conn.execute(
        "SELECT MIN(downloaded_at) m FROM papers "
        "WHERE account=? AND downloaded_at IS NOT NULL AND downloaded_at >= ?",
        (account, cutoff),
    ).fetchone()
    if not row or not row["m"]:
        return None
    oldest = _parse_iso_ts(row["m"])
    if oldest is None:
        return None
    return oldest + _timedelta(hours=window_hours)


def _parse_iso_ts(s: str | None) -> "datetime | None":
    if not s:
        return None
    try:
        dt = _datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=_timezone.utc)
    except ValueError:
        return None
