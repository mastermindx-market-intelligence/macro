"""Frozen TTI R1-B v4 candidate construction; no outcomes or live authority.

Consumes an indexed five-minute OHLCV frame and caller-qualified prior values.
Processes only completed bars, in session-clock order. This is not an event store,
production detector registration, backtest or provider client. The caller owns
input acquisition; source-arrival/availability remains unproven here.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from numbers import Real

import pandas as pd

from engine.session_digest import session_window_et
from lib.nyse_calendar import is_session, session_n_back

CONFIG_SHA256 = '24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19'
BAR = timedelta(minutes=5)
COLUMNS = ('open', 'high', 'low', 'close', 'volume')


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def _row_values(row: pd.Series) -> tuple[float, ...] | None:
    values = tuple(row[k] for k in COLUMNS)
    if not all(_number(v) for v in values):
        return None
    o, h, low, c, v = map(float, values)
    if min(o, h, low, c) <= 0 or v < 0 or not low <= min(o, c) <= max(o, c) <= h:
        return None
    return o, h, low, c, v


def construct_session(
    frame: pd.DataFrame, *, symbol: str, session: date, prior_session: date | None,
    prior_close: float, prior_atr: float, asof: datetime, config_bytes: bytes,
    price_basis: str = 'adjusted',
) -> dict:
    """Construct v4 events/anchors known by ``asof``, never post-entry outcomes.

    Entry references are FUTURE CLOCKS, not observed prices or simulated fills.
    The clock delay and every market threshold come from the exact frozen bytes.
    A late gap/invalid bar cannot delete already-constructed earlier events.
    """
    if hashlib.sha256(config_bytes).hexdigest() != CONFIG_SHA256:
        raise ValueError('frozen v4 config identity mismatch')
    cfg = json.loads(config_bytes)
    if not isinstance(asof, datetime) or asof.tzinfo is None or asof.utcoffset() is None:
        raise ValueError('timezone-aware asof required')
    if not isinstance(symbol, str) or symbol not in cfg['symbols']:
        raise ValueError('symbol outside frozen pilot universe')
    report = {
        'schema': 'mastermind.tti.r1b.construction.v4',
        'study_id': cfg['study_id'], 'config_sha256': CONFIG_SHA256,
        'symbol': symbol, 'session': session.isoformat(), 'asof': _iso(asof),
        'authority': 'research_construction_only', 'may_alert': False,
        'may_rank': False, 'may_size': False, 'may_trade': False,
        'historical_availability_proven': False, 'market_outcomes_computed': False,
        'source_evidence_class': 'availability_time_unproven',
        'availability': 'AVAILABLE', 'reason': None,
        'events': [], 'anchors': [], 'control_census': [], 'diagnostics': [],
    }

    def unavailable(reason: str) -> dict:
        report.update(availability='UNAVAILABLE', reason=reason)
        return report

    if price_basis != 'adjusted':
        return unavailable('price_basis_mismatch')
    if not is_session(session):
        return unavailable('not_trading_session')
    start, end = session_window_et(session)
    if end - start != timedelta(minutes=390):
        return unavailable('normal_session_required')
    if prior_session != session_n_back(session, 1):
        return unavailable('stale_or_missing_prior_session')
    if not all(_number(v) and v > 0 for v in (prior_close, prior_atr)):
        return unavailable('invalid_prior_normalization')
    if not isinstance(frame, pd.DataFrame) or any(k not in frame.columns for k in COLUMNS):
        raise ValueError('indexed OHLCV frame required')
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError('timezone-aware bar-start index required')
    if frame.index.hasnans:
        raise ValueError('unlocatable bar timestamp')
    # Crucially, no validation of values outside the decision prefix.
    known = frame[(frame.index >= start) & (frame.index < end) &
                  (frame.index + BAR <= asof)]
    groups = {t: g for t, g in known.groupby(level=0, sort=False)}
    bad_slots = set()
    previous = None
    for t in known.index:
        elapsed = (t - start).total_seconds()
        if elapsed % 300:
            bad_slots.add(pd.Timestamp(start + timedelta(seconds=int(elapsed // 300) * 300)))
        if previous is not None and t < previous:
            bad_slots.add(t)
        previous = t

    emitted: set[str] = set()
    controls_seen: set[int] = set()
    anchors: list[dict] = []
    recent: list[tuple[float, ...] | None] = []
    running_low: float | None = None
    prefix_complete = True
    usable_bars = 0

    def event(selector: str, a: dict, decision: datetime, delay: int) -> None:
        if selector in emitted:
            return
        emitted.add(selector)
        report['events'].append({
            'selector': selector, 'anchor_id': a['anchor_id'],
            'candidate_at': a['candidate_at'], 'decision_at': _iso(decision),
            'entry_reference_at': _iso(decision + timedelta(minutes=cfg['execution_latency_minutes'])),
            'entry_reference_state': 'scheduled_clock_only_not_a_fill',
            'confirmation_delay_bars': delay,
            'processing_latency_minutes': cfg['execution_latency_minutes'],
            'candidate_low': a['candidate_low'], 'episode_low': a['episode_low'],
            'reclaim_level': a['reclaim_level'], 'continuation_level': a['continuation_level'],
            'prior_atr': float(prior_atr), 'previous_regular_close': float(prior_close),
            'displacement_atr': a['displacement_atr'],
            'close_location': a['close_location'], 'fresh_low_extension_atr': a['fresh_low_extension_atr'],
            'authority': 'research_construction_only',
        })

    i, t = 0, start
    while t < end and t + BAR <= asof:
        decision = t + BAR
        rows = groups.get(pd.Timestamp(t))
        reason = None
        if pd.Timestamp(t) in bad_slots:
            reason = 'off_grid_or_unordered_bar'
        elif rows is None:
            reason = 'missing_bar'
        elif len(rows) != 1:
            reason = 'duplicate_bar'
        values = None if reason else _row_values(rows.iloc[0])
        if reason is None and values is None:
            reason = 'invalid_ohlcv'
        positive = values is not None and values[4] > 0
        if reason:
            prefix_complete = False
        if not positive:
            report['diagnostics'].append({'at': _iso(decision),
                                          'reason': reason or 'nonpositive_volume'})
        recent.append(values if positive else None)
        recent = recent[-cfg['recent_impulse_bars']:]

        # Pending anchors compete in chronological confirmation time, not in
        # the future resolution order of a preselected first candidate.
        for a in anchors:
            if a['race'] != 'PENDING':
                continue
            delay = i - a['_index']
            if not positive:
                a.update(race='UNAVAILABLE', resolved_at=_iso(decision),
                         race_reason=reason or 'nonpositive_volume')
                continue
            a['episode_low'] = min(a['episode_low'], values[2])
            if values[3] > a['reclaim_level']:
                a.update(race='RECLAIM', resolved_at=_iso(decision))
                event('RECLAIM_ONLY', a, decision, delay)
                if a['forming']:
                    event('EXHAUSTION_RECLAIM', a, decision, delay)
            elif values[3] <= a['continuation_level']:
                a.update(race='CONTINUATION', resolved_at=_iso(decision))
                event('CONTINUATION_RISK', a, decision, delay)
            elif delay >= cfg['confirmation_window_bars']:
                a.update(race='EXPIRED', resolved_at=_iso(decision))

        minute = decision.hour * 60 + decision.minute
        eligible_clock = cfg['candidate_decision_start_minute_et'] <= minute <= cfg['candidate_decision_end_minute_et']
        trailing_complete = len(recent) == cfg['recent_impulse_bars'] and all(x is not None for x in recent)
        if (positive and prefix_complete and eligible_clock and running_low is not None
                and values[2] < running_low and trailing_complete):
            o, h, low, c, volume = values
            displacement = (prior_close - low) / prior_atr
            impulse = (recent[0][0] - low) / prior_atr
            if h == low:
                report['diagnostics'].append({'at': _iso(decision), 'reason': 'zero_range_candidate'})
            elif displacement >= cfg['base_displacement_atr_min'] and impulse >= cfg['recent_impulse_atr_min']:
                location = (c - low) / (h - low)
                extension = (running_low - low) / prior_atr
                a = {
                    'anchor_id': f'{symbol}:{session.isoformat()}:{_iso(decision)}',
                    '_index': i, 'candidate_at': _iso(decision),
                    'candidate_low': low, 'episode_low': low,
                    'reclaim_level': running_low,
                    'continuation_level': low - cfg['continuation_extension_atr'] * prior_atr,
                    'displacement_atr': displacement, 'recent_impulse_atr': impulse,
                    'close_location': location, 'fresh_low_extension_atr': extension,
                    'forming': location >= cfg['exhaustion_close_location_min'] and extension <= cfg['exhaustion_extension_atr_max'],
                    'race': 'PENDING', 'resolved_at': None,
                }
                anchors.append(a)
                event('BASE_FRESH_LOW', a, decision, 0)
                if a['forming']:
                    event('EXHAUSTION_FORMING', a, decision, 0)
                clock_bin = minute // cfg['clock_bin_minutes']
                if clock_bin not in controls_seen:
                    controls_seen.add(clock_bin)
                    report['control_census'].append({
                        'anchor_id': a['anchor_id'], 'candidate_at': a['candidate_at'],
                        'symbol': symbol, 'session': session.isoformat(),
                        'clock_bin': clock_bin,
                        'displacement_bucket': bisect_right(cfg['displacement_bucket_edges_atr'], displacement) - 1,
                        'displacement_atr': displacement,
                        'future_family_labels_used': False,
                    })
        if positive:
            usable_bars += 1
            running_low = values[2] if running_low is None else min(running_low, values[2])
        i += 1
        t += BAR
    report['anchors'] = [{k: v for k, v in a.items() if not k.startswith('_')} for a in anchors]
    if i == 0:
        report.update(availability='PENDING', reason='no_completed_regular_bar_yet')
    elif usable_bars == 0:
        report.update(availability='UNAVAILABLE', reason='no_usable_completed_bars')
    elif report['diagnostics']:
        report.update(availability='PARTIAL', reason='input_gaps_or_unusable_observations')
    return report
