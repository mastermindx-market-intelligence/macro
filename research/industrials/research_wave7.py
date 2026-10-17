"""Authored research examples, not a production gate, backtest or trading rule."""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date
from fractions import Fraction
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def pct(new: float, old: float) -> float:
    if not all(math.isfinite(x) for x in (new, old)) or old <= 0:
        raise ValueError('Finite amounts and a positive comparison denominator required')
    return 100 * (new / old - 1)

@dataclass(frozen=True)
class Observation:
    issuer: str
    period: str
    metric: str
    basis: str
    denominator: str
    unit: str
    role: str
    published: str | None
    observed: str
    value: float | None
    numeric: bool = True
    archived_before_event: bool = False


def comparison_status(estimate: Observation, actual: Observation) -> str:
    """Narrow illustrative semantics only; dates are explicitly day-grain."""
    if any(getattr(estimate, k) != getattr(actual, k) for k in
           ('issuer', 'period', 'metric', 'basis', 'denominator', 'unit')):
        return 'INCOMPATIBLE_MEASUREMENT'
    if estimate.role not in ('external_poll', 'management_guidance') or actual.role != 'actual':
        return 'WRONG_STATEMENT_ROLES'
    if not estimate.numeric or not actual.numeric or estimate.value is None or actual.value is None:
        return 'NON_NUMERIC_OR_MISSING'
    if not all(math.isfinite(x) for x in (estimate.value, actual.value)):
        return 'NON_NUMERIC_OR_MISSING'
    if estimate.published is None or actual.published is None:
        return 'PUBLICATION_UNKNOWN'
    ep, ap = date.fromisoformat(estimate.published), date.fromisoformat(actual.published)
    if ep > ap:
        return 'AFTER_RESULT'
    if ep == ap:
        return 'INTRADAY_ORDER_UNPROVEN'
    # A later collector refresh cannot replace the source's published clock.
    return 'RETROSPECTIVE_DAY_GRAIN_ONLY'


def price_study_status(estimate: Observation, timestamps: bool, price_binding: bool,
                       confounder_resolved: bool, rights: bool) -> str:
    if not estimate.archived_before_event:
        return 'NATIVE_VINTAGE_NOT_PROVEN'
    if not timestamps:
        return 'EVENT_TIME_NOT_PROVEN'
    if not price_binding:
        return 'PRICE_BINDING_NOT_PROVEN'
    if not confounder_resolved:
        return 'CONFOUNDER_UNRESOLVED'
    if not rights:
        return 'RIGHTS_NOT_PROVEN'
    return 'INPUTS_PRESENT_NOT_PREDICTIVE_PROOF'


