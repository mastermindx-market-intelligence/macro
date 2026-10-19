"""Pydantic schemas + status enum shared across the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Status(str, Enum):
    DISCOVERED = "DISCOVERED"
    SKIPPED_SEEN = "SKIPPED_SEEN"
    SKIPPED_OLD = "SKIPPED_OLD"
    BLOB_FOUND = "BLOB_FOUND"
    DOWNLOADED = "DOWNLOADED"
    PARSED = "PARSED"
    UPLOADED = "UPLOADED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    SKIPPED_UNSUPPORTED = "SKIPPED_UNSUPPORTED"  # blob is not a PDF (ZIP/XLSX/etc.) — terminal, never retry
    SKIPPED_EXCLUDED = "SKIPPED_EXCLUDED"  # institution/topic exclusion filter (filters.py) — terminal, never a download candidate


class ArticleMeta(BaseModel):
    """A MarketDesk paper as discovered (before download/parse/upload)."""

    blob_id: str                      # item pathId; also the blob id
    article_url: str
    blob_url: str
    title: str
    institution: str | None = None
    published_at: datetime | None = None   # from item `t` (unix seconds)
    published_unix: int | None = None
    size_bytes: int | None = None
    marketdesk_age_text: str | None = None
    marketdesk_summary: str | None = None
    breadcrumb: list[str] = Field(default_factory=list)   # e.g. [2026, July, Jul 7, Goldman, S&T]

    # feed membership flags (enrichment)
    is_latest: bool = False
    is_top_pick: bool = False
    is_saved: bool = False

    # set by score.py
    local_priority_score: int | None = None

    @staticmethod
    def unix_to_dt(t: int | None) -> datetime | None:
        if t is None:
            return None
        return datetime.fromtimestamp(int(t), tz=timezone.utc)


class ParseResult(BaseModel):
    """Result of converting a downloaded PDF to Markdown."""

    markdown_path: str | None = None
    metadata_path: str | None = None
    page_count: int | None = None
    parser: str = "none"
    status: Status = Status.PARSED
    error: str | None = None


class ManifestEntry(BaseModel):
    """One line of the daily JSONL manifest — the local-LLM hand-off contract."""

    paper_id: int | None = None
    title: str
    institution: str | None = None
    article_url: str
    blob_url: str
    blob_id: str
    published_at: str | None = None
    marketdesk_age_text: str | None = None
    marketdesk_summary: str | None = None
    local_priority_score: int | None = None
    sha256: str | None = None
    page_count: int | None = None
    parser: str | None = None
    local_pdf_path: str | None = None
    local_markdown_path: str | None = None
    r2_pdf_key: str | None = None
    r2_markdown_key: str | None = None
    r2_metadata_key: str | None = None
    dropbox_pdf_path: str | None = None
    status: str = Status.COMPLETE.value
