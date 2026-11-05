"""Compact per-name evaluator state for the live Entry Radar pack.

The live evaluator answers one question per name per pass: "what do the
indicators read if today's bar closes at this price?"  Answering it from the
frozen price history means carrying every name's whole history in memory.  This
module writes, once per pack, the small amount of state that question actually
needs, so an evaluator can answer it for a whole market without the histories:

* the StochRSI append state and the RSI-MACD histogram append state, exactly as
  :mod:`engine.entry_radar.indicator_core` builds them from the confirmed closes;
* the tail of the confirmed closes (``TAIL_ROWS`` rows, reaching further back
  until it holds ``TAIL_MIN_FINITE`` finite closes or the history ends), kept
  as **display context only** — the last confirmed closes for a glance surface.
  It is never an input to any indicator value or any decision.  A 252-row tail
  cannot reproduce the canonical SMA-seeded Wilder-RMA / EMA recursions within
  the live oracle tie band (measured tail-recompute error ≈1e-3, 7.6e-4 to 8.05e-4
  off vs 1e-14 for the append
  states here).  A decision whose |margin| is at or below the tie band must be
  settled from the pack's frozen substrate frame through the pack reader, never
  from this file (see :data:`CANONICAL_FALLBACK`).

Both append states of a name are built by ONE function from ONE closes series,
so they cannot be paired with each other's history.  A name whose StochRSI state
is unavailable stores no histogram state either: the histogram append needs the
StochRSI state, so a lone histogram state could never be used.

The file is bound to its pack only through the pack manifest (its sha256 and
byte count).  :func:`load_compact` refuses a file that is absent, that does not
hash to the manifest's value, or whose contents break the layout — it never
returns a partial or guessed state.

This module computes no signal and reads no price store.  It imports the
indicator core and nothing else from the Radar.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from engine import canon
from engine.entry_radar import indicator_core as ic

#: The file name inside a pack's session directory.
COMPACT_NAME = "compact.parquet"

#: The layout identity, stored in the file's own metadata and in the manifest.
SCHEMA_COMPACT = "mastermind.entry_radar_pack_compact.v1"

#: Contract: ``tail_close`` is display context only, not a canonical recompute input.
TAIL_CLOSE_PURPOSE = "display_only"

#: Where near-boundary decisions must be settled when this file is not enough.
CANONICAL_FALLBACK = "pack_substrate_frame"

#: Confirmed closes kept per name: the last ``TAIL_ROWS`` rows, reaching further
#: back until ``TAIL_MIN_FINITE`` of them are finite or the history ends.
TAIL_ROWS = 252
TAIL_MIN_FINITE = 121

_FLOATS = pa.list_(pa.float64())

COMPACT_SCHEMA = pa.schema([
    pa.field("ticker", pa.string(), nullable=False),
    pa.field("state_through", pa.date32(), nullable=False),
    pa.field("n_rows", pa.int32(), nullable=False),
    pa.field("price_basis", pa.string(), nullable=False),
    pa.field("kd_ok", pa.bool_(), nullable=False),
    pa.field("kd_last_close", pa.float64()),
    pa.field("kd_up_prev", pa.float64()),
    pa.field("kd_dn_prev", pa.float64()),
    pa.field("kd_rsi_tail", _FLOATS),
    pa.field("kd_rawk_tail", _FLOATS),
    pa.field("kd_k_tail", _FLOATS),
    pa.field("hist_ok", pa.bool_(), nullable=False),
    pa.field("hist_fast", pa.float64()),
    pa.field("hist_base", pa.float64()),
    pa.field("hist_sig", pa.float64()),
    pa.field("tail_close", _FLOATS, nullable=False),
], metadata={
    b"schema": SCHEMA_COMPACT.encode(),
    b"tail_close_purpose": TAIL_CLOSE_PURPOSE.encode(),
    b"canonical_fallback": CANONICAL_FALLBACK.encode(),
})

_KD_SCALARS = ("kd_last_close", "kd_up_prev", "kd_dn_prev")
_KD_TAILS = (("kd_rsi_tail", canon.STOCH_LEN - 1), ("kd_rawk_tail", canon.SMOOTH_K - 1),
             ("kd_k_tail", canon.SMOOTH_D - 1))
_HIST_SCALARS = ("hist_fast", "hist_base", "hist_sig")


class CompactStateError(ValueError):
    """The compact state file cannot be written or trusted.  ``reason`` is a stable code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class CompactName:
    """One name's compact state.  Everything here is knowable at the pack's ``as_of``."""

    ticker: str
    state_through: date
    n_rows: int
    price_basis: str
    kd_state: ic.StochRsiAppendState | None
    hist_state: ic.RsiMacdHistAppendState | None
    #: Display context only (last confirmed closes); never an indicator or decision input.
    tail_close: tuple[float, ...]


def confirmed_closes(frame: pd.DataFrame) -> pd.Series:
    """The closes series every state in this module is built from."""
    return pd.to_numeric(frame["close"], errors="coerce").astype("float64")


