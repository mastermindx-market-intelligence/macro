"""Ten frozen allocation rules with next-close target-notional cost accounting."""
import numpy as np
import pandas as pd

RULES={
 'R1':'Trend','R2':'Credit','R3':'Unemployment','R4':'Confluence',
 'R5':'Relative momentum','R6':'Confluence rotation','R7':'Breadth divergence',
 'R8':'Washout confirmation','R9':'Nominal-rate rotation','R10':'Real-rate plus credit'}

def states(data):
    p=data['price']; b=data['breadth']; m=data['macro'];idx=p.index
    ma200=p.rolling(200,min_periods=200).mean()
    ma50=p.rolling(50,min_periods=50).mean()
    trend=p.M.le(ma200.M).astype(float).where(ma200.M.notna())
    credit=m.credit;unemployment=m.unemployment
    conf=(trend+credit+unemployment).ge(2).astype(float).where(trend.notna()&credit.notna()&unemployment.notna())
    output={}
    def assign(off,onasset,offasset):
        return pd.Series(np.where(off.eq(1),offasset,onasset),index=idx,dtype=object).where(off.notna())
    for rid,off in [('R1',trend),('R2',credit),('R3',unemployment),('R4',conf)]:
        output[rid]=assign(off,'M','RF')
    rel=(p/p.shift(126)).where(p.notna().rolling(127,min_periods=127).sum().eq(127))
    off=rel.C.le(rel.D).astype(float).where(rel[['C','D']].notna().all(axis=1))
    output['R5']=assign(off,'C','D')
    cdvalid=data['targets']['C'].notna().all(axis=1)&data['targets']['D'].notna().all(axis=1)
    output['R6']=assign(conf.where(cdvalid),'C','D')
    ret63=(p.C/p.C.shift(63)-1).where(p.C.notna().rolling(64,min_periods=64).sum().eq(64))
    bmax=b.C200.rolling(63,min_periods=63).max()
    div=((ret63>0)&(b.C200<.5)&(bmax-b.C200>=.2))
    reopen=(b.C200>.6)&(p.C>ma200.C)
    valid=ret63.notna()&bmax.notna()&ma200.C.notna()&cdvalid
    arr=[];possible={'C'};started=False
    for ok,out,into in zip(valid,div,reopen):
        if not ok:
            if started:possible={'C','D'}
            arr.append(np.nan);continue
        started=True
        possible={('D' if state=='C' and out else ('C' if state=='D' and into else state)) for state in possible}
        arr.append(next(iter(possible)) if len(possible)==1 else np.nan)
    output['R7']=pd.Series(arr,index=idx,dtype=object)
    valid=ma200.C.notna()&ma50.C.notna()&b.C50.notna()&cdvalid
    arr=[];possible={('C',False)};started=False
    for date,ok in valid.items():
        if not ok:
            if started:possible={('C',False),('D',False),('D',True)}
            arr.append(np.nan);continue
        started=True;new=set()
        for current,washed in possible:
            if current=='C':
                if p.at[date,'C']<ma200.at[date,'C']:
                    current='D';washed=b.at[date,'C50']<=.2
            else:
                if b.at[date,'C50']<=.2:washed=True
                if washed and b.at[date,'C50']>.5 and p.at[date,'C']>ma50.at[date,'C']:
                    current='C';washed=False
            new.add((current,washed))
        possible=new;allocations={x[0] for x in possible}
        arr.append(next(iter(allocations)) if len(allocations)==1 else np.nan)
    output['R8']=pd.Series(arr,index=idx,dtype=object)
    output['R9']=assign(m.nominal_high.where(cdvalid),'C','D')
    off=(m.real_high.eq(1)&m.credit.eq(1)).astype(float).where(m.real_high.notna()&m.credit.notna()&cdvalid)
    output['R10']=assign(off,'C','D')
    return pd.DataFrame(output)

