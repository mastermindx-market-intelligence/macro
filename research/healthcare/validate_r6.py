"""Validate R6 research-file consistency, not source truth or product behavior.

Python 3.10+ standard library only. No network or external writes. The application
specifications remain NOT_EXECUTED. Negative cases alter local in-memory copies.
"""
from __future__ import annotations
import copy
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

P = Path(__file__).with_name('HEALTHCARE_COVERAGE_RELEASE_R6_EXAMPLES_2026-09-23.json')
D = Decimal


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(x: dict) -> list[str]:
    require(date.fromisoformat(x['as_of']) == date(2026, 9, 23), 'research date')
    require(x['operation_key'] == 'gmi-healthcare-deep-research-20260923-sol-001', 'operation')
    for key in ('production_validated', 'design_accepted', 'fable_dispatch_authorized',
                'basket_membership_authorized', 'trading_authorized'):
        require(x[key] is False, 'authority: ' + key)
    require(x['application_case_execution'] == 'NOT_EXECUTED', 'application execution')
    sources = set(x['source_ids'])
    require(sources == {f'R6-S{i:02}' for i in range(1, 18)}, 'source registry')
    require(set(x['source_limits']) <= sources, 'source limits')
    arrays = ('coverage_families', 'mechanism_examples', 'measurements', 'gates', 'application_specifications')
    records = [r for k in arrays for r in x[k]] + [x['hypothetical_scenario']]
    ids = [r['id'] for r in records]
    require(len(ids) == len(set(ids)) == 59, 'record count/uniqueness')
    for r in records:
        require(set(r.get('sources', [])) <= sources, 'unknown source')
        for k in ('observation_date',):
            if k in r:
                require(date.fromisoformat(r[k]) <= date.fromisoformat(x['as_of']), 'future observation')
        for k, v in r.items():
            if v is None:
                require(bool(r.get('null_reason')), 'unexplained null')
    require(x['materiality']['value'] is None and bool(x['materiality']['reason']), 'materiality')
    families = x['coverage_families']
    require(len(families) == 12 and len({r['name'] for r in families}) == 12, 'family coverage')
    mechanisms = {r['id'] for r in x['mechanism_examples']}
    for r in families:
        require(r['coverage'] == 'SELECTED_RESEARCH_ONLY' and bool(r['remaining_gap']), 'coverage promotion')
        require(set(r['new_mechanisms']) <= mechanisms, 'unknown mechanism')
        require(r['canonical_theme_id'] is None, 'canonical family promotion')
    c = x['candidate']
    require(c['existing_theme_id'] == 'glp1_obesity' and c['existing_route'] == 'state_of_themes.html', 'incumbent identity')
    require(c['new_canonical_theme_ids'] == [] and c['approval_state'] == 'PROPOSED_FOR_REVIEW', 'candidate promotion')
    require(c['valuation_claim_allowed'] is False, 'valuation claim')
    gates = {r['id']: r for r in x['gates']}
    require(len(gates) == 8, 'gate count')
    done: set[str] = set()
    active: set[str] = set()
    def visit(key: str) -> None:
        require(key in gates, 'unknown dependency')
        require(key not in active, 'cyclic dependency')
        if key in done:
            return
        active.add(key)
        require(gates[key]['satisfied'] is False, 'unproved gate promotion')
        for dep in gates[key]['depends_on']:
            visit(dep)
        active.remove(key)
        done.add(key)
    for key in gates:
        visit(key)
    require(gates['R6-G06']['phase'] == 'DESIGN_REVIEW', 'design before build')
    require(gates['R6-G08']['phase'] == 'RELEASE_ACCEPTANCE', 'browser release stage')
    require(all(r['execution'] == 'NOT_EXECUTED' for r in x['application_specifications']), 'application promotion')
    n = {r['id']: r for r in x['measurements']}
    passed: list[str] = []
    def check(name: str, condition: bool) -> None:
        require(condition, name)
        passed.append(name)
    a=n['R6-N01']
    check('immunology component reconciliation', sum(map(D,a['components'])) == D(a['total']) == D('8786'))
    a=n['R6-N02']
    old=sum(map(D,a['old_range']))/2
    new=sum(map(D,a['new_range']))/2
    check('guidance midpoint bridge', new-old == D(a['operating_change'])+D(a['proposed_deal_change']) == D('-0.04'))
    a=n['R6-N03']
    check('collaboration component reconciliation', D(a['profit_participation'])+D(a['manufacturing_reimbursement']) == D(a['total']) == D('2174.3'))
    check('no inferred universal royalty', a['universal_royalty_rate'] is None)
    a=n['R6-N04']
    ratio=(D(a['net_awards'])/D(a['revenue'])).quantize(D('0.01'), rounding=ROUND_HALF_UP)
    step=D(a['display_precision_millions'])/2
    low=(D(a['net_awards'])-step)/(D(a['revenue'])+step)
    high=(D(a['net_awards'])+step)/(D(a['revenue'])-step)
    reported=D(a['rounded_reported'])
    check('reported ratio compatible with input precision', ratio == D(a['displayed_quotient_rounded']) == D('1.12') and reported == D('1.13') and low < reported+D('.005') and high >= reported-D('.005') and a['precision_relation']=='COMPATIBLE_NOT_EXACT_REPRODUCTION')
    check('unknown comparable clinician productivity', n['R6-N05']['same_clinician_productivity'] is None)
    a=n['R6-N06']
    check('requested duration not approved', a['current_duration_years']==3 and a['requested_duration_years']==6 and a['requested_duration_approved'] is False and a['current_paid_adoption'] is None)
    a=n['R6-N07']
    check('in-progress appraisal not final funding', a['project_status']=='IN_PROGRESS' and a['expected_publication'] is None and a['historical_draft_is_current_guidance'] is False and a['funding_conclusion']=='NOT_ESTABLISHED')
    a=n['R6-N08']
    check('issuer-specific threshold', a['issuer']=='Zoetis' and D(a['value'])==D('100') and a['universal_definition'] is False)
    h=x['hypothetical_scenario']
    check('hypothetical not empirical', h['empirical'] is False and h['company_calibrated'] is False)
    before=D(h['patient_months_before'])*D(h['net_revenue_per_patient_month_before'])
    after=D(h['patient_months_after'])*D(h['net_revenue_per_patient_month_after'])
    check('hypothetical revenue bridge', before==D(h['revenue_before'])==D('10000') and after==D(h['revenue_after'])==D('10200'))
    check('hypothetical retained contribution', before*D(h['contribution_margin_before'])==D(h['contribution_before'])==D('6000') and after*D(h['contribution_margin_after'])==D(h['contribution_after'])==D('5610'))
    return passed


