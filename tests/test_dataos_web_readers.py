"""Real-handle qualification for the bounded web data readers.

All files are temporary synthetic fixtures. No application config, provider,
collector, production data directory or network service is used.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import io
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lib.dataos import web_readers as readers
from lib.dataos.web_readers import ReaderError, inspect_file, read_rows


def _read(raw: bytes, suffix: str, **kwargs):
    with io.BytesIO(raw) as handle:
        return read_rows(handle, suffix, file_bytes=len(raw), **kwargs)


def _error(raw: bytes, suffix: str, code: str, **kwargs):
    with pytest.raises(ReaderError) as caught:
        _read(raw, suffix, **kwargs)
    assert caught.value.code == code
    assert str(caught.value) == code


@pytest.fixture
def parquet_path(tmp_path):
    path = tmp_path / "history.parquet"
    table = pa.table({
        "symbol": ["AMD", "MU", "AMD", "AMD", "MU", "AMD"],
        "published_at": pa.array([
            datetime(2026, 10, day, 12, tzinfo=timezone.utc)
            for day in (8, 9, 9, 10, 10, 11)
        ], type=pa.timestamp("us", tz="UTC")),
        "close_tradj": [1.0, 2.0, float("nan"), 4.0, float("inf"), 6.0],
        "session": pa.array([date(2026, 10, day) for day in (8, 9, 9, 10, 10, 11)]),
        "index": [100, 101, 102, 103, 104, 105],
    })
    pq.write_table(table, path, row_group_size=2)
    return path


def test_real_parquet_metadata_keeps_source_columns_and_clocks(parquet_path):
    with parquet_path.open("rb") as handle:
        handle.seek(5)
        result = inspect_file(handle, ".parquet", file_bytes=parquet_path.stat().st_size)
        assert handle.tell() == 5
        assert not handle.closed
    assert result["row_count"] == 6
    assert result["row_groups"] == 3
    assert result["observed_rows"] == 0
    assert result["columns"] == ["symbol", "published_at", "close_tradj", "session", "index"]
    assert result["time_ranges"]["published_at"]["min"] == "2026-10-08T12:00:00+00:00"
    assert result["time_ranges"]["published_at"]["max"] == "2026-10-11T12:00:00+00:00"
    assert result["time_ranges"]["session"]["min"] == "2026-10-08"
    assert result["time_ranges"]["index"]["max"] == 105
    assert result["time_ranges"]["published_at"]["statistics_complete"] is True
    assert not any("fresh" in key.lower() or "mtime" in key.lower() for key in result)


def test_real_parquet_projection_filters_and_absolute_positions(parquet_path):
    with parquet_path.open("rb") as handle:
        result = read_rows(
            handle, ".parquet", file_bytes=parquet_path.stat().st_size,
            columns=["close_tradj", "published_at"], time_column="published_at",
            start="2026-10-09", end="2026-10-10", equals={"symbol": "AMD"},
            offset=1, limit=2,
        )
        assert not handle.closed
        assert handle.tell() == 0
    assert result["row_positions"] == [2, 3]
    assert result["scanned_rows"] == 3
    assert result["next_offset"] == 4
    assert result["scan_complete"] is False
    assert result["rows"] == [
        {"close_tradj": None, "published_at": "2026-10-09T12:00:00+00:00"},
        {"close_tradj": 4.0, "published_at": "2026-10-10T12:00:00+00:00"},
    ]
    assert result["missingness_notes"] == [{"code": "NONFINITE_AS_NULL", "count": 1}]
    json.dumps(result, allow_nan=False)


def test_parquet_resume_skips_row_groups_without_reindexing(parquet_path):
    with parquet_path.open("rb") as handle:
        result = read_rows(
            handle, "PARQUET", file_bytes=parquet_path.stat().st_size,
            columns=["symbol"], offset=4, limit=2,
        )
    assert result["rows"] == [{"symbol": "MU"}, {"symbol": "AMD"}]
    assert result["row_positions"] == [4, 5]
    assert result["scan_complete"] is True
    assert result["next_offset"] is None


def test_parquet_metadata_reports_missing_statistics(tmp_path):
    path = tmp_path / "no_stats.parquet"
    pq.write_table(pa.table({"event_at": ["2026-10-08", "2026-10-09"]}),
                   path, write_statistics=False)
    with path.open("rb") as handle:
        result = inspect_file(handle, ".parquet", file_bytes=path.stat().st_size)
    assert result["time_ranges"]["event_at"] == {
        "min": None, "max": None, "statistics_complete": False,
        "row_groups_with_statistics": 0, "ordering": "stored_column_statistics",
    }


def test_projected_parquet_group_allocation_boundary(parquet_path, monkeypatch):
    monkeypatch.setattr(readers, "MAX_ROW_GROUP_BYTES", 1)
    with parquet_path.open("rb") as handle:
        with pytest.raises(ReaderError) as caught:
            read_rows(handle, ".parquet", file_bytes=parquet_path.stat().st_size,
                      columns=["symbol"])
    assert caught.value.code == "ROW_GROUP_TOO_LARGE"


def test_parquet_decimal_binary_and_nested_values_are_json_representable(tmp_path):
    path = tmp_path / "typed.parquet"
    table = pa.table({
        "exact": pa.array([Decimal("123.45")], type=pa.decimal128(8, 2)),
        "binary": [b"abc"],
        "nested": [{"a": [1.0, float("nan")]}],
    })
    pq.write_table(table, path)
    with path.open("rb") as handle:
        result = read_rows(handle, ".parquet", file_bytes=path.stat().st_size)
    assert result["rows"] == [{
        "exact": "123.45", "binary": {"encoding": "base64", "value": "YWJj"},
        "nested": {"a": [1.0, None]},
    }]
    assert result["missingness_notes"] == [{"code": "NONFINITE_AS_NULL", "count": 1}]
    json.dumps(result, allow_nan=False)


def test_csv_projection_keeps_values_and_calendar_dates(tmp_path):
    path = tmp_path / "history.csv"
    path.write_bytes(
        b"Date,symbol,close_tradj\r\n2026-10-08,AMD,1.00\r\n"
        b"2026-10-09,MU,2.00\r\n2026-10-10,AMD,3.00\r\n"
    )
    with path.open("rb") as handle:
        handle.seek(3)
        meta = inspect_file(handle, ".csv", file_bytes=path.stat().st_size)
        result = read_rows(
            handle, ".csv", file_bytes=path.stat().st_size,
            columns=["symbol", "close_tradj"], time_column="Date",
            start="2026-10-09", end="2026-10-10", equals={"symbol": "AMD"},
        )
        assert handle.tell() == 3
    assert meta["row_count"] == 3
    assert meta["columns"] == ["Date", "symbol", "close_tradj"]
    assert result["rows"] == [{"symbol": "AMD", "close_tradj": "3.00"}]
    assert result["row_positions"] == [2]
    assert result["scanned_rows"] == 3
    assert result["scan_complete"] is True


def test_csv_handles_bom_quoted_newlines_and_blank_lines():
    raw = '\ufeffname,note\nA,"first\nsecond"\n\nB,"last"\n'.encode()
    result = _read(raw, ".csv")
    assert result["row_positions"] == [0, 1]
    assert result["rows"] == [
        {"name": "A", "note": "first\nsecond"}, {"name": "B", "note": "last"}]


@pytest.mark.parametrize("suffix", [".jsonl", ".ndjson"])
def test_jsonl_blank_lines_and_heterogeneous_fields(suffix):
    raw = b'\n{"symbol":"AMD","price":1}\n\n{"symbol":"MU","session":"2026-10-10"}\n'
    result = _read(raw, suffix, offset=1)
    assert result["rows"] == [{"symbol": "MU", "price": None, "session": "2026-10-10"}]
    assert result["row_positions"] == [1]
    assert result["scanned_rows"] == 1
    assert result["missingness_notes"] == [{"code": "ABSENT_FIELD_AS_NULL", "count": 1}]


@pytest.mark.parametrize("value,count", [
    ([{"x": 1}, {"x": 2}], 2), ({"x": 1, "nested": {"y": 2}}, 1), ([], 0),
])
def test_json_array_and_dictionary_envelopes(value, count):
    raw = json.dumps(value).encode()
    with io.BytesIO(raw) as handle:
        result = inspect_file(handle, ".json", file_bytes=len(raw))
    assert result["row_count"] == count
    observed = _read(raw, ".json")
    assert len(observed["rows"]) == count
    assert observed["scan_complete"] is True
    assert observed["next_offset"] is None


def test_nonfinite_json_values_become_null_with_missingness():
    raw = b'[{"x":NaN,"y":Infinity,"z":-Infinity,"a":[NaN]}]'
    result = _read(raw, ".json")
    assert result["rows"] == [{"x": None, "y": None, "z": None, "a": [None]}]
    assert result["missingness_notes"] == [{"code": "NONFINITE_AS_NULL", "count": 4}]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("suffix", [".json", ".jsonl", ".csv"])
def test_scan_budget_and_resumption_are_original_row_based(suffix):
    records = [{"symbol": s, "n": i} for i, s in enumerate(["B", "B", "A", "B", "A", "A"])]
    if suffix == ".json":
        raw = json.dumps(records).encode()
    elif suffix == ".jsonl":
        raw = "\n".join(json.dumps(row) for row in records).encode()
    else:
        raw = ("symbol,n\n" + "\n".join(f"{r['symbol']},{r['n']}" for r in records)).encode()
    first = _read(raw, suffix, equals={"symbol": "A"}, max_scan_rows=2)
    assert first["rows"] == []
    assert first["row_positions"] == []
    assert first["scanned_rows"] == 2
    assert first["next_offset"] == 2
    assert first["scan_complete"] is False
    second = _read(raw, suffix, equals={"symbol": "A"}, offset=first["next_offset"], limit=2)
    assert second["row_positions"] == [2, 4]
    assert second["scanned_rows"] == 3
    assert second["next_offset"] == 5
    last = _read(raw, suffix, equals={"symbol": "A"}, offset=second["next_offset"])
    assert last["row_positions"] == [5]
    assert last["scan_complete"] is True
    beyond = _read(raw, suffix, offset=50)
    assert beyond == {"rows": [], "row_positions": [], "scanned_rows": 0,
                      "next_offset": None, "scan_complete": True, "missingness_notes": []}


def test_calendar_date_bounds_do_not_relabel_local_date_as_utc():
    raw = json.dumps([
        {"t": "2026-10-10T23:30:00-05:00", "id": 1},
        {"t": "2026-10-11T00:30:00+14:00", "id": 2},
    ]).encode()
    result = _read(raw, ".json", time_column="t", start="2026-10-10", end="2026-10-10")
    assert result["row_positions"] == [0]
    assert result["rows"][0]["t"] == "2026-10-10T23:30:00-05:00"
    instant = _read(raw, ".json", time_column="t",
                    start="2026-10-10T00:00:00Z", end="2026-10-10T23:59:59Z")
    assert instant["row_positions"] == [1]


def test_missing_clock_is_explicitly_excluded():
    raw = b'[{"date":null},{"date":"2026-10-10"}]'
    result = _read(raw, ".json", time_column="date", start="2026-10-10")
    assert result["row_positions"] == [1]
    assert result["missingness_notes"] == [{"code": "MISSING_TIME_EXCLUDED", "count": 1}]


@pytest.mark.parametrize("raw,kwargs,code", [
    (b'[{"t":"2026-10-10T01:00:00Z"},{"t":"2026-10-10T02:00:00"}]',
     {"time_column": "t", "start": "2026-10-10"}, "TIMEZONE_MISMATCH"),
    (b'[{"t":"2026-10-10T01:00:00Z"}]',
     {"time_column": "t", "start": "2026-10-10T00:00:00"}, "TIMEZONE_MISMATCH"),
    (b'[{"t":"2026-10-10"}]',
     {"time_column": "t", "start": "2026-10-10T00:00:00"}, "TIME_PRECISION_MISMATCH"),
    (b'[{"t":1234}]', {"time_column": "t", "start": "2026-10-10"}, "INVALID_TIME_VALUE"),
    (b'[{"t":"garbage"}]', {"time_column": "t", "start": "2026-10-10"}, "INVALID_TIME_VALUE"),
    (b'[{"t":"2026-10-10"}]', {"start": "2026-10-10"}, "TIME_COLUMN_REQUIRED"),
    (b'[{"t":"2026-10-10"}]',
     {"time_column": "t", "start": "2026-10-11", "end": "2026-10-10"}, "INVALID_TIME_BOUND"),
    (b'[{"t":"2026-10-10"}]',
     {"time_column": "t", "start": "2026-10-10T00:00:00Z",
      "end": "2026-10-11T00:00:00"}, "TIMEZONE_MISMATCH"),
    (b'[{"t":"2026-10-10"}]', {"time_column": "missing"}, "INVALID_TIME_COLUMN"),
])
def test_invalid_time_controls_are_closed(raw, kwargs, code):
    _error(raw, ".json", code, **kwargs)


@pytest.mark.parametrize("kwargs,code", [
    ({"columns": ["missing"]}, "INVALID_COLUMNS"),
    ({"columns": ["x", "x"]}, "INVALID_COLUMNS"),
    ({"columns": []}, "INVALID_COLUMNS"),
    ({"columns": ["x"] * 129}, "INVALID_COLUMNS"),
    ({"columns": "x"}, "INVALID_COLUMNS"),
    ({"equals": {"missing": "v"}}, "INVALID_FILTER_COLUMN"),
    ({"equals": {"x": float("nan")}}, "INVALID_FILTER"),
    ({"equals": {"x": []}}, "INVALID_FILTER"),
    ({"offset": -1}, "INVALID_OFFSET"),
    ({"offset": True}, "INVALID_OFFSET"),
    ({"limit": 201}, "INVALID_LIMIT"),
    ({"limit": 0}, "INVALID_LIMIT"),
    ({"max_scan_rows": 100001}, "INVALID_SCAN_LIMIT"),
    ({"max_scan_rows": 0}, "INVALID_SCAN_LIMIT"),
])
def test_argument_bounds(kwargs, code):
    _error(b'[{"x":1}]', ".json", code, **kwargs)


@pytest.mark.parametrize("raw,suffix", [
    (b'{"x":', ".json"), (b'[1,2]', ".json"), (b'42', ".json"),
    (b'{"x":1,"x":2}', ".json"), (b'{"x":1}\nnope', ".jsonl"),
    (b'[1,2]', ".jsonl"), (b'{"x":"\xff"}', ".json"),
    (b"a,a\n1,2", ".csv"), (b"a,b\n1", ".csv"), (b'a\n"unterminated', ".csv"),
    (b"", ".csv"), (b"not parquet", ".parquet"),
])
def test_malformed_sources_have_no_raw_error_text(raw, suffix):
    _error(raw, suffix, "MALFORMED_SOURCE")


def test_unsupported_compression_is_not_automatically_opened():
    _error(b"anything", ".json.gz", "UNSUPPORTED_FORMAT")
    _error(b"anything", ".sqlite", "UNSUPPORTED_FORMAT")


def test_text_byte_limit_is_enforced_before_decoding(tmp_path):
    path = tmp_path / "too_large.json"
    with path.open("wb") as handle:
        handle.truncate(readers.MAX_TEXT_BYTES + 1)
    with path.open("rb") as handle:
        with pytest.raises(ReaderError) as caught:
            inspect_file(handle, ".json", file_bytes=path.stat().st_size)
    assert caught.value.code == "FILE_TOO_LARGE"


def test_parquet_footer_cap_precedes_arrow_allocation():
    raw = b"PAR1" + (readers.MAX_FOOTER_BYTES + 1).to_bytes(4, "little") + b"PAR1"
    _error(raw, ".parquet", "METADATA_TOO_LARGE")


def test_admitted_length_must_match_current_handle():
    with io.BytesIO(b'[]') as handle:
        handle.seek(1)
        with pytest.raises(ReaderError) as caught:
            inspect_file(handle, ".json", file_bytes=3)
        assert handle.tell() == 1
        assert not handle.closed
    assert caught.value.code == "SOURCE_SIZE_CHANGED"


def test_handle_position_is_retained_on_malformed_source():
    with io.BytesIO(b'{"bad":') as handle:
        handle.seek(2)
        with pytest.raises(ReaderError):
            read_rows(handle, ".json", file_bytes=7)
        assert handle.tell() == 2
        assert not handle.closed


def test_binary_handle_is_required_and_dependency_errors_are_closed():
    with io.StringIO("[]") as handle:
        with pytest.raises(ReaderError) as caught:
            inspect_file(handle, ".json", file_bytes=2)
    assert caught.value.code == "BINARY_STREAM_REQUIRED"


def test_scalar_bool_filter_does_not_equal_numeric_zero():
    result = _read(b'[{"x":false},{"x":0}]', ".json", equals={"x": 0})
    assert result["row_positions"] == [1]


def test_source_more_than_128_columns_can_be_explicitly_projected():
    value = {f"c{i}": i for i in range(130)}
    raw = json.dumps([value]).encode()
    with io.BytesIO(raw) as handle:
        observed = inspect_file(handle, ".json", file_bytes=len(raw))
    assert observed["total_columns"] == 130
    assert observed["schema_complete"] is False
    assert len(observed["columns"]) == 128
    _error(raw, ".json", "TOO_MANY_COLUMNS")
    assert _read(raw, ".json", columns=["c129"])["rows"] == [{"c129": 129}]


def test_large_unselected_cell_does_not_block_narrow_projection():
    raw = json.dumps([{"id": 1, "body": "a" * (readers.MAX_CELL_BYTES + 1)}]).encode()
    assert _read(raw, ".json", columns=["id"])["rows"] == [{"id": 1}]
    _error(raw, ".json", "VALUE_TOO_LARGE")
