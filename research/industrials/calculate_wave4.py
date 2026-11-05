"""Original research sensitivities, not company forecasts or product decision code."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
import json
from typing import Any


def _number(value: float, name: str, *, positive: bool = False) -> float:
    value = float(value)
    if not isfinite(value) or value < 0 or (positive and value <= 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return value


@dataclass(frozen=True)
class Maintenance:
    engines: float = 1000
    annual_hours_per_engine: float = 3000
    hours_between_visits: float = 6000
    cost_per_visit: float = 1_200_000
    fee_per_hour: float = 300
    other_cost_per_hour: float = 40
    third_party_price_per_visit: float = 1_500_000


def maintenance(s: Maintenance) -> dict[str, float]:
    """Long-run renewal-rate proxy; not realized visits, GAAP profit or finite-fleet simulation."""
    for name, value in vars(s).items():
        _number(value, name, positive=name in {'engines', 'hours_between_visits'})
    hours = s.engines * s.annual_hours_per_engine
    visits = hours / s.hours_between_visits
    billings = hours * s.fee_per_hour
    visit_cost = visits * s.cost_per_visit
    other = hours * s.other_cost_per_hour
    event_revenue = visits * s.third_party_price_per_visit
    return {
        'hours': hours, 'renewal_visit_equivalent': visits,
        'hourly_billings': billings, 'renewal_cost': visit_cost,
        'other_cost': other, 'hourly_contract_contribution': billings - visit_cost - other,
        'event_provider_revenue': event_revenue,
        'event_provider_contribution': event_revenue - visit_cost,
        'breakeven_fee_per_hour': s.cost_per_visit / s.hours_between_visits + s.other_cost_per_hour,
    }


def shop_wip(annual_completions: float, turnaround_days: float, days_per_year: float = 365) -> float:
    """Little's-law steady-state proxy; all stocks and flows share one defined shop boundary."""
    _number(annual_completions, 'annual_completions')
    _number(turnaround_days, 'turnaround_days')
    _number(days_per_year, 'days_per_year', positive=True)
    return annual_completions * turnaround_days / days_per_year


def backlog_change(admissions: float, completions: float) -> float:
    return _number(admissions, 'admissions') - _number(completions, 'completions')


def cohort_npv(upfront_net_cost: float, annual_net_service_cash: float,
               first_service_year: int, service_years: int, discount_rate: float) -> float:
    """End-year cash, fixed finite life, no terminal value, no current company calibration."""
    _number(upfront_net_cost, 'upfront_net_cost')
    _number(annual_net_service_cash, 'annual_net_service_cash')
    _number(discount_rate, 'discount_rate')
    if not isinstance(first_service_year, int) or first_service_year < 1:
        raise ValueError('first_service_year must be a positive integer')
    if not isinstance(service_years, int) or service_years < 1:
        raise ValueError('service_years must be a positive integer')
    return -upfront_net_cost + sum(
        annual_net_service_cash / (1 + discount_rate) ** year
        for year in range(first_service_year, first_service_year + service_years)
    )


def cost_to_cost_revenue(contract_price: float, cost_incurred: float, total_expected_cost: float) -> float:
    """Generic illustrative recognition method, not a representation of every issuer's policy."""
    _number(contract_price, 'contract_price', positive=True)
    _number(cost_incurred, 'cost_incurred')
    _number(total_expected_cost, 'total_expected_cost', positive=True)
    if cost_incurred > total_expected_cost:
        raise ValueError('incurred cost exceeds expected total; reconcile estimate first')
    return contract_price * cost_incurred / total_expected_cost


def comparable(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Narrow, intentionally strict research fixture; not a production admission checker."""
    keys = ('business', 'period', 'measure', 'unit', 'currency', 'basis', 'contract', 'vintage')
    return all(a.get(k) is not None and a.get(k) == b.get(k) for k in keys)


def available_as_of(publication: str | None, cutoff: str) -> bool:
    if publication is None:
        return False
    return date.fromisoformat(publication) <= date.fromisoformat(cutoff)


def calculate() -> dict[str, Any]:
    base = maintenance(Maintenance())
    longer = maintenance(Maintenance(hours_between_visits=9000))
    shorter = maintenance(Maintenance(hours_between_visits=4000))
    return {
        'research_only': True,
        'maintenance_hypothetical': {'baseline': base, 'longer_interval': longer, 'shorter_interval': shorter},
        'shop_hypothetical': {
            'wip_90_days': shop_wip(200, 90), 'wip_150_days': shop_wip(200, 150),
            'extra_wip': shop_wip(200, 150) - shop_wip(200, 90),
            'additional_capital_at_2m_per_unit': (shop_wip(200, 150) - shop_wip(200, 90)) * 2_000_000,
            'backlog_growth_if_750_admitted_600_completed': backlog_change(750, 600),
        },
        'cohort_hypothetical': {
            'base_100_cost_25_cash_years_3_to_12': cohort_npv(100, 25, 3, 10, .10),
            'delay_to_years_5_to_14': cohort_npv(100, 25, 5, 10, .10),
            'cash_lower_to_20': cohort_npv(100, 20, 3, 10, .10),
            'higher_upfront_cost_130': cohort_npv(130, 25, 3, 10, .10),
            'license_cost_40_cash_10_years_1_to_5': cohort_npv(40, 10, 1, 5, .09),
        },
        'recognition_hypothetical': {
            'old_revenue': cost_to_cost_revenue(1000, 400, 800),
            'new_revenue_lower_cost': cost_to_cost_revenue(1000, 400, 700),
            'new_revenue_higher_cost': cost_to_cost_revenue(1000, 400, 900),
            'cash_change_assumed': 0,
        },
        'pass_through_hypothetical': {
            'before_revenue': 100, 'before_cost': 80, 'after_revenue': 40, 'after_cost': 20,
            'before_margin': .20, 'after_margin': .50, 'profit_change': 0,
        },
        'source_calculations': {
            'W4-S02': {'net_contract_benefit': 574 - 77, 'component_sum': 372 + 125,
                       'share_of_civil_underlying_profit_pct': 497 / 1567 * 100,
                       'benefit_change': 497 - 288},
            'W4-S05': {'total_rpo': 32085 + 178705, 'service_rpo_share_pct': 178705 / (32085 + 178705) * 100,
                       'other_net_estimate_changes_implied': -42 - 118},
            'W4-S08': {'maintenance_revenue_growth_pct': (3391 / 2799 - 1) * 100,
                       'maintenance_profit_growth_pct': (271 / 241 - 1) * 100,
                       'current_margin_pct': 271 / 3391 * 100, 'prior_margin_pct': 241 / 2799 * 100},
            'W4-S15': {'revenues_after_elimination': 947.803 + 483.487 - 18.240,
                       'profit_after_corporate': 245.299 + 125.565 - 15.667,
                       'parent_net_income': 254.478 - 19.039,
                       'cfo_less_ppe_capex_only': 815.906 - 54.104,
                       'then_less_acquisitions_only': 815.906 - 54.104 - 1018.164},
            'W4-S25': {'group_adjusted_ebitda': 255.411 - 25.534,
                       'q1_cfo_derived': -47.227 - 72.328,
                       'unpaid_intangible_liability': 180.777},
        },
    }


if __name__ == '__main__':
    print(json.dumps(calculate(), indent=2, allow_nan=False))
