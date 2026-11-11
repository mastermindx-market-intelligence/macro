"""The seven build-lane readers of the US board ledger must see rows that live only in parts.

``snapshots.jsonl`` is a frozen prefix once ``snapshots_parts/part-NNNNNN.jsonl``
exists beside it. Each test below builds that layout under ``tmp_path`` and
calls one reader the way its own tests call it. A reader that still opens only
the base file fails, because the asserted as_of, ticker, or count is not in
the base.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from engine import prophet_board_since as pbs
from engine import us_board_snapshots as ubs
from engine import us_prophet_w3 as w3
from scripts import build_exit_policy_vintage_fixture as vintage
from scripts import build_prophet
from scripts import build_track_record_page as track_page
from scripts import check_surface_freshness as freshness
from scripts.exit_policy_study import load_board_days


def _line(row: dict) -> str:
    return json.dumps(row, separators=(",", ":"))


def _ledger(root: Path, base_rows: list[dict], *parts: list[dict]) -> Path:
    ledger = root / "data" / "us_board_ledger"
    ledger.mkdir(parents=True)
    base = ledger / "snapshots.jsonl"
    base.write_text("".join(_line(row) + "\n" for row in base_rows), encoding="utf-8")
    if parts:
        part_dir = ledger / "snapshots_parts"
        part_dir.mkdir()
        for i, rows in enumerate(parts, start=1):
            (part_dir / f"part-{i:06d}.jsonl").write_text(
                "".join(_line(row) + "\n" for row in rows), encoding="utf-8")
    return base


def test_prophet_board_since_reads_rows_in_snapshot_parts(tmp_path):
    pbs._us_obs_cache.clear()
    base = _ledger(
        tmp_path,
        [{"as_of": "2026-06-30", "buy": [{"ticker": "AAA"}]}],
        [{"as_of": "2026-07-01", "buy": [{"ticker": "BBB"}]}],
        [{"as_of": "2026-11-02", "buy": [{"ticker": "ONLYPART"}]}],
    )
    obs = dict(pbs.observations_from_us_snapshots_jsonl(base))
    assert obs["2026-07-01"] == frozenset({"BBB"})
    assert obs["2026-11-02"] == frozenset({"ONLYPART"})


def test_prophet_board_since_reads_rows_appended_to_snapshot_parts(tmp_path):
    """A part that grows after the first call must bust the memo key."""
    pbs._us_obs_cache.clear()
    base = _ledger(
        tmp_path,
        [{"as_of": "2026-06-30", "buy": [{"ticker": "AAA"}]}],
        [{"as_of": "2026-07-01", "buy": [{"ticker": "BBB"}]}],
    )
    first = dict(pbs.observations_from_us_snapshots_jsonl(base))
    assert "2026-07-02" not in first
    ubs.append_line(base, _line({"as_of": "2026-07-02", "buy": [{"ticker": "CCC"}]}))
    second = dict(pbs.observations_from_us_snapshots_jsonl(base))
    assert second["2026-07-02"] == frozenset({"CCC"})


class _Log:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, msg: str, *args) -> None:
        self.warnings.append(msg % args)


def test_prophet_board_since_broken_parts_layout_is_loud_not_silent(tmp_path):
    """A gap in the part numbering must raise. The build's fail-open wrapper then
    logs a warning and leaves the board unstamped, instead of quietly stamping
    every row as if no history existed."""
    pbs._us_obs_cache.clear()
    base = _ledger(
        tmp_path,
        [{"as_of": "2026-06-30", "buy": [{"ticker": "AAA"}]}],
        [{"as_of": "2026-07-01", "buy": [{"ticker": "AAA"}]}],
    )
    part_dir = base.parent / "snapshots_parts"
    (part_dir / "part-000001.jsonl").rename(part_dir / "part-000002.jsonl")
    with pytest.raises(ubs.SnapshotLedgerError):
        pbs.observations_from_us_snapshots_jsonl(base)
    log = _Log()
    artifact = {"as_of": "2026-07-02", "buy": [{"ticker": "AAA"}]}
    out = pbs.stamp_us_board_since_fail_open(artifact, data_dir=tmp_path / "data", log=log)
    assert "added_date" not in out["buy"][0]
    assert len(log.warnings) == 1 and "us board_since stamp failed" in log.warnings[0]


def test_prophet_board_since_torn_base_line_is_loud_not_silent(tmp_path):
    """A base whose last row has no newline while parts exist is a torn join: the
    read must raise, not return an empty history."""
    pbs._us_obs_cache.clear()
    base = _ledger(
        tmp_path,
        [{"as_of": "2026-06-30", "buy": [{"ticker": "AAA"}]}],
        [{"as_of": "2026-07-01", "buy": [{"ticker": "AAA"}]}],
    )
    base.write_bytes(base.read_bytes().rstrip(b"\n"))
    with pytest.raises(ubs.SnapshotLedgerError):
        pbs.observations_from_us_snapshots_jsonl(base)


def test_us_prophet_w3_reads_rows_in_snapshot_parts(tmp_path):
    _ledger(
        tmp_path,
        [{"as_of": "2026-08-01", "ranking": {"fusion": {}}}],
        [{
            "as_of": "2026-11-02",
            "ranking": {"fusion": {"w3_structural": {
                "schema": w3.STRUCTURAL_SCHEMA,
                "part_marker": "ONLYPART",
            }}},
        }],
    )
    got = w3.load_committed_structural_receipt("2026-11-02", tmp_path)
    assert got is not None
    assert got["part_marker"] == "ONLYPART"


def test_build_exit_policy_vintage_fixture_reads_rows_in_snapshot_parts(tmp_path):
    base = _ledger(
        tmp_path,
        [{"as_of": "2026-08-01", "buy": [{"ticker": "AAA"}]}],
        [{"as_of": "2026-09-01", "buy": [{"ticker": "BBB"}]}],
        [{"as_of": "2026-11-02", "buy": [{"ticker": "ONLYPART"}]}],
    )
    dest = tmp_path / "distilled" / "snapshots.jsonl"
    n = vintage._distil_snapshots(base, dest)
    assert n == 3
    text = dest.read_text(encoding="utf-8")
    assert "2026-11-02" in text
    assert "ONLYPART" in text


def test_build_exit_policy_vintage_fixture_materialise_reads_rows_in_snapshot_parts(
        tmp_path, monkeypatch):
    part_a = "data/us_board_ledger/snapshots_parts/part-000001.jsonl"
    part_b = "data/us_board_ledger/snapshots_parts/part-000002.jsonl"
    body = b'{"as_of":"2026-11-02","buy":[{"ticker":"ONLYPART"}]}\n'

    def fake_run(args, **kwargs):
        del kwargs
        if "ls-tree" in args:
            stdout = part_a + "\n" + part_b + "\n"
            return subprocess.CompletedProcess(args, 0, stdout=stdout)
        return subprocess.CompletedProcess(args, 0, stdout=body)

    monkeypatch.setattr(vintage.subprocess, "run", fake_run)
    dest = tmp_path / "scratch"
    vintage._materialise("abc123", dest)
    assert (dest / part_a).read_bytes() == body
    assert (dest / part_b).read_bytes() == body


def test_build_prophet_reads_rows_in_snapshot_parts(tmp_path):
    base = _ledger(
        tmp_path,
        [{"as_of": "2026-08-01", "buy": [{"ticker": "AAA"}]}],
        [{"as_of": "2026-11-02", "buy": [{"ticker": "ONLYPART"}]}],
    )
    snaps = build_prophet._load_board_snapshots(base)
    assert snaps["2026-11-02"]["buy"][0]["ticker"] == "ONLYPART"


def test_build_track_record_page_reads_rows_in_snapshot_parts(tmp_path):
    base = _ledger(
        tmp_path,
        [{"as_of": "2026-06-30", "buy": ["AAA"]}],
        [{"as_of": "2026-08-01", "buy": ["BBB", "CCC"]}],
        [{"as_of": "2026-11-02", "buy": ["ONLYPART"]}],
    )
    series = track_page._compute_board_series(base)["series"]
    by_as_of = {row["as_of"]: row for row in series}
    assert by_as_of["2026-11-02"]["total"] == 1
    assert by_as_of["2026-11-02"]["by_lane"] == {"buy": 1}
    assert by_as_of["2026-08-01"]["total"] == 2


def test_check_surface_freshness_reads_rows_in_snapshot_parts(tmp_path, monkeypatch):
    # 2026-08-07 stamp vs 2026-08-13 board is 4 sessions — the sentinel's own geometry.
    # The 08-13 row lives only in part-000002, so a base-only read returns 0.
    import pandas as pd

    monkeypatch.setattr("engine.alert_triage.push_ops_alert", lambda **_kwargs: True)
    _ledger(
        tmp_path,
        [{"as_of": "2026-08-07", "buy": []}],
        [{"as_of": "2026-08-10", "buy": []}],
        [{"as_of": "2026-08-13", "buy": []}],
    )
    store = tmp_path / "data" / "us_prophet_rank" / "candidates"
    store.mkdir(parents=True)
    pd.DataFrame({"stamp_date": ["2026-08-07"], "ticker": ["T"]}).to_parquet(
        store / "2026-08.parquet", index=False)
    assert freshness.check_candidates_freshness(tmp_path) == 4


def test_exit_policy_study_reads_rows_in_snapshot_parts(tmp_path):
    _ledger(
        tmp_path,
        [{"as_of": "2026-08-01", "buy": [{"ticker": "AAA"}]}],
        [{"as_of": "2026-11-02", "buy": [
            {"ticker": "ONLYPART", "hold": {"invalidation": 12.5}}]}],
    )
    days, invalidation, prov = load_board_days(tmp_path)
    assert "ONLYPART" in days["2026-11-02"]
    assert invalidation[("2026-11-02", "ONLYPART")] == 12.5
    assert prov["n_days_snapshots"] == 2
