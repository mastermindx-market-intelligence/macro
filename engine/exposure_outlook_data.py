"""Read-only eligibility audit of the existing options surface replay store.

No collector, repair, publication, model promotion, or inventory inference lives here.
Follow the canonical dated index, never directory glob order. Declared timestamps are
checked for consistency but are not proof of historical availability or calibration.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, time, timezone
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
_ROOT = re.compile(r'[A-Z0-9]{1,10}(?:[.-][A-Z0-9]{1,4})?\Z')
_STAMP = re.compile(r'(?:[01][0-9]|2[0-3])[0-5][0-9]\Z')
_CLOCK = re.compile(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z')
_QUALIFICATION = 'INTRADAY_TRAINING_CORPUS_NOT_QUALIFIED'


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError('timestamp must be an ISO-8601 string with timezone')
    try:
        out = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid ISO-8601 timestamp') from exc
    if out.tzinfo is None or out.utcoffset() is None:
        raise ValueError('timestamp must include timezone')
    return out.astimezone(timezone.utc)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _gaps(values: list[datetime]) -> dict[str, float | None]:
    gaps = [(b - a).total_seconds() for a, b in zip(values, values[1:])]
    return {'median': median(gaps) if gaps else None, 'max': max(gaps) if gaps else None,
            'min': min(gaps) if gaps else None}


def audit_surface_session(
    surface_dir: str | Path, root: str, session: str, *, as_of: str,
    max_gap_seconds: int = 300, max_file_bytes: int = 16 * 1024 * 1024,
    layout: str = 'dated', max_session_bytes: int = 64 * 1024 * 1024,
) -> dict[str, Any]:
    """Audit root/date/idx.json and only its referenced frames, without writing.

    ``layout=current`` explicitly audits the legacy root/idx.json stage, still
    requiring its exact session identity. It is never a dated-history fallback.
    ``as_of`` is the requested knowledge cutoff, not filesystem modification time.
    ``max_gap_seconds`` is a caller-declared audit tolerance, not a vendor guarantee.
    ``forecast_eligible`` intentionally stays false: this source audit cannot qualify
    a training corpus or a model. ``source_integrity`` describes only checked inputs.
    """
    if not isinstance(root, str) or not _ROOT.fullmatch(root) or len(root) > 12:
        raise ValueError('invalid option root')
    if not isinstance(session, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', session):
        raise ValueError('invalid session date')
    day = date.fromisoformat(session)
    cutoff = _timestamp(as_of)
    if (not isinstance(max_gap_seconds, int) or isinstance(max_gap_seconds, bool)
            or max_gap_seconds <= 0 or not isinstance(max_file_bytes, int)
            or isinstance(max_file_bytes, bool) or max_file_bytes <= 0
            or not isinstance(max_session_bytes, int) or isinstance(max_session_bytes, bool)
            or max_session_bytes <= 0):
        raise ValueError('read and gap limits must be positive integers')
    if layout not in ('dated', 'current'):
        raise ValueError('layout must be dated or current; no silent fallback')
    base = Path(surface_dir).resolve()
    folder = base / root / session if layout == 'dated' else base / root
    reasons: Counter[str] = Counter()
    evidence: list[dict[str, Any]] = []
    bytes_read = 0
    result: dict[str, Any] = {
        'schema': 'options.exposure_outlook.source_audit/v1', 'root': root,
        'session': session, 'layout': layout, 'cutoff': cutoff.isoformat(), 'authority_tier': 'research',
        'indexed_frames': 0, 'readable_frames': 0, 'consistent_frames': 0,
        'nominal_cadence_seconds': None, 'observed_cadence_seconds': _gaps([]),
        'source_cadence_seconds': _gaps([]), 'max_gap_tolerance_seconds': max_gap_seconds,
        'forecast_eligible': False, 'source_integrity': 'inconsistent',
        'availability_proven': False, 'evidence': evidence, 'frame_findings': [],
    }

    def finish() -> dict[str, Any]:
        result['source_integrity'] = 'consistent' if not reasons else 'inconsistent'
        reasons[_QUALIFICATION] += 1
        result['reason_codes'] = sorted(reasons)
        result['reason_counts'] = dict(sorted(reasons.items()))
        return result

    def read(name: str, missing_code: str) -> dict[str, Any] | None:
        nonlocal bytes_read
        if bytes_read >= max_session_bytes:
            reasons['SESSION_SIZE_LIMIT'] += 1
            return None
        path = folder / name
        # Refuse symlinks anywhere in the selected source chain, including folder.
        if any(p.is_symlink() for p in (base / root, folder, path)):
            reasons['UNSAFE_SOURCE_PATH'] += 1
            return None
        try:
            with path.open('rb') as stream:
                raw = stream.read(min(max_file_bytes, max_session_bytes - bytes_read) + 1)
            bytes_read += len(raw)
            if bytes_read > max_session_bytes:
                reasons['SESSION_SIZE_LIMIT'] += 1
                return None
            if len(raw) > max_file_bytes:
                reasons['SOURCE_SIZE_LIMIT'] += 1
                return None
            evidence.append({'path': str(path.relative_to(base)), 'bytes': len(raw),
                             'sha256': hashlib.sha256(raw).hexdigest()})
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError('expected JSON object')
            return obj
        except FileNotFoundError:
            reasons[missing_code] += 1
        except (UnicodeError, ValueError):
            reasons['INVALID_INDEX' if name == 'idx.json' else 'INVALID_FRAME'] += 1
        except OSError:
            reasons['SOURCE_READ_ERROR'] += 1
        return None

    index = read('idx.json', 'MISSING_INDEX')
    if index is None:
        return finish()
    stamps = index.get('stamps')
    if (index.get('root') != root or index.get('date') != session
            or not isinstance(stamps, list) or not stamps or len(stamps) > 1440
            or not all(isinstance(s, str) and _STAMP.fullmatch(s) for s in stamps)
            or stamps != sorted(set(stamps)) or index.get('latest') != stamps[-1]):
        reasons['INVALID_INDEX'] += 1
        return finish()
    nominal = index.get('pollFloorSec', index.get('cadenceSec'))
    if _number(nominal) and nominal > 0:
        result['nominal_cadence_seconds'] = nominal
    else:
        reasons['NOMINAL_CADENCE_MISSING'] += 1
    try:
        index_time = _timestamp(index.get('asof'))
        if index_time > cutoff:
            reasons['INDEX_AFTER_CUTOFF'] += 1
    except ValueError:
        reasons['INDEX_TIME_MISSING'] += 1
    result['indexed_frames'] = len(stamps)
    label_times = [datetime.combine(day, time(int(s[:2]), int(s[2:])), ET) for s in stamps]
    result['observed_cadence_seconds'] = _gaps(label_times)
    if len(stamps) < 2:
        reasons['INSUFFICIENT_OBSERVATIONS'] += 1
    elif result['observed_cadence_seconds']['max'] > max_gap_seconds:
        reasons['SPARSE_OBSERVATIONS'] += 1
    source_times = []
    for stamp, label_time in zip(stamps, label_times):
        frame = read(f'{stamp}.json', 'MISSING_FRAME')
        if frame is None:
            continue
        result['readable_frames'] += 1
        before = sum(reasons.values())
        prior_reasons = reasons.copy()
        if frame.get('root') != root or frame.get('session_date') != session:
            reasons['IDENTITY_MISMATCH'] += 1
        try:
            source_time = _timestamp(frame.get('asof'))
            source_times.append(source_time)
            if source_time > cutoff:
                reasons['FRAME_AFTER_CUTOFF'] += 1
            if source_time.astimezone(ET).date() != day:
                reasons['IDENTITY_MISMATCH'] += 1
            if label_time > source_time:
                reasons['FRAME_TIME_AFTER_ASOF'] += 1
        except ValueError:
            reasons['FRAME_SOURCE_TIME_MISSING'] += 1
            source_time = None
        published = frame.get('published_at')
        if published is None:
            reasons['PUBLICATION_TIME_MISSING'] += 1
        else:
            try:
                publication_time = _timestamp(published)
                if source_time is not None and publication_time < source_time:
                    reasons['PUBLICATION_BEFORE_SOURCE'] += 1
                if publication_time > cutoff:
                    reasons['PUBLICATION_AFTER_CUTOFF'] += 1
            except ValueError:
                reasons['PUBLICATION_TIME_INVALID'] += 1
        prices, times, grids = (frame.get(k) for k in ('price_levels', 'time_steps', 'grids'))
        axes_valid = (
            isinstance(prices, list) and bool(prices)
            and all(_number(v) and v > 0 for v in prices)
            and all(a < b for a, b in zip(prices, prices[1:]))
            and isinstance(times, list) and bool(times) and len(times) <= 1440
            and all(isinstance(v, str) and _CLOCK.fullmatch(v) for v in times)
            and times == sorted(set(times))
        )
        if axes_valid:
            if times[-1].replace(':', '') != stamp:
                reasons['STAMP_COLUMN_MISMATCH'] += 1
            column_time = datetime.combine(day, time.fromisoformat(times[-1]), ET)
            if source_time is not None and column_time > source_time:
                reasons['FRAME_TIME_AFTER_ASOF'] += 1
        grid = grids.get('gex') if isinstance(grids, dict) else None
        grid_valid = (
            axes_valid and isinstance(grid, list) and len(grid) == len(prices)
            and all(isinstance(row, list) and len(row) == len(times)
                    and all(_number(v) for v in row) for row in grid)
        )
        invalid_fields = []
        if not axes_valid:
            invalid_fields.append('axes')
        if not grid_valid:
            invalid_fields.append('gex_grid')
        if not _number(frame.get('spot')) or frame['spot'] <= 0:
            invalid_fields.append('spot')
        if invalid_fields:
            reasons['INVALID_FRAME'] += 1
        if not isinstance(grids, dict) or 'gex' not in grids:
            reasons['GEX_UNAVAILABLE'] += 1
        # A numerically valid zero grid can be padding after a cycle supplied
        # no Greeks. Coverage's denominator is the quoted-strike union, not
        # the full chain, so even 1.0 cannot establish full-inventory coverage.
        coverage = frame.get('coverage')
        fraction = coverage.get('greeks') if isinstance(coverage, dict) else None
        if not _number(fraction) or not 0 <= fraction <= 1:
            reasons['GEX_COVERAGE_NOT_VALID'] += 1
            fraction = None
        elif fraction == 0:
            reasons['GEX_NO_CONTRIBUTING_STRIKES'] += 1
        result['frame_findings'].append({
            'stamp': stamp, 'source_asof': frame.get('asof'),
            'reported_greek_coverage': fraction,
            'coverage_scope': 'quoted_strike_union_not_full_chain',
            'invalid_fields': invalid_fields,
            'reason_codes': sorted(code for code, count in reasons.items()
                                   if count > prior_reasons[code]),
        })
        if sum(reasons.values()) == before:
            result['consistent_frames'] += 1
    result['source_cadence_seconds'] = _gaps(source_times)
    if any(b <= a for a, b in zip(source_times, source_times[1:])):
        reasons['NON_ADVANCING_SOURCE_CLOCK'] += 1
    if (len(source_times) > 1
            and result['source_cadence_seconds']['max'] > max_gap_seconds):
        reasons['SPARSE_SOURCE_OBSERVATIONS'] += 1
    return finish()
