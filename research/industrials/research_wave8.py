"""Original research arithmetic; no forecasts, trading or production admission logic."""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date
from fractions import Fraction
import json
import math
from pathlib import Path


def finite(*xs: float) -> None:
    if not all(math.isfinite(x) for x in xs):
        raise ValueError('finite inputs required')


def pct(new: float, old: float) -> float:
    finite(new, old)
    if old <= 0:
        raise ValueError('positive comparison denominator required')
    return (new / old - 1) * 100


def staffing(hours: float, bill: float, wage: float, burden: float, fixed: float,
             wage_rise: float = 0, repricing_lag_months: float = 0) -> dict:
    finite(hours, bill, wage, burden, fixed, wage_rise, repricing_lag_months)
    if min(hours, bill, wage, burden, fixed) < 0 or wage_rise < 0:
        raise ValueError('nonnegative economic inputs required')
    if not 0 <= repricing_lag_months <= 12:
        raise ValueError('lag must be within year')
    new_wage = wage * (1 + wage_rise)
    # Same-dollar recovery of wage inflation, not preservation of percentage margin.
    average_bill = bill + (new_wage - wage) * (1 - repricing_lag_months / 12)
    revenue = hours * average_bill
    gross = revenue - hours * (new_wage + burden)
    return dict(revenue=revenue, gross_profit=gross, contribution=gross-fixed,
                gross_margin_pct=100*gross/revenue if revenue else None)


def incremental_receivables(annual_credit_revenue: float, dso_change: float) -> float:
    finite(annual_credit_revenue, dso_change)
    if annual_credit_revenue < 0:
        raise ValueError('revenue must be nonnegative')
    return annual_credit_revenue / 365 * dso_change


def float_yield(principal: float, fixed_weight: float, fixed_yield: float,
                short_yield: float, maturing_weight: float = 0,
                new_yield: float | None = None) -> dict:
    values = [principal, fixed_weight, fixed_yield, short_yield, maturing_weight]
    if new_yield is not None:
        values.append(new_yield)
    finite(*values)
    if principal < 0 or not 0 <= maturing_weight <= fixed_weight <= 1:
        raise ValueError('invalid principal or portfolio weights')
    if maturing_weight and new_yield is None:
        raise ValueError('maturing portion requires reinvestment yield')
    blended = ((fixed_weight-maturing_weight)*fixed_yield +
               maturing_weight*(new_yield or 0) + (1-fixed_weight)*short_yield)
    return dict(interest=principal*blended, blended_yield=blended,
                client_principal_in_enterprise_excess_cash=0)


def automation(volume: float, base_price: float, base_cost: float, fixed: float,
               labor_saving: float, tool_cost: float, concession: float,
               migration: float) -> dict:
    finite(volume, base_price, base_cost, fixed, labor_saving, tool_cost, concession, migration)
    if min(volume, base_price, base_cost, fixed, labor_saving, tool_cost, concession, migration) < 0:
        raise ValueError('negative inputs not allowed')
    if labor_saving > base_cost or concession > base_price:
        raise ValueError('invalid saving or concession')
    revenue = volume*(base_price-concession)
    steady = revenue-volume*(base_cost-labor_saving+tool_cost)-fixed
    return dict(revenue=revenue, steady_contribution=steady,
                first_year_contribution=steady-migration)


def effective_slots(fleet_slots: float, round_trip_days: float, load_factor: float) -> float:
    finite(fleet_slots, round_trip_days, load_factor)
    if fleet_slots < 0 or round_trip_days <= 0 or not 0 <= load_factor <= 1:
        raise ValueError('invalid capacity assumptions')
    return fleet_slots*365/round_trip_days*load_factor


@dataclass(frozen=True)
class Expectation:
    subject: str
    period: str
    metric: str
    basis: str
    currency: str
    value: float
    source_time: date | None
    observed_time: date | None
    kind: str = 'external_aggregate'


def paired_gap(expected: Expectation, actual: Expectation) -> dict:
    # Deliberately narrow research fixture, NOT a production comparator.
    keys = ('subject', 'period', 'metric', 'basis', 'currency')
    if any(getattr(expected, k) != getattr(actual, k) for k in keys):
        raise ValueError('incompatible measures')
    if expected.source_time is None or actual.source_time is None:
        raise ValueError('unknown publication time')
    if expected.source_time >= actual.source_time:
        raise ValueError('expectation must precede outcome')
    if expected.kind != 'external_aggregate':
        raise ValueError('not an external aggregate')
    # Retrospective comparison allowed; historical native retention is a separate result.
    pre_event_retention = (expected.observed_time is not None and
                           expected.observed_time < actual.source_time)
    return dict(gap_pct=pct(actual.value, expected.value),
                native_pre_event_observation_proved=pre_event_retention,
                predictive_validation=False, time_precision='day_only')


