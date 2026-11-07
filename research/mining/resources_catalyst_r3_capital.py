"""R3 pure RESEARCH specimens, not production identity/capital/evaluation owners.

Date views are calendar-disclosure views, NOT intraday first-known proof. Inputs must
already carry owner-qualified identities, rights, basis and versions; this module does
not mint or persist them. No network, storage, fitting, ranking, or trade authority.
"""
from collections import Counter
from datetime import date
from decimal import Decimal as D
from typing import Any, Iterable, Mapping, Sequence
from resources_catalyst_r1_reference import nonnegative


def _day(value: str) -> date:
    if not isinstance(value,str): raise ValueError('date_required')
    try: parsed=date.fromisoformat(value)
    except ValueError as exc: raise ValueError('invalid_calendar_date') from exc
    if parsed.isoformat()!=value: raise ValueError('canonical_calendar_date_required')
    return parsed


def _count(value: Any) -> int:
    if type(value) is not int or value<0: raise ValueError('nonnegative_integer_required')
    return value


def _unique(rows: Sequence[Mapping[str,Any]]) -> None:
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('missing_or_duplicate_identity')


def visible_events(events: Sequence[Mapping[str,Any]], cutoff_date: str,
                   mode: str='public_reconstruction') -> list[Mapping[str,Any]]:
    """Availability from the supplied source set, not globally earliest publication.

    A known future proposal stays visible as a proposal. Actual count effects are
    separately dated below. Date equality means a date-labelled disclosure view only.
    Corrections/repeated native IDs must be resolved by the existing owner first.
    """
    if mode not in {'public_reconstruction','system_replay'}: raise ValueError('invalid_time_mode')
    cut=_day(cutoff_date); _unique(events); result=[]
    for e in events:
        known,recorded=_day(e['known_on']),_day(e['recorded_on'])
        _day(e['effective_on'])
        if known<=cut and (mode=='public_reconstruction' or recorded<=cut): result.append(e)
    return result


def reconcile_capital(opening: int, events: Sequence[Mapping[str,Any]], anchor_date: str,
                      cutoff_date: str, basis: str, reported_total: int|None=None,
                      census_complete: bool=False) -> dict[str,Any]:
    """Sparse common-share bridge. 'covered_total' is NOT estimated shares outstanding.

    A caller binds the reported_total to the relevant end-date/source before use.
    Basis identifies the same issuer/share class/corporate-action units, not a ticker.
    This reference accepts only an explicit prequalified coverage flag; a zero residual
    does not create that flag or certify an otherwise incomplete event census.
    """
    total=_count(opening); start,end=_day(anchor_date),_day(cutoff_date)
    if start>end: raise ValueError('future_anchor')
    if not isinstance(basis,str) or not basis: raise ValueError('basis_required')
    if type(census_complete) is not bool: raise ValueError('coverage_boolean_required')
    reported=None if reported_total is None else _count(reported_total)
    visible=visible_events(events,cutoff_date); contributions=[]; ignored=[]
    kinds={'common_issue','common_retirement','secondary_trade','warrant_issue','reported_total','proposed_issue'}
    for e in visible:
        if e['basis']!=basis: raise ValueError('incompatible_share_basis')
        if e['kind'] not in kinds: raise ValueError('unknown_event_kind')
        count=_count(e['count']); effective=_day(e['effective_on'])
        if start<effective<=end and e['kind'] in {'common_issue','common_retirement'}:
            delta=count if e['kind']=='common_issue' else -count
            contributions.append((e['id'],delta));total+=delta
        else: ignored.append(e['id'])
    if total<0: raise ValueError('negative_common_count')
    gap=None if reported is None else reported-total
    conflict=census_complete and gap not in (None,0)
    complete=census_complete and not conflict
    return dict(covered_total=total,reported_total=reported,unexplained_net_movement=gap,
                exact_total=total if complete else None,
                state='CONFLICT' if conflict else ('RECONCILED' if complete else 'INCOMPLETE_CENSUS'),
                included=tuple(contributions),ignored=tuple(ignored),basis=basis,
                intraday_eligible=False,can_rank=False)