def run() -> dict:
    checks: list[dict] = []
    def check(name: str, ok: bool) -> None:
        checks.append({'name': name, 'passed': bool(ok)})
    def close(name: str, actual: float, expected: float) -> None:
        check(name, math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10))

    outputs = {
        'research_only': True,
        'cutoff': '2026-09-23',
        'external_poll_case': {
            'issuer': 'SGS', 'period': 'H1 2026', 'contributors': 6,
            'estimate_source': 'W7-S05', 'actual_source': 'W7-S03',
            'estimate_day': '2026-07-23', 'actual_day': '2026-07-24',
            'sales_expected_chf_m': 3633, 'sales_actual_chf_m': 3683,
            'sales_difference_chf_m': 3683-3633,
            'sales_difference_pct': pct(3683, 3633),
            'organic_expected_pct': 5.3, 'organic_actual_pct': 5.6,
            'organic_difference_basis_points': (5.6-5.3)*100,
            'margin_expected_pct': 15.1, 'margin_actual_pct': 15.1,
            'margin_difference_basis_points': 0,
            'actual_adjusted_ebit': None,
            'intraday_publication_timezone': None,
            'native_pre_event_retention': False,
        },
        'management_guidance_case': {
            'issuer': 'Exponent', 'period': 'fiscal Q2 2026',
            'estimate_source': 'W7-S10', 'actual_source': 'W7-S11',
            'estimate_day': '2026-04-30', 'actual_day': '2026-07-30',
            'forecast_ebitda_margin_range_pct': [27.0, 27.8],
            'reported_rounded_margin_pct': 28.7,
            'margin_above_guidance_upper_bp': (28.7-27.8)*100,
            'net_sales_growth_pct': pct(148860,132868),
            'gross_sales_growth_pct': pct(171612,141962),
            'ebitda_to_net_sales_pct': 100*42728/148860,
            'ebitda_to_gross_sales_pct': 100*42728/171612,
            'forecast_revenue_phrase': 'high-single digits',
            'forecast_revenue_numeric_value': None,
            'full_intervening_disclosure_census': False,
        },
        'ul': {
            'source': 'W7-S01; W7-S02',
            'ongoing_share_2025_pct': 100*1006/3053,
            'initial_share_2025_pct': 100*851/3053,
            'initial_growth_2025_pct': pct(851,784),
            'ongoing_growth_2025_pct': pct(1006,953),
            'ongoing_to_initial_revenue_ratio':1006/851,
            'implied_retention': None,
            'h1_cfo_increase_usd_m':379-301,
            'h1_capex_increase_usd_m':138-93,
            'h1_fcf_increase_usd_m':241-208,
            'h1_fcf_growth_pct':pct(241,208),
            'h1_capex_growth_pct':pct(138,93),
        },
        'hypothetical_cohort_identification': {
            'opening_programs':1000, 'fee_each':100,
            'world_a_retained':950, 'world_a_new':50,
            'world_b_retained':700, 'world_b_new':300,
            'world_a_revenue':(950+50)*100,
            'world_b_revenue':(700+300)*100,
            'world_a_retention':.95,'world_b_retention':.70,
            'note':'Same aggregate revenue does not identify retention; not calibrated to UL.',
        },
        'sgs_cash_conditional_reconstruction': {
            'source':'W7-S03', 'current_fcf_chf_m':260,
            'derived_prior_ex_disposal':260/1.25,
            'prior_disposal_proceeds':80,
            'conditional_prior_including_disposal':260/1.25+80,
            'conditional_reported_growth_pct':pct(260,260/1.25+80),
            'use':'Illustration assuming stated percentage exact and no other basis changes; not a newly read financial table.',
        },
    }
    s = outputs['external_poll_case']; e = outputs['management_guidance_case']; u = outputs['ul']
    close('SGS revenue deviation exact fraction',s['sales_difference_pct'],float(Fraction(5000,3633)))
    close('SGS organic difference is 30bp',s['organic_difference_basis_points'],30)
    check('SGS margin on reported precision is unchanged',s['margin_difference_basis_points']==0)
    check('unread actual EBIT remains absent',s['actual_adjusted_ebit'] is None)
    close('EXPO net growth exact fraction',e['net_sales_growth_pct'],float(Fraction(1599200,132868)))
    close('EXPO gross growth exact fraction',e['gross_sales_growth_pct'],float(Fraction(2965000,141962)))
    close('EXPO net margin exact fraction',e['ebitda_to_net_sales_pct'],float(Fraction(4272800,148860)))
    close('EXPO gross margin exact fraction',e['ebitda_to_gross_sales_pct'],float(Fraction(4272800,171612)))
    close('EXPO rounded margin relative to upper guidance',e['margin_above_guidance_upper_bp'],90)
    check('qualitative outlook not coerced',e['forecast_revenue_numeric_value'] is None)
    close('UL ongoing revenue share',u['ongoing_share_2025_pct'],float(Fraction(100600,3053)))
    close('UL cash bridge',u['h1_cfo_increase_usd_m']-u['h1_capex_increase_usd_m'],u['h1_fcf_increase_usd_m'])
    check('UL revenue ratio is not retention',u['implied_retention'] is None)
    h=outputs['hypothetical_cohort_identification']
    check('equal aggregate revenue',h['world_a_revenue']==h['world_b_revenue'])
    check('unequal retention',h['world_a_retention']!=h['world_b_retention'])
    close('different replacement intensity',h['world_b_new']/h['world_a_new'],6)
    close('conditional cash comparator',outputs['sgs_cash_conditional_reconstruction']['conditional_prior_including_disposal'],288)

    est=Observation('SGS','H1 2026','revenue','reported','group','CHF_m','external_poll','2026-07-23','2026-09-23',3633)
    act=replace(est,role='actual',published='2026-07-24',value=3683)
    check('external snapshot comparison is limited',comparison_status(est,act)=='RETROSPECTIVE_DAY_GRAIN_ONLY')
    for field,value in [('issuer','UL'),('period','FY2026'),('metric','EBIT'),('basis','organic'),('denominator','segment'),('unit','USD_m')]:
        check('reject incompatible '+field,comparison_status(est,replace(act,**{field:value}))=='INCOMPATIBLE_MEASUREMENT')
    check('management is a separate permitted role',comparison_status(replace(est,role='management_guidance'),act)=='RETROSPECTIVE_DAY_GRAIN_ONLY')
    check('post-result estimate rejected',comparison_status(replace(est,published='2026-07-25'),act)=='AFTER_RESULT')
    check('same day lacks order',comparison_status(replace(est,published='2026-07-24'),act)=='INTRADAY_ORDER_UNPROVEN')
    check('missing publication refused',comparison_status(replace(est,published=None),act)=='PUBLICATION_UNKNOWN')
    check('qualitative value refused',comparison_status(replace(est,numeric=False,value=None),act)=='NON_NUMERIC_OR_MISSING')
    check('latest refresh does not make archive',price_study_status(est,True,True,True,True)=='NATIVE_VINTAGE_NOT_PROVEN')
    archived=replace(est,archived_before_event=True)
    check('missing event time held',price_study_status(archived,False,True,True,True)=='EVENT_TIME_NOT_PROVEN')
    check('unbound prices held',price_study_status(archived,True,False,True,True)=='PRICE_BINDING_NOT_PROVEN')
    check('takeover confound held',price_study_status(archived,True,True,False,True)=='CONFOUNDER_UNRESOLVED')
    check('rights held',price_study_status(archived,True,True,True,False)=='RIGHTS_NOT_PROVEN')
    check('complete inputs still not predictive proof',price_study_status(archived,True,True,True,True)=='INPUTS_PRESENT_NOT_PREDICTIVE_PROOF')
    for new,old in [(2,0),(2,-1),(float('nan'),2),(2,float('inf'))]:
        try: pct(new,old)
        except ValueError: ok=True
        else: ok=False
        check('invalid percent input '+repr((new,old)),ok)
    outputs['verification']={'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'checks':checks}
    return outputs

if __name__ == '__main__':
    result=run()
    (ROOT/'WAVE7_CALCULATIONS_AND_CHECKS.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result['verification'].items() if k!='checks'}))
    if result['verification']['failed']:
        print(json.dumps([x for x in result['verification']['checks'] if not x['passed']],indent=2))
        raise SystemExit(1)
