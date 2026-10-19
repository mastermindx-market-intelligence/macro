"""research_vault.corpus — standalone FTS5 search index (corpus.sqlite).

Full-text search over research documents: title + summary + BODY + institution.
The API loads this DB from R2 into the VPS with a TTL cache for read-only queries.

House law CXI-R23: this is a SEPARATE corpus that only borrows the *code* from
``engine/context_index`` — it NEVER imports, opens, or queries the CXI databases,
and PDFs are NEVER added as CXI sources. The FTS5 contentless-table + trigger
pattern is copied from ``context_index/schema.py`` and the BM25 query + sanitizer
from ``context_index/lexical.py``.

Column weights (masterplan §8): title=4, summary=3, body=1.
Facets (institution, date) are indexed columns on the ``documents`` table →
compound ``WHERE`` alongside the FTS ``MATCH``. stdlib + sqlite3 only.

Schema v2 adds the engine-MEASURED columns from :mod:`research_vault.probe`
(page count, text-layer density, content hash, PDF provenance, page-1 text).
They are metadata only — deliberately NOT added to the FTS table: ``first_page_text``
is a prefix of ``body``, so indexing it would double-count those postings and
silently reweight every BM25 score. Exactly one of them, ``text_layer``, is also
projected by :func:`get_document` (see :data:`DOCUMENT_FIELDS`): it is the field
that tells a consumer holding an empty ``body`` whether the document HAS no text
('none') or whether our extraction merely did not reach it ('unavailable'/'').

The bottom of this module holds the PROCESS-WIDE read-through cache
(:func:`corpus_connection`) and the by-id reader (:func:`get_document`) that both
``app/research.py`` and the Mastermind brain read through — see the block comment
above them for why the cache lives here rather than in the router.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import tempfile
import threading
import time
import unicodedata
from pathlib import Path

log = logging.getLogger("research_vault.corpus")

# ---------------------------------------------------------------------------
# DDL — contentless FTS5 + sync triggers (copied idiom: context_index/schema.py)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 2

_DDL = """
-- Rollback-journal (single-file) mode, NOT WAL: the corpus is written in one
-- hourly batch then the WHOLE .sqlite file is published to R2, so every commit
-- must land in the main file (no -wal/-shm sidecars whose writes would be lost
-- when only the main file is uploaded). Read-only API access needs no WAL.
PRAGMA journal_mode=DELETE;

-- Public-safe document metadata + the body text kept ONLY for search (never in
-- the catalog). rowid links to the contentless FTS table below.
CREATE TABLE IF NOT EXISTS documents (
    rowid          INTEGER PRIMARY KEY,
    doc_id         TEXT UNIQUE NOT NULL,
    title          TEXT,
    summary        TEXT,
    institution    TEXT,
    side           TEXT,
    published_at   TEXT,
    published_date TEXT,          -- YYYY-MM-DD facet (compound WHERE)
    body           TEXT
);

CREATE INDEX IF NOT EXISTS idx_rv_docs_inst ON documents(institution);
CREATE INDEX IF NOT EXISTS idx_rv_docs_date ON documents(published_date);

-- FTS5 contentless table; triggers below maintain all postings explicitly (same
-- reasoning as CXI: avoids the external-content rebuild/integrity-check path).
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title,
    summary,
    body,
    institution,
    content=''
);

CREATE TRIGGER IF NOT EXISTS rv_docs_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, summary, body, institution)
    VALUES (new.rowid, new.title, new.summary, new.body, new.institution);
END;

CREATE TRIGGER IF NOT EXISTS rv_docs_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, summary, body, institution)
    VALUES ('delete', old.rowid,
            COALESCE(old.title, ''), COALESCE(old.summary, ''),
            COALESCE(old.body, ''), COALESCE(old.institution, ''));
END;

CREATE TRIGGER IF NOT EXISTS rv_docs_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, summary, body, institution)
    VALUES ('delete', old.rowid,
            COALESCE(old.title, ''), COALESCE(old.summary, ''),
            COALESCE(old.body, ''), COALESCE(old.institution, ''));
    INSERT INTO documents_fts(rowid, title, summary, body, institution)
    VALUES (new.rowid, new.title, new.summary, new.body, new.institution);
END;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# Engine-measured columns (schema v2), declared EXACTLY ONCE and applied by
# ALTER TABLE in :func:`_migrate` on every open — never inline in the CREATE
# TABLE above.
#
# Why migration-only rather than "new columns in the DDL plus a migration for old
# files": ``CREATE TABLE IF NOT EXISTS`` is a no-op against the v1 corpus that
# :func:`ingest._restore_corpus` pulls from R2 at the start of every run, so the
# DDL alone would leave the live database on v1 while the INSERT below named v2
# columns — an OperationalError inside ``_ingest_one``'s catch-all, i.e. every
# document silently marked "failed". Declaring them in one place, applied through
# one idempotent path, removes that whole failure mode.
_V2_COLUMNS: tuple[tuple[str, str], ...] = (
    ("pages", "INTEGER"),
    ("language", "TEXT"),
    ("char_count", "INTEGER"),
    ("word_count", "INTEGER"),
    ("text_layer", "TEXT"),
    ("content_sha256", "TEXT"),
    ("byte_size", "INTEGER"),
    ("pdf_creator", "TEXT"),
    ("pdf_producer", "TEXT"),
    ("pdf_created_at", "TEXT"),
    ("pdf_modified_at", "TEXT"),
)

