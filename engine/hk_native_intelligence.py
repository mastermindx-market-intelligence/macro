"""HK-native evidence families for the zero-authority Prophet discovery lane.

H3 and X1 remain ACCRUING research families. This module only projects their
pre-registered, point-in-time-safe reads onto existing discovery candidates.
It never selects candidates, grants entry, ranks the live board, or publishes.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd

OWN_WIN = 504
OWN_MIN = 252
X1_LOOKBACK = 21
# X1 prereg requires a month-end signal to be no more than 10 calendar days old.
# Reuse that conservative research freshness bound for both daily A/H inputs.
MAX_INPUT_LAG_DAYS = 10

ACCRUING = "ACCRUING"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNAVAILABLE = "UNAVAILABLE"
STALE = "STALE"
PARTIAL = "PARTIAL"

FAMILIES = ("h3_ah_discount", "x1_atwin_momentum")
BNRS_FAMILY = "beta_neutral_rs"
DISCOVERY_FAMILIES = (*FAMILIES, BNRS_FAMILY)
FAMILY_FIELDS = tuple(
    field for family in DISCOVERY_FAMILIES
    for field in (f"{family}_status", f"{family}_value")
)

# Wave 7: two SEPARATE same-population rank races. These names identify
# zero-authority Lane-A challengers; they are not production board definitions
# and must never be fused into an ungoverned HK master score.
RANK_DEFINITIONS = {
    "h3_ah_discount": "hk_h3_ah_discount_rank_v1",
    "x1_atwin_momentum": "hk_x1_atwin_momentum_rank_v1",
}

# Broad-coverage HK screen. The masterplan explicitly classifies beta-neutral
# relative strength as candidate/intelligence SCREEN input only until separately
# promoted. Keep it outside RANK_DEFINITIONS so it cannot be mistaken for the
# two ACCRUING selection-evidence families above.
BNRS_STATUS = "SCREEN"
BNRS_AUTHORITY = "candidate_intelligence_screen"
BNRS_DEFINITION = "hk_beta_neutral_rs_screen_rank_v1"


def with_bnrs_evidence(
    family_rows: Mapping[str, Mapping[str, Any]] | None,
    tickers: Iterable[str],
    screen_values: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Add the broad beta-neutral RS screen to existing native-family rows.

    Every requested ticker receives an explicit status. A finite screen read is
    SCREEN; absent/non-finite input is UNAVAILABLE with a null value. Existing
    H3/X1 evidence is copied, never mutated in place.
    """
    source = family_rows or {}
    values = screen_values or {}
    out: dict[str, dict[str, Any]] = {}
    for raw_ticker in tickers:
        ticker = str(raw_ticker)
        row = dict(source.get(ticker) or {})
        value: float | None = None
        try:
            candidate = float(values.get(ticker))
        except (TypeError, ValueError):
            candidate = float("nan")
        if np.isfinite(candidate):
            value = candidate
            status = BNRS_STATUS
        else:
            status = UNAVAILABLE
        row[f"{BNRS_FAMILY}_status"] = status
        row[f"{BNRS_FAMILY}_value"] = value
        out[ticker] = row
    return out


def rank_bnrs_calls(
    calls: Iterable[Mapping[str, Any]],
    screen_values: Mapping[str, Any] | None,
) -> dict[str, dict[str, float | None]]:
    """Project existing beta-neutral RS onto exactly the incumbent population.

    This is a zero-authority SCREEN race. It never originates a name, never
    substitutes missing with zero and has no conservative haircut because no
    such calibration is frozen for this screen.
    """
    values = screen_values or {}
    out: dict[str, dict[str, float | None]] = {}
    for call in calls or ():
        raw_ticker = call.get("ticker") if isinstance(call, Mapping) else None
        if raw_ticker in (None, ""):
            continue
        ticker = str(raw_ticker)
        if ticker in out:
            continue
        score: float | None = None
        try:
            candidate = float(values.get(ticker))
        except (TypeError, ValueError):
            candidate = float("nan")
        if np.isfinite(candidate):
            score = candidate
        out[ticker] = {
            "score_raw": score,
            "score_conservative": None,
        }
    return out


