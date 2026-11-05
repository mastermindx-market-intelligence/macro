"""Original research sensitivities, not production decision or valuation-target code."""
from __future__ import annotations
from datetime import date
from math import ceil, isfinite
import json


def finite(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def annuity_pv(cash: float, years: int, rate: float) -> float:
    positive_integer(years, "years")
    cash, rate = finite(cash, "cash"), finite(rate, "rate")
    if rate <= -1:
        raise ValueError("rate must exceed -1")
    return sum(cash / (1 + rate) ** t for t in range(1, years + 1))


def project_npv(initial: float, annual_cash: float, years: int, rate: float) -> float:
    initial = finite(initial, "initial")
    if initial < 0:
        raise ValueError("initial investment must be nonnegative")
    return -initial + annuity_pv(annual_cash, years, rate)


def account_value(contribution: float, retention: float, years: int, rate: float) -> float:
    """First year's contribution certain; survival applies to subsequent renewals."""
    positive_integer(years, "years")
    contribution = finite(contribution, "contribution")
    retention, rate = finite(retention, "retention"), finite(rate, "rate")
    if not 0 <= retention <= 1 or rate <= -1:
        raise ValueError("invalid retention or discount rate")
    return sum(contribution * retention ** (t - 1) / (1 + rate) ** t
               for t in range(1, years + 1))


def route_contribution(stops: int, capacity: int, price: float = 12,
                       variable_cost: float = 6, route_cost: float = 1200) -> dict:
    """Discrete fixed-route illustration, not spatial routing or an optimized network."""
    positive_integer(capacity, "capacity")
    if isinstance(stops, bool) or not isinstance(stops, int) or stops < 0:
        raise ValueError("stops must be a nonnegative integer")
    price, variable_cost, route_cost = [finite(v, "route input")
                                      for v in (price, variable_cost, route_cost)]
    if min(price, variable_cost, route_cost) < 0:
        raise ValueError("negative route price/cost")
    routes = ceil(stops / capacity)
    return {"stops": stops, "routes": routes, "revenue": stops * price,
            "contribution": stops * (price - variable_cost) - routes * route_cost}


def measurement_case(old_energy: float, baseline_adjusted: float, post_energy: float,
                     old_tariff: float, new_tariff: float) -> dict:
    values = [finite(v, "measurement input") for v in
              (old_energy, baseline_adjusted, post_energy, old_tariff, new_tariff)]
    if min(values) < 0:
        raise ValueError("measurement inputs must be nonnegative")
    old_energy, baseline_adjusted, post_energy, old_tariff, new_tariff = values
    return {"raw_energy_difference": old_energy-post_energy,
            "adjusted_energy_saving": baseline_adjusted-post_energy,
            "old_bill": old_energy*old_tariff, "new_bill": post_energy*new_tariff,
            "counterfactual_bill": baseline_adjusted*new_tariff,
            "avoided_current_bill": (baseline_adjusted-post_energy)*new_tariff}


def water_contribution(volume: float, availability_fee: float, unit_price: float) -> float:
    """Volume in million m3; fee/cash in millions; price/cost per m3."""
    volume, availability_fee, unit_price = [finite(v, "water input") for v in
                                         (volume, availability_fee, unit_price)]
    if min(volume, availability_fee, unit_price) < 0:
        raise ValueError("water inputs must be nonnegative")
    return availability_fee + volume * (unit_price - 1.2) - 0.9 - 0.3


GUIDANCE = [
    {"published_at": "2026-04-28", "value": 1.485, "status": "guidance_midpoint", "source": "W6-S15"},
    {"published_at": "2026-07-14", "value": 1.12, "status": "preliminary", "source": "W6-S16"},
    {"published_at": "2026-07-28", "value": 1.14, "status": "final_reported", "source": "W6-S17"},
]


def available_event(as_of: str) -> dict | None:
    """Day-grain research availability, not an intraday release/price alignment."""
    cutoff = date.fromisoformat(as_of)
    eligible = [e for e in GUIDANCE if date.fromisoformat(e["published_at"]) <= cutoff]
    return dict(eligible[-1]) if eligible else None


def calculate() -> dict:
    af8 = annuity_pv(1, 8, .09)
    return {
        "research_only": True,
        "cutoff": "2026-09-23",
        "assumptions": {
            "modular": {"initial_m": 10, "years": 8, "discount_rate": .09,
                        "savings_at_full_utilization_m": 5, "annual_support_m": 2,
                        "terminal_value": 0, "taxes_finance_and_growth_not_modeled": True},
            "retention": {"years": 10, "discount_rate": .09, "first_payment_year": 1,
                          "initial_contribution": 30, "acquisition_cost_excluded": True},
            "retrofit": {"initial_m": 2, "annual_gross_savings_m": .4,
                         "annual_incremental_maintenance_m": .05, "discount_rate": .08},
            "route": {"daily_price_per_stop": 12, "variable_cost_per_stop": 6,
                      "daily_fixed_cost_per_route": 1200, "capacity_per_route": 300},
            "water": {"variable_cost_per_m3": 1.2, "fixed_support_m": .9,
                      "maintenance_m": .3, "initial_growth_capital_not_modeled": True}
        },
        "modular": {
            "npv_full_m": project_npv(10, 3, 8, .09),
            "npv_60pct_m": project_npv(10, 1, 8, .09),
            "break_even_utilization": (10/af8 + 2)/5,
        },
        "retention": {
            "pv_contribution30_retention95": account_value(30, .95, 10, .09),
            "pv_contribution30_retention90": account_value(30, .90, 10, .09),
            "pv_contribution35_retention90": account_value(35, .90, 10, .09),
            "ending_units95": 1000*.95+120,
            "ending_units90": 1000*.90+120,
        },
        "measurement": measurement_case(1200, 1050, 1000, .15, .25),
        "retrofit": {
            "npv_ten_years_m": project_npv(2, .35, 10, .08),
            "npv_five_years_m": project_npv(2, .35, 5, .08),
            "npv_30pct_net_benefit_capture_m": project_npv(2, .35*.3, 10, .08),
            "npv_25pct_capex_overrun_m": project_npv(2.5, .35, 10, .08),
        },
        "routes": [route_contribution(n, 300) for n in (250, 275, 300, 301, 500)],
        "price_churn": route_contribution(225, 300, price=12.6),
        "water": {
            "baseline_volume_only_m": water_contribution(1, 0, 3),
            "lower_volume_only_m": water_contribution(.7, 0, 3),
            "baseline_availability_m": water_contribution(1, 1, 2),
            "lower_volume_availability_m": water_contribution(.7, 1, 2),
        },
        "reported_arithmetic": {
            "sources": ["W6-S01", "W6-S03", "W6-S04", "W6-S05", "W6-S12", "W6-S13",
                        "W6-S15", "W6-S16", "W6-S17", "W6-S18", "W6-S19", "W6-S24"],
            "fix_cfo_increase_m": 1528.254-164.545,
            "fix_billings_cash_contribution_change_m": 1061.506-376.780,
            "emcor_reported_incremental_margin_pct": (547.340-415.212)/(5154.892-4304.400)*100,
            "otis_service_reported_incremental_margin_pct": (599-578)/(2580-2319)*100,
            "kone_reported_profit_change_pct": (322.2/338-1)*100,
            "kone_adjusted_profit_change_pct": (369.9/347.2-1)*100,
            "wm_fcf_current_m": 3227-1144-136+77,
            "wm_fcf_previous_m": 2753-1275-288+103,
            "wm_fcf_change_m": 474+131+152-26,
            "xylem_product_gross_margin_pct": (1953-1093)/1953*100,
            "xylem_service_gross_margin_pct": (383-280)/383*100,
            "limbach_acquisition_share_reported_increase_pct": 30.935/31.216*100,
            "limbach_guidance_previous_margin_midpoint_pct": 92/745*100,
            "limbach_guidance_current_margin_midpoint_pct": 81/775*100,
            "abm_quarter_cfo_growth_pct": (146.8/175-1)*100,
            "abm_nine_month_cfo_growth_pct": (275/101-1)*100,
            "veralto_reported_recurring_share_pct": 1802/2896*100,
            "pentair_final_vs_april_midpoint_pct": (1.14/1.485-1)*100,
            "pentair_final_vs_preliminary_pct": (1.14/1.12-1)*100,
        },
        "guidance_history": GUIDANCE,
        "limitations": [
            "No current fair value, consensus gap or stock-return forecast.",
            "Scenario assumptions are chosen, not estimated from issuer contract cohorts.",
            "No optimized routing, causal savings estimator or production admission service.",
            "Company ratios preserve source scope; growth and annual cash are not always comparable.",
            "Taxes, financing, renewal uncertainty, capex and shared costs vary by model as stated."
        ],
    }


if __name__ == "__main__":
    print(json.dumps(calculate(), indent=2, allow_nan=False))
