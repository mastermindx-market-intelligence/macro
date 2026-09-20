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


def _daily_by_session(frame: pd.DataFrame, *, columns: tuple[str, ...], name: str) -> dict[date, dict[str, float]]:
    if not isinstance(frame, pd.DataFrame) or any(c not in frame.columns for c in columns):
        raise ValueError(f'{name} daily frame missing required columns')
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans:
        raise ValueError(f'{name} daily frame requires DatetimeIndex')
    days = [ts.date() for ts in frame.index]
    if len(days) != len(set(days)):
        raise ValueError(f'{name} daily frame has duplicate session')
    if any(a >= b for a, b in zip(days, days[1:])):
        raise ValueError(f'{name} daily frame must be ordered')
    out: dict[date, dict[str, float]] = {}
    for day, (_, row) in zip(days, frame.iterrows()):
        values: dict[str, float] = {}
        for col in columns:
            value = row[col]
            if not _number(value) or float(value) <= 0:
                continue
            values[col] = float(value)
        if len(values) == len(columns):
            if {'high', 'low', 'close'} <= values.keys():
                if not values['low'] <= values['close'] <= values['high']:
                    continue
            out[day] = values
    return out


def build_prior_normalization(
    stock_daily: pd.DataFrame, benchmark_daily: pd.DataFrame, *, session: date,
    config_bytes: bytes, price_basis: str = 'adjusted',
) -> dict:
    """Build frozen v4 prior-only ATR20/beta inputs; never current-session data."""
    if hashlib.sha256(config_bytes).hexdigest() != CONFIG_SHA256:
        raise ValueError('frozen v4 config identity mismatch')
    cfg = json.loads(config_bytes)
    stock = _daily_by_session(stock_daily, columns=('high', 'low', 'close'), name='stock')
    benchmark = _daily_by_session(benchmark_daily, columns=('close',), name='benchmark')
    report = {
        'schema': 'mastermind.tti.r1b.prior_normalization.v4',
        'study_id': cfg['study_id'], 'config_sha256': CONFIG_SHA256,
        'session': session.isoformat(), 'authority': 'research_normalization_only',
        'historical_availability_proven': False, 'market_outcomes_computed': False,
        'source_evidence_class': 'availability_time_unproven',
        'availability': 'AVAILABLE', 'reason': None,
        'prior_session': None, 'prior_close': None, 'prior_atr': None,
        'atr_sessions': 0, 'beta_available': False, 'beta': None,
        'beta_raw': None, 'beta_pairs': 0, 'beta_reason': None,
    }
    if price_basis != 'adjusted':
        report.update(availability='UNAVAILABLE', reason='price_basis_mismatch')
        return report
    if not is_session(session):
        report.update(availability='UNAVAILABLE', reason='not_trading_session')
        return report
    prior = session_n_back(session, 1)
    report['prior_session'] = None if prior is None else prior.isoformat()

    # Beta uses only adjacent scheduled prior-session close pairs; missing rows
    # skip that pair rather than bridging across a data gap.
    beta_lookback = int(cfg['beta_lookback_sessions'])
    beta_days = [session_n_back(session, n) for n in range(beta_lookback + 1, 0, -1)]
    beta_days = [d for d in beta_days if d is not None]
    stock_r: list[float] = []
    bench_r: list[float] = []
    for left, right in zip(beta_days, beta_days[1:]):
        sl, sr = stock.get(left), stock.get(right)
        ql, qr = benchmark.get(left), benchmark.get(right)
        if not all(x is not None for x in (sl, sr, ql, qr)):
            continue
        stock_r.append(sr['close'] / sl['close'] - 1.0)
        bench_r.append(qr['close'] / ql['close'] - 1.0)
    report['beta_pairs'] = len(stock_r)
    beta_min = int(cfg['beta_minimum_sessions'])
    if len(stock_r) >= beta_min:
        mx = sum(stock_r) / len(stock_r)
        mq = sum(bench_r) / len(bench_r)
        denom = sum((q - mq) ** 2 for q in bench_r)
        if denom > 0:
            raw = sum((sret - mx) * (q - mq) for sret, q in zip(stock_r, bench_r)) / denom
            lo, hi = map(float, cfg['beta_clip'])
            report.update(beta_available=True, beta_raw=raw, beta=max(lo, min(hi, raw)))
        else:
            report['beta_reason'] = 'zero_benchmark_variance'
    else:
        report['beta_reason'] = 'insufficient_prior_beta_pairs'

    atr_n = int(cfg['atr_lookback_sessions'])
    atr_days = [session_n_back(session, n) for n in range(atr_n + 1, 0, -1)]
    if any(d is None for d in atr_days) or any(d not in stock for d in atr_days):
        report.update(availability='UNAVAILABLE', reason='incomplete_prior_atr_window')
        return report
    assert prior is not None
    report['prior_close'] = stock[prior]['close']
    true_ranges: list[float] = []
    for left, right in zip(atr_days, atr_days[1:]):
        previous_close = stock[left]['close']
        row = stock[right]
        true_ranges.append(max(row['high'] - row['low'],
                               abs(row['high'] - previous_close),
                               abs(row['low'] - previous_close)))
    if len(true_ranges) != atr_n or any((not math.isfinite(x) or x <= 0) for x in true_ranges):
        report.update(availability='UNAVAILABLE', reason='invalid_prior_atr_window')
        return report
    report['atr_sessions'] = atr_n
    report['prior_atr'] = sum(true_ranges) / atr_n
    return report


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



