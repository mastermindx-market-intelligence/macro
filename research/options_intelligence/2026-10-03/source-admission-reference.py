#!/usr/bin/env python3
"""Offline research contract/fixture reference. Never a production admission gate."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re
import sys


POLICY_ID = 'synthetic_source_admission/v1'
PRICE = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$')
TIMESTAMP = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,3})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$')
SEQUENCE = re.compile(r'^(?:0|[1-9][0-9]*)$')
GREEK_UNITS = {
    'sigma_unit': 'decimal_annualized',
    'delta_unit': 'price_per_underlying_price',
    'gamma_unit': 'per_underlying_price',
    'vega_unit': 'price_per_decimal_sigma',
    'vanna_unit': 'delta_per_decimal_sigma',
    'charm_unit': 'delta_per_calendar_year',
}


def _decimal(value):
    if type(value) is int:
        return Decimal(value)
    if isinstance(value, str) and PRICE.fullmatch(value):
        number = Decimal(value)
        return number if number.is_finite() else None
    return None


def _number(value):
    if value is None:
        return None
    out = format(value, 'f')
    return out.rstrip('0').rstrip('.') if '.' in out else out


def _ratio(numerator, denominator):
    return None if denominator is None or denominator <= 0 else _number(numerator / denominator)


def _time(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.microsecond % 1000:
            return None
        return stamp.astimezone(timezone.utc)
    except ValueError:
        return None


def _milliseconds(later, earlier):
    delta = later - earlier
    return Decimal(delta.days * 86400000 + delta.seconds * 1000) + Decimal(delta.microseconds) / 1000


def _positive_integer(value):
    return type(value) is int and value > 0


def _nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def _sequence_qualified(record):
    return (record.get('sequence_scope') == 'synthetic_contract_session'
            and isinstance(record.get('source_sequence'), str)
            and SEQUENCE.fullmatch(record['source_sequence']) is not None)


def _join_compatible(left, right):
    keys = ('as_of', 'artifact_revision', 'population_ref')
    return (all(_nonempty_text(x.get(k)) for x in (left, right) for k in keys)
            and all(_positive_integer(x.get('row_count')) for x in (left, right))
            and all(left[k] == right[k] for k in (*keys, 'row_count')))


def _causal_quote(quote_time, trade_time):
    return quote_time < trade_time


def _condition_policy_ok(policy):
    cp = policy.get('condition_policy', {})
    return (cp.get('policy_id') == 'synthetic_conditions/v1'
            and type(cp.get('version')) is int and cp['version'] == 1
            and cp.get('qualification') == 'synthetic_fixture_only'
            and cp.get('allowed_trade') == ['SYN_T_REGULAR']
            and cp.get('allowed_quote') == ['SYN_Q_TWO_SIDED'])


def _nbbo_basis(basis):
    return basis == 'synthetic_trade_quote'


def _correction_resolved(status):
    # No amendment engine or sequence-derived correction inference is installed.
    return status == 'synthetic_original_unamended'


def _premium(price, quantity, multiplier):
    return price * quantity * multiplier


def _artifact_chain(computed, published, received):
    return computed <= published <= received


def _consumer_cutoff(received, admitted, candidate_decision):
    return received <= admitted <= candidate_decision


def _captured_mode(evidence):
    prov = evidence.get('provenance', {})
    receipts = [evidence.get('publication_receipt', {}), evidence.get('consumer_receipt', {})]
    receipts += [r.get('input_receipt', {}) for r in evidence.get('records', [])]
    receipts += [r.get('contract_reference', {}) for r in evidence.get('records', [])]
    receipts += evidence.get('additional_input_refs', [])
    return (prov.get('mode') == 'captured_pit'
            and prov.get('original_receipts_retained') is True
            and all(r.get('original_receipt_retained') is True for r in receipts))


def _infer_sign(price, bid, ask):
    if price < bid or price > ask:
        return None, 'OUTSIDE_QUOTE_SIGN_UNKNOWN'
    midpoint = (bid + ask) / 2
    if price == midpoint:
        return None, 'MIDPOINT_SIGN_UNKNOWN'
    return (1 if price > midpoint else -1), None


def _record(record, policy, basis, condition_ok, duplicate):
    reasons = []
    price = _decimal(record.get('price'))
    quantity = record.get('contracts')
    if price is None or price <= 0 or not _positive_integer(quantity):
        reasons.append('TRADE_ECONOMICS_INVALID')
    ref = record.get('contract_reference', {})
    multiplier = _decimal(record.get('quote_multiplier'))
    reference_multiplier = _decimal(ref.get('multiplier'))
    underlying_units = _decimal(ref.get('underlying_units'))
    if multiplier is None or reference_multiplier is None or multiplier <= 0 or reference_multiplier <= 0:
        reasons.append('MULTIPLIER_UNQUALIFIED')
    elif multiplier != reference_multiplier:
        reasons.append('MULTIPLIER_REFERENCE_MISMATCH')
    if (ref.get('deliverable_kind') != 'synthetic_single_underlying'
            or underlying_units is None or underlying_units != reference_multiplier):
        reasons.append('DELIVERABLE_TRANSFORM_UNQUALIFIED')
    if (not _nonempty_text(record.get('contract_id'))
            or not _nonempty_text(ref.get('contract_id'))
            or ref.get('contract_id') != record.get('contract_id')
            or ref.get('currency') != 'USD'
            or ref.get('quote_unit') != 'USD_per_underlying_unit'
            or not _nonempty_text(ref.get('reference_id')) or not _nonempty_text(ref.get('revision'))):
        reasons.append('CONTRACT_REFERENCE_UNQUALIFIED')
    money_errors = bool(reasons)
    premium = None if money_errors else _premium(price, quantity, multiplier)
    if duplicate:
        reasons.append('DUPLICATE_RECORD_ID_UNRESOLVED')
    trade_time = _time(record.get('trade_timestamp'))
    if trade_time is None:
        reasons.append('TRADE_CLOCK_INVALID')
    if not _sequence_qualified(record):
        reasons.append('SEQUENCE_CONTRACT_UNQUALIFIED')
    if not _correction_resolved(record.get('correction_status')):
        reasons.append('CORRECTION_UNRESOLVED')
    if not _nbbo_basis(basis):
        reasons.append('SOURCE_BASIS_NOT_NBBO')
    quote = record.get('quote')
    quote_age = None
    if not isinstance(quote, dict):
        reasons.append('QUOTE_MISSING')
        quote = {}
    if (not _nonempty_text(quote.get('contract_id'))
            or quote.get('contract_id') != record.get('contract_id')):
        reasons.append('QUOTE_CONTRACT_MISMATCH')
    qt = _time(quote.get('quote_timestamp'))
    if qt is None:
        reasons.append('QUOTE_CLOCK_INVALID')
    elif trade_time is not None:
        quote_age = _milliseconds(trade_time, qt)
        if not _causal_quote(qt, trade_time):
            reasons.append('FUTURE_OR_EQUAL_QUOTE')
        if quote_age > policy['max_quote_age_ms']:
            reasons.append('STALE_QUOTE')
    bid, ask = _decimal(quote.get('bid')), _decimal(quote.get('ask'))
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        reasons.append('QUOTE_PRICE_INVALID')
    elif bid == ask:
        reasons.append('LOCKED_QUOTE')
    elif bid > ask:
        reasons.append('CROSSED_QUOTE')
    if not _positive_integer(quote.get('bid_size')) or not _positive_integer(quote.get('ask_size')):
        reasons.append('QUOTE_SIZE_INVALID')
    if not condition_ok:
        reasons.append('CONDITION_POLICY_UNQUALIFIED')
    elif (record.get('trade_condition') not in policy['condition_policy']['allowed_trade']
          or quote.get('bid_condition') not in policy['condition_policy']['allowed_quote']
          or quote.get('ask_condition') not in policy['condition_policy']['allowed_quote']):
        reasons.append('CONDITION_INELIGIBLE')
    valid = not reasons
    location, sign = None, None
    if valid:
        if price == ask:
            location = 'at_ask'
        elif price == bid:
            location = 'at_bid'
        elif bid < price < ask:
            location = 'inside'
        else:
            location = 'outside'
        sign, abstention = _infer_sign(price, bid, ask)
        if abstention:
            reasons.append(abstention)
    return {'record_id': record.get('record_id'), 'quote_valid': valid,
            'quote_location': location, 'quote_age_ms': _number(quote_age),
            'inferred_sign': sign, 'premium_usd': _number(premium),
            'reasons': sorted(set(reasons)), 'retained_source_record': copy.deepcopy(record)}


def _additional_refs(refs, contract_ids):
    views, times, reasons = [], [], []
    for ref in refs:
        local = []
        kind, details = ref.get('kind'), ref.get('details', {})
        source, received, available = (_time(ref.get(k)) for k in ('source_timestamp', 'received_at', 'available_at'))
        if (not _nonempty_text(ref.get('reference_id')) or not _nonempty_text(ref.get('revision'))
                or None in (source, received, available) or not source <= received <= available):
            local.append('ADDITIONAL_INPUT_CLOCK_INVALID')
        if available is not None:
            times.append(available)
        view = {'kind': kind, 'reference_id': ref.get('reference_id'),
                'revision': ref.get('revision'), 'available_at': ref.get('available_at'),
                'numerical_accuracy_qualified': False, 'retained_reference': copy.deepcopy(ref)}
        if kind == 'open_interest':
            effective = _time(details.get('effective_at'))
            view['effective_at'] = details.get('effective_at')
            oi = details.get('open_interest')
            if (effective is None or source is None or not effective < source
                    or type(oi) is not int or oi < 0):
                local.append('OI_EFFECTIVE_TIME_UNQUALIFIED')
        elif kind == 'greeks':
            underlying = _time(details.get('underlying_timestamp'))
            tte = _decimal(details.get('tte_seconds'))
            required = ['underlying_source_ref', 'model_id', 'model_version', 'price_basis',
                        'rate_ref', 'dividend_ref', 'iv_solver_ref', 'expiry_rule_ref']
            if (underlying is None or source is None or underlying > source
                    or tte is None or tte <= 0 or details.get('day_count') != 'ACT/365F'
                    or details.get('contract_ref') not in contract_ids
                    or any(not _nonempty_text(details.get(k)) for k in required)
                    or any(details.get(k) != v for k, v in GREEK_UNITS.items())):
                local.append('GREEK_PROVENANCE_UNQUALIFIED')
        else:
            local.append('ADDITIONAL_INPUT_KIND_UNQUALIFIED')
        view['valid'] = not local
        view['reasons'] = sorted(set(local))
        views.append(view)
        reasons.extend(local)
    return views, times, reasons


def _outcome_view(reference):
    if reference is None:
        return {'status': 'unavailable', 'value': None}
    maturity, available, evaluation = (_time(reference.get(k)) for k in ('matures_at', 'available_at', 'evaluation_at'))
    if (None in (maturity, available, evaluation) or available < maturity
            or not _nonempty_text(reference.get('label_id'))
            or not _nonempty_text(reference.get('label_revision'))):
        return {'status': 'unavailable', 'value': None, 'reason': 'LABEL_AVAILABILITY_UNQUALIFIED'}
    if evaluation < max(maturity, available):
        return {'status': 'pending', 'value': None}
    value = _decimal(reference.get('value'))
    return {'status': 'available' if value is not None else 'unavailable', 'value': _number(value)}


def _invalid_result(reason):
    return {'reference_scope': 'research_fixture_only', 'source_certified_accepted': False,
            'acceptance': {'synthetic_contract_pass': False, 'captured_pit_eligible': False,
                           'reasons': [reason]}, 'nbbo': None, 'rows': [], 'outcome': {'status': 'unavailable', 'value': None}}


def evaluate(evidence: dict, policy: dict) -> dict:
    """No writes, external lookups, source certification or candidate-schema changes."""
    if not isinstance(evidence, dict) or not isinstance(policy, dict):
        return _invalid_result('INVALID_INPUT_SHAPE')
    try:
        with localcontext() as context:
            context.prec = 40
            return _evaluate(evidence, policy)
    except (TypeError, ValueError, KeyError, InvalidOperation, OverflowError, AttributeError):
        return _invalid_result('MALFORMED_RESEARCH_INPUT')


def _evaluate(evidence, policy):
    if (policy.get('policy_id') != POLICY_ID or type(policy.get('version')) is not int
            or policy['version'] != 1 or policy.get('status') != 'proposed_synthetic_only'
            or not _positive_integer(policy.get('max_quote_age_ms'))
            or policy.get('stale_limit_inclusive') is not True or policy.get('price_tolerance') != '0'):
        return _invalid_result('POLICY_UNQUALIFIED')
    if not isinstance(evidence.get('records'), list) or not all(isinstance(r, dict) for r in evidence['records']):
        return _invalid_result('INVALID_RECORD_COLLECTION')
    reasons = []
    pref = evidence.get('policy_ref', {})
    if pref != {'policy_id': POLICY_ID, 'version': 1} or type(pref.get('version')) is not int:
        reasons.append('POLICY_REFERENCE_MISMATCH')
    condition_ok = _condition_policy_ok(policy)
    if not condition_ok:
        reasons.append('CONDITION_POLICY_UNQUALIFIED')
    if evidence.get('input_origin') != 'synthetic':
        reasons.append('REAL_SOURCE_UNQUALIFIED')
    if evidence.get('requested_coverage_scope') != evidence.get('coverage_scope'):
        reasons.append('COVERAGE_SCOPE_OVERCLAIM')
    if evidence.get('coverage_scope') not in ('selected_notable_event_subset', 'synthetic_fixture_population'):
        reasons.append('COVERAGE_SCOPE_UNQUALIFIED')
    records = evidence['records']
    ids = [r.get('record_id') for r in records]
    duplicate_record_ids = len(set(ids)) != len(ids) or any(not _nonempty_text(x) for x in ids)
    economic_ids = [(r.get('contract_id'), r.get('sequence_scope'), r.get('source_sequence'),
                     _time(r.get('trade_timestamp')).date().isoformat() if _time(r.get('trade_timestamp')) else None)
                    for r in records]
    duplicate_source_ids = len(set(economic_ids)) != len(economic_ids)
    duplicates = duplicate_record_ids or duplicate_source_ids
    if duplicate_record_ids:
        reasons.append('DUPLICATE_RECORD_ID_UNRESOLVED')
    if duplicate_source_ids:
        reasons.append('DUPLICATE_SOURCE_IDENTITY_UNRESOLVED')
    unresolved_corrections = any(not _correction_resolved(r.get('correction_status')) for r in records)
    if unresolved_corrections:
        reasons.append('CORRECTION_UNRESOLVED')
    unqualified_sequences = any(not _sequence_qualified(r) for r in records)
    if unqualified_sequences:
        reasons.append('SEQUENCE_CONTRACT_UNQUALIFIED')
    rows = [_record(r, policy, evidence.get('input_basis'), condition_ok, duplicates) for r in records]
    clocks = evidence.get('clocks', {})
    if (clocks.get('precision_ms') != 1 or type(clocks.get('precision_ms')) is not int
            or clocks.get('offset_uncertainty_ms') != 0
            or type(clocks.get('offset_uncertainty_ms')) is not int
            or evidence.get('provenance', {}).get('source_timestamp_meaning') != 'synthetic_event_time_only'):
        reasons.append('CLOCK_CONTRACT_UNQUALIFIED')
    input_times = []
    for record in records:
        receipt = record.get('input_receipt', {})
        if (receipt.get('record_id') != record.get('record_id')
                or receipt.get('source_revision') != record.get('source_revision')
                or not _nonempty_text(record.get('source_revision'))
                or not _nonempty_text(receipt.get('source_revision'))):
            reasons.append('INPUT_REVISION_MISMATCH')
        event, observed, available = (_time(v) for v in (record.get('trade_timestamp'), receipt.get('observed_at'), receipt.get('available_at')))
        if None in (event, observed, available) or not event <= observed <= available:
            reasons.append('INPUT_CLOCK_INVALID')
        if available is not None:
            input_times.append(available)
        ref_available = _time(record.get('contract_reference', {}).get('available_at'))
        if ref_available is None:
            reasons.append('CONTRACT_REFERENCE_CLOCK_INVALID')
        else:
            input_times.append(ref_available)
    classifier_input_times = list(input_times)
    additional, other_times, additional_reasons = _additional_refs(evidence.get('additional_input_refs', []), {r.get('contract_id') for r in records})
    input_times.extend(other_times)
    reasons.extend(additional_reasons)
    producer, computed, decision = (_time(clocks.get(k)) for k in ('producer_classified_at', 'computed_at', 'candidate_decision_at'))
    pub, consumer, artifact = (evidence.get(k, {}) for k in ('publication_receipt', 'consumer_receipt', 'artifact'))
    if (not _nonempty_text(artifact.get('artifact_id')) or not _nonempty_text(artifact.get('revision'))
            or any(r.get('artifact_id') != artifact.get('artifact_id') or r.get('revision') != artifact.get('revision') for r in [pub, consumer])):
        reasons.append('ARTIFACT_REVISION_MISMATCH')
    published, received, admitted = (_time(v) for v in (pub.get('published_at'), consumer.get('received_at'), consumer.get('admitted_at')))
    if None in (producer, computed, decision, published, received, admitted):
        reasons.append('ARTIFACT_CLOCK_INVALID')
    else:
        if classifier_input_times and max(classifier_input_times) > producer:
            reasons.append('INPUT_AFTER_CLASSIFICATION')
        if (input_times and max(input_times) > computed) or producer > computed:
            reasons.append('INPUT_AFTER_COMPUTATION')
        if not _artifact_chain(computed, published, received):
            reasons.append('ARTIFACT_CLOCK_CHAIN_INVALID')
        if not _consumer_cutoff(received, admitted, decision):
            reasons.append('CONSUMER_AFTER_DECISION')
    if not _captured_mode(evidence):
        reasons.append('CAPTURED_PIT_NOT_EVIDENCED')
    capture_blockers = {'CLOCK_CONTRACT_UNQUALIFIED', 'INPUT_REVISION_MISMATCH', 'INPUT_CLOCK_INVALID',
                        'CONTRACT_REFERENCE_CLOCK_INVALID', 'ARTIFACT_REVISION_MISMATCH', 'ARTIFACT_CLOCK_INVALID',
                        'INPUT_AFTER_CLASSIFICATION', 'INPUT_AFTER_COMPUTATION', 'ARTIFACT_CLOCK_CHAIN_INVALID', 'CONSUMER_AFTER_DECISION',
                        'CAPTURED_PIT_NOT_EVIDENCED', 'ADDITIONAL_INPUT_CLOCK_INVALID', 'REAL_SOURCE_UNQUALIFIED',
                        'CORRECTION_UNRESOLVED', 'DUPLICATE_RECORD_ID_UNRESOLVED', 'DUPLICATE_SOURCE_IDENTITY_UNRESOLVED',
                        'SEQUENCE_CONTRACT_UNQUALIFIED'}
    captured = not any(reason in capture_blockers for reason in reasons)
    premiums = [_decimal(r['premium_usd']) for r in rows]
    complete = (all(x is not None for x in premiums) and not duplicates
                and not unresolved_corrections and not unqualified_sequences)
    known = sum((x for x in premiums if x is not None), Decimal(0))
    total = known if complete else None
    valid = [r for r in rows if r['quote_valid']]
    covered = sum((_decimal(r['premium_usd']) for r in valid), Decimal(0))
    counts = {'source_print_count': len(rows), 'valid_print_count': len(valid)}
    nbbo = dict(counts, source_premium_usd=_number(total), known_record_premium_usd=_number(known),
                source_premium_complete=complete, covered_premium_usd=_number(covered),
                print_coverage=_ratio(Decimal(len(valid)), Decimal(len(rows))),
                premium_coverage=_ratio(covered, total), measure_kind='synthetic_quote_locations_only')
    for location in ['at_ask', 'at_bid', 'inside', 'outside']:
        money = sum((_decimal(r['premium_usd']) for r in valid if r['quote_location'] == location), Decimal(0))
        nbbo[location + '_share'] = _ratio(money, covered)
    classified = [r for r in rows if r['inferred_sign'] in (-1, 1)]
    unknown = [r for r in rows if r['inferred_sign'] not in (-1, 1)]
    unknown_values = [_decimal(r['premium_usd']) for r in unknown]
    signed = sum((Decimal(r['inferred_sign']) * _decimal(r['premium_usd']) for r in classified), Decimal(0))
    inferred = {'classified_print_count': len(classified), 'unknown_print_count': len(unknown),
                'signed_premium_usd': _number(signed) if classified else None,
                'unknown_premium_usd': _number(sum(unknown_values, Decimal(0))) if all(x is not None for x in unknown_values) else None,
                'meaning': 'synthetic_midpoint_inference_not_customer_opening_or_dealer_identity'}
    category_weights = {'~buy': Decimal('0.8'), '~sell': Decimal('0.2'), 'mixed': Decimal('0.5')}
    proxy_numerator, proxy_denominator = Decimal(0), Decimal(0)
    for record, premium in zip(records, premiums):
        weight = category_weights.get(record.get('legacy_side_category'))
        if weight is not None and premium is not None:
            proxy_numerator += weight * premium
            proxy_denominator += premium
    proxy = {'measure_kind': 'source_side_category_proxy', 'method_version': 'legacy_category_0.8_0.2_0.5/v1',
             'ask_share_proxy': _ratio(proxy_numerator, proxy_denominator),
             'category_covered_premium_usd': _number(proxy_denominator),
             'category_premium_coverage': _ratio(proxy_denominator, total)}
    claim = evidence.get('requested_claim')
    if claim == 'synthetic_measured_nbbo':
        if not _nbbo_basis(evidence.get('input_basis')):
            reasons.append('BASIS_CLAIM_MISMATCH')
        if not valid or not complete:
            reasons.append('NO_QUALIFIED_MEASUREMENT')
    elif claim == 'legacy_side_proxy':
        if evidence.get('input_basis') != 'source_side_category_proxy' or proxy['ask_share_proxy'] is None:
            reasons.append('BASIS_CLAIM_MISMATCH')
        if not complete:
            reasons.append('PROXY_DENOMINATOR_UNQUALIFIED')
    else:
        reasons.append('REQUESTED_CLAIM_UNQUALIFIED')
    join = evidence.get('join_request')
    join_identity = {'requested': join is not None, 'compatible': None}
    if join is not None:
        join_identity['compatible'] = _join_compatible(join.get('left', {}), join.get('right', {}))
        if not join_identity['compatible']:
            reasons.append('ARTIFACT_COHORT_JOIN_MISMATCH')
    canonical = json.dumps(evidence, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return {'reference_scope': 'research_fixture_only', 'source_certified_accepted': False,
            'evidence_ref': evidence.get('evidence_ref'), 'input_basis': evidence.get('input_basis'),
            'coverage_scope': evidence.get('coverage_scope'), 'input_digest_sha256': hashlib.sha256(canonical.encode()).hexdigest(),
            'policy_ref': {'policy_id': policy['policy_id'], 'version': policy['version'],
                           'digest_sha256': hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(',', ':')).encode()).hexdigest()},
            'acceptance': {'synthetic_contract_pass': not reasons, 'captured_pit_eligible': captured,
                           'reasons': sorted(set(reasons))},
            'nbbo': nbbo, 'inferred': inferred, 'side_proxy': proxy, 'rows': rows,
            'additional_inputs': additional, 'outcome': _outcome_view(evidence.get('outcome_reference')),
            'join_identity': join_identity,
            'candidate_boundary': 'separate_evidence_reference_no_candidate_fields_appended'}


def _path_get(obj, path):
    for key in path.split('.'):
        try:
            obj = obj[int(key)] if isinstance(obj, list) else obj[key]
        except (KeyError, IndexError, TypeError, ValueError):
            return '<missing>'
    return obj


def _patch(obj, changes):
    obj = copy.deepcopy(obj)
    for path, value in changes.items():
        keys = path.split('.')
        parent = obj
        for key in keys[:-1]:
            parent = parent[int(key)] if isinstance(parent, list) else parent[key]
        last = int(keys[-1]) if isinstance(parent, list) else keys[-1]
        parent[last] = copy.deepcopy(value)
    return obj


def run_fixtures(bundle, evaluator=evaluate):
    failures = []
    for case in bundle['cases']:
        evidence = _patch(bundle['base_evidence'], case['changes'])
        policy = _patch(bundle['policy'], case['policy_changes'])
        original_evidence, original_policy = copy.deepcopy(evidence), copy.deepcopy(policy)
        actual = evaluator(evidence, policy)
        if evidence != original_evidence or policy != original_policy:
            failures.append({'case': case['id'], 'path': 'input_immutability', 'expected': True, 'actual': False})
        if evaluator(evidence, policy) != actual:
            failures.append({'case': case['id'], 'path': 'deterministic_output', 'expected': True, 'actual': False})
        for row in actual.get('rows', []):
            matched = [r for r in original_evidence['records'] if r.get('record_id') == row.get('record_id')]
            if row.get('retained_source_record') not in matched:
                failures.append({'case': case['id'], 'path': 'source_field_roundtrip', 'expected': 'original source record', 'actual': row.get('retained_source_record')})
        expected = dict(bundle['common_expect'], **case['expect'])
        for path, want in expected.items():
            got = _path_get(actual, path)
            if got != want or type(got) is not type(want):
                failures.append({'case': case['id'], 'path': path, 'expected': want, 'actual': got})
        for path, values in case['expect_contains'].items():
            got = _path_get(actual, path)
            for value in values:
                if not isinstance(got, list) or value not in got:
                    failures.append({'case': case['id'], 'path': path, 'must_contain': value, 'actual': got})
    return failures


def run_mutations(bundle):
    """Test-only helper replacement. Nothing is written or installed."""
    original_ratio, original_sign = _ratio, _infer_sign

    def zero_unknown_ratio(numerator, denominator):
        value = original_ratio(numerator, denominator)
        return '0' if value is None else value

    def zero_unknown_sign(price, bid, ask):
        sign, reason = original_sign(price, bid, ask)
        return (0 if sign is None else sign), reason

    variants = {
        'unknown_to_zero': {'_ratio': zero_unknown_ratio, '_infer_sign': zero_unknown_sign},
        'future_quote_allowed': {'_causal_quote': lambda quote_time, trade_time: True},
        'publication_ignored': {'_artifact_chain': lambda computed, published, received: computed <= received},
        'unqualified_condition_policy_allowed': {'_condition_policy_ok': lambda policy: True},
        'category_proxy_as_measured': {'_nbbo_basis': lambda basis: True},
        'blanket_multiplier_100': {'_premium': lambda price, quantity, multiplier: price * quantity * Decimal(100)},
        'reconstructed_as_captured': {'_captured_mode': lambda evidence: True},
        'consumer_cutoff_ignored': {'_consumer_cutoff': lambda received, admitted, candidate_decision: True},
        'correction_ignored': {'_correction_resolved': lambda status: True},
        'date_only_artifact_join': {'_join_compatible': lambda left, right: left.get('as_of') == right.get('as_of')},
    }
    if set(bundle['required_mutations']) != set(variants):
        raise ValueError('Fixture mutation inventory disagrees with the implemented test harness')
    results = []
    for name, replacements in variants.items():
        saved = {key: globals()[key] for key in replacements}
        try:
            globals().update(replacements)
            failures = run_fixtures(bundle)
        finally:
            globals().update(saved)
        cases = sorted({failure['case'] for failure in failures})
        results.append({'mutation': name, 'killed': bool(failures), 'failing_cases': cases,
                        'failed_assertions': len(failures)})
    return results


def _load_json(text):
    def reject_constant(value):
        raise ValueError('Nonfinite JSON number')

    def unique_object(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('Duplicate JSON key')
            obj[key] = value
        return obj

    return json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_object)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=Path(__file__).with_name('source-admission-fixtures.json'))
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--mutation-check', action='store_true')
    parser.add_argument('--validate-stdin', action='store_true', help='Read a research {evidence,policy} object; never a candidate feed')
    parser.add_argument('--case')
    args = parser.parse_args()
    if args.validate_stdin:
        try:
            packet = _load_json(sys.stdin.read())
            if not isinstance(packet, dict) or set(packet) != {'evidence', 'policy'}:
                raise ValueError('Wrong research envelope')
            result = evaluate(packet['evidence'], packet['policy'])
        except (ValueError, TypeError):
            result = _invalid_result('INVALID_JSON_RESEARCH_ENVELOPE')
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0 if result['acceptance']['synthetic_contract_pass'] else 2
    bundle = _load_json(args.fixtures.read_text())
    if args.case:
        case = next((c for c in bundle['cases'] if c['id'] == args.case), None)
        if case is None:
            parser.error('Unknown fixture case')
        result = evaluate(_patch(bundle['base_evidence'], case['changes']), _patch(bundle['policy'], case['policy_changes']))
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    failures = run_fixtures(bundle)
    report = {'cases': len(bundle['cases']), 'failed_cases': len({x['case'] for x in failures}),
              'failed_assertions': len(failures), 'examples': failures[:8]}
    if args.mutation_check and not failures:
        report['mutations'] = run_mutations(bundle)
        report['mutation_survivors'] = sum(not x['killed'] for x in report['mutations'])
        # Prove test-only patches were restored before exit.
        report['post_mutation_baseline_failures'] = len(run_fixtures(bundle))
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 1 if failures or report.get('mutation_survivors', 0) or report.get('post_mutation_baseline_failures', 0) else 0


if __name__ == '__main__':
    sys.exit(main())