def calculations() -> dict:
    manpower_bridge = dict(gross_profit=780.3-763.7, sga=700.3-668.3, impairment=88.7)
    trinet_bridge = dict(insurance=(1007-867)-(1048-947),
                        professional=159-172, interest=12-18,
                        other_cost_savings=(1187-947)-(1104-867))
    adp_net = 1354.8+278.1-318.3
    adp_prior = 1189.1+225.3-341.1
    cnx = dict(quarter_fcf=257.891-48.174, prior_quarter_fcf=236.536-55.792,
               quarter_adjusted_fcf=257.891-48.174+32.607,
               prior_quarter_adjusted_fcf=236.536-55.792+19.542,
               h1_fcf_growth_pct=pct(72.595,131.534))
    exp = Expectation('Randstad','2026Q2','EBITA','underlying_ex_exceptionals','EURm',175,
                      date(2026,7,9),
                      date(2026,9,23))
    act = replace(exp,value=182,source_time=date(2026,7,22))
    return dict(
        source_numbers=dict(
            manpower_revenue_growth_pct=pct(4860.2,4519.3),
            manpower_gp_growth_pct=pct(780.3,763.7),
            manpower_operating_change=112-(-25.3), manpower_bridge=manpower_bridge,
            trinet_pretax_change=74-51,trinet_bridge=trinet_bridge,
            trinet_wse_growth_pct=pct(297615,336010),
            adp_peo_ex_benefits_current=7128.1-4607.3,
            adp_peo_ex_benefits_prior=6690.4-4289.0,
            adp_peo_ex_benefits_growth_pct=pct(7128.1-4607.3,6690.4-4289.0),
            adp_net_interest_strategy=adp_net,adp_prior_net_interest_strategy=adp_prior,
            adp_net_strategy_growth_pct=pct(adp_net,adp_prior),
            paychex_gaap_change=619.2-541.9,paychex_adjusted_change=684.7-626.7,
            paychex_adjustment_shrink=(626.7-541.9)-(684.7-619.2),
            concentrix=cnx,randstad_revenue_gap_pct=pct(5897,5798),
            randstad_ebita_gap_pct=pct(182,175),
            maersk_naive_volume_rate_pct=((1.041*1.22)-1)*100),
        hypothetical=dict(
            staffing_base=staffing(100000,30,22,3,200000),
            staffing_immediate_reprice=staffing(100000,30,22,3,200000,.1,0),
            staffing_lagged=staffing(100000,30,22,3,200000,.1,3),
            additional_receivables=incremental_receivables(3000000,15),
            float_before=float_yield(100,.8,.02,.05),
            float_after=float_yield(100,.8,.02,.04,.2,.04),
            automation_before=automation(1000000,5,3,500000,0,0,0,0),
            automation_after=automation(1000000,5,3,500000,1,.3,.4,400000),
            automation_volume_down=automation(800000,5,3,500000,1,.3,.4,400000),
            commissioning_before=dict(ebitda=100,depreciation=20,expensed_interest=10,
                pretax_profit=70,capitalized_interest=20,total_cash_interest=30,
                cash_asset_spend_ex_interest=120,pretax_cash_proxy=-50),
            commissioning_after=dict(ebitda=110,depreciation=35,expensed_interest=30,
                pretax_profit=45,capitalized_interest=0,total_cash_interest=30,
                cash_asset_spend_ex_interest=40,pretax_cash_proxy=40),
            slots_40_days=effective_slots(100000,40,.9),
            slots_50_days=effective_slots(100000,50,.9)),
        expectation_example=paired_gap(exp,act))


