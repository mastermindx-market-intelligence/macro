"""R5 controlled price-only timing diagnostic. No IO, source admission or orders.

CLI writes synthetic summary CSV to stdout. Published design fixes every grid cell.
The vectorized cost calculation implements the R2 equation, not a new cost convention.
"""
from __future__ import annotations
from dataclasses import dataclass
import csv
import math
import sys
import numpy as np

START, END, CHANGE = 252, 453, 313
REPS, SEED = 512, 20261017
WORLDS = ('no_edge', 'durable', 'gradual', 'headfake')


@dataclass(frozen=True)
class Policy:
    name: str
    lookback: int
    cadence: int
    confirmations: int


POLICIES = (Policy('slow_review',63,20,1),
            Policy('same_signal_fast_review',63,1,1),
            Policy('short_signal_fast_review',20,1,1),
            Policy('short_signal_confirmed',20,1,3))


def first_strict_source(lookback: int) -> int:
    if type(lookback) is not int or lookback <= 0:
        raise ValueError('positive interval count required')
    return lookback//2+1


def first_execution(lookback:int, delay:int, cadence:int, phase:int, confirmations:int)->int:
    if any(type(v) is not int for v in (delay,cadence,phase,confirmations)):
        raise ValueError('integer session coordinates required')
    if delay < 0 or cadence < 1 or not 0<=phase<cadence or confirmations<1:
        raise ValueError('invalid clock specification')
    ready=first_strict_source(lookback)+delay
    first=phase+max(0,math.ceil((ready-phase)/cadence))*cadence
    return first+(confirmations-1)*cadence+1


def switch_break_even(cost:float, relative_log_drift:float)->float:
    if not 0<=cost<1 or not math.isfinite(relative_log_drift) or relative_log_drift<=0:
        raise ValueError('valid costs and positive constant relative log drift required')
    return (math.log1p(cost)-math.log1p(-cost))/relative_log_drift


def rebalance_many(holdings:np.ndarray, weights:np.ndarray, cost:float)->dict:
    h=np.asarray(holdings,dtype=float);w=np.asarray(weights,dtype=float)
    if h.ndim!=2 or w.shape!=h.shape or h.shape[1]<2 or len(h)==0:
        raise ValueError('complete aligned portfolio matrices required')
    if isinstance(cost,bool) or not np.isfinite(cost) or not 0<=cost<=.01:
        raise ValueError('synthetic uniform cost must be in [0,.01]')
    if not np.isfinite(h).all() or not np.isfinite(w).all() or (h<0).any() or (w<0).any():
        raise ValueError('finite nonnegative holdings and weights required')
    W=h.sum(axis=1)
    if (W<=0).any() or not np.allclose(w.sum(axis=1),1.,rtol=0,atol=1e-12):
        raise ValueError('positive capital and complete target required')
    v=W.copy()
    # Contraction constant <=cost<=.01; twelve iterations plus a residual test.
    for _ in range(12):
        fees=cost*np.abs(w[:,1:]*v[:,None]-h[:,1:]).sum(axis=1)
        v=W-fees
    after=w*v[:,None]
    traded=np.abs(after[:,1:]-h[:,1:]).sum(axis=1)
    fees=cost*traded
    if not np.allclose(after.sum(axis=1)+fees,W,rtol=1e-12,atol=1e-13):
        raise AssertionError('self-financing residual')
    return {'wealth':v,'holdings':after,'fees':fees,'traded':traded}


def rolling_target(log_prices:np.ndarray, anchor:int, lookback:int, delay:int)->np.ndarray:
    if log_prices.ndim!=3 or log_prices.shape[2]!=13:
        raise ValueError('thirteen synthetic input paths required')
    if any(type(v) is not int for v in (anchor,lookback,delay)) or lookback<1 or delay<0:
        raise ValueError('invalid causal lookback')
    end=anchor-delay;begin=end-lookback
    if begin<0 or end>=log_prices.shape[1]:
        raise ValueError('incomplete source history')
    prefix=log_prices[:,begin:end+1,:]
    if not np.isfinite(prefix).all():raise ValueError('invalid source observations')
    ret=prefix[:,-1,:]-prefix[:,0,:]
    scores=ret[:,:11]-ret[:,12,None]
    order=np.argsort(-scores,axis=1,kind='stable')[:,:3]
    eligible=np.take_along_axis(ret[:,:11],order,axis=1)>ret[:,11,None]
    slots=np.where(eligible,order,11)
    counts=np.zeros((len(log_prices),12),dtype=int)
    np.add.at(counts,(np.repeat(np.arange(len(log_prices)),3),slots.ravel()),1)
    return counts


