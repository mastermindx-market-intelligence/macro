"""Issuer 8-K body minting for the wave-w2 news-impact benchmark.

For each drawn benchmark case (a headline about one issuer on one date) this
module finds the issuer's own 8-K filed inside a session band around the
headline, fetches the 8-K primary document and its EX-99 exhibits through the
existing SEC collectors, turns them into plain text, mints a byte-replayable
citation for each text, and reports per case whether a body is available or
why not.

Two band versions exist.  ``ni-edgar-body-1`` uses one session either side of
the seen session and is the default; its output is unchanged.
``ni-edgar-body-2`` keeps one session before and reaches four sessions after,
because a Form 8-K is due within four business days of the event it reports.
Version 2 requires an ``as_of`` date: a window whose last session is not
strictly before it may still gain filings and is refused as ``window_open``.
Version 2 also tags each filing with its session offset from the seen session.

Bytes reach this module only through the injected
``SecForensicsCollector`` and ``SecFilingArchiveCollector`` (S14).  All
document discovery, span minting, and the CLI in this module is pure with
respect to the wall clock; the archive collector's ``utc_now`` is the only
clock consulted.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from collectors.edgar_forensics import SecForensicsCollector
from collectors.sec_document_spine import (
    ArchiveReceipt,
    ArchiveResponseTooLarge,
    ArchiveStoreError,
    SecFilingArchiveCollector,
    read_archive_document,
)
from collectors.sec_request_pacer import SecRequestPacer
from engine.company_intelligence.documents import (
    DocumentError,
    FilingKey,
    SourceDocument,
    text_span,
    verify_span,
)


# ---------------------------------------------------------------------------
# S1 - constants and errors
# ---------------------------------------------------------------------------

EDGAR_BODY_VERSION = "ni-edgar-body-1"
EDGAR_BODY_VERSION_2 = "ni-edgar-body-2"
EDGAR_BODY_VERSIONS: tuple[str, ...] = (EDGAR_BODY_VERSION, EDGAR_BODY_VERSION_2)
# Sessions before and after the seen session that a qualifying 8-K may carry.
BODY_BANDS: dict[str, tuple[int, int]] = {
    EDGAR_BODY_VERSION: (1, 1),
    EDGAR_BODY_VERSION_2: (1, 4),
}
QUALIFYING_ITEMS: tuple[str, ...] = ("1.01", "2.02", "7.01", "8.01")
BODY_FORMS: tuple[str, ...] = ("8-K",)
EXHIBIT_TYPE_RE = re.compile(r"^EX-99(\.[0-9A-Z]+)?$", re.IGNORECASE)
BODY_SUFFIXES: tuple[str, ...] = (".htm", ".html", ".txt")
MAX_FILINGS_PER_CASE = 3
MAX_EXHIBITS_PER_FILING = 3
ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
MARKET_TZ = "America/New_York"
REASON_ORDER: tuple[str, ...] = (
    "no_cik",
    "calendar_gap",
    "submissions_failed",
    "no_qualifying_8k",
    "index_failed",
    "no_body_document",
    "fetch_failed",
    "document_missing",
    "too_large",
    "empty_text",
    "span_failed",
)
REASON_ORDER_V2: tuple[str, ...] = (
    REASON_ORDER[:2] + ("window_open",) + REASON_ORDER[2:]
)
REASON_ORDERS: dict[str, tuple[str, ...]] = {
    EDGAR_BODY_VERSION: REASON_ORDER,
    EDGAR_BODY_VERSION_2: REASON_ORDER_V2,
}
_REASON_RE = re.compile(r"^[a-z0-9_]+$")
for _reason in REASON_ORDER_V2:
    if not _REASON_RE.fullmatch(_reason):
        raise AssertionError(f"reason { _reason!r } does not match ^[a-z0-9_]+$")
_REASON_TO_INDEX = {name: idx for idx, name in enumerate(REASON_ORDER)}
_REASON_INDEXES: dict[str, dict[str, int]] = {
    version: {name: idx for idx, name in enumerate(order)}
    for version, order in REASON_ORDERS.items()
}
_MARKET_ZONE = ZoneInfo(MARKET_TZ)
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK_LABEL_RE = re.compile(r"^cik:(\d{10})$")
_SUMMARY_TABLE_RE = re.compile(
    r"<table\b[^>]*summary=\"Document Format Files\"[^>]*>",
    re.IGNORECASE,
)
_TABLE_FILE_RE = re.compile(
    r"<table\b[^>]*class=\"tableFile\"[^>]*>",
    re.IGNORECASE,
)
_TR_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
_TD_RE = re.compile(r"<td\b[^>]*>.*?</td>", re.IGNORECASE | re.DOTALL)
_TH_RE = re.compile(r"<th\b[^>]*>.*?</th>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_HREF_RE = re.compile(r"<a\b[^>]*href=\"([^\"]*)\"[^>]*>", re.IGNORECASE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_SCRIPT_RE = re.compile(
    r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL
)
_STYLE_RE = re.compile(
    r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL
)
_IX_HEADER_RE = re.compile(
    r"<ix:header\b[^>]*>.*?</ix:header>", re.IGNORECASE | re.DOTALL
)
_BLOCK_TAGS = ("br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table")
_BLOCK_END_RE = re.compile(
    r"</(" + "|".join(_BLOCK_TAGS) + r")\s*>", re.IGNORECASE
)
_WHITESPACE_RUN_RE = re.compile(r"[ \t]+")
_DATE_FIELDS = ("accessionDate", "filingDate")


class EdgarBodyError(ValueError):
    """A precondition for body minting was violated (bad input, bad state)."""


# ---------------------------------------------------------------------------
# S2 - parse_issuer_cik
# ---------------------------------------------------------------------------


def parse_issuer_cik(issuer: str) -> str | None:
    """Return the 10-digit CIK when ``issuer`` is a fully-canonical CIK label."""
    if not isinstance(issuer, str):
        return None
    match = _CIK_LABEL_RE.fullmatch(issuer)
    if match is None:
        return None
    return match.group(1)


# ---------------------------------------------------------------------------
# S3 - validate_sessions / session_window
# ---------------------------------------------------------------------------


def validate_sessions(session_dates: Sequence[date]) -> tuple[date, ...]:
    """Validate that ``session_dates`` is a non-empty strictly increasing list of dates."""
    if not isinstance(session_dates, (list, tuple)):
        raise EdgarBodyError("session_dates must be a list or tuple of dates")
    if len(session_dates) < 3:
        raise EdgarBodyError("session_dates must have at least 3 entries")
    cleaned: list[date] = []
    for index, entry in enumerate(session_dates):
        if isinstance(entry, datetime):
            raise EdgarBodyError(
                f"session_dates[{index}] must be a date, not a datetime"
            )
        if not isinstance(entry, date):
            raise EdgarBodyError(
                f"session_dates[{index}] must be a date instance"
            )
        cleaned.append(entry)
    for index in range(1, len(cleaned)):
        if cleaned[index] <= cleaned[index - 1]:
            raise EdgarBodyError("session_dates must be strictly increasing")
    return tuple(cleaned)


def _coerce_seendate(value: Any) -> datetime:
    """Parse a seendate value (ISO string with optional Z, or a datetime)."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise EdgarBodyError(f"seendate is not ISO-8601: {value!r}") from exc
    else:
        raise EdgarBodyError(f"seendate must be an ISO string or datetime: {value!r}")
    if parsed.tzinfo is None:
        raise EdgarBodyError("seendate must be timezone-aware")
    return parsed


