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
    capacity,
    derived_bar_path,
    normalized_day_path,
    manifest_path,
    raw_export_path,
    require_capacity,
    sha256_file,
    storage_root,
    verify_manifest,
    write_manifest_atomic,
)
from scripts import futures_tape_ingest as fti


def test_current_day_timestamp_window_remains_provisional() -> None:
    today = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    assert fti._lse_window_state(today) is PartitionState.FINAL
    assert fti._lse_window_state(today + "T00:01:00Z") is PartitionState.PROVISIONAL


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


@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
def test_lse_normalization_preserves_instants_across_timestamp_units(unit: str) -> None:
    """Already-typed provider frames must obey the same canonical ns contract."""
    timestamps = pd.Series(pd.to_datetime([
        "2026-10-02T13:30:01Z", "2026-10-02T13:30:00Z",
        "2026-10-02T13:30:00Z", None,
    ], utc=True)).dt.tz_convert("America/New_York").astype(
        f"datetime64[{unit}, America/New_York]"
    )
    raw = pd.DataFrame({
        "timestamp": timestamps, "price": [2.0, 1.0, 1.0, 3.0],
        "volume": [1, 1, 1, 1],
    })
    out = fti._normalize_lse_frame(raw, "ES.F")
    assert str(out["timestamp_utc"].dtype) == "datetime64[ns, UTC]"
    assert out["timestamp_utc"].tolist() == [
        pd.Timestamp("2026-10-02T13:30:00Z"),
        pd.Timestamp("2026-10-02T13:30:01Z"),
    ]
    assert out["price_raw"].tolist() == [1.0, 2.0]


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


