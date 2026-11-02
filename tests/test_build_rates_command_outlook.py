"""The board builder publishes the regime-outlook projection beside the board (slice E1c4).

Imports ``scripts/build_rates_command.py`` as a module and drives
``_attach_regime_outlook`` against the golden owner files written under a
temporary data directory. Never runs the script itself and never writes
under ``data/`` or ``site/``.
"""

from __future__ import annotations

import importlib
import inspect
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

brc = importlib.import_module("scripts.build_rates_command")
from engine import rates_command_outlook as rco  # noqa: E402
from engine import rates_command_outlook_compose as roc  # noqa: E402
from lib import nyse_calendar  # noqa: E402

GOLDEN = json.loads(
    (REPO / "tests" / "fixtures" / "regime_outlook" / "readings_golden_v2.json").read_text(
        encoding="utf-8"
    )
)
MAPPING = rco.load_mapping()
WARNING_HEAD = "::warning title=regime-outlook-compose-failed::"


def _write_owner_files(data_dir: Path, *, omit: frozenset[str] = frozenset()) -> None:
    """Write the golden base bytes of every owner under ``data_dir`` (minus ``omit``)."""
    for letter, rel in MAPPING["artifacts"].items():
        if letter in omit:
            continue
        parts = Path(rel).parts
        assert parts[0] == "data", rel
        target = data_dir.joinpath(*parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(GOLDEN["base"][letter]), encoding="utf-8")


def _board() -> dict:
    return {"asof": "2026-10-02", "stance": {}, "changes": [], "prev_state": None}


def _warning_lines(captured: str) -> list[str]:
    return [line for line in captured.splitlines() if line.startswith(WARNING_HEAD)]


# --- T1 ----------------------------------------------------------------------


def test_happy_path_writes_the_projection_beside_the_board(tmp_path):
    _write_owner_files(tmp_path)
    artifact = _board()
    before = json.loads(json.dumps(artifact))

    brc._attach_regime_outlook(artifact, None, tmp_path)

    proj = artifact["regime_outlook"]
    assert proj["schema_version"] == "regime_outlook.v1"
    assert len(proj["evidence"]) == 30
    assert len(proj["conditional_paths"]) == 9
    assert len(proj["authority"]) == 6
    assert set(proj["authority"].values()) == {False}
    assert set(proj["inputs"]) == set(MAPPING["artifacts"])
    assert all(rec["read_status"] == "available" for rec in proj["inputs"].values())
    assert proj["baseline"] == {"status": "absent", "reason": "no_earlier_projection"}
    for key, value in before.items():
        assert artifact[key] == value, key
    assert set(artifact) == set(before) | {"regime_outlook"}
    assert json.loads(json.dumps(artifact))["regime_outlook"] == proj


# --- T2 ----------------------------------------------------------------------


def test_a_missing_owner_file_is_reported_and_the_key_is_still_written(tmp_path):
    _write_owner_files(tmp_path, omit=frozenset({"L"}))
    artifact = _board()

    brc._attach_regime_outlook(artifact, None, tmp_path)

    proj = artifact["regime_outlook"]
    assert proj["inputs"]["L"]["read_status"] == "missing"
    assert proj["inputs"]["L"]["sha256"] is None
    assert len(proj["evidence"]) == 30
    assert all(
        rec["read_status"] == "available" for letter, rec in proj["inputs"].items() if letter != "L"
    )


# --- T3 ----------------------------------------------------------------------


def test_second_build_takes_the_first_read_as_baseline(tmp_path, monkeypatch):
    _write_owner_files(tmp_path)
    first_artifact = _board()
    brc._attach_regime_outlook(first_artifact, None, tmp_path)
    first = first_artifact["regime_outlook"]
    first_cutoff = datetime.fromisoformat(first["analysis_cutoff"])
    first_session = nyse_calendar.expected_last_session(first_cutoff)

    def later_session_for_later_cutoffs(now=None):
        when = now if now is not None else datetime.now(timezone.utc)
        if when <= first_cutoff:
            return first_session
        return first_session + timedelta(days=1)

    monkeypatch.setattr(nyse_calendar, "expected_last_session", later_session_for_later_cutoffs)

    second_artifact = _board()
    brc._attach_regime_outlook(second_artifact, {"regime_outlook": first}, tmp_path)

    baseline = second_artifact["regime_outlook"]["baseline"]
    assert baseline["us_session"] == first_session.isoformat()
    assert baseline["analysis_cutoff"] == first["analysis_cutoff"]
    assert set(baseline["evidence"]) == {row["id"] for row in first["evidence"]}


# --- T4 / T5 -----------------------------------------------------------------


def _previous_read() -> dict:
    return {
        "schema_version": "regime_outlook.v1",
        "analysis_cutoff": "2026-10-01T02:00:00+00:00",
        "evidence": [],
        "marker": "the earlier read",
    }


def test_a_compose_failure_carries_the_previous_read_forward(tmp_path, monkeypatch, capsys):
    _write_owner_files(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(roc, "compose_outlook", boom)
    previous = _previous_read()
    artifact = _board()
    before = json.loads(json.dumps(artifact))

    brc._attach_regime_outlook(artifact, {"regime_outlook": previous}, tmp_path)

    assert artifact["regime_outlook"] == previous
    for key, value in before.items():
        assert artifact[key] == value, key
    lines = _warning_lines(capsys.readouterr().out)
    assert len(lines) == 1
    assert lines[0] == WARNING_HEAD + "RuntimeError: boom"


def test_a_compose_failure_with_no_previous_read_leaves_the_key_absent(tmp_path, monkeypatch, capsys):
    _write_owner_files(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(roc, "compose_outlook", boom)
    artifact = _board()
    before = json.loads(json.dumps(artifact))

    brc._attach_regime_outlook(artifact, None, tmp_path)

    assert "regime_outlook" not in artifact
    assert artifact == before
    lines = _warning_lines(capsys.readouterr().out)
    assert len(lines) == 1
    assert lines[0] == WARNING_HEAD + "RuntimeError: boom"


def test_a_previous_board_without_the_key_is_treated_as_no_previous(tmp_path, monkeypatch, capsys):
    _write_owner_files(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(roc, "compose_outlook", boom)
    artifact = _board()

    brc._attach_regime_outlook(artifact, {"asof": "2026-10-01"}, tmp_path)

    assert "regime_outlook" not in artifact
    assert len(_warning_lines(capsys.readouterr().out)) == 1


# --- T6 ----------------------------------------------------------------------


def test_a_dirty_mapping_is_a_failure_not_a_projection(tmp_path, monkeypatch, capsys):
    _write_owner_files(tmp_path)
    monkeypatch.setattr(rco, "lint_mapping", lambda mapping: ["x"])

    with_previous = _board()
    previous = _previous_read()
    brc._attach_regime_outlook(with_previous, {"regime_outlook": previous}, tmp_path)
    assert with_previous["regime_outlook"] == previous

    without_previous = _board()
    brc._attach_regime_outlook(without_previous, None, tmp_path)
    assert "regime_outlook" not in without_previous

    lines = _warning_lines(capsys.readouterr().out)
    assert len(lines) == 2
    assert all(line == WARNING_HEAD + "ValueError: mapping lint: x" for line in lines)


# --- T7 ----------------------------------------------------------------------


def test_main_calls_the_helper_once_before_the_build_stamp():
    src = inspect.getsource(brc.main)
    assert src.count("_attach_regime_outlook(") == 1
    assert src.index("_attach_regime_outlook(") < src.index('artifact["built"]')
    assert src.index("build_changes(") < src.index("_attach_regime_outlook(")
