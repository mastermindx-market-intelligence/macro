"""Read the existing raw daily store for the per-stock liquidity projection.

This reader never restores a store, fetches a reference or writes an artifact.
The stock-library writer owns publication. Missing raw bars or currency-window
evidence remain unknown; the adjusted legacy chip is not a fallback source.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from engine.liquidity_profile import project
from engine.liquidity_source_availability import coverage_clock, source_expected_session
from lib import nyse_calendar
from lib.massive_ticker import artifact_relative_path

MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_SOURCE_ROWS = 50_000
MAX_DECODED_BYTES = 16 * 1024 * 1024


def read_profile(ticker: str, *, data_root: Path, recorded_at: datetime,
                 currency_evidence: dict | None = None) -> dict:
    """Return one typed projection from native producer inputs, with no effects.

    ``currency_evidence`` is an explicit qualified input, not inferred from a
    ticker, country, profile currency or a current-only reference. The
    stock-library caller adopts only the retained, exact dated-session receipt
    under stock_currency; missing evidence remains unknown.
    """
    try:
        expected = source_expected_session(recorded_at)
    except ValueError:
        return project(None, ticker=ticker, expected_session=None,
                       recorded_at=recorded_at, ingested_at=None,
                       source_sha256=None, currency_evidence=currency_evidence)
    kwargs = dict(ticker=ticker, expected_session=expected,
                  recorded_at=recorded_at, ingested_at=None,
                  source_sha256=None, currency_evidence=currency_evidence)
    if not isinstance(ticker, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^=-]{0,31}", ticker):
        result = project(None, **kwargs)
        result.update(status="READ_NO_COVERAGE", reason="IDENTITY_NOT_COVERED")
        return result
    root = Path(data_root) / "massive_stock_day"
    path = root / artifact_relative_path(ticker)
    if path.is_symlink():
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_NOT_REGULAR")
        return result
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
    except FileNotFoundError:
        return project(None, **kwargs)
    except OSError:
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_UNREADABLE")
        return result
    if len(raw) > MAX_SOURCE_BYTES:
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_OVER_BOUND")
        return result
    kwargs["source_sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        parquet = pq.ParquetFile(io.BytesIO(raw))
        metadata = parquet.metadata
        decoded_bytes = sum(
            metadata.row_group(group).column(column).total_uncompressed_size
            for group in range(metadata.num_row_groups)
            for column in range(metadata.num_columns)
        )
        if metadata.num_rows > MAX_SOURCE_ROWS or decoded_bytes > MAX_DECODED_BYTES:
            result = project(None, **kwargs)
            result.update(status="READ_UNAVAILABLE", reason="SOURCE_OVER_BOUND")
            return result
        frame = pd.read_parquet(io.BytesIO(raw), columns=["close", "volume"])
    except Exception:  # malformed file is an unavailable read, never zero
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_UNREADABLE")
        return result
    # Use the observed final bar only when it meets the provider's availability
    # floor and names a completed market session. A normal T+1 gap is explicit;
    # the pure projection still rejects future/malformed/gapped source rows.
    market_completed = nyse_calendar.expected_last_session(recorded_at)
    if isinstance(frame.index, pd.DatetimeIndex) and len(frame.index):
        final = frame.index[-1].date()
        if expected <= final <= market_completed:
            kwargs["expected_session"] = final
    if currency_evidence is None:
        receipt_path = Path(data_root) / "stock_currency" / artifact_relative_path(ticker).with_suffix(".json")
        try:
            if not receipt_path.is_symlink():
                with receipt_path.open("rb") as stream:
                    receipt_bytes = stream.read(3 * 1024 * 1024 + 1)
                if len(receipt_bytes) <= 3 * 1024 * 1024:
                    kwargs["currency_evidence"] = json.loads(receipt_bytes)
        except (OSError, ValueError, TypeError):
            pass
    # A store manifest's updated_at is not a ticker's ingestion time. Retain it
    # as a separately named observation rather than promoting it to known_at.
    store_updated_at = None
    try:
        with (root / "_manifest.json").open("rb") as stream:
            manifest_bytes = stream.read(8193)
        if len(manifest_bytes) <= 8192:
            value = json.loads(manifest_bytes).get("updated_at")
            stamp = datetime.fromisoformat(value) if isinstance(value, str) else None
            if stamp is not None and stamp.utcoffset() is not None and stamp <= recorded_at:
                store_updated_at = stamp.isoformat()
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    result = project(frame, **kwargs)
    result["store_updated_at"] = store_updated_at
    result["availability"] = coverage_clock(recorded_at)
    # This producer's parser fills a missing volume with zero. Its retained
    # parquet cannot distinguish that from genuine zero activity, so a window
    # containing zero cannot earn a qualified full-coverage turnover metric.
    if frame["volume"].tail(20).eq(0).any():
        result.update(status="READ_NO_COVERAGE", reason="ZERO_VOLUME_SOURCE_AMBIGUOUS",
                      metrics=None, sample_n=None, thinly_traded=None)
    return result


def write_record(path: Path, rec: dict, *, data_root: Path,
                 recorded_at: datetime) -> None:
    """Existing stock-library writer's one-record seam, with one added field.

    The caller supplies its existing output path; this module never selects a
    publication destination or writes any index, board, store or user state.
    """
    rec["liquidity_profile"] = read_profile(
        rec.get("ticker", ""), data_root=data_root, recorded_at=recorded_at)
    path.write_text(json.dumps(rec, default=str))
