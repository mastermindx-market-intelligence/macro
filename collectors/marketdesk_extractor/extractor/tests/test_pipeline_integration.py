"""End-to-end pipeline stitching test with a fake MarketDesk client.

Exercises discover -> download -> parse -> upload -> manifest with NO network, NO auth,
NO boto3, NO Playwright. Proves the orchestration wiring the live run would use.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from marketdesk_extractor import db
from marketdesk_extractor.config import Config
from marketdesk_extractor.marketdesk import (
    DownloadCapExhausted, MarketDeskError, ProviderBlobRefused,
    TransientHTTPError, UnsupportedBlobError,
)
from marketdesk_extractor.schemas import Status

T = 1782000000  # fixed publish time -> stable date folder


class FakeClient:
    """Stand-in for MarketDeskClient with canned, deterministic data."""

    PAPERS = [
        {"pathId": "PID1", "parent": "brk", "name": "JPM  Earnings Upgrade Catalyst",
         "type": "application/pdf", "t": T, "size": 1000, "institution": "JPM"},
        {"pathId": "PID2", "parent": "brk", "name": "MS Weekly Calendar Recap",
         "type": "application/pdf", "t": T, "size": 2000, "institution": "MS"},
    ]

    def latest(self, institutions=None): return []
    def picks(self): return []
    def saved(self): return []
    def provision(self, ids): return []

    def walk_papers(self, *, since_unix=None, limit=None, max_days=None):
        for p in self.PAPERS:
            yield p

    def item_extra(self, item_id):
        return {"summary": f"AI summary for {item_id}", "images": []}

    def download_blob(self, blob_id):
        # unique bytes per id -> distinct sha256; valid %PDF header
        return b"%PDF-1.4\n" + blob_id.encode() + b"\n%%EOF\n"


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
        "DROPBOX_ENABLED": "false",
        "PARSER_BACKEND": "none",
    }.items():
        monkeypatch.setenv(k, v)
    cfg = Config.from_env()
    cfg.ensure_dirs()
    return cfg


def test_full_pipeline_stitch(tmp_path, monkeypatch):
    from marketdesk_extractor.discover import discover
    from marketdesk_extractor.download import download_pending
    from marketdesk_extractor.pipeline import parse_pending, upload_pending, write_manifest

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    client = FakeClient()

    # 1) discover
    dres = discover(cfg, conn, client, limit=10)
    assert dres.discovered_new == 2
    row = db.get_by_blob_id(conn, "PID1")
    assert row["status"] == Status.DISCOVERED.value
    assert row["marketdesk_summary"] == "AI summary for PID1"
    assert (row["local_priority_score"] or 0) > 0  # JPM + catalyst scored

    # 2) download
    dl = download_pending(cfg, conn, client)
    assert dl.downloaded == 2
    row = db.get_by_blob_id(conn, "PID1")
    assert row["status"] == Status.DOWNLOADED.value
    assert row["sha256"]
    assert (Path(cfg.raw_pdf_dir) / row["pdf_filename"]).exists()

    # 3) parse (noop backend -> PARSED, metadata written, no markdown)
    pr = parse_pending(cfg, conn)
    assert pr.parsed == 2
    row = db.get_by_blob_id(conn, "PID1")
    assert row["status"] == Status.PARSED.value
    assert row["parser"] == "none"
    assert (Path(cfg.metadata_dir) / _date() / row["metadata_filename"]).exists()

    # 4) upload (R2/Dropbox off -> COMPLETE local-only)
    up = upload_pending(cfg, conn)
    assert up.completed_local == 2
    assert db.get_by_blob_id(conn, "PID1")["status"] == Status.COMPLETE.value

    # 5) manifest
    mpath = write_manifest(cfg, conn, _date(), upload=False)
    lines = Path(mpath).read_text().strip().splitlines()
    assert len(lines) == 2
    import json
    entry = json.loads(lines[0])
    assert entry["blob_id"] in {"PID1", "PID2"}
    assert entry["blob_url"].endswith("/blob")
    assert entry["status"] == Status.COMPLETE.value


@pytest.mark.parametrize(
    "error",
    [ProviderBlobRefused, MarketDeskError, DownloadCapExhausted,
     TransientHTTPError],
)
def test_manual_download_pass_preserves_metadata_on_unqualified_provider_error(
    tmp_path, monkeypatch, error,
):
    from marketdesk_extractor.discover import discover
    from marketdesk_extractor.download import download_pending

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    discover(cfg, conn, FakeClient(), limit=10)

    class ProviderFailure(FakeClient):
        def __init__(self):
            self.calls = []

        def download_blob(self, blob_id):
            self.calls.append(blob_id)
            raise error("provider did not deliver PDF")

    client = ProviderFailure()
    try:
        result = download_pending(cfg, conn, client)
        assert result.failed == 1
        assert len(client.calls) == 1, "a rejected report must stop the pass"
        for blob_id in ("PID1", "PID2"):
            row = db.get_by_blob_id(conn, blob_id)
            assert row["status"] == Status.DISCOVERED.value
            assert row["sha256"] is None
    finally:
        conn.close()


def test_manual_download_pass_preserves_and_raises_expired_auth(
    tmp_path, monkeypatch,
):
    from marketdesk_extractor.discover import discover
    from marketdesk_extractor.download import download_pending
    from marketdesk_extractor.marketdesk import SessionExpired

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    discover(cfg, conn, FakeClient(), limit=10)

    class LoggedOutClient(FakeClient):
        def __init__(self):
            self.calls = []

        def download_blob(self, blob_id):
            self.calls.append(blob_id)
            raise SessionExpired("session control confirmed logged out")

    client = LoggedOutClient()
    try:
        with pytest.raises(SessionExpired, match="confirmed logged out"):
            download_pending(cfg, conn, client)
        assert len(client.calls) == 1
        for blob_id in ("PID1", "PID2"):
            row = db.get_by_blob_id(conn, blob_id)
            assert row["status"] == Status.DISCOVERED.value
            assert row["sha256"] is None
    finally:
        conn.close()


def test_manual_download_pass_terminal_only_for_proven_binary_non_pdf(
    tmp_path, monkeypatch,
):
    from marketdesk_extractor.discover import discover
    from marketdesk_extractor.download import download_pending

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    discover(cfg, conn, FakeClient(), limit=10)

    class OneUnsupported(FakeClient):
        def download_blob(self, blob_id):
            if blob_id == "PID1":
                raise UnsupportedBlobError("binary ZIP container")
            return super().download_blob(blob_id)

    try:
        result = download_pending(cfg, conn, OneUnsupported())
        assert result.failed == 1
        assert result.downloaded == 1
        assert db.get_by_blob_id(conn, "PID1")["status"] == (
            Status.SKIPPED_UNSUPPORTED.value
        )
        assert db.get_by_blob_id(conn, "PID2")["status"] == (
            Status.DOWNLOADED.value
        )
    finally:
        conn.close()


def _date() -> str:
    return datetime.fromtimestamp(T, tz=timezone.utc).strftime("%Y-%m-%d")
