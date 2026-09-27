"""R6 isolated acceptance examples for semiconductor options confluence.

Consumes already-produced owner aggregates. No source ingestion, chain/heatmap
construction, trade signing, storage, model fit, runtime or production imports.
Probability arithmetic accepts SYNTHETIC inputs only. Not a production validator.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from math import log
from typing import Any, Mapping, Sequence

D = Decimal


def _d(value: Any, *, nonnegative: bool = False, positive: bool = False) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError('a finite number is required')
    try:
        result = D(str(value))
    except (ValueError, InvalidOperation) as exc:
        raise ValueError('invalid number') from exc
    if not result.is_finite() or (nonnegative and result < 0) or (positive and result <= 0):
        raise ValueError('number outside domain')
    return result


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('aware timestamp required')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid timestamp') from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('timezone required')
    return stamp


def _fraction(value: Any, *, positive: bool = False) -> Decimal:
    value = _d(value, nonnegative=True, positive=positive)
    if value > 1:
        raise ValueError('fraction exceeds one')
    return value


def _required_match(a: Mapping, b: Mapping, fields: Sequence[str]) -> bool:
    return all(a.get(key) is not None and a.get(key) == b.get(key) for key in fields)


def activity_change(before: Mapping, after: Mapping) -> dict:
    """Compare disjoint interval totals, never differences of cumulative totals.

    signed_delta_usd is the upstream demand estimate, NOT dealer inventory.
    Acceleration is change in signed USD/min divided by window-center separation.
    Missing signed evidence does not discard measured unusual premium activity.
    """
    if not _required_match(before, after, ('population_ref', 'sign_method', 'units')):
        raise ValueError('incompatible activity definitions')
    windows = []
    for obj in (before, after):
        minutes = _d(obj['window_minutes'], positive=True)
        premium = _d(obj['gross_premium_usd'], nonnegative=True)
        baseline = _d(obj['baseline_premium_per_min'], positive=True)
        mass = _d(obj['absolute_delta_usd'], nonnegative=True)
        signed = None if obj['signed_delta_usd'] is None else _d(obj['signed_delta_usd'])
        if signed is not None and abs(signed) > mass:
            raise ValueError('signed delta exceeds absolute delta mass')
        end = _time(obj['interval_end'])
        center = end - timedelta(seconds=float(minutes * 30))
        windows.append(dict(minutes=minutes, end=end, center=center,
                            pace=premium/minutes/baseline,
                            balance=None if signed is None or mass == 0 else signed/mass,
                            rate=None if signed is None else signed/minutes, mass=mass))
    a, b = windows
    if b['end'] - timedelta(seconds=float(b['minutes']*60)) < a['end']:
        raise ValueError('overlapping or unordered interval windows')
    elapsed = D(str((b['center']-a['center']).total_seconds()))/60
    if elapsed <= 0:
        raise ValueError('nonpositive interval separation')
    acc = None if a['rate'] is None or b['rate'] is None else (b['rate']-a['rate'])/elapsed
    delta = None if a['balance'] is None or b['balance'] is None else b['balance']-a['balance']
    direction = ('unavailable' if b['rate'] is None else
                 'no_directional_mass' if b['mass'] == 0 else
                 'positive_delta_demand_estimate' if b['rate'] > 0 else
                 'negative_delta_demand_estimate' if b['rate'] < 0 else 'balanced_delta_demand_estimate')
    return dict(pace_before=a['pace'], pace_after=b['pace'],
                delta_balance_before=a['balance'], delta_balance_after=b['balance'],
                one_sided_change=delta, signed_rate_acceleration=acc,
                acceleration_unit='USD delta notional/minute^2',
                center_separation_minutes=elapsed, direction=direction,
                probability=None, position_observed=False)


def concentration_change(before: Mapping, after: Mapping) -> dict:
    """Consume topology statistics; do not rebuild #7298's existing topology.

    Conservative reference compares fixed-support magnitude maps. Changed support
    needs the owner's composition/decomposition return before interpreting a delta.
    Raw-centroid and forward-relative changes are separate; neither proves a trade.
    """
    a, b = [], []
    for obj, target in ((before,a),(after,b)):
        target.extend([_fraction(obj['top_share'], positive=True), _fraction(obj['hhi'], positive=True),
                       _fraction(obj['event_expiry_share']),
                       _d(obj['centroid_strike'], positive=True), _d(obj['forward'],positive=True)])
        # For nonnegative normalized node weights: max(p)^2 <= sum(p^2) <= max(p).
        # Require unrounded owner statistics; rounded display fields are not inputs.
        if not target[0]**2 <= target[1] <= target[0]:
            raise ValueError('top share and HHI are internally inconsistent')
    empty = dict(state='NOT_COMPARABLE', top_share_change=None, hhi_change=None,
                 event_expiry_share_change=None, raw_centroid_change=None,
                 log_relative_change=None, position_growth_proven=False)
    if (not _required_match(before,after,('scope','support_ref','units','normalization'))
        or before.get('coverage_state')!='COMPLETE' or after.get('coverage_state')!='COMPLETE'):
        return empty
    return dict(state='COMPARABLE', top_share_change=b[0]-a[0], hhi_change=b[1]-a[1],
                event_expiry_share_change=b[2]-a[2], raw_centroid_change=b[3]-a[3],
                log_relative_change=log(float((b[3]/b[4])/(a[3]/a[4]))),
                position_growth_proven=False)


def skew_change(before: Mapping, after: Mapping) -> dict:
    """Changes in matched call/put wings; IV fractions, not percentages or odds.

    This is not options_skew.compute_skew or its exact 25P-50C definition.
    It consumes an explicitly qualified constant-tenor surface from that owner.
    """
    values=[]
    for obj in (before,after):
        put,call,atm=(_d(obj[k],positive=True) for k in ('put25_iv','call25_iv','atm_iv'))
        _d(obj['tenor_days'],positive=True)
        values.append((call-put,put-atm,call-atm))
    if _time(after['asof']) <= _time(before['asof']):
        raise ValueError('surface ordering invalid')
    keys=('delta_convention','exercise_model','tenor_convention','source_method','tenor_days')
    if not _required_match(before,after,keys):
        return dict(state='NOT_COMPARABLE', probability=None)
    a,b=values
    return dict(state='COMPARABLE',risk_reversal_before=a[0],risk_reversal_after=b[0],
                risk_reversal_change=b[0]-a[0],put_wing_change=b[1]-a[1],
                call_wing_change=b[2]-a[2],unit='decimal_IV',probability=None)


def conditional_update(base_probability: Any, steps: Sequence[Mapping], *, cutoff: str,
                       target: str, synthetic: bool) -> dict:
    """Illustrate a CONDITIONAL likelihood-ratio chain; never fit or publish it.

    Each included block must condition on all preceding included blocks. Within a
    block correlated features are modeled jointly. LR=1 carries no incremental
    evidence. These checks do not establish that supplied likelihoods are correct.
    A production estimator belongs to the existing Alpha/evaluation owner.
    """
    if synthetic is not True or not isinstance(target,str) or not target.strip():
        raise ValueError('explicit synthetic input and named target required')
    limit=_time(cutoff)
    p=_fraction(base_probability,positive=True)
    if p>=1:
        raise ValueError('nondegenerate baseline required')
    included=[];seen=set();trace=[];missing=[]
    with localcontext() as context:
        context.prec=40
        odds=p/(1-p)
        for item in steps:
            block=item.get('block')
            if not isinstance(block,str) or not block.strip() or block in seen:
                raise ValueError('duplicate or invalid evidence block')
            seen.add(block)
            if item.get('target',target)!=target:
                raise ValueError('target mismatch')
            if item.get('lr') is None:
                missing.append(block)
                continue
            if list(item.get('given',[]))!=included:
                raise ValueError('factor not conditional on included evidence')
            if _time(item['available_at'])>limit:
                raise ValueError('future evidence cannot enter forecast')
            lr=_d(item['lr'],positive=True)
            odds*=lr
            p=odds/(1+odds)
            included.append(block)
            trace.append(dict(block=block,conditional_likelihood_ratio=lr,probability=p))
        return dict(target=target,probability=p,trace=trace,unavailable_blocks=missing,
                    synthetic=True,empirically_qualified=False,recommendation_authority=False)


def first_passage(bars: Sequence[Mapping], *, cutoff: str, upper: Any, lower: Any) -> dict:
    """Freeze barriers before outcomes. OHLC cannot order two intrabar touches.

    Evaluation begins at the first supplied bar, not at an earlier decision cutoff.
    Gaps inside this continuous observation window withhold later first-touch labels.
    This labels observations, not fills/profits; the existing evaluator supplies
    corporate actions, complete path coverage, trading calendar, cost and fills.
    """
    top=_d(upper,positive=True);bottom=_d(lower,positive=True)
    if bottom>=top:
        raise ValueError('barriers must be ordered')
    last=_time(cutoff)
    prepared=[]
    for bar in bars:
        start,end=_time(bar['start']),_time(bar['end'])
        if start<last or end<=start:
            raise ValueError('pre-cutoff, overlapping or unordered bars')
        lo,hi,op,cl=(_d(bar[k],positive=True) for k in ('low','high','open','close'))
        if not lo<=min(op,cl)<=max(op,cl)<=hi:
            raise ValueError('invalid OHLC')
        prepared.append((bar['end'],lo,hi,bool(prepared) and start>last))
        last=end
    evaluated_from = bars[0]['start'] if bars else None
    for end,lo,hi,gap_before in prepared:
        if gap_before:
            return dict(outcome='PATH_COVERAGE_GAP',bar_end=end,fill_price=None,evaluated_from=evaluated_from)
        up,down=hi>=top,lo<=bottom
        if up or down:
            return dict(outcome='INTRABAR_ORDER_UNKNOWN' if up and down else 'UPPER_FIRST' if up else 'LOWER_FIRST',
                        bar_end=end,fill_price=None,evaluated_from=evaluated_from)
    return dict(outcome='NO_TOUCH_IN_OBSERVED_WINDOW' if bars else 'NO_OBSERVATIONS',bar_end=None,fill_price=None,evaluated_from=evaluated_from)
