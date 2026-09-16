"""Offline numerical-contract oracle for research qualification only.

Consumes MANUALLY normalized, reviewed examples. It does not extract documents,
prove licenses, verify signatures, authenticate a user, read a production corpus,
or implement a product tool. The local allowed_for_assay/review_state values are
fixture labels, NOT production permission or evidence authorities. Never import
this module into a running Mastermind service.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
import re

_DIMENSIONS = ('entity', 'scope', 'metric', 'currency', 'scale', 'basis')
_REQUIRED = _DIMENSIONS + ('period_start', 'period_end', 'scenario', 'origin',
                            'id', 'document_id', 'document_version', 'event_date')
_AUTHORITY = dict(authority='offline_context_only', may_rank=False,
                  may_size=False, may_trade=False)
_DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z')
_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\Z')


def _out(status: str, **values) -> dict:
    return {'status': status, **values, **_AUTHORITY}


def _day(raw: str) -> date:
    if not isinstance(raw, str) or not _DATE.fullmatch(raw):
        raise ValueError('date precision required')
    return date.fromisoformat(raw)


def _number(raw: str) -> Decimal:
    if not isinstance(raw, str) or not _DECIMAL.fullmatch(raw) or len(raw) > 60:
        raise ValueError('finite canonical decimal string required')
    value = Decimal(raw)
    if not value.is_finite():
        raise ValueError('finite number required')
    return value


def _interval(value: Mapping) -> tuple[Decimal, Decimal, bool]:
    if not isinstance(value, Mapping):
        raise ValueError('value object required')
    shape = value.get('shape')
    if shape in ('approximate_point', 'rounded_actual', 'exact_point'):
        if set(value) != {'shape', 'point'}:
            raise ValueError('ambiguous point representation')
        n = _number(value['point'])
        return n, n, shape != 'exact_point'
    if shape == 'range':
        if set(value) != {'shape', 'low', 'high'}:
            raise ValueError('ambiguous range representation')
        lo, hi = _number(value['low']), _number(value['high'])
        if lo > hi:
            raise ValueError('reversed range')
        return lo, hi, False
    raise ValueError('unsupported value representation')


def _format(value: Decimal) -> str:
    if value == 0:
        return '0'
    return format(value.normalize(), 'f')


def _validation(claim: Mapping) -> str | None:
    if any(not isinstance(claim.get(k), str) or not claim[k].strip()
           for k in _REQUIRED):
        return 'incomplete_comparison_key'
    if claim.get('claim_kind') not in ('guidance', 'actual'):
        return 'invalid_claim'
    try:
        if _day(claim['period_start']) > _day(claim['period_end']):
            return 'invalid_claim'
        _day(claim['event_date'])
        lo, hi, _ = _interval(claim.get('value'))
        if claim['metric'] == 'capital_expenditure' and lo < 0:
            return 'invalid_claim'
        if claim['claim_kind'] == 'actual' and lo != hi:
            return 'invalid_claim'
    except (ValueError, InvalidOperation, TypeError):
        return 'invalid_claim'
    return None


def compare(before: Mapping, after: Mapping) -> dict:
    """Classify a pair and calculate only genuinely comparable quantities.

    This is retrospective manual-case analysis. It never asserts operational
    historical availability. Day-only source dates cannot order two same-day
    distinct source records. No implicit FX, scale, fiscal-period or basis
    conversion is performed; those transforms belong to existing data owners.
    """
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        return {'status': 'not_served'}
    if any(c.get('allowed_for_assay') is not True for c in (before, after)):
        return {'status': 'not_served'}
    if any(c.get('review_state') != 'manually_checked_public_statement'
           for c in (before, after)):
        return _out('unverified_evidence')
    for claim in (before, after):
        problem = _validation(claim)
        if problem:
            return _out(problem)
    for key in ('period_start', 'period_end'):
        if before[key] != after[key]:
            return _out('not_comparable', reason='different_period')
    for key in _DIMENSIONS:
        if before[key] != after[key]:
            return _out('not_comparable', reason='different_' + key)

    old_lo, old_hi, old_approx = _interval(before['value'])
    new_lo, new_hi, new_approx = _interval(after['value'])
    same_document = before['document_id'] == after['document_id']
    if same_document and before['document_version'] == after['document_version']:
        same_record = (before['id'] == after['id'] and before['origin'] == after['origin']
                       and before['value'] == after['value']
                       and before['claim_kind'] == after['claim_kind']
                       and before['scenario'] == after['scenario'])
        if same_record:
            return _out('same_source_record')
        # Several different claims may legitimately live in the same document.
        # A repeated claim id whose value changes without a version change is not.
        if before['id'] == after['id']:
            return _out('conflicting_same_source_record')
    if same_document and before['document_version'] != after['document_version']:
        return _out('source_amendment_requires_review')
    before_day, after_day = _day(before['event_date']), _day(after['event_date'])
    same_origin = before['origin'] == after['origin']
    if same_origin and before_day > after_day:
        return _out('invalid_order')
    if same_origin and before_day == after_day:
        return _out('same_day_order_unknown')

    if before['claim_kind'] == 'guidance' and after['claim_kind'] == 'actual':
        if before['origin'] != after['origin']:
            return _out('cross_source_realization_requires_review')
        position = ('below_stated_range' if new_lo < old_lo else
                    'above_stated_range' if new_lo > old_hi else
                    'inside_stated_range')
        return _out('realization', actual_position=position,
                    actual=_format(new_lo), stated_low=_format(old_lo),
                    stated_high=_format(old_hi),
                    approximate_inputs=old_approx or new_approx,
                    precision_note='comparison at the stated source precision')
    if before['claim_kind'] != after['claim_kind'] or before['claim_kind'] == 'actual':
        return _out('observation_comparison_requires_review')
    if before['scenario'] != after['scenario']:
        return _out('not_comparable', reason='different_scenario')

    unchanged = before['value'] == after['value']
    same_endpoints = old_lo == new_lo and old_hi == new_hi
    # Unchanged stated endpoints are no forecast revision. They are not two
    # independent uncertain draws from a range.
    delta_lo, delta_hi = ((Decimal(0), Decimal(0)) if same_endpoints else
                          (new_lo - old_hi, new_hi - old_lo))
    if before['origin'] != after['origin']:
        status = 'cross_source_difference'
    elif unchanged:
        status = 'reaffirmation' if after.get('explicit_reaffirmation') is True else 'unchanged_value'
    elif same_endpoints:
        status = 'representation_changed'
    else:
        status = 'revision'
    direction = ('higher' if delta_lo > 0 else 'lower' if delta_hi < 0 else
                 'unchanged' if same_endpoints else 'overlap_or_mixed')
    result = _out(status, delta_low=_format(delta_lo), delta_high=_format(delta_hi),
                  direction=direction, approximate_inputs=old_approx or new_approx,
                  interval_meaning='arithmetic bounds, not a probability interval')
    if old_lo > 0:
        with localcontext() as context:
            context.prec = 128
            pct_lo = Decimal(0) if same_endpoints else (new_lo / old_hi - 1) * 100
            pct_hi = Decimal(0) if same_endpoints else (new_hi / old_lo - 1) * 100
            result['percent_low'] = _format(pct_lo.quantize(Decimal('0.000001')))
            result['percent_high'] = _format(pct_hi.quantize(Decimal('0.000001')))
    return result


def _instant(raw: str) -> datetime:
    if not isinstance(raw, str) or 'T' not in raw:
        raise ValueError('timezone-aware timestamp required')
    stamp = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('timezone-aware timestamp required')
    return stamp


def select_visible(claims: list[Mapping], cutoff: str) -> dict:
    """Exercise known-availability selection with synthetic timestamp fixtures.

    Real public-control claims have unknown available_at and therefore cannot
    pass this operational check. This function is not a historical data service.
    """
    deadline = _instant(cutoff)
    eligible, unknown = [], 0
    for claim in claims:
        if claim.get('allowed_for_assay') is not True:
            continue
        try:
            known = _instant(claim.get('available_at'))
        except (ValueError, TypeError):
            unknown += 1
            continue
        if known <= deadline:
            try:
                event_day = _day(claim['event_date'])
            except (KeyError, ValueError, TypeError):
                continue
            if event_day > known.date():
                continue
            eligible.append(claim)
    if not eligible:
        return {'status': 'no_eligible_claim', 'excluded_unknown': unknown}
    keys = {tuple(c.get(k) for k in _DIMENSIONS + ('period_start','period_end','scenario','origin','claim_kind'))
            for c in eligible}
    if len(keys) != 1:
        return {'status': 'ambiguous_series'}
    newest = max(c['event_date'] for c in eligible)
    newest_claims = [c for c in eligible if c['event_date'] == newest]
    if len({(c['document_id'],c['document_version'],c['id']) for c in newest_claims}) > 1:
        return {'status': 'same_day_order_unknown'}
    return {'status': 'selected', 'id': newest_claims[0]['id'], 'excluded_unknown': unknown}


def invalidated_outputs(outputs: Mapping[str, list[str]], changed_version: str) -> list[str]:
    """Pure dependency closure. Does not store, mutate or republish anything."""
    affected = {changed_version}
    while True:
        newly = {key for key, dependencies in outputs.items()
                 if any(dependency in affected for dependency in dependencies)}
        if newly <= affected:
            break
        affected |= newly
    return sorted(key for key in outputs if key in affected)


def source_counts(records: list[Mapping]) -> dict:
    """Contrast raw labels with provided origin keys; does not infer aliases.

    A resolved publisher key is still NOT proof of independent underlying data.
    In particular S&T has no automatic institution-wide mapping in this oracle.
    """
    def present(value):
        return isinstance(value, str) and bool(value.strip())
    labels = {r['institution_label'] for r in records if present(r.get('institution_label'))}
    origins = {r['origin_id'] for r in records if present(r.get('origin_id'))}
    return {'raw_labels': len(labels), 'resolved_origins': len(origins),
            'unresolved_records': sum(not present(r.get('origin_id')) for r in records),
            'origin_resolution_is_not_evidence_independence': True}


def validate_locator(locator: Mapping, current_source_hash: str | None) -> dict:
    """Structural source-opening precondition assay, not actual byte proof.

    Synthetic hash strings in tests stand in for digests supplied by the existing
    source owner. This function cannot establish their provenance. A bound result
    means only that supplied references are internally consistent; production also
    needs actual trusted source custody, body-version and entitled viewer checks.
    """
    if not isinstance(locator, Mapping):
        return {'status': 'source_binding_missing'}
    hashes = (locator.get('source_hash'), locator.get('body_hash'), current_source_hash)
    if any(not isinstance(h, str) or re.fullmatch(r'[0-9a-f]{64}', h) is None for h in hashes):
        return {'status': 'source_binding_missing'}
    if locator['source_hash'] != current_source_hash:
        return {'status': 'source_changed'}
    page, pages = locator.get('page'), locator.get('page_count')
    if type(page) is not int or type(pages) is not int or page < 1 or pages < 1 or page > pages:
        return {'status': 'invalid_locator'}
    return {'status': 'bound_locator', 'actual_bytes_verified_by_this_oracle': False}
