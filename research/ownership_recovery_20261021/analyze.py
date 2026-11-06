"""Registered mechanism audit and capital accounting. No parameter selection."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_inputs import CORE, PEERS, SECTORS, sha
from vendor_v11_native import NativeState, snapshots, episodes

SEED = 20261021

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, default=str, allow_nan=False))

def clean(obj):
    if isinstance(obj, dict): return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj, list): return [clean(v) for v in obj]
    if isinstance(obj, (float,np.floating)) and not np.isfinite(obj): return None
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.bool_,)): return bool(obj)
    return obj

def rma(x, n=14):
    x=np.asarray(x,float); out=np.full(len(x),np.nan)
    start=np.flatnonzero(np.isfinite(x))
    if not len(start) or start[0]+n>len(x): return out
    i=int(start[0])+n-1
    if not np.isfinite(x[i-n+1:i+1]).all(): raise ValueError('Noncontiguous RMA seed')
    out[i]=np.mean(x[i-n+1:i+1])
    for j in range(i+1,len(x)): out[j]=((n-1)*out[j-1]+x[j])/n
    return out

def atr14(d):
    c=d.close.shift()
    tr=pd.concat([d.high-d.low,(d.high-c).abs(),(d.low-c).abs()],axis=1).max(axis=1)
    return rma(tr)

def load_data(manifest):
    m=json.loads(manifest.read_text()); raw={}; adj={}
    for r in m['assets']:
        p=Path(r['path']); assert sha(p)==r['parquet_sha256']
        d=pd.read_parquet(p).sort_index().loc['2010-01-04':'2026-10-08'].copy()
        assert d.index.is_unique and d.index.is_monotonic_increasing
        f=d.adjclose/d.close
        assert np.isfinite(f).all() and (f>0).all()
        raw[r['ticker']]=d
        a=d.copy(); a[['open','high','low','close']]=d[['open','high','low','close']].mul(f,axis=0)
        adj[r['ticker']]=a
    ix=raw['SPY'].index
    for s in CORE+PEERS: assert raw[s].index.equals(ix),s
    return m,raw,adj,ix

def defensive_features(d, calendar):
    daily=snapshots(d.close,calendar,'1D')
    w=snapshots(d.close,calendar,'1W'); b=snapshots(d.close,calendar,'2W')
    known=(w['count']>=200)&(b['count']>=200)&w.k.notna()&b.k.notna()&w.recent3.notna()&b.recent2.notna()
    wc=w.recent3.le(20); bc=b.recent2.le(20)&b.k.lt(60)
    state=np.where(~known,'UNKNOWN',np.where(wc&bc,'JOINT',np.where(wc,'WEEKLY_ONLY',np.where(bc,'TWO_WEEK_ONLY','NEITHER'))))
    f=pd.DataFrame({'date':d.index,'t':np.arange(len(d)),'cell':state,'bull':daily.bull.to_numpy(bool),
                    'atr':atr14(d),'own_above200':(d.close>d.close.rolling(200).mean()).to_numpy(),
                    'weekly_k':w.k.to_numpy(),'two_week_k':b.k.to_numpy()},index=d.index)
    f['sequence']='NO_ACTIVE_WATCH';f['watch_arm_t']=np.nan;f['watch_id']=np.nan
    start=int(d.index.searchsorted(pd.Timestamp('2018-01-01')))
    eps=episodes(state=='JOINT',b.k.to_numpy(),daily.bull.to_numpy(bool),start_i=start)
    for ep in eps:
        a,z=ep['arm_i'],ep['end_i']; hits=np.flatnonzero(daily.bull.to_numpy()[a:z])+a
        f.iloc[a:z,f.columns.get_loc('watch_arm_t')]=a
        f.iloc[a:z,f.columns.get_loc('watch_id')]=ep['episode']
        for k,i in enumerate(hits): f.iloc[i,f.columns.get_loc('sequence')]='FIRST' if k==0 else 'REPEAT'
    return f,eps

def outcomes(raw, adj, h, fee, stop_basis='adjusted'):
    """All complete t+1-open to t+h-close outcomes, including entry-day stops."""
    d=adj if stop_basis=='adjusted' else raw
    n=len(d);k=n-h;ix=np.arange(k);entry=adj.open.to_numpy()[ix+1]
    atr=atr14(d); o=d.open.to_numpy(); lo=d.low.to_numpy(); c=d.close.to_numpy()
    stop=o[ix+1]-3*atr[:k]; valid=np.isfinite(stop)&(stop>0)
    windows=np.lib.stride_tricks.sliding_window_view(lo[1:],h)
    hit=(windows<=stop[:,None])&valid[:,None]; stopped=hit.any(axis=1)
    j=ix+1+hit.argmax(axis=1); exit_t=np.where(stopped,j,ix+h)
    fill=np.where(stopped,np.minimum(o[j],stop),c[ix+h])
    factor=(adj.close/raw.close).to_numpy() if stop_basis=='raw' else np.ones(n)
    ratio=adj.close.to_numpy()[ix+h]/entry
    stop_ratio=fill*factor[exit_t]/entry
    lows=adj.low.to_numpy(); awin=np.lib.stride_tricks.sliding_window_view(lows[1:],h)
    ref=pd.Series(d.low).rolling(63).min().to_numpy()[:k]
    # Most recent tied low, using only the 63 sessions through signal close.
    age=np.full(k,np.nan)
    for t in range(62,k): age[t]=62-np.flatnonzero(lo[t-62:t+1]==ref[t])[-1]
    intact=np.zeros(k,bool);both=np.zeros(k,bool);undercut=np.zeros(k,bool)
    for t in np.flatnonzero(stopped):
        intact[t]=bool(lo[t+1:j[t]+1].min()>ref[t])
        undercut[t]=bool(lo[t+1:j[t]+1].min()<ref[t])
        both[t]=bool(lo[j[t]]<=ref[t] and (j[t]==t+1 or lo[t+1:j[t]].min()>ref[t]))
    out=pd.DataFrame({'date':d.index[:k],'t':ix,'entry_date':d.index[ix+1],'exit_date':d.index[ix+h],
        'net':ratio*(1-fee)/(1+fee)-1,'net50':ratio*(1-.0025)/(1+.0025)-1,
        'price_net':raw.close.to_numpy()[ix+h]/raw.open.to_numpy()[ix+1]*(1-fee)/(1+fee)-1,
        'stop_net':np.where(valid,stop_ratio*(1-fee)/(1+fee)-1,np.nan),'stop_hit':stopped,
        'stop_t':np.where(stopped,j,-1),'mae':np.minimum(awin.min(axis=1)/entry-1,0),
        'reference_low':ref,'reference_age':age,'entry_distance_atr':(o[ix+1]-ref)/atr[:k],
        'stop_above_reference':stop>ref,'reference_intact_at_stop':intact,
        'reference_undercut_at_stop':undercut,
        'both_levels_touched_on_stop_day':both,'reference_break_horizon':windows.min(axis=1)<ref,
        'reference_touch_horizon':windows.min(axis=1)<=ref,
        'tolerant_reference_break_horizon':windows.min(axis=1)<ref-.25*atr[:k],
        'horizon':h,
        'stop_price':stop,'entry_price':o[ix+1],'atr':atr[:k]},index=d.index[:k])
    out['winner_stopped_reference_untouched']=(out.net>0)&(out.stop_net<=0)&out.reference_intact_at_stop
    return out

def block_weights(start,end,B=2000):
    grid=np.arange(start.year*2+int(start.month>6),end.year*2+int(end.month>6)+1)
    rng=np.random.default_rng(SEED);n=len(grid)
    starts=rng.integers(0,n,size=(B,(n+1)//2));pick=np.stack([starts,(starts+1)%n],axis=2).reshape(B,-1)[:,:n]
    weights=np.zeros((B,n),int)
    for i in range(B): weights[i]=np.bincount(pick[i],minlength=n)
    return grid,weights

def boot_mean(g,col,grid,weights):
    a=g[['halfyear',col]].dropna();z=a.groupby('halfyear')[col].agg(['sum','count']).reindex(grid,fill_value=0)
    denom=weights@z['count'].to_numpy();num=weights@z['sum'].to_numpy()
    vals=np.divide(num,denom,out=np.full(len(denom),np.nan),where=denom>0)
    good=vals[np.isfinite(vals)]
    support=int((z['count']>0).sum());valid=len(good)/len(vals)
    eligible=support>=4 and valid>=.95
    ci=np.quantile(good,[.025,.975]) if eligible else [np.nan,np.nan]
    return vals,float(ci[0]),float(ci[1]),valid,support,eligible

def boot_contrast(a,b,col,grid,weights):
    av,_,_,_,sa,ea=boot_mean(a,col,grid,weights)
    bv,_,_,_,sb,eb=boot_mean(b,col,grid,weights)
    diff=av-bv;good=diff[np.isfinite(diff)];valid=len(good)/len(diff)
    eligible=ea and eb and valid>=.95
    ci=np.quantile(good,[.025,.975]) if eligible else [np.nan,np.nan]
    return {'point':float(a[col].mean()-b[col].mean()),'lo':float(ci[0]),'hi':float(ci[1]),
            'arm_a_populated_halfyears':sa,'arm_b_populated_halfyears':sb,
            'joint_valid_draw_fraction':valid,'interval_available':eligible}

def summarize(g,grid=None,weights=None):
    if not len(g): return {'n':0}
    converted=(g.net>0)&(g.stop_net<=0)
    x={'n':len(g),'assets':g.symbol.nunique(),'dates':g.date.nunique(),'halfyears':g.halfyear.nunique(),
       'positive':float((g.net>0).mean()),'mean':float(g.net.mean()),'median':float(g.net.median()),
       'p05':float(g.net.quantile(.05)),'worst':float(g.net.min()),'mae_mean':float(g.mae.mean()),
       'mae_worst':float(g.mae.min()),'stop_positive':float((g.stop_net>0).mean()),
       'stop_mean':float(g.stop_net.mean()),'stop_hit':float(g.stop_hit.mean()),
       'positive_to_stopped_loss':float(converted.mean()),'positive_to_stopped_loss_n':int(converted.sum()),
       'winner_stopped_reference_untouched_n':int(g.winner_stopped_reference_untouched.sum()),
       'winner_stopped_reference_untouched':float(g.winner_stopped_reference_untouched.mean()),
       'reference_untouched_given_converted_winner':float(g.loc[converted,'reference_intact_at_stop'].mean()),
       'stop_above_reference':float(g.stop_above_reference.mean()),
       'intact_reference_stops_all':float(g.reference_intact_at_stop.mean()),
       'intact_reference_given_stop':float(g.loc[g.stop_hit,'reference_intact_at_stop'].mean()),
       'undercut_reference_given_stop':float(g.loc[g.stop_hit,'reference_undercut_at_stop'].mean()),
       'reference_touch':float(g.reference_touch_horizon.mean()),
       'reference_break':float(g.reference_break_horizon.mean()),
       'tolerant_reference_break':float(g.tolerant_reference_break_horizon.mean()),
       'mean_distance_atr':float(g.entry_distance_atr.mean()),
       'price_positive':float((g.price_net>0).mean()),'price_mean':float(g.price_net.mean()),
       'positive_cost50':float((g.net50>0).mean()),'mean_cost50':float(g.net50.mean()),
       'equal_date_mean':float(g.groupby('date').net.mean().mean()),
       'equal_date_positive':float(g.assign(win=(g.net>0).astype(float)).groupby('date').win.mean().mean())}
    for c in ['ordinary_net','core_peer_net','broad_peer_net','spy_net']:
        if c not in g:continue
        z=g[g[c].notna()];x[c+'_n']=len(z);x[c+'_coverage']=len(z)/len(g)
        x[c+'_mean']=float(z[c].mean());x[c+'_delta']=float((z.net-z[c]).mean());x[c+'_excess_positive']=float((z.net>z[c]).mean())
        if grid is not None:
            gg=z.assign(delta=z.net-z[c]);_,lo,hi,valid,support,eligible=boot_mean(gg,'delta',grid,weights)
            x[c+'_delta_lo']=lo;x[c+'_delta_hi']=hi;x[c+'_bootstrap_valid']=valid
            x[c+'_populated_halfyears']=support;x[c+'_interval_available']=eligible
    if 'ordinary_win' in g: x['ordinary_positive']=float(g.ordinary_win.mean())
    if 'ordinary_stopwin' in g:x['ordinary_stop_positive']=float(g.ordinary_stopwin.mean())
    if 'ordinary_conversion' in g:x['ordinary_positive_to_stopped_loss']=float(g.ordinary_conversion.mean())
    if 'ordinary_intact' in g:x['ordinary_intact_stops_all']=float(g.ordinary_intact.mean())
    if 'ordinary_winnerintact' in g:x['ordinary_winner_stopped_reference_untouched']=float(g.ordinary_winnerintact.mean())
    if 'ordinary_refbreak' in g:x['ordinary_reference_break']=float(g.ordinary_refbreak.mean())
    if 'ordinary_stopabove' in g:x['ordinary_stop_above_reference']=float(g.ordinary_stopabove.mean())
    return x

def ordinary_matches(panel,events,start,end):
    p=panel[(panel.date>=start)&(panel.exit_date<=end)].copy()
    p['win']=(p.net>0).astype(float);p['stopwin']=(p.stop_net>0).astype(float)
    p['conversion']=((p.net>0)&(p.stop_net<=0)).astype(float)
    p['intact']=p.reference_intact_at_stop.astype(float)
    p['winnerintact']=p.winner_stopped_reference_untouched.astype(float)
    p['refbreak']=p.reference_break_horizon.astype(float);p['stopabove']=p.stop_above_reference.astype(float)
    cols=['net','win','stopwin','conversion','intact','winnerintact','refbreak','stopabove'];keys=['symbol','halfyear','own_above200','market_above200']
    ag=p.groupby(keys)[cols].agg(['sum','count'])
    e=events[(events.date>=start)&(events.exit_date<=end)].copy()
    lookup=p.set_index(['symbol','date'])
    for c in cols:e['ordinary_'+c]=np.nan
    e['ordinary_n']=0
    for j,r in e.iterrows():
        key=tuple(r[k] for k in keys)
        if key not in ag.index:continue
        cell=ag.loc[key];n=int(cell[('net','count')])-1
        if n<10:continue
        focal=lookup.loc[(r.symbol,r.date)]
        for c in cols:e.loc[j,'ordinary_'+c]=(cell[(c,'sum')]-focal[c])/n
        e.loc[j,'ordinary_n']=n
    return e

def accepted_roster(signals,h,n):
    roster=[];skipped=[];free=-1
    for i in sorted(set(int(t) for t in signals)):
        if i+1>=n:skipped.append((i,'NO_NEXT_OPEN'));continue
        if i<free:skipped.append((i,'CAPITAL_OCCUPIED'));continue
        roster.append({'signal_t':i,'entry_t':i+1,'scheduled_exit_t':i+h});free=i+h
    return roster,skipped

def sleeve(prices,raw,nominee,roster,start,fee,cash_yield=0.,stop=False,basket=None,stop_basis='adjusted'):
    """One unlevered cash/position sleeve; entries already reserve their full interval."""
    ix=prices[nominee].index;n=len(ix);basis=prices[nominee] if stop_basis=='adjusted' else raw[nominee]
    atr=atr14(basis);look={r['entry_t']:r for r in roster}
    if len(look)!=len(roster):raise ValueError('Duplicate entry')
    cash=1.;units={};active=None;rows=[];trades=[];equity=[];held=[];turn=[]
    for t in range(start,n):
        if t>start:cash*=((1+cash_yield)**(1/252))
        turnover=0.
        if t in look:
            assert not units
            active=dict(look[t]);active['capital_before_entry']=cash;active['stop_hit']=False
            names=basket or [nominee];investment=cash/(1+fee)
            for s in names:
                op=float(prices[s].open.iloc[t]);assert np.isfinite(op) and op>0
                units[s]=investment/len(names)/op
            turnover+=investment;cash=0.
            active['stop_price']=float(basis.open.iloc[t]-3*atr[active['signal_t']]) if stop else np.nan
            assert not stop or (np.isfinite(active['stop_price']) and active['stop_price']>0)
        stopped=False
        if units and stop and float(basis.low.iloc[t])<=active['stop_price']:
            assert len(units)==1 and nominee in units
            fill=min(float(basis.open.iloc[t]),active['stop_price'])
            if stop_basis=='raw':fill*=float(prices[nominee].close.iloc[t]/raw[nominee].close.iloc[t])
            proceeds=units[nominee]*fill;turnover+=proceeds;cash+=proceeds*(1-fee);units={};stopped=True
        scheduled=bool(units and t==active['scheduled_exit_t'])
        if scheduled:
            proceeds=sum(q*float(prices[s].close.iloc[t]) for s,q in units.items())
            turnover+=proceeds;cash+=proceeds*(1-fee);units={}
        if stopped or scheduled:
            tr={**active,'nominee':nominee,'exit_t':t,'stop_hit':stopped,'closed':True,
                'trade_net':cash/active['capital_before_entry']-1,'exit_reason':'STOP' if stopped else 'TIME'}
            trades.append(tr);active=None
        gross=sum(q*float(prices[s].close.iloc[t]) for s,q in units.items())
        equity.append(cash+gross*(1-fee));held.append(gross);turn.append(turnover)
        assert cash>=-1e-12 and np.isfinite(equity[-1]) and equity[-1]>0
    if units:
        trades.append({**active,'nominee':nominee,'exit_t':n-1,'closed':False,'stop_hit':False,
                       'trade_net':equity[-1]/active['capital_before_entry']-1,'exit_reason':'MARKED_OPEN'})
    return np.array(equity),np.array(held),np.array(turn),trades

def account_stats(nav,held,turn,ix,trades,fee):
    returns=np.diff(np.r_[1.,nav])/np.r_[1.,nav[:-1]]
    peaks=np.maximum.accumulate(np.r_[1.,nav])[1:];dd=nav/peaks-1
    run=longest=0
    for u in dd< -1e-12:run=run+1 if u else 0;longest=max(longest,run)
    ts=pd.DataFrame(trades);closed=ts[ts.closed.astype(bool)] if len(ts) else ts
    z={'terminal_wealth':float(nav[-1]),'cagr':float(nav[-1]**(252/len(nav))-1),'max_drawdown':float(dd.min()),
       'annual_volatility':float(np.std(returns,ddof=1)*np.sqrt(252)),
       'invested_fraction':float(np.mean(np.divide(held,nav+fee*held,out=np.zeros(len(nav)),where=nav>0))),
       'max_underwater_sessions':int(longest),'underwater_fraction':float(np.mean(dd<-1e-12)),
       'gross_turnover_initial_capital':float(turn.sum()),'entries':len(ts),'closed_trades':len(closed),
       'open_trades':len(ts)-len(closed),'closed_trade_positive':float((closed.trade_net>0).mean()) if len(closed) else np.nan,
       'worst_closed_trade':float(closed.trade_net.min()) if len(closed) else np.nan}
    annual=[];prev=1.
    for y in sorted(set(ix.year)):
        end=float(nav[np.flatnonzero(ix.year==y)[-1]]);annual.append({'year':int(y),'return':end/prev-1});prev=end
    return z,annual

def run_portfolio(prices,raw,rosters,nominees,start,fee,cash_yield,stop=False,basket=None,stop_basis='adjusted'):
    values=[];held=[];turn=[];trades=[]
    for s in nominees:
        v,h,u,t=sleeve(prices,raw,s,rosters[s],start,fee,cash_yield,stop,basket,stop_basis)
        values.append(v);held.append(h);turn.append(u);trades+=t
    nav=np.mean(values,axis=0);h=np.mean(held,axis=0);u=np.mean(turn,axis=0)
    ix=prices[nominees[0]].index[start:]
    stats,annual=account_stats(nav,h,u,ix,trades,fee)
    return stats,annual,pd.DataFrame({'date':ix,'nav':nav,'held':h,'turnover':u}),trades

def main():
    pa=argparse.ArgumentParser();pa.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);a=pa.parse_args()
    root=a.root;out=root/'results';out.mkdir(exist_ok=True);(root/'private').mkdir(exist_ok=True)
    registration={'started_utc':pd.Timestamp.now(tz='UTC').isoformat(),'protocol_sha256':sha(root/'PROTOCOL.md'),
                  'code_sha256':sha(__file__),'native_sha256':sha(root/'vendor_v11_native.py'),
                  'manifest_sha256':sha(root/'data/input_manifest.json'),'seed':SEED,'new_parameter_grid':False}
    dump(out/'registration.json',registration)
    manifest,raw,adj,ix=load_data(root/'data/input_manifest.json')
    tail=pd.to_datetime(['2026-10-09','2026-10-12','2026-10-13','2026-10-14','2026-10-15','2026-10-16',
        '2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-26','2026-10-27',
        '2026-10-28','2026-10-29','2026-10-30','2026-11-02'])
    calendar=ix.append(tail);features={};watch_rows=[];panels=[]
    market=(adj['SPY'].close>adj['SPY'].close.rolling(200).mean())
    for s in CORE+PEERS:
        f,eps=defensive_features(adj[s],calendar);features[s]=f
        watch_rows += [{'symbol':s,**e} for e in eps]
        o=outcomes(raw[s],adj[s],126,.0005)
        p=o.join(f.drop(columns=['date','t','atr']),how='left');p['symbol']=s;p['panel']='CORE5' if s in CORE else 'PEERS13'
        p['market_above200']=market.reindex(p.index);p['halfyear']=p.index.year*2+(p.index.month>6).astype(int)
        p=p[p.date>=pd.Timestamp('2018-01-01')];panels.append(p.reset_index(drop=True))
        print('FEATURES',s,'complete_crosses',int((p.bull&(p.cell!='UNKNOWN')).sum()),flush=True)
    panel=pd.concat(panels,ignore_index=True)
    net=panel.pivot(index='date',columns='symbol',values='net')
    sp=outcomes(raw['SPY'],adj['SPY'],126,.0005).net
    for pop,col in [(CORE,'core_peer_net'),(PEERS,'broad_peer_net')]:
        panel[col]=np.nan
        for s in CORE+PEERS:
            names=[x for x in pop if x!=s];m=net[names].mean(axis=1).where(net[names].count(axis=1)>=2)
            mask=panel.symbol.eq(s);panel.loc[mask,col]=panel.loc[mask,'date'].map(m)
    panel['spy_net']=panel.date.map(sp)
    events=panel[panel.bull & panel.cell.ne('UNKNOWN')].copy()
    panel.to_parquet(root/'private/ordinary_panel.parquet',index=False)
    rows=[];subrows=[];matched={}
    periods=[('ALL','2018-01-01','2026-10-08'),('2018_2022','2018-01-01','2022-12-31'),('2023_2026','2023-01-01','2026-10-08')]
    for name,beg,end in periods:
        start,finish=pd.Timestamp(beg),pd.Timestamp(end);e=ordinary_matches(panel,events,start,finish);matched[name]=e
        grid,w=block_weights(start,finish)
        for (pop,cell),g in e.groupby(['panel','cell']):
            rows.append({'period':name,'panel':pop,'cell':cell,**summarize(g,grid,w)})
        for dim in ['symbol','sequence','stop_above_reference']:
            for (pop,cell,value),g in e.groupby(['panel','cell',dim]):
                subrows.append({'period':name,'panel':pop,'cell':cell,'dimension':dim,'value':value,**summarize(g)})
    e=matched['ALL'];e.to_csv(out/'defensive_events.csv',index=False,float_format='%.10g')
    pd.DataFrame(rows).to_csv(out/'defensive_summary.csv',index=False)
    pd.DataFrame(subrows).to_csv(out/'defensive_subgroups.csv',index=False)
    pd.DataFrame(watch_rows).to_csv(out/'defensive_watches.csv',index=False)
    influence=[]
    for pop,g in e[e.cell.eq('JOINT')].groupby('panel'):
        for dim in ['symbol','year']:
            values=g.symbol.unique() if dim=='symbol' else sorted(g.date.dt.year.unique())
            for v in values:
                z=g[g.symbol.ne(v)] if dim=='symbol' else g[g.date.dt.year.ne(v)]
                influence.append({'panel':pop,'omit_dimension':dim,'omit':v,**summarize(z)})
    pd.DataFrame(influence).to_csv(out/'defensive_influence.csv',index=False)
    grid,w=block_weights(pd.Timestamp('2018-01-01'),pd.Timestamp('2026-10-08'))
    contrasts=[]
    for pop in ['CORE5','PEERS13']:
        g=e[e.panel.eq(pop)];a=g[g.cell.eq('JOINT')];b=g[g.cell.eq('NEITHER')]
        contrasts.append({'contrast':pop+'_joint_minus_neither',**boot_contrast(a,b,'net',grid,w)})
    deltas={}
    for pop in ['CORE5','PEERS13']:
        z=e[e.panel.eq(pop)&e.cell.eq('JOINT')].assign(delta=lambda q:q.net-q.ordinary_net)
        deltas[pop]=z
    contrasts.append({'contrast':'core_minus_peer_ordinary_increment',
                      **boot_contrast(deltas['CORE5'],deltas['PEERS13'],'delta',grid,w)})
    pd.DataFrame(contrasts).to_csv(out/'defensive_contrasts.csv',index=False)
    archived=pd.read_csv(root/'data/archive/signal_state_events.csv');archived=archived[archived.frame.eq('1D')].copy()
    archived['date']=pd.to_datetime(archived.signal_date);archived=archived.rename(columns={'symbol':'symbol','cell':'old_cell','net':'old_net'})
    comparison=e[['symbol','date','cell','net']].merge(archived[['symbol','date','old_cell','old_net']],on=['symbol','date'],how='outer',indicator=True)
    comparison['net_difference']=comparison.net-comparison.old_net
    comparison.to_csv(out/'v11_reconstruction_comparison.csv',index=False)
    parity={'new_events':len(e),'archived_events':len(archived),'matched_dates':int(comparison._merge.eq('both').sum()),
            'new_only':int(comparison._merge.eq('left_only').sum()),'old_only':int(comparison._merge.eq('right_only').sum()),
            'cell_mismatches':int((comparison.loc[comparison._merge.eq('both'),'cell']!=comparison.loc[comparison._merge.eq('both'),'old_cell']).sum()),
            'max_abs_return_difference':float(comparison.net_difference.abs().max())}
    dump(out/'v11_reconstruction.json',clean(parity))
    # Reconcile archived first-watch records separately; no new outcome is used to pick policies.
    watch=pd.read_csv(root/'data/archive/core_episode_ledger_complete_metadata.csv')
    watch=watch[(watch['mode']=='confirmed')&(watch.frame=='1D')&(watch.two_week_phase==0)&(watch.lower_phase==0)&(watch.warmup==200)]
    watch.to_csv(out/'archived_first_watch_core.csv',index=False)
    # Frozen capital policies; one accepted schedule reused by the stopped arm.
    psummary=[];annual=[];paths=[];ptrades=[];roster_rows=[]
    start=int(ix.searchsorted(pd.Timestamp('2018-01-01')));n=len(ix)
    rosters={'OWN':{},'ALL_CROSSES':{},'JOINT':{}}
    for s in CORE+PEERS:
        f=features[s];v=(f.index>=ix[start])&(f.cell!='UNKNOWN')&f.bull
        rosters['OWN'][s]=[{'signal_t':start-1,'entry_t':start,'scheduled_exit_t':n+1}]
        for label,mask in [('ALL_CROSSES',v),('JOINT',v&f.cell.eq('JOINT'))]:
            rr,skip=accepted_roster(f.loc[mask,'t'],126,n);rosters[label][s]=rr
            roster_rows += [{'population':'DEFENSIVE','policy':label,'symbol':s,'accepted':True,**r} for r in rr]
            roster_rows += [{'population':'DEFENSIVE','policy':label,'symbol':s,'accepted':False,'signal_t':i,'reason':reason} for i,reason in skip]
    for pop,names in [('CORE5',CORE),('PEERS13',PEERS),('ALL18',CORE+PEERS)]:
        for policy in ['OWN','ALL_CROSSES','JOINT','JOINT_STOP']:
            rr=rosters['JOINT' if policy=='JOINT_STOP' else policy]
            for scenario,fee,cy in [('PRIMARY',.0005,0.),('CASH3_SCENARIO',.0005,.03),('COST50',.0025,0.)]:
                st,an,path,tr=run_portfolio(adj,raw,rr,names,start,fee,cy,stop=policy.endswith('_STOP'))
                key={'experiment':'DEFENSIVE','population':pop,'policy':policy,'scenario':scenario}
                psummary.append({**key,**st});annual += [{**key,**r} for r in an]
                if scenario=='PRIMARY':
                    paths.append(path.assign(**key));ptrades += [{**key,**r} for r in tr]
    # Sector roster is the original pre-outcome event catalogue, including immature signals.
    base=Path(manifest['base_events_path']);assert sha(base)==manifest['base_events_sha256']
    old=pd.read_parquet(base,columns=['ticker','date','base'])
    old=old[old.ticker.isin(SECTORS)&old.base.eq('bottom|BASE:rsi_recovery')&(old.date>=pd.Timestamp('2020-01-01'))]
    sar={s:raw[s].reindex(ix) for s in SECTORS+['SPY']};sadj={s:adj[s].reindex(ix) for s in SECTORS+['SPY']}
    start=int(ix.searchsorted(pd.Timestamp('2020-01-01')));sector_rosters={};own={};se=[]
    sector_out={s:outcomes(raw[s],adj[s],63,.001,'raw') for s in SECTORS+['SPY']}
    for s in SECTORS:
        dates=pd.DatetimeIndex(old.loc[old.ticker.eq(s),'date']);ii=ix.get_indexer(dates);assert (ii>=0).all()
        rr,sk=accepted_roster(ii,63,len(ix));sector_rosters[s]=rr;own[s]=[{'signal_t':start-1,'entry_t':start,'scheduled_exit_t':len(ix)+1}]
        roster_rows += [{'population':'SECTORS','policy':'RSI','symbol':s,'accepted':True,**r} for r in rr]
        roster_rows += [{'population':'SECTORS','policy':'RSI','symbol':s,'accepted':False,'signal_t':i,'reason':reason} for i,reason in sk]
        q=sector_out[s].reindex(dates).dropna(subset=['net']).copy();q['symbol']=s
        peers=pd.concat({t:sector_out[t].net for t in SECTORS if t!=s},axis=1)
        q['peer_net']=peers.mean(axis=1).reindex(q.index);q['spy_net']=sector_out['SPY'].net.reindex(q.index)
        q['halfyear']=q.index.year*2+(q.index.month>6).astype(int);se.append(q)
    sec=pd.concat(se,ignore_index=True);sec.to_csv(out/'sector_events.csv',index=False)
    srows=[];grid,w=block_weights(pd.Timestamp('2020-01-01'),pd.Timestamp('2026-10-08'))
    for name,mask in [('ALL',np.ones(len(sec),bool)),('2020_2022',sec.exit_date<=pd.Timestamp('2022-12-31')),('2023_2026',sec.date>=pd.Timestamp('2023-01-01'))]:
        g=sec[mask].copy();g['broad_peer_net']=g.peer_net;srows.append({'period':name,**summarize(g,grid,w)})
    pd.DataFrame(srows).to_csv(out/'sector_event_summary.csv',index=False)
    for policy in ['OWN','RSI_SELECTED','RSI_ALL_SECTORS','RSI_SPY','RSI_STOP']:
        rr=own if policy=='OWN' else sector_rosters
        basket=SECTORS if policy=='RSI_ALL_SECTORS' else ['SPY'] if policy=='RSI_SPY' else None
        for scenario,fee,cy in [('PRIMARY',.001,0.),('CASH3_SCENARIO',.001,.03),('COST50',.0025,0.)]:
            st,an,path,tr=run_portfolio(sadj,sar,rr,SECTORS,start,fee,cy,stop=policy=='RSI_STOP',basket=basket,stop_basis='raw')
            key={'experiment':'SECTOR','population':'SECTORS12','policy':policy,'scenario':scenario}
            psummary.append({**key,**st});annual += [{**key,**r} for r in an]
            if scenario=='PRIMARY':paths.append(path.assign(**key));ptrades += [{**key,**r} for r in tr]
    pd.DataFrame(psummary).to_csv(out/'portfolio_summary.csv',index=False)
    pd.DataFrame(annual).to_csv(out/'portfolio_annual.csv',index=False)
    pd.concat(paths,ignore_index=True).to_csv(out/'portfolio_paths.csv',index=False,float_format='%.10g')
    pd.DataFrame(ptrades).to_csv(out/'portfolio_trades.csv',index=False,float_format='%.10g')
    pd.DataFrame(roster_rows).to_csv(out/'capital_rosters.csv',index=False)
    summary={**registration,'completed_utc':pd.Timestamp.now(tz='UTC').isoformat(),'defensive_complete_events':len(e),
             'sector_complete_events':len(sec),'sector_all_signals':len(old),'portfolio_policies_scenarios':len(psummary),
             'archive_parity':parity,'interpretation':'exploratory exposed history; no production qualification'}
    dump(out/'run_summary.json',clean(summary));print(json.dumps(clean(summary)),flush=True)

if __name__=='__main__':main()
