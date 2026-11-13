"""Validate a PROPOSED research envelope's shape and necessary consistency.

This does not resolve/authenticate references, validate market-data rights,
recompute reported metrics, accept a native interface, or prove production use.
The fixtures deliberately use unverified fixture:* references.
"""
from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'contracts/factor_read_model.v0.schema.json'


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('NONFINITE_JSON_CONSTANT:'+value)


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('NONFINITE_JSON_NUMBER')
    if isinstance(value, dict):
        for item in value.values(): _finite(item)
    elif isinstance(value, list):
        for item in value: _finite(item)


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text[:-1]+'+00:00')


def _metric_consistency(metric: dict[str, Any]):
    c = metric['coverage']
    eligible, observed, fraction = c['eligible_count'], c['observed_count'], c['count_fraction']
    if eligible is not None and observed is not None:
        if observed > eligible:
            raise ValueError('OBSERVED_COUNT_EXCEEDS_ELIGIBLE')
        if eligible == 0:
            if fraction is not None:
                raise ValueError('EMPTY_DENOMINATOR_IS_NOT_ZERO_FRACTION')
        elif fraction is None or abs(fraction-observed/eligible) > 1e-12:
            raise ValueError('COUNT_COVERAGE_MISMATCH')
    elif fraction is not None:
        raise ValueError('UNKNOWN_DENOMINATOR_HAS_NO_COVERAGE_FRACTION')
    for field in ['requested_window', 'actual_window']:
        window = metric[field]
        if (window['start'] is None) != (window['end'] is None):
            raise ValueError('HALF_SPECIFIED_METRIC_WINDOW')
        if window['start'] is not None and _instant(window['end']) < _instant(window['start']):
            raise ValueError('REVERSED_METRIC_WINDOW')


def validate_json(text: str) -> dict[str, Any]:
    result = json.loads(text, object_pairs_hook=_object, parse_constant=_reject_constant)
    _finite(result)
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(result)
    except ValidationError as exc:
        raise ValueError('CANDIDATE_SCHEMA_REJECTED:'+exc.message) from exc
    mode = result['request']['history_mode']
    cutoff = _instant(result['request']['measurement_cutoff'])
    previous_end = None
    for point in result['observations']:
        start, end = _instant(point['interval_start']), _instant(point['interval_end'])
        if end <= start or (previous_end is not None and start < previous_end):
            raise ValueError('NONPOSITIVE_OR_OVERLAPPING_INTERVAL')
        if end > cutoff:
            raise ValueError('OUTCOME_AFTER_MEASUREMENT_CUTOFF')
        previous_end = end
        if mode.startswith('PIT_'):
            if point['selection_cutoff'] is None or point['membership_revision_ref'] is None:
                raise ValueError('PIT_SELECTION_AND_MEMBERSHIP_REFERENCE_REQUIRED')
            if _instant(point['selection_cutoff']) >= start:
                raise ValueError('PIT_SELECTION_MUST_PRECEDE_HOLDING_INTERVAL')
        for field in ['return', 'index_level']:
            metric = point[field]
            _metric_consistency(metric)
            if result['status'] == 'READY' and metric['status'] != 'READY':
                raise ValueError('READY_ENVELOPE_HAS_UNAVAILABLE_PRIMARY_POINT')
        if (result['series_spec']['measurement_kind'] == 'portfolio_index'
                and point['return']['status'] == 'READY'
                and point['return']['coverage']['weight_fraction'] != 1):
            raise ValueError('READY_PORTFOLIO_RETURN_NEEDS_COMPLETE_VALUED_WEIGHT')
    for metric in result['metrics'].values():
        _metric_consistency(metric)
    calculation = result['calculation']
    if calculation['supersedes_ref'] is not None and not (calculation['correction_reason'] or '').strip():
        raise ValueError('SUPERSEDING_REVISION_NEEDS_REASON')
    if result['status'] in ['READY', 'PARTIAL']:
        spec, refs = result['series_spec'], result['owner_receipt_refs']
        if spec['return_kind'] == 'TOTAL' and spec['price_basis'] not in ['tradj', 'raw']:
            raise ValueError('TOTAL_RETURN_BASIS_UNQUALIFIED')
        if spec['measurement_kind'] == 'portfolio_index':
            if not all(refs[name] for name in ['membership','identity','prices','actions','rights','calendar']):
                raise ValueError('PORTFOLIO_SOURCE_REFERENCE_MISSING')
    return result
