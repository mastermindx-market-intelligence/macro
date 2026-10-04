"""Tests for pipeline.write_manifest — JSONL shape, ManifestEntry fields.

pipeline.py has a module-level import of discover.py which in turn imports
tenacity (a declared dependency). The tests skip gracefully when the full
dependency set is not installed so the file is always importable.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

# Skip the whole module if heavy pipeline deps are absent.
pytest.importorskip("tenacity", reason="tenacity not installed; skipping manifest tests")

from marketdesk_extractor import db
from marketdesk_extractor.config import Config
from marketdesk_extractor.pipeline import write_manifest
from marketdesk_extractor.schemas import ManifestEntry, Status


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Build a fully offline Config pointing at tmp_path directories."""
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "db" / "test.sqlite"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RAW_PDF_DIR", str(tmp_path / "data" / "raw_pdfs"))
    monkeypatch.setenv("MARKDOWN_DIR", str(tmp_path / "data" / "markdown"))
    monkeypatch.setenv("METADATA_DIR", str(tmp_path / "data" / "metadata"))
    monkeypatch.setenv("MANIFEST_DIR", str(tmp_path / "data" / "manifests"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("R2_ENABLED", "false")
    monkeypatch.setenv("DROPBOX_ENABLED", "false")
    return Config.from_env()


@pytest.fixture()
def conn(cfg: Config) -> sqlite3.Connection:
    c = db.connect(cfg.database_url)
    db.init_db(c)
    return c


def _seed_complete_row(conn: sqlite3.Connection, cfg: Config, date_str: str) -> int:
    """Insert a fully COMPLETE paper row for date_str and return its row id."""
    published_at = f"{date_str}T10:00:00+00:00"
    pdf_filename = f"{date_str}_jpm_earnings-upgrade-catalyst_blob99.pdf"
    base = f"{date_str}_jpm_earnings-upgrade-catalyst_blob99"

    cur = conn.execute(
        "INSERT INTO papers "
        "(article_url, blob_url, blob_id, title, institution, published_at, "
        " marketdesk_age_text, marketdesk_summary, local_priority_score, sha256, "
        " page_count, parser, pdf_filename, markdown_filename, metadata_filename, "
        " r2_pdf_key, r2_markdown_key, r2_metadata_key, status, "
        " discovered_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
        (
            "https://marketdesk.ai/library/browse?item=blob99",
            "https://marketdesk.ai/files/blob99/blob",
            "blob99",
            "Earnings Upgrade Catalyst",
            "JPM",
            published_at,
            "1 hr",
            "Strong buy; margin expansion expected.",
            78,
            "aabbcc" * 10 + "aabb",  # 64 hex chars
            5,
            "noop",
            pdf_filename,
            f"{base}.md",
            f"{base}.json",
            f"marketdesk/raw_pdfs/{date_str}/{pdf_filename}",
            f"marketdesk/markdown/{date_str}/{base}.md",
            f"marketdesk/metadata/{date_str}/{base}.json",
            Status.COMPLETE.value,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_write_manifest_creates_jsonl_file(
    cfg: Config, conn: sqlite3.Connection
) -> None:
    date_str = "2026-07-07"
    _seed_complete_row(conn, cfg, date_str)
    out = write_manifest(cfg, conn, date_str, upload=False)
    assert out.exists()
    assert out.suffix == ".jsonl"
    assert out.name == f"{date_str}.jsonl"


def test_write_manifest_one_line_per_row(
    cfg: Config, conn: sqlite3.Connection
) -> None:
    date_str = "2026-07-07"
    _seed_complete_row(conn, cfg, date_str)
    out = write_manifest(cfg, conn, date_str, upload=False)
    lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1


def test_write_manifest_valid_json_per_line(
    cfg: Config, conn: sqlite3.Connection
) -> None:
    date_str = "2026-07-07"
    _seed_complete_row(conn, cfg, date_str)
    out = write_manifest(cfg, conn, date_str, upload=False)
    for line in out.read_text().splitlines():
        if line.strip():
            obj = json.loads(line)
            assert isinstance(obj, dict)


def test_write_manifest_entry_fields_match_schema(
    cfg: Config, conn: sqlite3.Connection
) -> None:
    date_str = "2026-07-07"
    _seed_complete_row(conn, cfg, date_str)
    out = write_manifest(cfg, conn, date_str, upload=False)
    line = out.read_text().strip()
    obj = json.loads(line)

    # ManifestEntry must parse cleanly
    entry = ManifestEntry(**obj)
    assert entry.blob_id == "blob99"
    assert entry.title == "Earnings Upgrade Catalyst"
    assert entry.institution == "JPM"
    assert entry.status == Status.COMPLETE.value
    assert entry.local_priority_score == 78
    assert entry.page_count == 5
    assert entry.parser == "noop"


def test_write_manifest_excludes_discovered_status(
    cfg: Config, conn: sqlite3.Connection
) -> None:
    """Papers still at DISCOVERED (no PDF yet) must not appear in the manifest."""
    date_str = "2026-07-07"
    published_at = f"{date_str}T09:00:00+00:00"
    conn.execute(
        "INSERT INTO papers (article_url, blob_url, blob_id, title, published_at, status, "
        "discovered_at, updated_at) VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
        (
            "https://marketdesk.ai/library/browse?item=disconly",
            "https://marketdesk.ai/files/disconly/blob",
            "disconly",
            "Undiscovered Gem",
            published_at,
            Status.DISCOVERED.value,
        ),
    )
    conn.commit()
    out = write_manifest(cfg, conn, date_str, upload=False)
    lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
    assert len(lines) == 0


def test_write_manifest_multiple_rows(
    cfg: Config, conn: sqlite3.Connection
) -> None:
    date_str = "2026-07-08"
    for i in range(3):
        published_at = f"{date_str}T0{i}:00:00+00:00"
        pdf_name = f"{date_str}_gs_paper{i}_blob{i}.pdf"
        conn.execute(
            "INSERT INTO papers "
            "(article_url, blob_url, blob_id, title, published_at, pdf_filename, "
            " status, discovered_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
            (
                f"https://marketdesk.ai/library/browse?item=blob{i}",
                f"https://marketdesk.ai/files/blob{i}/blob",
                f"blob{i}",
                f"Paper {i}",
                published_at,
                pdf_name,
                Status.COMPLETE.value,
            ),
        )
    conn.commit()
    out = write_manifest(cfg, conn, date_str, upload=False)
    lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