def rank_family_calls(
    calls: Iterable[Mapping[str, Any]],
    family_rows: Mapping[str, Mapping[str, Any]] | None,
    family: str,
) -> dict[str, dict[str, float | None]]:
    """Score one preregistered HK family over exactly the incumbent population.

    Lane A owns population identity. This adapter iterates only calls and never
    emits an off-list name merely because family_rows contains one. Only
    ACCRUING family values are rankable: stale, partial, unavailable and
    not-applicable reads stay null rather than becoming zero.
    score_conservative is deliberately null because neither H3 nor X1(b) has
    a frozen conservative haircut for this same-population race.
    """
    if family not in FAMILIES:
        raise ValueError(f"unregistered HK native family: {family!r}")
    rows = family_rows or {}
    status_key = f"{family}_status"
    value_key = f"{family}_value"
    out: dict[str, dict[str, float | None]] = {}
    for call in calls:
        raw_ticker = call.get("ticker") if isinstance(call, Mapping) else None
        if raw_ticker in (None, ""):
            continue
        ticker = str(raw_ticker)
        if ticker in out:
            continue
        evidence = rows.get(ticker) or {}
        score: float | None = None
        if evidence.get(status_key) == ACCRUING:
            try:
                candidate = float(evidence.get(value_key))
            except (TypeError, ValueError):
                candidate = float("nan")
            if np.isfinite(candidate):
                score = candidate
        out[ticker] = {
            "score_raw": score,
            "score_conservative": None,
        }
    return out

def _pair_map(
    pair_rows: Iterable[Mapping[str, Any]] | Mapping[str, str] | None,
) -> dict[str, str] | None:
    if pair_rows is None:
        return None
    if isinstance(pair_rows, Mapping):
        return {
            str(h): str(a) for h, a in pair_rows.items()
            if h not in (None, "") and a not in (None, "")
        }
    out: dict[str, str] = {}
    for row in pair_rows:
        if not isinstance(row, Mapping):
            continue
        h, a = row.get("h"), row.get("a")
        if h not in (None, "") and a not in (None, ""):
            out[str(h)] = str(a)
    return out


def load_a_twin_closes(pair_rows, reader) -> pd.DataFrame | None:
    """Load X1 from its preregistered per-name china_stocks price plane.

    reader is the existing store.read-compatible seam. Missing or corrupt
    individual twins degrade that twin to UNAVAILABLE downstream; there is no
    fallback to china_search because that vintage matrix is a distinct price
    plane and is not the X1 preregistered signal source.
    """
    pairs = _pair_map(pair_rows)
    if not pairs:
        return None
    columns: dict[str, pd.Series] = {}
    for a_ticker in dict.fromkeys(pairs.values()):
        try:
            frame = reader("china_stocks", a_ticker)
        except Exception:
            continue
        if frame is None or frame.empty or "close" not in frame.columns:
            continue
        series = pd.to_numeric(frame["close"], errors="coerce").copy()
        series.index = pd.to_datetime(series.index, errors="coerce")
        series = series[~series.index.isna()].sort_index().dropna()
        if not series.empty:
            columns[a_ticker] = series
    return pd.DataFrame(columns).sort_index() if columns else None


def _asof_series(series: pd.Series | None, asof: pd.Timestamp | None) -> pd.Series:
    if series is None or asof is None:
        return pd.Series(dtype=float)
    s = pd.to_numeric(series, errors="coerce").copy()
    s.index = pd.to_datetime(s.index, errors="coerce")
    s = s[~s.index.isna()].sort_index()
    return s.loc[s.index <= asof].dropna()


