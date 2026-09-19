"""Pure conditional financial arithmetic; never a fact, forecast or trade owner.

Two explicitly comparable periods, a closed field vocabulary, no IO/eval/model.
Inputs are caller-supplied and unverified. Decimal strings preserve visible math.
"""
from __future__ import annotations

from decimal import (Context, Decimal, DivisionByZero, InvalidOperation,
                     Overflow, ROUND_HALF_EVEN, localcontext)
import re
from typing import Any, Callable

SCHEMA = 'brain.financial_bridge.v1'
_FIELDS = (
    'revenue', 'gross_margin_pct', 'operating_expenses',
    'depreciation_amortization', 'cash_interest', 'cash_taxes',
    'working_capital_increase', 'capital_expenditures',
    'other_operating_cash_adjustments', 'eps', 'earnings_multiple',
)
_TOP_KEYS = {'basis', 'currency', 'amount_scale', 'prior', 'current'}
_SCALES = {'units', 'thousands', 'millions', 'billions'}
_DECIMAL_PATTERN = r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,3})?'
_DECIMAL = re.compile(_DECIMAL_PATTERN + r'\Z')
_NONNEGATIVE = {'revenue', 'operating_expenses', 'depreciation_amortization',
                'capital_expenditures', 'earnings_multiple'}
_LIMITATIONS = [
    'All inputs are caller-supplied unverified assumptions, not current or reported issuer facts.',
    'One common currency/scale and comparable periods are assumptions; no FX, split or period reconciliation is performed.',
    'Simplified operating cash is a conditional bridge, not a reconstructed GAAP/IFRS cash-flow statement; cash after capex is not a standardised free-cash-flow claim.',
    'EPS is currency per share, unscaled; the P/E product requires positive annual EPS and a positive multiple. No quarterly annualisation.',
    'Decomposition order is arithmetic, not causal evidence. No probability, target price, ranking, signal or permission to trade is produced.',
]


def invalid_result(errors: list[str]) -> dict[str, Any]:
    """Fixed bounded errors: no rejected text, private fields or exception echo."""
    return {'schema': SCHEMA, 'status': 'invalid_request', 'authority': 'analysis_only',
            'input_provenance': 'caller_supplied_unverified', 'calculations': {},
            'arithmetic_observations': [], 'errors': errors[:32]}


def _number(value: object) -> Decimal | None:
    if value is None:
        return None
    if type(value) not in (int, float, str):
        raise ValueError('invalid_number')
    if type(value) is str and (len(value) > 48 or not _DECIMAL.fullmatch(value)):
        raise ValueError('invalid_number')
    if type(value) is int and value.bit_length() > 64:
        raise ValueError('invalid_number')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('invalid_number') from None
    if not number.is_finite() or abs(number) > Decimal('1e18'):
        raise ValueError('invalid_number')
    if number and abs(number) < Decimal('1e-12'):
        raise ValueError('invalid_number')
    if number.normalize().as_tuple().exponent < -12:
        raise ValueError('invalid_number')
    return number


def _plain(value: Decimal) -> str:
    if not value:
        return '0'
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _text(value: Decimal) -> str:
    # Significant-digit rounding never turns a small nonzero loss into zero.
    if not value:
        return '0'
    quantum = Decimal(1).scaleb(value.adjusted() - 11)
    return _plain(value.quantize(quantum, rounding=ROUND_HALF_EVEN))


def _validate(payload: object) -> tuple[dict[str, Any] | None, list[str]]:
    if type(payload) is not dict or set(payload) != _TOP_KEYS:
        return None, ['request:invalid_fields']
    if payload['basis'] != 'supplied_scenario':
        return None, ['basis:unsupported']
    if type(payload['currency']) is not str or not re.fullmatch(r'[A-Z]{3}', payload['currency']):
        return None, ['currency:invalid']
    if type(payload['amount_scale']) is not str or payload['amount_scale'] not in _SCALES:
        return None, ['amount_scale:invalid']
    result = {k: payload[k] for k in ('basis', 'currency', 'amount_scale')}
    errors = []
    for period in ('prior', 'current'):
        raw = payload[period]
        if type(raw) is not dict or set(raw) - set(_FIELDS) - {'period_months'}:
            errors.append(f'{period}:invalid_fields')
            continue
        months = raw.get('period_months')
        if type(months) is not int or not 1 <= months <= 24:
            errors.append(f'{period}.period_months:invalid')
        row: dict[str, Any] = {'period_months': months}
        for field in _FIELDS:
            try:
                value = _number(raw.get(field))
                if value is not None and (
                    (field in _NONNEGATIVE and value < 0)
                    or (field == 'gross_margin_pct' and not -1000 <= value <= 100)
                ):
                    raise ValueError('invalid_number')
                row[field] = value
            except ValueError:
                errors.append(f'{period}.{field}:invalid_number')
        result[period] = row
    if not errors and result['prior']['period_months'] != result['current']['period_months']:
        errors.append('periods:not_comparable')
    return (None if errors else result), errors


