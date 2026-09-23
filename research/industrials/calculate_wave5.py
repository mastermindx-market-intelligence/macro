"""Original research sensitivities only; not contract adjudication or trade code."""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from datetime import date
from math import isfinite
from typing import Iterable
import json


def finite(value: float, name: str, *, nonnegative: bool = False) -> float:
    value = float(value)
    if not isfinite(value) or (nonnegative and value < 0):
        raise ValueError(f'{name} must be finite' + (' and nonnegative' if nonnegative else ''))
    return value


def growth(current: float, prior: float) -> float:
    current, prior = finite(current, 'current'), finite(prior, 'prior')
    if prior <= 0:
        raise ValueError('Percentage-growth denominator must be positive; use absolute change otherwise')
    return 100 * (current / prior - 1)


def midpoint(bounds: tuple[float, float]) -> float:
    low, high = (finite(x, 'range endpoint') for x in bounds)
    if low > high:
        raise ValueError('Reversed interval')
    return (low + high) / 2


def ffp(price: float, actual_cost: float) -> dict[str, float]:
    price, cost = finite(price, 'price', nonnegative=True), finite(actual_cost, 'cost', nonnegative=True)
    return {'price': price, 'cost': cost, 'profit': price - cost}


def cpff(actual_cost: float, fixed_fee: float, cost_limit: float,
         *, allowable_and_authorized: bool = True) -> dict[str, float]:
    cost, fee, limit = [finite(x, n, nonnegative=True) for x, n in
                        [(actual_cost, 'cost'), (fixed_fee, 'fee'), (cost_limit, 'cost limit')]]
    if not allowable_and_authorized or cost > limit:
        raise ValueError('No unconditional cost recovery assumed outside authorization/allowability/limit')
    return {'price': cost + fee, 'cost': cost, 'profit': fee,
            'margin': fee / (cost + fee) if cost + fee else 0.0}


def fpi(actual_cost: float, target_cost: float = 100, target_profit: float = 20,
        contractor_share: float = .2, price_ceiling: float = 132) -> dict[str, float]:
    cost, target, profit, ceiling = [finite(x, n, nonnegative=True) for x, n in
        [(actual_cost, 'cost'), (target_cost, 'target'), (target_profit, 'profit'), (price_ceiling, 'ceiling')]]
    share = finite(contractor_share, 'share')
    if not 0 <= share < 1 or ceiling < target + profit:
        raise ValueError('This illustration requires 0 <= contractor share < 1 and ceiling >= target price')
    uncapped_price = cost + profit + share * (target - cost)
    price = min(ceiling, uncapped_price)
    return {'price': price, 'cost': cost, 'profit': price - cost,
            'ceiling_cost_threshold': target + (ceiling - target - profit) / (1 - share)}


def cash_schedule(receipts: Iterable[float], costs: Iterable[float], rate: float = .1) -> dict:
    receipts, costs = tuple(receipts), tuple(costs)
    rate = finite(rate, 'rate', nonnegative=True)
    if not receipts or len(receipts) != len(costs):
        raise ValueError('Matching nonempty period arrays required, starting at t=0')
    receipts = [finite(x, 'receipt', nonnegative=True) for x in receipts]
    costs = [finite(x, 'cost', nonnegative=True) for x in costs]
    net = [r-c for r, c in zip(receipts, costs)]
    accumulated, balances = 0.0, []
    for x in net:
        accumulated += x
        balances.append(accumulated)
    return {'receipts': receipts, 'costs': costs, 'net': net,
            'lifetime_net_cash': sum(net),
            'npv': sum(x / (1 + rate)**t for t, x in enumerate(net)),
            'peak_net_funding': max(0, -min(balances)),
            'limitation': 'Period-end net funding; intra-period cash peaks, tax and financing omitted.'}


def cumulative_buckets(cumulative_12: float, cumulative_24: float) -> list[float]:
    x, y = finite(cumulative_12, 'share'), finite(cumulative_24, 'share')
    if not 0 <= x <= y <= 1:
        raise ValueError('Cumulative shares must be ordered in [0,1]')
    return [x, y-x, 1-y]


@dataclass(frozen=True)
class Observation:
    """A deliberately narrow comparison fixture, not a production schema."""
    subject: str = 'example_business'
    metric: str = 'backlog'
    definition: str = 'firm_excludes_options'
    unit: str = 'USD_million'
    period_kind: str = 'quarter_end_stock'
    duration_months: int = 0
    consolidation: str = 'consolidated'
    perimeter: str = 'same_scope'
    adjustment: str = 'reported'
    clock_family: str = 'source_publication'
    statement: str = 'reported'
    method_revision: str = 'comparison_basis_1'
    published: str | None = '2026-07-01'


