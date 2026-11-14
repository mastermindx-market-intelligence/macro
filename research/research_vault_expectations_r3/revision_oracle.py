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


def _forecast_target(raw: Mapping) -> dict:
    """Validate manual target labels; never infer a fixing or roll a date."""
    if not isinstance(raw, Mapping):
        raise ValueError('target object required')
    kind = raw.get('kind')
    common = {'kind', 'measure', 'fixing'}
    if kind == 'year_end':
        if set(raw) != common | {'year'}:
            raise ValueError('ambiguous fixed target')
        if type(raw['year']) is not int or not 1900 <= raw['year'] <= 9999:
            raise ValueError('literal target year required')
    elif kind == 'relative_tenor':
        if set(raw) != common | {'label', 'anchor_date', 'resolved_target_date', 'resolution_basis'}:
            raise ValueError('ambiguous relative target')
        label = raw.get('label')
        if not isinstance(label, str) or re.fullmatch(r'[1-9][0-9]?[DWMY]', label) is None:
            raise ValueError('bounded literal tenor required')
        if raw['anchor_date'] is not None:
            _day(raw['anchor_date'])
        resolved, basis = raw['resolved_target_date'], raw['resolution_basis']
        if resolved is not None:
            _day(resolved)
            if basis != 'publisher_explicit_date':
                raise ValueError('no inferred resolved dates')
        elif basis is not None:
            raise ValueError('basis without resolved date')
    else:
        raise ValueError('unsupported target kind')
    if raw['measure'] not in ('end_of_period', 'period_average'):
        raise ValueError('target measure required')
    if raw['fixing'] is not None and (not isinstance(raw['fixing'], str) or not raw['fixing'].strip()):
        raise ValueError('invalid fixing convention')
    return dict(raw)


def _validation(claim: Mapping) -> str | None:
    analyst = claim.get('claim_kind') == 'analyst_forecast'
    required = tuple(k for k in _REQUIRED if not analyst or k not in ('period_start', 'period_end'))
    if any(not isinstance(claim.get(k), str) or not claim[k].strip() for k in required):
        return 'incomplete_comparison_key'
    if claim.get('claim_kind') not in ('guidance', 'actual', 'analyst_forecast'):
        return 'invalid_claim'
    try:
        if analyst:
            target = _forecast_target(claim.get('target'))
            if 'period_start' in claim or 'period_end' in claim:
                return 'invalid_claim'  # exactly one target representation
            event_day = _day(claim['event_date'])
            if target['kind'] == 'relative_tenor' and target['resolved_target_date'] is not None:
                target_day = _day(target['resolved_target_date'])
                if target_day < event_day:
                    return 'invalid_claim'
                if target['anchor_date'] is not None and target_day < _day(target['anchor_date']):
                    return 'invalid_claim'
            if claim.get('source_role') != 'publisher_forecast':
                return 'invalid_claim'
            if 'explicit_revision' in claim and type(claim['explicit_revision']) is not bool:
                return 'invalid_claim'
            if claim.get('explicit_revision') is True and 'reported_prior' not in claim:
                return 'invalid_claim'
            if isinstance(claim.get('value'), Mapping) and claim['value'].get('shape') == 'rounded_actual':
                return 'invalid_claim'
            if 'reported_prior' in claim:
                prior_lo, _prior_hi, _prior_approx = _interval(claim['reported_prior'])
                if claim['reported_prior'].get('shape') == 'rounded_actual':
                    return 'invalid_claim'
                if claim['metric'] == 'exchange_rate' and prior_lo <= 0:
                    return 'invalid_claim'
        elif _day(claim['period_start']) > _day(claim['period_end']):
            return 'invalid_claim'
        _day(claim['event_date'])
        lo, hi, _ = _interval(claim.get('value'))
        if claim['metric'] == 'capital_expenditure' and lo < 0:
            return 'invalid_claim'
        if claim['metric'] == 'exchange_rate' and lo <= 0:
            return 'invalid_claim'
        if claim['claim_kind'] == 'actual' and lo != hi:
            return 'invalid_claim'
    except (ValueError, InvalidOperation, TypeError, KeyError):
        return 'invalid_claim'
    return None


def _target_relation(before: Mapping, after: Mapping, mode: str) -> tuple[str | None, str]:
    """Returns refusal reason and comparison scope, not a temporal fact store."""
    a, b = before['target'], after['target']
    if a['measure'] != b['measure']:
        return 'different_target_measure', ''
    if a['fixing'] != b['fixing']:
        return 'different_fixing_convention', ''
    if a['kind'] != b['kind']:
        return 'different_target_kind', ''
    if mode == 'constant_horizon_profile':
        if a['kind'] != 'relative_tenor':
            return 'profile_requires_relative_target', ''
        if a['label'] != b['label']:
            return 'different_horizon', ''
        return None, 'constant_horizon_profile_not_fixed_date'
    if a['kind'] == 'year_end':
        if a['year'] != b['year']:
            return 'different_target', ''
        return None, 'publisher_named_fixed_target'
    if a['resolved_target_date'] is None or b['resolved_target_date'] is None:
        return 'unresolved_relative_target', ''
    if a['resolved_target_date'] != b['resolved_target_date']:
        return 'different_target', ''
    return None, 'publisher_explicit_fixed_date'


