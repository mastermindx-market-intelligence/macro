"""Eighteen fixed, entirely synthetic research experiments.

Not a Mastermind engine, valuation service, source parser or investment model.
No network, model, native-owner, identity, market-price or private-data imports.
All amounts, rates, joint states and costs are assumptions invented to test the
reasoning in COMMUNICATIONS_EARNINGS_SENSITIVITY_AND_VALUATION_2026-09-24.md.
Private helpers perform algebra only for this fixed experiment set. There is no
input dataset or CLI scenario parameter. Only explicit --output writes a file.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as F
import json
from pathlib import Path


def _stable_value(next_nopat: F, growth: F, discount: F, incremental_return: F) -> F:
    """Restricted stable-state illustration; NOT a whole-company valuation."""
    if next_nopat <= 0 or not (0 <= growth < discount) or incremental_return <= growth:
        raise ValueError('outside_fixed_stable_state_domain')
    return next_nopat * (1 - growth / incremental_return) / (discount - growth)


def _required_return(multiple: F, growth: F, discount: F) -> F | None:
    if multiple <= 0 or not (0 < growth < discount):
        raise ValueError('outside_fixed_inverse_domain')
    denominator = 1 - multiple * (discount - growth)
    return None if denominator <= 0 else growth / denominator


def build_examples() -> dict:
    """Return fixed assumptions and exact rational results; no issuer estimates."""
    cases: dict = {}

    def add(n: int, title: str, assumptions: str, **values) -> None:
        cases[f'SX{n:02d}'] = {
            'kind': 'synthetic_reference_only', 'title': title,
            'assumptions': assumptions, 'values': values,
        }

    add(1, 'Observed slope does not identify the marginal effect',
        'Two models fit R=100,110 and EBIT=30,32. A uses EBIT=.2R+10. '
        'B uses EBIT=.5R-F with F=20,23, then holds F=23 at R=120.',
        observed_a=[F('.2') * r + 10 for r in (100, 110)],
        observed_b=[F('.5') * r - f for r, f in ((100, 20), (110, 23))],
        forecast_a=F('.2') * 120 + 10, forecast_b=F('.5') * 120 - 23)

    v0, v1, y0, y1, c0, c1 = map(F, ('100', '110', '1', '1.02', '.30', '.32'))
    add(2, 'Revenue growth can coexist with lower contribution after investment costs',
        'Volume 100->110, yield 1->1.02, service cost/unit .30->.32, '
        'fixed operating cost 20->23, depreciation 10->15; one identical population.',
        revenue_before=v0*y0, revenue_after=v1*y1,
        profit_before=v0*(y0-c0)-20-10, profit_after=v1*(y1-c1)-23-15,
        volume_yield_interaction=(v1-v0)*(y1-y0))

    legacy_margin, ai_margin = F('.8'), F('.6')
    lost = 30 * (legacy_margin-ai_margin)
    hurdle = lost / ai_margin
    add(3, 'Migration versus genuinely additional demand',
        '100 legacy units yield 1 with cost .2. Thirty migrate to a format '
        'yielding 1.1 with cost .5. Incremental units have that same .6 margin. '
        'No extra fixed cost, capex or tax included.',
        before_contribution=100*legacy_margin,
        after_migration_only=70*legacy_margin+30*ai_margin,
        incremental_units_needed=hurdle,
        after_hurdle=70*legacy_margin+(30+hurdle)*ai_margin)

    add(4, 'Aggregate cost-rate reduction from mix alone',
        'Two categories retain unchanged cost rates 10% and 50%; '
        'revenue weights move from 80/20 to 90/10.',
        aggregate_rate_before=F('.8')*F('.1')+F('.2')*F('.5'),
        aggregate_rate_after=F('.9')*F('.1')+F('.1')*F('.5'),
        component_rate_changes=[0, 0])

    add(5, 'Presentation change without new profit',
        'The same supplier cost of 15 moves from a revenue deduction to expense. '
        'Reported revenue 100->115; costs 40->55; activity unchanged.',
        revenue_delta=15, cost_delta=15, profit_delta=(115-55)-(100-40))

    add(6, 'Query workload versus retained fees',
        'Gross spend 1000->1100; retained fee 20%. Requests 10000->15000; '
        'cost/request .005; other costs 100 in both states.',
        retained_fees_before=1000*F('.2'), retained_fees_after=1100*F('.2'),
        profit_before=1000*F('.2')-10000*F('.005')-100,
        profit_after=1100*F('.2')-15000*F('.005')-100)

    add(7, 'Channel mix with unchanged channel economics',
        'Retained receipts remain 100. Channel mix 40/60->50/50; '
        'contribution rates are assumed .6 and .3, not observed company margins.',
        contribution_before=40*F('.6')+60*F('.3'),
        contribution_after=50*F('.6')+50*F('.3'), total_receipts_delta=0)

    gross_per_year, fee_rate, extra_days = F(3650), F('.10'), F(10)
    add(8, 'Working-capital denominator and credit sensitivity',
        'Uniform annual gross billings 3650, 365 days, 10% retained fee. '
        'Collection takes 10 extra days; settlement timing unchanged. '
        'A separate credit-loss illustration loses 1% of gross without recovery.',
        funding_requirement=gross_per_year/F(365)*extra_days,
        wrong_net_fee_estimate=gross_per_year*fee_rate/F(365)*extra_days,
        loss_as_fraction_of_fee=(gross_per_year*F('.01'))/(gross_per_year*fee_rate))

    def step_profit(volume):
        return F('.5')*volume-(8 if volume > 105 else 0)
    add(9, 'Capacity steps make local slopes change',
        'Contribution/unit .5; a capacity block costs 8 above 105 units.',
        first_increment=step_profit(110)-step_profit(100),
        next_increment=step_profit(120)-step_profit(110))

    add(10, 'Book depreciation and cash taxes must not be conflated',
        'EBITDA 200, book depreciation 100->75; cash tax remains 20, '
        'capex 120 and additional working capital 10. No tax deduction change.',
        ebit_before=200-100, ebit_after=200-75,
        cash_before=200-20-120-10, cash_after=200-20-120-10)

    add(11, 'Net-income growth can coexist with EPS decline',
        'Net income 100->108 and like-for-like shares 100->110; no other claims.',
        earnings_growth=F(108,100)-1, share_growth=F(110,100)-1,
        eps_growth=(F(108,110)/F(100,100))-1)

    def repurchase_value(price):
        return F(900)/(F(100)-F(100)/price)
    add(12, 'Mechanical EPS accretion is not value creation',
        'Equity value including excess cash 1000, shares 100, cash buyback 100. '
        'No fees/tax/foregone cash earnings, unchanged operating income 100. '
        'Value hypothesis held fixed; compare buyback prices 8,10,12.',
        fair_price_value=repurchase_value(F(10)),
        under_value_price=repurchase_value(F(8)),
        over_value_price=repurchase_value(F(12)), mechanical_eps_after=F(100,90))

    add(13, 'One future compensation claim counted once',
        'Perpetual cash before a recurring assumed compensation claim 100, '
        'claim 20/year, discount .10. Optional distinct existing claim PV50. '
        'This is not an option-pricing or GAAP-SBC conversion model.',
        cash_cost_representation=F(100-20)/F('.1'),
        separate_claim_representation=F(100)/F('.1')-F(20)/F('.1'),
        double_charge_error=F(100-20)/F('.1')-F(20)/F('.1'),
        after_distinct_existing_claim=F(100-20)/F('.1')-50)

    add(14, 'Stable growth requires reinvestment',
        'First stable-year after-tax operating profit held at 100; '
        'discount .10, growth .02 versus .04. Incremental return .20,.10,.06. '
        'No finite high-growth phase or additional liabilities.',
        high_return_g2=_stable_value(F(100),F('.02'),F('.1'),F('.20')),
        high_return_g4=_stable_value(F(100),F('.04'),F('.1'),F('.20')),
        equal_return_g2=_stable_value(F(100),F('.02'),F('.1'),F('.10')),
        equal_return_g4=_stable_value(F(100),F('.04'),F('.1'),F('.10')),
        low_return_g2=_stable_value(F(100),F('.02'),F('.1'),F('.06')),
        low_return_g4=_stable_value(F(100),F('.04'),F('.1'),F('.06')))

    add(15, 'Reverse valuation is conditional and can be infeasible',
        'Multiple is value divided by NEXT stable-year NOPAT, not current '
        'EBITDA/P-E. Fix growth .03; compare discount .10 and .09 at M12. '
        'M15, discount .10 and growth .03 has no finite positive return solution.',
        required_return_k10=_required_return(F(12),F('.03'),F('.10')),
        required_return_k9=_required_return(F(12),F('.03'),F('.09')),
        multiple_ceiling=1/(F('.10')-F('.03')),
        fifteen_times_solution=_required_return(F(15),F('.03'),F('.10')))

    add(16, 'Earnings and multiple changes multiply',
        'Matched forward EPS 1->1.2; P/E 20->16. No dividend, split or horizon roll.',
        price_return=(F('1.2')*16)/(F(1)*20)-1,
        wrong_additive_return=F('.2')+F('-.2'))

    add(17, 'Preserve dependence in joint scenarios',
        'Invented two-state illustration, equal weights: (volume80,yield1.2) '
        'or (volume120,yield.8). These are not estimated probabilities.',
        mean_joint_revenue=(80*F('1.2')+120*F('.8'))/2,
        product_of_means=F(80+120,2)*((F('1.2')+F('.8'))/2))

    annuity_factor = sum((1/F('1.1')**t for t in range(1,6)), F(0))
    annual = F(1000)/annuity_factor
    add(18, 'Investment-to-cash hurdle, not an issuer target',
        'Investment 1000 now; five equal year-end NET incremental cash payments; '
        'discount .10; no residual value. Delay shifts all five payments one '
        'year without moving initial investment. Revenue conversion .4 is '
        'invented and includes all required recurring cash uses for this case.',
        annual_cash_hurdle=annual, delayed_hurdle=annual*F('1.1'),
        revenue_hurdle=annual/F('.4'), npv_at_hurdle=-1000+annual*annuity_factor)
    return cases


def _json_safe(value):
    if isinstance(value, F):
        with localcontext() as ctx:
            ctx.prec = 40
            display = format(Decimal(value.numerator)/Decimal(value.denominator), '.6f')
        return {'rational': str(value), 'display_only': display}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Explicit local JSON destination')
    args = parser.parse_args()
    payload = {'purpose': 'fixed_synthetic_research_only', 'product_tests_run': 0,
               'issuer_forecasts_or_targets': 0, 'examples': _json_safe(build_examples())}
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        except OSError as exc:
            parser.exit(2, f'Cannot write explicit research output: {exc}\n')
    print(f"Computed {len(payload['examples'])} fixed synthetic examples; no issuer target or product call.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
