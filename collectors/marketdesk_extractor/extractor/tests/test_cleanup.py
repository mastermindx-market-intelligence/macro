"""Tests for local artifact cleanup (prune_local)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from marketdesk_extractor import db
from marketdesk_extractor.config import Config
from marketdesk_extractor.schemas import ArticleMeta, Status


def _cfg(tmp_path, monkeypatch) -> Config:
    for k, v in {
        "DATABASE_URL": str(tmp_path / "db" / "t.sqlite"),
        "OUTPUT_DIR": str(tmp_path / "data"),
        "RAW_PDF_DIR": str(tmp_path / "data" / "raw_pdfs"),
        "MARKDOWN_DIR": str(tmp_path / "data" / "markdown"),
        "METADATA_DIR": str(tmp_path / "data" / "metadata"),
        "MANIFEST_DIR": str(tmp_path / "data" / "manifests"),
        "LOG_DIR": str(tmp_path / "logs"),
        "MARKETDESK_PROFILE_DIR": str(tmp_path / "prof"),
        "R2_ENABLED": "false",
    }.items():
        monkeypatch.setenv(k, v)
    cfg = Config.from_env()
    cfg.ensure_dirs()
    return cfg


def _seed(cfg, conn, *, blob_id, r2=True, days_old=30) -> Path:
    """Insert a COMPLETE paper and create its local PDF file. Returns the pdf path."""
    meta = ArticleMeta(
        blob_id=blob_id,
        article_url=cfg.article_url(blob_id),
        blob_url=cfg.blob_url(blob_id),
        title="Test Paper",
        institution="JPM",
        published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    db.upsert_discovered(conn, meta)
    pdf_name = f"2026-07-01_jpm_test_{blob_id}.pdf"
    dl_at = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    db.update_fields(
        conn, blob_id,
        pdf_filename=pdf_name, downloaded_at=dl_at, status=Status.COMPLETE.value,
        r2_pdf_key=(f"marketdesk/raw_pdfs/2026-07-01/{pdf_name}" if r2 else None),
    )
    p = Path(cfg.raw_pdf_dir) / pdf_name
    p.write_bytes(b"%PDF-1.7\n" + b"x" * 5000)
    return p


def test_prune_removes_uploaded_pdf(tmp_path, monkeypatch):
    from marketdesk_extractor.cleanup import prune_local
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    pdf = _seed(cfg, conn, blob_id="AAA111", r2=True, days_old=30)
    assert pdf.exists()

    res = prune_local(cfg, conn, older_than_days=7)
    assert res.pruned_pdfs == 1
    assert res.bytes_freed > 0
    assert not pdf.exists()
    # DB row (dedup memory) must survive
    assert db.get_by_blob_id(conn, "AAA111") is not None


def test_require_r2_skips_unarchived(tmp_path, monkeypatch):
    from marketdesk_extractor.cleanup import prune_local
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    pdf = _seed(cfg, conn, blob_id="BBB222", r2=False, days_old=30)

    res = prune_local(cfg, conn, older_than_days=7)  # require_r2=True by default
    assert res.pruned_pdfs == 0
    assert res.skipped_no_r2 == 1
    assert pdf.exists()  # not archived -> kept


def test_dry_run_deletes_nothing(tmp_path, monkeypatch):
    from marketdesk_extractor.cleanup import prune_local
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    pdf = _seed(cfg, conn, blob_id="CCC333", r2=True, days_old=30)

    res = prune_local(cfg, conn, older_than_days=7, dry_run=True)
    assert res.pruned_pdfs == 1        # counted as "would prune"
    assert res.dry_run is True
    assert pdf.exists()                # but nothing actually deleted


def test_age_filter_keeps_recent(tmp_path, monkeypatch):
    from marketdesk_extractor.cleanup import prune_local
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    pdf = _seed(cfg, conn, blob_id="DDD444", r2=True, days_old=1)

    res = prune_local(cfg, conn, older_than_days=7)
    assert res.pruned_pdfs == 0
    assert res.skipped_recent == 1
    assert pdf.exists()