class Confirmation:
    """Fixture state only; no new product event or lifecycle owner."""
    def __init__(self,initial:np.ndarray,required:int,source_version:int):
        if type(required) is not int or required<1:raise ValueError('positive confirmation count')
        self.accepted=initial.copy();self.candidate=initial.copy()
        self.streak=np.ones(len(initial),dtype=int)
        self.required=required;self.version=source_version
    def observe(self,target:np.ndarray,source_version:int)->np.ndarray:
        if source_version<self.version:raise ValueError('source version regressed')
        if source_version==self.version:return self.accepted.copy()
        same=np.all(target==self.candidate,axis=1)
        self.streak=np.where(same,self.streak+1,1)
        self.candidate=target.copy();self.version=source_version
        use=self.streak>=self.required
        self.accepted[use]=target[use]
        return self.accepted.copy()


def simulate(log_prices:np.ndarray,policy:Policy,delay:int,cost:float,*,trace=False)->dict:
    """Prices only. No world/onset/latent drift enters an investment choice.

    CHANGE is used exclusively for an explicitly synthetic response diagnostic.
    At close e, accrue interval e to old holdings before filling origin e-1 order.
    """
    if log_prices.ndim!=3 or log_prices.shape[1]<=END or log_prices.shape[2]!=13:
        raise ValueError('complete declared synthetic date and input panel required')
    if not np.isfinite(log_prices).all():raise ValueError('nonfinite invented prices')
    if policy.lookback+delay>START or policy.cadence<1 or policy.confirmations<1:
        raise ValueError('invalid policy support')
    n=len(log_prices)
    gross=np.exp(np.diff(log_prices[:,:,:12],axis=1))
    if not np.isfinite(gross).all() or (gross<=0).any():raise ValueError('invalid return multipliers')
    h=np.zeros((n,13));h[:,0]=1
    initial=rolling_target(log_prices,START,policy.lookback,delay)
    st=Confirmation(initial,policy.confirmations,START-delay)
    accepted=initial.copy();turnover=np.zeros(n);fees=np.zeros(n)
    changes=np.zeros(n,dtype=int);peak=np.ones(n);drawdown=np.zeros(n);bill=np.zeros(n)
    first_new=np.full(n,np.nan);preposition=np.zeros(n,dtype=bool)
    wp=[];targets=[]
    for e in range(START+1,END+1):
        h[:,1:]*=gross[:,e-1,:] # old holdings, including bill fund
        old=accepted.copy();changed=np.zeros(n,dtype=bool)
        if e==START+1:
            act=np.ones(n,dtype=bool)
        elif e<END:
            origin=e-1
            if (origin-START)%policy.cadence==0:
                proposed=rolling_target(log_prices,origin,policy.lookback,delay)
                accepted=st.observe(proposed,origin-delay)
                changed=np.any(accepted!=old,axis=1)
                changes+=changed
            act=changed | ((e-(START+1))%20==0)
        else:
            act=np.zeros(n,dtype=bool)
        if np.any(act):
            w=np.column_stack((np.zeros(act.sum()),accepted[act]/3.))
            r=rebalance_many(h[act],w,cost)
            h[act]=r['holdings'];turnover[act]+=r['traded'];fees[act]+=r['fees']
        if e==END:
            w=np.zeros_like(h);w[:,0]=1
            r=rebalance_many(h,w,cost)
            h=r['holdings'];turnover+=r['traded'];fees+=r['fees']
        wealth=h.sum(axis=1);peak=np.maximum(peak,wealth)
        drawdown=np.maximum(drawdown,1-wealth/peak)
        if e<END:bill+=h[:,-1]/wealth/(END-(START+1))
        new_mass=accepted[:,3:6].sum(axis=1)>=2
        if e==CHANGE-1:preposition=new_mass.copy()
        if CHANGE<=e<END:
            hit=np.isnan(first_new)&new_mass
            first_new[hit]=e-CHANGE
        if trace:wp.append(wealth.copy());targets.append(accepted.copy())
    out={'terminal':wealth,'log_terminal':np.log(wealth),'turnover':turnover,
         'fees':fees,'max_drawdown':drawdown,'membership_changes':changes,
         'bill_occupancy':bill,'new_group_delay':first_new,'prepositioned':preposition,
         'synthetic':True,'investment_authority':False}
    if trace:out.update(wealth_path=np.stack(wp,axis=1),targets=np.stack(targets,axis=1))
    return out