def comparable(a: Observation, b: Observation) -> bool:
    keys = ('subject', 'metric', 'definition', 'unit', 'period_kind', 'duration_months',
            'consolidation', 'perimeter', 'adjustment', 'clock_family', 'statement', 'method_revision')
    return all(getattr(a, k) == getattr(b, k) for k in keys)


def available(o: Observation, cutoff: str) -> bool:
    if o.published is None or o.clock_family != 'source_publication':
        return False
    return date.fromisoformat(o.published) <= date.fromisoformat(cutoff)


def results() -> dict:
    costs = [90, 100, 115, 120, 145]
    commercial = {'firm_fixed_price': [ffp(120, c) for c in costs],
                  'fixed_price_incentive': [fpi(c) for c in costs],
                  'cost_plus_fixed_fee': [cpff(c, 10, 150) for c in costs]}
    gd = {'firm_now': 104111 + 32387, 'firm_prior': 130840,
          'potential_now': 50404, 'potential_prior': 57601}
    gd.update(firm_change=gd['firm_now']-gd['firm_prior'],
              potential_change=gd['potential_now']-gd['potential_prior'],
              total_now=gd['firm_now']+gd['potential_now'],
              total_prior=gd['firm_prior']+gd['potential_prior'])
    gd['total_change'] = gd['total_now'] - gd['total_prior']
    lmt = {'operating_cash_prior': midpoint((9150, 9450)), 'operating_cash_now': midpoint((9200, 9400)),
           'capex_prior': midpoint((2500, 2800)), 'capex_now': midpoint((2000, 2400)),
           'fcf_prior': midpoint((6500, 6800)), 'fcf_now': midpoint((7000, 7200)),
           'sales_delta': midpoint((79750, 81750))-midpoint((77500, 80000)),
           'segment_profit_delta': midpoint((8500, 8700))-midpoint((8425, 8675))}
    caci = {'cfo_now': 378266, 'cfo_prior': 155982,
            'adjusted_now': 378266-98606, 'adjusted_prior': 155982+11091}
    caci.update(fcf_now=caci['adjusted_now']-46777, fcf_prior=caci['adjusted_prior']-27963,
                cfo_growth_pct=growth(caci['cfo_now'], caci['cfo_prior']),
                adjusted_cfo_growth_pct=growth(caci['adjusted_now'], caci['adjusted_prior']))
    return {'research_only': True, 'not_a_forecast': True, 'as_of': '2026-09-23',
      'contract_models': commercial,
      'cash_timing': {
         'early': cash_schedule([30,30,30,30], [20,30,30,20]),
         'late': cash_schedule([0,10,30,80], [20,30,30,20]),
         'later': cash_schedule([0,10,30,0,80], [20,30,30,20,0])},
      'service_productivity': {'baseline_revenue': 15, 'baseline_cost': 10, 'baseline_profit': 5,
         'improved_cost_with_tool': 9, 'fixed_price_profit': 15-9, 'time_materials_profit': 12-9,
         'assumptions': 'Same accepted outcome, 20% fewer actual hours, tool cost 1; no redeployment or rebid.'},
      'remaining_loss_cash': {'total_price':120, 'new_lifetime_cost':135, 'cost_spent':40,
         'cash_collected':50, 'remaining_cost':95, 'remaining_receipts':70,
         'cash_to_date':10, 'future_net_cash':-25, 'lifetime_net_cash':-15,
         'double_counted_future_cash_wrong':-40},
      'gd':gd, 'northrop': {'recognition_buckets':cumulative_buckets(.35,.55),
         'segment_guidance_change': midpoint((4850,5000))-midpoint((4850,5000)),
         'eps_guidance_change':midpoint((28.60,29.10))-midpoint((27.40,27.90))},
      'lmt':lmt, 'caci':caci,
      'hii': {'net_contract_assets_prior':1758-1220, 'net_contract_assets_now':2154-690,
         'net_contract_asset_change':(2154-690)-(1758-1220), 'h1_fcf':-421-193+3},
      'saab': {'named_award_share_pct':47000/68393*100, 'remaining_orders':68393-47000},
      'fincantieri': {'firm_backlog':43016, 'soft_backlog':30900, 'total_backlog':43016+30900,
         'reported_adjusted_debt_reduction':1311-756, 'equity_effect':1234-756,
         'reduction_ex_equity':1311-1234, 'equity_effect_share_pct':(1234-756)/(1311-756)*100,
         'liquidity_sensitivity_debt_plus_supplier_finance':756+891},
      'rheinmetall': {'computed_growth_pct':growth(20646,14829), 'source_claim_pct':80,
         'unresolved_conflict':True, 'q1_issuer_attributed_expectation_gap':1938-2300,
         'q1_issuer_attributed_expectation_gap_pct':growth(1938,2300)}}

if __name__ == '__main__':
    print(json.dumps(results(), indent=2, allow_nan=False))