def _tail_close(values: np.ndarray) -> tuple[float, ...]:
    start = max(0, len(values) - TAIL_ROWS)
    finite = int(np.isfinite(values[start:]).sum())
    while start > 0 and finite < TAIL_MIN_FINITE:
        start -= 1
        if np.isfinite(values[start]):
            finite += 1
    return tuple(float(v) for v in values[start:])


def compact_state_row(ticker: str, frame: pd.DataFrame, *, price_basis: str) -> CompactName:
    """Build one name's compact state from its frozen frame."""
    if frame is None or len(frame) == 0:
        raise CompactStateError("compact_empty_frame", f"{ticker}: no confirmed rows")
    if "close" not in frame.columns:
        raise CompactStateError("compact_schema", f"{ticker}: frame has no close column")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise CompactStateError("compact_schema", f"{ticker}: frame index is not DatetimeIndex")
    if not frame.index.is_monotonic_increasing or not frame.index.is_unique:
        raise CompactStateError("compact_schema", f"{ticker}: frame index is not strictly increasing")
    closes = confirmed_closes(frame)
    kd_state = ic.stoch_rsi_append_state(closes)
    hist_state = ic.rsi_macd_hist_append_state(closes) if kd_state is not None else None
    through = pd.Timestamp(pd.DatetimeIndex(frame.index)[-1]).date()
    return CompactName(
        ticker=str(ticker), state_through=through, n_rows=int(len(closes)),
        price_basis=str(price_basis), kd_state=kd_state, hist_state=hist_state,
        tail_close=_tail_close(closes.to_numpy(dtype="float64")))


class CompactStateSink:
    """Collect compact rows one name at a time; a ticker may be added once."""

    def __init__(self) -> None:
        self._rows: dict[str, CompactName] = {}

    def add(self, ticker: str, frame: pd.DataFrame, *, price_basis: str) -> CompactName:
        key = str(ticker)
        if key in self._rows:
            raise CompactStateError("compact_duplicate_ticker", key)
        row = compact_state_row(key, frame, price_basis=price_basis)
        self._rows[key] = row
        return row

    def rows(self) -> list[CompactName]:
        return [self._rows[key] for key in sorted(self._rows)]


def _check(row: CompactName) -> None:
    """Refuse a row that breaks the layout's own rules."""
    who = row.ticker
    if not who:
        raise CompactStateError("compact_schema", "empty ticker")
    if row.n_rows < 1:
        raise CompactStateError("compact_schema", f"{who}: n_rows {row.n_rows}")
    tail = len(row.tail_close)
    if tail < 1 or tail > row.n_rows or (tail < TAIL_ROWS and tail != row.n_rows):
        raise CompactStateError(
            "compact_schema", f"{who}: tail_close holds {tail} of {row.n_rows} rows")
    if row.hist_state is not None and row.kd_state is None:
        raise CompactStateError(
            "compact_schema", f"{who}: histogram state without StochRSI state")
    if row.kd_state is not None:
        for name, want in _KD_TAILS:
            got = len(getattr(row.kd_state, name[len("kd_"):]))
            if got != want:
                raise CompactStateError(
                    "compact_schema", f"{who}: {name} holds {got} values, expected {want}")


def _table(rows: list[CompactName]) -> pa.Table:
    columns: dict[str, list[Any]] = {field.name: [] for field in COMPACT_SCHEMA}
    for row in rows:
        kd, hist = row.kd_state, row.hist_state
        columns["ticker"].append(row.ticker)
        columns["state_through"].append(row.state_through)
        columns["n_rows"].append(row.n_rows)
        columns["price_basis"].append(row.price_basis)
        columns["kd_ok"].append(kd is not None)
        columns["kd_last_close"].append(None if kd is None else kd.last_close)
        columns["kd_up_prev"].append(None if kd is None else kd.up_prev)
        columns["kd_dn_prev"].append(None if kd is None else kd.dn_prev)
        columns["kd_rsi_tail"].append(None if kd is None else list(kd.rsi_tail))
        columns["kd_rawk_tail"].append(None if kd is None else list(kd.rawk_tail))
        columns["kd_k_tail"].append(None if kd is None else list(kd.k_tail))
        columns["hist_ok"].append(hist is not None)
        columns["hist_fast"].append(None if hist is None else hist.fast)
        columns["hist_base"].append(None if hist is None else hist.base)
        columns["hist_sig"].append(None if hist is None else hist.sig)
        columns["tail_close"].append(list(row.tail_close))
    arrays = [pa.array(columns[field.name], type=field.type) for field in COMPACT_SCHEMA]
    return pa.Table.from_arrays(arrays, schema=COMPACT_SCHEMA)