def synthetic_worlds(reps:int=REPS)->dict[str,np.ndarray]:
    """Common shocks across worlds; independent Monte Carlo replications."""
    rng=np.random.default_rng(SEED)
    t=END;n=reps
    common=np.empty((n,t));common[:,0]=rng.normal(0,.006,n)
    for j in range(1,t):
        common[:,j]=.15*common[:,j-1]+rng.normal(0,.006*math.sqrt(1-.15**2),n)
    idio=rng.normal(0,.008,(n,t,11))
    shock=common[:,:,None]+idio
    old=np.zeros(11);old[:3]=.0012;old[3:6]=-.0006
    new=np.zeros(11);new[:3]=-.0006;new[3:6]=.0012
    date=np.arange(1,END+1)
    result={}
    for world in WORLDS:
        if world=='no_edge':drift=np.zeros((t,11))
        else:
            if world=='durable':a=(date>=CHANGE).astype(float)
            elif world=='gradual':a=np.clip((date-CHANGE+1)/40,0,1)
            else:a=((date>=CHANGE)&(date<CHANGE+12)).astype(float)
            drift=(1-a[:,None])*old+a[:,None]*new
        sector=.0001+drift[None,:,:]+shock
        lr=np.empty((n,t,13));lr[:,:,:11]=sector;lr[:,:,11]=.00008
        lr[:,:,12]=np.log(np.mean(np.exp(sector),axis=2))
        result[world]=np.concatenate((np.zeros((n,1,13)),np.cumsum(lr,axis=1)),axis=1)
    return result


def grid(reps:int=REPS)->list[dict]:
    rows=[]
    for world,x in synthetic_worlds(reps).items():
        for lag in (0,5):
            for cost in (.0005,.0025):
                baseline=None
                for p in POLICIES:
                    r=simulate(x,p,lag,cost)
                    if baseline is None:baseline=r['log_terminal'].copy()
                    delta=r['log_terminal']-baseline
                    delay=r['new_group_delay'];valid=np.isfinite(delay)
                    response=world in ('durable','gradual')
                    rows.append(dict(world=world,source_lag=lag,cost=cost,policy=p.name,
                        replications=reps,mean_net_wealth=float(np.mean(r['terminal'])),
                        mean_log_wealth=float(np.mean(r['log_terminal'])),
                        paired_log_delta=float(delta.mean()),paired_mc_se=float(delta.std(ddof=1)/math.sqrt(reps)),
                        mean_drawdown=float(r['max_drawdown'].mean()),mean_turnover=float(r['turnover'].mean()),
                        mean_membership_changes=float(r['membership_changes'].mean()),mean_bill_occupancy=float(r['bill_occupancy'].mean()),
                        mean_response_delay=float(delay[valid].mean()) if response and valid.any() else '',
                        nonarrival_fraction=float(1-valid.mean()) if response else '',
                        prepositioned_fraction=float(r['prepositioned'].mean()) if response else ''))
    return rows


def main():
    rows=grid()
    writer=csv.DictWriter(sys.stdout,fieldnames=list(rows[0]));writer.writeheader()
    for r in rows:
        writer.writerow({k:format(v,'.9f') if isinstance(v,float) else v for k,v in r.items()})

if __name__=='__main__':main()