class _Calculator:
    """Request-local expression graph over a finite hard-coded vocabulary."""
    def __init__(self, inputs: dict[str, Any]):
        self.values = {f'{p}.{f}': inputs[p][f] for p in ('prior', 'current') for f in _FIELDS}
        self.cells: dict[str, dict[str, Any]] = {}

    def add(self, name: str, unit: str, formula: str, inputs: tuple[str, ...],
            calculate: Callable[..., Decimal], domain: str | None = None,
            requires: tuple[str, ...] = ()) -> None:
        unavailable = [key for key in (*inputs, *requires) if self.values[key] is None]
        missing: set[str] = set()
        for key in unavailable:
            if key in self.cells:
                missing.update(self.cells[key]['missing_inputs'])
            else:
                missing.add(key)
        reason = ('missing_inputs' if missing else domain or 'dependency_unavailable') if unavailable else domain
        value = None if reason else calculate(*(self.values[key] for key in inputs))
        self.values[name] = value
        self.cells[name] = {
            'value': _text(value) if value is not None else None, 'unit': unit,
            'rounded': (Decimal(_text(value)) != value) if value is not None else False,
            'formula': formula, 'inputs': list(inputs), 'missing_inputs': sorted(missing),
            'reason': reason, 'state': 'calculated' if value is not None else 'unavailable',
        }
        if requires:
            self.cells[name]['requires'] = list(requires)


