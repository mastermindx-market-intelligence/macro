from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from lib.nyse_calendar import is_session
from scripts.research.rotation_persistence.contracts import AUTHORITY, ContractError
from scripts.research.rotation_persistence.report import validate_output_dir

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "research" / "run_rotation_persistence_rph0.py"


def _sessions(start: date, count: int) -> list[date]:
    values: list[date] = []
    cursor = start
    while len(values) < count:
        if is_session(cursor):
            values.append(cursor)
        cursor += timedelta(days=1)
    return values


def _write_valid_archive(path: Path, *, count: int = 30) -> None:
    rows = []
    ids = [f"t{i:02d}" for i in range(12)]
    for offset, asof in enumerate(_sessions(date(2026, 6, 1), count)):
        order = ids[offset % 12 :] + ids[: offset % 12]
        themes = []
        for rank, theme_id in enumerate(order, start=1):
            themes.append(
                {
                    "id": theme_id,
                    "rank": rank,
                    "score": 100.0 - rank + 0.25 * offset,
                    "label": "dominant" if rank <= 3 else "neutral",
                    "components": {"breadth": 0.9 - 0.03 * rank},
                }
            )
        rows.append(
            {
                "asof": asof.isoformat(),
                "logged_at": f"{asof.isoformat()}T22:00:00Z",
                "snapshot_json": json.dumps(
                    {"as_of": asof.isoformat(), "themes": themes},
                    separators=(",", ":"),
                ),
            }
        )
    pd.DataFrame(rows).to_parquet(path, index=False)


def _run(archive: Path, out_dir: Path, *, produced_at: str = "2026-09-10T21:00:00Z"):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--archive",
            str(archive),
            "--out-dir",
            str(out_dir),
            "--produced-at",
            produced_at,
            "--bootstrap-resamples",
            "30",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_writes_strict_result_and_markdown(tmp_path: Path) -> None:
    archive = tmp_path / "baskets.parquet"
    out_dir = tmp_path / "result"
    _write_valid_archive(archive)

    completed = _run(archive, out_dir)

    assert completed.returncode == 0, completed.stderr
    assert sorted(path.name for path in out_dir.iterdir()) == ["report.md", "result.json"]
    text = (out_dir / "result.json").read_text(encoding="utf-8")
    assert "NaN" not in text
    assert "Infinity" not in text
    payload = json.loads(text)
    assert payload["schema_version"] == "research.rotation_persistence_rph0.v1"
    assert payload["operation_key"] == "leadership-persistence-rph0-20260910-sol-001"
    assert payload["produced_at"] == "2026-09-10T21:00:00Z"
    expected_authority = {
        "is_context_only": True,
        "may_rank": False,
        "may_gate": False,
        "may_size": False,
        "may_trade": False,
        "may_modify_prophet": False,
        "may_modify_oracle": False,
    }
    assert AUTHORITY == expected_authority
    assert payload["authority"] == expected_authority
    assert payload["source"]["rows_valid"] == 30
    assert payload["surface"]
    assert payload["transition_matrix"]["pairs_eligible"] == 29
    assert payload["residency"]["episodes"]
    assert payload["temporal_shape"]["label"] in {
        "MULTI_SCALE",
        "REVERSAL_DOMINANT",
        "CONTINUATION_DOMINANT",
        "TRANSITIONAL",
        "INSUFFICIENT_HISTORY",
    }
    estimability = payload["temporal_shape"]["estimability"]
    assert estimability["state"] == "STRUCTURALLY_UNESTIMABLE"
    assert estimability["reason"] == "RECENT_WINDOW_CANNOT_MATURE_REQUIRED_LONG_CELLS"
    assert estimability["measurable_long_horizons"] == [10]
    assert estimability["minimum_recent_sessions_for_shape"] == 23
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "Leadership Persistence RPH-0" in report
    assert payload["temporal_shape"]["label"] in report
    assert "STRUCTURALLY_UNESTIMABLE" in report
    assert "minimum recent window: 23 sessions" in report
    assert "Long-horizon maximum matured anchors: 10→10, 15→5, 20→0" in report
    assert all(line == line.rstrip() for line in report.splitlines())


def test_cli_is_byte_deterministic_with_injected_clock(tmp_path: Path) -> None:
    archive = tmp_path / "baskets.parquet"
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_valid_archive(archive)

    one = _run(archive, first)
    two = _run(archive, second)

    assert one.returncode == 0, one.stderr
    assert two.returncode == 0, two.stderr
    assert (first / "result.json").read_bytes() == (second / "result.json").read_bytes()
    assert (first / "report.md").read_bytes() == (second / "report.md").read_bytes()


def test_validate_output_dir_refuses_production_owner_roots() -> None:
    for owner in ("data", "site", "engine", "config"):
        with pytest.raises(ContractError, match="forbidden owner root"):
            validate_output_dir(ROOT / owner / "rotation-persistence-test", repo_root=ROOT)


def test_cli_malformed_input_returns_two_without_false_result(tmp_path: Path) -> None:
    archive = tmp_path / "bad.parquet"
    pd.DataFrame([{"asof": "2026-09-08"}]).to_parquet(archive, index=False)
    out_dir = tmp_path / "result"

    completed = _run(archive, out_dir)

    assert completed.returncode == 2
    assert "required columns" in completed.stderr
    assert not (out_dir / "result.json").exists()
    assert not (out_dir / "report.md").exists()


def test_cli_rejects_non_timezone_produced_at(tmp_path: Path) -> None:
    archive = tmp_path / "baskets.parquet"
    _write_valid_archive(archive)
    out_dir = tmp_path / "result"

    completed = _run(archive, out_dir, produced_at="2026-09-10T21:00:00")

    assert completed.returncode == 2
    assert "timezone" in completed.stderr
    assert not (out_dir / "result.json").exists()
