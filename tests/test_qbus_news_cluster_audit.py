"""Read-only audit harness for stored and fixture news clusters."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from engine.qkernel import title_similarity
from engine.qbus_news_cluster import ClusterPolicy
from engine.qbus_news_contract import normalize_news
from engine import qbus_news_store as store_mod
import scripts.qbus_news_cluster_audit as audit

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qbus_news_cluster_audit.py"
UTC = timezone.utc
T0 = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)
POLICY_KEYS = ("title_threshold", "window_seconds", "max_candidates")
REPORT_KEYS = (
    "schema",
    "clusters",
    "multi_member_clusters",
    "size_histogram",
    "near_misses",
    "joined_with_number_mismatch",
    "policy",
)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _story(
    story_id: str,
    title: str,
    *,
    minute: int = 0,
    subjects: list[str] | None = None,
    cluster_id: str | None = None,
    family: str = "company",
) -> dict:
    row = {
        "story_id": story_id,
        "title": title,
        "observed_at": (T0 + timedelta(minutes=minute)).isoformat(),
        "subject_ids": subjects or ["sec-NVDA"],
        "event_family": family,
    }
    if cluster_id is not None:
        row["cluster_id"] = cluster_id
    return row


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _assert_report_shape(report: dict) -> None:
    assert list(report) == list(REPORT_KEYS)
    assert report["schema"] == "qbus.news_cluster_audit.v1"
    assert list(report["policy"]) == list(POLICY_KEYS)
    policy = ClusterPolicy()
    assert report["policy"] == {
        "title_threshold": policy.title_threshold,
        "window_seconds": policy.window_seconds,
        "max_candidates": policy.max_candidates,
    }


def test_jsonl_replay_reports_join_and_period_near_miss(tmp_path):
    """Skipping period_mismatch, or replaying joins as new, changes this report."""
    path = tmp_path / "stories.jsonl"
    rows = [
        _story("benzinga:1", "Apple unveils new product line for developers"),
        _story("reuters:9", "Apple unveils new product line for developers", minute=1),
        _story("benzinga:2", "Apple reports Q2 revenue growth this season", minute=2),
        _story("benzinga:3", "Apple reports Q3 revenue growth this season", minute=3),
    ]
    _write_jsonl(path, rows)
    proc = _run(["--jsonl", str(path)])
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    report = json.loads(proc.stdout)
    _assert_report_shape(report)
    assert report["clusters"] == 3
    assert report["multi_member_clusters"] == 1
    assert report["size_histogram"] == {"1": 2, "2": 1}
    assert report["joined_with_number_mismatch"] == []
    pair = next(
        row
        for row in report["near_misses"]
        if {row["a_story"], row["b_story"]} == {"benzinga:2", "benzinga:3"}
    )
    assert pair["a_story"] == "benzinga:2"
    assert pair["b_story"] == "benzinga:3"
    assert pair["reason"] == "period_mismatch"
    assert pair["similarity"] == title_similarity(rows[2]["title"], rows[3]["title"])
    assert [row["similarity"] for row in report["near_misses"]] == sorted(
        (row["similarity"] for row in report["near_misses"]), reverse=True
    )


def test_labeled_jsonl_keeps_a_stored_number_mismatch(tmp_path):
    """Reclustering the fixture instead of trusting cluster_id hides the mismatch."""
    path = tmp_path / "labeled.jsonl"
    _write_jsonl(
        path,
        [
            _story(
                "benzinga:1",
                "Nvidia guides revenue to $8.2B",
                cluster_id="ev2_bad",
            ),
            _story(
                "benzinga:2",
                "Nvidia guides revenue to $9.1B",
                minute=1,
                cluster_id="ev2_bad",
            ),
        ],
    )
    report = audit.audit_jsonl(path)
    _assert_report_shape(report)
    assert report["clusters"] == 1
    assert report["multi_member_clusters"] == 1
    assert report["near_misses"] == []
    assert report["joined_with_number_mismatch"] == [
        {
            "cluster_id": "ev2_bad",
            "a_story": "benzinga:1",
            "b_story": "benzinga:2",
            "a_numbers": ["$8.2b"],
            "b_numbers": ["$9.1b"],
        }
    ]


def test_near_miss_list_is_capped_at_50_and_ordered(tmp_path):
    """A cap of 51, or a similarity-ascending sort, fails the expected prefix."""
    rows = [
        _story(
            f"src:{index:02d}",
            "Apple unveils new product line for developers",
            cluster_id=f"ev2_{index:02d}",
        )
        for index in range(12)
    ]
    path = tmp_path / "cap.jsonl"
    _write_jsonl(path, rows)
    report = audit.audit_jsonl(path)
    expected = []
    for left in range(12):
        for right in range(left + 1, 12):
            expected.append((f"src:{left:02d}", f"src:{right:02d}"))
    expected.sort()
    assert len(expected) == 66
    got = [(row["a_story"], row["b_story"]) for row in report["near_misses"]]
    assert got == expected[:50]
    assert {row["reason"] for row in report["near_misses"]} == {"passed_gates_unjoined"}
    assert {row["similarity"] for row in report["near_misses"]} == {1.0}


def test_near_miss_window_matches_cluster_boundary(tmp_path):
    """Using >= to reject the window drops the pair that sits exactly on it."""
    window = ClusterPolicy().window_seconds
    inside = tmp_path / "inside.jsonl"
    outside = tmp_path / "outside.jsonl"
    left = _story("benzinga:1", "Alpha copper warehouse note", cluster_id="ev2_a")
    right = _story("benzinga:2", "Beta wheat harvest note", cluster_id="ev2_b")
    right["observed_at"] = (T0 + timedelta(seconds=window)).isoformat()
    _write_jsonl(inside, [left, right])
    right_out = dict(right)
    right_out["observed_at"] = (T0 + timedelta(seconds=window + 1)).isoformat()
    _write_jsonl(outside, [left, right_out])
    inside_report = audit.audit_jsonl(inside)
    outside_report = audit.audit_jsonl(outside)
    assert [(row["a_story"], row["b_story"]) for row in inside_report["near_misses"]] == [
        ("benzinga:1", "benzinga:2")
    ]
    assert outside_report["near_misses"] == []


def test_mixed_cluster_ids_are_rejected(tmp_path):
    path = tmp_path / "mixed.jsonl"
    _write_jsonl(
        path,
        [
            _story("benzinga:1", "Apple unveils a chip", cluster_id="ev2_a"),
            _story("benzinga:2", "Apple unveils a chip", minute=1),
        ],
    )
    proc = _run(["--jsonl", str(path)])
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "qbus_news_cluster_audit:mixed_cluster_ids" in proc.stderr


def test_cli_requires_one_source_and_a_real_file(tmp_path):
    missing = _run([])
    assert missing.returncode == 2
    both = _run(["--store", str(tmp_path / "a.sqlite3"), "--jsonl", str(tmp_path / "a.jsonl")])
    assert both.returncode == 2
    absent = _run(["--store", str(tmp_path / "missing.sqlite3")])
    assert absent.returncode == 2
    assert "qbus_news_cluster_audit:not_a_file" in absent.stderr
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json}\n", encoding="utf-8")
    invalid = _run(["--jsonl", str(bad)])
    assert invalid.returncode == 2
    assert "qbus_news_cluster_audit:jsonl_invalid:1" in invalid.stderr


def _build_fixture_store(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE news_clusters (
            cluster_id TEXT PRIMARY KEY,
            anchor_story_id TEXT NOT NULL,
            anchor_title TEXT NOT NULL,
            anchor_observed_at TEXT NOT NULL,
            subject_ids_json TEXT NOT NULL,
            event_family TEXT NOT NULL
        );
        CREATE TABLE news_cluster_members (
            source TEXT NOT NULL,
            source_item_id TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            story_id TEXT NOT NULL,
            PRIMARY KEY (source, source_item_id)
        );
        CREATE TABLE news_state_projection (
            source TEXT NOT NULL,
            source_item_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            teaser TEXT NOT NULL,
            published_at TEXT,
            updated_at TEXT,
            received_at TEXT NOT NULL,
            PRIMARY KEY (source, source_item_id)
        );
        """
    )
    when = T0.isoformat()
    for cluster_id, story_id, title in (
        ("ev2_bad", "benzinga:1", "Nvidia guides revenue to $8.2B"),
        ("ev2_solo", "benzinga:3", "Nvidia CFO resigns abruptly"),
        ("ev2_empty", "benzinga:9", "Unused anchor"),
    ):
        connection.execute(
            """
            INSERT INTO news_clusters (
                cluster_id, anchor_story_id, anchor_title,
                anchor_observed_at, subject_ids_json, event_family
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cluster_id, story_id, title, when, '["sec-NVDA"]', "company"),
        )
    members = (
        ("benzinga", "1", "ev2_bad", "benzinga:1", "Nvidia guides revenue to $8.2B", 0),
        ("benzinga", "2", "ev2_bad", "benzinga:2", "Nvidia guides revenue to $9.1B", 1),
        ("benzinga", "3", "ev2_solo", "benzinga:3", "Nvidia CFO resigns abruptly", 2),
    )
    for source, source_item_id, cluster_id, story_id, title, minute in members:
        connection.execute(
            """
            INSERT INTO news_cluster_members (
                source, source_item_id, cluster_id, story_id
            ) VALUES (?, ?, ?, ?)
            """,
            (source, source_item_id, cluster_id, story_id),
        )
        connection.execute(
            """
            INSERT INTO news_state_projection (
                source, source_item_id, title, url, teaser,
                published_at, updated_at, received_at
            ) VALUES (?, ?, ?, '', '', NULL, NULL, ?)
            """,
            (source, source_item_id, title, (T0 + timedelta(minutes=minute)).isoformat()),
        )
    connection.commit()
    connection.close()


def test_store_audit_is_read_only_and_flags_number_mismatch(tmp_path):
    """A writable open, or ignoring joined number sets, fails this fixture."""
    database = tmp_path / "news.sqlite3"
    _build_fixture_store(database)
    before = database.read_bytes()
    names_before = sorted(path.name for path in tmp_path.iterdir())
    proc = _run(["--store", str(database)])
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert database.read_bytes() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == names_before
    digest = hashlib.sha256(before).hexdigest()
    assert hashlib.sha256(database.read_bytes()).hexdigest() == digest
    report = json.loads(proc.stdout)
    _assert_report_shape(report)
    assert report["clusters"] == 3
    assert report["multi_member_clusters"] == 1
    assert report["size_histogram"] == {"0": 1, "1": 1, "2": 1}
    assert report["joined_with_number_mismatch"] == [
        {
            "cluster_id": "ev2_bad",
            "a_story": "benzinga:1",
            "b_story": "benzinga:2",
            "a_numbers": ["$8.2b"],
            "b_numbers": ["$9.1b"],
        }
    ]
    reasons = {tuple(sorted((row["a_story"], row["b_story"]))): row["reason"] for row in report["near_misses"]}
    assert reasons[("benzinga:1", "benzinga:3")] == "below_title_threshold"
    assert reasons[("benzinga:2", "benzinga:3")] == "below_title_threshold"
    ro = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError):
            ro.execute("INSERT INTO news_clusters (cluster_id) VALUES ('x')")
    finally:
        ro.close()
    assert database.read_bytes() == before


def _routed(item_id: int, title: str, minute: int = 0):
    updated = datetime(2026, 10, 5, 15, 0, tzinfo=UTC) + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (updated - timedelta(seconds=1)).isoformat(),
            "updated": updated.isoformat(),
            "title": title,
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=updated + timedelta(seconds=2),
    )
    return store_mod.RoutedRevision(
        revision=revision,
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )


def test_news_store_file_audits_without_rewriting_bytes(tmp_path):
    """The audit of a real NewsStore must not rewrite the database bytes."""
    database = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(database, source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(1, "Nvidia launches new AI accelerator"),
                _routed(2, "Nvidia launches its new AI accelerator", 1),
                _routed(3, "Nvidia CFO resigns", 2),
            ],
            expected_cursor=None,
            next_cursor="1",
        )
    before = database.read_bytes()
    proc = _run(["--store", str(database)])
    assert proc.returncode == 0, proc.stderr
    assert database.read_bytes() == before
    report = json.loads(proc.stdout)
    _assert_report_shape(report)
    assert report["clusters"] == 2
    assert report["multi_member_clusters"] == 1
    assert report["size_histogram"] == {"1": 1, "2": 1}
    assert report["joined_with_number_mismatch"] == []
    assert len(report["near_misses"]) == 2


def test_audit_source_does_not_write_or_read_env():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'sqlite3.connect(uri, uri=True)' in text or "mode=ro" in text
    assert "file:{path.resolve()}?mode=ro" in text
    for banned in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "os.environ", "requests."):
        assert banned not in text
    assert "news_clusters" in text
    assert "news_cluster_members" in text
    assert "news_state_projection" in text
    assert "news_states" not in text
    assert "news_revisions" not in text