def analyze_financial_bridge(payload: object) -> dict[str, Any]:
    """Return inspectable conditional arithmetic or a bounded invalid envelope."""
    # Decimal policy is local to this request; never mutate a server-global context.
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-999999,
                              Emax=999999, capitals=1, clamp=0, flags=[],
                              traps=[InvalidOperation, DivisionByZero, Overflow])):
        data, errors = _validate(payload)
        if errors:
            return invalid_result(errors)
        assert data is not None
        calc = _Calculator(data)
        money = f'{data["currency"]}_{data["amount_scale"]}'
        per_share = f'{data["currency"]}/share'
        for p in ('prior', 'current'):
            calc.add(f'{p}.gross_profit', money, 'revenue * gross_margin_pct / 100',
                     (f'{p}.revenue', f'{p}.gross_margin_pct'), lambda r, m: r*m/100)
            calc.add(f'{p}.operating_profit', money, 'gross_profit - operating_expenses',
                     (f'{p}.gross_profit', f'{p}.operating_expenses'), lambda g, o: g-o)
            cash = ('operating_profit', 'depreciation_amortization', 'cash_interest',
                    'cash_taxes', 'working_capital_increase', 'other_operating_cash_adjustments')
            calc.add(f'{p}.simplified_operating_cash', money,
                     'operating_profit + depreciation_amortization - cash_interest - cash_taxes - working_capital_increase + other_operating_cash_adjustments',
                     tuple(f'{p}.{f}' for f in cash), lambda o, d, i, t, w, a: o+d-i-t-w+a)
            calc.add(f'{p}.cash_after_capex', money, 'simplified_operating_cash - capital_expenditures',
                     (f'{p}.simplified_operating_cash', f'{p}.capital_expenditures'), lambda c, x: c-x)
            eps, multiple = data[p]['eps'], data[p]['earnings_multiple']
            domain = ('annual_eps_required' if data[p]['period_months'] != 12 else
                      'positive_eps_and_multiple_required' if
                      ((eps is not None and eps <= 0) or (multiple is not None and multiple <= 0)) else None)
            calc.add(f'{p}.implied_price', per_share, 'annual_eps * earnings_multiple',
                     (f'{p}.eps', f'{p}.earnings_multiple'), lambda e, m: e*m, domain)
        compared = ('revenue', 'gross_profit', 'operating_profit', 'simplified_operating_cash',
                    'cash_after_capex', 'eps', 'implied_price')
        for field in compared:
            prior, current = f'prior.{field}', f'current.{field}'
            unit = per_share if field in ('eps', 'implied_price') else money
            calc.add(f'change.{field}', unit, 'current - prior', (prior, current), lambda p, c: c-p)
            base = calc.values[prior]
            calc.add(f'change.{field}_pct', 'percent', '(current - prior) / prior * 100',
                     (prior, current), lambda p, c: (c-p)/p*100,
                     'nonpositive_base' if base is not None and base <= 0 else None)
        calc.add('change.gross_margin_pp', 'percentage_points', 'current_margin_pct - prior_margin_pct',
                 ('prior.gross_margin_pct', 'current.gross_margin_pct'), lambda p, c: c-p)
        calc.add('bridge.gross_profit_sales_effect', money, '(current_revenue - prior_revenue) * prior_margin_pct / 100',
                 ('prior.revenue', 'current.revenue', 'prior.gross_margin_pct'), lambda p, c, m: (c-p)*m/100)
        calc.add('bridge.gross_profit_margin_effect', money, 'current_revenue * (current_margin_pct - prior_margin_pct) / 100',
                 ('current.revenue', 'prior.gross_margin_pct', 'current.gross_margin_pct'), lambda r, p, c: r*(c-p)/100)
        calc.add('bridge.operating_expense_effect', money, 'prior_operating_expenses - current_operating_expenses',
                 ('prior.operating_expenses', 'current.operating_expenses'), lambda p, c: p-c)
        price_domain = None if all(calc.values[f'{p}.implied_price'] is not None for p in ('prior','current')) else 'valid_annual_price_bases_required'
        calc.add('bridge.price_earnings_effect', per_share, '(current_eps - prior_eps) * prior_multiple',
                 ('prior.eps','current.eps','prior.earnings_multiple'), lambda p,c,m: (c-p)*m, price_domain,
                 requires=('prior.implied_price', 'current.implied_price'))
        calc.add('bridge.price_multiple_effect', per_share, 'current_eps * (current_multiple - prior_multiple)',
                 ('current.eps','prior.earnings_multiple','current.earnings_multiple'), lambda e,p,c: e*(c-p), price_domain,
                 requires=('prior.implied_price', 'current.implied_price'))
        observations = []
        v = calc.values
        def opposite(a: str, b: str) -> bool:
            return v[a] is not None and v[b] is not None and v[a] > 0 and v[b] < 0
        if opposite('change.revenue', 'change.gross_profit'):
            observations.append('revenue_up_gross_profit_down')
        if opposite('change.eps', 'change.implied_price'):
            observations.append('eps_up_implied_price_down')
        if opposite('current.operating_profit', 'current.simplified_operating_cash'):
            observations.append('current_profit_positive_operating_cash_negative')
        primary_cells = dict(calc.cells)
        count = sum(c['value'] is not None for c in primary_cells.values())
        scenario_tests = _scenario_tests(calc, data)
        return {
            'schema': SCHEMA, 'status': 'complete' if count == len(primary_cells) else 'partial' if count else 'unavailable',
            'authority': 'analysis_only', 'input_provenance': 'caller_supplied_unverified',
            'currency': data['currency'], 'amount_scale': data['amount_scale'],
            'period_months': data['prior']['period_months'],
            'rounding': 'up_to_12_significant_decimal_digits_half_even',
            'inputs': {f'{p}.{f}': _plain(data[p][f]) if data[p][f] is not None else None
                       for p in ('prior','current') for f in _FIELDS},
            'calculations': primary_cells, 'arithmetic_observations': observations,
            'scenario_tests': scenario_tests, 'reasoning': _conditional_reasoning(observations),
            'limitations': list(_LIMITATIONS), 'errors': [],
        }


