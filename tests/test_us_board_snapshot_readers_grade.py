"""Pins the grader and five readers of the US board snapshots ledger.

Each ``*_reads_rows_in_snapshot_parts`` test builds a base file plus
``snapshots_parts/`` and requires a row that exists only in a part. A reader
that still opens ``snapshots.jsonl`` alone fails that test. The append test
pins that once a part exists the grader leaves the base bytes alone. The
fusion gap test pins fail-closed ``RaceRefusal``. The pit-replay tests pin
the vintage runner: parts when ``engine/us_board_snapshots.py`` is in the
tree, and the base file when that module is not.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from engine import us_board_snapshots
from scripts import grade_bottom_calls
from scripts import grade_us_board
from scripts import prophet_fusion_race
from scripts import prophet_pit_replay
from scripts import prophet_postmortem
from scripts import replay_standout_books


def _line(row: dict) -> str:
    return json.dumps(row, separators=(",", ":")) + "\n"


def _board(as_of: str, ticker: str) -> dict:
    """The smallest board row these readers keep: an as_of and one buy ticker."""
    return {"as_of": as_of, "buy": [{"ticker": ticker}]}


def _layout(parent: Path, base_rows: list[dict], *parts: list[dict]) -> Path:
    ledger = parent / "us_board_ledger"
    ledger.mkdir(parents=True)
    base = ledger / "snapshots.jsonl"
    base.write_text("".join(_line(row) for row in base_rows), encoding="utf-8")
    if parts:
        directory = ledger / "snapshots_parts"
        directory.mkdir()
        for index, rows in enumerate(parts, start=1):
            (directory / f"part-{index:06d}.jsonl").write_text(
                "".join(_line(row) for row in rows), encoding="utf-8")
    return base


def _grade_paths(monkeypatch: pytest.MonkeyPatch, base: Path) -> None:
    monkeypatch.setattr(grade_us_board, "SNAPSHOTS_JSONL", base)
    monkeypatch.setattr(grade_us_board, "LEDGER_DIR", base.parent)


def _postmortem_root(tmp_path: Path, *parts: list[dict]) -> Path:
    _layout(
        tmp_path / "data",
        [_board("2026-10-01", "AAA")],
        [_board("2026-10-02", "BBB")],
        *parts,
    )
    return tmp_path


def test_grade_us_board_collect_boards_reads_rows_in_snapshot_parts(tmp_path, monkeypatch):
    base = _layout(
        tmp_path,
        [_board("2026-10-01", "AAA")],
        [_board("2026-10-02", "BBB")],
        [_board("2026-10-03", "CCC")],
    )
    _grade_paths(monkeypatch, base)
    monkeypatch.setattr(grade_us_board, "_git_revisions", lambda: [])
    boards = grade_us_board.collect_boards({})
    by_as_of = {board["as_of"]: board for board in boards}
    assert by_as_of["2026-10-01"]["rows"][0]["ticker"] == "AAA"
    assert by_as_of["2026-10-03"]["rows"][0]["ticker"] == "CCC"


def test_grade_us_board__snapshot_existing_as_of_reads_rows_in_snapshot_parts(
    tmp_path, monkeypatch,
):
    base = _layout(
        tmp_path,
        [_board("2026-10-01", "AAA")],
        [_board("2026-10-02", "BBB")],
    )
    _grade_paths(monkeypatch, base)
    assert grade_us_board._snapshot_existing_as_of() == {"2026-10-01", "2026-10-02"}


def test_grade_us_board__append_snapshot_row_appends_into_existing_part(
    tmp_path, monkeypatch,
):
    base_row = _board("2026-10-01", "AAA")
    part_row = _board("2026-10-02", "BBB")
    new_row = _board("2026-10-04", "NNN")
    base = _layout(tmp_path, [base_row], [part_row])
    _grade_paths(monkeypatch, base)
    before = hashlib.sha256(base.read_bytes()).hexdigest()
    grade_us_board._append_snapshot_row(new_row)
    assert hashlib.sha256(base.read_bytes()).hexdigest() == before
    part = base.parent / "snapshots_parts" / "part-000001.jsonl"
    assert part.read_text(encoding="utf-8").splitlines()[-1] == json.dumps(
        new_row, separators=(",", ":"))
    assert grade_us_board._snapshot_existing_as_of() == {
        "2026-10-01", "2026-10-02", "2026-10-04"}


def test_grade_bottom_calls__read_snapshots_reads_rows_in_snapshot_parts(
    tmp_path, monkeypatch,
):
    base = _layout(
        tmp_path,
        [_board("2026-10-01", "AAA")],
        [_board("2026-10-02", "BBB")],
    )
    monkeypatch.setattr(grade_bottom_calls, "SNAPSHOTS_JSONL", base)
    rows = grade_bottom_calls._read_snapshots()
    assert {row["as_of"] for row in rows} == {"2026-10-01", "2026-10-02"}
    assert rows[-1]["buy"][0]["ticker"] == "BBB"


def test_prophet_postmortem_load_snapshots_reads_rows_in_snapshot_parts(tmp_path):
    root = _postmortem_root(tmp_path, [_board("2026-10-03", "CCC")])
    snaps = prophet_postmortem.load_snapshots(root)
    assert snaps["2026-10-01"]["AAA"]["ticker"] == "AAA"
    assert snaps["2026-10-03"]["CCC"]["ticker"] == "CCC"


def test_prophet_postmortem_board_days_reads_rows_in_snapshot_parts(tmp_path):
    root = _postmortem_root(tmp_path)
    days = prophet_postmortem.board_days(pd.DataFrame(), {}, root)
    assert days["2026-10-01"] == {"AAA"}
    assert days["2026-10-02"] == {"BBB"}


def test_prophet_postmortem_load_snapshot_membership_reads_rows_in_snapshot_parts(tmp_path):
    root = _postmortem_root(tmp_path, [_board("2026-10-03", "CCC")])
    members, status = prophet_postmortem.load_snapshot_membership(root)
    assert status["readable"] is True
    assert status["error"] is None
    assert "AAA" in members["2026-10-01"]
    assert "CCC" in members["2026-10-03"]


def test_replay_standout_books__load_us_snapshots_reads_rows_in_snapshot_parts(tmp_path):
    data_dir = tmp_path / "data"
    _layout(
        data_dir,
        [_board("2026-10-01", "AAA")],
        [_board("2026-10-02", "BBB")],
    )
    rows, err = replay_standout_books._load_us_snapshots(data_dir)
    assert err is None
    assert [row["as_of"] for row in rows] == ["2026-10-01", "2026-10-02"]
    assert rows[-1]["buy"][0]["ticker"] == "BBB"


def test_prophet_fusion_race_load_snapshots_reads_rows_in_snapshot_parts(tmp_path):
    base = _layout(
        tmp_path,
        [_board("2026-10-01", "AAA")],
        [_board("2026-10-02", "BBB")],
        [_board("2026-10-03", "CCC")],
    )
    snaps = prophet_fusion_race.load_snapshots(base)
    assert snaps["2026-10-01"]["buy"][0]["ticker"] == "AAA"
    assert snaps["2026-10-03"]["buy"][0]["ticker"] == "CCC"


def test_prophet_fusion_race_load_snapshots_gap_raises_race_refusal(tmp_path):
    base = _layout(tmp_path, [_board("2026-10-01", "AAA")])
    parts = base.parent / "snapshots_parts"
    parts.mkdir()
    (parts / "part-000002.jsonl").write_text(
        _line(_board("2026-10-03", "CCC")), encoding="utf-8")
    with pytest.raises(prophet_fusion_race.RaceRefusal, match="unreadable"):
        prophet_fusion_race.load_snapshots(base)


def _vintage_tree(tmp_path: Path, session: str, *, copy_reader: bool) -> Path:
    """A fake vintage whose grade_us_board stub returns ``session`` and nothing else.

    ``engine/__init__.py`` makes ``engine`` the vintage's own package, so a
    seat that has this repo on ``sys.path`` cannot satisfy the import from
    the orchestrator tree. Without ``us_board_snapshots.py`` that import
    raises ``ImportError`` and the runner uses the base-file fallback.
    """
    vintage = tmp_path / "vintage"
    scripts = vintage / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "__init__.py").write_text("", encoding="utf-8")
    (scripts / "grade_us_board.py").write_text(
        "from pathlib import Path\n"
        "SNAPSHOTS_JSONL = Path(__file__).resolve().parents[1] / "
        "\"data\" / \"us_board_ledger\" / \"snapshots.jsonl\"\n"
        "def snapshot_today():\n"
        f"    return {session!r}\n",
        encoding="utf-8",
    )
    engine = vintage / "engine"
    engine.mkdir()
    (engine / "__init__.py").write_text("", encoding="utf-8")
    if copy_reader:
        text = Path(us_board_snapshots.__file__).read_text()
        (engine / "us_board_snapshots.py").write_text(text, encoding="utf-8")
    return vintage


def test_prophet_pit_replay_capture_us_snapshot_row_reads_rows_in_snapshot_parts(tmp_path):
    session = "2026-10-02"
    part_row = _board(session, "BBB")
    vintage = _vintage_tree(tmp_path, session, copy_reader=True)
    _layout(vintage / "data", [_board("2026-10-01", "AAA")], [part_row])
    work = tmp_path / "work"
    work.mkdir()
    result = prophet_pit_replay.capture_us_snapshot_row(
        vintage, session=session, work=work)
    assert result == {"ok": True, "row": part_row}


def test_prophet_pit_replay_capture_us_snapshot_row_falls_back_to_base_file(tmp_path):
    session = "2026-10-01"
    base_row = _board(session, "AAA")
    vintage = _vintage_tree(tmp_path, session, copy_reader=False)
    assert not (vintage / "engine" / "us_board_snapshots.py").exists()
    # Same as_of in a part. The fallback never opens parts, so the base row wins.
    # A runner that imported the real module would return the part row instead.
    _layout(
        vintage / "data",
        [base_row],
        [_board(session, "DECOY")],
    )
    work = tmp_path / "work"
    work.mkdir()
    result = prophet_pit_replay.capture_us_snapshot_row(
        vintage, session=session, work=work)
    assert result == {"ok": True, "row": base_row}
