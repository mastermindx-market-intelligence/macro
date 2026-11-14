"""Rotation-context nightly capture (engine/rotation_context_capture.py).

Fixture proof of every field, byte-identical second run, skip-on-existing,
nulls for missing series, exceptions never propagate, no later holdings
snapshot is ever used, and the collect.py hook point. Stdlib + pandas + pytest;
no network.
"""
from __future__ import annotations

import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine import rotation_context_capture as rc

ASOF = "2026-11-10"
NOW = datetime(2026, 11, 11, 3, 0, 0, tzinfo=timezone.utc)
MTIME = 1_762_800_000  # fixed file mtime -> fixed file_mtime_utc


def _series(path: Path, column: str, rows: dict[str, float | None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    idx = pd.DatetimeIndex(pd.to_datetime(list(rows)), name="date")
    pd.DataFrame({column: list(rows.values())}, index=idx).to_parquet(path)
    os.utime(path, (MTIME, MTIME))


def _holdings(path: Path, weights: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"ticker": [f"T{i}" for i in range(len(weights))],
                  "weight_pct": weights}).to_parquet(path)
    os.utime(path, (MTIME, MTIME))


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    for i, (key, group, stem, col) in enumerate(rc.SERIES):
        # last row NaN for the first series: the latest NON-null level is taken
        rows = {"2026-11-06": 1.0 + i, "2026-11-09": 2.0 + i}
        if i == 0:
            rows["2026-11-10"] = None
        _series(d / group / f"{stem}.parquet", col, rows)
    # SPY: 12 names, weights in percent
    _holdings(d / "etf_holdings/SPY/2026-11-09.parquet",
              [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0.5, 0.5])
    # a LATER snapshot than asof must never be used
    _holdings(d / "etf_holdings/SPY/2026-11-11.parquet", [50, 50])
    _holdings(d / "etf_holdings/QQQ/2026-06-13.parquet", [40, 30, 30])
    return d


def _load(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes()))


def test_every_field_from_fixture(data_dir: Path) -> None:
    written, p, n = rc.write_capture(ASOF, data_dir=data_dir, now_utc=NOW)
    assert written and n == p.stat().st_size and p.name == f"{ASOF}.json.gz"
    rec = _load(p)
    assert rec["schema"] == "rotation_context.v1"
    assert rec["asof"] == ASOF
    assert rec["captured_at_utc"] == "2026-11-11T03:00:00+00:00"
    mt = datetime.fromtimestamp(MTIME, tz=timezone.utc).isoformat(timespec="seconds")
    assert set(rec["series"]) == {k for k, *_ in rc.SERIES}
    for i, (key, group, stem, col) in enumerate(rc.SERIES):
        s = rec["series"][key]
        assert s["source"] == f"data/{group}/{stem}.parquet"
        assert s["column"] == col
        assert s["value"] == 2.0 + i
        assert s["obs_date"] == "2026-11-09"
        assert s["file_mtime_utc"] == mt
    spy = rec["holdings"]["SPY"]
    assert spy["snapshot_date"] == "2026-11-09"            # never the later 11-11 file
    assert spy["source"] == "data/etf_holdings/SPY/2026-11-09.parquet"
    assert spy["top10_weight"] == pytest.approx(0.55)
    w = [x / 100 for x in [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0.5, 0.5]]
    assert spy["sum_sq_weight"] == pytest.approx(sum(x * x for x in w))
    assert spy["file_mtime_utc"] == mt
    qqq = rec["holdings"]["QQQ"]
    assert qqq["snapshot_date"] == "2026-06-13"
    assert qqq["top10_weight"] == pytest.approx(1.0)
    assert qqq["sum_sq_weight"] == pytest.approx(0.16 + 0.09 + 0.09)
    # levels only: no derived keys anywhere
    allowed = {"source", "column", "value", "obs_date", "file_mtime_utc"}
    assert all(set(s) == allowed for s in rec["series"].values())


def test_second_run_is_byte_identical_and_skips(data_dir: Path, tmp_path: Path) -> None:
    _, p, _ = rc.write_capture(ASOF, data_dir=data_dir, now_utc=NOW)
    first = p.read_bytes()
    # the existing file is skipped, never overwritten
    written, p2, n = rc.write_capture(ASOF, data_dir=data_dir, now_utc=NOW)
    assert (written, n) == (False, 0) and p2.read_bytes() == first
    # a fresh write from the same inputs is byte-identical
    p.unlink()
    rc.write_capture(ASOF, data_dir=data_dir, now_utc=NOW)
    assert p.read_bytes() == first
    assert not list(p.parent.glob("*.tmp"))


def test_missing_series_yield_nulls(tmp_path: Path) -> None:
    d = tmp_path / "data"
    d.mkdir()
    _, p, _ = rc.write_capture(ASOF, data_dir=d, now_utc=NOW)
    rec = _load(p)
    for key, group, stem, col in rc.SERIES:
        assert rec["series"][key] == {"source": f"data/{group}/{stem}.parquet",
                                      "column": col, "value": None,
                                      "obs_date": None, "file_mtime_utc": None}
    for fund in rc.HOLDINGS_FUNDS:
        assert rec["holdings"][fund]["top10_weight"] is None
        assert rec["holdings"][fund]["sum_sq_weight"] is None
        assert rec["holdings"][fund]["snapshot_date"] is None


def test_unreadable_store_is_null_not_fill(data_dir: Path) -> None:
    (data_dir / "fred/DGS10.parquet").write_bytes(b"not a parquet")
    (data_dir / "etf_holdings/QQQ/2026-06-13.parquet").write_bytes(b"junk")
    _, p, _ = rc.write_capture(ASOF, data_dir=data_dir, now_utc=NOW)
    rec = _load(p)
    assert rec["series"]["us10y"]["value"] is None
    assert rec["series"]["us10y"]["obs_date"] is None
    assert rec["series"]["us10y_real"]["value"] == 3.0     # others unaffected
    q = rec["holdings"]["QQQ"]
    assert q["top10_weight"] is None and q["sum_sq_weight"] is None
    assert q["snapshot_date"] == "2026-06-13"


def test_exception_does_not_propagate(data_dir: Path, monkeypatch) -> None:
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(rc, "write_capture", boom)
    out = rc.run_nightly(ASOF, data_dir=data_dir, now_utc=NOW)
    assert out["status"] == "error" and "disk full" in out["error"]


def test_run_nightly_writes_then_skips(data_dir: Path) -> None:
    assert rc.run_nightly(ASOF, data_dir=data_dir, now_utc=NOW)["status"] == "written"
    assert rc.run_nightly(ASOF, data_dir=data_dir, now_utc=NOW)["status"] == "skipped"


def test_collect_hook_runs_after_adapters_on_nightly_lane_only() -> None:
    src = (Path(__file__).resolve().parents[1] / "scripts/collect.py").read_text()
    hook = src.index("from engine.rotation_context_capture import run_nightly")
    assert src.index("CONCURRENT phase") < hook          # after both adapter phases
    assert src.index("FRED per-series PIT lag record skipped") < hook
    gate = src.rindex('if os.environ.get("COLLECT_LANE") == "nightly" and not (args.only or args.group):', 0, hook)
    assert hook - gate < 200
