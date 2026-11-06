"""Typed read of retained DGS3MO observations; no collection or publication.

The FRED cache is not an original H.15 acquisition. Its provenance stays FRED,
and publication remains unqualified. A prospective original-Board acquisition
needs its own verified source identity and receipt, never a relabel of this file.
"""
from __future__ import annotations

import hashlib
import io
import math
import re
from datetime import date, datetime, timezone
from numbers import Real
from pathlib import Path

SCHEMA = "treasury.daily_history.v1"
NATIVE_PATH = Path("data/fred/DGS3MO.parquet")
MAX_BYTES = 16 * 1024 * 1024
MAX_CALENDAR_DAYS = 3660


def _date(value) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value)
    if isinstance(value, datetime) and value.tzinfo is None and value == value.replace(
            hour=0, minute=0, second=0, microsecond=0) and getattr(value, "nanosecond", 0) == 0:
        return value.date()
    raise ValueError("invalid_date")


def _envelope(start, end, expected_through, read_at):
    try:
        lo, hi, expected = map(_date, (start, end, expected_through))
        now = read_at if read_at is not None else datetime.now(timezone.utc)
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError
        now = now.astimezone(timezone.utc)
        span = (hi - lo).days + 1
        if not (1 <= span <= MAX_CALENDAR_DAYS and lo <= expected <= hi <= now.date()):
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise ValueError("invalid_window") from None
    result = {
        "schema": SCHEMA, "status": "unavailable", "reason": None,
        "unit": "percent_per_annum", "basis": "investment", "points": [],
        "requested": {"start": lo.isoformat(), "end": hi.isoformat(),
                      "expected_through": expected.isoformat()},
        "coverage": {"observation_count": 0, "requested_calendar_days": span,
                     "first": None, "last": None},
        "clocks": {"read_at": now.isoformat(), "release_at": None,
                   "knowledge_at": None, "vintage_at": None},
        "source": {"source_id": "DGS3MO", "native_alias": "us3m",
                   "origin": "FRED", "native_path": NATIVE_PATH.as_posix(),
                   "last_observation_date": None, "sha256": None,
                   "citation": "Board of Governors of the Federal Reserve System (US), H.15, via FRED",
                   "source_url": "https://fred.stlouisfed.org/series/DGS3MO",
                   "publication_status": "not_qualified"},
    }
    return result, lo, hi, expected, now.date()


def compose_history(frame, *, start, end, expected_through, read_at=None) -> dict:
    """Project actual dated observations; coverage counts no inferred sessions.

    ``expected_through`` is the caller's explicit observation floor, not an
    inferred exchange calendar. Stale points remain dated and marked stale.
    This is an observation-date view, never a point-in-time/vintage assertion.
    """
    out, lo, hi, expected, today = _envelope(start, end, expected_through, read_at)
    if frame is None:
        out["reason"] = "missing"
        return out
    import pandas as pd  # Request-scoped native data work, never API import/auth.

    if not isinstance(frame, pd.DataFrame) or list(frame.columns) != ["us3m"]:
        out["reason"] = "invalid"
        return out
    if frame.empty:
        out["reason"] = "empty"
        return out
    rows = []
    try:
        seen = set()
        for index, value in frame["us3m"].items():
            day = _date(index)
            if day in seen or day > today or isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError
            number = float(value)
            if not math.isfinite(number):
                raise ValueError
            seen.add(day)
            rows.append((day, number))
    except (TypeError, ValueError, OverflowError):
        out["reason"] = "invalid"
        return out
    rows.sort()
    out["source"]["last_observation_date"] = rows[-1][0].isoformat()
    points = [{"date": day.isoformat(), "value": value} for day, value in rows if lo <= day <= hi]
    if not points:
        out["reason"] = "no_coverage"
        return out
    out["points"] = points
    out["coverage"].update(observation_count=len(points), first=points[0]["date"], last=points[-1]["date"])
    stale = points[-1]["date"] < expected.isoformat()
    out.update(status="stale" if stale else "read", reason="before_expected_through" if stale else None)
    return out


def read_history(root: Path, *, start, end, expected_through, read_at=None) -> dict:
    """One bounded immutable-byte read; fixed path, no store helper/write/cache."""
    out, *_ = _envelope(start, end, expected_through, read_at)
    try:
        with (Path(root) / NATIVE_PATH).open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            out["reason"] = "oversized"
            return out
        digest = hashlib.sha256(content).hexdigest()
        import pandas as pd  # Only after the authorized, bounded native read.

        frame = pd.read_parquet(io.BytesIO(content))
    except FileNotFoundError:
        out["reason"] = "missing"
        return out
    except Exception:  # Malformed native input is unavailable, never exception text.
        out["reason"] = "unreadable"
        return out
    result = compose_history(frame, start=start, end=end, expected_through=expected_through,
                             read_at=datetime.fromisoformat(out["clocks"]["read_at"]))
    result["source"]["sha256"] = digest
    return result