def _seen_index(seendate: Any, sessions_t: Sequence[date]) -> int:
    """Index of the seen session: the first session on or after the market date."""
    parsed = _coerce_seendate(seendate)
    market = parsed.astimezone(_MARKET_ZONE)
    return bisect_left(sessions_t, market.date())


def _check_band(band: Any) -> tuple[int, int]:
    if (
        not isinstance(band, tuple)
        or len(band) != 2
        or not all(isinstance(n, int) and not isinstance(n, bool) for n in band)
        or band[0] < 1
        or band[1] < 1
    ):
        raise EdgarBodyError(f"band must be a pair of positive ints: {band!r}")
    return band


def session_window(
    seendate: Any, sessions: Sequence[date], band: tuple[int, int] = (1, 1)
) -> tuple[date, date, date] | None:
    """Map a seendate to the window ``(start, seen, end)``.

    ``band=(before, after)`` counts sessions either side of the seen session;
    the default ``(1, 1)`` is the version-1 window ``(prev, this, next)``.
    """
    before, after = _check_band(band)
    sessions_t = validate_sessions(sessions)
    a = _seen_index(seendate, sessions_t)
    if a - before < 0 or a + after >= len(sessions_t):
        return None
    return (sessions_t[a - before], sessions_t[a], sessions_t[a + after])


def filing_session_offset(
    filing_date: date, seendate: Any, sessions: Sequence[date]
) -> int:
    """Sessions from the seen session to the filing (a non-session date rolls forward)."""
    sessions_t = validate_sessions(sessions)
    return bisect_left(sessions_t, filing_date) - _seen_index(seendate, sessions_t)


def filing_relation(offset: int) -> str:
    """Name the filing's position relative to the seen session."""
    if offset < 0:
        return "filed_before_seen"
    if offset == 0:
        return "filed_same_session"
    return "filed_after_seen"


# ---------------------------------------------------------------------------
# S4 - FilingRow, parse_submissions, older_shards
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FilingRow:
    """One filing row extracted from a Submissions payload."""

    accession: str
    filing_date: date
    form: str
    items: tuple[str, ...]
    primary_document: str


def _read_field(payload: Mapping[str, Any], key: str) -> list[Any]:
    if key not in payload:
        raise EdgarBodyError(f"submissions array missing: {key!r}")
    value = payload[key]
    if not isinstance(value, list):
        raise EdgarBodyError(f"submissions array {key!r} is not a list")
    return value


def _parse_filing_date(text: Any) -> date:
    if not isinstance(text, str):
        raise EdgarBodyError(f"filingDate is not a string: {text!r}")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise EdgarBodyError(f"unparseable filingDate: {text!r}") from exc


