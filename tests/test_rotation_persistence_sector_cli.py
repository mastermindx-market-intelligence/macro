"""CLI and data-boundary tests for RPH-1 sector control."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.research.rotation_persistence.contracts import ContractError
from scripts.research.rotation_persistence.sector_control import ALL_SYMBOLS, load_price_panel
from scripts.research.run_sector_control_rph1 import OUTPUT_FILENAMES, main, validate_output_dir


def _write_price(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {"close": [value for _, value in rows]},
        index=pd.to_datetime([date for date, _ in rows]),
    )
    frame.to_parquet(path)


def test_loader_keeps_first_duplicate_drops_invalid_and_intersects_exact_dates(tmp_path: Path) -> None:
    dates = pd.bdate_range("2026-01-02", periods=110)
    for offset, symbol in enumerate(ALL_SYMBOLS):
        rows = [(d.date().isoformat(), 100.0 + offset + i) for i, d in enumerate(dates)]
        if symbol == "XLB":
            rows.insert(6, (dates[5].date().isoformat(), 9999.0))
        if symbol == "XLC":
            rows[8] = (rows[8][0], float("nan"))
        _write_price(tmp_path / f"{symbol}.parquet", rows)

    panel, receipt = load_price_panel(tmp_path)
    assert len(panel) == 109
    assert dates[8] not in panel.index
    assert float(panel.loc[dates[5], "XLB"]) != 9999.0
    assert receipt["files"]["XLB"]["duplicate_dates"] == [dates[5].date().isoformat()]
    assert receipt["files"]["XLC"]["invalid_rows"] == 1
    assert receipt["excluded_rows"] == 1


def test_loader_never_fills_missing_sessions(tmp_path: Path) -> None:
    dates = pd.bdate_range("2026-01-02", periods=110)
    for offset, symbol in enumerate(ALL_SYMBOLS):
        selected = list(dates)
        if symbol == "XLK":
            selected.pop(10)
        rows = [(d.date().isoformat(), 100.0 + offset + i) for i, d in enumerate(selected)]
        _write_price(tmp_path / f"{symbol}.parquet", rows)

    panel, _ = load_price_panel(tmp_path)
    assert dates[10] not in panel.index
    assert len(panel) == 109


def test_loader_requires_close_column(tmp_path: Path) -> None:
    pd.DataFrame({"adj_close": [1.0]}, index=pd.to_datetime(["2026-01-02"])).to_parquet(
        tmp_path / "XLB.parquet"
    )
    with pytest.raises(ContractError, match="close"):
        load_price_panel(tmp_path, symbols=("XLB",))


def test_output_dir_refuses_production_and_data_trees(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for forbidden in ("data", "site", "engine", "config"):
        with pytest.raises(ContractError, match="research-safe"):
            validate_output_dir(repo / forbidden / "rph1", repo_root=repo)
    assert validate_output_dir(repo / "research" / "rotation_persistence" / "rph1", repo_root=repo)


def test_cli_writes_strict_deterministic_json_and_markdown(tmp_path: Path) -> None:
    data_dir = tmp_path / "prices"
    dates = pd.bdate_range("2024-01-02", periods=340)
    for offset, symbol in enumerate(ALL_SYMBOLS):
        rows = [
            (d.date().isoformat(), 100.0 + offset + i * (0.08 + offset / 10000.0))
            for i, d in enumerate(dates)
        ]
        _write_price(data_dir / f"{symbol}.parquet", rows)

    out1 = tmp_path / "research" / "run1"
    out2 = tmp_path / "research" / "run2"
    argv = ["--data-dir", str(data_dir), "--produced-at", "2026-09-12T21:00:00Z"]
    assert main([*argv, "--output-dir", str(out1)], repo_root=tmp_path) == 0
    assert main([*argv, "--output-dir", str(out2)], repo_root=tmp_path) == 0

    json1 = (out1 / OUTPUT_FILENAMES[0]).read_bytes()
    json2 = (out2 / OUTPUT_FILENAMES[0]).read_bytes()
    md1 = (out1 / OUTPUT_FILENAMES[1]).read_bytes()
    md2 = (out2 / OUTPUT_FILENAMES[1]).read_bytes()
    assert json1 == json2
    assert md1 == md2
    decoded = json.loads(json1)
    assert decoded["produced_at"] == "2026-09-12T21:00:00Z"
    assert b"NaN" not in json1 and b"Infinity" not in json1
    assert decoded["authority"]["may_trade"] is False
