"""Read-only adapter from the existing Yahoo store to the Risk Envelope.

No collection, refresh, writes, FX inference or historical-availability assertion.
Only US-listed proxies share this daily session comparison. The strict event-time
observation core is separate and is not fed invented quote/availability clocks.
"""
from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from engine.multi_asset_context import instant, stamp
from engine.multi_asset_daily import UNIVERSE, compose_daily_context
from lib.nyse_calendar import expected_last_session, is_session, session_n_back

_MAX_SOURCE_BYTES = 8 * 1024 * 1024


def _read_source(root: Path, ticker: str) -> dict[str, Any]:
    path = root / "data" / "yahoo" / (ticker + ".parquet")
    result: dict[str, Any] = {"instrument_id": ticker}
    try:
        if path.is_symlink():
            return {**result, "read_error": "source_symlink_refused"}
        before = path.stat()
        if before.st_size > _MAX_SOURCE_BYTES:
            return {**result, "read_error": "source_too_large"}
        payload = path.read_bytes()
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            return {**result, "read_error": "source_changed_during_capture"}
        result["source_digest"] = hashlib.sha256(payload).hexdigest()
        frame = pd.read_parquet(io.BytesIO(payload), columns=["close"])
        index = frame.index
        if (frame.empty or not isinstance(index, pd.DatetimeIndex) or index.tz is not None
                or index.hasnans or not index.is_unique or not index.is_monotonic_increasing
                or not index.equals(index.normalize())
                or getattr(frame["close"].dtype, "kind", "") not in "iuf"):
            return {**result, "read_error": "source_shape_invalid"}
        # Prices are internal arithmetic inputs; the published context contains returns only.
        prices = {day.date().isoformat(): float(value) for day, value in frame["close"].items()}
        return {**result, "prices": prices, "last_source_session": index[-1].date().isoformat(),
                "currency": "USD", "listing_market": "US", "return_basis": "total_return"}
    except FileNotFoundError:
        return {**result, "read_error": "source_missing"}
    except (OSError, ValueError, KeyError, TypeError):
        return {**result, "read_error": "source_unreadable"}


def build_multi_asset_context(root: Path, *, now: datetime | None = None,
                              horizon_sessions: int = 5) -> dict[str, Any]:
    """Capture current cache bytes; older snapshots remain visibly STALE, not live."""
    if now is not None and (now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("aware_capture_clock_required")
    if not isinstance(horizon_sessions, int) or isinstance(horizon_sessions, bool) or not 1 <= horizon_sessions <= 252:
        raise ValueError("invalid_horizon_sessions")
    sources = [_read_source(root, ticker) for ticker, *_ in UNIVERSE]
    clock = now if now is not None else datetime.now(timezone.utc)
    captured = instant(stamp(clock))
    expected = expected_last_session(captured)
    benchmark = next(s for s in sources if s["instrument_id"] == "SPY")
    # Discard unsettled rows explicitly; do not backfill another asset to fit the window.
    eligible = sorted(day for day in benchmark.get("prices", {})
                      if day <= expected.isoformat() and is_session(datetime.fromisoformat(day).date()))
    end = datetime.fromisoformat(eligible[-1]).date() if eligible else expected
    start = session_n_back(end, horizon_sessions)
    if start is None:
        raise ValueError("session_calendar_unavailable")
    return compose_daily_context(sources, captured_at=stamp(captured),
                                 expected_session=expected.isoformat(), start_session=start.isoformat(),
                                 end_session=end.isoformat(), horizon_sessions=horizon_sessions)
