"""Resources Catalyst R1: executable RESEARCH-ONLY arithmetic specimens.

No network, production imports, collectors, storage, ranking or recommendation authority.
Amounts in each call must already share currency, perimeter, valuation date and units.
Millions of currency and millions of shares yield currency/share. Operational values are
AFTER future project spending/stream burdens at the specified horizon; funding already
spent before that horizon must not be added again as cash. Source/rights admission stays
with the incumbent owners. These examples are not an accepted replacement owner API.
"""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal as D, InvalidOperation

AUTHORITY = dict(can_rank=False, can_gate=False, can_size=False,
                 can_originate=False, can_open_entry=False)


def number(value):
    """Finite decimal; reject booleans and absent values rather than treating them as zero."""
    if value is None or isinstance(value, bool):
        raise ValueError('missing_or_boolean_number')
    try:
        result = D(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('invalid_number') from exc
    if not result.is_finite():
        raise ValueError('nonfinite_number')
    return result


def nonnegative(value):
    value = number(value)
    if value < 0: raise ValueError('negative_number')
    return value


def fraction(value, *, below_one=False):
    value = nonnegative(value)
    if value > 1 or (below_one and value == 1): raise ValueError('invalid_fraction')
    return value


def available_funding(items, currency):
    """Availability must be qualified upstream for the SAME entity, use and time.

    known_available is a subtotal, NOT a certified fully usable total if complete=False.
    CONDITIONAL/RESTRICTED facilities are excluded, not silently promoted by a headline.
    Reported cash without proven use constraints is UNKNOWN, not AVAILABLE.
    """
    total, seen, excluded, unknown = D(0), set(), [], []
    for item in items:
        key = item['id']
        if not key or key in seen: raise ValueError('duplicate_or_missing_facility')
        seen.add(key)
        if item['currency'] != currency: raise ValueError('unbound_fx')
        state = item['availability']
        if state not in {'AVAILABLE','CONDITIONAL','RESTRICTED','UNKNOWN'}:
            raise ValueError('unknown_availability_state')
        amount = None if item['amount'] is None else nonnegative(item['amount'])
        if state in {'CONDITIONAL','RESTRICTED'}:
            excluded.append(key)
        elif state == 'UNKNOWN' or amount is None:
            unknown.append(key)
        else:
            total += amount
    return dict(known_available=total, complete=not unknown,
                excluded=tuple(excluded), unknown=tuple(unknown))


def stream_cashflow(produced_oz, threshold_remaining_oz, high_rate, low_rate,
                    payment_fraction, spot):
    """Simplified quoted-term model; NOT a full executed agreement parser.

    Threshold means delivered STREAM ounces, not total mine ounces. The whole-output
    spot fraction is pre-tax/pre-operating-cost gross realization. Delivery lag, payable
    metal, refiners, minimum deliveries and agreement exceptions need separate contracts.
    """
    if threshold_remaining_oz is None: return None
    produced, left, price = map(nonnegative,(produced_oz,threshold_remaining_oz,spot))
    high, low, pay = map(fraction,(high_rate,low_rate,payment_fraction))
    if high == 0: raise ValueError('zero_high_rate')
    high_production = min(produced, left/high)
    delivered_high = high_production*high
    delivered = delivered_high + (produced-high_production)*low
    retained = (produced-delivered+delivered*pay)*price
    return dict(stream_ounces=delivered, retained_revenue=retained,
                threshold_remaining=max(D(0),left-delivered_high),
                retained_spot_fraction=(retained/(produced*price) if produced*price else None))


def equity_raise(net_needed, fee_rate, issue_price):
    need, price = map(nonnegative,(net_needed,issue_price))
    fee = fraction(fee_rate,below_one=True)
    if price == 0: raise ValueError('zero_issue_price')
    gross = need/(1-fee)
    return dict(gross=gross, fees=gross*fee, new_shares=gross/price)


def equity_price(operating_value, other_assets, horizon_cash, senior_claims,
                 old_shares, new_shares):
    values=(operating_value,other_assets,horizon_cash,senior_claims,old_shares,new_shares)
    if any(x is None for x in values): return None
    # Asset values can be signed, e.g. closure obligations; share counts cannot.
    op, rest, cash, claims = map(number,values[:4])
    old, new = map(nonnegative,values[4:])
    if old+new == 0: raise ValueError('zero_share_count')
    if cash < 0 or claims < 0: raise ValueError('invalid_cash_or_claims')
    return max(D(0),op+rest+cash-claims)/(old+new)


def net_return(terminal_price, reference_price, buy_cost, sell_cost, distribution='0'):
    end, start, distribution = map(nonnegative,(terminal_price,reference_price,distribution))
    buy, sell = map(fraction,(buy_cost,sell_cost))
    if start == 0: raise ValueError('zero_reference_price')
    return (end*(1-sell)+distribution)/(start*(1+buy))-1


def funding_path(opening_cash, dated_net_flows):
    """Period-end funding path, with same-date flows netted. No intraday claim.

    Pass only upstream-qualified realizable flows. An end balance cannot erase an earlier
    cash shortfall. Monthly periods do not prove within-month solvency or lender consent.
    """
    cash = minimum = nonnegative(opening_cash)
    flows = defaultdict(lambda: D(0))
    for day, flow in dated_net_flows:
        parsed = date.fromisoformat(day)
        if parsed.isoformat() != day:
            raise ValueError('canonical_calendar_date_required')
        flows[day] += number(flow)
    breach = None
    for day in sorted(flows):
        cash += flows[day]
        minimum = min(minimum,cash)
        if cash < 0 and breach is None: breach=day
    return dict(closing_cash=cash,minimum_cash=minimum,first_breach=breach)


def probability_weighted_return(probabilities, returns):
    """Arithmetic only. Does not fit, qualify or grant authority to a probability model."""
    if len(probabilities)!=len(returns) or not probabilities: raise ValueError('invalid_scenario_count')
    if any(x is None for x in (*probabilities,*returns)): return None
    probs=list(map(fraction,probabilities)); rets=list(map(number,returns))
    if abs(sum(probs)-1)>D('1e-12'): raise ValueError('probability_mass')
    return sum((p*r for p,r in zip(probs,rets)),D(0))


def reconcile_total(reported, components):
    total=number(reported); calculated=sum(map(number,components),D(0))
    return dict(reported=total,calculated=calculated,residual=calculated-total,
                exact_match=calculated==total)


def _clock(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None: raise ValueError('timezone_required')
    return result


def evidence_admissible(publication_upper, recorded_at, cutoff, time_mode):
    """Date uncertainty uses upper bound; reconstruction never establishes old possession.

    pub upper bounds must have a source-qualified timezone; date-only UTC here is a
    test specimen, not an asserted release time for the real historical company.
    """
    pub, recorded, cut=map(_clock,(publication_upper,recorded_at,cutoff))
    if time_mode not in {'public_reconstruction','system_replay'}: raise ValueError('time_mode')
    return pub <= cut and (time_mode=='public_reconstruction' or recorded <= cut)
