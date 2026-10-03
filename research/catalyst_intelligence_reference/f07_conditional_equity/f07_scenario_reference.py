"""Pure F07 successor CONTRACT REFERENCE; not a production valuation service.

All inputs must be synthetic. References are structural labels, never identity,
rights, source, calibration or runtime admission receipts. No network, storage,
clock, provider, ranking, recommendation or trade effect exists in this module.
The frozen engine/valuation_scenario.py and valuation_scenario.v1 are unchanged.
"""
from __future__ import annotations
import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping


class ContractError(ValueError):
    """A named incompatibility; unknown/missing input never becomes zero."""


ROOT = frozenset('mode version subject_ref share_basis_ref financial_ref rights_ref forecast_ref known_at as_of horizon currency money_unit quote opening_cash opening_debt opening_common_shares roundtrip_cost_fraction probability_semantics states'.split())
STATE = frozenset('id probability valuation_at earnings_period revenue gross_margin operating_expense interest_expense income_tax_expense other_income_claims method multiple operating_enterprise_value other_senior_claims dividend_to_entry_share cash_flow'.split())
CASH = frozenset('operating_after_interest_tax capex new_common_shares equity_issue_price equity_issue_fees new_debt debt_repayment distributions_paid'.split())
QUOTE = frozenset('id observed_at valid_until price currency subject_ref share_basis_ref common_shares_per_unit'.split())


def _shape(obj: Any, keys: frozenset[str], where: str) -> None:
    if not isinstance(obj, Mapping):
        raise ContractError(f'mapping_required:{where}')
    if set(obj) - keys:
        raise ContractError(f'unknown_fields:{where}')
    if keys - set(obj):
        raise ContractError(f'missing_fields:{where}')