def test_manifest_round_trips_source_request_window(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    target = raw_export_path(tmp_path, "lse", "ES.F", "2026-01-01T00:00:00Z", "2026-01-01T12:00:00Z")
    df = pd.DataFrame({
        "timestamp": ["2026-01-01T00:00:01Z"],
        "price": [6700.0],
    })
    fti._write_dataframe_export(
        df,
        target,
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS,
        source_symbol="ES.F",
        state=PartitionState.FINAL,
        request_start="2026-01-01T00:00:00Z",
        request_end="2026-01-01T12:00:00Z",
    )
    loaded = PartitionManifest.from_json(
        Path(str(target) + ".manifest.json").read_text()
    )
    assert loaded.request_start == "2026-01-01T00:00:00Z"
    assert loaded.request_end == "2026-01-01T12:00:00Z"


def test_day_coverage_accepts_two_final_half_day_windows() -> None:
    base = dict(
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS.value,
        source_symbol="ES.F",
        relative_path="raw/x.parquet",
        row_count=1,
        byte_count=1,
        sha256="0" * 64,
        retrieved_at_utc="2026-10-05T00:00:00Z",
        state=PartitionState.FINAL.value,
    )
    first = PartitionManifest(
        **base,
        request_start="2026-01-01T00:00:00Z",
        request_end="2026-01-01T12:00:00Z",
    )
    second = PartitionManifest(
        **base,
        request_start="2026-01-01T12:00:00Z",
        request_end="2026-01-02T00:00:00Z",
    )
    assert fti._day_is_fully_covered("2026-01-01", [first, second]) is True


def test_day_coverage_rejects_gap_and_provisional_window() -> None:
    base = dict(
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS.value,
        source_symbol="ES.F",
        relative_path="raw/x.parquet",
        row_count=1,
        byte_count=1,
        sha256="0" * 64,
        retrieved_at_utc="2026-10-05T00:00:00Z",
    )
    first = PartitionManifest(
        **base,
        state=PartitionState.FINAL.value,
        request_start="2026-01-01T00:00:00Z",
        request_end="2026-01-01T11:00:00Z",
    )
    second = PartitionManifest(
        **base,
        state=PartitionState.FINAL.value,
        request_start="2026-01-01T12:00:00Z",
        request_end="2026-01-02T00:00:00Z",
    )
    assert fti._day_is_fully_covered("2026-01-01", [first, second]) is False
    full_but_provisional = PartitionManifest(
        **base,
        state=PartitionState.PROVISIONAL.value,
        request_start="2026-01-01T00:00:00Z",
        request_end="2026-01-02T00:00:00Z",
    )
    assert fti._day_is_fully_covered("2026-01-01", [full_but_provisional]) is False


def test_normalize_combines_split_raw_windows_before_writing_day(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    chunks = [
        (
            "2026-01-01T00:00:00Z",
            "2026-01-01T12:00:00Z",
            ["2026-01-01T00:00:01Z", "2026-01-01T11:59:59Z"],
            [6700.0, 6701.0],
        ),
        (
            "2026-01-01T12:00:00Z",
            "2026-01-02T00:00:00Z",
            ["2026-01-01T12:00:01Z", "2026-01-01T23:59:59Z"],
            [6702.0, 6703.0],
        ),
    ]
    for start, end, stamps, prices in chunks:
        target = raw_export_path(tmp_path, "lse", "ES.F", start, end)
        fti._write_dataframe_export(
            pd.DataFrame({"timestamp": stamps, "price": prices, "volume": [1, 1]}),
            target,
            source="lse",
            source_role=SourceRole.VENDOR_CONTINUOUS,
            source_symbol="ES.F",
            state=PartitionState.FINAL,
            request_start=start,
            request_end=end,
        )

    args = type("Args", (), {
        "root": str(tmp_path),
        "symbol": "ES.F",
        "identity": "LSE_ES.F",
        "force": False,
    })()
    assert fti.cmd_normalize_lse(args) == 0
    target = normalized_day_path(tmp_path, "lse", "LSE_ES.F", "2026-01-01")
    out = pd.read_parquet(target)
    assert out["price_raw"].tolist() == [6700.0, 6701.0, 6702.0, 6703.0]
    manifest = PartitionManifest.from_json(
        Path(str(target) + ".manifest.json").read_text()
    )
    assert manifest.state == PartitionState.FINAL.value


def test_normalize_marks_partial_day_provisional(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    target = raw_export_path(
        tmp_path, "lse", "ES.F",
        "2026-01-01T00:00:00Z", "2026-01-01T12:00:00Z",
    )
    fti._write_dataframe_export(
        pd.DataFrame({
            "timestamp": ["2026-01-01T00:00:01Z"],
            "price": [6700.0],
            "volume": [1],
        }),
        target,
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS,
        source_symbol="ES.F",
        state=PartitionState.FINAL,
        request_start="2026-01-01T00:00:00Z",
        request_end="2026-01-01T12:00:00Z",
    )
    args = type("Args", (), {
        "root": str(tmp_path),
        "symbol": "ES.F",
        "identity": "LSE_ES.F",
        "force": False,
    })()
    assert fti.cmd_normalize_lse(args) == 0
    normalized = normalized_day_path(tmp_path, "lse", "LSE_ES.F", "2026-01-01")
    manifest = PartitionManifest.from_json(
        Path(str(normalized) + ".manifest.json").read_text()
    )
    assert manifest.state == PartitionState.PROVISIONAL.value


def test_backfill_refuses_capped_lse_export(monkeypatch, tmp_path: Path) -> None:
    class FakeClient:
        def catalog(self, category):
            assert category == "futures"
            return [{"symbol": "ES.F"}]

        def history(self, symbol, **kwargs):
            return pd.DataFrame({
                "timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"],
                "price": [1.0, 1.25],
            })

    monkeypatch.setattr(fti, "_lse_client", lambda: FakeClient())
    monkeypatch.setattr(fti, "LSE_EXPORT_ROW_CAP", 2)
    args = type("Args", (), {
        "root": str(tmp_path),
        "reserve_gib": 0.0,
        "symbol": "ES.F",
        "start": "2026-01-01",
        "end": "2026-01-02",
        "force": False,
    })()
    with pytest.raises(SystemExit, match="capped/incomplete"):
        fti.cmd_backfill_lse(args)
    target = raw_export_path(tmp_path, "lse", "ES.F", "2026-01-01", "2026-01-02")
    assert not target.exists()


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


def _receipted_test_bytes(root: Path, relative: str, content: bytes) -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    write_manifest_atomic(target, PartitionManifest(
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS.value,
        source_symbol="ES.F",
        state=PartitionState.FINAL.value,
        relative_path=target.relative_to(root).as_posix(),
        row_count=1,
        byte_count=len(content),
        sha256=sha256_file(target),
        retrieved_at_utc="2026-10-05T00:00:00Z",
    ))
    return target


@pytest.mark.parametrize("sidecar_kind", ["copy", "symlink"])
def test_resume_rejects_another_partitions_valid_receipt(tmp_path: Path, sidecar_kind) -> None:
    other = _receipted_test_bytes(tmp_path, "raw/other.parquet", b"verified")
    target = tmp_path / "raw" / "target.parquet"
    target.write_bytes(b"unverified")
    receipt = manifest_path(target)
    if sidecar_kind == "copy":
        receipt.write_bytes(manifest_path(other).read_bytes())
    else:
        receipt.symlink_to(manifest_path(other))

    assert fti._valid_receipted(tmp_path, other) is True
    assert fti._valid_receipted(tmp_path, target) is False
    assert any("adjacent" in problem for problem in verify_manifest(tmp_path, receipt))
    assert target.read_bytes() == b"unverified"


@pytest.mark.parametrize("escaped_part", ["data", "receipt"])
def test_receipt_verification_rejects_outside_root_symlinks(
    monkeypatch, tmp_path: Path, escaped_part
) -> None:
    root = tmp_path / "tape"
    root.mkdir()
    target = _receipted_test_bytes(root, "raw/target.parquet", b"verified")
    if escaped_part == "data":
        outside = tmp_path / "outside.parquet"
        outside.write_bytes(b"verified")
        target.unlink()
        target.symlink_to(outside)
    else:
        outside = tmp_path / "outside.manifest.json"
        outside.write_text("must not be read")
        manifest_path(target).unlink()
        manifest_path(target).symlink_to(outside)

    def no_hash(_path):
        pytest.fail("an escaped receipt or data path must be rejected before hashing")

    monkeypatch.setattr("lib.dataos.futures_tape.sha256_file", no_hash)
    assert any("escapes" in problem for problem in verify_manifest(root, manifest_path(target)))
    assert fti._valid_receipted(root, target) is False


def test_receipts_allow_a_contained_storage_root_symlink(tmp_path: Path) -> None:
    root = tmp_path / "actual"
    root.mkdir()
    _receipted_test_bytes(root, "raw/target.parquet", b"verified")
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    target = alias / "raw" / "target.parquet"

    assert verify_manifest(alias, manifest_path(target)) == []
    assert fti._valid_receipted(alias, target) is True


@pytest.mark.parametrize("relative", [
    "raw/source=lse/symbol=ES.F/window=a_b/export.parquet",
    "normalized/ticks/source=lse/instrument=LSE_ES.F/date=2026-01-01/part-000.parquet",
    "derived/bars/instrument=LSE_ES.F/freq=1min/date=2026-01-01/part-000.parquet",
])
def test_audit_rejects_finalized_data_without_its_receipt(tmp_path: Path, relative) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(b"unreceipted")

    problems = audit_manifests(tmp_path)
    assert any(str(target) in problem and "missing" in problem for problem in problems)
    assert target.read_bytes() == b"unreceipted"


def test_audit_exposes_interruption_between_data_and_receipt(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    target = raw_export_path(tmp_path, "lse", "ES.F", "2026-01-01", "2026-01-02")

    def interrupted(*_args, **_kwargs):
        raise RuntimeError("interrupted before receipt")

    monkeypatch.setattr(fti, "write_manifest_atomic", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        fti._write_dataframe_export(
            pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z"], "price": [100.0]}),
            target,
            source="lse",
            source_role=SourceRole.VENDOR_CONTINUOUS,
            source_symbol="ES.F",
            state=PartitionState.FINAL,
        )

    assert target.is_file() and not manifest_path(target).exists()
    assert any("missing" in problem for problem in audit_manifests(tmp_path))


def test_partial_file_is_not_claimed_as_finalized_data(tmp_path: Path) -> None:
    partial = tmp_path / "export.parquet.partial"
    partial.write_bytes(b"incomplete")

    assert audit_manifests(tmp_path) == []
    assert partial.read_bytes() == b"incomplete"


def test_encoded_source_and_instrument_round_trip_through_bars(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MMX_FUTURES_TAPE_ROOT", str(tmp_path))
    symbol, identity = "ES/F", "LSE:ES.F"
    raw = raw_export_path(tmp_path, "lse", symbol, "2026-01-01", "2026-01-02")
    fti._write_dataframe_export(
        pd.DataFrame({
            "timestamp": ["2026-01-01T09:30:00Z", "2026-01-01T09:30:30Z"],
            "price": [100.0, 101.0],
            "volume": [1.0, 2.0],
        }),
        raw,
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS,
        source_symbol=symbol,
        state=PartitionState.FINAL,
        request_start="2026-01-01",
        request_end="2026-01-02",
    )
    normalize = type("Args", (), {
        "root": str(tmp_path), "symbol": symbol, "identity": identity, "force": False,
    })()
    derive = type("Args", (), {
        "root": str(tmp_path), "instrument": identity, "freq": "1min", "force": False,
    })()

    assert fti.cmd_normalize_lse(normalize) == 0
    assert normalized_day_path(tmp_path, "lse", identity, "2026-01-01").is_file()
    assert fti.cmd_derive_bars(derive) == 0
    target = derived_bar_path(tmp_path, identity, "1min", "2026-01-01")
    bars = pd.read_parquet(target)
    assert bars[["open", "high", "low", "close", "volume"]].to_dict("records") == [
        {"open": 100.0, "high": 101.0, "low": 100.0, "close": 101.0, "volume": 3.0}
    ]
    assert audit_manifests(tmp_path) == []


def test_production_capacity_refuses_system_root_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "is_mount", lambda path: path == Path(path.anchor))

    def no_measure(_path):
        pytest.fail("an absent data volume must not be measured as the system root")

    monkeypatch.setattr("lib.dataos.futures_tape.shutil.disk_usage", no_measure)
    with pytest.raises(FuturesTapeError, match="not mounted"):
        capacity(tmp_path / "missing" / "tape", require_mounted_volume=True)


def test_production_capacity_measures_the_contained_mount(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    mount = tmp_path / "mounted"
    mount.mkdir()
    root = mount / "future" / "tape"
    monkeypatch.setattr(Path, "is_mount", lambda path: path == mount or path == Path(path.anchor))
    measured = []

    def measure(path):
        measured.append(path)
        return (200 * 1024 ** 3, 50 * 1024 ** 3, 150 * 1024 ** 3)

    monkeypatch.setattr("lib.dataos.futures_tape.shutil.disk_usage", measure)
    args = fti._build_parser().parse_args([
        "--root", str(root), "storage", "--reserve-gib", "100", "--require-mounted-volume",
    ])

    assert fti.cmd_storage(args) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["root"] == str(root)
    assert receipt["mounted_volume_verified"] is True
    assert receipt["bulk_ready"] is True
    assert measured == [mount]


def test_production_capacity_rejects_root_symlink_escape(monkeypatch, tmp_path: Path) -> None:
    mount, outside = tmp_path / "mounted", tmp_path / "outside"
    mount.mkdir()
    outside.mkdir()
    (mount / "escape").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(Path, "is_mount", lambda path: path == mount or path == Path(path.anchor))

    def no_measure(_path):
        pytest.fail("a root redirected off its configured volume must not be measured")

    monkeypatch.setattr("lib.dataos.futures_tape.shutil.disk_usage", no_measure)
    with pytest.raises(FuturesTapeError, match="escapes"):
        capacity(mount / "escape" / "tape", require_mounted_volume=True)