def target_weights(state,data):
    assets=data['assets'];t=pd.DataFrame(np.nan,index=assets.index,columns=assets.columns)
    for choice in ['M','RF','C','D','MIX']:
        mask=state.eq(choice)
        if not mask.any():continue
        t.loc[mask]=0.
        if choice in ['M','RF']:t.loc[mask,choice]=1.
        elif choice=='MIX':
            t.loc[mask,data['vw'].columns]=.5*(data['targets']['C'].loc[mask]+data['targets']['D'].loc[mask])
        else:t.loc[mask,data['vw'].columns]=data['targets'][choice].loc[mask]
    valid=t.notna().all(axis=1)
    assert np.allclose(t.loc[valid].sum(axis=1),1)
    return t

def causal_exposure_target(targets,always_equity=False):
    valid=targets.notna().all(axis=1)
    exposure=(1-targets.RF).where(valid)
    if always_equity and valid.any():
        # Even ambiguous C/D states have exactly 100% intended equity.
        exposure.loc[valid.idxmax():]=1.;valid=exposure.notna()
    q=exposure.expanding(min_periods=1).mean().where(valid)
    t=pd.DataFrame(0.,index=targets.index,columns=targets.columns)
    t['M']=q;t['RF']=1-q;t.loc[~valid]=np.nan
    return t

def simulate(targets,returns,cost_multiplier=1,allow_unknown=False):
    """Targets are decision-close weights. Trade only at the following close.

    Costs are a fraction of pretrade NAV; target weights apply to net postcost NAV.
    The exact multiplicative convention is fixed in the preregistration.
    """
    assert targets.index.equals(returns.index) and targets.columns.equals(returns.columns)
    arr=returns.to_numpy();orders=targets.shift(1).to_numpy()
    weights=np.zeros(arr.shape[1]);weights[-1]=1.
    n=len(arr);net=np.full(n,np.nan);turn=np.zeros(n);equity=np.zeros(n);grosses=np.zeros(n);costs=np.zeros(n)
    valid=~np.isnan(orders).any(axis=1)
    started=False
    for i,date in enumerate(returns.index):
        unknown=np.isnan(weights).any() or np.any(np.isnan(arr[i]) & (np.abs(weights)>1e-14))
        if unknown and not allow_unknown:raise ValueError(f'Missing held return at {date}')
        if unknown:
            gross=np.nan;pre=np.full(len(weights),np.nan)
        else:
            r=np.nan_to_num(arr[i],nan=0.) # only zero-weight missing positions
            gross=float(weights@r);pre=weights*(1+r)/(1+gross)
        equity[i]=1-weights[-1];grosses[i]=gross
        if valid[i]:
            new=orders[i]
            traded=np.abs(new[:-1]-pre[:-1]).sum()
            c=(.0025 if date<pd.Timestamp('1975-01-01') else .0005)*cost_multiplier
            cost=c*traded
            assert (np.isnan(cost) or 0<=cost<1) and np.all(new>=0) and abs(new.sum()-1)<1e-8
            weights=new.copy();started=True
            turn[i]=traded;costs[i]=cost
        else:
            if started:
                if not allow_unknown:raise ValueError(f'Unavailable target after inception: {date}')
                weights=np.full(len(weights),np.nan);cost=np.nan;turn[i]=np.nan;costs[i]=np.nan
            else:weights=pre;cost=0.
        if started:net[i]=(1+gross)*(1-cost)-1
    return pd.DataFrame({'return':net,'gross_return':grosses,'turnover':turn,'equity':equity,'cost':costs},index=returns.index)

def run_rules(data):
    choices=states(data);paths={};stress={};benchmarks={};targets={}
    for rid in RULES:
        t=target_weights(choices[rid],data);targets[rid]=t
        paths[rid]=simulate(t,data['assets'],allow_unknown=True)
        stress[rid]=simulate(t,data['assets'],2,allow_unknown=True)
        benchmarks[rid]=simulate(causal_exposure_target(t,always_equity=rid not in ['R1','R2','R3','R4']),data['assets'],allow_unknown=True)
    passive={}
    valid=data['targets']['C'].notna().all(axis=1)&data['targets']['D'].notna().all(axis=1)
    for choice in ['C','D','MIX']:
        s=pd.Series(choice,index=data['index']).where(valid)
        passive[choice]=simulate(target_weights(s,data),data['assets'],allow_unknown=True)
    return choices,paths,stress,benchmarks,passive,targets
