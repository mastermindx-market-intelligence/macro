"""Unit tests for the futures-tape Data OS plane.

No network and no vendor credentials. These tests prove path safety, immutable
partition receipts, capacity fencing, LSE normalization, and deterministic bars.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from lib.dataos.futures_tape import (
    FuturesTapeError,
    PartitionManifest,
    PartitionState,
    SourceRole,
    audit_manifests,
    derived_bar_path,
    normalized_day_path,
    raw_export_path,
    require_capacity,
    sha256_file,
    storage_root,
    write_manifest_atomic,
)
from scripts import futures_tape_ingest as fti


def test_date_chunks_are_bounded_and_cover_range() -> None:
    assert fti._date_chunks("2026-01-01", "2026-01-20", 7) == [
        ("2026-01-01", "2026-01-08"),
        ("2026-01-08", "2026-01-15"),
        ("2026-01-15", "2026-01-20"),
    ]


def test_date_chunks_reject_invalid_range() -> None:
    with pytest.raises(SystemExit, match="after"):
        fti._date_chunks("2026-01-02", "2026-01-02", 7)
    with pytest.raises(SystemExit, match=">= 1"):
        fti._date_chunks("2026-01-01", "2026-01-02", 0)


def test_range_backfill_rejects_zero_job_budget(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="--max-jobs"):
        fti.cmd_backfill_lse_range(
            type("Args", (), {
                "max_jobs": 0,
                "root": str(tmp_path),
                "reserve_gib": 0.0,
                "start": "2026-01-01",
                "end": "2026-01-02",
                "chunk_days": 1,
                "symbol": "ES.F",
                "force": False,
            })()
        )


def test_storage_root_prefers_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    assert storage_root() == tmp_path


def test_storage_paths_are_partitioned_and_safe(tmp_path: Path) -> None:
    raw = raw_export_path(tmp_path, "lse", "ES.F", "2020-03-01", "2020-04-01")
    assert raw.relative_to(tmp_path).as_posix() == (
        "raw/source=lse/symbol=ES.F/window=2020-03-01_2020-04-01/export.parquet"
    )
    norm = normalized_day_path(tmp_path, "lse", "LSE_ES.F", "2020-03-16")
    assert "date=2020-03-16" in norm.as_posix()
    bar = derived_bar_path(tmp_path, "LSE_ES.F", "1min", "2020-03-16")
    assert "freq=1min" in bar.as_posix()


def test_manifest_rejects_escape_path() -> None:
    m = PartitionManifest(
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS.value,
        source_symbol="ES.F",
        state=PartitionState.FINAL.value,
        relative_path="../outside.parquet",
        row_count=1,
        byte_count=1,
        sha256="0" * 64,
        retrieved_at_utc="2026-10-05T00:00:00Z",
    )
    with pytest.raises(FuturesTapeError, match="relative_path"):
        m.validate()


def test_manifest_hash_audit_detects_mutation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    p = tmp_path / "raw" / "x.parquet"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"first")
    m = PartitionManifest(
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS.value,
        source_symbol="ES.F",
        state=PartitionState.FINAL.value,
        relative_path=p.relative_to(tmp_path).as_posix(),
        row_count=1,
        byte_count=p.stat().st_size,
        sha256=sha256_file(p),
        retrieved_at_utc="2026-10-05T00:00:00Z",
    )
    write_manifest_atomic(p, m)
    assert audit_manifests(tmp_path) == []
    p.write_bytes(b"mutated")
    problems = audit_manifests(tmp_path)
    assert any("byte_count" in x or "sha256" in x for x in problems)


def test_capacity_fence_can_be_forced_to_fail(tmp_path: Path) -> None:
    with pytest.raises(FuturesTapeError, match="reserve required"):
        require_capacity(tmp_path, 10**9)


def test_lse_normalization_has_canonical_columns_and_dedupes() -> None:
    raw = pd.DataFrame({
        "timestamp": [
            "2026-10-02T13:30:00.000000Z",
            "2026-10-02T13:30:00.000000Z",
            "2026-10-02T13:30:00.250000Z",
        ],
        "price": [6700.0, 6700.0, 6700.25],
        "bid": [6699.75, 6699.75, 6700.0],
        "ask": [6700.0, 6700.0, 6700.25],
        "volume": [2, 2, 1],
    })
    out = fti._normalize_lse_frame(raw, "ES.F")
    assert list(out.columns) == [
        "timestamp_utc", "price_raw", "source_symbol",
        "bid_raw", "ask_raw", "volume",
    ]
    assert len(out) == 2
    assert str(out["timestamp_utc"].dtype) == "datetime64[ns, UTC]"
    assert out["source_symbol"].unique().tolist() == ["ES.F"]


def test_row_bounds_are_utc_and_ignore_bad_rows() -> None:
    df = pd.DataFrame({
        "timestamp": ["bad", "2026-10-02T13:30:00Z", "2026-10-02T14:00:00Z"],
        "price": [1, 2, 3],
    })
    lo, hi = fti._row_bounds(df)
    assert lo.startswith("2026-10-02T13:30:00")
    assert hi.startswith("2026-10-02T14:00:00")


def test_row_bounds_accept_canonical_timestamp_column() -> None:
    df = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(
            ["2026-10-02T13:30:00Z", "2026-10-02T14:00:00Z"], utc=True
        ),
        "price_raw": [1.0, 2.0],
    })
    lo, hi = fti._row_bounds(df)
    assert lo.startswith("2026-10-02T13:30:00")
    assert hi.startswith("2026-10-02T14:00:00")


def test_write_dataframe_export_is_atomic_and_receipted(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    target = raw_export_path(tmp_path, "lse", "ES.F", "2026-10-01", "2026-10-02")
    df = pd.DataFrame({
        "timestamp": ["2026-10-01T22:00:00Z", "2026-10-01T22:00:01Z"],
        "price": [6700.0, 6700.25],
    })
    m = fti._write_dataframe_export(
        df, target,
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS,
        source_symbol="ES.F",
        state=PartitionState.FINAL,
    )
    assert target.is_file()
    assert not target.with_suffix(target.suffix + ".partial").exists()
    receipt = Path(str(target) + ".manifest.json")
    assert receipt.is_file()
    loaded = PartitionManifest.from_json(receipt.read_text())
    assert loaded.sha256 == sha256_file(target)
    assert loaded.row_count == 2
    assert m.relative_path == target.relative_to(tmp_path).as_posix()


def test_history_result_accepts_dataframe_and_list(tmp_path: Path) -> None:
    df = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z"], "price": [1.0]})
    got = fti._coerce_history_result(df, tmp_path)
    assert got is not df and len(got) == 1
    got2 = fti._coerce_history_result([{"timestamp": "x", "price": 1.0}], tmp_path)
    assert len(got2) == 1


def test_resume_skip_requires_a_valid_receipt(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    target = raw_export_path(tmp_path, "lse", "ES.F", "2026-10-01", "2026-10-02")
    target.parent.mkdir(parents=True)
    target.write_bytes(b"good")
    m = PartitionManifest(
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS.value,
        source_symbol="ES.F",
        state=PartitionState.FINAL.value,
        relative_path=target.relative_to(tmp_path).as_posix(),
        row_count=1,
        byte_count=target.stat().st_size,
        sha256=sha256_file(target),
        retrieved_at_utc="2026-10-05T00:00:00Z",
    )
    write_manifest_atomic(target, m)
    assert fti._valid_receipted(tmp_path, target) is True
    target.write_bytes(b"corrupt")
    assert fti._valid_receipted(tmp_path, target) is False


def test_audit_missing_root_is_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    problems = audit_manifests(missing)
    assert problems and "does not exist" in problems[0]
