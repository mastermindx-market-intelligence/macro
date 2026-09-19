from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from marketdesk_extractor.feed_probe import (
    FeedProbeTimeout,
    _run_command,
    read_vault_state,
)


def _database(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE papers (vaulted_at TEXT)")
    conn.executemany(
        "INSERT INTO papers(vaulted_at) VALUES (?)",
        [
            ("2026-09-09T21:20:21+00:00",),
            ("2026-09-14T09:40:00+00:00",),
            (None,),
        ],
    )
    conn.commit()
    conn.close()
    return path


def test_read_vault_state_returns_newest_and_count_after_watermark(tmp_path: Path) -> None:
    database = _database(tmp_path / "marketdesk.sqlite")

    state = read_vault_state(
        database,
        "2026-09-10T00:00:00+00:00",
        timeout_seconds=1,
    )

    assert state.database == database
    assert state.newest == "2026-09-14T09:40:00+00:00"
    assert state.count == 1


def test_read_vault_state_times_out_a_stalled_database_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "marketdesk.sqlite"
    database.touch()

    def stalled_connect(*args, **kwargs):
        time.sleep(5)
        raise AssertionError("deadline failed to interrupt stalled connect")

    monkeypatch.setattr(sqlite3, "connect", stalled_connect)
    started = time.monotonic()

    with pytest.raises(FeedProbeTimeout):
        read_vault_state(database, "1970-01-01T00:00:00+00:00", timeout_seconds=0.05)

    assert time.monotonic() - started < 1


def test_probe_supervisor_kills_a_worker_stuck_in_open() -> None:
    started = time.monotonic()

    with pytest.raises(FeedProbeTimeout):
        _run_command(["/bin/sh", "-c", "sleep 5"], timeout_seconds=0.05)

    assert time.monotonic() - started < 1