def financial_bridge_tool_schema() -> dict[str, Any]:
    """Fresh native Brain metadata; defining a schema does not register a tool.

    Runtime validation remains authoritative for finite values, precision and
    comparable periods. No account, provider, origin or source-rights knobs.
    """
    def period_schema() -> dict[str, Any]:
        properties: dict[str, Any] = {
            'period_months': {'type': 'integer', 'minimum': 1, 'maximum': 24},
        }
        for field in _FIELDS:
            properties[field] = {
                'anyOf': [
                    {'type': 'number', 'minimum': -10**18, 'maximum': 10**18},
                    {'type': 'string', 'maxLength': 48,
                     'pattern': '^' + _DECIMAL_PATTERN + '$'},
                    {'type': 'null'},
                ],
                'description': (
                    'Explicit scenario input; omit or use null when unknown. '
                    'Finite decimal: magnitude <=1e18, at most 12 fractional places. '
                    'EPS is currency/share; gross_margin_pct is percent; '
                    'earnings_multiple is unitless; other amounts use the common scale.'
                ),
            }
            if field == 'operating_expenses':
                properties[field]['description'] += ' Expenses after gross profit, excluding cost of sales; include noncash charges.'
            elif field == 'depreciation_amortization':
                properties[field]['description'] += ' Noncash charges already deducted in operating profit, not capex.'
            elif field == 'working_capital_increase':
                properties[field]['description'] += ' Period cash flow: positive use, negative release; not the working-capital balance.'
        return {'type': 'object', 'properties': properties,
                'required': ['period_months'], 'additionalProperties': False}
    return {
        'name': 'calculate_financial_bridge',
        'description': (
            'Calculate a conditional revenue-to-profit-to-cash bridge and an annual '
            'EPS-times-multiple comparison from explicit assumptions, not verified facts. '
            'Returns equality boundaries, local sensitivities and untested rivals with evidence questions. '
            'Do not invent missing values or replace unknown cash adjustments with zero. '
            'Label all arguments unverified; same currency, scale and period length required. '
            'This pure arithmetic tool does not fetch data, verify sources, forecast prices '
            'or grant signal/trade authority. A computed P/E product is not a price target.'
        ),
        'input_schema': {
            'type': 'object', 'additionalProperties': False,
            'required': ['basis', 'currency', 'amount_scale', 'prior', 'current'],
            'properties': {
                'basis': {'type': 'string', 'enum': ['supplied_scenario']},
                'currency': {'type': 'string', 'pattern': '^[A-Z]{3}$'},
                'amount_scale': {'type': 'string', 'enum': sorted(_SCALES)},
                'prior': period_schema(), 'current': period_schema(),
            },
        },
    }


def _scenario_tests(calc: _Calculator, data: dict[str, Any]) -> dict[str, Any]:
    """Conditional equality tests using the existing request-local calculator."""
    v = calc.values
    results: dict[str, Any] = {}
    money = f'{data["currency"]}_{data["amount_scale"]}'
    def add(name, unit, formula, operands, operation, varied, target,
            domain=None, lower=None, upper=None, kind='equality_boundary_not_forecast'):
        calc.add(name, unit, formula, operands, operation, domain)
        cell = calc.cells[name]
        cell.update(authority='conditional_test_only', varied_input=varied,
                    target_ref=target, fixed_inputs=[key for key in operands if key != varied],
                    baseline_inputs=[key for key in operands if key == varied], interpretation=kind)
        number = v[name]
        if lower is not None and upper is not None:
            cell['within_value_range'] = (lower <= number <= upper) if number is not None else None
        results[name] = cell
    revenue = data['current']['revenue']
    margin = data['current']['gross_margin_pct']
    add('hold.operating_profit_margin_pct', 'percent',
        '(prior_operating_profit + current_operating_expenses) / current_revenue * 100',
        ('prior.operating_profit', 'current.operating_expenses', 'current.revenue'),
        lambda p, o, r: (p+o)/r*100, 'current.gross_margin_pct', 'prior.operating_profit',
        'positive_current_revenue_required' if revenue is not None and revenue <= 0 else None,
        Decimal(-1000), Decimal(100))
    add('hold.operating_profit_revenue', money,
        '(prior_operating_profit + current_operating_expenses) / current_margin_pct * 100',
        ('prior.operating_profit', 'current.operating_expenses', 'current.gross_margin_pct'),
        lambda p, o, m: (p+o)/m*100, 'current.revenue', 'prior.operating_profit',
        'positive_current_margin_required' if margin is not None and margin <= 0 else None,
        Decimal(0), Decimal('1e18'))
    add('zero.operating_cash_working_capital', money,
        'operating_profit + depreciation_amortization - cash_interest - cash_taxes + other_operating_cash_adjustments',
        ('current.operating_profit', 'current.depreciation_amortization', 'current.cash_interest',
         'current.cash_taxes', 'current.other_operating_cash_adjustments'),
        lambda o, d, i, t, a: o+d-i-t+a, 'current.working_capital_increase', 'literal:0',
        lower=Decimal('-1e18'), upper=Decimal('1e18'))
    add('zero.cash_after_capex_working_capital', money,
        'zero_operating_cash_working_capital - capital_expenditures',
        ('zero.operating_cash_working_capital', 'current.capital_expenditures'),
        lambda c, x: c-x, 'current.working_capital_increase', 'literal:0',
        lower=Decimal('-1e18'), upper=Decimal('1e18'))
    eps = data['current']['eps']
    annual_domain = ('annual_eps_required' if data['current']['period_months'] != 12 else
                     'positive_current_eps_required' if eps is not None and eps <= 0 else None)
    add('hold.implied_price_multiple', 'multiple', 'prior_implied_price / current_annual_eps',
        ('prior.implied_price', 'current.eps'), lambda p, e: p/e,
        'current.earnings_multiple', 'prior.implied_price', annual_domain,
        Decimal(0), Decimal('1e18'))
    sensitivity = 'local_arithmetic_sensitivity_not_forecast'
    add('sensitivity.operating_profit_per_margin_pp', money+'/percentage_point',
        'current_revenue / 100', ('current.revenue',), lambda r: r/100,
        'current.gross_margin_pct', 'current.operating_profit', kind=sensitivity)
    add('sensitivity.operating_profit_per_revenue_pct', money+'/percent_change',
        'current_revenue * current_margin_pct / 10000',
        ('current.revenue', 'current.gross_margin_pct'), lambda r, m: r*m/10000,
        'current.revenue', 'current.operating_profit', kind=sensitivity)
    add('sensitivity.implied_price_per_multiple_turn', data['currency']+'/share/multiple',
        'current_annual_eps', ('current.eps',), lambda e: e,
        'current.earnings_multiple', 'current.implied_price', annual_domain, kind=sensitivity)
    return results


