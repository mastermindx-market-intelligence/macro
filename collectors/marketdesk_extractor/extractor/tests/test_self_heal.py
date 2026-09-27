"""Self-heal for papers first seen before their data was ready.

MarketDesk generates the AI summary ASYNCHRONOUSLY and ships some titles truncated
(a dropped ``.EX)`` Reuters suffix). A paper discovered before its summary existed —
or with a truncated title — used to be stuck forever, because a seen blob_id
short-circuits before ``item_extra`` is ever called again. These tests cover:

  1. discovery re-fetches ``/extra`` for a seen-but-incomplete paper and backfills
     the summary + recovered title, nulling ``vaulted_at`` so the sidecar re-publishes;
  2. the vault pass routes an already-vaulted (re-heal) row through the JSON-only
     ``republish_sidecar`` instead of a full ``publish`` (no PDF bytes needed).
"""
from __future__ import annotations

from pathlib import Path

from marketdesk_extractor import db
from marketdesk_extractor.config import Config

T = 1782000000  # fixed publish time


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


class HealClient:
    """Fake client whose ``/extra`` payload is mutable between discover passes,
    simulating MarketDesk generating the summary + full title only later."""

    def __init__(self):
        self.extra = {"summary": None}          # what /extra returns right now
        self.extra_calls: list[str] = []

    # a paper whose display name arrives truncated (dropped '.US)')
    PAPERS = [
        {"pathId": "P1", "parent": "brk", "name": "Alcon Inc. (ALCC",
         "type": "application/pdf", "t": T, "size": 100, "institution": "GS"},
    ]

    def latest(self, institutions=None): return []
    def picks(self): return []
    def saved(self): return []
    def provision(self, ids): return []

    def walk_papers(self, *, since_unix=None, limit=None, max_days=None):
        yield from self.PAPERS

    def item_extra(self, item_id):
        self.extra_calls.append(item_id)
        return dict(self.extra)


def test_discovery_self_heals_late_summary_and_truncated_title(tmp_path, monkeypatch):
    from marketdesk_extractor.discover import discover

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    client = HealClient()

    # 1) first discovery: /extra has no summary yet; name is truncated
    r1 = discover(cfg, conn, client, limit=10)
    assert r1.discovered_new == 1 and r1.healed == 0
    row = db.get_by_blob_id(conn, "P1")
    assert not (row["marketdesk_summary"] or "")          # summary absent
    assert row["title"] == "Alcon Inc. (ALCC"             # truncated

    # simulate a prior vault publish (so a re-heal must re-publish the sidecar)
    db.mark_vaulted(conn, "P1", "marketdesk-p1-abcdef", "2026-07-24T00:00:00Z")

    # 2) MarketDesk has now generated the summary + a full title
    client.extra = {"summary": "Late AI summary. Now present.", "title": "Alcon Inc. (ALCC.US)"}
    r2 = discover(cfg, conn, client, limit=10)
    assert r2.discovered_new == 0 and r2.skipped_seen == 1 and r2.healed == 1
    row = db.get_by_blob_id(conn, "P1")
    assert row["marketdesk_summary"] == "Late AI summary. Now present."
    assert row["title"] == "Alcon Inc. (ALCC.US)"          # recovered
    assert row["vaulted_at"] is None                       # queued for re-publish
    assert row["vault_key"] == "marketdesk-p1-abcdef"      # kept (JSON re-publish target)

    # 3) a third pass finds nothing left to heal
    r3 = discover(cfg, conn, client, limit=10)
    assert r3.healed == 0


def test_healthy_paper_is_not_refetched(tmp_path, monkeypatch):
    from marketdesk_extractor.discover import discover

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)
    client = HealClient()
    client.extra = {"summary": "Good summary right away.", "title": "Alcon Inc. (ALCC.US)"}

    discover(cfg, conn, client, limit=10)
    # heal a truncated title on pass 2, then pass 3 must not touch /extra again
    r2 = discover(cfg, conn, client, limit=10)
    assert r2.healed == 1                                   # title recovered
    n_calls = len(client.extra_calls)
    r3 = discover(cfg, conn, client, limit=10)
    assert r3.healed == 0
    assert len(client.extra_calls) == n_calls              # no wasted /extra call


class FakePublisher:
    """Records which publish path each paper took."""
    enabled = True

    def __init__(self, cfg):
        self.published: list[str] = []
        self.residecared: list[str] = []

    def publish(self, view, *, force=False):
        self.published.append(view["blob_id"]); return "vid-" + view["blob_id"]

    def republish_sidecar(self, view):
        self.residecared.append(view["blob_id"]); return "vid-" + view["blob_id"]


def test_vault_pass_routes_reheal_to_json_only_republish(tmp_path, monkeypatch):
    from marketdesk_extractor import pipeline
    from marketdesk_extractor.schemas import Status

    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url); db.init_db(conn)

    # a FRESH complete paper (never vaulted) and a RE-HEAL one (vault_key set,
    # vaulted_at nulled by a prior self-heal)
    conn.execute(
        "INSERT INTO papers (blob_id, title, status, vault_key, vaulted_at) VALUES (?,?,?,?,?)",
        ("FRESH", "New Report", Status.COMPLETE.value, None, None),
    )
    conn.execute(
        "INSERT INTO papers (blob_id, title, status, vault_key, vaulted_at) VALUES (?,?,?,?,?)",
        ("REHEAL", "Alcon Inc. (ALCC.US)", Status.COMPLETE.value, "marketdesk-reheal-x", None),
    )
    conn.commit()

    fake = {}
    def _factory(c):
        fake["pub"] = FakePublisher(c); return fake["pub"]
    monkeypatch.setattr(pipeline, "VaultPublisher", _factory, raising=False)
    monkeypatch.setattr("marketdesk_extractor.publish_vault.VaultPublisher", _factory, raising=False)

    res = pipeline.publish_vault_pending(cfg, conn)
    pub = fake["pub"]
    assert res.published == 2
    assert pub.published == ["FRESH"]          # never-vaulted → full publish
    assert pub.residecared == ["REHEAL"]       # already-vaulted → JSON-only re-publish
    # both are now (re)marked vaulted
    assert db.get_by_blob_id(conn, "REHEAL")["vaulted_at"] is not None
