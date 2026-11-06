"""Bounded data observations over already-open, existing binary file handles.

This module owns no paths, credentials, configuration, stores or execution. The
caller owns opening/admission, source identity, and the final serialized response
budget. Original field names, row positions and clocks are retained; no freshness,
price basis, timezone or epoch unit is guessed.

Text sources are decoded/validated within a 32 MiB byte envelope to establish
their exact schema. Query scanned_rows counts records evaluated after offset,
not the separate bounded text-format/schema pass. Parquet uses footer metadata
and projected row-group batches rather than loading a whole table.
"""
from __future__ import annotations

import base64
from collections import Counter
from contextlib import contextmanager
import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import io
import json
import math
import re
from typing import Any, BinaryIO, Iterator

MAX_TEXT_BYTES = 32 * 1024 * 1024
MAX_FOOTER_BYTES = 8 * 1024 * 1024
MAX_ROW_GROUP_BYTES = 256 * 1024 * 1024
MAX_COLUMNS = 128
MAX_SOURCE_COLUMNS = 4096
MAX_ROWS = 200
MAX_SCAN_ROWS = 100_000
MAX_CELL_BYTES = 1024 * 1024
MAX_NESTING = 32
MAX_CONTAINER_ITEMS = 4096
_FORMATS = {"parquet": "parquet", "csv": "csv", "jsonl": "jsonl",
            "ndjson": "jsonl", "json": "json"}
_CLOCK_NAME = re.compile(
    r"(?:^|[_.])(?:date|datetime|timestamp|time|ts|asof|as_of|session|index)"
    r"(?:$|[_.])|(?:_date|_time|_timestamp|_at)$|^__index_level_\d+__$", re.I
)


