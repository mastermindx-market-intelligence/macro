"""Offline synthetic checks for GMI C ruling 5810356948. Not product code.

Run: python test_measurement_repair.py --out MEASUREMENT_REPAIR_CHECKS.json
No issuer data, network, authentication, accounting-policy or forecast validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path

OP = 'gmi-theme-research-automation-mobility-deployment-20260924-001'

def measured_revenue(cells: list[tuple[D | None, D | None]]) -> D | None:
    """Matched realized net USD/kWh; no capacity/availability multipliers."""
    if any(e is None or p is None for e, p in cells):
        return None
    return sum((e * p for e, p in cells), D(0))

def prospective_energy(hours: D | None, rate: D | None,
                       basis: str, availability: D | None = None) -> D | None:
    if basis not in ('available_hour', 'scheduled_hour'):
        raise ValueError('unknown rate basis')
    if basis == 'scheduled_hour' and availability is not None:
        raise ValueError('availability already embedded in scheduled-hour rate')
    if hours is None or rate is None:
        return None
    if hours < 0 or rate < 0:
        raise ValueError('negative exposure or intensity')
    if basis == 'scheduled_hour':
        return hours * rate
    if availability is None:
        return None
    if not D(0) <= availability <= D(1):
        raise ValueError('availability outside [0, 1]')
    return hours * availability * rate

def stall_days(cohorts: list[tuple[int, int, int]], period_days: int) -> int:
    """Count, first eligible day, exclusive last eligible day; no overlap per stall."""
    if period_days <= 0:
        raise ValueError('invalid measurement period')
    total = 0
    for count, start, end in cohorts:
        if count < 0 or not 0 <= start <= end <= period_days:
            raise ValueError('invalid commissioning interval')
        total += count * (end - start)
    return total

def accounting_and_cash(revenue: D, accrued_cash_like_cost: D, depreciation: D,
                        cash_tax: D | None, delta_operating_nwc: D | None,
                        cash_capex: D | None) -> dict[str, D | None]:
    """Hypothesis: only D&A is noncash; accrual/cash timing captured in delta NWC.
    No interest, debt principal, tax-payable change or capital offset in this view.
    Actual issuer reconciliations must add other known noncash/timing adjustments.
    """
    op_profit = revenue - accrued_cash_like_cost - depreciation
    if any(x is None for x in (cash_tax, delta_operating_nwc, cash_capex)):
        return {'operating_profit': op_profit, 'cash_direct': None, 'cash_bridge': None}
    cash_direct = revenue - accrued_cash_like_cost - cash_tax - delta_operating_nwc - cash_capex
    cash_bridge = op_profit + depreciation - cash_tax - delta_operating_nwc - cash_capex
    return {'operating_profit': op_profit, 'cash_direct': cash_direct, 'cash_bridge': cash_bridge}

def run() -> dict:
    checks: list[dict] = []
    mutations: list[dict] = []
    def eq(name: str, actual, expected) -> None:
        checks.append({'id': name, 'actual': str(actual), 'expected': str(expected), 'passed': actual == expected})
    def reject(name: str, wrong, correct) -> None:
        mutations.append({'id': name, 'wrong': str(wrong), 'correct': str(correct), 'detected': wrong != correct})
    def raises(name: str, fn) -> None:
        try:
            fn()
        except ValueError:
            eq(name, 'ValueError', 'ValueError')
        else:
            eq(name, 'accepted', 'ValueError')

    # C-R1: all hypothetical USD/kWh values; observed total energy stays fixed.
    cells = [(D(600), D('0.4')), (D(400), D('0.65'))]
    revenue = measured_revenue(cells)
    eq('R1_matched_cells', revenue, D(500))
    for count, avail in [(10, D('0.9')), (100, D('0.4')), (999, D(1))]:
        eq('R1_metadata_invariance_' + str(count), measured_revenue(cells), D(500))
    reject('R1_wrong_measured_energy_times_stalls_availability', revenue * 10 * D('0.9'), revenue)
    eq('R1_prospective_available_rate', prospective_energy(D(1000), D(20), 'available_hour', D('0.8')), D(16000))
    eq('R1_prospective_scheduled_rate', prospective_energy(D(1000), D(16), 'scheduled_hour'), D(16000))
    reject('R1_double_availability_on_scheduled_rate', D(1000) * 16 * D('0.8'), D(16000))
    raises('R1_refuse_duplicate_availability_argument', lambda: prospective_energy(D(1000), D(16), 'scheduled_hour', D('0.8')))
    raises('R1_refuse_invalid_availability', lambda: prospective_energy(D(1000), D(20), 'available_hour', D('1.1')))
    eq('R1_missing_price_is_unknown', measured_revenue([(D(1000), None)]), None)
    eq('R1_missing_availability_is_unknown', prospective_energy(D(1000), D(20), 'available_hour'), None)
    eq('R1_separate_nondelivery_revenue', revenue + D(50) + D(25), D(575))

    # C-R2: one stall eligible for 91 days; another opens on day 45 (46 days).
    exposure = stall_days([(1, 0, 91), (1, 45, 91)], 91)
    eq('R2_integrated_exposure', exposure, 137)
    eq('R2_endpoint_exposure', 2 * 91, 182)
    reject('R2_endpoint_is_not_integrated', 182, exposure)
    eq('R2_integrated_energy_hypothesis', exposure * 276, 37812)
    reject('R2_endpoint_energy_overstates_hypothesis', 182 * 276, 37812)
    eq('R2_constant_count_special_case', stall_days([(2, 0, 91)], 91), 182)
    eq('R2_reviewed_endpoint_arithmetic_only', 3930 * 276 * 91, 98705880)
    raises('R2_refuse_invalid_interval', lambda: stall_days([(1, 45, 92)], 91))

    # C-R3: synthetic operating/cash view; zero omitted items are explicit fixtures.
    x = accounting_and_cash(D(1000), D(600), D(100), D(60), D(40), D(200))
    eq('R3_operating_profit', x['operating_profit'], D(300))
    eq('R3_direct_cash', x['cash_direct'], D(100))
    eq('R3_profit_to_cash_bridge', x['cash_bridge'], x['cash_direct'])
    reject('R3_no_DA_addback_before_capex', x['operating_profit'] - 60 - 40 - 200, x['cash_direct'])
    y = accounting_and_cash(D(1000), D(600), D(150), D(60), D(40), D(200))
    eq('R3_DA_change_affects_profit', y['operating_profit'], D(250))
    eq('R3_DA_change_not_second_cash_cost', y['cash_bridge'], D(100))
    # Interest 20, new debt 50, principal repayment 30; financing shown once.
    eq('R3_separate_financing', x['cash_bridge'] - 20 + 50 - 30, D(100))
    reject('R3_double_interest', x['cash_bridge'] - 20 - 20 + 50 - 30, D(100))
    # Cash offset 75 received, outside revenue/cost/NWC and outside gross capex.
    eq('R3_offset_gross_presentation', x['cash_bridge'] + 75, D(175))
    eq('R3_offset_net_presentation', D(1000) - 600 - 60 - 40 - (200 - 75), D(175))
    reject('R3_double_offset', D(1000) - 600 - 60 - 40 - (200 - 75) + 75, D(175))
    eq('R3_missing_NWC_not_zero', accounting_and_cash(D(1000), D(600), D(100), D(60), None, D(200))['cash_bridge'], None)

    return {'operation': OP, 'ruling_comment': 5810356948,
            'reviewed_head': '28b517561187412b8ea9b32b6001bcdb1a68b1af',
            'scope': 'offline synthetic arithmetic and negative variants; not issuer audit or product tests',
            'checks': checks, 'negative_formula_variants': mutations,
            'summary': {'checks_passed': sum(x['passed'] for x in checks),
                        'checks_failed': sum(not x['passed'] for x in checks),
                        'negative_variants_detected': sum(x['detected'] for x in mutations),
                        'negative_variants_missed': sum(not x['detected'] for x in mutations)}}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('MEASUREMENT_REPAIR_CHECKS.json'))
    args = ap.parse_args()
    result = run()
    b = Path(__file__).read_bytes()
    result['script_sha256'] = hashlib.sha256(b).hexdigest()
    result['script_git_blob'] = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], sort_keys=True))
    return 1 if result['summary']['checks_failed'] or result['summary']['negative_variants_missed'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