def _matching_partition(session: date, cfg: dict) -> str | None:
    early_end = date.fromisoformat(str(cfg['early_partition_end']))
    late_start = date.fromisoformat(str(cfg['late_partition_start']))
    if session <= early_end:
        return 'early'
    if session >= late_start:
        return 'late'
    return None


def _aware_iso(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f'{field} must be an aware ISO datetime')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'{field} must be an aware ISO datetime') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f'{field} must be an aware ISO datetime')
    return parsed


def match_controls(
    selected_event: dict, *, selected_symbol: str,
    selected_session: str | date, selected_qqq_sign: int,
    control_census, config_bytes: bytes,
) -> dict:
    """Select the frozen v4 matched-control pool without reading future results.

    Controls are matched only on candidate-time covariates named in the v4
    preregistration.  The selected event's confirmation delay is copied onto each
    baseline anchor before the same processing latency is applied.  No widening
    fallback exists when the frozen minimum pool cannot be met.
    """
    if hashlib.sha256(config_bytes).hexdigest() != CONFIG_SHA256:
        raise ValueError('frozen v4 config identity mismatch')
    cfg = json.loads(config_bytes)
    required = ('candidate_at', 'confirmation_delay_bars', 'displacement_atr')
    if not isinstance(selected_event, dict) or any(k not in selected_event for k in required):
        raise ValueError('selected event missing frozen matching fields')
    if selected_qqq_sign not in (-1, 0, 1) or isinstance(selected_qqq_sign, bool):
        raise ValueError('selected QQQ sign must be -1, 0, or 1')
    if not isinstance(selected_symbol, str) or not selected_symbol:
        raise ValueError('selected symbol required')
    try:
        selected_day = (selected_session if isinstance(selected_session, date)
                        else date.fromisoformat(str(selected_session)))
    except ValueError as exc:
        raise ValueError('selected session must be ISO date') from exc
    partition = _matching_partition(selected_day, cfg)
    if partition is None:
        raise ValueError('selected session outside frozen partitions')
    candidate_at = _aware_iso(selected_event['candidate_at'], field='selected candidate_at')
    session_open, _session_close = session_window_et(selected_day)
    local_candidate = candidate_at.astimezone(session_open.tzinfo)
    if local_candidate.date() != selected_day:
        raise ValueError('selected event candidate/session mismatch')
    minute = local_candidate.hour * 60 + local_candidate.minute
    clock_bin = minute // int(cfg['clock_bin_minutes'])
    displacement = selected_event['displacement_atr']
    if not _number(displacement):
        raise ValueError('selected event displacement invalid')
    displacement_bucket = bisect_right(cfg['displacement_bucket_edges_atr'], float(displacement)) - 1
    delay = selected_event['confirmation_delay_bars']
    if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
        raise ValueError('selected event confirmation delay invalid')
    processing_minutes = int(cfg['execution_latency_minutes'])

    excluded: dict[str, int] = {}
    seen: set[str] = set()
    matched: list[dict] = []

    def reject(reason: str) -> None:
        excluded[reason] = excluded.get(reason, 0) + 1

    for raw in control_census:
        if not isinstance(raw, dict):
            reject('malformed')
            continue
        anchor_id = raw.get('anchor_id')
        if not isinstance(anchor_id, str) or not anchor_id:
            reject('malformed')
            continue
        if anchor_id in seen:
            reject('duplicate_identity')
            continue
        seen.add(anchor_id)
        try:
            control_day = date.fromisoformat(str(raw.get('session')))
            control_at = _aware_iso(raw.get('candidate_at'), field='control candidate_at')
        except (TypeError, ValueError):
            reject('malformed')
            continue
        if raw.get('symbol') != selected_symbol:
            reject('ticker')
            continue
        if control_day == selected_day:
            reject('same_date')
            continue
        if _matching_partition(control_day, cfg) != partition:
            reject('partition')
            continue
        if raw.get('clock_bin') != clock_bin:
            reject('clock_bin')
            continue
        if raw.get('displacement_bucket') != displacement_bucket:
            reject('displacement_bucket')
            continue
        if raw.get('qqq_open_to_decision_sign') != selected_qqq_sign:
            reject('market_sign')
            continue
        entry_at = control_at + timedelta(
            minutes=delay * 5 + processing_minutes)
        matched.append({
            'anchor_id': anchor_id,
            'candidate_at': _iso(control_at),
            'session': control_day.isoformat(),
            'symbol': selected_symbol,
            'clock_bin': clock_bin,
            'displacement_bucket': displacement_bucket,
            'qqq_open_to_decision_sign': selected_qqq_sign,
            'confirmation_delay_bars': delay,
            'processing_latency_minutes': processing_minutes,
            'entry_reference_at': _iso(entry_at),
            'entry_reference_state': 'scheduled_clock_only_not_a_fill',
        })

    matched.sort(key=lambda row: (row['session'], row['candidate_at'], row['anchor_id']))
    floor = int(cfg['matched_control_min_rows'])
    available = len(matched) >= floor
    return {
        'schema': 'mastermind.tti.r1b.matched_controls.v4',
        'study_id': cfg['study_id'], 'config_sha256': CONFIG_SHA256,
        'authority': 'research_matching_only', 'market_outcomes_computed': False,
        'fallback_used': False,
        'availability': 'AVAILABLE' if available else 'NO_CONTROL',
        'reason': None if available else 'matched_control_floor_not_met',
        'required_min_rows': floor, 'matched_count': len(matched),
        'selected': {
            'symbol': selected_symbol, 'session': selected_day.isoformat(),
            'candidate_at': _iso(candidate_at), 'partition': partition,
            'clock_bin': clock_bin, 'displacement_bucket': displacement_bucket,
            'qqq_open_to_decision_sign': selected_qqq_sign,
            'confirmation_delay_bars': delay,
            'processing_latency_minutes': processing_minutes,
        },
        'matched_controls': matched if available else [],
        'excluded_counts': dict(sorted(excluded.items())),
    }