def settle_warrants(rights: int, shares_per_right: Any, strike_per_right: Any,
                    mode: str, eligible: bool|None, *, cashless_shares_per_right: Any=None) -> dict[str,Any]:
    """Conditional settlement arithmetic, never a receipt of exercise/cash.

    'strike_per_right' is the cash required to exercise ONE warrant. Under a 4:1
    share-unit change, that warrant may deliver .25 shares at the same per-right cost.
    Cashless conversion is deliberately NOT invented from a generic market formula.
    A supplied cashless ratio must already be qualified under the actual agreement.
    """
    w=_count(rights);q,k=nonnegative(shares_per_right),nonnegative(strike_per_right)
    if q==0: raise ValueError('zero_deliverable')
    if mode not in {'cash','cashless'}: raise ValueError('unknown_settlement_mode')
    if eligible is not None and type(eligible) is not bool: raise ValueError('eligibility_boolean_required')
    ratio=None if cashless_shares_per_right is None else nonnegative(cashless_shares_per_right)
    if ratio is not None and ratio>q: raise ValueError('cashless_ratio_exceeds_deliverable')
    result=dict(state='CONDITIONAL_ONLY',new_shares=None,conditional_issuer_cash=None,
                price_per_whole_share=k/q,actual_exercise=False,can_rank=False)
    if eligible is not True:
        result['state']='INELIGIBLE' if eligible is False else 'ELIGIBILITY_UNBOUND'
    elif mode=='cash':
        result.update(new_shares=w*q,conditional_issuer_cash=w*k)
    else:
        result['conditional_issuer_cash']=D(0)
        if ratio is None: result['state']='CASHLESS_RATIO_UNBOUND'
        else: result['new_shares']=w*ratio
    return result


def first_transition_cif(rows: Sequence[Mapping[str,Any]], horizon: int,
                         causes: Iterable[str]=('delivery','equity_extinguished')) -> dict[str,Any]:
    """Aalen-Johansen first-transition empirical reference; common entry at time zero.

    Independent-censoring and comparable cohort/target assumptions are NOT established
    by running this function. Exact nonnegative integer times only; interval censoring,
    delayed entry, weights, recurrent events and unknown event types require separately
    qualified methods. At tied times events occur before administrative censor removal.
    Sparse/selected fixtures never qualify a mining forecast or a recommendation.
    """
    h=_count(horizon); cs=tuple(causes)
    if not cs or any(not isinstance(c,str) or not c or c=='censored' for c in cs) or len(set(cs))!=len(cs):
        raise ValueError('invalid_causes')
    if not rows: raise ValueError('empty_cohort')
    _unique(rows)
    for r in rows:
        if set(r)!={'id','time','cause'}: raise ValueError('unsupported_record_shape')
        _count(r['time'])
        if r['cause'] not in (*cs,'censored'): raise ValueError('unqualified_cause')
    n=len(rows);s=D(1);cif={c:D(0) for c in cs};steps=[]
    for t in sorted({r['time'] for r in rows if r['time']<=h}):
        at=Counter(r['cause'] for r in rows if r['time']==t)
        d=sum(at[c] for c in cs);prior=s
        for c in cs:cif[c]+=prior*D(at[c])/D(n)
        s=prior*(D(1)-D(d)/D(n))
        steps.append(dict(time=t,at_risk=n,events={c:at[c] for c in cs},censored=at['censored']))
        n-=d+at['censored']
    exhausted=h>max(r['time'] for r in rows) and s>0
    return dict(state='FOLLOWUP_EXHAUSTED' if exhausted else 'REFERENCE_ONLY',
                cif=None if exhausted else cif,event_free=None if exhausted else s,
                horizon=h,cohort_size=len(rows),at_risk_after_horizon=n,steps=steps,
                can_rank=False,empirically_qualified=False)