# Deliberately NOT a column: ``first_page_text``. ``body`` is truncated at the
# TAIL (BODY_MAX_CHARS), so page 1 is always inside the row we already store —
# downstream extractors read it via :func:`research_vault.probe.first_page` over
# ``body`` instead. A separate column would duplicate ~4KB per row in a file the
# API pulls whole on every corpus refresh.

# bm25(documents_fts, w_title, w_summary, w_body, w_institution) — §8 weights.
_BM25_WEIGHTS = "4.0, 3.0, 1.0, 2.0"

_EXCERPT_LEN = 240

# Per-document body-text cap. The corpus ships to R2 and is pulled whole by the
# API, so unbounded body text (40-page PDFs ≈ 100KB+ each) would balloon the
# .sqlite into hundreds of MB across a multi-thousand-doc backfill. 60KB keeps
# roughly the first 15-25 pages searchable — headline/thesis/core argument —
# while bounding the file. Raise deliberately if deep-tail search matters more
# than transfer size.
BODY_MAX_CHARS = 60_000


# ---------------------------------------------------------------------------
# R1B source-bound evidence passages — pure projection over one entitled row
# ---------------------------------------------------------------------------
# This is deliberately NOT another index. The existing corpus is the retrieval
# authority and its stored `body` is the exact text surface this selector reads.
# Normalization exists only for locating a user's words; every emitted passage is
# sliced from the original body so width, case, punctuation and source language
# remain the publisher's, not ours.
EVIDENCE_PASSAGE_LIMIT = 3
EVIDENCE_WINDOW_CHARS = 900

_EVIDENCE_HAN_RANGE = (
    r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f"
)
_EVIDENCE_HAN_RE = re.compile("[" + _EVIDENCE_HAN_RANGE + "]+")
_EVIDENCE_RAW_ATOM_RE = re.compile(
    r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*|[" + _EVIDENCE_HAN_RANGE + "]+"
)
_EVIDENCE_WORD_RE = re.compile(r"[a-z0-9]{2,}")
_EVIDENCE_STOPWORDS = frozenset({
    "about", "after", "again", "also", "among", "an", "and", "are", "as",
    "at", "be", "because", "before", "being", "between", "both", "but",
    "by", "can", "could", "did", "do", "does", "doing", "for", "from",
    "had", "has", "have", "how", "if", "in", "into", "is", "it", "its",
    "may", "me", "more", "most", "no", "not", "of", "on", "or", "our",
    "should", "so", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "to", "under", "us",
    "very", "was", "we", "were", "what", "when", "where", "which", "why",
    "will", "with", "would", "you", "your",
})


def _evidence_normalize_with_map(value) -> tuple[str, list[int]]:
    """NFKC/casefold text plus a normalized-index → original-index map.

    Whitespace runs collapse to one ASCII space so a phrase still matches across
    PDF line breaks. The map points every normalized codepoint back to the source
    character that produced it (including casefold expansions such as ß → ss).
    It is used only to recover exact source slices; normalized text is never
    returned to a caller.
    """
    source = str(value or "")
    out: list[str] = []
    origins: list[int] = []
    for index, char in enumerate(source):
        piece = unicodedata.normalize("NFKC", char).casefold()
        for normalized in piece:
            if normalized.isspace():
                if out and out[-1] != " ":
                    out.append(" ")
                    origins.append(index)
            else:
                out.append(normalized)
                origins.append(index)
    return "".join(out), origins


def _evidence_identifier(raw: str) -> bool:
    """The exact identifier shapes already admitted by Brain R1A."""
    if "." in raw:
        return True
    parts = raw.split("-")
    return (
        len(parts) == 2
        and 1 <= len(parts[0]) <= 5
        and len(parts[1]) == 1
        and parts[0].isalnum()
        and parts[1].isalpha()
    )


def _evidence_atoms(query) -> tuple[str, ...]:
    """Ordered, de-duplicated meaningful atoms for passage support."""
    normalized, _ = _evidence_normalize_with_map(query)
    atoms: list[str] = []

    def add(atom: str) -> None:
        if len(atom) >= 2 and atom not in _EVIDENCE_STOPWORDS and atom not in atoms:
            atoms.append(atom)

    for raw in _EVIDENCE_RAW_ATOM_RE.findall(normalized):
        if _EVIDENCE_HAN_RE.fullmatch(raw) or _evidence_identifier(raw):
            add(raw)
        else:
            for word in _EVIDENCE_WORD_RE.findall(raw):
                add(word)
    return tuple(atoms)