def _split_items(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if not isinstance(value, str):
        raise EdgarBodyError(f"items is not a string: {value!r}")
    parts = tuple(part.strip() for part in value.split(","))
    return tuple(part for part in parts if part)


def _parse_rows(payload: Mapping[str, Any]) -> list[FilingRow]:
    accessions = _read_field(payload, "accessionNumber")
    filing_dates = _read_field(payload, "filingDate")
    forms = _read_field(payload, "form")
    items_list = _read_field(payload, "items")
    primaries = _read_field(payload, "primaryDocument")
    arrays = (accessions, filing_dates, forms, items_list, primaries)
    length = len(accessions)
    for other in arrays:
        if len(other) != length:
            raise EdgarBodyError("submissions arrays have unequal lengths")
    rows: list[FilingRow] = []
    for index in range(length):
        accession = accessions[index]
        if not isinstance(accession, str) or not _ACCESSION_RE.fullmatch(accession):
            raise EdgarBodyError(f"unparseable accession: {accession!r}")
        rows.append(
            FilingRow(
                accession=accession,
                filing_date=_parse_filing_date(filing_dates[index]),
                form=str(forms[index]) if forms[index] is not None else "",
                items=_split_items(items_list[index]),
                primary_document=str(primaries[index])
                if primaries[index] is not None
                else "",
            )
        )
    return rows


def parse_submissions(payload: Mapping[str, Any]) -> list[FilingRow]:
    """Parse either a current Submissions JSON or a historical shard JSON."""
    if not isinstance(payload, Mapping):
        raise EdgarBodyError("submissions payload must be a Mapping")
    recent = payload.get("filings", {}).get("recent") if isinstance(
        payload.get("filings"), Mapping
    ) else None
    if isinstance(recent, Mapping):
        return _parse_rows(recent)
    return _parse_rows(payload)


def older_shards(payload: Mapping[str, Any]) -> list[tuple[str, date, date]]:
    """Return ``(name, filingFrom, filingTo)`` for every older shard in the payload."""
    if not isinstance(payload, Mapping):
        raise EdgarBodyError("submissions payload must be a Mapping")
    files = payload.get("filings", {}).get("files") if isinstance(
        payload.get("filings"), Mapping
    ) else None
    if not isinstance(files, list):
        return []
    out: list[tuple[str, date, date]] = []
    for entry in files:
        if not isinstance(entry, Mapping):
            raise EdgarBodyError("older shard entry is not a Mapping")
        name = entry.get("name")
        filing_from = entry.get("filingFrom")
        filing_to = entry.get("filingTo")
        if not isinstance(name, str) or not name:
            raise EdgarBodyError("older shard entry missing name")
        out.append(
            (name, _parse_filing_date(filing_from), _parse_filing_date(filing_to))
        )
    return out


# ---------------------------------------------------------------------------
# S5 - qualifying_filings
# ---------------------------------------------------------------------------


def qualifying_filings(
    rows: Sequence[FilingRow], window: tuple[date, date, date]
) -> tuple[list[FilingRow], int]:
    """Return kept filings and the count truncated beyond ``MAX_FILINGS_PER_CASE``."""
    start, middle, end = window
    qualifying_items = set(QUALIFYING_ITEMS)
    body_forms = set(BODY_FORMS)
    kept: list[FilingRow] = []
    seen: set[str] = set()
    for row in rows:
        if row.form not in body_forms:
            continue
        if not (set(row.items) & qualifying_items):
            continue
        if not (start <= row.filing_date <= end):
            continue
        if row.accession in seen:
            continue
        seen.add(row.accession)
        kept.append(row)
    middle_date = middle
    kept.sort(
        key=lambda row: (
            abs((row.filing_date - middle_date).days),
            row.filing_date,
            row.accession,
        )
    )
    if len(kept) <= MAX_FILINGS_PER_CASE:
        return list(kept), 0
    truncated = len(kept) - MAX_FILINGS_PER_CASE
    return list(kept[:MAX_FILINGS_PER_CASE]), truncated


# ---------------------------------------------------------------------------
# S7 - URLs
# ---------------------------------------------------------------------------


def _cik_int(cik10: str) -> int:
    return int(cik10)


def index_url(cik10: str, accession: str) -> str:
    """Return the URL of the EDGAR filing index for ``accession``."""
    if not _ACCESSION_RE.fullmatch(accession):
        raise EdgarBodyError(f"invalid accession: {accession!r}")
    cik_natural = _cik_int(cik10)
    return (
        f"{ARCHIVES_BASE}/{cik_natural}/{accession.replace('-', '')}/"
        f"{accession}-index.htm"
    )


def document_url(cik10: str, accession: str, filename: str) -> str:
    """Return the URL of a single document inside the ``accession`` archive."""
    if not _ACCESSION_RE.fullmatch(accession):
        raise EdgarBodyError(f"invalid accession: {accession!r}")
    if not _FILENAME_RE.fullmatch(filename):
        raise EdgarBodyError(f"invalid document filename: {filename!r}")
    cik_natural = _cik_int(cik10)
    return (
        f"{ARCHIVES_BASE}/{cik_natural}/{accession.replace('-', '')}/{filename}"
    )


# ---------------------------------------------------------------------------
# S8 - parse_filing_index
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndexDocument:
    """One row extracted from an EDGAR filing-index page."""

    seq: str
    description: str
    filename: str
    doc_type: str


def _find_index_table(html: str) -> str | None:
    summary = _SUMMARY_TABLE_RE.search(html)
    if summary is not None:
        start = summary.end()
        end = _find_matching_close(html, start, "table")
        if end is not None:
            return html[start:end]
    fallback = _TABLE_FILE_RE.search(html)
    if fallback is not None:
        start = fallback.end()
        end = _find_matching_close(html, start, "table")
        if end is not None:
            return html[start:end]
    return None


def _find_matching_close(html: str, start: int, tag: str) -> int | None:
    pattern = re.compile(rf"</{tag}\s*>", re.IGNORECASE)
    match = pattern.search(html, start)
    if match is None:
        return None
    return match.end()


def _cell_text(raw: str) -> str:
    stripped = _TAG_RE.sub("", raw)
    text = unescape(stripped)
    text = _WHITESPACE_RUN_RE.sub(" ", text)
    return text.strip()


def _cell_filename(raw: str) -> str:
    href = _HREF_RE.search(raw)
    if href is None:
        return ""
    value = href.group(1)
    if value.startswith("/ix?doc="):
        value = value[len("/ix?doc=") :]
    if "/" in value:
        value = value.rsplit("/", 1)[-1]
    return value


def _parse_index_rows(table_html: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for tr_match in _TR_RE.finditer(table_html):
        tr_inner = tr_match.group(0)
        if _TH_RE.search(tr_inner):
            continue
        tds = _TD_RE.findall(tr_inner)
        if len(tds) < 4:
            continue
        seq = _cell_text(tds[0])
        description = _cell_text(tds[1])
        filename = _cell_filename(tds[2])
        doc_type = _cell_text(tds[3])
        rows.append((seq, description, filename, doc_type))
    return rows


def parse_filing_index(html_text: str) -> list[IndexDocument]:
    """Return one ``IndexDocument`` per row in the EDGAR filing index table."""
    if not isinstance(html_text, str):
        return []
    table = _find_index_table(html_text)
    if table is None:
        return []
    out: list[IndexDocument] = []
    for seq, description, filename, doc_type in _parse_index_rows(table):
        if not filename:
            continue
        out.append(
            IndexDocument(
                seq=seq,
                description=description,
                filename=filename,
                doc_type=doc_type,
            )
        )
    return out


# ---------------------------------------------------------------------------
# S9 - select_body_documents
# ---------------------------------------------------------------------------


def _ends_with_any(text: str, suffixes: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(lowered.endswith(suffix) for suffix in suffixes)


def select_body_documents(
    index_docs: Sequence[IndexDocument], primary_document: str
) -> list[IndexDocument]:
    """Pick the primary 8-K document and up to 3 EX-99 exhibits in index order."""
    body_suffixes = [suffix.lower() for suffix in BODY_SUFFIXES]
    primary = next(
        (doc for doc in index_docs if doc.filename == primary_document), None
    )
    if primary is None:
        primary = next(
            (doc for doc in index_docs if doc.doc_type == "8-K"), None
        )
    if primary is not None and not _ends_with_any(primary.filename, body_suffixes):
        primary = None
    selected: list[IndexDocument] = []
    if primary is not None:
        selected.append(primary)
    exhibits: list[IndexDocument] = []
    for doc in index_docs:
        if primary is not None and doc is primary:
            continue
        if not EXHIBIT_TYPE_RE.fullmatch(doc.doc_type):
            continue
        if not _ends_with_any(doc.filename, body_suffixes):
            continue
        exhibits.append(doc)
        if len(exhibits) >= MAX_EXHIBITS_PER_FILING:
            break
    return selected + exhibits


# ---------------------------------------------------------------------------
# S10 - html_to_text
# ---------------------------------------------------------------------------


def _decode_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def html_to_text(raw: bytes) -> str:
    """Turn an SEC 8-K HTML body into a deterministic plain-text rendering."""
    text = _decode_bytes(raw)
    text = _HTML_COMMENT_RE.sub("", text)
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)
    text = _IX_HEADER_RE.sub("", text)
    text = _BLOCK_END_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    lines: list[str] = []
    for line in text.split("\n"):
        collapsed = _WHITESPACE_RUN_RE.sub(" ", line).strip()
        if collapsed:
            lines.append(collapsed)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# S11 - per-document minting + memoisation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _IndexOutcome:
    reason: str | None  # None means the index was parsed successfully.


@dataclass(frozen=True)
class _DocumentOutcome:
    reason: str | None
    text: str | None
    text_sha256: str | None
    text_bytes: int | None
    receipt_id: str | None
    content_sha256: str | None
    byte_length: int | None
    span_id: str | None
    source_document: SourceDocument | None
    document_kind_doc: IndexDocument | None


def _write_text(out_dir: Path, text_sha256: str, text_bytes: bytes) -> None:
    texts_dir = out_dir / "texts"
    texts_dir.mkdir(parents=True, exist_ok=True)
    target = texts_dir / f"{text_sha256}.txt"
    if not target.exists():
        target.write_bytes(text_bytes)


def _empty_outcome() -> _DocumentOutcome:
    return _DocumentOutcome(
        reason="span_failed",
        text=None,
        text_sha256=None,
        text_bytes=None,
        receipt_id=None,
        content_sha256=None,
        byte_length=None,
        span_id=None,
        source_document=None,
        document_kind_doc=None,
    )


def _fetch_index(
    archive: SecFilingArchiveCollector,
    cik10: str,
    accession: str,
    *,
    retrieved_at: str | None,
    max_document_bytes: int | None,
    memo: dict[str, _IndexOutcome | list[IndexDocument]],
) -> tuple[_IndexOutcome | None, list[IndexDocument] | None]:
    """Fetch and parse the filing index; memoised per URL across the whole run."""
    url = index_url(cik10, accession)
    if url in memo:
        cached = memo[url]
        if isinstance(cached, _IndexOutcome):
            return cached, None
        return None, cached
    doc = {"document_id": f"sec-index:{accession}", "archive_url": url}
    try:
        receipt = archive.fetch_document(
            doc,
            retrieved_at=retrieved_at,
            max_document_bytes=max_document_bytes,
        )
    except ArchiveResponseTooLarge:
        outcome = _IndexOutcome(reason="index_failed")
        memo[url] = outcome
        return outcome, None
    except Exception:
        outcome = _IndexOutcome(reason="index_failed")
        memo[url] = outcome
        return outcome, None
    if isinstance(receipt, Mapping):
        outcome = _IndexOutcome(reason="index_failed")
        memo[url] = outcome
        return outcome, None
    try:
        raw = read_archive_document(archive.cache_root, receipt)
    except Exception:
        outcome = _IndexOutcome(reason="index_failed")
        memo[url] = outcome
        return outcome, None
    html_text = _decode_bytes(raw)
    index_docs = parse_filing_index(html_text)
    memo[url] = index_docs
    return None, index_docs


def _fetch_document(
    archive: SecFilingArchiveCollector,
    cik10: str,
    accession: str,
    item_id: str,
    index_doc: IndexDocument,
    *,
    retrieved_at: str | None,
    max_document_bytes: int | None,
    memo: dict[str, _DocumentOutcome],
) -> _DocumentOutcome:
    """Fetch, extract, and mint one EDGAR document; memoised per URL across the run."""
    url = document_url(cik10, accession, index_doc.filename)
    if url in memo:
        return memo[url]
    doc = {
        "document_id": f"sec:{accession}:{index_doc.filename}",
        "archive_url": url,
    }
    reason: str | None = None
    receipt: ArchiveReceipt | Mapping[str, Any] | None = None
    try:
        receipt = archive.fetch_document(
            doc,
            retrieved_at=retrieved_at,
            max_document_bytes=max_document_bytes,
        )
    except ArchiveResponseTooLarge:
        reason = "too_large"
    except Exception:
        reason = "fetch_failed"
    if reason is not None:
        outcome = _DocumentOutcome(
            reason=reason,
            text=None,
            text_sha256=None,
            text_bytes=None,
            receipt_id=None,
            content_sha256=None,
            byte_length=None,
            span_id=None,
            source_document=None,
            document_kind_doc=index_doc,
        )
        memo[url] = outcome
        return outcome
    if isinstance(receipt, Mapping):
        outcome = _DocumentOutcome(
            reason="document_missing",
            text=None,
            text_sha256=None,
            text_bytes=None,
            receipt_id=None,
            content_sha256=None,
            byte_length=None,
            span_id=None,
            source_document=None,
            document_kind_doc=index_doc,
        )
        memo[url] = outcome
        return outcome
    if receipt is None:
        outcome = _DocumentOutcome(
            reason="fetch_failed",
            text=None,
            text_sha256=None,
            text_bytes=None,
            receipt_id=None,
            content_sha256=None,
            byte_length=None,
            span_id=None,
            source_document=None,
            document_kind_doc=index_doc,
        )
        memo[url] = outcome
        return outcome
    try:
        raw = read_archive_document(archive.cache_root, receipt)
    except Exception:
        outcome = _DocumentOutcome(
            reason="fetch_failed",
            text=None,
            text_sha256=None,
            text_bytes=None,
            receipt_id=None,
            content_sha256=None,
            byte_length=None,
            span_id=None,
            source_document=None,
            document_kind_doc=index_doc,
        )
        memo[url] = outcome
        return outcome
    text = html_to_text(raw)
    if not text:
        outcome = _DocumentOutcome(
            reason="empty_text",
            text=None,
            text_sha256=None,
            text_bytes=None,
            receipt_id=None,
            content_sha256=None,
            byte_length=None,
            span_id=None,
            source_document=None,
            document_kind_doc=index_doc,
        )
        memo[url] = outcome
        return outcome
    text_bytes = text.encode("utf-8")
    text_sha = sha256(text_bytes).hexdigest()
    parsed_fetched = _parse_receipt_retrieved_at(receipt.retrieved_at)
    source = SourceDocument(
        document_id=doc["document_id"],
        event_id=f"ni-case:{item_id}",
        document_kind="filing",
        source_class="primary_filing",
        content_sha256=receipt.content_sha256,
        content_bytes=receipt.byte_length,
        filing_key=FilingKey(cik10, accession),
        fetched_at=parsed_fetched,
        rights_state="internal_only",
    )
    span: Any
    try:
        span = text_span(
            document_id=doc["document_id"],
            document_version=1,
            body_sha256=text_sha,
            segment_index=0,
            segment_text=text,
            start_byte=0,
            end_byte=len(text_bytes),
            text=text,
            display_excerpt="",
        )
    except DocumentError:
        outcome = _DocumentOutcome(
            reason="span_failed",
            text=None,
            text_sha256=None,
            text_bytes=None,
            receipt_id=None,
            content_sha256=None,
            byte_length=None,
            span_id=None,
            source_document=None,
            document_kind_doc=index_doc,
        )
        memo[url] = outcome
        return outcome
    try:
        verify_span(span, segment_text=text, body_sha256=text_sha)
    except DocumentError:
        outcome = _DocumentOutcome(
            reason="span_failed",
            text=None,
            text_sha256=None,
            text_bytes=None,
            receipt_id=None,
            content_sha256=None,
            byte_length=None,
            span_id=None,
            source_document=None,
            document_kind_doc=index_doc,
        )
        memo[url] = outcome
        return outcome
    outcome = _DocumentOutcome(
        reason=None,
        text=text,
        text_sha256=text_sha,
        text_bytes=len(text_bytes),
        receipt_id=receipt.receipt_id,
        content_sha256=receipt.content_sha256,
        byte_length=receipt.byte_length,
        span_id=span.span_id,
        source_document=source,
        document_kind_doc=index_doc,
    )
    memo[url] = outcome
    return outcome


def _parse_receipt_retrieved_at(value: Any) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# S6 - submissions coverage
# ---------------------------------------------------------------------------


@dataclass
class _SubmissionsState:
    """Per-issuer memoised Submissions coverage result."""

    rows: list[FilingRow] | None
    failed: bool
    exception: BaseException | None


def _submissions_coverage(
    forensics: SecForensicsCollector,
    cik10: str,
    window: tuple[date, date, date],
    state: dict[str, _SubmissionsState],
    counts: dict[str, int],
) -> _SubmissionsState:
    """Fetch current + overlapping older shards for ``cik10`` and union their rows."""
    if cik10 in state:
        return state[cik10]
    state[cik10] = _SubmissionsState(rows=None, failed=False, exception=None)
    try:
        current_bytes, _ = forensics.retrieve_current(cik10, "submissions")
    except Exception as exc:
        state[cik10] = _SubmissionsState(rows=None, failed=True, exception=exc)
        return state[cik10]
    try:
        current_payload = json.loads(current_bytes.decode("utf-8"))
    except Exception as exc:
        state[cik10] = _SubmissionsState(rows=None, failed=True, exception=exc)
        return state[cik10]
    try:
        recent_rows = parse_submissions(current_payload)
    except Exception as exc:
        state[cik10] = _SubmissionsState(rows=None, failed=True, exception=exc)
        return state[cik10]
    counts["submissions_fetched"] += 1
    try:
        shards = older_shards(current_payload)
    except Exception as exc:
        state[cik10] = _SubmissionsState(rows=None, failed=True, exception=exc)
        return state[cik10]
    rows_by_accession: dict[str, FilingRow] = {
        row.accession: row for row in recent_rows
    }
    need_shards = (
        not recent_rows
        or window[0] < min(row.filing_date for row in recent_rows)
    )
    if need_shards:
        start_date, _middle, end_date = window
        for name, filing_from, filing_to in shards:
            if filing_to < start_date or filing_from > end_date:
                continue
            try:
                shard_bytes, _ = forensics.retrieve_historical_submissions_file(
                    cik10, name
                )
            except Exception as exc:
                state[cik10] = _SubmissionsState(
                    rows=None, failed=True, exception=exc
                )
                return state[cik10]
            counts["shards_fetched"] += 1
            try:
                shard_payload = json.loads(shard_bytes.decode("utf-8"))
            except Exception as exc:
                state[cik10] = _SubmissionsState(
                    rows=None, failed=True, exception=exc
                )
                return state[cik10]
            try:
                shard_rows = parse_submissions(shard_payload)
            except Exception as exc:
                state[cik10] = _SubmissionsState(
                    rows=None, failed=True, exception=exc
                )
                return state[cik10]
            for row in shard_rows:
                if row.accession not in rows_by_accession:
                    rows_by_accession[row.accession] = row
    state[cik10] = _SubmissionsState(
        rows=list(rows_by_accession.values()),
        failed=False,
        exception=None,
    )
    return state[cik10]


# ---------------------------------------------------------------------------
# S12 - fetch_bodies
# ---------------------------------------------------------------------------


def _coerce_text(value: Any) -> str:
    if isinstance(value, datetime):
        text = value.isoformat()
    elif value is None:
        text = ""
    else:
        text = str(value)
    return text


def _iso_date(value: date) -> str:
    return value.isoformat()


def _record_document(
    outcome: _DocumentOutcome, accession: str, cik10: str
) -> dict[str, Any]:
    index_doc = outcome.document_kind_doc
    record: dict[str, Any] = {
        "document_id": f"sec:{accession}:{index_doc.filename}" if index_doc else None,
        "filename": index_doc.filename if index_doc else None,
        "doc_type": index_doc.doc_type if index_doc else None,
        "archive_url": (
            document_url(cik10, accession, index_doc.filename) if index_doc else None
        ),
        "status": "available" if outcome.reason is None else outcome.reason,
        "content_sha256": outcome.content_sha256,
        "byte_length": outcome.byte_length,
        "receipt_id": outcome.receipt_id,
        "text_sha256": outcome.text_sha256,
        "text_bytes": outcome.text_bytes,
        "span_id": outcome.span_id,
        "source_document": (
            outcome.source_document.to_payload() if outcome.source_document else None
        ),
    }
    return record


def fetch_bodies(
    cases: Sequence[Mapping[str, Any]],
    *,
    forensics: SecForensicsCollector,
    archive: SecFilingArchiveCollector,
    session_dates: Sequence[date],
    out_dir: Path,
    retrieved_at: str | None = None,
    max_document_bytes: int | None = None,
    version: str = EDGAR_BODY_VERSION,
    as_of: date | None = None,
) -> tuple[dict[str, str], list[dict[str, Any]], dict[str, Any]]:
    """Mint per-case 8-K body receipts (or refusal reasons) and a run report.

    ``version`` picks the session band (``BODY_BANDS``).  Version 2 needs
    ``as_of``: a case whose window ends on or after it is ``window_open``.
    """
    if version not in BODY_BANDS:
        raise EdgarBodyError(f"unknown edgar body version: {version!r}")
    is_v2 = version == EDGAR_BODY_VERSION_2
    if is_v2:
        if not isinstance(as_of, date) or isinstance(as_of, datetime):
            raise EdgarBodyError(f"{version} requires an as_of date")
    elif as_of is not None:
        raise EdgarBodyError(f"{version} takes no as_of")
    band = BODY_BANDS[version]
    reason_order = REASON_ORDERS[version]
    reason_index = _REASON_INDEXES[version]
    sessions = validate_sessions(session_dates)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    case_list = list(cases)
    seen_item_ids: set[str] = set()
    for entry in case_list:
        item_id = entry.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            raise EdgarBodyError(f"case missing item_id: {entry!r}")
        if item_id in seen_item_ids:
            raise EdgarBodyError(f"duplicate item_id: {item_id!r}")
        seen_item_ids.add(item_id)
    ordered = sorted(
        case_list,
        key=lambda entry: (
            str(entry.get("issuer", "")),
            str(entry.get("seendate", "")),
            str(entry.get("item_id", "")),
        ),
    )
    submissions_state: dict[str, _SubmissionsState] = {}
    index_memo: dict[str, Any] = {}
    document_memo: dict[str, _DocumentOutcome] = {}
    counts = {
        "submissions_fetched": 0,
        "shards_fetched": 0,
        "indexes_fetched": 0,
        "documents_fetched": 0,
        "texts_written": 0,
        "bytes_fetched": 0,
    }
    records: list[dict[str, Any]] = []
    status_map: dict[str, str] = {}
    issuers: set[str] = set()
    for case in ordered:
        item_id = str(case.get("item_id"))
        issuer_raw = str(case.get("issuer", ""))
        seendate = case.get("seendate")
        issuers.add(issuer_raw)
        reasons: set[str] = set()
        cik10 = parse_issuer_cik(issuer_raw)
        if cik10 is None:
            reasons.add("no_cik")
            window_value: list[str] | None = None
            filing_record: list[dict[str, Any]] = []
            truncated = 0
        else:
            window = session_window(seendate, sessions, band)
            if window is None:
                reasons.add("calendar_gap")
                window_value = None
                filing_record = []
                truncated = 0
            elif is_v2 and as_of is not None and window[2] >= as_of:
                reasons.add("window_open")
                window_value = [_iso_date(d) for d in window]
                filing_record = []
                truncated = 0
            else:
                window_value = [_iso_date(d) for d in window]
                state = _submissions_coverage(
                    forensics, cik10, window, submissions_state, counts
                )
                if state.failed:
                    reasons.add("submissions_failed")
                    filing_record = []
                    truncated = 0
                else:
                    kept, truncated = qualifying_filings(
                        state.rows or [], window
                    )
                    if not kept:
                        reasons.add("no_qualifying_8k")
                        filing_record = []
                    else:
                        filing_record = []
                        for row in kept:
                            filing_entry: dict[str, Any] = {
                                "accession": row.accession,
                                "filing_date": _iso_date(row.filing_date),
                                "form": row.form,
                                "items": list(row.items),
                                "index_url": index_url(cik10, row.accession),
                                "reason": None,
                                "documents": [],
                            }
                            if is_v2:
                                offset = filing_session_offset(
                                    row.filing_date, seendate, sessions
                                )
                                filing_entry["session_offset"] = offset
                                filing_entry["relation"] = filing_relation(offset)
                            (
                                index_outcome,
                                index_docs,
                            ) = _fetch_index(
                                archive,
                                cik10,
                                row.accession,
                                retrieved_at=retrieved_at,
                                max_document_bytes=max_document_bytes,
                                memo=index_memo,
                            )
                            if index_outcome is not None:
                                reasons.add(index_outcome.reason or "index_failed")
                                filing_entry["reason"] = index_outcome.reason
                                filing_record.append(filing_entry)
                                continue
                            if index_docs is None:
                                filing_entry["reason"] = "index_failed"
                                reasons.add("index_failed")
                                filing_record.append(filing_entry)
                                continue
                            counts["indexes_fetched"] += 1
                            body_docs = select_body_documents(
                                index_docs, row.primary_document
                            )
                            if not body_docs:
                                reasons.add("no_body_document")
                                filing_entry["reason"] = "no_body_document"
                                filing_record.append(filing_entry)
                                continue
                            available_for_filing = False
                            for body_doc in body_docs:
                                outcome = _fetch_document(
                                    archive,
                                    cik10,
                                    row.accession,
                                    item_id,
                                    body_doc,
                                    retrieved_at=retrieved_at,
                                    max_document_bytes=max_document_bytes,
                                    memo=document_memo,
                                )
                                if outcome.reason is None:
                                    available_for_filing = True
                                    counts["documents_fetched"] += 1
                                    counts["bytes_fetched"] += int(
                                        outcome.byte_length or 0
                                    )
                                    text_bytes = (outcome.text or "").encode("utf-8")
                                    texts_dir = out_dir / "texts"
                                    target = texts_dir / f"{outcome.text_sha256}.txt"
                                    if not target.exists():
                                        target.parent.mkdir(
                                            parents=True, exist_ok=True
                                        )
                                        target.write_bytes(text_bytes)
                                        counts["texts_written"] += 1
                                else:
                                    reasons.add(outcome.reason)
                                filing_entry["documents"].append(
                                    _record_document(outcome, row.accession, cik10)
                                )
                            if available_for_filing:
                                filing_entry["reason"] = None
                            else:
                                filing_reasons = sorted(
                                    {
                                        doc["status"]
                                        for doc in filing_entry["documents"]
                                        if doc["status"] != "available"
                                    },
                                    key=lambda name: reason_index.get(name, -1),
                                )
                                filing_entry["reason"] = (
                                    filing_reasons[-1] if filing_reasons else None
                                )
                            filing_record.append(filing_entry)
        if not reasons:
            status = "available"
            reason_value: str | None = None
        else:
            top_reason = max(reasons, key=lambda name: reason_index.get(name, -1))
            status = f"body_unavailable:{top_reason}"
            reason_value = top_reason
        status_map[item_id] = status
        record: dict[str, Any] = {
            "item_id": item_id,
            "issuer": issuer_raw,
            "seendate": _coerce_text(seendate),
            "status": status,
            "reason": reason_value,
            "window": window_value,
            "filings_truncated": truncated,
            "filings": filing_record,
        }
        records.append(record)
    records.sort(key=lambda entry: entry["item_id"])
    reason_counts: dict[str, int] = {name: 0 for name in reason_order}
    for entry in records:
        if entry["status"] == "available":
            continue
        reason = entry["reason"]
        if reason is not None:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    available = sum(1 for entry in records if entry["status"] == "available")
    body_unavailable = sum(1 for entry in records if entry["status"] != "available")
    report = {
        "version": version,
        "cases": len(records),
        "available": available,
        "body_unavailable": body_unavailable,
        "reasons": reason_counts,
        "issuers": sorted(issuers),
        "submissions_fetched": counts["submissions_fetched"],
        "shards_fetched": counts["shards_fetched"],
        "indexes_fetched": counts["indexes_fetched"],
        "documents_fetched": counts["documents_fetched"],
        "texts_written": counts["texts_written"],
        "bytes_fetched": counts["bytes_fetched"],
    }
    return status_map, records, report


# ---------------------------------------------------------------------------
# S13 - CLI
# ---------------------------------------------------------------------------


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            cases.append(json.loads(stripped))
    return cases


def _load_sessions(path: Path) -> list[date]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or "sessions" not in payload:
        raise EdgarBodyError("sessions file must contain a 'sessions' key")
    raw_sessions = payload["sessions"]
    if not isinstance(raw_sessions, list):
        raise EdgarBodyError("sessions must be a list")
    return [date.fromisoformat(entry) for entry in raw_sessions]


def _parse_as_of(raw: str | None, version: str) -> date | None:
    if version != EDGAR_BODY_VERSION_2:
        if raw is not None:
            raise EdgarBodyError(f"--as-of applies only to {EDGAR_BODY_VERSION_2}")
        return None
    if raw is None:
        raise EdgarBodyError(f"{EDGAR_BODY_VERSION_2} requires --as-of YYYY-MM-DD")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise EdgarBodyError(f"bad --as-of {raw!r}: {exc}") from exc


def main(
    argv: Sequence[str] | None = None,
    *,
    forensics: SecForensicsCollector | None = None,
    archive: SecFilingArchiveCollector | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--sessions", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--user-agent",
        required=True,
        help='SEC contact user agent, e.g. "Name email@host"',
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-document-bytes", type=int, default=None)
    parser.add_argument(
        "--version",
        choices=EDGAR_BODY_VERSIONS,
        default=EDGAR_BODY_VERSION,
        help="session band version (default: %(default)s)",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="YYYY-MM-DD; required by ni-edgar-body-2 (windows ending on or after it are window_open)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        as_of = _parse_as_of(args.as_of, args.version)
        cases = _load_cases(args.cases)
        sessions = _load_sessions(args.sessions)
    except EdgarBodyError as exc:
        print(f"edgar_body: {exc}", file=sys.stderr)
        return 2
    if args.limit is not None:
        cases = cases[: args.limit]
    pacer = SecRequestPacer(min_interval_seconds=0.12)
    if forensics is None:
        forensics = SecForensicsCollector(
            args.cache / "forensics",
            user_agent=args.user_agent,
            pacer=pacer,
        )
    if archive is None:
        archive = SecFilingArchiveCollector(
            args.cache / "archive",
            user_agent=args.user_agent,
            pacer=pacer,
        )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    status_map, records, report = fetch_bodies(
        cases,
        forensics=forensics,
        archive=archive,
        session_dates=sessions,
        out_dir=out_dir,
        max_document_bytes=args.max_document_bytes,
        version=args.version,
        as_of=as_of,
    )
    bodies_path = out_dir / "bodies.jsonl"
    with bodies_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    (out_dir / "status_map.json").write_text(
        json.dumps(status_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "body_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"cases": report["cases"], "available": report["available"], "out": str(out_dir)}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
