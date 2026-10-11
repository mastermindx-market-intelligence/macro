"""Check this research artifact's consistency, not financial truth or product behavior.

Run with Python 3.10+ using the standard library. The adversarial application
specifications are not executed here. No network request or external write occurs.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
JSON_NAME = 'HEALTHCARE_PROVIDER_PAYER_ECONOMICS_R5_EXAMPLES_2026-09-23.json'
MD_NAME = 'HEALTHCARE_PROVIDER_PAYER_ECONOMICS_R5_2026-09-23.md'
RESEARCH_DATE = date(2026, 9, 23)
ARRAYS = ('entities', 'measurements', 'hypothetical_scenarios',
          'research_opportunities', 'source_readiness', 'adversarial_specifications')

class ValidationError(ValueError):
    """A research-artifact invariant failed."""

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)

def dec(value: Any) -> Decimal:
    return Decimal(str(value))

def rounded(value: Decimal, digits: str = '0.1') -> Decimal:
    return value.quantize(Decimal(digits), rounding=ROUND_HALF_UP)

def validate(data: dict[str, Any], markdown: str) -> list[str]:
    require(data['as_of'] == RESEARCH_DATE.isoformat(), 'research-date mismatch')
    require(data['application_case_execution'] == 'NOT_EXECUTED', 'application claim promoted')
    for flag in ('production_validated', 'basket_membership_authorized', 'trading_authorized'):
        require(data[flag] is False, f'{flag} promoted')
    require(json.loads(json.dumps(data)) == data, 'JSON round-trip mismatch')
    sources = data['sources']
    source_ids = {s['id'] for s in sources}
    require(len(source_ids) == len(sources) == 29, 'source count or identity mismatch')
    documented = set(re.findall(r'^- \*\*(R5-S\d+):\*\*', markdown, re.M))
    require(source_ids == documented, 'dossier/source closure mismatch')
    for s in sources:
        require(s['url'].startswith('https://'), 'invalid source URL')
        require(s['full_corpus_acquired'] is False, 'source acquisition promoted')
        require(date.fromisoformat(s['accessed_at']) <= RESEARCH_DATE, 'future source observation')
    entity_keys = {'id', 'name', 'research_role', 'supported_distinction',
                   'next_discriminating_observation', 'sources', 'as_of',
                   'materiality', 'canonical_security'}
    for entity in data['entities']:
        require(set(entity) == entity_keys, 'entity field schema mismatch')
    records = [r for array in ARRAYS for r in data[array]]
    ids = [r['id'] for r in records]
    require(len(ids) == len(set(ids)), 'duplicate research record ID')
    require(len(records) == 87, 'record count mismatch')
    for r in records:
        require(set(r['sources']) <= source_ids, f"unknown source on {r['id']}")
        if 'as_of' in r:
            require(date.fromisoformat(r['as_of']) <= RESEARCH_DATE, 'future observation')
    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if 'value' in obj and obj['value'] is None:
                require(isinstance(obj.get('reason'), str) and bool(obj['reason'].strip()),
                        'null without reason')
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    walk(data)
    for r in data['adversarial_specifications']:
        require(r['execution_status'] == 'NOT_EXECUTED', 'application case promoted')
    for r in data['hypothetical_scenarios']:
        require(r['kind'] == 'explicitly_hypothetical', 'hypothetical flag missing')
        require(r['real_company_calibration'] is False, 'toy scenario promoted')
    for r in data['source_readiness']:
        require(r['bytes_acquired'] is False and r['production_integrated'] is False,
                'source readiness promoted without acquisition')

    by_id = {r['id']: r for r in records}
    m = lambda n: by_id[f'R5-M{n:02d}']['values']
    h = lambda n: by_id[f'R5-H{n:02d}']['inputs']
    checks: list[str] = []
    def check(name: str, condition: bool) -> None:
        require(condition, name)
        checks.append(name)

    a = m(1); premium = a['government_premiums'] + a['commercial_premiums']
    check('CVS premium denominator', a['mbr_denominator'] == 'premium_revenue' and
          rounded(dec(a['health_cost']) / premium * 100) == dec(a['reported_mbr_pct']))
    check('CVS total denominator is not interchangeable',
          abs(dec(a['health_cost']) / a['total_revenue'] * 100 - dec(a['reported_mbr_pct'])) > 1)
    a = m(2)
    check('Molina total-revenue components', sum(a[k] for k in
          ('premiums','premium_tax_revenue','investment_income','other_revenue')) == a['total_revenue'])
    check('Molina premium-tax equality', a['premium_tax_revenue'] == a['premium_tax_expense'])
    check('Molina medical margin and ratio', a['premiums']-a['medical_cost'] == a['medical_margin'] and
          rounded(dec(a['medical_cost'])/a['premiums']*100) == dec(a['reported_mcr_pct']))
    a = m(3)
    check('Cigna business bridges', a['pbs_revenue']+a['specialty_revenue']==a['evernorth_revenue'] and
          a['pbs_adjusted_pretax']+a['specialty_adjusted_pretax']==a['evernorth_adjusted_pretax'])
    check('Cigna revenue and profit directions differ', a['pbs_revenue']>a['pbs_revenue_prior'] and
          a['pbs_adjusted_pretax']<a['pbs_adjusted_pretax_prior'])
    a = m(4)
    check('Privia gross and care margin', a['revenue']-a['provider_expense']-a['amortization']==a['gross_profit'] and
          a['gross_profit']+a['amortization']==a['care_margin'])
    check('Privia EBITDA denominator', a['reported_denominator']=='care_margin' and
          rounded(dec(a['adjusted_ebitda'])/a['care_margin']*100)==dec(a['reported_ebitda_margin_pct']))
    a = m(5)
    check('Privia incurred-paid roll-forward', a['beginning']+a['current_incurred']+a['prior_incurred']-a['paid']==a['ending'])
    a = m(6)
    check('HCA service-period bridge', a['all_revenue']-a['all_expense']==543 and
          a['pre_2026_revenue']-a['pre_2026_expense']==423 and
          (a['all_revenue']-a['pre_2026_revenue'])-(a['all_expense']-a['pre_2026_expense'])==120 and
          a['residual_is_q2_run_rate'] is False)
    a = m(7)
    check('agilon end versus average and consolidation', a['ma_ending']+a['aco_ending']==a['platform_ending'] and
          a['ma_average']!=a['ma_ending'] and a['aco_consolidated'] is False)
    a = m(8)
    check('DaVita treatment-day rounding', rounded(dec(a['treatments'])/a['treatment_days'],'1')==dec(a['reported_treatments_per_day']))
    check('DaVita partial contribution not net profit', dec(a['revenue_per_treatment'])-dec(a['patient_care_cost_per_treatment'])==dec('138.47') and
          a['revenue_minus_patient_cost_is_net_profit'] is False)
    a = m(9)
    check('Cardinal identified-item subtraction only', a['gmpd_segment_profit']-a['identified_refund_profit']==50 and
          a['complete_normalization_claimed'] is False)
    a = m(10)
    check('Evolent overlapping populations', sum(a[k] for k in ('performance_average','technology_average','administrative_average'))>
          a['reported_unique_average'] and a['definitions_allow_cross_category_overlap'] is True)
    check('Evolent future launch not current revenue', a['new_contract_expected_launch']>'2026-09' and
          a['regulatory_conditions'] is True and a['new_contract_is_q2_booked_revenue'] is False)
    a = m(11)
    check('Centene group and available cash distinct', a['group_cash_investments_restricted_m']>a['general_corporate_cash_m'] and
          a['all_group_cash_is_surplus'] is False)
    a = m(12)
    check('UnitedHealth service year distinction', a['majority_service_year']==2026 and
          a['all_development_is_prior_calendar_year'] is False)
    a = m(13)
    check('Humana annual guidance not a quarterly extrapolation', dec(a['h1_adjusted_eps'])>dec(a['full_year_adjusted_eps_floor']) and
          a['full_year_is_guidance'] is True and a['straight_line_annualization_authorized'] is False)
    a = h(1); before=dec(a['premium']-a['claims']-a['administration'])
    after=before-dec(a['claims'])*dec(a['claims_increase_pct'])/100
    check('Toy insured claims sensitivity', before==20 and after==11)
    a = h(2)
    check('Toy fixed unit fee', a['units']*a['fee_per_unit']==200 and a['price_after']<a['price_before'])
    a = h(3)
    check('Toy percentage fee counterexample', dec(a['units']*a['price_before'])*a['fee_pct']/100==200 and
          dec(a['units']*a['price_after'])*a['fee_pct']/100==180)
    a = h(4); factor=1+dec(a['illustrative_discount_pct'])/100
    check('Toy cash timing', rounded(dec(a['cash'])/factor**a['early_year'],'0.01')==dec('90.91') and
          rounded(dec(a['cash'])/factor**a['late_year'],'0.01')==dec('82.64'))
    a = h(5)
    check('Toy share denominator', dec(a['earnings'])/a['shares_before']==1 and
          rounded(dec(a['earnings'])/a['shares_after'],'0.01')==dec('1.11'))
    a = h(6)
    check('Unknown sharing remains unknown', a['retained_share'] is None and bool(a['retained_share_reason']))
    a = h(7)
    check('Toy annualized versus prelaunch', a['annualized_revenue']/a['planned_full_year_months']==25 and
          a['prelaunch_recognized_revenue']==0)
    a = h(8)
    check('Toy earnings and multiple', dec(a['eps_after'])>dec(a['eps_before']) and
          dec(a['eps_before'])*a['multiple_before']==100 and dec(a['eps_after'])*a['multiple_after']==99)
    return checks

def digest(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    blob = b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw
    return {'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1':hashlib.sha1(blob).hexdigest()}

def main() -> int:
    try:
        data = json.loads((ROOT/JSON_NAME).read_text(encoding='utf-8'))
        markdown = (ROOT/MD_NAME).read_text(encoding='utf-8')
        checks = validate(data, markdown)
        corruptions = [
            ('misspelled_entity_field', lambda x: x['entities'][12].update(supported_distinctiontion=x['entities'][12].pop('supported_distinction'))),
            ('duplicate_id', lambda x: x['entities'][1].update(id=x['entities'][0]['id'])),
            ('unknown_source', lambda x: x['entities'][0]['sources'].append('R5-S99')),
            ('future_observation', lambda x: x['entities'][0].update(as_of='2026-09-24')),
            ('authority_promotion', lambda x: x.update(trading_authorized=True)),
            ('wrong_margin_denominator', lambda x: x['measurements'][3]['values'].update(reported_denominator='revenue')),
            ('corrupted_claims', lambda x: x['measurements'][4]['values'].update(paid=142588)),
            ('unproved_download', lambda x: x['source_readiness'][0].update(bytes_acquired=True)),
            ('toy_promoted', lambda x: x['hypothetical_scenarios'][0].update(real_company_calibration=True))]
        rejected=[]
        for name, corrupt in corruptions:
            bad=copy.deepcopy(data); corrupt(bad)
            try:
                validate(bad, markdown)
            except ValidationError:
                rejected.append(name)
            else:
                raise ValidationError(f'corrupted artifact not rejected: {name}')
        print(json.dumps({'validation_scope':'research artifact consistency only', 'result':'PASS',
              'source_count':len(data['sources']), 'research_record_count':sum(len(data[k]) for k in ARRAYS),
              'deterministic_check_count':len(checks),'checks':checks,
              'checker_negative_cases_rejected':rejected,'application_specifications_executed':0,
              'independent_financial_validation':False,'production_proof':False,
              'artifacts':[digest(ROOT/p) for p in (MD_NAME,JSON_NAME,Path(__file__).name)]},indent=2))
        return 0
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(f'RESEARCH ARTIFACT VALIDATION FAILED: {exc}',file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
