"""B1 — the durable CLI stamps its own wall clock; committed events keep theirs.

Closes the D07 S3-episode-registry gap (recorded_at is "caller-supplied ... not
stamped by the writer at write time"): the command line can no longer steer a
durable nightly generation with a caller clock, and a durable run provably
carries the writer's own `_now()` clock while already-committed events keep
their first-written clock. Fixtures and helpers are reused from
tests/test_us_candidate_episode_reconciler.py.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.us_candidate_episode import canonical_json
from scripts import reconcile_us_candidate_episodes as writer
from tests.test_us_candidate_episode_reconciler import (
    RECORDED_AT,
    _event_rows,
    _rehash_turn_watch,
    _seed_sources,
    _snapshot,
    _turn_path,
)


CLOCK_LATER = "2026-11-27T18:06:00Z"


def _run_durable_cli(repo_root: Path, monkeypatch) -> int:
    """One durable CLI run with the lane gate open and no --recorded-at."""
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    return writer.main(["--nightly", "--repo-root", str(repo_root)])


def _patch_writer_clock(monkeypatch, *clocks: str) -> list[str]:
    """Serve fixed writer clocks one per run and record every _now() call."""
    remaining = list(clocks)
    calls: list[str] = []

    def fixed_now() -> str:
        calls.append(remaining.pop(0))
        return calls[-1]

    monkeypatch.setattr(writer, "_now", fixed_now)
    return calls


def test_cli_durable_recorded_at_is_refused_before_any_read_or_write(
    tmp_path: Path, monkeypatch, capsys
):
    """A caller clock must never steer a durable generation (D07 S3 gap)."""
    load_calls: list[str] = []

    def forbidden_load(*args, **kwargs):
        load_calls.append("read")
        raise AssertionError("_load_and_build ran before the durable clock refusal")

    def forbidden_publish(*args, **kwargs):
        raise AssertionError("publication ran before the durable clock refusal")

    monkeypatch.setattr(writer, "_load_and_build", forbidden_load)
    monkeypatch.setattr(writer, "_publish_transaction", forbidden_publish)

    with pytest.raises(
        writer.ReconcileRefused,
        match="durable write refused: --recorded-at is a report/replay override;",
    ):
        writer.main([
            "--nightly", "--recorded-at", RECORDED_AT,
            "--repo-root", str(tmp_path),
        ])

    assert load_calls == []
    assert capsys.readouterr().out == ""
    assert _snapshot(tmp_path) == {}


def test_cli_durable_recorded_at_exits_nonzero_without_a_receipt(tmp_path: Path):
    """The refusal is a failed CLI run printing no receipt, not a warning."""
    repo_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [
            sys.executable, "-m", "scripts.reconcile_us_candidate_episodes",
            "--nightly", "--recorded-at", RECORDED_AT,
            "--repo-root", str(tmp_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "durable write refused: --recorded-at is a report/replay override;" in completed.stderr
    assert _snapshot(tmp_path) == {}


def test_cli_replay_with_recorded_at_is_allowed_and_read_only(
    tmp_path: Path, capsys
):
    """Replay keeps its caller clock: it re-reads history, never writes it."""
    _seed_sources(tmp_path)
    before = _snapshot(tmp_path)

    exit_code = writer.main([
        "--nightly", "--replay", "--recorded-at", RECORDED_AT,
        "--repo-root", str(tmp_path),
    ])

    receipt = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert receipt["mode"] == "replay"
    assert receipt["recorded_at"] == RECORDED_AT
    assert receipt["durable_write"] is False
    assert _snapshot(tmp_path) == before


def test_cli_report_with_recorded_at_is_allowed_and_read_only(
    tmp_path: Path, capsys
):
    """Report mode keeps its caller clock for the same read-only reason."""
    _seed_sources(tmp_path)
    before = _snapshot(tmp_path)

    exit_code = writer.main([
        "--recorded-at", RECORDED_AT, "--repo-root", str(tmp_path),
    ])

    receipt = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert receipt["mode"] == "report"
    assert receipt["recorded_at"] == RECORDED_AT
    assert receipt["durable_write"] is False
    assert _snapshot(tmp_path) == before


def test_cli_durable_without_override_stamps_the_writer_clock_once(
    tmp_path: Path, monkeypatch, capsys
):
    """A durable run without --recorded-at stamps _now() exactly once."""
    _seed_sources(tmp_path)
    clock_calls = _patch_writer_clock(monkeypatch, RECORDED_AT)

    exit_code = _run_durable_cli(tmp_path, monkeypatch)

    assert exit_code == 0
    assert clock_calls == [RECORDED_AT]
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["recorded_at"] == RECORDED_AT
    events = _event_rows(tmp_path)
    assert [event["event_type"] for event in events] == ["OPENED"]
    assert [event["recorded_at"] for event in events] == [RECORDED_AT]


def test_second_durable_run_keeps_committed_clocks_and_stamps_only_new_events(
    tmp_path: Path, monkeypatch, capsys
):
    """A later durable run re-derives committed events with their first clock."""
    _seed_sources(tmp_path)
    clock_calls = _patch_writer_clock(monkeypatch, RECORDED_AT, CLOCK_LATER)

    assert _run_durable_cli(tmp_path, monkeypatch) == 0
    first_receipt = json.loads(capsys.readouterr().out)
    assert first_receipt["recorded_at"] == RECORDED_AT
    assert [event["recorded_at"] for event in _event_rows(tmp_path)] == [RECORDED_AT]

    document = json.loads(_turn_path(tmp_path).read_text())
    document["rows"][0]["observation_revision"] = 2
    _turn_path(tmp_path).write_text(canonical_json(_rehash_turn_watch(document)) + "\n")

    assert _run_durable_cli(tmp_path, monkeypatch) == 0

    second_receipt = json.loads(capsys.readouterr().out)
    events = _event_rows(tmp_path)
    assert sorted(event["event_type"] for event in events) == ["OBSERVED", "OPENED"]
    committed = next(event for event in events if event["event_type"] == "OPENED")
    appended = next(event for event in events if event["event_type"] == "OBSERVED")
    assert committed["recorded_at"] == RECORDED_AT
    assert appended["recorded_at"] == CLOCK_LATER
    assert second_receipt["recorded_at"] == CLOCK_LATER
    assert second_receipt["counts"]["appended_events"] == 1
    assert clock_calls == [RECORDED_AT, CLOCK_LATER]


def test_main_docstring_pins_the_writer_clock_contract():
    """The CLI states the rule where the CLI is entered."""
    doc = writer.main.__doc__ or ""
    assert "stamps its own wall clock" in doc
    assert "report/replay override only" in doc


def test_cli_durable_recorded_at_refusal_is_one_stderr_line_not_a_traceback(tmp_path: Path):
    """B01 review F1: the refusal exits 2 with one `reconcile refused:` line and no traceback."""
    repo_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [
            sys.executable, "-m", "scripts.reconcile_us_candidate_episodes",
            "--nightly", "--recorded-at", RECORDED_AT,
            "--repo-root", str(tmp_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "Traceback" not in completed.stderr
    assert completed.stderr.rstrip("\n").splitlines()[-1] == (
        "reconcile refused: durable write refused: --recorded-at is a report/replay override; "
        "the durable writer stamps its own wall clock"
    )
    assert _snapshot(tmp_path) == {}
