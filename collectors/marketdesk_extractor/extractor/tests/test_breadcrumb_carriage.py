"""W5 source-native breadcrumb carriage into the Research Vault.

These tests are intentionally separate from test_self_heal.py because PR #7226
already owns that existing test file. They prove the new metadata path without
creating a release collision.
"""
from __future__ import annotations

from pathlib import Path

from marketdesk_extractor import db
from marketdesk_extractor.config import Config


T = 1782000000


def _cfg(tmp_path: Path, monkeypatch) -> Config:
    for key, value in {
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
        monkeypatch.setenv(key, value)
    cfg = Config.from_env()
    cfg.ensure_dirs()
    return cfg


class BreadcrumbClient:
    PAPERS = [{
        "pathId": "P1",
        "parent": "brk",
        "name": "CrowdStrike (CRWD) Fal.con 2026 product takeaways",
        "type": "application/pdf",
        "t": T,
        "size": 100,
        "institution": "GS",
    }]

    def __init__(self):
        self.extra_calls: list[str] = []
        self.path_calls: list[str] = []
        self.path = [
            {"name": "2026"},
            {"name": "July"},
            {"name": "Jul 21"},
            {"name": "Goldman"},
            {"name": "S&T"},
        ]

    def latest(self, institutions=None):
        return []

    def picks(self):
        return []

    def saved(self):
        return []

    def provision(self, ids):
        return []

    def walk_papers(self, *, since_unix=None, limit=None, max_days=None):
        yield from self.PAPERS

    def item_extra(self, item_id):
        self.extra_calls.append(item_id)
        return {"summary": "Healthy source summary."}

    def item_path(self, item_id):
        self.path_calls.append(item_id)
        return list(self.path)


def test_new_discovery_persists_source_breadcrumb_and_vault_derives_desk(
    tmp_path, monkeypatch
):
    from marketdesk_extractor.discover import discover
    from marketdesk_extractor.publish_vault import sidecar_for

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url)
    db.init_db(conn)
    client = BreadcrumbClient()

    result = discover(cfg, conn, client, limit=10)
    row = db.get_by_blob_id(conn, "P1")

    assert result.discovered_new == 1
    assert client.path_calls == ["P1"]
    assert row["breadcrumb"] == '["2026", "July", "Jul 21", "Goldman", "S&T"]'
    assert sidecar_for(dict(row))["desk"] == "S&T"


def test_seen_row_backfills_breadcrumb_without_summary_fetch_and_requeues_sidecar(
    tmp_path, monkeypatch
):
    from marketdesk_extractor.discover import discover

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url)
    db.init_db(conn)
    client = BreadcrumbClient()

    discover(cfg, conn, client, limit=10)
    db.update_fields(conn, "P1", breadcrumb=None)
    db.mark_vaulted(conn, "P1", "marketdesk-p1-abcdef", "2026-07-24T00:00:00Z")
    client.extra_calls.clear()
    client.path_calls.clear()

    result = discover(cfg, conn, client, limit=10, fetch_summary=False)
    row = db.get_by_blob_id(conn, "P1")

    assert result.discovered_new == 0
    assert result.skipped_seen == 1
    assert result.healed == 1
    assert client.extra_calls == []
    assert client.path_calls == ["P1"]
    assert row["breadcrumb"]
    assert row["vaulted_at"] is None
    assert row["vault_key"] == "marketdesk-p1-abcdef"


def test_missing_source_path_does_not_fabricate_breadcrumb(tmp_path, monkeypatch):
    from marketdesk_extractor.discover import discover

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url)
    db.init_db(conn)
    client = BreadcrumbClient()
    client.path = []

    result = discover(cfg, conn, client, limit=10)
    row = db.get_by_blob_id(conn, "P1")

    assert result.discovered_new == 1
    assert row["breadcrumb"] is None

    client.extra_calls.clear()
    client.path_calls.clear()
    result2 = discover(cfg, conn, client, limit=10, fetch_summary=False)

    assert result2.healed == 0
    assert client.extra_calls == []
    assert client.path_calls == ["P1"]
    assert db.get_by_blob_id(conn, "P1")["breadcrumb"] is None
