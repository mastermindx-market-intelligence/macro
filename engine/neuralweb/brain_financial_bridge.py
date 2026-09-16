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
        count = sum(c['value'] is not None for c in calc.cells.values())
        return {
            'schema': SCHEMA, 'status': 'complete' if count == len(calc.cells) else 'partial' if count else 'unavailable',
            'authority': 'analysis_only', 'input_provenance': 'caller_supplied_unverified',
            'currency': data['currency'], 'amount_scale': data['amount_scale'],
            'period_months': data['prior']['period_months'],
            'rounding': 'up_to_12_significant_decimal_digits_half_even',
            'inputs': {f'{p}.{f}': _plain(data[p][f]) if data[p][f] is not None else None
                       for p in ('prior','current') for f in _FIELDS},
            'calculations': calc.cells, 'arithmetic_observations': observations,
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