def _conditional_reasoning(observations: list[str]) -> dict[str, Any]:
    """Test prompts, not inferred issuer events or sourced causal proof."""
    definitions = {
        'revenue_up_gross_profit_down': (
            'Revenue growth does not imply higher gross profit under the supplied margins.',
            ['change.revenue', 'change.gross_profit', 'bridge.gross_profit_sales_effect', 'bridge.gross_profit_margin_effect'],
            ['hold.operating_profit_margin_pct', 'hold.operating_profit_revenue'],
            [
                ('Temporary launch or product-mix investment',
                 'Dated segment mix, ramp costs and later margin conversion.',
                 'Margins fail to recover after the proposed ramp period.'),
                ('Persistent pricing or unit-cost pressure',
                 'Comparable selling prices, unit costs and repeat-period margins.',
                 'Stable prices/costs and a documented one-off mix effect explain the gap.'),
            ]),
        'current_profit_positive_operating_cash_negative': (
            'Positive operating profit does not cover the supplied operating cash uses.',
            ['current.operating_profit', 'current.simplified_operating_cash'],
            ['zero.operating_cash_working_capital', 'zero.cash_after_capex_working_capital'],
            [
                ('Temporary cash-conversion timing',
                 'Receivable collections, inventory aging, payment terms and later cash conversion.',
                 'The proposed timing gap persists or inventory/receivables deteriorate.'),
                ('Recurring cash burden not captured by operating profit alone',
                 'Dated cash-interest/tax outlays, working-capital movements and residual adjustments.',
                 'Verified nonrecurring payments unwind and comparable cash conversion recovers.'),
            ]),
        'eps_up_implied_price_down': (
            'Assumed multiple contraction more than offsets annual EPS growth in this comparison.',
            ['change.eps_pct', 'change.implied_price_pct', 'bridge.price_earnings_effect', 'bridge.price_multiple_effect'],
            ['hold.implied_price_multiple', 'sensitivity.implied_price_per_multiple_turn'],
            [
                ('The lower multiple reflects a durable earnings-quality or growth concern',
                 'Recurring versus one-off EPS, cash conversion and dated forward assumptions.',
                 'Recurring earnings and cash conversion improve without that proposed concern.'),
                ('The lower multiple reflects temporary repricing rather than weaker operations',
                 'Rates, dated peer comparisons, funding needs and subsequent operating evidence.',
                 'Company-specific operating deterioration explains the repricing better.'),
            ]),
    }
    findings = []
    for code in observations:
        conclusion, supports, tests, rivals = definitions[code]
        findings.append({
            'id': code, 'conclusion': conclusion, 'conclusion_type': 'supplied_scenario_implication',
            'supports': supports, 'reversal_tests': tests,
            'rivals': [{'hypothesis': h, 'status': 'untested', 'evidence_to_check': e, 'would_weaken': w}
                       for h, e, w in rivals],
        })
    return {
        'basis': 'conditional_arithmetic_not_causal_proof',
        'evidence_retrieval_performed': False, 'findings': findings,
        'scope': 'Illustrative rival hypotheses are not exhaustive, scored, or adjudicated. No company evidence has been read.',
        'test_assumption': 'Change one input at a time; hold other scenario inputs fixed. Equality boundaries use unrounded arithmetic; displayed values may be rounded.',
    }