def _is_stale(series: pd.Series, asof: pd.Timestamp) -> bool:
    if series.empty:
        return False
    last = pd.Timestamp(series.index[-1]).normalize()
    return (asof.normalize() - last).days > MAX_INPUT_LAG_DAYS

def _h3_read(series: pd.Series, asof: pd.Timestamp) -> tuple[str, float | None]:
    s = _asof_series(series, asof)
    if s.empty:
        return UNAVAILABLE, None
    window = s.tail(OWN_WIN)
    if len(window) < OWN_MIN:
        return PARTIAL, None
    last = float(window.iloc[-1])
    value = float((window < last).sum() / len(window))
    return (STALE if _is_stale(s, asof) else ACCRUING), value


def _x1_read(series: pd.Series, asof: pd.Timestamp) -> tuple[str, float | None]:
    s = _asof_series(series, asof)
    if s.empty:
        return UNAVAILABLE, None
    returns = (s / s.shift(X1_LOOKBACK) - 1.0).dropna().tail(OWN_WIN)
    if len(returns) < OWN_MIN:
        return PARTIAL, None
    sd = float(returns.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        return PARTIAL, None
    value = float((float(returns.iloc[-1]) - float(returns.mean())) / sd)
    return (STALE if _is_stale(s, asof) else ACCRUING), value


def unavailable_family_evidence(tickers: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Fail-soft family projection when applicability/source reads are unknown."""
    return {
        str(t): {
            "h3_ah_discount_status": UNAVAILABLE,
            "h3_ah_discount_value": None,
            "x1_atwin_momentum_status": UNAVAILABLE,
            "x1_atwin_momentum_value": None,
        }
        for t in tickers
    }

def build_family_evidence(
    tickers: Iterable[str],
    *,
    asof: str | pd.Timestamp | None,
    pair_rows: Iterable[Mapping[str, Any]] | Mapping[str, str] | None,
    premium_panel: pd.DataFrame | None,
    a_closes: pd.DataFrame | None,
) -> dict[str, dict[str, Any]]:
    """Project frozen H3/X1 reads onto existing HK discovery candidates.

    H3 is the current A/H premium percentile inside its trailing 504
    observations (min 252). X1(b) is the A twin's trailing 21-session return
    standardized inside its own trailing 504 return observations (min 252,
    sample SD). Both inputs are cut at asof before any statistic is formed.
    """
    names = [str(t) for t in tickers if t not in (None, "")]
    pairs = _pair_map(pair_rows)
    try:
        asof_ts = pd.Timestamp(asof).normalize() if asof is not None else None
    except (TypeError, ValueError):
        asof_ts = None
    if pairs is None or asof_ts is None:
        return unavailable_family_evidence(names)

    premium = premium_panel if isinstance(premium_panel, pd.DataFrame) else None
    a_panel = a_closes if isinstance(a_closes, pd.DataFrame) else None
    out: dict[str, dict[str, Any]] = {}

    for ticker in names:
        twin = pairs.get(ticker)
        if twin is None:
            out[ticker] = {
                "h3_ah_discount_status": NOT_APPLICABLE,
                "h3_ah_discount_value": None,
                "x1_atwin_momentum_status": NOT_APPLICABLE,
                "x1_atwin_momentum_value": None,
            }
            continue

        if premium is None or ticker not in premium.columns:
            h3_status, h3_value = UNAVAILABLE, None
        else:
            h3_status, h3_value = _h3_read(premium[ticker], asof_ts)

        if a_panel is None or twin not in a_panel.columns:
            x1_status, x1_value = UNAVAILABLE, None
        else:
            x1_status, x1_value = _x1_read(a_panel[twin], asof_ts)

        out[ticker] = {
            "h3_ah_discount_status": h3_status,
            "h3_ah_discount_value": h3_value,
            "x1_atwin_momentum_status": x1_status,
            "x1_atwin_momentum_value": x1_value,
        }
    return out