class ReaderError(Exception):
    """A closed, non-secret observation refusal."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _integer(value: Any, minimum: int, maximum: int, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReaderError(code)
    if not minimum <= value <= maximum:
        raise ReaderError(code)
    return value


def _format(suffix: str, file_bytes: int) -> str:
    if not isinstance(suffix, str) or suffix.lower().lstrip(".") not in _FORMATS:
        raise ReaderError("UNSUPPORTED_FORMAT")
    kind = _FORMATS[suffix.lower().lstrip(".")]
    _integer(file_bytes, 0, 2**63 - 1, "INVALID_FILE_SIZE")
    if kind != "parquet" and file_bytes > MAX_TEXT_BYTES:
        raise ReaderError("FILE_TOO_LARGE")
    return kind


@contextmanager
def _open_observation(stream: BinaryIO, file_bytes: int):
    """Retain ownership and original position; detect observed size changes."""
    try:
        position = stream.tell()
    except Exception:
        raise ReaderError("SOURCE_UNREADABLE") from None
    try:
        if not isinstance(stream.read(0), bytes):
            raise ReaderError("BINARY_STREAM_REQUIRED")
        stream.seek(0, io.SEEK_END)
        if stream.tell() != file_bytes:
            raise ReaderError("SOURCE_SIZE_CHANGED")
        stream.seek(0)
        yield
        stream.seek(0, io.SEEK_END)
        if stream.tell() != file_bytes:
            raise ReaderError("SOURCE_SIZE_CHANGED")
    finally:
        try:
            stream.seek(position)
        except Exception:
            raise ReaderError("SOURCE_UNREADABLE") from None


def _field_names(names: list[str]) -> list[str]:
    if len(names) > MAX_SOURCE_COLUMNS:
        raise ReaderError("TOO_MANY_COLUMNS")
    if any(not isinstance(n, str) or not n or len(n) > 1024 for n in names):
        raise ReaderError("MALFORMED_SOURCE")
    if len(names) != len(set(names)):
        raise ReaderError("MALFORMED_SOURCE")
    return names


def _object(pairs: list[tuple[str, Any]]) -> dict:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ReaderError("MALFORMED_SOURCE")
        obj[key] = value
    return obj


def _decode_json(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_object)
    except ReaderError:
        raise
    except Exception:
        raise ReaderError("MALFORMED_SOURCE") from None


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    raise ReaderError("MALFORMED_SOURCE")


class _TextSource:
    """A bounded text body with repeatable, non-materializing CSV/JSONL passes."""

    def __init__(self, stream: BinaryIO, kind: str, file_bytes: int) -> None:
        raw = stream.read(file_bytes + 1)
        if not isinstance(raw, bytes):
            raise ReaderError("BINARY_STREAM_REQUIRED")
        if len(raw) != file_bytes:
            raise ReaderError("SOURCE_SIZE_CHANGED")
        try:
            self.text = raw.decode("utf-8-sig")
        except UnicodeError:
            raise ReaderError("MALFORMED_SOURCE") from None
        self.kind = kind
        self.json_rows: list[dict] | None = None
        self.header: list[str] | None = None
        if kind == "json":
            value = _decode_json(self.text)
            if isinstance(value, dict):
                self.json_rows = [value]
            elif isinstance(value, list) and all(isinstance(r, dict) for r in value):
                self.json_rows = value
            else:
                raise ReaderError("MALFORMED_SOURCE")
        elif kind == "csv":
            reader = csv.reader(io.StringIO(self.text, newline=""), strict=True)
            try:
                self.header = _field_names(next(reader))
            except StopIteration:
                raise ReaderError("MALFORMED_SOURCE") from None
            except csv.Error:
                raise ReaderError("MALFORMED_SOURCE") from None
            if not self.header:
                raise ReaderError("MALFORMED_SOURCE")
        self.columns: list[str] = list(self.header or [])
        types: dict[str, set[str]] = {n: {"string"} for n in self.columns}
        self.row_count = 0
        for row in self.rows():
            for key in _field_names(list(row)):
                if key not in types:
                    self.columns.append(key)
                    types[key] = set()
                    if len(self.columns) > MAX_SOURCE_COLUMNS:
                        raise ReaderError("TOO_MANY_COLUMNS")
                types[key].add(_type_name(row[key]))
            self.row_count += 1
        self.schema = [{"name": n, "type": "|".join(sorted(types[n]))}
                       for n in self.columns]

    def rows(self) -> Iterator[dict]:
        if self.kind == "json":
            yield from self.json_rows or []
        elif self.kind == "jsonl":
            for line in io.StringIO(self.text):
                if not line.strip():
                    continue
                row = _decode_json(line)
                if not isinstance(row, dict):
                    raise ReaderError("MALFORMED_SOURCE")
                yield row
        else:
            try:
                reader = csv.reader(io.StringIO(self.text, newline=""), strict=True)
                next(reader)
                for fields in reader:
                    if not fields:
                        continue
                    if len(fields) != len(self.header or []):
                        raise ReaderError("MALFORMED_SOURCE")
                    yield dict(zip(self.header or [], fields, strict=True))
            except (csv.Error, StopIteration):
                raise ReaderError("MALFORMED_SOURCE") from None


def _parquet(stream: BinaryIO, file_bytes: int):
    if file_bytes < 12:
        raise ReaderError("MALFORMED_SOURCE")
    stream.seek(0)
    if stream.read(4) != b"PAR1":
        raise ReaderError("MALFORMED_SOURCE")
    stream.seek(-8, io.SEEK_END)
    trailer = stream.read(8)
    if len(trailer) != 8 or trailer[4:] != b"PAR1":
        raise ReaderError("MALFORMED_SOURCE")
    footer_size = int.from_bytes(trailer[:4], "little")
    if footer_size > MAX_FOOTER_BYTES:
        raise ReaderError("METADATA_TOO_LARGE")
    if not footer_size or footer_size > file_bytes - 12:
        raise ReaderError("MALFORMED_SOURCE")
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise ReaderError("DEPENDENCY_UNAVAILABLE") from None
    stream.seek(0)
    try:
        result = pq.ParquetFile(
            stream, pre_buffer=False, buffer_size=65536,
            thrift_string_size_limit=MAX_FOOTER_BYTES,
            thrift_container_size_limit=1_000_000,
        )
        _field_names(result.schema_arrow.names)
        return result
    except ReaderError:
        raise
    except Exception:
        raise ReaderError("MALFORMED_SOURCE") from None


def _json_value(value: Any, notes: Counter, depth: int = 0) -> Any:
    if depth > MAX_NESTING:
        raise ReaderError("VALUE_TOO_COMPLEX")
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            notes["NONFINITE_AS_NULL"] += 1
            return None
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            notes["NONFINITE_AS_NULL"] += 1
            return None
        return str(value)
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_CELL_BYTES:
            raise ReaderError("VALUE_TOO_LARGE")
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return {"days": value.days, "seconds": value.seconds,
                "microseconds": value.microseconds}
    if isinstance(value, bytes):
        if len(value) > MAX_CELL_BYTES:
            raise ReaderError("VALUE_TOO_LARGE")
        return {"encoding": "base64",
                "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise ReaderError("VALUE_TOO_COMPLEX")
        _field_names(list(value))
        return {k: _json_value(v, notes, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise ReaderError("VALUE_TOO_COMPLEX")
        return [_json_value(v, notes, depth + 1) for v in value]
    raise ReaderError("UNSUPPORTED_VALUE")


def _notes(notes: Counter) -> list[dict]:
    return [{"code": key, "count": notes[key]} for key in sorted(notes)]


def _parquet_metadata(pf, file_bytes: int) -> dict:
    import pyarrow as pa

    names = pf.schema_arrow.names
    fields = list(pf.schema_arrow)[:MAX_COLUMNS]
    ranges: dict[str, dict] = {}
    notes: Counter = Counter()
    for field in fields:
        if not (pa.types.is_timestamp(field.type) or pa.types.is_date(field.type)
                or pa.types.is_time(field.type) or _CLOCK_NAME.search(field.name)):
            continue
        lows: list[Any] = []
        highs: list[Any] = []
        required = 0
        for group_index in range(pf.metadata.num_row_groups):
            group = pf.metadata.row_group(group_index)
            if not group.num_rows:
                continue
            required += 1
            for column_index in range(group.num_columns):
                column = group.column(column_index)
                if column.path_in_schema != field.name:
                    continue
                stats = column.statistics
                if stats is not None and stats.has_min_max:
                    low, high = stats.min, stats.max
                    if low is not None and high is not None:
                        lows.append(low)
                        highs.append(high)
                break
        try:
            low = min(lows) if lows else None
            high = max(highs) if highs else None
        except (TypeError, ValueError):
            raise ReaderError("MALFORMED_SOURCE") from None
        ranges[field.name] = {
            "min": _json_value(low, notes), "max": _json_value(high, notes),
            "statistics_complete": len(lows) == required and required > 0,
            "row_groups_with_statistics": len(lows),
            "ordering": "stored_column_statistics",
        }
    return {
        "format": "parquet", "file_bytes": file_bytes,
        "row_count": pf.metadata.num_rows, "observed_rows": 0,
        "columns": names[:MAX_COLUMNS],
        "schema": [{"name": f.name, "type": str(f.type)} for f in fields],
        "total_columns": len(names), "schema_complete": len(names) <= MAX_COLUMNS,
        "row_groups": pf.metadata.num_row_groups, "scan_complete": True,
        "time_ranges": ranges, "missingness_notes": _notes(notes),
    }


def inspect_file(stream: BinaryIO, suffix: str, *, file_bytes: int) -> dict:
    """Observe schema/count/clocks without closing or taking ownership of a file."""
    kind = _format(suffix, file_bytes)
    try:
        with _open_observation(stream, file_bytes):
            if kind == "parquet":
                return _parquet_metadata(_parquet(stream, file_bytes), file_bytes)
            source = _TextSource(stream, kind, file_bytes)
            return {
                "format": kind, "file_bytes": file_bytes,
                "row_count": source.row_count, "observed_rows": source.row_count,
                "columns": source.columns[:MAX_COLUMNS],
                "schema": source.schema[:MAX_COLUMNS],
                "total_columns": len(source.columns),
                "schema_complete": len(source.columns) <= MAX_COLUMNS,
                "scan_complete": True, "time_ranges": {},
                "missingness_notes": [],
            }
    except ReaderError:
        raise
    except OSError:
        raise ReaderError("SOURCE_UNREADABLE") from None
    except Exception:
        raise ReaderError("MALFORMED_SOURCE") from None


def _clock(value: Any, code: str) -> date | datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ReaderError(code)
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        if not re.match(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}", value):
            raise ValueError
        return datetime.fromisoformat(value.replace("z", "+00:00")
                                      .replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ReaderError(code) from None


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


class _TimeFilter:
    def __init__(self, start: str | None, end: str | None) -> None:
        self.start = _clock(start, "INVALID_TIME_BOUND") if start is not None else None
        self.end = _clock(end, "INVALID_TIME_BOUND") if end is not None else None
        self.awareness: bool | None = None
        for value in (self.start, self.end):
            if isinstance(value, datetime):
                self._check(value)
        if self.start is not None and self.end is not None:
            if isinstance(self.start, datetime) and isinstance(self.end, datetime):
                reversed_bounds = self.start > self.end
            else:
                first = self.start.date() if isinstance(self.start, datetime) else self.start
                last = self.end.date() if isinstance(self.end, datetime) else self.end
                reversed_bounds = first > last
            if reversed_bounds:
                raise ReaderError("INVALID_TIME_BOUND")

    def _check(self, value: datetime) -> None:
        awareness = _aware(value)
        if self.awareness is not None and self.awareness != awareness:
            raise ReaderError("TIMEZONE_MISMATCH")
        self.awareness = awareness

    def accepts(self, value: Any, notes: Counter) -> bool:
        if self.start is None and self.end is None:
            return True
        if value is None or value == "":
            notes["MISSING_TIME_EXCLUDED"] += 1
            return False
        clock = _clock(value, "INVALID_TIME_VALUE")
        if isinstance(clock, datetime):
            self._check(clock)
        for bound, is_start in ((self.start, True), (self.end, False)):
            if bound is None:
                continue
            if isinstance(bound, datetime):
                if not isinstance(clock, datetime):
                    raise ReaderError("TIME_PRECISION_MISMATCH")
                compared = clock
            else:
                compared = clock.date() if isinstance(clock, datetime) else clock
            if (is_start and compared < bound) or (not is_start and compared > bound):
                return False
        return True


def _query_columns(names: list[str], columns, time_column, start, end, equals):
    if columns is not None and (not isinstance(columns, list) or not columns
                                or len(columns) > MAX_COLUMNS
                                or any(not isinstance(n, str) for n in columns)
                                or len(columns) != len(set(columns))):
        raise ReaderError("INVALID_COLUMNS")
    selected = list(names if columns is None else columns)
    if len(selected) > MAX_COLUMNS:
        raise ReaderError("TOO_MANY_COLUMNS")
    if any(n not in names for n in selected):
        raise ReaderError("INVALID_COLUMNS")
    if time_column is not None and (
        not isinstance(time_column, str) or time_column not in names
    ):
        raise ReaderError("INVALID_TIME_COLUMN")
    if (start is not None or end is not None) and time_column is None:
        raise ReaderError("TIME_COLUMN_REQUIRED")
    if start is not None and not isinstance(start, str):
        raise ReaderError("INVALID_TIME_BOUND")
    if end is not None and not isinstance(end, str):
        raise ReaderError("INVALID_TIME_BOUND")
    if equals is None:
        equals = {}
    if not isinstance(equals, dict) or len(equals) > MAX_COLUMNS:
        raise ReaderError("INVALID_FILTER")
    for key, value in equals.items():
        if not isinstance(key, str) or key not in names:
            raise ReaderError("INVALID_FILTER_COLUMN")
        if not (value is None or isinstance(value, (str, bool, int, float))):
            raise ReaderError("INVALID_FILTER")
        if isinstance(value, float) and not math.isfinite(value):
            raise ReaderError("INVALID_FILTER")
    needed = list(dict.fromkeys(selected + ([time_column] if time_column else [])
                                + list(equals)))
    return selected, needed, dict(equals), _TimeFilter(start, end)


def _parquet_rows(pf, names: list[str], offset: int) -> Iterator[tuple[int, dict]]:
    base = 0
    for group_index in range(pf.metadata.num_row_groups):
        group = pf.metadata.row_group(group_index)
        if base + group.num_rows <= offset:
            base += group.num_rows
            continue
        uncompressed = 0
        for column_index in range(group.num_columns):
            column = group.column(column_index)
            if any(column.path_in_schema == n or column.path_in_schema.startswith(n + ".")
                   for n in names):
                if column.total_uncompressed_size < 0:
                    raise ReaderError("MALFORMED_SOURCE")
                uncompressed += column.total_uncompressed_size
        if uncompressed > MAX_ROW_GROUP_BYTES:
            raise ReaderError("ROW_GROUP_TOO_LARGE")
        for batch in pf.iter_batches(batch_size=256, row_groups=[group_index],
                                     columns=names, use_threads=False):
            if set(batch.schema.names) != set(names) or len(batch.schema.names) != len(names):
                raise ReaderError("COLUMN_PROJECTION_MISMATCH")
            batch_end = base + batch.num_rows
            if batch_end <= offset:
                base = batch_end
                continue
            for index, row in enumerate(batch.to_pylist()):
                position = base + index
                if position >= offset:
                    yield position, row
            base = batch_end


def _equals(value: Any, expected: Any) -> bool:
    if isinstance(value, (datetime, date, time)):
        value = value.isoformat()
    if isinstance(value, bool) != isinstance(expected, bool):
        return False
    return value == expected


def _evaluate(records, *, row_count: int, selected: list[str], time_column,
              time_filter: _TimeFilter, equals: dict, offset: int,
              limit: int, max_scan_rows: int) -> dict:
    rows: list[dict] = []
    positions: list[int] = []
    scanned = 0
    next_position = min(offset, row_count)
    notes: Counter = Counter()
    for position, row in records:
        if position < offset:
            continue
        scanned += 1
        next_position = position + 1
        matches = (time_column is None
                   or time_filter.accepts(row.get(time_column), notes))
        if matches:
            matches = all(_equals(row.get(key), value) for key, value in equals.items())
        if matches:
            projected = {}
            for key in selected:
                if key not in row:
                    notes["ABSENT_FIELD_AS_NULL"] += 1
                projected[key] = _json_value(row.get(key), notes)
            rows.append(projected)
            positions.append(position)
        if len(rows) >= limit or scanned >= max_scan_rows:
            break
    complete = next_position >= row_count
    return {"rows": rows, "row_positions": positions, "scanned_rows": scanned,
            "next_offset": None if complete else next_position,
            "scan_complete": complete, "missingness_notes": _notes(notes)}


def read_rows(stream: BinaryIO, suffix: str, *, file_bytes: int,
              columns: list[str] | None = None, time_column: str | None = None,
              start: str | None = None, end: str | None = None,
              equals: dict | None = None, offset: int = 0, limit: int = 100,
              max_scan_rows: int = 100_000) -> dict:
    """Read a resumable source-row page, with exact names and supplied clocks.

    offset indexes logical records (CSV header/blank lines are not records).
    Date-only bounds include that date in the stored clock's own calendar.
    Timestamp bounds compare instants only with matching aware/naive precision.
    Parsing failures and operational failures are closed codes, never raw errors.
    """
    kind = _format(suffix, file_bytes)
    _integer(offset, 0, 2**63 - 1, "INVALID_OFFSET")
    _integer(limit, 1, MAX_ROWS, "INVALID_LIMIT")
    _integer(max_scan_rows, 1, MAX_SCAN_ROWS, "INVALID_SCAN_LIMIT")
    try:
        with _open_observation(stream, file_bytes):
            if kind == "parquet":
                source = _parquet(stream, file_bytes)
                names = source.schema_arrow.names
                row_count = source.metadata.num_rows
            else:
                source = _TextSource(stream, kind, file_bytes)
                names = source.columns
                row_count = source.row_count
            selected, needed, filters, clock = _query_columns(
                names, columns, time_column, start, end, equals)
            records = (_parquet_rows(source, needed, offset) if kind == "parquet"
                       else enumerate(source.rows()))
            return _evaluate(
                records, row_count=row_count, selected=selected,
                time_column=time_column, time_filter=clock, equals=filters,
                offset=offset, limit=limit, max_scan_rows=max_scan_rows,
            )
    except ReaderError:
        raise
    except OSError:
        raise ReaderError("SOURCE_UNREADABLE") from None
    except Exception:
        raise ReaderError("MALFORMED_SOURCE") from None