def verify() -> dict:
    d = calculations(); s=d['source_numbers']; h=d['hypothetical']; tests=[]
    def check(name, truth):
        tests.append(dict(name=name,passed=bool(truth)))
    def near(name, value, target, tol=1e-8):
        check(name, math.isclose(value,target,rel_tol=tol,abs_tol=tol))
    def rejects(name, fn):
        try:
            fn()
        except ValueError:
            check(name,True)
        else:
            check(name,False)
    near('Manpower revenue arithmetic',s['manpower_revenue_growth_pct'],float(Fraction(34090,45193)*10))
    near('Manpower profit bridge',sum(s['manpower_bridge'].values()),s['manpower_operating_change'])
    check('Manpower gross profit grew slower than revenue',s['manpower_gp_growth_pct']<s['manpower_revenue_growth_pct'])
    near('TriNet insurance contribution change',s['trinet_bridge']['insurance'],39)
    near('TriNet pretax bridge',sum(s['trinet_bridge'].values()),23)
    check('TriNet workforce declined',s['trinet_wse_growth_pct']<0)
    near('ADP ex-benefits current',s['adp_peo_ex_benefits_current'],2520.8)
    near('ADP ex-benefits prior',s['adp_peo_ex_benefits_prior'],2401.4)
    near('ADP net strategy current',s['adp_net_interest_strategy'],1314.6)
    near('ADP net strategy prior',s['adp_prior_net_interest_strategy'],1073.3)
    near('Paychex adjustment-change bridge',s['paychex_adjusted_change']+s['paychex_adjustment_shrink'],s['paychex_gaap_change'])
    near('Concentrix FCF',s['concentrix']['quarter_fcf'],209.717)
    near('Concentrix adjusted FCF',s['concentrix']['quarter_adjusted_fcf'],242.324)
    check('Concentrix opposite quarter and half-year cash directions',s['concentrix']['quarter_fcf']>s['concentrix']['prior_quarter_fcf'] and s['concentrix']['h1_fcf_growth_pct']<0)
    near('Randstad EBITA gap',s['randstad_ebita_gap_pct'],4)
    near('Randstad revenue gap',s['randstad_revenue_gap_pct'],float(Fraction(9900,5798)))
    check('Maersk mismatched headline bridge retained',abs(s['maersk_naive_volume_rate_pct']-23)>1)
    near('Staffing baseline contribution',h['staffing_base']['contribution'],300000)
    near('Same-dollar repricing preserves absolute profit',h['staffing_immediate_reprice']['contribution'],300000)
    check('Same-dollar repricing lowers percentage margin',h['staffing_immediate_reprice']['gross_margin_pct']<h['staffing_base']['gross_margin_pct'])
    near('Lagged contribution',h['staffing_lagged']['contribution'],245000)
    near('Funding impact',h['additional_receivables'],float(Fraction(3000000*15,365)))
    near('Float initial interest',h['float_before']['interest'],2.6)
    near('Float subsequent interest',h['float_after']['interest'],2.8)
    near('Client principal excluded from excess cash',h['float_after']['client_principal_in_enterprise_excess_cash'],0)
    near('Automation original contribution',h['automation_before']['steady_contribution'],1500000)
    near('Automation first-year contribution',h['automation_after']['first_year_contribution'],1400000)
    near('Automation steady contribution',h['automation_after']['steady_contribution'],1800000)
    near('Automation lower-volume contribution',h['automation_volume_down']['first_year_contribution'],940000)
    check('Commissioning profit and cash can diverge',h['commissioning_after']['pretax_profit']<h['commissioning_before']['pretax_profit'] and h['commissioning_after']['pretax_cash_proxy']>h['commissioning_before']['pretax_cash_proxy'])
    near('Vessel effective capacity decline',h['slots_50_days']/h['slots_40_days'],.8)
    check('Retrospective comparison not pre-event retention',not d['expectation_example']['native_pre_event_observation_proved'])
    check('Retrospective comparison not predictive proof',not d['expectation_example']['predictive_validation'])
    rejects('Negative denominator',lambda:pct(1,-1))
    rejects('Nonfinite input',lambda:pct(float('nan'),1))
    rejects('Lag outside year',lambda:staffing(1,3,2,0,0,.1,13))
    rejects('Negative staffing input',lambda:staffing(-1,3,2,0,0))
    rejects('Invalid portfolio weights',lambda:float_yield(1,.5,.02,.04,.7,.03))
    rejects('Missing reinvestment rate',lambda:float_yield(1,.5,.02,.04,.2))
    rejects('Impossible cost saving',lambda:automation(1,5,3,0,4,0,0,0))
    rejects('Impossible price concession',lambda:automation(1,5,3,0,1,0,6,0))
    rejects('Invalid vessel cycle',lambda:effective_slots(100,0,.8))
    rejects('Invalid load factor',lambda:effective_slots(100,30,1.1))
    e=Expectation('x','2026Q2','EBITA','adjusted','EURm',175,date(2026,7,9),None)
    a=replace(e,value=182,source_time=date(2026,7,22))
    for field, value in [('subject','y'),('period','2026Q1'),('metric','net_income'),('basis','statutory'),('currency','USDm')]:
        rejects('Mismatch '+field,lambda f=field,v=value:paired_gap(e,replace(a,**{f:v})))
    rejects('Future expectation',lambda:paired_gap(replace(e,source_time=date(2026,8,1)),a))
    rejects('Same-day order unknown',lambda:paired_gap(replace(e,source_time=date(2026,7,22)),a))
    rejects('Unknown publication',lambda:paired_gap(replace(e,source_time=None),a))
    rejects('Guidance is not external aggregate',lambda:paired_gap(replace(e,kind='management_guidance'),a))
    check('Earlier native observation control',paired_gap(replace(e,observed_time=date(2026,7,10)),a)['native_pre_event_observation_proved'])
    failed=[t['name'] for t in tests if not t['passed']]
    return dict(passed=len(tests)-len(failed),failed=len(failed),failures=failed,checks=tests,
                limits='Authored research checks; no independent factual review, application test or empirical investment validation.')


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    result=verify()
    (root/'WAVE8_CALCULATIONS.json').write_text(json.dumps(calculations(),indent=2)+'\n')
    (root/'WAVE8_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','failed','failures')},indent=2))
    raise SystemExit(1 if result['failed'] else 0)
