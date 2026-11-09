"""Resources Catalyst R2 — pure research arithmetic, NOT a production owner/API.

Contracts here are specimen interfaces for testing proposed financial semantics. They do
not grant source/rights/model/policy admission. All money in a call must have the SAME
currency and basis; all input availability/conditions must be qualified upstream. Public
contract summaries are not complete executed agreements. No network, writes, ranking,
prices, clocks, model fitting or hidden defaults are used by these functions.
"""
from datetime import date
from decimal import Decimal as D
from resources_catalyst_r1_reference import number, nonnegative, fraction, stream_cashflow

DRAW_CONDITIONS=('cost_to_complete_funded','permits','security','engineering_confirmation')
VALUATION_INPUTS=('native_security','dated_rights','technical_cashflows','tax_timing',
                  'funding_conditions','diluted_capital','common_valuation_date',
                  'market_reference','policy_permission')


def _tri(value):
    if value is not None and type(value) is not bool:
        raise ValueError('expected_boolean_or_unknown')
    return value


def _day(value):
    if not isinstance(value,str): raise ValueError('date_string_required')
    parsed=date.fromisoformat(value)
    if parsed.isoformat()!=value: raise ValueError('canonical_calendar_date_required')
    return parsed


def _int(value, *, signed=False):
    if type(value) is not int or (not signed and value<0):
        raise ValueError('integer_required')
    return value


def cost_bridge(before_tax, taxes_paid, future_recoverable, spent_to_cutoff):
    """Separate initial construction cash from net economic cost; no tax-timing claim."""
    if any(x is None for x in (before_tax,taxes_paid,future_recoverable,spent_to_cutoff)):
        return None
    base,tax,recovery,spent=map(nonnegative,(before_tax,taxes_paid,future_recoverable,spent_to_cutoff))
    cash=base+tax
    if recovery>tax: raise ValueError('recovery_exceeds_tax')
    if spent>cash: raise ValueError('spend_exceeds_budget_rebaseline_required')
    return dict(cash_initial=cash,economic_initial=cash-recovery,
                cash_remaining=cash-spent,future_recoverable=recovery)


def draw_eligibility(family, cumulative_eligible_spend, minimum_spend,
                     predecessor_drawn, predecessor_capacity, conditions):
    """Eligibility is NOT cash disbursement. Full legal conditions still need an owner.

    'stream' and 'loan' are local specimen types, not canonical event/facility IDs.
    Supplied conditions must be verified as of the selected cutoff. A dated agreement
    cannot backdate our knowledge of a term disclosed only in a later filing.
    """
    if family not in {'stream','loan'}: raise ValueError('unsupported_specimen_facility')
    if set(conditions)!=set(DRAW_CONDITIONS): raise ValueError('closed_condition_set')
    failed=[]; unknown=[]
    checks={k:_tri(conditions[k]) for k in DRAW_CONDITIONS}
    if family=='stream':
        checks['minimum_project_spend']=(None if cumulative_eligible_spend is None or minimum_spend is None
            else nonnegative(cumulative_eligible_spend)>=nonnegative(minimum_spend))
    else:
        checks['prior_stream_fully_drawn']=(None if predecessor_drawn is None or predecessor_capacity is None
            else nonnegative(predecessor_drawn)>=nonnegative(predecessor_capacity))
    for key,state in checks.items():
        if state is False: failed.append(key)
        elif state is None: unknown.append(key)
    state='NOT_ELIGIBLE' if failed else 'UNVERIFIED' if unknown else 'ELIGIBLE_NOT_DRAWN'
    return dict(state=state,failed=tuple(failed),unknown=tuple(unknown),cash_received=None)


def loan_period(commitment, face_drawn_on_entry, new_face_draw, sofr, contract_completion,
                years, capitalize, *, capitalized_on_entry='0'):
    """One uniform-rate period, draw at START. Scenario, not an executed loan calculator.

    Assumes no intraperiod repayments; a single simple-interest period <=1 year. OID is
    withheld from cash, not face principal. Standby uses undrawn FACE capacity, not accrued
    debt. Capitalized interest compounds in the NEXT period. Actual day-count, SOFR floor,
    draw conditions and capitalization elections require executed-document qualification.
    'contract_completion' must never be inferred from a commercial-production headline.
    """
    _tri(contract_completion);_tri(capitalize)
    if capitalize is None: return None
    values=(commitment,face_drawn_on_entry,new_face_draw,sofr,years,capitalized_on_entry)
    if any(x is None for x in values) or contract_completion is None: return None
    cap,face,draw,base,t,accrued=map(nonnegative,values)
    if t>1: raise ValueError('split_long_period')
    if face+draw>cap: raise ValueError('facility_overdraw')
    margin=D('.0475') if contract_completion else D('.0575')
    coupon=base+margin
    opening_interest_base=face+draw+accrued
    undrawn=cap-face-draw
    interest=opening_interest_base*coupon*t
    standby=undrawn*D('.01')*t
    fees=interest+standby
    return dict(new_cash=draw*D('.98'),original_issue_discount=draw*D('.02'),
                coupon=coupon,interest=interest,standby_fee=standby,
                undrawn_face=undrawn,cash_interest_and_fees=D(0) if capitalize else fees,
                closing_principal=opening_interest_base+(fees if capitalize else D(0)))