def evidence_query_is_meaningful(query) -> bool:
    """Whether the selector treats ``query`` as a passage-evidence request."""
    return bool(_evidence_atoms(query))


def _ascii_alnum_boundary(char: str) -> bool:
    """True when ``char`` is an ASCII letter/digit that can extend an ASCII
    identifier. Han (and other non-ASCII) characters are NOT boundary-blocking
    for an ASCII needle — ``.isalnum()`` alone returns True for Han, which would
    otherwise reject a Latin ticker/acronym embedded in Chinese prose."""
    return char.isascii() and char.isalnum()


def _iter_evidence_hits(text: str, needle: str):
    """Yield normalized [start,end) hits with exact ASCII identifier boundaries.

    An ASCII needle (ticker, acronym) may sit directly against Han script on
    either side — Han is not an ASCII identifier continuation — but a longer
    ASCII sibling (``AAPLX`` for a ``AAPL`` needle) still correctly blocks it.
    """
    if not needle:
        return
    start = 0
    bounded = needle.isascii()
    while True:
        found = text.find(needle, start)
        if found < 0:
            return
        end = found + len(needle)
        if not bounded or (
            (found == 0 or not _ascii_alnum_boundary(text[found - 1]))
            and (end == len(text) or not _ascii_alnum_boundary(text[end]))
        ):
            yield found, end
        start = found + max(1, len(needle))


def _original_span(origins: list[int], start: int, end: int) -> tuple[int, int] | None:
    if start < 0 or end <= start or end > len(origins):
        return None
    return origins[start], origins[end - 1] + 1


def _evidence_body_text(value) -> str:
    """Accept publisher body text only when it is already a string.

    Coercing a dict, list, tuple, number, or boolean with ``str()`` would create
    searchable Python syntax that the publisher never wrote. Malformed bodies
    therefore become honestly unavailable rather than fabricated evidence.
    """
    return value if isinstance(value, str) else ""


def _bounded_window_chars(value) -> int:
    """Return one literal-int evidence window inside the frozen safe interval."""
    if type(value) is int:
        return max(80, min(EVIDENCE_WINDOW_CHARS, value))
    return EVIDENCE_WINDOW_CHARS


def _evidence_int(value) -> int | None:
    """A literal nonnegative JSON/Python integer, never a coercible lookalike."""
    return value if type(value) is int and value >= 0 else None