def main() -> None:
    raw=P.read_bytes()
    x=json.loads(raw)
    require(json.loads(json.dumps(x)) == x, 'JSON round trip')
    checks=validate(x)
    mutations = {
        'duplicate record': lambda q: q['coverage_families'][0].update(id='R6-F02'),
        'unknown source': lambda q: q['mechanism_examples'][0].update(sources=['UNKNOWN']),
        'future observation': lambda q: q['measurements'][5].update(observation_date='2026-09-24'),
        'authority promotion': lambda q: q.update(trading_authorized=True),
        'false full coverage': lambda q: q['coverage_families'][0].update(coverage='COMPLETE'),
        'requested approval promotion': lambda q: q['measurements'][5].update(requested_duration_approved=True),
        'dependency cycle': lambda q: q['gates'][0].update(depends_on=['R6-G08']),
        'toy promoted to observation': lambda q: q['hypothetical_scenario'].update(empirical=True),
        'incompatible rounded ratio': lambda q: q['measurements'][3].update(rounded_reported='1.14'),
        'corrupted contribution': lambda q: q['hypothetical_scenario'].update(contribution_after='6000'),
    }
    rejected=[]
    for name, mutate in mutations.items():
        q=copy.deepcopy(x)
        mutate(q)
        try:
            validate(q)
        except (ValueError, KeyError, TypeError):
            rejected.append(name)
        else:
            raise ValueError('negative case was not rejected: '+name)
    print(json.dumps({'result':'PASS','scope':'research-artifact consistency only','records':59,'sources':17,
        'deterministic_checks':checks,'rejected_corruptions':rejected,'application_cases_executed':0,
        'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
        'git_blob_sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()},indent=2))

if __name__=='__main__':
    main()