def equal_principal_repayments(amortization_base, count, fraction_per_installment):
    """Equal installments on a FIXED supplied base; no calendar dates are guessed.

    The source describes ten 7.5% installments plus 25% bullet. Exact repayment base,
    capitalized balances and final legal maturity must be checked in the agreement.
    """
    base=nonnegative(amortization_base);count=_int(count);part=fraction(fraction_per_installment)
    if count<1 or count*part>1: raise ValueError('invalid_amortization_mass')
    amounts=tuple(base*part for _ in range(count))
    return dict(installments=amounts,bullet=base-sum(amounts,D(0)))


def stream_life(output_oz, threshold_remaining_oz, high_rate, low_rate, payment_fraction, gold_price):
    """Source-plan sensitivity under constant price and produced==payable assumptions.

    This is gross revenue transfer, NOT margin, after-tax value, equity value or a forecast
    of stream duration. Ore reserve ounces, recovered ounces and delivered stream ounces
    are not interchangeable. The unchanged R1 threshold calculation is reused.
    """
    result=stream_cashflow(output_oz,threshold_remaining_oz,high_rate,low_rate,payment_fraction,gold_price)
    if result is None: return None
    output=nonnegative(output_oz);left=nonnegative(threshold_remaining_oz);high=fraction(high_rate)
    full_value=output*nonnegative(gold_price)
    threshold_output=left/high
    return dict(stream_oz=result['stream_ounces'],operator_revenue=result['retained_revenue'],
                net_revenue_transfer=full_value-result['retained_revenue'],
                remaining_threshold_oz=result['threshold_remaining'],
                output_needed_for_first_stepdown_oz=threshold_output,
                lower_tier_used=output>threshold_output)


def acquisition_payment_paths(total, deferrable_fraction, premium, discount_rate):
    """Latest contractual-anniversary alternatives, not advice to postpone payment.

    time0 is assumed commercial-production trigger; earlier voluntary payment is possible.
    No calendar due dates, notice fulfillment, failure recovery or probability inferred.
    The one-year extension rate is premium / amount deferred, not premium / total claim.
    """
    amount=nonnegative(total);share=fraction(deferrable_fraction);fee=nonnegative(premium)
    rate=nonnegative(discount_rate);deferred=amount*share
    if deferred==0: raise ValueError('no_deferrable_amount')
    normal=((1,amount),);later=((1,amount-deferred),(2,deferred+fee))
    pv=lambda schedule:sum((cash/(1+rate)**year for year,cash in schedule),D(0))
    return dict(normal=normal,defer=later,one_year_extension_rate=fee/deferred,
                pv_normal=pv(normal),pv_defer=pv(later))


def share_rollforward(opening_shares, baseline_date, changes, cutoff, census_complete):
    """Observed deltas cannot establish an exact denominator from an incomplete census.

    Caller is responsible for FIRST-KNOWN filtering of event records before this function.
    No reverse derivation from rounded investor percentages or a later annual total.
    Returns a known delta even when the opening identity/count remains unbound.
    """
    start=_day(baseline_date);end=_day(cutoff);complete=_tri(census_complete)
    if end<start: raise ValueError('cutoff_before_baseline')
    opening=None if opening_shares is None else _int(opening_shares)
    seen=set();events=[]
    for record in changes:
        key=record['id']
        if not isinstance(key,str) or not key or key in seen: raise ValueError('duplicate_or_missing_issue_id')
        seen.add(key);day=_day(record['date']);delta=_int(record['count'],signed=True)
        if start<day<=end:events.append((day,key,delta))
    events.sort();delta=sum(e[2] for e in events)
    if opening is not None and opening+delta<0:raise ValueError('negative_share_count')
    shares=opening+delta if opening is not None and complete is True else None
    return dict(shares=shares,known_issuance_delta=delta,included=tuple(e[1] for e in events))


def research_eligibility(inputs):
    """Specimen missing-input explainer. Never use as production admission/rights policy."""
    if set(inputs)!=set(VALUATION_INPUTS):raise ValueError('closed_input_set')
    unresolved=tuple(k for k in VALUATION_INPUTS if _tri(inputs[k]) is not True)
    return dict(state='WITHHELD' if unresolved else 'INPUTS_COMPLETE_NOT_VALUED',
                unresolved=unresolved,equity_value=None,can_rank=False,can_gate=False,
                can_size=False,can_originate=False,can_open_entry=False)
