"""Observed-move primitives for the Grey Deer pullback study (W2).

Implements the label and feature definitions frozen in
``research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md``:

* §3 price-basis checks -> :func:`assert_price_basis`
* §4 forward maximum loss and the loss event -> :func:`forward_max_loss`,
  :func:`loss_event`, :func:`maturity_summary`
* §6 trailing features -> :func:`trailing_drawdown`, :func:`log_return`,
  :func:`sma_gap`. Realized volatility is NOT reimplemented here: callers use
  ``engine.vol_forecast.realized_vol`` exactly as the preregistration names it.

Two kinds of series live in this module and must never be confused:

LABELS (``forward_max_loss``, ``loss_event``) look AHEAD. Row t reads closes
t+1..t+h. They are outcomes, never features, and an immature row (fewer than h
closes after it) is absent (NaN / <NA>), never zero.

FEATURES (``trailing_drawdown``, ``log_return``, ``sma_gap``) read only closes
at or before t. A row whose window is not yet full is NaN.

Research path only: nothing on the render, nightly or serving path imports
this module. Inputs are a single symbol's close series on a sorted, unique
DatetimeIndex (or any strictly increasing index).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SPLIT_LIKE_RATIO = 0.75
LOSS_THRESHOLD = 0.05
HORIZONS = (5, 10, 21)
DRAWDOWN_WINDOW = 63


class ObservedMoveRefusal(ValueError):
    """The input cannot be measured as given. ``code`` names the refusal."""

    code = "OBSERVED_MOVE_REFUSAL"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class PriceBasisDiscontinuity(ObservedMoveRefusal):
    """A day-over-day close ratio outside [0.75, 1/0.75] (prereg §3 check 3)."""

    code = "PRICE_BASIS_DISCONTINUITY"


def _as_series(close: pd.Series) -> pd.Series:
    if not isinstance(close, pd.Series):
        raise TypeError("close must be a pandas Series")
    return close.astype(float)


def assert_price_basis(close: pd.Series, split_like_ratio: float = SPLIT_LIKE_RATIO) -> None:
    """Refuse a close series whose basis cannot be trusted. Never re-adjusts.

    Checks run in preregistration order and the first failure raises:

    1. index strictly increasing with no duplicates
       (``INDEX_NOT_STRICTLY_INCREASING``);
    2. every close positive and finite (``NON_POSITIVE_OR_NON_FINITE_CLOSE``);
    3. every day-over-day ratio P_t / P_{t-1} inside
       [split_like_ratio, 1 / split_like_ratio], bounds inclusive
       (:class:`PriceBasisDiscontinuity`).

    The session-set check (trading calendar completeness) is the W3 runner's.
    """
    s = _as_series(close)
    idx = s.index
    if idx.has_duplicates or not idx.is_monotonic_increasing:
        raise ObservedMoveRefusal(
            "close index is not strictly increasing", code="INDEX_NOT_STRICTLY_INCREASING"
        )
    values = s.to_numpy()
    bad = ~np.isfinite(values) | (values <= 0)
    if bad.any():
        first = idx[int(np.argmax(bad))]
        raise ObservedMoveRefusal(
            f"non-positive or non-finite close at {first!r}",
            code="NON_POSITIVE_OR_NON_FINITE_CLOSE",
        )
    if len(values) < 2:
        return
    ratio = values[1:] / values[:-1]
    low, high = split_like_ratio, 1.0 / split_like_ratio
    out = (ratio < low) | (ratio > high)
    if out.any():
        i = int(np.argmax(out))
        raise PriceBasisDiscontinuity(
            f"close ratio {ratio[i]:.6f} at {idx[i + 1]!r} is outside "
            f"[{low:.6f}, {high:.6f}]; refusing rather than re-adjusting"
        )


def forward_max_loss(close: pd.Series, h: int) -> pd.Series:
    """LABEL. A(t, h) = max(0, 1 - min(P_{t+1..t+h}) / P_t). Looks ahead.

    The last ``h`` rows are immature and NaN, never zero.
    """
    h = int(h)
    if h < 1:
        raise ValueError("h must be >= 1")
    s = _as_series(close)
    future_min = s.rolling(h, min_periods=h).min().shift(-h)
    return (1.0 - future_min / s).clip(lower=0.0).rename(f"fwd_max_loss_{h}")


def loss_event(A: pd.Series, threshold: float = LOSS_THRESHOLD) -> pd.Series:
    """LABEL. Y = 1 iff A >= threshold; an immature (NaN) A stays <NA>."""
    y = pd.Series(pd.NA, index=A.index, dtype="boolean", name=getattr(A, "name", None))
    mature = A.notna()
    y[mature] = A[mature] >= threshold
    return y


def maturity_summary(A: pd.Series) -> dict[str, int]:
    """Counts of mature and immature label rows, printed rather than hidden."""
    n_total = int(len(A))
    n_mature = int(A.notna().sum())
    return {"n_total": n_total, "n_mature": n_mature, "n_immature": n_total - n_mature}


def trailing_drawdown(close: pd.Series, w: int = DRAWDOWN_WINDOW) -> pd.Series:
    """FEATURE. dd_w = 1 - P_t / max(P over the w closes ending at t)."""
    s = _as_series(close)
    peak = s.rolling(int(w), min_periods=int(w)).max()
    return (1.0 - s / peak).rename(f"dd{int(w)}")


def log_return(close: pd.Series, k: int) -> pd.Series:
    """FEATURE. r_k = log(P_t / P_{t-k})."""
    s = _as_series(close)
    return np.log(s / s.shift(int(k))).rename(f"r{int(k)}")


def sma_gap(close: pd.Series, w: int) -> pd.Series:
    """FEATURE. close / SMA_w - 1, with SMA_w including P_t."""
    s = _as_series(close)
    sma = s.rolling(int(w), min_periods=int(w)).mean()
    return (s / sma - 1.0).rename(f"sma_gap{int(w)}")
