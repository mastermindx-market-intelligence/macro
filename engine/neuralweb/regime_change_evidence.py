"""Qualify the recorded-change lobe at the existing world-state read boundary.

No new transition ledger, scorer or history reconstruction. Other world-state
blocks remain byte-content equivalent; this module does not certify them.
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from engine.neuralweb.mechanism_evidence import (
    MAX_SOURCE_BYTES, _number, _reject_constant, _token, _unique,
)

SOURCE_PATH = 'data/neuralweb/world_state.json'
# The existing world-state artifact's registered SLA, pinned by a contract test.
WORLD_STATE_SLA_HOURS = 30
MAX_INPUT_RECORDS = 512
MAX_RETURNED_RECORDS = 20


def _source_clock(raw: Any, now: datetime) -> dict:
    out = {'as_of': None, 'reading_status': 'unknown_date', 'age_hours': None,
           'clock_semantics': 'world_state_build_time_not_market_event_time'}
    if not isinstance(raw, str):
        return out
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
            # A future day is certainly after the cutoff even without an instant.
            # A past date alone cannot stand in for the producer's UTC build time.
            if date.fromisoformat(raw) > now.date():
                out.update(as_of=raw, reading_status='future_dated')
            return out
        value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if value.tzinfo is None:
            return out
        value = value.astimezone(timezone.utc)
        age = (now - value).total_seconds() / 3600
        out.update(as_of=value.isoformat(), age_hours=age,
                   reading_status='future_dated' if value > now else 'stale' if age > WORLD_STATE_SLA_HOURS else 'available')
    except (ValueError, OverflowError):
        pass
    return out


def _label(value: Any) -> tuple[bool, Any]:
    if value is None or isinstance(value, bool):
        return True, value
    if isinstance(value, str):
        # Do not truncate distinct source labels into an apparent duplicate.
        return len(value) <= 180 and all(ord(c) >= 32 for c in value), value
    number = _number(value)
    return number is not None, number


def qualify_world_state(payload: Any, *, now: datetime) -> dict:
    """Qualify only macro_deltas; never derive a new current regime or forecast."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError('timezone-aware observation time required')
    now = now.astimezone(timezone.utc)
    if not isinstance(payload, dict):
        return {'error': 'world_state unavailable', 'reading_status': 'unavailable'}
    out = copy.deepcopy(payload)
    if 'macro_deltas' not in payload:
        return out  # a legacy artifact acquires no invented history
    original = payload.get('macro_deltas')
    original = original if isinstance(original, dict) else {}
    source = _source_clock(payload.get('produced_at'), now)
    cutoff = now.date() - timedelta(days=14)
    excluded = {key: 0 for key in ('invalid_record', 'future_dated', 'after_source_snapshot',
                                  'outside_window', 'duplicate_record', 'unchanged_record')}
    d = {
        'display_only': True, 'transitions': None, 'n_transitions_14d': None,
        'owner_reported_count': None, 'count_semantics': 'retained_records_not_total_market_changes',
        'reading_status': source['reading_status'], 'source_snapshot': source,
        'window_start': cutoff.isoformat(), 'window_end': now.date().isoformat(),
        'coverage_complete': False, 'event_time_verified': False,
        'record_date_semantics': 'aggregate_snapshot_max_source_date_not_field_event_time',
        'historical_replay_eligible': False, 'excluded': excluded, 'omitted_records': 0,
        'note': ('Recorded owner-label changes only. This source already retains a subset of its ledger. '
                 'Empty output does not establish no market changes; dates are not event onset or forecast issuance. '
                 'This qualification applies only to macro_deltas, not the other world-state blocks.'),
    }
    out['macro_deltas'] = d
    count = original.get('n_transitions_14d')
    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
        d['owner_reported_count'] = count
    if source['reading_status'] in ('unknown_date', 'future_dated'):
        return out
    rows = original.get('transitions')
    if not isinstance(rows, list):
        d['reading_status'] = 'unavailable'
        return out
    if len(rows) > MAX_INPUT_RECORDS:
        d['reading_status'] = 'unavailable'
        d['reason'] = 'projection_exceeds_record_limit'
        return out
    snapshot_day = date.fromisoformat(source['as_of'][:10])
    selected = []
    seen = set()
    for r in rows:
        if not isinstance(r, dict):
            excluded['invalid_record'] += 1; continue
        try:
            stamp = r.get('asof')
            if not isinstance(stamp, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', stamp):
                raise ValueError('recorded date required')
            day = date.fromisoformat(stamp)
            domain, field = _token(r.get('domain')), _token(r.get('field'))
            valid_from, before = _label(r.get('from'))
            valid_to, after = _label(r.get('to'))
            if not domain or not field or not valid_from or not valid_to or 'from' not in r or 'to' not in r:
                raise ValueError('recorded fields required')
        except (ValueError, TypeError):
            excluded['invalid_record'] += 1; continue
        if day > now.date():
            excluded['future_dated'] += 1; continue
        if day > snapshot_day:
            excluded['after_source_snapshot'] += 1; continue
        if day < cutoff:
            excluded['outside_window'] += 1; continue
        if type(before) is type(after) and before == after:
            excluded['unchanged_record'] += 1; continue
        identity = json.dumps([stamp, domain, field, before, after], ensure_ascii=True, separators=(',', ':'))
        if identity in seen:
            excluded['duplicate_record'] += 1; continue
        seen.add(identity)
        selected.append({'asof': stamp, 'domain': domain, 'field': field, 'from': before, 'to': after,
                         'within_day_order_verified': False,
                         'recorded_policy_label_not_instruction': field.endswith('_action')})
    groups = Counter((r['asof'], r['domain'], r['field']) for r in selected)
    for r in selected:
        r['same_day_field_ambiguous'] = groups[(r['asof'], r['domain'], r['field'])] > 1
    selected.sort(key=lambda r: (-date.fromisoformat(r['asof']).toordinal(), r['domain'], r['field'],
                                json.dumps([r['from'], r['to']], ensure_ascii=True)))
    d['omitted_records'] = max(0, len(selected) - MAX_RETURNED_RECORDS)
    d['transitions'] = selected[:MAX_RETURNED_RECORDS]
    d['n_transitions_14d'] = len(d['transitions'])
    return out


def read_world_state_evidence(root: Path, *, now: datetime | None = None) -> dict:
    """Read the same world-state file once; no fallback, producer or network."""
    observed = now or datetime.now(timezone.utc)
    try:
        with (Path(root) / SOURCE_PATH).open('rb') as stream:
            data = stream.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            return {'error': 'world_state exceeds read limit', 'reading_status': 'unavailable'}
        payload = json.loads(data, object_pairs_hook=_unique, parse_constant=_reject_constant)
        return qualify_world_state(payload, now=observed)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        return {'error': 'world_state unavailable', 'reading_status': 'unavailable'}
