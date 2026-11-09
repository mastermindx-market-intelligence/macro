"""Constituent evidence for the incumbent rate-futures collector and RIC.

Measurement only. No fetching, archive, scheduling, forecast or trade authority.
The shared store retains latest vintages, not historical first-known receipts.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path

import pandas as pd

SCHEMA = 'rate_futures.constituents.v1'
TOKEN = '_constituents_token'
FAMILIES = {'ZQ': ('EFFR', 'monthly'), 'SR3': ('SOFR', 'quarterly')}
WEIGHT_BASIS = 'legacy_whole_month_centres.v1'
QUOTE_KIND = 'provider_daily_Close_unverified_exchange_settlement'
AUTHORITY = {'display_only': True, 'authority': False, 'can_score': False,
             'can_rank': False, 'can_size': False, 'can_gate': False, 'can_trade': False}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _stamp(value):
    out = pd.Timestamp(value)
    if pd.isna(out) or out.tz is None:
        raise ValueError('timezone_aware_capture_required')
    return out.tz_convert('UTC')


def _number(value):
    if isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError('nonfinite_or_boolean_number')
    return float(value)


def reference_period(root: str, year: int, month: int) -> tuple[str, str]:
    if root not in FAMILIES or type(year) is not int or type(month) is not int:
        raise ValueError('unsupported_contract_identity')
    start = date(year, month, 1)
    if root == 'ZQ':
        end = date(year + month // 12, month % 12 + 1, 1)
    else:
        start += timedelta(days=(2 - start.weekday()) % 7 + 14)
        end = date(year + (month + 2) // 12, (month + 2) % 12 + 1, 1)
        end += timedelta(days=(2 - end.weekday()) % 7 + 14)
    return start.isoformat(), end.isoformat()


def _daily_frame(frame):
    idx = frame.index
    if (not isinstance(idx, pd.DatetimeIndex) or idx.hasnans or not idx.is_unique
            or idx.tz is not None or not idx.equals(idx.normalize())
            or not frame.columns.is_unique):
        raise ValueError('invalid_daily_source_grid')
    return frame.sort_index()


def attach_constituents(path, components, contracts, symbols, *, root, cadence,
                        max_months, captured_at):
    """One same-download companion, persisted by the existing adapter/store.

    The numeric token is exactly representable as a float and binds both files.
    It detects torn generations; it is NOT authentication or a historical receipt.
    """
    if root not in FAMILIES or FAMILIES[root][1] != cadence:
        raise ValueError('incompatible_rate_family')
    capture = _stamp(captured_at)
    capture_day = capture.tz_convert('America/New_York').date()
    path = _daily_frame(path).copy()
    records, tokens = [], []
    for stamp, row in path.iterrows():
        quotes = {}
        for (year, month), series in contracts.items():
            if stamp not in series.index or pd.isna(series.loc[stamp]):
                continue
            price = _number(series.loc[stamp])
            quotes[f'{year:04d}-{month:02d}'] = {
                'provider_symbol': symbols[(year, month)], 'price': price,
                'implied_rate': 100.0 - price,
                'reference_period': list(reference_period(root, year, month))}
        payload = {'schema': SCHEMA, 'root': root, 'rate_family': FAMILIES[root][0],
            'cadence': cadence, 'max_months': max_months,
            'horizons_m': [int(c[1:]) for c in path.columns],
            'weight_basis': WEIGHT_BASIS, 'quote_kind': QUOTE_KIND,
            'observation_date': str(stamp.date()), 'captured_at': capture.isoformat(),
            'publisher_available_at': None, 'historical_availability_qualified': False,
            'prior_calendar_day_at_capture': stamp.date() < capture_day,
            'path': {c: None if pd.isna(v) else _number(v) for c, v in row.items()},
            'components': components[stamp], 'quotes': quotes}
        digest = sha256(_json(payload).encode()).hexdigest()
        token = int(digest[:13], 16)
        records.append(_json({'payload': payload, 'sha256': digest}))
        tokens.append(token)
    path[TOKEN] = tokens
    evidence = pd.DataFrame({'snapshot_json': records, TOKEN: tokens}, index=path.index)
    return path, evidence


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate_snapshot_key')
        out[key] = value
    return out


def _validated_snapshot(raw, numeric_row, evidence_token, observation, root):
    from collectors.rate_futures import implied_path_with_components, _MONTH_CODE
    wrapper = json.loads(raw, object_pairs_hook=_unique_object)
    payload = wrapper['payload']
    digest = sha256(_json(payload).encode()).hexdigest()
    if digest != wrapper['sha256']:
        raise ValueError('snapshot_digest_mismatch')
    token = int(digest[:13], 16)
    if _number(numeric_row[TOKEN]) != token or _number(evidence_token) != token:
        raise ValueError('generation_mismatch')
    if (payload['schema'] != SCHEMA or payload['root'] != root
            or payload['rate_family'] != FAMILIES[root][0]
            or payload['cadence'] != FAMILIES[root][1]
            or payload['weight_basis'] != WEIGHT_BASIS or payload['quote_kind'] != QUOTE_KIND
            or payload['historical_availability_qualified'] is not False
            or payload['publisher_available_at'] is not None):
        raise ValueError('unsupported_source_semantics')
    if payload['observation_date'] != str(observation.date()):
        raise ValueError('observation_date_mismatch')
    capture = _stamp(payload['captured_at'])
    prior_day = observation.date() < capture.tz_convert('America/New_York').date()
    if payload['prior_calendar_day_at_capture'] is not prior_day:
        raise ValueError('inconsistent_capture_completion_rule')
    horizons = payload['horizons_m']
    if (not isinstance(horizons, list) or not horizons
            or any(type(h) is not int or h < 1 for h in horizons)
            or len(set(horizons)) != len(horizons)
            or type(payload['max_months']) is not int or payload['max_months'] < 1):
        raise ValueError('invalid_path_coordinates')
    contracts = {}
    for key, quote in payload['quotes'].items():
        year, month = (int(v) for v in key.split('-'))
        prefix = f'{root}{_MONTH_CODE[month]}{year % 100:02d}.'
        if (key != f'{year:04d}-{month:02d}'
                or not quote['provider_symbol'].startswith(prefix)
                or quote['reference_period'] != list(reference_period(root, year, month))
                or abs(_number(quote['implied_rate']) - (100 - _number(quote['price']))) > 1e-10):
            raise ValueError('inconsistent_contract_identity_or_rate')
        contracts[(year, month)] = pd.Series([quote['price']], index=[observation])
    expected, expected_components = implied_path_with_components(
        contracts, horizons, payload['max_months'], payload['cadence'])
    if expected.empty or payload['components'] != expected_components[observation]:
        raise ValueError('constituent_weights_do_not_reproduce_path')
    expected_values = {c: None if pd.isna(v) else float(v)
                       for c, v in expected.iloc[0].items()}
    if _json(expected_values) != _json(payload['path']):
        raise ValueError('snapshot_path_mismatch')
    columns = [c for c in numeric_row.index if c.startswith('m') and c[1:].isdigit()]
    if set(columns) != set(expected_values):
        raise ValueError('path_horizon_mismatch')
    for column, value in expected_values.items():
        stored = None if pd.isna(numeric_row[column]) else _number(numeric_row[column])
        if value != stored:
            raise ValueError('published_path_mismatch')
        weights = payload['components'][column]['weights']
        reconstructed = sum(w * payload['quotes'][k]['implied_rate'] for k, w in weights.items())
        if value is not None and abs(value - reconstructed) > 0.000051:
            raise ValueError('weighted_rate_does_not_reproduce_path')
    return payload, digest


def _horizon_change(previous, current, horizon):
    out = {'status': 'unavailable', 'reason': None, 'raw_change_bp': None,
           'matched_contract_change_bp': None, 'roll_change_bp': None,
           'rounding_residual_bp': None, 'forward_reference_only': None,
           'matched_previous_weight': None, 'matched_current_weight': None}
    a, b = previous['components'][horizon], current['components'][horizon]
    if a['status'] not in ('exact', 'interpolated') or b['status'] not in ('exact', 'interpolated'):
        return dict(out, reason='unbracketed_horizon')
    wa, wb = a['weights'], b['weights']
    union = set(wa) | set(wb)
    qa, qb = previous['quotes'], current['quotes']
    matched = {key for key in union if key in qa and key in qb
               and qa[key]['provider_symbol'] == qb[key]['provider_symbol']
               and qa[key]['reference_period'] == qb[key]['reference_period']}
    out.update(matched_previous_weight=sum(wa.get(k, 0) for k in matched),
               matched_current_weight=sum(wb.get(k, 0) for k in matched))
    if matched != union:
        return dict(out, reason='incomplete_matched_components', missing_components=sorted(union - matched))
    if any(qb[k]['reference_period'][1] <= current['observation_date'] for k in union):
        return dict(out, reason='expired_component')
    repricing = sum((wa.get(k, 0) + wb.get(k, 0)) / 2 *
                    (qb[k]['implied_rate'] - qa[k]['implied_rate']) for k in union) * 100
    roll = sum((qa[k]['implied_rate'] + qb[k]['implied_rate']) / 2 *
               (wb.get(k, 0) - wa.get(k, 0)) for k in union) * 100
    raw = (current['path'][horizon] - previous['path'][horizon]) * 100
    residual = raw - repricing - roll
    # Finite source numbers do not guarantee finite products, sums or bp scaling.
    # Withhold the entire attribution rather than publish Infinity/NaN as available.
    if not all(math.isfinite(value) for value in (raw, repricing, roll, residual)):
        return dict(out, reason='nonfinite_derived_attribution')
    return dict(out, status='available', raw_change_bp=raw,
                matched_contract_change_bp=repricing, roll_change_bp=roll,
                rounding_residual_bp=residual,
                forward_reference_only=all(qb[k]['reference_period'][0] >
                                           current['observation_date'] for k in union),
                causal_policy_shock=False)


def _from_frames(path, evidence, root, asof, evaluated_at):
    out = {'status': 'unavailable', 'reason': None, 'rate_family': FAMILIES[root][0],
           'horizons': {}, 'historical_availability_qualified': False, **AUTHORITY}
    try:
        cut = pd.Timestamp(asof)
        if pd.isna(cut) or cut.tz is not None or cut != cut.normalize():
            return dict(out, reason='invalid_daily_cut')
        evaluation_day = evaluated_at.tz_convert('America/New_York').date()
        if cut.date() > evaluation_day:
            return dict(out, reason='decision_cut_in_future')
        eligible = path.loc[:cut]
        if eligible.empty:
            return dict(out, reason='future_source')
        if len(eligible) < 2:
            return dict(out, reason='insufficient_endpoints')
        selected = eligible.iloc[-2:]
        # A backdated board input must not make an old source look current.
        if (evaluation_day - selected.index[-1].date()).days > 5:
            return dict(out, reason='stale_source')
        if (selected.index[-1] - selected.index[0]).days > 5:
            return dict(out, reason='unqualified_observation_gap')
        snapshots, digests = [], []
        for observation, numeric in selected.iterrows():
            if observation not in evidence.index:
                return dict(out, reason='missing_constituents_endpoint')
            companion = evidence.loc[observation]
            payload, digest = _validated_snapshot(companion['snapshot_json'], numeric,
                companion[TOKEN], observation, root)
            if _stamp(payload['captured_at']) > evaluated_at:
                return dict(out, reason='capture_after_decision')
            if not payload['prior_calendar_day_at_capture']:
                return dict(out, reason='capture_may_include_incomplete_bar')
            snapshots.append(payload)
            digests.append(digest)
        previous, current = snapshots
        for field in ('horizons_m', 'max_months', 'weight_basis', 'quote_kind'):
            if previous[field] != current[field]:
                return dict(out, reason='path_specification_changed')
        horizons = {h: _horizon_change(previous, current, h) for h in current['path']}
        n = sum(value['status'] == 'available' for value in horizons.values())
        return dict(out, status='available' if n == len(horizons) else 'partial' if n else 'unavailable',
                    reason=None if n else 'no_attributable_horizon', horizons=horizons,
                    observation_dates=[value['observation_date'] for value in snapshots],
                    captured_at=[value['captured_at'] for value in snapshots],
                    snapshot_sha256=digests,
                    elapsed_calendar_days=int((selected.index[-1] - selected.index[0]).days),
                    horizon_basis='successive_retained_source_rows',
                    evidence_basis=('same_capture_corrected_history' if
                        previous['captured_at'] == current['captured_at'] else
                        'latest_vintages_cross_capture'),
                    weight_basis=WEIGHT_BASIS, quote_kind=QUOTE_KIND)
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError, OSError) as exc:
        reason = str(exc) if type(exc) is ValueError else 'invalid_source'
        return dict(out, reason=reason[:120])


def _read_family(data_dir, key, root, asof, evaluated_at):
    unavailable = {'status': 'unavailable', 'rate_family': FAMILIES[root][0],
        'horizons': {}, 'historical_availability_qualified': False, **AUTHORITY}
    try:
        folder = Path(data_dir) / 'rate_futures'
        path_file, companion = folder / f'{key}_path.parquet', folder / f'{key}_constituents.parquet'
        if not path_file.is_file() or not companion.is_file():
            return dict(unavailable, reason='missing_source')
        path = _daily_frame(pd.read_parquet(path_file))
        evidence = _daily_frame(pd.read_parquet(companion))
        current = _from_frames(path, evidence, root, asof, evaluated_at)
        if current.get('reason') == 'capture_may_include_incomplete_bar':
            # Explicit dated context only, from the SAME read. Never promote it
            # to the current result or conceal a corrupt/future/stale latest row.
            selected = path.loc[:pd.Timestamp(asof)]
            completed_cut = selected.index[-1] - pd.Timedelta(days=1)
            context = _from_frames(path, evidence, root, completed_cut, evaluated_at)
            if context['status'] in ('available', 'partial'):
                current['last_completed_observation_context'] = dict(context,
                    context_only=True, source_cut=str(completed_cut.date()),
                    current_observation_qualified=False)
        return current
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError, OSError) as exc:
        reason = str(exc) if type(exc) is ValueError else 'invalid_source'
        return dict(unavailable, reason=reason[:120])


def build_policy_repricing(data_dir, *, asof=None, evaluated_at=None):
    """Read the existing collector output; no latest-row fallback or trade signal.

    Each family is isolated. A missing SR3 source cannot erase a valid ZQ read.
    The capture rule only excludes potentially incomplete same-day daily bars;
    it does not certify exchange settlement, authentic clocks or historical PIT.
    """
    stamp = _stamp(evaluated_at or datetime.now(timezone.utc))
    cut = asof if asof is not None else str(stamp.tz_convert('America/New_York').date())
    return {'schema': 'rate_futures.repricing.v1', 'evaluated_at': stamp.isoformat(),
            'asof': str(cut), 'historical_availability_qualified': False, **AUTHORITY,
            'families': {key: _read_family(data_dir, key, root, cut, stamp)
                         for key, root in (('zq', 'ZQ'), ('sofr', 'SR3'))},
            'caveats': [
                'Matched-contract changes include fixings and risk premia; not a causal policy shock.',
                'Rolling coordinates use the incumbent whole-month centre approximation.',
                'Provider daily Close is not authenticated exchange settlement.',
                'Latest-vintage storage and capture clocks do not certify historical availability.',
                'This is measured context, not a directional forecast or trading permission.']}
