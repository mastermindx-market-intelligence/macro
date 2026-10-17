"""Research-only proportional-cost accounting witness, not a trading engine.
No network, price data, product imports, order execution or runtime state.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
from pathlib import Path
import random


def rebalance(holdings: list[float], weights: list[float], costs: list[float]) -> dict:
    if not holdings or len(holdings) != len(weights) or len(weights) != len(costs):
        raise ValueError('complete aligned vectors required')
    for x in holdings + weights + costs:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError('finite numeric inputs required')
    wealth = sum(holdings)
    if wealth <= 0 or min(holdings) < 0 or min(weights) < 0:
        raise ValueError('positive wealth and nonnegative holdings/weights required')
    if not math.isclose(sum(weights), 1.0, abs_tol=1e-12, rel_tol=0):
        raise ValueError('complete target weights must sum to one')
    if min(costs) < 0 or max(costs) >= 1:
        raise ValueError('cost rates must lie in [0,1)')
    def fees(v: float) -> float:
        return sum(c * abs(w*v-h) for h,w,c in zip(holdings,weights,costs))
    lo, hi = 0.0, wealth
    for _ in range(90):
        v = (lo+hi)/2
        if v+fees(v) > wealth: hi = v
        else: lo = v
    v = (lo+hi)/2
    after = [w*v for w in weights]
    charged = fees(v)
    residual = wealth-sum(after)-charged
    if abs(residual) > 1e-10*wealth:
        raise AssertionError('self-financing residual')
    return {'post_wealth':v, 'holdings':after, 'fees':charged,
            'gross_traded_notional':sum(abs(a-h) for a,h in zip(after,holdings)),
            'budget_residual':residual}


def algebraic_solution(h: list[float], w: list[float], c: list[float]) -> float:
    """Independent finite sign-region enumeration, used only for test fixtures."""
    W=sum(h)
    candidates=[]
    for signs in itertools.product((-1,1),repeat=len(h)):
        v=(W+sum(ci*si*hi for ci,si,hi in zip(c,signs,h)))/(1+sum(ci*si*wi for ci,si,wi in zip(c,signs,w)))
        if 0 <= v <= W+1e-12*W and all(si*(wi*v-hi)>=-1e-12*W for si,wi,hi in zip(signs,w,h)):
            candidates.append(v)
    if not candidates or max(candidates)-min(candidates)>1e-10*W:
        raise AssertionError('algebraic solution not uniquely reconciled')
    return sum(candidates)/len(candidates)


def run() -> dict:
    c=0.001
    cases=[]
    def case(name,h,w,fees,expected):
        r=rebalance(h,w,fees)
        assert math.isclose(r['post_wealth'],expected,rel_tol=1e-11,abs_tol=1e-12), name
        cases.append({'name':name,'expected_wealth':expected,'result':r})
    # Coordinate zero is uninvested settlement cash with zero trade fee.
    case('cash_to_fund',[1.,0.,0.],[0.,1.,0.],[0.,c,c],1/(1+c))
    case('fund_A_to_fund_B',[0.,1.,0.],[0.,0.,1.],[0.,c,c],(1-c)/(1+c))
    case('no_trade_at_drifted_weights',[0.,.6,.4],[0.,.6,.4],[0.,c,c],1.)
    case('rebalance_drifted_weights',[0.,.6,.4],[0.,.5,.5],[0.,c,c],1-.2*c)
    case('liquidate_to_settlement_cash',[0.,1.,0.],[1.,0.,0.],[0.,c,c],1-c)
    first=rebalance([1.,0.,0.],[0.,1.,0.],[0.,c,c])
    case('flat_price_round_trip',first['holdings'],[1.,0.,0.],[0.,c,c],(1-c)/(1+c))
    case('zero_cost_switch',[0.,1.,0.],[0.,0.,1.],[0.,0.,0.],1.)
    rng=random.Random(20261017)
    errors=[]
    for _ in range(512):
        h=[rng.random()+.01 for _ in range(3)]
        w=[rng.random() for _ in range(3)];w=[x/sum(w) for x in w]
        costs=[0.,rng.uniform(0,.02),rng.uniform(0,.02)]
        a=rebalance(h,w,costs)['post_wealth'];b=algebraic_solution(h,w,costs)
        errors.append(abs(a-b)/sum(h))
    assert max(errors)<1e-11
    for _ in range(128):
        h=[rng.random()+.01 for _ in range(3)];w=[rng.random() for _ in range(3)];w=[x/sum(w) for x in w]
        values=[rebalance(h,w,[0.,rate,rate])['post_wealth'] for rate in [.0005,.001,.0025,.005]]
        assert all(a>=b-1e-12 for a,b in zip(values,values[1:]))
    invalid=[([-1.,2.],[0.,1.],[0.,c]),([1.,0.],[.4,.5],[0.,c]),([1.,0.],[0.,1.],[0.,-c]),
             ([1.,0.],[0.,1.],[0.,1.]),([1.,0.],[False,1.],[0.,c]),([1.,0.],[math.nan,1.],[0.,c]),([0.,0.],[0.,1.],[0.,c])]
    for args in invalid:
        try: rebalance(*args)
        except ValueError: pass
        else: raise AssertionError('invalid fixture accepted')
    return {'scope':'synthetic_accounting_design_only','network_calls':0,'market_data_read':False,
        'native_evaluator_qualification':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'deterministic_cases':cases,'algebraic_crosschecks':512,'maximum_relative_algebraic_error':max(errors),
        'cost_monotonicity_checks':128,'invalid_inputs_rejected':len(invalid),
        'costs_are_synthetic_assumptions':True,'cash_is_uninvested_settlement_cash_not_BIL':True}

if __name__=='__main__':
    print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
