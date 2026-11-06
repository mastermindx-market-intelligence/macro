"""Disk-backed substrate spool for Entry Radar live pack builds (P-SCALE-2)."""
from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from engine.entry_radar.live_pack import (
    LivePackError,
    PackName,
    _SUBSTRATE_COLUMNS,
    _refuse_substrate_index_not_normalized,
    substrate_fingerprint,
)

SIDECAR_SCHEMA = "entry_radar.substrate_spool/v1"
_FLAT_COLUMNS: tuple[str, ...] = ("ticker", "session", "high", "low", "close")

_PARQUET_SCHEMA = pa.schema(
    [
        ("ticker", pa.string()),
        ("session", pa.date32()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
    ]
)


def _validate_frozen_frame(frozen: pd.DataFrame, ticker: str) -> None:
    if list(frozen.columns) != list(_SUBSTRATE_COLUMNS):
        raise LivePackError(f"spool_frame_not_frozen:{ticker}")
    try:
        _refuse_substrate_index_not_normalized(frozen, ticker=ticker)
    except LivePackError:
        raise LivePackError(f"spool_frame_not_frozen:{ticker}") from None


def _frame_to_table(ticker: str, frozen: pd.DataFrame) -> pa.Table:
    index = pd.DatetimeIndex(frozen.index)
    data: dict[str, Any] = {
        "ticker": [ticker] * len(frozen),
        "session": [ts.date() for ts in index],
    }
    for column in _SUBSTRATE_COLUMNS:
        data[column] = frozen[column].astype(np.float64).to_numpy()
    return pa.Table.from_pydict(data, schema=_PARQUET_SCHEMA)


def _table_to_frame(table: pa.Table) -> pd.DataFrame:
    pdf = table.to_pandas()
    sessions = pd.to_datetime(pdf["session"]).astype("datetime64[s]")
    frame = pdf.loc[:, list(_SUBSTRATE_COLUMNS)].astype(np.float64)
    index = pd.DatetimeIndex(sessions, freq=None)
    index.name = None
    frame.index = index
    return frame


def spool_fingerprints(path: Path | str) -> dict[str, str]:
    return dict(load_sidecar(path)["fingerprints"])


class SpoolSubstrate(Mapping[str, pd.DataFrame]):
    """Read-only lazy mapping over a finished substrate spool on disk.

    Immutable spool bytes; single-process reader. Not safe against concurrent
    writers mutating the spool path while this mapping is in use.
    """

    def __init__(self, path: Path | str) -> None:
        sidecar = load_sidecar(path)
        self.path = Path(path)
        self._row_groups: dict[str, int] = dict(sidecar["row_groups"])
        self.fingerprints: dict[str, str] = dict(sidecar["fingerprints"])
        self._parquet: pq.ParquetFile | None = None
        try:
            n_groups = pq.ParquetFile(self.path).num_row_groups
        except Exception as exc:  # noqa: BLE001 — malformed parquet is a sidecar read failure
            raise LivePackError(f"spool_sidecar_malformed: parquet unreadable: {exc}") from exc
        for ticker, idx in self._row_groups.items():
            if idx >= n_groups:
                raise LivePackError(
                    f"spool_sidecar_malformed: row_groups[{ticker!r}] out of range")

    def _open_parquet(self) -> pq.ParquetFile:
        if self._parquet is None:
            self._parquet = pq.ParquetFile(self.path)
        return self._parquet

    def __len__(self) -> int:
        return len(self._row_groups)

    def __iter__(self) -> Iterator[str]:
        return iter(self._row_groups)

    def __contains__(self, key: object) -> bool:
        return key in self._row_groups

    def __getitem__(self, ticker: str) -> pd.DataFrame:
        if ticker not in self._row_groups:
            raise KeyError(ticker)
        try:
            table = self._open_parquet().read_row_group(self._row_groups[ticker])
        except Exception as exc:  # noqa: BLE001
            raise LivePackError(f"spool_sidecar_malformed: row_group read failed: {exc}") from exc
        return _table_to_frame(table)

    def __repr__(self) -> str:
        return f"SpoolSubstrate(path={self.path!r}, n_names={len(self)})"

    def close(self) -> None:
        if self._parquet is not None:
            self._parquet.close()
            self._parquet = None


class ParquetSpoolSink:
    """Write each frozen substrate frame to one parquet row group; hold no frames."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.fingerprints: dict[str, str] = {}
        self.row_groups: dict[str, int] = {}
        self._writer: pq.ParquetWriter | None = None
        self._finished = False
        self._next_row_group = 0

    def add(self, row: PackName, frozen: pd.DataFrame, *, next_session: date) -> None:
        if self._finished:
            raise LivePackError("spool_closed")
        ticker = row.ticker
        if ticker in self.fingerprints:
            raise LivePackError(f"spool_duplicate_ticker:{ticker}")
        _validate_frozen_frame(frozen, ticker)
        self.fingerprints[ticker] = substrate_fingerprint(frozen)
        self.row_groups[ticker] = self._next_row_group
        self._next_row_group += 1
        table = _frame_to_table(ticker, frozen)
        if self._writer is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._writer = pq.ParquetWriter(self.path, _PARQUET_SCHEMA)
        self._writer.write_table(table)

    def finish(self) -> SpoolSubstrate:
        if self._finished:
            raise LivePackError("spool_closed")
        self._finished = True
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            writer = pq.ParquetWriter(self.path, _PARQUET_SCHEMA)
            writer.close()
        sidecar_path = Path(f"{self.path}.sidecar.json")
        payload = {
            "schema": SIDECAR_SCHEMA,
            "fingerprints": self.fingerprints,
            "row_groups": self.row_groups,
            "n_names": len(self.fingerprints),
            "columns": list(_FLAT_COLUMNS),
        }
        sidecar_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return SpoolSubstrate(self.path)


def load_sidecar(path: Path | str) -> dict[str, Any]:
    sidecar_path = Path(f"{path}.sidecar.json")
    if not sidecar_path.is_file():
        raise LivePackError("spool_sidecar_missing")
    try:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LivePackError(f"spool_sidecar_malformed: invalid json: {exc}") from exc
    if data.get("schema") != SIDECAR_SCHEMA:
        raise LivePackError("spool_sidecar_schema")
    row_groups = data.get("row_groups")
    if not isinstance(row_groups, dict):
        raise LivePackError("spool_sidecar_malformed: row_groups missing or not a dict")
    for ticker, idx in row_groups.items():
        if isinstance(idx, bool) or not isinstance(idx, int):
            raise LivePackError(f"spool_sidecar_malformed: row_groups[{ticker!r}] not an int")
        if idx < 0:
            raise LivePackError(f"spool_sidecar_malformed: row_groups[{ticker!r}] negative")
    data["row_groups"] = row_groups
    return data


def iter_spool(path: Path | str) -> Iterator[tuple[str, pd.DataFrame]]:
    path = Path(path)
    load_sidecar(path)
    parquet = pq.ParquetFile(path)
    for row_group in range(parquet.num_row_groups):
        table = parquet.read_row_group(row_group)
        if table.num_rows == 0:
            continue
        ticker = table.column("ticker")[0].as_py()
        yield ticker, _table_to_frame(table)


def read_spool_frame(path: Path | str, ticker: str) -> pd.DataFrame | None:
    sidecar = load_sidecar(path)
    row_group = sidecar["row_groups"].get(ticker)
    if row_group is None:
        return None
    parquet = pq.ParquetFile(path)
    table = parquet.read_row_group(row_group)
    return _table_to_frame(table)


def verify_spool(path: Path | str, expected: Mapping[str, str]) -> None:
    recomputed: dict[str, str] = {}
    for ticker, frame in iter_spool(path):
        recomputed[ticker] = substrate_fingerprint(frame)
    got = set(recomputed)
    want = set(expected)
    if got != want:
        missing = sorted(want - got)
        extra = sorted(got - want)
        raise LivePackError(f"spool_key_mismatch: missing={missing} extra={extra}")
    for ticker, fingerprint in expected.items():
        if recomputed[ticker] != fingerprint:
            raise LivePackError(f"spool_fingerprint_mismatch:{ticker}")