def _text(v: Any, field: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ContractError(f'missing_binding:{field}')
    return v


def _d(v: Any, field: str, *, nonnegative: bool = False, positive: bool = False) -> Decimal:
    if v is None:
        raise ContractError(f'missing_numeric:{field}')
    if isinstance(v, bool) or not isinstance(v, (str, int, Decimal)):
        raise ContractError(f'numeric_type:{field}')
    try:
        n = Decimal(v)
    except (InvalidOperation, ValueError):
        raise ContractError(f'numeric_type:{field}') from None
    if not n.is_finite():
        raise ContractError(f'nonfinite:{field}')
    if positive and n <= 0:
        raise ContractError(f'positive_required:{field}')
    if nonnegative and n < 0:
        raise ContractError(f'nonnegative_required:{field}')
    return n


def _iso(v: Any, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(_text(v, field).replace('Z', '+00:00'))
    except ValueError:
        raise ContractError(f'invalid_time:{field}') from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ContractError(f'timezone_required:{field}')
    return dt


def _day(v: Any, field: str) -> date:
    try:
        return date.fromisoformat(_text(v, field))
    except ValueError:
        raise ContractError(f'invalid_date:{field}') from None


def _s(v: Decimal) -> str:
    out = format(v, 'f')
    return out.rstrip('0').rstrip('.') if '.' in out else out


def _export_input(value: Any) -> Any:
    """Canonical JSON-safe copy of the already validated synthetic envelope."""
    if isinstance(value, Decimal):
        return _s(value)
    if type(value) is int:
        return str(value)
    if isinstance(value, Mapping):
        return {k: _export_input(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_export_input(v) for v in value]
    return value


def _state(s: Mapping[str, Any], p: Mapping[str, Any], horizon: date, price: Decimal, cost: Decimal) -> dict[str, Any]:
    _shape(s, STATE, 'state')
    _text(s['id'], 'state.id')
    if _day(s['valuation_at'], 'valuation_at') != horizon:
        raise ContractError('horizon_mismatch')
    period = s['earnings_period']
    _shape(period, frozenset(('start', 'end', 'basis')), 'earnings_period')
    start = _day(period['start'], 'earnings_period.start')
    end = _day(period['end'], 'earnings_period.end')
    try:
        next_year = start.replace(year=start.year + 1)
    except ValueError:  # A 29-Feb start includes the full following February.
        next_year = date(start.year + 1, 3, 1)
    if (period['basis'] != 'forward_12m' or start != horizon + timedelta(days=1)
            or end != next_year - timedelta(days=1)):
        raise ContractError('annual_basis_required')

    revenue = _d(s['revenue'], 'revenue', nonnegative=True)
    gm = _d(s['gross_margin'], 'gross_margin')
    if gm > 1:
        raise ContractError('margin_above_one')
    gp = revenue * gm
    operating = gp - _d(s['operating_expense'], 'operating_expense', nonnegative=True)
    pretax = operating - _d(s['interest_expense'], 'interest_expense', nonnegative=True)
    # An explicitly provided tax benefit may be negative; none is inferred from a loss.
    common = (pretax - _d(s['income_tax_expense'], 'income_tax_expense')
              - _d(s['other_income_claims'], 'other_income_claims', nonnegative=True))

    cf = s['cash_flow']
    _shape(cf, CASH, 'cash_flow')
    n = {k: _d(cf[k], k, nonnegative=k != 'operating_after_interest_tax')
         for k in CASH - {'equity_issue_price'}}
    new_shares = n['new_common_shares']
    if new_shares:
        issue_price = _d(cf['equity_issue_price'], 'equity_issue_price', positive=True)
        issue_proceeds = issue_price * new_shares
    else:
        if cf['equity_issue_price'] is not None or n['equity_issue_fees'] != 0:
            raise ContractError('issuance_without_shares')
        issue_proceeds = Decimal(0)
    if n['equity_issue_fees'] > issue_proceeds:
        raise ContractError('fees_exceed_proceeds')
    debt = (_d(p['opening_debt'], 'opening_debt', nonnegative=True)
            + n['new_debt'] - n['debt_repayment'])
    if debt < 0:
        raise ContractError('negative_debt')
    cash = (_d(p['opening_cash'], 'opening_cash', nonnegative=True)
            + n['operating_after_interest_tax'] - n['capex']
            + issue_proceeds - n['equity_issue_fees']
            + n['new_debt'] - n['debt_repayment'] - n['distributions_paid'])
    if cash < 0:
        raise ContractError('unfunded_path')
    opening_shares = _d(p['opening_common_shares'], 'opening_common_shares', positive=True)
    shares = opening_shares + new_shares
    dividend = _d(s['dividend_to_entry_share'], 'dividend_to_entry_share', nonnegative=True)
    if dividend * opening_shares > n['distributions_paid']:
        raise ContractError('distribution_inconsistent')

    claims = _d(s['other_senior_claims'], 'other_senior_claims', nonnegative=True)
    if s['method'] == 'common_earnings_multiple':
        # This fixed multiple has no proceeds-deployment/excess-cash model.
        # Use the operating-enterprise branch for share-issuance scenarios.
        if new_shares != 0:
            raise ContractError('pe_financing_out_of_scope')
        if s['operating_enterprise_value'] is not None:
            raise ContractError('mixed_valuation_methods')
        if claims != 0:
            raise ContractError('pe_claim_basis')
        if common <= 0:
            raise ContractError('nonpositive_pe_earnings')
        multiple = _d(s['multiple'], 'multiple', positive=True)
        residual = common * multiple  # Common earnings multiple already values equity.
    elif s['method'] == 'operating_enterprise':
        if s['multiple'] is not None:
            raise ContractError('mixed_valuation_methods')
        ev = _d(s['operating_enterprise_value'], 'operating_enterprise_value', nonnegative=True)
        # EV must exclude cash and senior claims, at this same horizon.
        residual = ev + cash - debt - claims
    else:
        raise ContractError('unsupported_valuation_method')
    equity = max(Decimal(0), residual)  # Explicit limited-liability common-equity reference rule.
    terminal_price = equity / shares
    gross_return = (terminal_price + dividend) / price - 1
    return {'id': s['id'], 'method': s['method'],
            'probability': _s(_d(s['probability'], 'probability')) if s['probability'] is not None else None,
            'gross_profit': _s(gp), 'operating_income': _s(operating),
            'net_common_income': _s(common), 'equity_issue_gross_proceeds': _s(issue_proceeds),
            'horizon_cash': _s(cash), 'horizon_debt': _s(debt),
            'horizon_common_shares': _s(shares), 'equity_residual_before_floor': _s(residual),
            'limited_liability_floor_applied': residual < 0, 'equity_value': _s(equity),
            'price_at_horizon': _s(terminal_price), 'dividend_to_entry_share': _s(dividend),
            'gross_return': _s(gross_return), 'net_return': _s(gross_return - cost)}


def evaluate(packet: Mapping[str, Any], *, expected_version: str) -> dict[str, Any]:
    """Evaluate a complete synthetic envelope, or raise ContractError.

    Output is always research/reference-only. Caller-provided labels and weights
    cannot make it a calibrated forecast or authorized production recommendation.
    """
    with localcontext() as ctx:
        ctx.prec = 34
        _shape(packet, ROOT, 'packet')
        if packet['mode'] != 'synthetic_reference':
            raise ContractError('reference_only')
        if packet['version'] != expected_version:
            raise ContractError('version_mismatch')
        for name in ('version', 'subject_ref', 'share_basis_ref', 'financial_ref', 'rights_ref', 'forecast_ref', 'currency'):
            _text(packet[name], name)
        if packet['money_unit'] != 'currency_units':
            raise ContractError('unit_mismatch')
        at = _iso(packet['as_of'], 'as_of')
        known_at = _iso(packet['known_at'], 'known_at')
        if known_at > at:
            raise ContractError('future_input')
        horizon = _day(packet['horizon'], 'horizon')
        if horizon <= at.date():
            raise ContractError('horizon_not_future')
        quote = packet['quote'];_shape(quote, QUOTE, 'quote');_text(quote['id'], 'quote.id')
        if quote['currency'] != packet['currency']:
            raise ContractError('currency_mismatch')
        quote_at = _iso(quote['observed_at'], 'quote.observed_at')
        if quote_at > at:
            raise ContractError('future_quote')
        if quote_at < known_at:
            raise ContractError('quote_precedes_information')
        if _text(quote['subject_ref'], 'quote.subject_ref') != packet['subject_ref']:
            raise ContractError('quote_subject_mismatch')
        if _text(quote['share_basis_ref'], 'quote.share_basis_ref') != packet['share_basis_ref']:
            raise ContractError('quote_share_basis_mismatch')
        if _d(quote['common_shares_per_unit'], 'quote.common_shares_per_unit', positive=True) != 1:
            raise ContractError('share_conversion_not_supported')
        if _iso(quote['valid_until'], 'quote.valid_until') <= at:
            raise ContractError('stale_quote')
        price = _d(quote['price'], 'quote.price', positive=True)
        cost = _d(packet['roundtrip_cost_fraction'], 'roundtrip_cost_fraction', nonnegative=True)
        if cost >= 1:
            raise ContractError('cost_out_of_scope')
        states = packet['states']
        if not isinstance(states, list) or not states:
            raise ContractError('states_required')
        for s in states:
            _shape(s, STATE, 'state');_text(s['id'], 'state.id')
        if len({s['id'] for s in states}) != len(states):
            raise ContractError('duplicate_state')
        raw = [s['probability'] for s in states]
        weighted = all(v is not None for v in raw)
        if not weighted and any(v is not None for v in raw):
            raise ContractError('partial_probabilities')
        semantics = packet['probability_semantics']
        if semantics not in ('illustrative_partition', 'unweighted_conditional'):
            raise ContractError('unsupported_probability_semantics')
        if weighted != (semantics == 'illustrative_partition'):
            raise ContractError('probability_semantics_mismatch')
        weights = [_d(v, 'probability', nonnegative=True) for v in raw] if weighted else []
        if weighted and (any(v > 1 for v in weights) or sum(weights) != 1):
            raise ContractError('weights_not_one')
        results = [_state(s, packet, horizon, price, cost) for s in states]
        expected = sum(w * Decimal(s['net_return']) for w, s in zip(weights, results)) if weighted else None
        profitable = sum(w for w, s in zip(weights, results) if Decimal(s['net_return']) > 0) if weighted else None
        binding = {k: packet[k] for k in ('version', 'subject_ref', 'share_basis_ref', 'financial_ref', 'rights_ref', 'forecast_ref', 'known_at', 'as_of', 'horizon', 'currency')}
        binding['quote_id'] = quote['id']
        # An export must be self-contained: synthetic labels cannot dereference inputs.
        envelope = _export_input(packet)
        canonical = json.dumps(envelope, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        input_digest = hashlib.sha256(canonical).hexdigest()
        return {'scope':'synthetic_contract_reference',
                'status':'illustrative_weighted' if weighted else 'conditional_only',
                'binding':binding, 'states':results,
                'input_envelope':envelope, 'input_sha256':input_digest,
                'illustrative_expected_net_return':_s(expected) if expected is not None else None,
                'probability_of_positive_net_return':_s(profitable) if profitable is not None else None,
                'probability_semantics':semantics, 'production_admission':False,
                'can_rank':False, 'recommendation':None, 'calibrated_probability':None,
                'liquidity_path_assessed':False,
                'limitations':['Endpoint cash does not prove interim funding availability.',
                               'Synthetic labels are not admitted owner receipts.',
                               'Scenario weights are illustrative, not calibrated forecasts.',
                               'P/E states do not support new common-share issuance.',
                               'Only matching one-common-share quote units are supported.',
                               'Post-information quote ordering is not an executable-fill receipt.',
                               'No buybacks, conversions, share exchanges or tax model are implemented.']}
