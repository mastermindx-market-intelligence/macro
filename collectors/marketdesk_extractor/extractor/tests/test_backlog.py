"""Tests for the deferred-papers ledger report (backlog.py).

The report is the backfill plan for the day we add more accounts, so what it must
get right is: WHICH rows count as still-pullable (exactly the allocator's
candidate set — nothing already downloaded, nothing terminally skipped), the
new-vs-backfill split, and the value ordering a new account would drain in.
Everything runs against a temp DB with an injected ``now``; no network, no clock.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from marketdesk_extractor import backlog, db
from marketdesk_extractor.schemas import Status

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)  # a Monday, 08:00 ET


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = db.connect(tmp_path / "backlog.sqlite")
    db.init_db(c)
    return c


def _insert(
    conn: sqlite3.Connection,
    blob_id: str,
    *,
    published_at: datetime | None,
    score: int | None = None,
    institution: str | None = "JPM",
    title: str | None = None,
    status: Status = Status.DISCOVERED,
) -> None:
    conn.execute(
        "INSERT INTO papers (blob_id, article_url, blob_url, title, institution, "
        "published_at, status, local_priority_score) VALUES (?,?,?,?,?,?,?,?)",
        (
            blob_id,
            f"https://marketdesk.ai/library/browse?item={blob_id}",
            f"https://marketdesk.ai/files/{blob_id}/blob",
            title if title is not None else f"title {blob_id}",
            institution,
            published_at.astimezone(timezone.utc).isoformat() if published_at else None,
            status.value,
            score,
        ),
    )
    conn.commit()


def _report(conn, **kw):
    return backlog.build_report(conn, NOW, new_window_hours=48, **kw)


# ---------------------------------------------------------------------------
# candidate set + new/backfill split
# ---------------------------------------------------------------------------
def test_counts_only_pullable_candidates(conn):
    _insert(conn, "new1", published_at=NOW - timedelta(hours=2))
    _insert(conn, "new2", published_at=NOW - timedelta(hours=47),
            status=Status.BLOB_FOUND)
    _insert(conn, "back1", published_at=NOW - timedelta(hours=49))
    _insert(conn, "back_undated", published_at=None)
    # none of these can be pulled again -> must NOT appear in the ledger
    _insert(conn, "done", published_at=NOW - timedelta(hours=1),
            status=Status.COMPLETE)
    _insert(conn, "excluded", published_at=NOW - timedelta(hours=1),
            status=Status.SKIPPED_EXCLUDED)
    _insert(conn, "unsupported", published_at=NOW - timedelta(hours=1),
            status=Status.SKIPPED_UNSUPPORTED)
    _insert(conn, "failed", published_at=NOW - timedelta(hours=1),
            status=Status.FAILED)

    rep = _report(conn)
    assert rep.total == 4
    assert rep.new_count == 2
    assert rep.backfill_count == 2  # dated-old + undated
    assert {c["blob_id"] for c in rep.candidates} == {
        "new1", "new2", "back1", "back_undated"
    }
    assert "new=2 backfill=2" in rep.summary()


def test_empty_db_reports_zeroes(conn):
    rep = _report(conn)
    assert rep.total == 0 and rep.new_count == 0 and rep.backfill_count == 0
    assert rep.top == [] and rep.by_institution == []
    assert len(rep.by_day) == backlog.DAY_HISTOGRAM_DAYS
    assert all(n == 0 for _d, n in rep.by_day)
    assert "(none)" in backlog.render(rep)


# ---------------------------------------------------------------------------
# ordering — score first, recency second (the queue a new account would drain)
# ---------------------------------------------------------------------------
def test_top_is_ordered_by_score_then_recency(conn):
    _insert(conn, "junk_fresh", published_at=NOW - timedelta(minutes=5), score=0)
    _insert(conn, "gold_old", published_at=NOW - timedelta(hours=200), score=91)
    _insert(conn, "mid_new", published_at=NOW - timedelta(hours=1), score=50)
    _insert(conn, "mid_old", published_at=NOW - timedelta(hours=90), score=50)
    _insert(conn, "unscored", published_at=NOW - timedelta(hours=3), score=None)

    rep = _report(conn)
    # score first; within a score, newest first — so the two 0-value rows (an
    # explicit 0 and a NULL) rank against each other purely on recency.
    assert [c["blob_id"] for c in rep.top] == [
        "gold_old", "mid_new", "mid_old", "junk_fresh", "unscored",
    ]
    # a NULL score is reported as 0, never as None (the export is a work queue)
    assert rep.top[-1]["score"] == 0


def test_top_n_limits_the_printed_list_but_not_the_export(conn):
    for i in range(10):
        _insert(conn, f"p{i}", published_at=NOW - timedelta(hours=i + 1), score=i)
    rep = _report(conn, top_n=3)
    assert len(rep.top) == 3
    assert [c["blob_id"] for c in rep.top] == ["p9", "p8", "p7"]
    assert len(rep.candidates) == 10, "the full ledger is always retained"


# ---------------------------------------------------------------------------
# histograms
# ---------------------------------------------------------------------------
def test_by_day_covers_the_last_14_days_newest_first(conn):
    _insert(conn, "today1", published_at=NOW - timedelta(hours=1))
    _insert(conn, "today2", published_at=NOW - timedelta(hours=2))
    _insert(conn, "d3", published_at=NOW - timedelta(days=3))
    _insert(conn, "d13", published_at=NOW - timedelta(days=13))
    _insert(conn, "too_old", published_at=NOW - timedelta(days=40))  # outside window
    _insert(conn, "undated", published_at=None)                      # no day at all

    rep = _report(conn)
    days = dict(rep.by_day)
    assert len(rep.by_day) == 14
    assert rep.by_day[0][0] == "2026-07-27" and rep.by_day[-1][0] == "2026-07-14"
    assert days["2026-07-27"] == 2
    assert days["2026-07-24"] == 1
    assert days["2026-07-14"] == 1
    assert sum(days.values()) == 4, "old + undated rows are not in the histogram"
    assert rep.total == 6, "...but they ARE in the ledger"


def test_by_institution_is_top_15_biggest_first(conn):
    for i in range(4):
        _insert(conn, f"gs{i}", published_at=NOW - timedelta(hours=1),
                institution="Goldman Sachs")
    for i in range(2):
        _insert(conn, f"ms{i}", published_at=NOW - timedelta(hours=1),
                institution="Morgan Stanley")
    _insert(conn, "none1", published_at=NOW - timedelta(hours=1), institution=None)
    _insert(conn, "blank", published_at=NOW - timedelta(hours=1), institution="   ")

    rep = _report(conn)
    assert rep.by_institution[0] == ("Goldman Sachs", 4)
    # NULL and blank institutions collapse into one "(unknown)" bucket; equal
    # counts break by name ascending, so the order is deterministic across runs
    assert rep.by_institution[1:] == [("(unknown)", 2), ("Morgan Stanley", 2)]


def test_by_institution_caps_at_15(conn):
    for i in range(20):
        _insert(conn, f"p{i}", published_at=NOW - timedelta(hours=1),
                institution=f"House {i:02d}")
    rep = _report(conn)
    assert len(rep.by_institution) == backlog.TOP_INSTITUTIONS


# ---------------------------------------------------------------------------
# rendering + JSON export
# ---------------------------------------------------------------------------
def test_render_includes_the_headline_numbers(conn):
    _insert(conn, "gold", published_at=NOW - timedelta(hours=1), score=91,
            institution="Goldman Sachs", title="Semis initiation")
    _insert(conn, "old", published_at=NOW - timedelta(hours=100), score=5)
    out = backlog.render(_report(conn))
    assert "backlog: 2 candidates (new=1 backfill=1)" in out
    assert "Semis initiation" in out
    assert "Goldman Sachs" in out
    assert "2026-07-27" in out


def test_json_export_shape(conn, tmp_path):
    _insert(conn, "gold", published_at=NOW - timedelta(hours=1), score=91,
            institution="Goldman Sachs", title="Semis initiation")
    _insert(conn, "undated", published_at=None, score=None, institution=None,
            title=None, status=Status.BLOB_FOUND)

    rep = _report(conn, top_n=1)
    path = backlog.export_json(rep, tmp_path / "out" / "backlog.json")
    assert path.exists(), "export creates its parent directory"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["total"] == 2
    assert payload["new_count"] == 1 and payload["backfill_count"] == 1
    assert payload["new_window_hours"] == 48
    assert payload["generated_at"] == NOW.isoformat()
    # the FULL ledger is exported, not just the printed top N
    assert len(payload["candidates"]) == 2 and len(rep.top) == 1

    first = payload["candidates"][0]
    assert set(first) == {
        "blob_id", "title", "institution", "published_at", "score", "status"
    }
    assert first == {
        "blob_id": "gold",
        "title": "Semis initiation",
        "institution": "Goldman Sachs",
        "published_at": (NOW - timedelta(hours=1)).isoformat(),
        "score": 91,
        "status": Status.DISCOVERED.value,
    }
    undated = payload["candidates"][1]
    assert undated["published_at"] is None and undated["score"] == 0
    assert undated["status"] == Status.BLOB_FOUND.value


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------
def test_cli_backlog_prints_and_writes_json(tmp_path, monkeypatch, capsys):
    from marketdesk_extractor.cli import main

    for k, v in {
        "DATABASE_URL": str(tmp_path / "db" / "t.sqlite"),
        "OUTPUT_DIR": str(tmp_path / "data"),
        "RAW_PDF_DIR": str(tmp_path / "data" / "raw_pdfs"),
        "MARKDOWN_DIR": str(tmp_path / "data" / "markdown"),
        "METADATA_DIR": str(tmp_path / "data" / "metadata"),
        "MANIFEST_DIR": str(tmp_path / "data" / "manifests"),
        "LOG_DIR": str(tmp_path / "logs"),
        "MARKETDESK_PROFILE_DIR": str(tmp_path / "prof"),
        "NEW_WINDOW_HOURS": "48",
    }.items():
        monkeypatch.setenv(k, v)

    c = db.connect(tmp_path / "db" / "t.sqlite")
    db.init_db(c)
    _insert(c, "gold", published_at=NOW - timedelta(hours=1), score=91,
            institution="Goldman Sachs", title="Semis initiation")
    c.close()

    out_json = tmp_path / "backlog.json"
    rc = main(["backlog", "--top", "5", "--json", str(out_json)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog: 1 candidates" in out
    assert "Semis initiation" in out
    assert json.loads(out_json.read_text(encoding="utf-8"))["total"] == 1
