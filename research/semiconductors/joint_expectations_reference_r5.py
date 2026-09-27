"""R5 pure research calculations and an R3-source comparison projection.

No I/O, network, production imports, model fitting, identity minting, financial
service or recommendation authority. Hypothetical mathematical inputs must not
be represented as learned parameters. Source projection is retrospective only.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps
from typing import Any, Mapping, Sequence

D=Decimal
ZERO, ONE = D(0), D(1)

def _precise(fn):
    @wraps(fn)
    def run(*args, **kwargs):
        with localcontext() as ctx:
            ctx.prec=40
            return fn(*args, **kwargs)
    return run

def _d(x: Any, *, nonnegative: bool=False) -> Decimal:
    if isinstance(x,bool) or x is None:
        raise ValueError('finite numeric value required; bool/null are not numbers')
    try: v=D(str(x))
    except (ValueError,InvalidOperation) as exc: raise ValueError('invalid decimal') from exc
    if not v.is_finite() or (nonnegative and v<0):
        raise ValueError('non-finite or negative value')
    return v

def _p(x: Any) -> Decimal:
    v=_d(x,nonnegative=True)
    if v>1:raise ValueError('probability exceeds one')
    return v

def _vec(x: Sequence[Any]) -> tuple[Decimal,...]:
    if isinstance(x,(str,bytes)) or not x:raise ValueError('nonempty numeric vector required')
    return tuple(_d(v) for v in x)

@_precise
def pricing_measure(probabilities, pricing_kernel):
    """Q_i = P_i m_i / E_P[m]; E_P[m] is the discount factor.

    Positive state prices do not identify P independently of the pricing kernel.
    This finite-state identity is not an options-market estimator.
    """
    p,m=_vec(probabilities),_vec(pricing_kernel)
    if len(p)!=len(m) or sum(p)!=1 or any(v<0 for v in p) or any(v<=0 for v in m):
        raise ValueError('invalid probability/kernel pair')
    z=sum(a*b for a,b in zip(p,m))
    return {'pricing_weights':tuple(a*b/z for a,b in zip(p,m)), 'discount_factor':z}

@_precise
def payoff_price(payoffs, probabilities, pricing_kernel):
    x=_vec(payoffs);measure=pricing_measure(probabilities,pricing_kernel)
    if len(x)!=len(measure['pricing_weights']):raise ValueError('payoff length mismatch')
    return measure['discount_factor']*sum(a*q for a,q in zip(x,measure['pricing_weights']))

@_precise
def dependence_envelope(p_a, p_b, equity_values, reference_price, dividend='0', cost_fraction='0'):
    """Frechet feasible joint range for two explicitly hypothetical binary events.

    Values follow (both, A-only, B-only, neither), not an inferred outcome order.
    Bounds are conditional on fixed marginals/values, not uncertainty intervals.
    """
    a,b=_p(p_a),_p(p_b);v=_vec(equity_values)
    price=_d(reference_price);div=_d(dividend,nonnegative=True);fee=_d(cost_fraction,nonnegative=True)
    if len(v)!=4 or any(x<0 for x in v) or price<=0:raise ValueError('invalid equity inputs')
    lo,hi=max(ZERO,a+b-1),min(a,b)
    def at(j):
        weights=(j,a-j,b-j,1-a-b+j)
        expected=sum(w*x for w,x in zip(weights,v))
        returns=tuple((x+div)/price-1-fee for x in v)
        return {'joint':j,'weights':weights,'expected_equity':expected,
                'net_return':(expected+div)/price-1-fee,
                'profit_probability':sum(w for w,ret in zip(weights,returns) if ret>0)}
    low,high=at(lo),at(hi)
    def extrema(key):return tuple(sorted((low[key],high[key])))
    return {'joint_range':(lo,hi),'interaction':v[0]-v[1]-v[2]+v[3],
            'lower_joint':low,'upper_joint':high,'independence':at(a*b),
            'expected_equity_range':extrema('expected_equity'),
            'net_return_range':extrema('net_return'),
            'profit_probability_range':extrema('profit_probability'),
            'is_probability_forecast':False}

@_precise
def event_variance_proxy(iv_before, t_before, iv_after, t_after, background_var_low, background_var_high, *, same_snapshot=True, event_bracketed=True, same_model=True, exercise_adjustment_qualified=True, event_count=1):
    """Conditional ATM total-variance proxy with an authored background bracket.

    Time units are years on the SAME convention; IV is decimal annual volatility.
    This is NOT model-free variance, a confidence interval, physical odds, or an
    American-option pricing engine. Its metadata booleans are caller assumptions,
    not this function's proof of market-source qualification.
    """
    s0,s1=_d(iv_before,nonnegative=True),_d(iv_after,nonnegative=True)
    t0,t1=_d(t_before),_d(t_after);b0,b1=_d(background_var_low,nonnegative=True),_d(background_var_high,nonnegative=True)
    if not ZERO<t0<t1 or b0>b1 or type(event_count) is not int or event_count<1:
        raise ValueError('invalid maturity/background/event count')
    flags=(same_snapshot,event_bracketed,same_model,exercise_adjustment_qualified)
    if any(type(v) is not bool for v in flags):raise ValueError('qualification flags must be booleans')
    base={'variance_range':None,'rms_proxy_range':None,'raw_residual_range':None,
          'physical_probability':None,'proxy_kind':'ATM_total_variance_residual'}
    if not all(flags):return {**base,'state':'unqualified_inputs'}
    delta=s1*s1*t1-s0*s0*t0
    raw=(delta-b1*(t1-t0),delta-b0*(t1-t0))
    if event_count!=1:return {**base,'state':'multiple_events_unidentified','basket_raw_residual_range':raw}
    if raw[1]<0:return {**base,'state':'inconsistent_proxy','raw_residual_range':raw}
    feasible=(max(ZERO,raw[0]),raw[1])
    return {**base,'state':'zero_included_conditional_proxy' if raw[0]<0 else 'conditional_proxy',
            'raw_residual_range':raw,'variance_range':feasible,
            'rms_proxy_range':tuple(v.sqrt() for v in feasible)}

@_precise
def linear_hedge_scenario(legs, spot_change, volatility_change, elapsed_days):
    """First-order change in delta-neutral stock hedge under FIXED assumed inventory.

    Gamma: option delta/$ underlying. Vanna: delta/1.00 decimal volatility.
    Charm: delta/elapsed calendar day (NOT remaining time to expiry).
    N signed contracts; multiplier deliverable shares/contract. All must already
    share compatible conventions. Large shocks require owner-native repricing.
    """
    if not legs:raise ValueError('empty inventory scenario')
    ds,dv,dt=_d(spot_change),_d(volatility_change),_d(elapsed_days,nonnegative=True)
    if any(leg.get('signed_contracts') is None for leg in legs):
        return {'state':'inventory_unknown','total_shares':None,'observed_dealer_flow':False}
    g=v=c=ZERO
    for leg in legs:
        if leg.get('inventory_basis')!='assumed_signed_position':raise ValueError('explicit assumed inventory required')
        n=_d(leg['signed_contracts']);m=_d(leg['multiplier'])
        if m<=0:raise ValueError('positive deliverable multiplier required')
        ga=_d(leg['gamma_delta_per_dollar'],nonnegative=True)
        va=_d(leg['vanna_delta_per_decimal_vol']);ch=_d(leg['charm_delta_per_elapsed_day'])
        g-=n*m*ga*ds;v-=n*m*va*dv;c-=n*m*ch*dt
    return {'state':'linear_scenario','gamma_shares':g,'vanna_shares':v,
            'charm_shares':c,'total_shares':g+v+c,'observed_dealer_flow':False}

def _clock(s):
    try:dt=datetime.fromisoformat(s.replace('Z','+00:00'))
    except (ValueError,TypeError,AttributeError) as exc:raise ValueError('invalid clock') from exc
    if dt.tzinfo is None or dt.utcoffset() is None:raise ValueError('timezone required')
    return dt

@_precise
def matched_loss_summary(rows):
    """Compare precomputed nonnegative losses on one common eligible population.

    This audits pairing only: no loss estimation, causal proof, calibration,
    bootstrap, power or significance is performed here. Lower loss is better.
    """
    if not rows:raise ValueError('empty population')
    ids=set();full=[];paired=[];excluded=Counter()
    for row in rows:
        oid=row.get('origin_id');cid=row.get('cluster_id');key=row.get('baseline_key')
        if not oid or oid in ids or not cid or not key:raise ValueError('unique origin and declared basis/cluster required')
        ids.add(oid);base=_d(row['baseline_loss'],nonnegative=True);full.append(base)
        cutoff=_clock(row['forecast_cutoff'])
        if row.get('augmented_loss') is None:excluded['missing_optional']+=1;continue
        if row.get('augmented_key')!=key:raise ValueError('paired score basis mismatch')
        aug=_d(row['augmented_loss'],nonnegative=True)
        known=row.get('optional_available_at')
        if known is None or _clock(known)>cutoff:
            excluded['optional_not_known_at_cutoff']+=1;continue
        paired.append((base,aug,cid))
    fullmean=sum(full)/len(full);n=len(paired)
    bmean=sum(x[0] for x in paired)/n if n else None
    amean=sum(x[1] for x in paired)/n if n else None
    return {'full_count':len(rows),'matched_count':n,'matched_cluster_count':len({x[2] for x in paired}),
            'coverage':D(n)/D(len(rows)),'full_baseline_mean':fullmean,
            'matched_baseline_mean':bmean,'matched_augmented_mean':amean,
            'paired_improvement':bmean-amean if n else None,
            'naive_unmatched_improvement':fullmean-amean if n else None,
            'exclusions':dict(sorted(excluded.items())),'statistical_significance':None}

@_precise
def project_research_casebook(casebook, selected_ids):
    """R3 diagnostic evidence -> faithful research rows, NEVER native investment cases.

    Input contract is the R3 ARCHIVE SPECIMEN, not a new production schema. It
    deliberately refuses a supposed upgraded/live case rather than silently
    discard its authority or source fields. Production uses incumbent readers.
    """
    if casebook.get('production_authority') is not False or casebook.get('forecasts_qualified') is not False or casebook.get('not_a_native_schema') is not True:
        raise ValueError('unqualified historical research specimen required')
    if casebook.get('research_mode')!='public_information_reconstruction':raise ValueError('unexpected research mode')
    if not selected_ids or len(set(selected_ids))!=len(selected_ids):raise ValueError('unique nonempty selection required')
    sources=casebook['sources'];source_index={s['id']:s for s in sources}
    cases=casebook['cases'];index={c['id']:c for c in cases};census=casebook['census']
    if len(source_index)!=len(sources) or len(index)!=len(cases):raise ValueError('duplicate source/case identity')
    if len(census)!=28 or len({c['origin'] for c in census})!=28:raise ValueError('R3 census must remain intact')
    out=[];refs=set()
    def relation(x,limits):
        low,mid,high=(_d(limits[k]) for k in ('low','mid','high'))
        if not low<=mid<=high:raise ValueError('inverted guidance')
        return 'below' if x<low else 'above' if x>high else 'inside'
    for cid in selected_ids:
        if cid not in index:raise ValueError('unknown case')
        case=index[cid];origin=case['origin'];guide=case['initial_guidance'];actual=case['outcome']
        if case.get('production_authority') is not False:raise ValueError('native authority not admitted')
        for field in ('reference_price','expected_return','recommendation','native_price_receipt','benchmark_receipt'):
            if case.get(field) is not None:raise ValueError('investment inputs do not belong in this source specimen')
        if not any(c['origin']==case['origin_census_slot'] and c['case_id']==cid for c in census):raise ValueError('case outside census')
        for f in ('period','scope','basis','unit'):
            if guide[f]!=actual[f]:raise ValueError('incomparable guidance/actual')
        for f in ('scope','basis','unit'):
            if origin[f]!=guide[f]:raise ValueError('origin scope mismatch')
        if guide['source_id']!=origin['source_id'] or guide['version']!='initial' or guide['analyst_consensus'] is not False:
            raise ValueError('initial management guidance required')
        all_records=[origin,guide,actual,*case['interim_updates']]
        if case.get('next_guidance') is not None:all_records.append(case['next_guidance'])
        for rec in all_records:
            ref=rec['source_id'];ident=rec['source_entity']
            if ref not in source_index:raise ValueError('source missing')
            if ident!=origin['source_entity'] or ident.get('canonical_security_id') is not None or ident.get('namespace')!='source_reported':raise ValueError('unverified native identity or source-identity mismatch')
            refs.add(ref)
        revenue=_d(actual['revenue_m']);gm=_d(actual['reported_gross_margin_fraction'])
        out.append({'research_case_id':cid,'origin_period':origin['period'],'target_period':actual['period'],
                    'basis':actual['basis'],'scope':actual['scope'],'unit':actual['unit'],
                    'original_source_id':guide['source_id'],'outcome_source_id':actual['source_id'],
                    'source_reported_entity':deepcopy(origin['source_entity']),
                    'revenue_error_m':revenue-_d(guide['revenue']['mid']),
                    'gross_margin_error_bp':(gm-_d(guide['gross_margin_fraction']['mid']))*10000,
                    'revenue_range_relation':relation(revenue,guide['revenue']),
                    'gross_margin_range_relation':relation(gm,guide['gross_margin_fraction']),
                    'interim_updates':deepcopy(case['interim_updates']),
                    'next_guidance':deepcopy(case.get('next_guidance')),
                    'prepared_interpretation':case['research_interpretation'],
                    'native_security_id':None,'native_financial_packet':None,'reference_price':None,
                    'expected_return':None,'investment_comparison_eligible':False})
    return {'artifact':'R5_research_comparison_projection','not_a_native_schema':True,
            'forecast_qualified':False,'production_authority':False,'rows':out,
            'sources':[deepcopy(source_index[s]) for s in sorted(refs)],'census':deepcopy(census),
            'limitations':['Selected diagnostic cases, not an outcome-blind cohort.',
                           'No owner-native identity, source-byte, financial, quote, policy or publication receipt.',
                           'Historical reported results are not a live forecast or a cross-sector investment score.']}
