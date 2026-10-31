"""Research-artifact consistency checks, not clinical or application acceptance tests."""
from __future__ import annotations
import copy
import hashlib
import json
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'HEALTHCARE_DEVICE_PROCEDURE_ECONOMICS_R4_EXAMPLES_2026-09-23.json'
DOSSIER = ROOT / 'HEALTHCARE_DEVICE_PROCEDURE_ECONOMICS_R4_2026-09-23.md'
ARRAYS = ('entity_examples', 'measurement_examples', 'clinical_examples',
          'access_examples', 'safety_examples', 'hypothetical_scenarios',
          'adversarial_specifications')

class ValidationError(ValueError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)

def dec(value: Any) -> Decimal:
    return Decimal(str(value))

def validate(data: dict[str, Any], markdown: str) -> dict[str, Any]:
    require(data['as_of'] == '2026-09-23', 'Unexpected research date')
    as_of = date.fromisoformat(data['as_of'])
    for flag in ('production_validated', 'basket_membership_authorized', 'trading_authorized'):
        require(data[flag] is False, f'Authority flag changed: {flag}')
    require(data['application_case_execution'] == 'NOT_EXECUTED', 'Application claim changed')
    require(json.loads(json.dumps(data, ensure_ascii=False)) == data, 'Round-trip mismatch')
    sources = {s['id'] for s in data['sources']}
    require(len(sources) == len(data['sources']) == 29, 'Invalid source identity count')
    require(set(re.findall(r'R4-S\d{2}', markdown)) == sources, 'Dossier/source closure mismatch')
    records = [r for name in ARRAYS for r in data[name]]
    ids = [r['id'] for r in records]
    require(len(ids) == len(set(ids)), 'Duplicate research IDs')
    for obj in records + [data['source_probe']]:
        require(set(obj['sources']) <= sources, 'Unknown source reference')
    for source in data['sources']:
        require(source['url'].startswith('https://'), 'Non-HTTPS source URL')
        require(bool(source['acquisition_limits']), 'Missing source limitation')
        if source['publication_date'] is None:
            require(bool(source['publication_date_missing_reason']), 'Unexplained source date')
    for key in ('materiality_default', 'security_identity_default'):
        require(data[key]['value'] is None and bool(data[key]['reason']), 'Unjustified default')
    for record in records:
        if any(value is None for value in record.values()):
            require(bool(record.get('missing_reason')), 'Missing record-level null reason')
    def dates(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                dates(child)
        elif isinstance(value, list):
            for child in value:
                dates(child)
        elif isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            require(date.fromisoformat(value) <= as_of, 'Future observation promoted to current')
    dates(data)
    require(all(c['execution'] == 'NOT_EXECUTED' for c in data['adversarial_specifications']),
            'Adversarial application execution claim changed')
    m = {r['id']: r for r in data['measurement_examples']}
    c = {r['id']: r for r in data['clinical_examples']}
    p = {r['id']: r for r in data['access_examples']}
    h = {r['id']: r for r in data['hypothetical_scenarios']}
    checks: list[str] = []
    def check(name: str, condition: bool) -> None:
        require(condition, name)
        checks.append(name)
    v = m['R4-M01']['values']
    check('lease_subset_reconciliation', v['usage_based_subset'] <= v['operating_leases'] <= v['total']
          and v['operating_leases'] - v['usage_based_subset'] == 123
          and v['total'] - v['operating_leases'] == 214)
    v = m['R4-M02']['values']
    check('distribution_plus_direct', dec(v['distribution']) + dec(v['direct']) == dec(v['total']))
    v = m['R4-M03']['values']
    check('tandem_cash_bridge', dec(v['operating_cash']) - dec(v['cash_capex']) == dec(v['free_cash_flow']))
    check('ebitda_not_cash_or_operating_profit', v['adjusted_ebitda'] > 0 > v['operating_loss']
          and v['free_cash_flow'] < 0)
    v = m['R4-M04']['values']
    check('ge_cash_bridge', v['operating_cash'] - v['cash_capex'] == v['free_cash_flow'])
    check('ge_refund_subtraction_only', v['operating_cash'] - v['cash_refund_included'] - v['cash_capex'] == -39)
    v = m['R4-M05']['values']
    check('ge_rounding_tolerance', abs(v['products'] + v['services'] - v['total']) == v['rounding_tolerance'] == 1)
    check('order_denominators_not_equal', m['R4-M06']['comparison_allowed'] is False)
    check('period_mismatch_and_no_invented_growth', m['R4-M07']['period_end'] != m['R4-M07']['peer_period_end']
          and m['R4-M07']['normalized_growth'] is None)
    v = m['R4-M08']['values']
    growth = ((1 + dec(v['case_growth'])/100) * (1 + dec(v['revenue_per_case_growth'])/100) - 1)*100
    check('uspi_multiplicative_growth', growth == Decimal('5.024400')
          and abs(growth - dec(v['revenue_growth'])) <= dec(v['rounding_tolerance_pp']))
    v = m['R4-M09']['values']
    check('nci_not_cash_distribution', v['adjusted_ebitda'] - v['adjusted_ebitda_less_nci'] == 212
          and m['R4-M09']['nci_cash_distribution'] is None)
    check('arr_not_external_quarter_revenue', m['R4-M10']['external_quarter_revenue'] is None)
    v = m['R4-M11']['values']
    check('philips_percentage_points', dec(v['adjusted_ebita_margin_percent']) - dec(v['refund_effect_pp']) == Decimal('12.2'))
    lo, hi = c['R4-C01']['efficacy_interval_pp']
    check('advent_interval_and_randomized_population', lo < 0 < hi and sum(c['R4-C01']['randomized_n']) == 607)
    check('early_tavr_population', sum(c['R4-C02']['randomized_n']) == c['R4-C02']['total_n'] == 901)
    check('page_observation_not_universal_denial', p['R4-P03']['state'] == 'NO_ENTRIES_DISPLAYED'
          and p['R4-P03']['universal_no_coverage_inference_allowed'] is False)
    check('regulatory_not_automatic_payment', p['R4-P04']['automatic_payer_coverage'] is False
          and p['R4-P05']['new_2026_policy'] is False)
    v = h['R4-H01']['inputs']
    slots = [v['available_minutes']//v[name] for name in ('baseline_cycle_minutes', 'faster_cycle_minutes', 'still_faster_cycle_minutes')]
    check('hypothetical_whole_cycle_and_bottleneck', slots == [4, 4, 5]
          and min(slots[-1], v['staff_recovery_case_cap']) == 4)
    v = h['R4-H02']['inputs']
    contributions = [(v['net_collection_per_case']-v['baseline_variable_cost'])*v['baseline_cases'],
                     (v['net_collection_per_case']-v['new_variable_cost'])*v['same_capacity_cases'],
                     (v['net_collection_per_case']-v['new_variable_cost'])*v['higher_capacity_cases']]
    check('hypothetical_contribution_not_throughput', contributions == [6000, 4400, 5500])
    v = h['R4-H03']['inputs']
    check('hypothetical_patient_time_vs_units', v['paid_patient_days']/v['baseline_wear_days'] == 30
          and v['paid_patient_days']/v['alternative_wear_days'] == 20)
    check('hypothetical_unknown_access_not_true', h['R4-H04']['inputs']['operational_access'] == 'UNKNOWN')
    require(all(s['kind'] == 'HYPOTHETICAL_NOT_EMPIRICAL' for s in data['hypothetical_scenarios']), 'Scenario promoted to observation')
    require(data['source_probe']['live_record_join_proven'] is False
            and data['source_probe']['general_outage_inferred'] is False, 'Probe overstated')
    return {'record_counts':{name:len(data[name]) for name in ARRAYS}, 'unique_record_ids':len(ids),
            'source_count':len(sources),'deterministic_checks_passed':len(checks),'check_names':checks,
            'application_cases_executed':0,'production_validated':False}

def main() -> int:
    try:
        data = json.loads(DATA.read_text(encoding='utf-8'))
        markdown = DOSSIER.read_text(encoding='utf-8')
        result = validate(data, markdown)
        mutations: list[tuple[str, Any]] = [
            ('duplicate_id', lambda d: d['entity_examples'][1].update(id=d['entity_examples'][0]['id'])),
            ('unknown_source', lambda d: d['entity_examples'][0].update(sources=['R4-S99'])),
            ('future_observation', lambda d: d['access_examples'][2].update(observed_on='2026-09-24')),
            ('authority_promotion', lambda d: d.update(trading_authorized=True)),
            ('lease_corruption', lambda d: d['measurement_examples'][0]['values'].update(usage_based_subset=999)),
            ('cash_corruption', lambda d: d['measurement_examples'][2]['values'].update(free_cash_flow=1)),
        ]
        rejected = []
        for name, mutate in mutations:
            altered = copy.deepcopy(data)
            mutate(altered)
            try:
                validate(altered, markdown)
            except ValidationError:
                rejected.append(name)
            else:
                raise ValidationError(f'Corruption not detected: {name}')
        result['deliberately_corrupted_artifacts_rejected'] = rejected
        result['files'] = {}
        for path in (DOSSIER, DATA, Path(__file__)):
            raw = path.read_bytes()
            result['files'][path.name] = {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(),
                'git_blob_sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Research artifact validation failed: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