def _value_change(old_value: Mapping, new_value: Mapping) -> dict:
    """Shared exact arithmetic over already admitted manual values, not probabilities."""
    old_lo, old_hi, old_approx = _interval(old_value)
    new_lo, new_hi, new_approx = _interval(new_value)
    same = old_lo == new_lo and old_hi == new_hi
    with localcontext() as context:
        context.prec = 128
        delta_lo, delta_hi = ((Decimal(0), Decimal(0)) if same else
                              (new_lo - old_hi, new_hi - old_lo))
        direction = ('higher' if delta_lo > 0 else 'lower' if delta_hi < 0 else
                     'unchanged' if same else 'overlap_or_mixed')
        result = dict(delta_low=_format(delta_lo), delta_high=_format(delta_hi),
                      direction=direction, approximate_inputs=old_approx or new_approx,
                      interval_meaning='arithmetic bounds, not a probability interval')
        if old_lo > 0:
            pct_lo = Decimal(0) if same else (new_lo / old_hi - 1) * 100
            pct_hi = Decimal(0) if same else (new_hi / old_lo - 1) * 100
            result['percent_low'] = _format(pct_lo.quantize(Decimal('0.000001')))
            result['percent_high'] = _format(pct_hi.quantize(Decimal('0.000001')))
    return result


def compare(before: Mapping, after: Mapping, *, comparison_mode: str = 'fixed_target') -> dict:
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
    if comparison_mode not in ('fixed_target', 'constant_horizon_profile'):
        return _out('invalid_comparison_mode')
    analyst = before['claim_kind'] == 'analyst_forecast' or after['claim_kind'] == 'analyst_forecast'
    comparison_scope = ''
    if analyst:
        if before['claim_kind'] != after['claim_kind']:
            return _out('not_comparable', reason='different_statement_kind')
        reason, comparison_scope = _target_relation(before, after, comparison_mode)
        if reason:
            return _out('not_comparable', reason=reason)
    else:
        if comparison_mode != 'fixed_target':
            return _out('not_comparable', reason='profile_requires_analyst_forecast')
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
    if not same_origin:
        status = 'cross_source_difference'
    elif unchanged:
        status = 'reaffirmation' if after.get('explicit_reaffirmation') is True else 'unchanged_value'
    elif same_endpoints:
        status = 'representation_changed'
    else:
        status = 'revision'
    details = _value_change(before['value'], after['value'])
    if analyst:
        quoted = after.get('reported_prior')
        quoted_relation = 'not_asserted'
        if quoted is not None:
            quote_endpoints = _interval(quoted)[:2]
            quoted_relation = ('matches_captured_earlier_value' if quote_endpoints == (old_lo, old_hi)
                               else 'differs_from_captured_earlier_value')
        repeated = (same_origin and same_endpoints
                    and before.get('explicit_revision') is True
                    and after.get('explicit_revision') is True
                    and _interval(before['reported_prior'])[:2] == _interval(after['reported_prior'])[:2]
                    and _interval(after['reported_prior'])[:2] != (new_lo, new_hi))
        change_relation = 'not_asserted'
        if after.get('explicit_revision') is True:
            if not same_origin:
                change_relation = 'different_origin_no_revision_lineage'
            elif repeated:
                change_relation = 'same_reported_endpoints_in_captured_sources'
            elif before.get('explicit_revision') is not True:
                change_relation = 'newly_captured_reported_change'
            elif same_endpoints:
                change_relation = 'different_quoted_prior_same_current'
            else:
                change_relation = 'different_captured_change_statement'
        if comparison_mode == 'constant_horizon_profile':
            status = 'constant_horizon_profile_change' if not same_endpoints else 'constant_horizon_profile_unchanged'
        elif repeated:
            status = 'repeated_reported_revision'
        details.update(
            comparison_scope=comparison_scope,
            numeric_change_between_inputs=not same_endpoints,
            fixed_target_revision=(status == 'revision' and comparison_mode == 'fixed_target'),
            fixing_convention_verified=before['target']['fixing'] is not None,
            quoted_prior_relation=quoted_relation,
            reported_change_relation=change_relation,
            immediate_predecessor_verified=False,
            first_ever_revision_date_known=False,
            original_pair_verified=False,
            other_report_content_assessed=False,
            repetition_scope='captured_source_statements_only' if repeated else None,
        )
    return _out(status, **details)


def reported_change(claim: Mapping) -> dict:
    """Describe a source's own quoted change without fabricating a prior original.

    All admission/review fields are local research labels. No source authenticity,
    commercial grant, notification eligibility or original-pair proof is created.
    """
    if not isinstance(claim, Mapping) or claim.get('allowed_for_assay') is not True:
        return {'status': 'not_served'}
    if claim.get('review_state') != 'manually_checked_public_statement':
        return _out('unverified_evidence')
    problem = _validation(claim)
    if problem:
        return _out(problem)
    if claim['claim_kind'] != 'analyst_forecast':
        return _out('unsupported_statement_kind')
    if claim.get('explicit_revision') is not True:
        return _out('no_explicit_reported_revision')
    if claim['target']['kind'] != 'year_end':
        return _out('not_comparable', reason='reported_target_not_fixed')
    details = _value_change(claim['reported_prior'], claim['value'])
    status = ('source_reported_unchanged_endpoints' if details['direction'] == 'unchanged'
              else 'source_reported_revision')
    return _out(status, **details,
                prior_evidence='quoted_within_current_source',
                original_pair_verified=False, immediate_predecessor_verified=False,
                first_ever_revision_date_known=False,
                comparison_scope='publisher_named_fixed_target')


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
    if any(c.get('claim_kind') == 'analyst_forecast' for c in eligible):
        # Analyst target integration into the real temporal owner is not admitted
        # by this offline arithmetic extension. Do not collapse missing period keys.
        return {'status': 'unsupported_operational_forecast_series'}
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
