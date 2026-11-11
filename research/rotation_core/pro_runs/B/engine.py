"""Ten frozen allocation rules and a next-close self-financing simulator."""
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
    rel=p/p.shift(126)
    off=rel.C.le(rel.D).astype(float).where(rel[['C','D']].notna().all(axis=1))
    output['R5']=assign(off,'C','D')
    cdvalid=data['targets']['C'].notna().all(axis=1)&data['targets']['D'].notna().all(axis=1)
    output['R6']=assign(conf.where(cdvalid),'C','D')
    ret63=p.C/p.C.shift(63)-1
    bmax=b.C200.rolling(63,min_periods=63).max()
    div=((ret63>0)&(b.C200<.5)&(bmax-b.C200>=.2))
    reopen=(b.C200>.6)&(p.C>ma200.C)
    valid=ret63.notna()&bmax.notna()&ma200.C.notna()&cdvalid
    arr=[];current='C'
    for ok,out,into in zip(valid,div,reopen):
        if not ok:arr.append(np.nan);continue
        if current=='C' and out:current='D'
        elif current=='D' and into:current='C'
        arr.append(current)
    output['R7']=pd.Series(arr,index=idx,dtype=object)
    valid=ma200.C.notna()&ma50.C.notna()&b.C50.notna()&cdvalid
    arr=[];current='C';washed=False
    for date,ok in valid.items():
        if not ok:arr.append(np.nan);continue
        if current=='C':
            if p.at[date,'C']<ma200.at[date,'C']:
                current='D';washed=b.at[date,'C50']<=.2
        else:
            if b.at[date,'C50']<=.2:washed=True
            if washed and b.at[date,'C50']>.5 and p.at[date,'C']>ma50.at[date,'C']:
                current='C';washed=False
        arr.append(current)
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

def causal_exposure_target(targets):
    valid=targets.notna().all(axis=1)
    exposure=(1-targets.RF).where(valid)
    q=exposure.expanding(min_periods=1).mean().where(valid)
    t=pd.DataFrame(0.,index=targets.index,columns=targets.columns)
    t['M']=q;t['RF']=1-q;t.loc[~valid]=np.nan
    return t

def simulate(targets,returns,cost_multiplier=1):
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
        if np.any(np.isnan(arr[i]) & (np.abs(weights)>1e-14)):
            raise ValueError(f'Missing held return at {date}')
        r=np.nan_to_num(arr[i],nan=0.) # only zero-weight missing positions, checked above
        equity[i]=1-weights[-1]
        gross=float(weights@r);grosses[i]=gross
        pre=weights*(1+r)/(1+gross)
        if valid[i]:
            new=orders[i]
            traded=np.abs(new[:-1]-pre[:-1]).sum()
            c=(.0025 if date<pd.Timestamp('1975-01-01') else .0005)*cost_multiplier
            cost=c*traded
            assert 0<=cost<1 and np.all(new>=0) and abs(new.sum()-1)<1e-8
            weights=new.copy();started=True
            turn[i]=traded;costs[i]=cost
        else:
            if started:raise ValueError(f'Unavailable target after inception: {date}')
            weights=pre;cost=0.
        if started:net[i]=(1+gross)*(1-cost)-1
    return pd.DataFrame({'return':net,'gross_return':grosses,'turnover':turn,'equity':equity,'cost':costs},index=returns.index)

def run_rules(data):
    choices=states(data);paths={};stress={};benchmarks={};targets={}
    for rid in RULES:
        t=target_weights(choices[rid],data);targets[rid]=t
        paths[rid]=simulate(t,data['assets'])
        stress[rid]=simulate(t,data['assets'],2)
        benchmarks[rid]=simulate(causal_exposure_target(t),data['assets'])
    passive={}
    valid=data['targets']['C'].notna().all(axis=1)&data['targets']['D'].notna().all(axis=1)
    for choice in ['C','D','MIX']:
        s=pd.Series(choice,index=data['index']).where(valid)
        passive[choice]=simulate(target_weights(s,data),data['assets'])
    return choices,paths,stress,benchmarks,passive,targets