def write_compact(path: Path | str, rows: Iterable[CompactName]) -> dict[str, Any]:
    """Write the compact state file and return its manifest entry.

    Rows are written in ticker order whatever order they arrive in, so the same
    rows produce the same bytes under one pyarrow version (the file footer names
    the writer, so the bytes are not promised to match across versions; the
    manifest's sha256 binds the bytes that were actually written).  The write is
    atomic: a reader sees the old file or the new one, never a partial one.
    """
    ordered = sorted(rows, key=lambda row: row.ticker)
    seen: set[str] = set()
    for row in ordered:
        if row.ticker in seen:
            raise CompactStateError("compact_duplicate_ticker", row.ticker)
        seen.add(row.ticker)
        _check(row)
    target = Path(path)
    # A name of its own, so two writers never share a scratch file.
    scratch = target.with_name(f"{target.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        pq.write_table(_table(ordered), scratch, compression="zstd",
                       use_dictionary=False, write_statistics=False)
        data = scratch.read_bytes()
        with open(scratch, "rb") as written:
            os.fsync(written.fileno())
        os.replace(scratch, target)
    finally:
        scratch.unlink(missing_ok=True)
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "rows": len(ordered), "schema": SCHEMA_COMPACT}


def _nulls(cells: dict[str, Any], names: Iterable[str]) -> list[str]:
    return [name for name in names if cells[name] is None]


def _row(cells: dict[str, Any]) -> CompactName:
    who = cells["ticker"]
    kd_names = _KD_SCALARS + tuple(name for name, _ in _KD_TAILS)
    kd_state = hist_state = None
    if cells["kd_ok"]:
        if _nulls(cells, kd_names):
            raise CompactStateError("compact_schema", f"{who}: StochRSI state has empty cells")
        for name, _ in _KD_TAILS:
            if any(value is None for value in cells[name]):
                raise CompactStateError("compact_schema", f"{who}: {name} has an empty value")
        kd_state = ic.StochRsiAppendState(
            last_close=cells["kd_last_close"], up_prev=cells["kd_up_prev"],
            dn_prev=cells["kd_dn_prev"], rsi_tail=tuple(cells["kd_rsi_tail"]),
            rawk_tail=tuple(cells["kd_rawk_tail"]), k_tail=tuple(cells["kd_k_tail"]))
    elif len(_nulls(cells, kd_names)) != len(kd_names):
        raise CompactStateError("compact_schema", f"{who}: StochRSI cells without kd_ok")
    if cells["hist_ok"]:
        if _nulls(cells, _HIST_SCALARS):
            raise CompactStateError("compact_schema", f"{who}: histogram state has empty cells")
        hist_state = ic.RsiMacdHistAppendState(
            fast=cells["hist_fast"], base=cells["hist_base"], sig=cells["hist_sig"])
    elif len(_nulls(cells, _HIST_SCALARS)) != len(_HIST_SCALARS):
        raise CompactStateError("compact_schema", f"{who}: histogram cells without hist_ok")
    if any(value is None for value in cells["tail_close"]):
        raise CompactStateError("compact_schema", f"{who}: tail_close has an empty value")
    row = CompactName(
        ticker=who, state_through=cells["state_through"], n_rows=cells["n_rows"],
        price_basis=cells["price_basis"], kd_state=kd_state, hist_state=hist_state,
        tail_close=tuple(cells["tail_close"]))
    _check(row)
    return row


def load_compact(path: Path | str, *, expected_sha256: str) -> dict[str, CompactName]:
    """Read the compact state file a pack manifest names, or refuse.

    ``expected_sha256`` is the manifest's value.  Refusals carry ``reason``
    ``compact_absent`` (no readable file), ``compact_hash_mismatch`` (the bytes
    are not the ones the manifest names) or ``compact_schema`` (the bytes are the
    named ones but the contents break the layout).
    """
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise CompactStateError("compact_absent", str(exc)) from exc
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise CompactStateError("compact_hash_mismatch", str(path))
    try:
        table = pq.read_table(pa.BufferReader(data))
    except Exception as exc:  # noqa: BLE001 — any unreadable layout is one refusal
        raise CompactStateError("compact_schema", f"unreadable: {exc}") from exc
    meta = table.schema.metadata or {}
    if not table.schema.equals(COMPACT_SCHEMA, check_metadata=False) or \
            meta.get(b"schema") != SCHEMA_COMPACT.encode():
        raise CompactStateError("compact_schema", "columns differ from the published layout")
    if meta.get(b"tail_close_purpose") != TAIL_CLOSE_PURPOSE.encode() or \
            meta.get(b"canonical_fallback") != CANONICAL_FALLBACK.encode():
        raise CompactStateError("compact_schema", "contract metadata differs")
    out: dict[str, CompactName] = {}
    prev_ticker: str | None = None
    for cells in table.to_pylist():
        row = _row(cells)
        if row.ticker in out:
            raise CompactStateError("compact_schema", f"{row.ticker}: listed twice")
        if prev_ticker is not None and row.ticker <= prev_ticker:
            raise CompactStateError("compact_schema", "rows not sorted by ticker")
        prev_ticker = row.ticker
        out[row.ticker] = row
    return out