def _source_binding(document: dict, body: str) -> dict:
    source_chars = _evidence_int(document.get("char_count"))
    stored_chars = len(body)
    if (source_chars is None or (source_chars == 0 and stored_chars > 0)
            or source_chars < stored_chars):
        coverage, tail_omitted = "unknown", None
    elif source_chars > stored_chars:
        coverage, tail_omitted = "prefix_partial", True
    else:
        coverage, tail_omitted = "complete", False
    digest = document.get("content_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        digest = ""
    pages = _evidence_int(document.get("pages"))
    return {
        "content_sha256": digest,
        "stored_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "coverage": coverage,
        "source_char_count": source_chars if coverage != "unknown" else None,
        "stored_char_count": stored_chars,
        "tail_omitted": tail_omitted,
        "text_layer": str(document.get("text_layer") or ""),
        "page_count": pages if pages and pages > 0 else None,
    }


def _passage_bounds(body: str, match_start: int, match_end: int,
                    window_chars: int) -> tuple[int, int]:
    """A bounded source slice centered on the match and confined to its PDF page.

    ``cap`` is independent of match length — an arbitrarily long single atom
    (e.g. one unsegmented Han run) must never make the emitted window grow past
    the configured budget; the match itself is clamped to the window by the
    caller when it exceeds ``cap``.
    """
    cap = _bounded_window_chars(window_chars)
    page_start, page_end = 0, len(body)
    if "\f" in body:
        previous = body.rfind("\f", 0, match_start)
        following = body.find("\f", match_end)
        page_start = previous + 1 if previous >= 0 else 0
        page_end = following if following >= 0 else len(body)
    room = max(0, cap - (match_end - match_start))
    start = max(page_start, match_start - room // 2)
    end = min(page_end, start + cap)
    if end - start < cap:
        start = max(page_start, end - cap)
    while start < match_start and body[start].isspace():
        start += 1
    while end > match_end and body[end - 1].isspace():
        end -= 1
    return start, end


def find_evidence_passages(
    document: dict,
    query,
    *,
    limit: int = EVIDENCE_PASSAGE_LIMIT,
    window_chars: int = EVIDENCE_WINDOW_CHARS,
) -> dict:
    """Return query-centered, source-bound passages from one entitled corpus row.

    Matching is deterministic NFKC/casefold lexical retrieval. ASCII atoms use
    exact word/identifier boundaries; Han phrases use literal substring matching.
    Page numbers are emitted only when the stored extraction contains form-feed
    boundaries from pdftotext; otherwise the locator honestly remains a text span.
    No score, confidence or model judgment is produced.
    """
    row = document if isinstance(document, dict) else {}
    body = _evidence_body_text(row.get("body"))
    window_chars = _bounded_window_chars(window_chars)
    atoms = _evidence_atoms(query)
    binding = _source_binding(row, body)
    base = {
        "query": str(query or ""),
        "passages": [],
        "source_binding": binding,
    }
    # A source-bound passage requires a canonical source-PDF fingerprint. Missing,
    # empty, malformed, non-string, or wrong-length content_sha256 fails CLOSED —
    # no passage or publisher body text, regardless of query shape — rather than
    # serving text this row cannot prove came from the fingerprinted PDF.
    if not binding["content_sha256"]:
        return {"status": "body_unavailable", **base}
    if not atoms:
        return {"status": "query_too_short", **base}
    if not body:
        return {"status": "body_unavailable", **base}

    normalized, origins = _evidence_normalize_with_map(body)
    occurrences: dict[str, list[tuple[int, int, int, int]]] = {}
    for atom in atoms:
        hits: list[tuple[int, int, int, int]] = []
        for norm_start, norm_end in _iter_evidence_hits(normalized, atom):
            source_span = _original_span(origins, norm_start, norm_end)
            if source_span is not None:
                hits.append((norm_start, norm_end, source_span[0], source_span[1]))
        occurrences[atom] = hits

    phrase = " ".join(atoms)
    candidates: dict[tuple[int, int], dict] = {}
    phrase_terms = list(atoms)
    if len(atoms) > 1:
        for norm_start, norm_end in _iter_evidence_hits(normalized, phrase):
            source_span = _original_span(origins, norm_start, norm_end)
            if source_span is None:
                continue
            candidates[source_span] = {
                "start": source_span[0], "end": source_span[1],
                "phrase": True, "anchor_terms": phrase_terms,
            }
    for atom in atoms:
        for _ns, _ne, source_start, source_end in occurrences[atom]:
            candidates.setdefault((source_start, source_end), {
                "start": source_start, "end": source_end,
                "phrase": False, "anchor_terms": [atom],
            })
    if not candidates:
        return {"status": "no_matching_passage", **base}

    ranked: list[tuple[tuple, dict]] = []
    for candidate in candidates.values():
        p_start, p_end = _passage_bounds(
            body, candidate["start"], candidate["end"], window_chars)
        supported = [
            atom for atom in atoms
            if any(not (end <= p_start or start >= p_end)
                   for _ns, _ne, start, end in occurrences[atom])
        ]
        candidate.update({"passage_start": p_start, "passage_end": p_end,
                          "supported": supported})
        key = (-int(candidate["phrase"]), -len(supported), candidate["start"],
               -(candidate["end"] - candidate["start"]))
        ranked.append((key, candidate))
    ranked.sort(key=lambda row_: row_[0])

    passages: list[dict] = []
    selected_ranges: list[tuple[int, int]] = []
    cap = max(1, min(EVIDENCE_PASSAGE_LIMIT, int(limit)))
    page_count = binding["page_count"]
    for _key, candidate in ranked:
        p_start, p_end = candidate["passage_start"], candidate["passage_end"]
        if any(not (p_end <= start or p_start >= end) for start, end in selected_ranges):
            continue
        # An atom longer than the window (one unsegmented Han run, say) must not
        # widen the emitted window — clamp the match span to it so the locator
        # stays coherent (start <= match_start < match_end <= end) and match_text
        # never exceeds the bounded passage text.
        match_start = max(candidate["start"], p_start)
        match_end = min(candidate["end"], p_end)
        locator = {
            "kind": "text_span",
            "start_char": p_start,
            "end_char": p_end,
            "match_start_char": match_start,
            "match_end_char": match_end,
        }
        if "\f" in body:
            page = body.count("\f", 0, candidate["start"]) + 1
            if page_count is None or page <= page_count:
                locator["kind"] = "page_text_span"
                locator["page"] = page
        passages.append({
            "text": body[p_start:p_end],
            "match_text": body[match_start:match_end],
            "matched_terms": candidate["supported"],
            "locator": locator,
        })
        selected_ranges.append((p_start, p_end))
        if len(passages) >= cap:
            break

    return {"status": "matched", **base, "passages": passages}



# ---------------------------------------------------------------------------
# FTS5 query sanitization (copied idiom: context_index/lexical._sanitize_fts5)
# ---------------------------------------------------------------------------

_FTS5_OPERATORS = re.compile(r"\b(AND|OR|NOT)\b")
_FTS5_SPECIAL = re.compile(r"[(){}\[\]^*\"'\\]")


def sanitize_fts5(query: str) -> str:
    """Free-text user query → safe FTS5 MATCH expression.

    Strips FTS5 boolean operators + special chars, wraps each token as an exact
    phrase, ORs them, and adds a full-phrase variant when >1 token. Returns ''
    for empty/degenerate input (caller must then return no results, not MATCH '').
    """
    if not query or not query.strip():
        return ""
    text = _FTS5_OPERATORS.sub(" ", query)
    text = _FTS5_SPECIAL.sub(" ", text)
    tokens = [t for t in text.split() if len(t) >= 2]
    safe = [t.replace('"', "") for t in tokens]
    safe = [t for t in safe if t]
    if not safe:
        return ""
    parts = [f'"{t}"' for t in safe]
    if len(safe) > 1:
        parts.append('"' + " ".join(safe) + '"')
    return " OR ".join(parts)


# ---------------------------------------------------------------------------
# open / build
# ---------------------------------------------------------------------------

def _existing_columns(conn: sqlite3.Connection, table: str = "documents") -> set[str]:
    """Column names currently on ``table`` ({} when the table is absent)."""
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.Error:
        return set()


def _migrate(conn: sqlite3.Connection) -> list[str]:
    """Add any missing :data:`_V2_COLUMNS` to ``documents``. Idempotent.

    Runs on EVERY open, so a fresh database and a v1 corpus restored from R2 both
    converge on the same shape. Returns the column names actually added (empty on
    an already-current database). A single failed ALTER is logged and skipped
    rather than raised: a corpus that is merely missing an enrichment column must
    still ingest and still serve search.
    """
    have = _existing_columns(conn)
    if not have:  # no documents table (should not happen — DDL ran first)
        return []
    added: list[str] = []
    for name, decl in _V2_COLUMNS:
        if name in have:
            continue
        try:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {name} {decl}")
            added.append(name)
        except sqlite3.Error as exc:
            log.warning("research_vault corpus: ALTER for %s failed (%s)", name, exc)
    if "content_sha256" in have or "content_sha256" in added:
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rv_docs_sha "
                         "ON documents(content_sha256)")
        except sqlite3.Error as exc:
            log.warning("research_vault corpus: sha index failed (%s)", exc)
    if added:
        conn.commit()
        log.info("research_vault corpus: migrated to v%d (+%d columns)",
                 SCHEMA_VERSION, len(added))
    return added


def open_db(path: str | Path) -> sqlite3.Connection:
    """Open (or create) corpus.sqlite, apply DDL + migrations, stamp the version."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    _migrate(conn)
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('schema_version',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------

def summary_text(item: dict) -> str:
    """The ``summary`` FTS column value for a catalog/sidecar item.

    Defined once because TWO paths write it: :func:`upsert` at ingest, and
    ``ingest._refresh_sidecars`` when a late-arriving sidecar summary is folded
    into a row that was already published. A separate join in either place would
    let the two drift into different searchable text for the same bullets.
    """
    return " • ".join(item.get("summary_points") or [])


def upsert(conn: sqlite3.Connection, item: dict, body_text: str,
           facts: dict | None = None) -> None:
    """Insert/replace one document's searchable row.

    ``item`` is a normalized sidecar item (see sidecar.normalize). ``body_text``
    is the pdftotext-extracted body ('' when extraction failed — the row is still
    searchable by title/summary). ``facts`` is the optional engine-measured bundle
    (:func:`research_vault.probe.probe` + :func:`~research_vault.probe.text_facts`
    + ``first_page_text``); absent → the v2 columns stay NULL, which is the honest
    "not measured" state.

    Delete-then-insert keeps the FTS postings in sync via the triggers (a bare
    REPLACE would not fire the delete trigger for the old body). The column list
    is built from the columns the database ACTUALLY has, so a corpus whose
    migration partially failed still ingests every document instead of raising
    per row. Never raises on a benign duplicate.
    """
    doc_id = item.get("id") or ""
    published_at = item.get("published_at") or ""

    row: dict = {
        "doc_id": doc_id,
        "title": item.get("title") or "",
        "summary": summary_text(item),
        "institution": item.get("institution") or "",
        "side": item.get("side") or "",
        "published_at": published_at,
        "published_date": published_at[:10] if len(published_at) >= 10 else "",
        "body": (body_text or "")[:BODY_MAX_CHARS],
    }

    if facts:
        for name, _decl in _V2_COLUMNS:
            if name in facts:
                row[name] = facts[name]
        # ``language`` and ``pages`` live on the normalized item, not the probe.
        row.setdefault("language", item.get("language") or "")
        row.setdefault("pages", item.get("pages"))

    have = _existing_columns(conn)
    cols = [c for c in row if c in have] if have else list(row)
    placeholders = ",".join("?" for _ in cols)

    conn.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
    conn.execute(
        f"INSERT INTO documents ({','.join(cols)}) VALUES ({placeholders})",
        [row[c] for c in cols],
    )
    conn.commit()


def sha_index(conn: sqlite3.Connection) -> dict[str, str]:
    """``{content_sha256: doc_id}`` for every hashed document. Never raises.

    Used to REPORT byte-identical duplicates at ingest. Deliberately not used to
    skip them: the same PDF legitimately re-arrives with a corrected sidecar, and
    skipping on a hash match would freeze the original bad metadata in place.
    Returns {} on a pre-v2 corpus where the column does not exist.
    """
    if "content_sha256" not in _existing_columns(conn):
        return {}
    try:
        rows = conn.execute(
            "SELECT content_sha256, doc_id FROM documents "
            "WHERE content_sha256 IS NOT NULL AND content_sha256 <> ''"
        ).fetchall()
    except sqlite3.Error:
        return {}
    return {r[0]: r[1] for r in rows}


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def _excerpt(text: str, limit: int = _EXCERPT_LEN) -> str:
    text = " ".join((text or "").split())
    return text[:limit] + ("…" if len(text) > limit else "")


def search(
    conn: sqlite3.Connection,
    q: str,
    institution: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """FTS5 BM25 search with optional institution + date-range facets.

    Returns ranked rows (best first) as dicts:
      {id, title, institution, side, published_at, summary, excerpt, rank}.
    The excerpt is drawn from the summary when present, else the body. Facet-only
    queries (empty ``q`` but an institution/date filter) are supported via a plain
    metadata scan. Returns [] on empty/degenerate input. Never raises.
    """
    fts = sanitize_fts5(q)
    where: list[str] = []
    params: list = []

    if institution:
        where.append("d.institution = ?")
        params.append(institution)
    if date_from:
        where.append("d.published_date >= ?")
        params.append(date_from[:10])
    if date_to:
        where.append("d.published_date <= ?")
        params.append(date_to[:10])

    try:
        if fts:
            sql = f"""
                SELECT d.doc_id, d.title, d.institution, d.side, d.published_at,
                       d.summary, d.body,
                       bm25(documents_fts, {_BM25_WEIGHTS}) AS score
                FROM documents_fts
                JOIN documents d ON d.rowid = documents_fts.rowid
                WHERE documents_fts MATCH ?
                {(' AND ' + ' AND '.join(where)) if where else ''}
                ORDER BY score
                LIMIT ?
            """
            rows = conn.execute(sql, [fts, *params, limit]).fetchall()
        else:
            # No text query: facet-only listing (newest first).
            if not where:
                return []
            sql = f"""
                SELECT d.doc_id, d.title, d.institution, d.side, d.published_at,
                       d.summary, d.body, 0.0 AS score
                FROM documents d
                WHERE {' AND '.join(where)}
                ORDER BY d.published_at DESC
                LIMIT ?
            """
            rows = conn.execute(sql, [*params, limit]).fetchall()
    except sqlite3.OperationalError:
        # Malformed MATCH or missing table — degrade to empty.
        return []

    out: list[dict] = []
    for r in rows:
        summary = r["summary"] or ""
        out.append({
            "id": r["doc_id"],
            "title": r["title"] or "",
            "institution": r["institution"] or "",
            "side": r["side"] or "",
            "published_at": r["published_at"] or "",
            "summary": summary,
            "excerpt": _excerpt(summary or r["body"]),
            "rank": float(r["score"]),
        })
    return out


def institutions(conn: sqlite3.Connection) -> list[str]:
    """Distinct institutions present in the corpus (sorted)."""
    rows = conn.execute(
        "SELECT DISTINCT institution FROM documents WHERE institution <> '' ORDER BY institution"
    ).fetchall()
    return [r["institution"] for r in rows]


# ---------------------------------------------------------------------------
# read-through cache + by-id reader — ONE local copy per process (W4)
# ---------------------------------------------------------------------------
# The corpus lives ONLY in R2. Until W4 the single fetcher was
# ``app/research.py::_corpus_conn``; the Mastermind brain's Pro full-report answer
# needs the same bytes and runs in the SAME FastAPI process (app/main.py imports
# brain_gateway lazily in the request path), so a second private cache there would
# mean two multi-MB downloads, two TTL clocks, and two writers racing over the one
# temp file. The machinery therefore lives here and the router delegates.
#
# ENGINE-SIDE ONLY: this module must never import ``app/*``. The store comes from
# ``research_vault.r2_store.build_store`` (the same env precedence the router used)
# or from a caller-supplied factory — the router passes its own, which is what its
# tests monkeypatch.
#
# Serve-stale-while-revalidate, unchanged from the router's original: a present
# local copy is served immediately; past the TTL exactly one background thread
# re-downloads it; only the very first call on a cold process blocks.

CORPUS_KEY = "research_vault/corpus.sqlite"   # mirrors ingest CORPUS_KEY
CORPUS_TTL = 300.0                            # seconds — local copy refresh age
CORPUS_LOCK = threading.Lock()                # guards the three globals below
_CACHE_DIRNAME = "research_vault_corpus"

_corpus_path: Path | None = None
_corpus_fetched_at: float = 0.0
_corpus_refreshing: bool = False  # guarded by CORPUS_LOCK — one refresher at a time

# The slug shape ``sidecar.slug`` produces, copied from app/research._DOC_ID_RE
# INCLUDING its anchors: ``\A``/``\Z``, never ``^``/``$`` — a ``$`` also matches
# just before a trailing newline, so "valid-id\n" would clear a ``$``-anchored
# check. Any id failing this never reaches a SQL parameter or an R2 key.
_DOC_ID_RE = re.compile(r"\A[a-z0-9][a-z0-9-]{0,120}\Z")

# The EXACT key set :func:`get_document` returns. Literal, like every other
# projection in this repo: a column added to ``documents`` later (the v2 probe
# bundle, say) cannot reach a caller — or a chat context — without someone editing
# this tuple and tripping tests/test_research_vault.py.
#
# ``text_layer`` is the ONE measured column that made the cut, because an empty
# ``body`` is ambiguous without it and every consumer has to explain the shortfall
# to a user: 'none' means the extractor ran and the document genuinely has no
# machine-readable text (a scan — there is nothing more to serve, ever), while
# 'unavailable'/'' means OUR extraction did not run or has not been retried yet
# (temporary, and ingest._reextract_bodies is repairing it). Saying "not reachable
# right now" about a scan is a false promise; saying "this is all there is" about
# a host outage is a false ceiling.
DOCUMENT_FIELDS: tuple[str, ...] = (
    "doc_id", "title", "institution", "side", "published_at", "summary", "body",
    "text_layer",
)
EVIDENCE_DOCUMENT_FIELDS: tuple[str, ...] = DOCUMENT_FIELDS + (
    "pages", "char_count", "content_sha256",
)
_NUMERIC_DOCUMENT_FIELDS = frozenset({"pages", "char_count"})


def valid_doc_id(doc_id) -> bool:
    """True iff ``doc_id`` has the catalog slug shape (shape only, not existence).

    Existence is the CALLER's gate — the router checks the catalog, the brain
    checks the catalog. This is the cheap shape check that keeps traversal,
    uppercase, slashes and trailing newlines out of the query in the first place.
    """
    return isinstance(doc_id, str) and bool(_DOC_ID_RE.match(doc_id))


def _cache_dir() -> Path:
    """Directory holding the local corpus copy (a function so tests can repoint it)."""
    return Path(tempfile.gettempdir()) / _CACHE_DIRNAME


def _default_store():
    """The private research bucket via r2_store.build_store, or None. Never raises.

    Imported lazily so this module keeps importing (and every pure-sqlite function
    keeps working) on a box with no boto3.
    """
    try:
        from engine.research_vault.r2_store import build_store  # noqa: PLC0415
        return build_store()
    except Exception as exc:  # noqa: BLE001 — no store → no corpus, never a raise
        log.debug("research_vault: store unavailable (%s)", exc)
        return None


def _resolve_store(store_factory):
    """Call the caller's factory (or the default) and swallow its failures."""
    try:
        return (store_factory or _default_store)()
    except Exception as exc:  # noqa: BLE001
        log.debug("research_vault: store factory failed (%s)", exc)
        return None


def _refresh_from_store(store_factory=None) -> Path | None:
    """Download corpus.sqlite to the local cache path (SYNCHRONOUS). Never raises.

    Returns the local path on success, None on any failure. Called inline only
    when no local copy exists yet; otherwise it runs on a background thread so a
    user's search never pays the multi-MB download (the corpus grows with the
    archive — a backfilled corpus is far too large to fetch inside a request).

    The store read is inside the try, unlike the router's original: a boto3
    exception used to propagate out of the route (a 500), which contradicts
    app/research.py's own never-raise-at-the-boundary invariant.
    """
    global _corpus_path, _corpus_fetched_at
    store = _resolve_store(store_factory)
    if store is None:
        return None
    try:
        data = store.get_bytes(CORPUS_KEY)
    except Exception as exc:  # noqa: BLE001 — a dead bucket degrades to no corpus
        log.debug("research_vault: corpus fetch failed (%s)", exc)
        return None
    if not data:
        return None
    try:
        tmp_dir = _cache_dir()
        tmp_dir.mkdir(parents=True, exist_ok=True)
        dst = tmp_dir / "corpus.sqlite"
        tmp = dst.with_suffix(".sqlite.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, dst)
        with CORPUS_LOCK:
            _corpus_path = dst
            _corpus_fetched_at = time.monotonic()
        return dst
    except Exception as exc:  # noqa: BLE001 — write failure → degrade
        log.debug("research_vault: corpus refresh failed (%s)", exc)
        return None


def _refresh_bg(store_factory=None) -> None:
    """Background-thread wrapper: refresh, then clear the in-flight flag."""
    global _corpus_refreshing
    try:
        _refresh_from_store(store_factory)
    finally:
        with CORPUS_LOCK:
            _corpus_refreshing = False


def corpus_connection(store_factory=None):
    """Open the shared local corpus copy, refreshing it WITHOUT blocking the caller.

    Returns a sqlite3 connection (caller closes it) or None. Never raises. A
    present local copy is served immediately; when it is older than
    :data:`CORPUS_TTL` a single background thread re-downloads it (dropped, not
    queued, if one is already in flight). Only the very first call on a cold
    process — no local copy at all — downloads inline.
    """
    global _corpus_refreshing
    now = time.monotonic()

    with CORPUS_LOCK:
        have_local = _corpus_path is not None and _corpus_path.exists()
        stale = not have_local or (now - _corpus_fetched_at) >= CORPUS_TTL
        path = _corpus_path
        if have_local and stale and not _corpus_refreshing:
            _corpus_refreshing = True
            threading.Thread(target=_refresh_bg, args=(store_factory,), daemon=True,
                             name="rv-corpus-refresh").start()

    if not have_local:
        # First fetch ever on this process: nothing to serve yet — block once.
        path = _refresh_from_store(store_factory)
        if path is None:
            return None

    try:
        return open_db(path)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001 — unreadable local copy → degrade
        log.debug("research_vault: corpus open failed (%s)", exc)
        return None


def reset_cache() -> None:
    """Forget the local copy (tests only — production never calls this).

    The cache is process-wide by design, so a test that seeds its own store must
    be able to drop a copy a previous test fetched; otherwise the first fetch of
    the session would decide what every later test reads.
    """
    global _corpus_path, _corpus_fetched_at, _corpus_refreshing
    with CORPUS_LOCK:
        _corpus_path = None
        _corpus_fetched_at = 0.0
        _corpus_refreshing = False


def _read_document_fields(doc_id: str, fields: tuple[str, ...],
                          store_factory=None) -> dict | None:
    """Read one whitelisted projection from the shared corpus. Never raises.

    Optional v2 columns are selected only when the corpus actually carries them;
    a partially migrated file therefore returns honest empty/None metadata instead
    of making the entire document disappear.
    """
    if not valid_doc_id(doc_id):
        return None
    try:
        conn = corpus_connection(store_factory=store_factory)
    except Exception as exc:  # noqa: BLE001 — belt; corpus_connection degrades already
        log.debug("research_vault: corpus connection failed (%s)", exc)
        return None
    if conn is None:
        return None

    available: set[str] = set()
    row = None
    try:
        available = _existing_columns(conn)
        selected = [field for field in fields if field in available]
        if not selected or "doc_id" not in selected:
            return None
        row = conn.execute(
            f"SELECT {','.join(selected)} FROM documents WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()
    except Exception as exc:  # noqa: BLE001 — corrupt/partial copy → no document
        log.debug("research_vault: document read failed (%s)", exc)
        return None
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass

    if row is None:
        return None
    result: dict = {}
    for field in fields:
        if field not in available:
            result[field] = None if field in _NUMERIC_DOCUMENT_FIELDS else ""
            continue
        value = row[field]
        result[field] = value if field in _NUMERIC_DOCUMENT_FIELDS else (value or "")
    return result


def get_document(doc_id: str, store_factory=None) -> dict | None:
    """One document's legacy body projection by id, or None. Never raises.

    The exact :data:`DOCUMENT_FIELDS` contract is intentionally unchanged. Body is
    the pdftotext extraction capped at :data:`BODY_MAX_CHARS`; ``text_layer``
    distinguishes an image-only scan (``none``) from a temporary/unmeasured
    extraction shortfall. All degraded cases return None so callers can fall back
    to public excerpts without leaking an internal failure.
    """
    return _read_document_fields(doc_id, DOCUMENT_FIELDS, store_factory=store_factory)


def get_evidence_document(doc_id: str, store_factory=None) -> dict | None:
    """Entitled R1B projection with only the metadata needed to bind passages.

    It extends the same row and cache owner as :func:`get_document`; it is not a
    second corpus or retrieval plane. ``pages`` enables a real page locator when
    the body has form-feed boundaries, ``char_count`` discloses prefix coverage,
    and ``content_sha256`` binds the passage to the exact source PDF bytes.
    """
    return _read_document_fields(
        doc_id, EVIDENCE_DOCUMENT_FIELDS, store_factory=store_factory
    )