def _exact_positive_path(frame: pd.DataFrame, start: datetime, end: datetime) -> tuple[str, list[tuple[float, ...]]]:
    """Exact [start,end) five-minute price-evidence path, no sort/fill/bridge."""
    if not isinstance(frame, pd.DataFrame) or any(c not in frame.columns for c in COLUMNS):
        return 'invalid', []
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None or frame.index.hasnans:
        return 'invalid', []
    expected = list(pd.date_range(start, end - BAR, freq=BAR)) if end > start else []
    rows = frame[(frame.index >= start) & (frame.index < end)]
    if len(rows) != len(expected) or list(rows.index) != expected or rows.index.has_duplicates:
        return 'missing', []
    values: list[tuple[float, ...]] = []
    for _, row in rows.iterrows():
        parsed = _row_values(row)
        if parsed is None or parsed[4] <= 0:
            return 'invalid', []
        values.append(parsed)
    return 'ok', values


def _touch_order(values: list[tuple[float, ...]], *, entry: float, atr: float, multiple: float) -> str:
    target = entry + multiple * atr
    adverse = entry - multiple * atr
    for o, h, low, _c, _v in values:
        hit_target = h >= target
        hit_adverse = low <= adverse
        if hit_target and hit_adverse:
            if o >= target:
                return 'target_first'
            if o <= adverse:
                return 'adverse_first'
            return 'same_bar_ambiguous'
        if hit_target:
            return 'target_first'
        if hit_adverse:
            return 'adverse_first'
    return 'neither'


