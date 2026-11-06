"""The current artifact reader distinguishes absence, failure and valid emptiness."""
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import international_macro_dashboard as owner


@pytest.fixture
def source(monkeypatch, tmp_path):
    monkeypatch.setattr(owner.config, "load", lambda: {"intl": {"countries": {"JP": {}, "KR": {}}}})
    monkeypatch.setattr(owner.config, "data_dir", lambda: tmp_path)
    directory = tmp_path / "intl_regime"
    directory.mkdir()
    path = directory / "JP_history.parquet"
    frame = pd.DataFrame({"growth_score": [0.0, None], "inflation_score": [-0.5, 0.0]},
                         index=pd.date_range("2026-01-01", periods=2, tz="Asia/Tokyo"))
    return path, frame


def test_real_parquet_retains_values_geometry_and_acquisition_clock(source):
    path, frame = source
    frame.to_parquet(path)
    result = owner.load_history_result("JP")
    assert set(result) == {"status", "market_id", "artifact_ref", "read_at", "method_ref", "frame"}
    assert result["status"] == "ready"
    assert result["market_id"] == "JP"
    assert result["artifact_ref"] == "intl_regime/JP_history.parquet"
    assert result["method_ref"] is None
    assert datetime.fromisoformat(result["read_at"]).utcoffset().total_seconds() == 0
    pd.testing.assert_frame_equal(result["frame"], frame, check_freq=False)


def test_missing_and_failed_reads_are_distinct(source, monkeypatch):
    path, _ = source
    calls = []
    def broken(candidate):
        calls.append(candidate)
        raise RuntimeError("private secret path /do/not/publish")
    monkeypatch.setattr(owner.pd, "read_parquet", broken)
    assert owner.load_history_result("JP")["status"] == "missing"
    assert calls == []
    path.touch()
    result = owner.load_history_result("JP")
    assert result["status"] == "failed" and result["frame"] is None
    assert calls == [path]
    assert "private" not in str(result) and str(path.parent) not in str(result)


@pytest.mark.parametrize("error,status", [
    (PermissionError, "failed"), (OSError, "failed"), (FileNotFoundError, "missing"),
])
def test_stat_failure_is_failed_not_missing(source, monkeypatch, error, status):
    def unavailable(*args, **kwargs):
        raise error("private filesystem denial")
    monkeypatch.setattr(owner.Path, "stat", unavailable)
    assert owner.load_history_result("JP")["status"] == status


@pytest.mark.parametrize("country", ["../JP", "JP/..", "jp", "XX", "JP\x00", None, 1, True, ["JP"]])
def test_unsupported_country_never_constructs_artifact_path(source, monkeypatch, country):
    def forbidden():
        raise AssertionError("unsupported country reached data path")
    monkeypatch.setattr(owner.config, "data_dir", forbidden)
    result = owner.load_history_result(country)
    assert result["status"] == "unsupported"
    assert result["market_id"] is None and result["artifact_ref"] is None
    assert result["frame"] is None


def test_configuration_failure_is_failed_and_never_reads_artifact(source, monkeypatch):
    def broken():
        raise RuntimeError("private configuration detail")
    monkeypatch.setattr(owner.config, "load", broken)
    monkeypatch.setattr(owner.pd, "read_parquet", lambda _: pytest.fail("unexpected artifact read"))
    result = owner.load_history_result("JP")
    assert result["status"] == "failed"
    assert result["artifact_ref"] is None and result["frame"] is None
    assert "private" not in str(result)


@pytest.mark.parametrize("kind", ["not_frame", "range_index", "nat", "duplicates", "unsorted", "duplicate_columns", "missing_column"])
def test_invalid_geometry_is_explicit(source, monkeypatch, kind):
    path, frame = source
    path.touch()
    if kind == "not_frame":
        frame = {"growth_score": []}
    elif kind == "range_index":
        frame = frame.reset_index(drop=True)
    elif kind == "nat":
        frame.index = pd.DatetimeIndex([frame.index[0], pd.NaT])
    elif kind == "duplicates":
        frame.index = pd.DatetimeIndex([frame.index[0], frame.index[0]])
    elif kind == "unsorted":
        frame = frame.iloc[::-1]
    elif kind == "duplicate_columns":
        frame = pd.concat([frame, frame[["growth_score"]]], axis=1)
    else:
        frame = frame.drop(columns="growth_score")
    monkeypatch.setattr(owner.pd, "read_parquet", lambda _: frame)
    result = owner.load_history_result("JP")
    assert result["status"] == "invalid" and result["frame"] is None


def test_empty_valid_frame_is_preserved_by_compatibility_wrapper(source, monkeypatch):
    path, frame = source
    path.touch()
    empty = frame.iloc[:0]
    calls = []
    def read(candidate):
        calls.append(candidate)
        return empty
    monkeypatch.setattr(owner.pd, "read_parquet", read)
    receipt = owner.load_history_result("JP")
    assert receipt["status"] == "empty" and receipt["frame"] is empty
    assert owner.load_history("JP") is empty
    assert calls == [path, path]


def test_wrapper_delegates_once_and_preserves_frame_identity(source, monkeypatch):
    _, frame = source
    calls = []
    def receipt(country):
        calls.append(country)
        return {"status": "ready", "frame": frame}
    monkeypatch.setattr(owner, "load_history_result", receipt)
    assert owner.load_history("JP") is frame
    assert calls == ["JP"]


def test_reader_does_not_mutate_frame_or_write(source, monkeypatch):
    path, frame = source
    path.touch()
    before = frame.copy(deep=True)
    calls = []
    def read(candidate):
        calls.append(candidate)
        return frame
    def forbidden(*args, **kwargs):
        pytest.fail("reader attempted a write")
    monkeypatch.setattr(owner.pd, "read_parquet", read)
    for name in ("to_parquet", "to_json", "to_csv"):
        monkeypatch.setattr(pd.DataFrame, name, forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    result = owner.load_history_result("JP")
    assert result["frame"] is frame and calls == [path]
    pd.testing.assert_frame_equal(frame, before)
