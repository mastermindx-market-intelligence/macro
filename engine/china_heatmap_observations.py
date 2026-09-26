"""China-only endpoint observation truth for the existing market heatmap engine.

Pure computation. No I/O, publication, monitoring, scheduling or trade authority.
Reuses lib.cn_calendar by default; never substitutes a stock's last available
observation for the requested endpoint. Missing returns are JSON nulls, not 0.

This validates observation intervals, not provider finality or wall-clock freshness.
The existing publisher owns those gates. Adjusted-price and membership provenance
remain the caller's responsibility; this is not a point-in-time backtest engine.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, timedelta
from numbers import Number
import math
from typing import Any

import numpy as np
import pandas as pd

TIMEFRAMES = ('1D', '1W', 'MTD', '1M', '3M', '6M', 'YTD', '1Y')
SCHEMA = 'china_heatmap_observations.v1'
SessionLookup = Callable[[date], date]


def _identity(values: Iterable[str], label: str) -> list[str]:
    result = list(values)
    if any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in result):
        raise ValueError(f'{label} must contain nonempty, unpadded string identities')
    if len(set(result)) != len(result):
        raise ValueError(f'{label} contains duplicate identities')
    return result


def _session_label(value: Any, label: str) -> pd.Timestamp:
    """Interpret daily labels as calendar dates, not intraday event timestamps."""
    if isinstance(value, (Number, bool, np.bool_)):
        raise ValueError(f'{label} must be a date label, not an epoch number')
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{label} is not a valid session date') from exc
    if pd.isna(stamp) or stamp != stamp.normalize():
        raise ValueError(f'{label} must be a midnight daily session label')
    # A date-labelled daily panel may use UTC or exchange-local midnight. It is
    # a calendar label, not an instant to shift into the preceding/following day.
    return stamp.tz_localize(None) if stamp.tzinfo else stamp


def _quote(value: Any) -> tuple[str, float | None]:
    if value is None or value is pd.NA or value is pd.NaT:
        return 'MISSING', None
    if isinstance(value, (bool, np.bool_, complex, np.complexfloating)):
        return 'INVALID', None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 'INVALID', None
    if math.isnan(number):
        return 'MISSING', None
    if not math.isfinite(number) or number <= 0:
        return 'INVALID', None
    return 'VALID', number


def _references(anchor: date, lookup: SessionLookup) -> dict[str, date]:
    stamp = pd.Timestamp(anchor)
    targets = {
        '1D': anchor - timedelta(days=1),
        '1W': (stamp - pd.DateOffset(weeks=1)).date(),
        'MTD': anchor.replace(day=1) - timedelta(days=1),
        '1M': (stamp - pd.DateOffset(months=1)).date(),
        '3M': (stamp - pd.DateOffset(months=3)).date(),
        '6M': (stamp - pd.DateOffset(months=6)).date(),
        'YTD': date(anchor.year, 1, 1) - timedelta(days=1),
        '1Y': (stamp - pd.DateOffset(years=1)).date(),
    }
    result = {}
    for key, target in targets.items():
        ref = lookup(target)
        if not isinstance(ref, date) or ref > target or ref >= anchor:
            raise ValueError('session calendar returned an invalid reference date')
        result[key] = ref
    return result


def build_china_observations(
    closes: pd.DataFrame,
    members: Iterable[str],
    *,
    asof: Any = None,
    session_on_or_before: SessionLookup | None = None,
    facts_builder: Callable[[pd.DataFrame, pd.Timestamp], dict] | None = None,
) -> dict[str, Any]:
    """Build interval returns, dates/statuses and membership-based coverage.

    ``asof`` is the declared payload session. Every timeframe requires a valid
    positive finite price at that session and at its exact calendar reference.
    A missing previous print is not silently converted into a two-day return.
    Missing members remain in the result and in every coverage denominator.

    Duplicate dates/identities and intraday timestamps fail closed. Later rows
    are ignored before quote/metadata calculation. Inputs are never mutated.
    Empty input needs an explicit asof; no wall clock is invented for it.
    """
    if not isinstance(closes, pd.DataFrame):
        raise TypeError('closes must be a pandas DataFrame')
    tickers = _identity(members, 'members')
    columns = _identity(closes.columns, 'close columns')
    if session_on_or_before is None:
        from lib.cn_calendar import last_session_on_or_before
        session_on_or_before = last_session_on_or_before
    lookup = session_on_or_before

    labels = pd.DatetimeIndex([_session_label(v, 'panel index') for v in closes.index])
    if labels.has_duplicates:
        raise ValueError('panel contains duplicate session dates')
    if asof is None:
        if labels.empty:
            raise ValueError('empty panel requires an explicit asof')
        anchor_stamp = labels.max()
    else:
        anchor_stamp = _session_label(asof, 'asof')
    anchor = anchor_stamp.date()
    if lookup(anchor) != anchor:
        raise ValueError('asof is not an exchange session')
    references = _references(anchor, lookup)

    frame = closes.copy(deep=True)
    frame.index = labels
    frame = frame.loc[frame.index <= anchor_stamp].sort_index()
    # Rows on non-sessions cannot become a last-observed market quote.
    frame = frame.loc[[lookup(d.date()) == d.date() for d in frame.index]]
    returns: dict[str, dict[str, float | None]] = {}
    observations: dict[str, dict[str, Any]] = {}
    counts = dict.fromkeys(TIMEFRAMES, 0)
    current_count = 0
    for ticker in tickers:
        series = frame[ticker] if ticker in columns else pd.Series(dtype=float)
        current_state, current_price = _quote(series.get(anchor_stamp))
        current_count += current_state == 'VALID'
        last_session, last_price = None, None
        for session, value in reversed(list(series.items())):
            state, price = _quote(value)
            if state == 'VALID':
                last_session, last_price = session.date().isoformat(), price
                break
        perf, frames = {}, {}
        for tf in TIMEFRAMES:
            reference = references[tf]
            reference_state, reference_price = _quote(series.get(pd.Timestamp(reference)))
            value: float | None = None
            if current_state != 'VALID':
                status = 'CURRENT_' + current_state
            elif reference_state != 'VALID':
                status = 'REFERENCE_' + reference_state
            else:
                raw = (current_price / reference_price - 1.0) * 100.0
                if math.isfinite(raw):
                    value = round(raw, 2)
                    status = 'VALID'
                    counts[tf] += 1
                else:
                    status = 'RETURN_INVALID'
            perf[tf] = value
            frames[tf] = {
                'status': status,
                'observation_session': anchor.isoformat(),
                'reference_session': reference.isoformat(),
            }
        returns[ticker] = perf
        observations[ticker] = {
            'schema': SCHEMA,
            'observation_session': anchor.isoformat(),
            'current_status': current_state,
            'last_observed_session': last_session,
            'last_observed_close': last_price,
            'timeframes': frames,
        }
    n = len(tickers)
    if facts_builder is not None:
        safe_frame = frame.reindex(columns=tickers).apply(
            lambda col: col.map(lambda value: _quote(value)[1]))
        facts = facts_builder(safe_frame.astype(float), anchor_stamp)
    else:
        facts = {t: {'px': round(o['last_observed_close'], 4)}
                 for t, o in observations.items()
                 if o['last_observed_close'] is not None}
    return {
        'facts': facts,
        'schema': SCHEMA,
        'asof': anchor.isoformat(),
        'returns': returns,
        'observations': observations,
        'coverage': {
            'basis': 'current_membership',
            'membership_count': n,
            'current_observation_count': int(current_count),
            'timeframes': {
                tf: {
                    'valid_count': counts[tf],
                    'missing_count': n - counts[tf],
                    'denominator': n,
                    'fraction': counts[tf] / n if n else 0.0,
                } for tf in TIMEFRAMES
            },
        },
    }
