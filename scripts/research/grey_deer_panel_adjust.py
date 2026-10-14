"""Panel input preparation for Grey Deer pullback stage-1b (seat amendment A1).

D14 applies the pinned split table. D15 intersects session dates against the
pinned calendar exclusion. Both run on identity frames
(date, open, high, low, close, volume, transactions) before any target, label,
feature, fit, or outcome exists. This module does not read or write files and
does not fetch prices.

A session is the calendar date of a row. Rows are ordered by that date before a
previous session is chosen. Missing sessions are never forward-filled.

Dividends are not an identity column. This adjustment does not change them;
dividend handling stays unadjusted and is only disclosed here.

A data problem returns ``AdjustResult(status="BLOCKED", ...)``. A wrong type
or an ill-formed pin raises ``TypeError`` or ``ValueError``.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

# Stage-1 identity columns (grey_deer_pullback_stage1.IDENTITY_COLUMNS).
# Duplicated so this module does not import the stage-1 runner.
_IDENTITY_COLUMNS = ("date", "open", "high", "low", "close", "volume", "transactions")
_PRICE_COLUMNS = ("open", "high", "low", "close")

PINNED_SPLITS: dict[tuple[str, str], float] = {
    ("XLB", "2025-12-05"): 2.0,
    ("XLE", "2025-12-05"): 2.0,
    ("XLK", "2025-12-05"): 2.0,
    ("XLU", "2025-12-05"): 2.0,
    ("XLY", "2025-12-05"): 2.0,
}

SPLIT_SOURCES = (
    "https://www.businesswire.com/news/home/20251120957218/en/State-Street-Investment-Management-Announces-Share-Splits-for-Five-Select-Sector-SPDR-ETFs",
    "https://www.ssga.com/library-content/products/fund-docs/etfs/us/information-schedules/select-sector-spdr-fund-share-splits-faq.pdf",
)

PINNED_CALENDAR_EXCLUSIONS = frozenset({"2026-08-18"})
SPLIT_CONFIRM_TOL = 0.10
BREAK_LOG_THRESHOLD = math.log(1.25)

Status = Literal["OK", "BLOCKED"]
Reason = Literal["SPLIT_TABLE_MISMATCH", "SPLIT_DISCONTINUITY", "CALENDAR_MISALIGNED"]


@dataclass(frozen=True, slots=True)
class AdjustResult:
    """One input-preparation outcome.

    ``frames``, ``calendar``, and ``confirmations`` are set only when this call
    produced them and ``status`` is ``OK``. A refusal uses ``None`` so a partial
    panel cannot be read as an input. ``detail`` is JSON-serialisable.

    ``SPLIT_TABLE_MISMATCH`` detail: ``mismatches`` (``ticker``, ``date``,
    ``ratio``, ``why``; ``observed`` rounded to 6 decimal places when a close
    ratio was computed), ``skipped_pins``, and ``why`` when every mismatch
    shares one reason.

    ``CALENDAR_MISALIGNED`` detail: ``unexpected``, ``pinned_absent``,
    ``missing_by_ticker``.

    ``SPLIT_DISCONTINUITY`` detail: ``breaks``, a list of ``{ticker, date}``.
    """

    status: Status
    reason: Reason | None
    detail: dict
    frames: dict[str, pd.DataFrame] | None
    calendar: list[str] | None
    confirmations: list[dict] | None

    def __post_init__(self) -> None:
        if self.status not in ("OK", "BLOCKED"):
            raise ValueError(f"status must be OK or BLOCKED, got {self.status!r}")
        if self.reason not in (None, "SPLIT_TABLE_MISMATCH", "SPLIT_DISCONTINUITY", "CALENDAR_MISALIGNED"):
            raise ValueError(f"unknown reason {self.reason!r}")
        if self.status == "OK" and self.reason is not None:
            raise ValueError("OK result cannot carry a reason")
        if self.status == "BLOCKED" and self.reason is None:
            raise ValueError("BLOCKED result requires a reason")
        if not isinstance(self.detail, dict):
            raise TypeError("detail must be a dict")


def apply_pinned_splits(
    frames: dict[str, pd.DataFrame],
    splits: dict[tuple[str, str], float] = PINNED_SPLITS,
    tol: float = SPLIT_CONFIRM_TOL,
) -> AdjustResult:
    """Confirm pinned splits and back-adjust rows strictly before each effective date.

    ``observed = close[previous session] / close[effective session]`` must lie in
    ``[(1 - tol) * ratio, (1 + tol) * ratio]``. Several splits on one ticker
    multiply in effective-date order. The caller's frames are not modified.
    Pins whose ticker is absent from ``frames`` are skipped, not refused.
    """
    _require_frames(frames)
    pins = _require_splits(splits)
    tolerance = _require_tol(tol)
    working = {ticker: _canonicalize(frame) for ticker, frame in frames.items()}

    mismatches: list[dict] = []
    skipped: list[dict] = []
    confirmed: list[tuple[str, str, float, float]] = []
    for ticker, effective, ratio in pins:
        if ticker not in working:
            skipped.append({"ticker": ticker, "date": effective, "ratio": ratio})
            continue
        problem, observed = _confirm_one(working[ticker], effective, ratio, tolerance)
        if problem is not None:
            entry = {"ticker": ticker, "date": effective, "ratio": ratio, "why": problem}
            if observed is not None:
                entry["observed"] = _round6(observed)
            mismatches.append(entry)
            continue
        assert observed is not None
        confirmed.append((ticker, effective, ratio, observed))

    detail: dict = {"skipped_pins": skipped}
    if mismatches:
        detail["mismatches"] = mismatches
        whys = {entry["why"] for entry in mismatches}
        if len(whys) == 1:
            detail["why"] = mismatches[0]["why"]
        return _blocked("SPLIT_TABLE_MISMATCH", detail)

    for ticker, effective, ratio, _observed in confirmed:
        _adjust_before(working[ticker], effective, ratio)

    confirmations = [
        {"ticker": ticker, "date": effective, "ratio": ratio, "observed": _round6(observed)}
        for ticker, effective, ratio, observed in confirmed
    ]
    return AdjustResult(
        status="OK",
        reason=None,
        detail=detail,
        frames=working,
        calendar=None,
        confirmations=confirmations,
    )


def detect_split_breaks(frame: pd.DataFrame, threshold: float = BREAK_LOG_THRESHOLD) -> list[str]:
    """Dates ``t`` where ``|log(close_t / close_{t-1})| > threshold``, in date order.

    Input-quality check only (D5). A non-positive or non-finite close is reported
    as a break. Nothing is adjusted and an unpinned split is never inferred.
    """
    limit = _require_threshold(threshold)
    prepared = _canonicalize(frame)
    closes = prepared["close"].to_numpy(dtype=np.float64, copy=True)
    dates = prepared["date"].tolist()
    if len(closes) < 2:
        return []
    prev = closes[:-1]
    curr = closes[1:]
    valid = np.isfinite(prev) & np.isfinite(curr) & (prev > 0.0) & (curr > 0.0)
    exceeds = np.zeros(curr.shape[0], dtype=bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        jump = np.abs(np.log(curr / prev))
    exceeds[valid] = jump[valid] > limit
    exceeds[~valid] = True
    return [dates[i + 1] for i in np.flatnonzero(exceeds)]


def intersect_calendar(
    frames: dict[str, pd.DataFrame],
    window_start: str,
    as_of: str,
    excluded: frozenset[str] | set[str] = PINNED_CALENDAR_EXCLUSIONS,
) -> AdjustResult:
    """Keep sessions present for every ticker inside the window.

    The symmetric difference of the union and the intersection must equal
    ``excluded`` exactly. Any other difference, or a pinned date that is not a
    difference, is ``CALENDAR_MISALIGNED``. On success each frame keeps the
    intersection, ordered by date.
    """
    _require_frames(frames)
    start = _require_date_str(window_start, "window_start")
    end = _require_date_str(as_of, "as_of")
    if start > end:
        raise ValueError(f"window_start {start} is after as_of {end}")
    pinned = _require_excluded(excluded)

    prepared: dict[str, pd.DataFrame] = {}
    date_sets: dict[str, set[str]] = {}
    for ticker, frame in frames.items():
        windowed = _window_frame(_canonicalize(frame), start, end)
        prepared[ticker] = windowed
        date_sets[ticker] = set(windowed["date"].tolist())

    if date_sets:
        union = set.union(*date_sets.values())
        intersection = set.intersection(*date_sets.values())
    else:
        union = set()
        intersection = set()
    symdiff = union - intersection
    if symdiff != pinned:
        missing_by_ticker = {}
        for ticker in sorted(date_sets):
            missing = sorted(symdiff - date_sets[ticker])
            if missing:
                missing_by_ticker[ticker] = missing
        return _blocked(
            "CALENDAR_MISALIGNED",
            {
                "unexpected": sorted(symdiff - pinned),
                "pinned_absent": sorted(pinned - symdiff),
                "missing_by_ticker": missing_by_ticker,
            },
        )

    calendar = sorted(intersection)
    keep = set(calendar)
    kept = {}
    for ticker, frame in prepared.items():
        rows = frame.loc[frame["date"].isin(keep)].reset_index(drop=True)
        kept[ticker] = rows
    return AdjustResult(
        status="OK",
        reason=None,
        detail={},
        frames=kept,
        calendar=calendar,
        confirmations=None,
    )


def prepare_panel(
    frames: dict[str, pd.DataFrame],
    window_start: str,
    as_of: str,
    splits: dict[tuple[str, str], float] = PINNED_SPLITS,
    excluded: frozenset[str] | set[str] = PINNED_CALENDAR_EXCLUSIONS,
) -> AdjustResult:
    """Restrict to ``date <= as_of``, adjust pinned splits, intersect, then re-check breaks.

    The first refusal wins. Later steps do not run, and no partial frames are
    returned. An unpinned discontinuity on the adjusted intersection is
    ``SPLIT_DISCONTINUITY``.
    """
    _require_frames(frames)
    end = _require_date_str(as_of, "as_of")
    # Reject a bad window bound before any adjustment step runs.
    _require_date_str(window_start, "window_start")
    restricted = {}
    for ticker, frame in frames.items():
        canonical = _canonicalize(frame)
        restricted[ticker] = canonical.loc[canonical["date"] <= end].reset_index(drop=True)

    split_result = apply_pinned_splits(restricted, splits=splits)
    if split_result.status != "OK":
        return split_result
    if split_result.frames is None:
        raise RuntimeError("split adjustment returned OK without frames")

    calendar_result = intersect_calendar(split_result.frames, window_start, as_of, excluded=excluded)
    if calendar_result.status != "OK":
        return calendar_result
    adjusted = calendar_result.frames
    if adjusted is None:
        raise RuntimeError("calendar intersection returned OK without frames")

    breaks: list[dict] = []
    for ticker in sorted(adjusted):
        for date in detect_split_breaks(adjusted[ticker]):
            breaks.append({"ticker": ticker, "date": date})
    if breaks:
        return _blocked("SPLIT_DISCONTINUITY", {"breaks": breaks})

    return AdjustResult(
        status="OK",
        reason=None,
        detail=dict(split_result.detail),
        frames=calendar_result.frames,
        calendar=calendar_result.calendar,
        confirmations=list(split_result.confirmations or []),
    )


def _blocked(reason: Reason, detail: dict) -> AdjustResult:
    return AdjustResult(
        status="BLOCKED",
        reason=reason,
        detail=detail,
        frames=None,
        calendar=None,
        confirmations=None,
    )


def _require_frames(frames: object) -> None:
    if not isinstance(frames, dict):
        raise TypeError(f"frames must be a dict[str, DataFrame], got {type(frames).__name__}")
    for ticker, frame in frames.items():
        if not isinstance(ticker, str) or ticker == "":
            raise TypeError("frame keys must be non-empty ticker strings")
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(f"frames[{ticker!r}] must be a DataFrame, got {type(frame).__name__}")


def _canonicalize(frame: pd.DataFrame) -> pd.DataFrame:
    """Deep copy, ISO-date strings, identity columns, ascending date order."""
    out = frame.copy(deep=True)
    if "date" not in out.columns:
        raise ValueError("frame is missing the date column")
    date_col = out["date"]
    if not isinstance(date_col, pd.Series):
        raise ValueError("date column must be a single column")
    missing = [name for name in _IDENTITY_COLUMNS if name not in out.columns]
    if missing:
        raise ValueError(f"frame is missing identity columns: {missing}")
    parsed = pd.to_datetime(date_col, errors="raise")
    if not isinstance(parsed, pd.Series) or bool(parsed.isna().any()):
        raise ValueError("date column contains a missing or unparseable date")
    out["date"] = parsed.dt.strftime("%Y-%m-%d")
    ordered = [_IDENTITY_COLUMNS[i] for i in range(len(_IDENTITY_COLUMNS))]
    extra = [name for name in out.columns if name not in _IDENTITY_COLUMNS]
    out = out.loc[:, ordered + extra]
    out = out.sort_values("date", kind="mergesort").reset_index(drop=True)
    return out


def _require_date_str(value: object, label: str) -> str:
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            try:
                dt.date.fromisoformat(text)
            except ValueError as exc:
                raise ValueError(f"{label} is not a calendar date: {value!r}") from exc
            return text
    try:
        stamp = pd.Timestamp(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{label} must be a YYYY-MM-DD string or datetime-like") from exc
    if pd.isna(stamp):
        raise ValueError(f"{label} is missing")
    return stamp.strftime("%Y-%m-%d")


def _require_splits(splits: object) -> list[tuple[str, str, float]]:
    if not isinstance(splits, dict):
        raise TypeError(f"splits must be a dict, got {type(splits).__name__}")
    pins: list[tuple[str, str, float]] = []
    seen: set[tuple[str, str]] = set()
    for key, ratio in splits.items():
        if not isinstance(key, tuple) or len(key) != 2:
            raise TypeError("each split key must be a (ticker, effective_date) tuple")
        ticker, raw_date = key
        if not isinstance(ticker, str) or ticker == "":
            raise TypeError("split ticker must be a non-empty string")
        effective = _require_date_str(raw_date, "split effective_date")
        if (ticker, effective) in seen:
            raise ValueError(f"duplicate split pin for {(ticker, effective)}")
        seen.add((ticker, effective))
        pins.append((ticker, effective, _require_ratio(ratio)))
    pins.sort(key=lambda item: (item[0], item[1]))
    return pins


def _require_ratio(ratio: object) -> float:
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
        raise TypeError("split ratio must be a positive number")
    value = float(ratio)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("split ratio must be finite and positive")
    return value


def _require_tol(tol: object) -> float:
    if isinstance(tol, bool) or not isinstance(tol, (int, float)):
        raise TypeError("tol must be a real number")
    value = float(tol)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("tol must be finite and >= 0")
    return value


def _require_threshold(threshold: object) -> float:
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise TypeError("threshold must be a real number")
    value = float(threshold)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("threshold must be finite and >= 0")
    return value


def _require_excluded(excluded: object) -> frozenset[str]:
    if isinstance(excluded, (str, bytes)):
        raise TypeError("excluded must be a collection of YYYY-MM-DD dates")
    try:
        iterator = iter(excluded)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError("excluded must be a collection of YYYY-MM-DD dates") from exc
    return frozenset(_require_date_str(item, "excluded date") for item in iterator)


def _round6(value: float) -> float:
    """Six decimal places as a decimal float so the detail stays JSON-stable."""
    return float(f"{value:.6f}")


def _confirm_one(
    frame: pd.DataFrame,
    effective: str,
    ratio: float,
    tol: float,
) -> tuple[str | None, float | None]:
    dates = frame["date"].tolist()
    matches = [i for i, date in enumerate(dates) if date == effective]
    if not matches:
        return "effective_date_missing", None
    index = matches[0]
    if index == 0:
        return "no_prior_session", None
    prev_close = float(frame["close"].iloc[index - 1])
    eff_close = float(frame["close"].iloc[index])
    if (
        not math.isfinite(prev_close)
        or not math.isfinite(eff_close)
        or prev_close <= 0.0
        or eff_close <= 0.0
    ):
        return "non_finite_close", None
    observed = prev_close / eff_close
    low = (1.0 - tol) * ratio
    high = (1.0 + tol) * ratio
    if not (low <= observed <= high):
        return "ratio_out_of_tolerance", observed
    return None, observed


def _adjust_before(frame: pd.DataFrame, effective: str, ratio: float) -> None:
    """Scale rows strictly before ``effective`` on a frame this module owns."""
    before = frame["date"].to_numpy() < effective
    for column in _PRICE_COLUMNS:
        values = frame[column].to_numpy(dtype=np.float64, copy=True)
        values[before] /= ratio
        frame[column] = values
    volume = frame["volume"].to_numpy(dtype=np.float64, copy=True)
    volume[before] *= ratio
    frame["volume"] = volume


def _window_frame(frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    dates = frame["date"]
    mask = (dates >= start) & (dates <= end)
    return frame.loc[mask].reset_index(drop=True)