def _lod_survival(frame: pd.DataFrame, *, start: datetime, close: datetime, low_anchor: float) -> tuple[str, bool | None]:
    state, values = _exact_positive_path(frame, start, close)
    if state != 'ok':
        return 'unavailable', None
    return 'available', not any(row[2] < low_anchor for row in values)


def measure_event_outcome(
    stock_frame: pd.DataFrame, benchmark_frame: pd.DataFrame, *, event: dict,
    session: date, horizon: str, beta: float | None, cost_bps: int,
    config_bytes: bytes,
) -> dict:
    """Measure one frozen v4 long event from its delayed price-reference entry.

    Corrected-history research only.  Missing path evidence censors the requested
    horizon rather than moving to a later bar.  Benchmark absence leaves the stock
    outcome measurable but beta residual unknown.  LOD diagnostics use their own
    through-close evidence and therefore may be unavailable while a shorter fixed
    horizon remains valid.
    """
    if hashlib.sha256(config_bytes).hexdigest() != CONFIG_SHA256:
        raise ValueError('frozen v4 config identity mismatch')
    cfg = json.loads(config_bytes)
    if horizon not in cfg['horizons']:
        raise ValueError('horizon outside frozen v4 grid')
    if cost_bps not in cfg['round_trip_cost_bps']:
        raise ValueError('cost outside frozen v4 grid')
    if not isinstance(event, dict) or event.get('selector') not in cfg['selectors']:
        raise ValueError('event outside frozen v4 selectors')
    for field in ('entry_reference_at', 'candidate_at', 'decision_at'):
        if field not in event:
            raise ValueError(f'event missing {field}')
    entry_at = _aware_iso(event['entry_reference_at'], field='entry_reference_at')
    candidate_at = _aware_iso(event['candidate_at'], field='candidate_at')
    decision_at = _aware_iso(event['decision_at'], field='decision_at')
    start, close = session_window_et(session)
    session_tz = start.tzinfo
    entry_at = entry_at.astimezone(session_tz)
    candidate_at = candidate_at.astimezone(session_tz)
    decision_at = decision_at.astimezone(session_tz)
    result = {
        'schema': 'mastermind.tti.r1b.outcome.v4',
        'study_id': cfg['study_id'], 'config_sha256': CONFIG_SHA256,
        'selector': event['selector'], 'anchor_id': event.get('anchor_id'),
        'session': session.isoformat(), 'horizon': horizon, 'cost_bps': int(cost_bps),
        'entry_reference_at': _iso(entry_at), 'status': 'censored', 'reason': None,
        'authority': 'retrospective_research_outcome_only',
        'historical_availability_proven': False, 'execution_proven': False,
        'may_rank': False, 'may_alert': False, 'may_size': False, 'may_trade': False,
        'entry_open': None, 'exit_close': None, 'raw_return': None, 'net_return': None,
        'benchmark_return': None, 'beta_residual': None, 'net_beta_residual': None,
        'mfe': None, 'mae': None, 'touch': None,
        'candidate_delay_atr': None, 'episode_delay_atr': None,
        'remaining_to_prior_close_atr': None,
        'lod_status': 'unavailable', 'candidate_lod_status': 'unavailable',
        'candidate_lod_survives': None, 'episode_lod_status': 'unavailable',
        'episode_lod_survives': None,
    }
    if not is_session(session) or close - start != timedelta(minutes=390):
        result['reason'] = 'normal_session_required'; return result
    if entry_at < start or entry_at >= close:
        result['reason'] = 'entry_outside_session'; return result
    elapsed = (entry_at - start).total_seconds()
    if elapsed % int(BAR.total_seconds()) != 0:
        result['reason'] = 'entry_off_session_grid'; return result
    latency = int(cfg['execution_latency_minutes'])
    if entry_at != decision_at + timedelta(minutes=latency):
        result['reason'] = 'entry_clock_mismatch'; return result
    if candidate_at > decision_at:
        result['reason'] = 'candidate_after_decision'; return result
    atr = event.get('prior_atr'); previous_close = event.get('previous_regular_close')
    candidate_low = event.get('candidate_low'); episode_low = event.get('episode_low')
    if not all(_number(x) and float(x) > 0 for x in (atr, previous_close, candidate_low, episode_low)):
        result['reason'] = 'invalid_event_normalization'; return result
    atr = float(atr); previous_close=float(previous_close); candidate_low=float(candidate_low); episode_low=float(episode_low)
    if horizon == 'close':
        path_end = close
    else:
        try:
            minutes = int(horizon[:-1])
        except (TypeError, ValueError):
            raise ValueError('invalid frozen horizon')
        path_end = entry_at + timedelta(minutes=minutes)
        if path_end > close:
            result['reason'] = 'horizon_after_session_close'; return result
    state, stock_values = _exact_positive_path(stock_frame, entry_at, path_end)
    if state == 'missing':
        result['reason'] = 'stock_path_missing_or_ambiguous'; return result
    if state != 'ok':
        result['reason'] = 'stock_path_invalid'; return result
    entry_open = stock_values[0][0]
    exit_close = stock_values[-1][3]
    raw = exit_close / entry_open - 1.0
    cost = int(cost_bps) / 10000.0
    result.update(status='available', reason=None, entry_open=entry_open, exit_close=exit_close,
                  raw_return=raw, net_return=raw-cost,
                  mfe=max(v[1] for v in stock_values)/entry_open-1.0,
                  mae=min(v[2] for v in stock_values)/entry_open-1.0,
                  touch=_touch_order(stock_values, entry=entry_open, atr=atr,
                                     multiple=float(cfg['local_touch_atr'])),
                  candidate_delay_atr=(entry_open-candidate_low)/atr,
                  episode_delay_atr=(entry_open-episode_low)/atr,
                  remaining_to_prior_close_atr=(previous_close-entry_open)/atr)
    bstate, bvalues = _exact_positive_path(benchmark_frame, entry_at, path_end)
    if bstate == 'ok':
        benchmark_return = bvalues[-1][3] / bvalues[0][0] - 1.0
        result['benchmark_return'] = benchmark_return
        if beta is not None and _number(beta) and 0 <= float(beta) <= 3:
            residual = raw - float(beta) * benchmark_return
            result['beta_residual'] = residual
            result['net_beta_residual'] = residual - cost
    cstate, csurvives = _lod_survival(stock_frame, start=candidate_at, close=close,
                                      low_anchor=candidate_low)
    estate, esurvives = _lod_survival(stock_frame, start=decision_at, close=close,
                                      low_anchor=episode_low)
    result['candidate_lod_status'] = cstate
    result['candidate_lod_survives'] = csurvives
    result['episode_lod_status'] = estate
    result['episode_lod_survives'] = esurvives
    if cstate == 'available' and estate == 'available':
        result['lod_status'] = 'available'
    return result
