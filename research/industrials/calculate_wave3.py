"""Research arithmetic only. No product signal, valuation target or trading action."""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def pct(new: float, old: float) -> float:
    if old <= 0:
        raise ValueError('Growth comparison requires a positive base')
    return 100.0 * (new / old - 1.0)

def pv_annuity(rate: float, years: int) -> float:
    if rate <= -1 or years <= 0:
        raise ValueError('Invalid horizon or discount rate')
    return sum((1.0 + rate) ** -t for t in range(1, years + 1))

def asset_case(cost: float, annual_cash: float, residual: float, years: int = 5, rate: float = .09) -> dict:
    if min(cost, residual) < 0:
        raise ValueError('Negative asset price or residual')
    af = pv_annuity(rate, years)
    salvage_pv = residual / (1 + rate) ** years
    capital_annuity = (cost - salvage_pv) / af
    return dict(cost=cost, annual_cash=annual_cash, residual=residual, years=years,
                rate=rate, pv_annuity=af, npv=annual_cash * af + salvage_pv - cost,
                capital_annuity=capital_annuity, annual_surplus=annual_cash - capital_annuity)

def replacement_case(old_value: float) -> dict:
    # Mutually exclusive alternatives at an identical workload and five-year horizon.
    # Opportunity value of the owned old asset is included; no second trade-in credit.
    rate, years = .08, 5
    af = pv_annuity(rate, years)
    old_pv = old_value + 10 + 30 * af - 30 / (1 + rate) ** years
    new_pv = 200 + 12 * af - 90 / (1 + rate) ** years
    return dict(old_value=old_value, new_price=200, old_initial_repair=10,
                annual_old_cost=30, annual_new_cost=12, old_terminal=30, new_terminal=90,
                years=years, rate=rate, keep_pv=old_pv, replace_pv=new_pv,
                keep_eac=old_pv/af, replace_eac=new_pv/af,
                trade_in_cash_gap=200-old_value)

def channel(opening: float, retail: float, desired_end: float) -> dict:
    shipments = retail + desired_end - opening
    if min(opening, retail, desired_end, shipments) < 0:
        raise ValueError('Impossible illustrative channel state')
    revenue, variable_cost, fixed_cost = shipments * 10, shipments * 7, 700
    return dict(opening=opening, retail=retail, shipments=shipments, ending=desired_end,
                sales=revenue, operating_profit=revenue-variable_cost-fixed_cost)

out = {
    'research_only': True,
    'current_fair_value_or_forecast': False,
    'operation': 'gmi-industrials-sector-research-20260923-sol-001',
    'source_register': 'INDUSTRIALS_WAVE3_EVIDENCE_2026-09-23.md',
    'reported_calculations': {
        'deere_ppa': {'sources':['W3-S01','W3-S02'],
            'sales_2024_2025_2026':[5099,4273,3998], 'profit_2024_2025_2026':[1162,580,527],
            'sales_change_2024_2026_pct':pct(3998,5099), 'profit_change_2024_2026_pct':pct(527,1162),
            'margins_pct':[100*p/s for p,s in zip([1162,580,527],[5099,4273,3998])]},
        'cnh_construction': {'source':'W3-S05','sales':[773,866],'ebit':[35,15],
            'sales_growth_pct':pct(866,773),'ebit_growth_pct':pct(15,35)},
        'agco_scope': {'sources':['W3-S03','W3-S04'],'sales_current':471.5,
            'prior_recast':393.9,'prior_unrecast':420.9,
            'valid_recast_growth_pct':pct(471.5,393.9),
            'invalid_mixed_scope_apparent_growth_pct':pct(471.5,420.9)},
        'uri': {'source':'W3-S11', 'rental_growth_components_pp':[7.1,-1.5,3.4,3.7],
            'bridge_sum_pct':sum([7.1,-1.5,3.4,3.7]),
            'h1_cfo':3305,'cash_rental_purchases':2720,'cash_other_purchases':165,
            'rental_disposals':680,'other_disposals':26,'insurance':23,
            'fcf':3305-2720-165+680+26+23,
            'gross_rental_capex':2931,'capex_minus_cash_payments':2931-2720,
            'h1_2025_cfo':2753,'h1_2025_fcf':1198,
            'cfo_growth_pct':pct(3305,2753),'fcf_growth_pct':pct(1149,1198)},
        'herc': {'source':'W3-S15','ebitda':[410,487], 'adjusted_eps':[1.97,1.43],
            'ebitda_growth_pct':pct(487,410),'adjusted_eps_growth_pct':pct(1.43,1.97)},
        'grainger': {'sources':['W3-S17','W3-S18'],'cfo':[377,444],'capex':[175,111],
            'fcf':[202,333], 'fcf_increase':333-202,'cfo_contribution':444-377,
            'lower_capex_contribution':175-111},
        'wesco': {'source':'W3-S19','quarter_cfo':[107.8,53.7],'half_cfo':[135.8,275.1],
            'quarter_growth_pct':pct(53.7,107.8),'half_growth_pct':pct(275.1,135.8)},
        'chrw': {'source':'W3-S23','operating_income':255.743,'revenue':4934.098,'adjusted_gross_profit':737.966,
            'revenue_margin_pct':100*255.743/4934.098,
            'agp_margin_pct':100*255.743/737.966},
        'odfl_august': {'source':'W3-S21','shipments_change_pct':-2.4,'weight_change_pct':1.7,
            'reported_tons_change_pct':-.9,
            'components_implied_tons_change_pct':100*(.976*1.017-1),
            'reported_minus_components_pp':-.9-100*(.976*1.017-1),
            'residual_explanation':'Not established; do not force equality or ascribe automatically to rounding.'}
    },
    'hypothetical': {
        'units':'arbitrary; no company forecast, taxes or financing are modeled',
        'channel':[channel(900,600,700),channel(700,600,600),channel(600,600,600)],
        'channel_retail_downside':channel(600,480,480),
        'replacement_baseline':replacement_case(80), 'replacement_lower_trade_value':replacement_case(60),
        'rental_base':asset_case(100,20,40),
        'rental_higher_purchase_price':asset_case(110,20,40),
        'rental_lower_residual':asset_case(100,20,25),
        'rental_lower_use':asset_case(100,16,40),
        'fuel_pass_through': {'before_revenue':100,'before_cost':80,'after_revenue':120,'after_cost':100,
            'before_profit':20,'after_profit':20,'before_operating_ratio_pct':80,
            'after_operating_ratio_pct':100*100/120},
        'months_supply':{'initial_units':900,'initial_monthly_sales':100,
            'later_units':810,'later_monthly_sales':80,
            'initial_months':9,'later_months':810/80}
    }
}
(ROOT/'INDUSTRIALS_WAVE3_CALCULATIONS_2026-09-23.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'deere':out['reported_calculations']['deere_ppa'],
                  'channel':out['hypothetical']['channel'],
                  'replacement':[out['hypothetical']['replacement_baseline'],out['hypothetical']['replacement_lower_trade_value']],
                  'rental':[out['hypothetical'][n] for n in ['rental_base','rental_higher_purchase_price','rental_lower_residual','rental_lower_use']],
                  'chrw':out['reported_calculations']['chrw'],
                  'odfl':out['reported_calculations']['odfl_august']},indent=2))
