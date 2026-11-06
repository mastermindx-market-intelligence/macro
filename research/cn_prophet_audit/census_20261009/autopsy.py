#!/usr/bin/env python3
"""Read-only China Prophet historical diagnostic at one immutable Git revision.

No repository modules are imported and no shared source or data is written. The
two pure fill functions are extracted by AST from the pinned source after review.
All analytical outputs go under --out. Prices are current-at-pin adjusted bars:
these diagnostics do not certify point-in-time investment returns.
"""
from __future__ import annotations
import argparse, ast, collections, hashlib, io, json, math, os, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

SHA = '3d90aad6d83152dfeeaf8345bc995826ac9d3139'
DEFAULT_REPO = '/Users/chriswong/Documents/Cluade/macro-main'
HORIZONS = (1, 3, 5, 10, 20, 60)

def clean(v):
    if isinstance(v, dict): return {str(k): clean(x) for k,x in v.items()}
    if isinstance(v, (list, tuple)): return [clean(x) for x in v]
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating, float)): return float(v) if np.isfinite(v) else None
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, (pd.Timestamp,)): return v.isoformat()
    if v is pd.NA or v is pd.NaT: return None
    return v

def describe(d, col='excess_cc', bootstrap=True):
    x=d.loc[d[col].notna()].copy() if len(d) and col in d else pd.DataFrame()
    if not len(x): return {'n':0,'n_dates':0}
    v=x[col].to_numpy(float); out={'n':len(v),'n_dates':x.date.nunique(),
        'mean_pct':v.mean(),'median_pct':np.median(v),'positive_n':int((v>0).sum()),
        'positive_rate':(v>0).mean(),'p10_pct':np.quantile(v,.1),'p90_pct':np.quantile(v,.9)}
    if bootstrap and x.date.nunique()>=2:
        g=x.groupby('date')[col].agg(['sum','count']); wins=x.assign(win=x[col]>0).groupby('date').win.sum()
        rng=np.random.default_rng(20261009); ix=rng.integers(0,len(g),size=(2000,len(g)))
        den=g['count'].to_numpy()[ix].sum(axis=1)
        out['mean_dateblock95']=np.quantile(g['sum'].to_numpy()[ix].sum(axis=1)/den,[.025,.975]).tolist()
        out['positive_dateblock95']=np.quantile(wins.to_numpy()[ix].sum(axis=1)/den,[.025,.975]).tolist()
    return clean(out)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default=DEFAULT_REPO);ap.add_argument('--out',required=True);args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    def git(*a):return subprocess.check_output(['git','-C',args.repo,*a])
    paths=git('ls-tree','-r','--name-only',SHA).decode().splitlines(); pathset=set(paths)
    blobs={}
    def blob(p):
        b=git('show',SHA+':'+p);blobs[p]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
    def parquet(p):return pd.read_parquet(io.BytesIO(blob(p)))
    board=parquet('data/china_standout_track/board.parquet')
    cand=parquet('data/china_prophet_rank/candidates.parquet')
    latch=parquet('data/china_standout_track/entry_latch.parquet')
    forward=parquet('data/cn_prophet_audit/forward_log.parquet')
    live=parquet('data/cn_prophet_live/forward.parquet')
    members=parquet('data/china_search/members.parquet')
    bench=parquet('data/china/510300.SS.parquet').sort_index()
    cal=pd.DatetimeIndex(bench.index); bclose=bench.close
    latest=json.loads(blob('data/cn_prophet_audit/latest.json'))
    cst=blob('engine/china_standout_track.py').decode()
    fill_ast=ast.Module(body=[n for n in ast.parse(cst).body if isinstance(n,ast.FunctionDef) and n.name in ('_dust','_t1_fill_detail')],type_ignores=[])
    ns={'pd':pd,'_PRICE_REL_TOL':1e-6,'BASIS_T1_OPEN':'t1_open','BASIS_T1_HL2':'t1_hl2','BASIS_T1_CLOSE':'t1_close','BASIS_DEFERRED':'deferred','_warn_corrupt_bar':lambda *a:None}
    exec(compile(fill_ast,'pinned_china_standout_track.py','exec'),ns)
    fill=ns['_t1_fill_detail']
    report={'source_sha':SHA,'schema':'cn-prophet-historical-diagnostic/v1',
      'methodology':{'primary':'One contiguous membership episode per definition; current adjusted close of first CSI300 session after recorded board date to the close h benchmark sessions later. Both stock and CSI300 use exact matched dates and close/close basis. Flat OHLC and zero-volume entry rows are conservatively indeterminate; this is not proof of legal limit status or an impossible fill.',
        'horizon_sessions':list(HORIZONS),'asof':str(cal.max().date()),
        'production_reconciliation':'H10 separately uses current pinned _t1_fill_detail open/HL2 and the 10th stock close INCLUDING fill session; benchmark starts at fill-session close, exactly reproducing ops telemetry. Latch variant differs only entry price.',
        'limitations':['Current adjusted-price snapshot, not archived point-in-time price vintages; intraday execution/liquidity and terminal delisting outcomes not certified.','Board dates and selected features have no per-record UTC publication receipt or source SHA.','Date-block intervals retain all names from sampled dates but do not fully correct serially overlapping holdings or repeated issuers.','Recorded board definitions must remain separate. Shadow/watch results are not user recommendations.','Close/close alternative defines h elapsed market sessions AFTER next-session-close entry, so it is deliberately not the production H10 measure.']}}
    report['datasets']={}
    for name,d,dc,key in [('board',board,'date',['date','ticker','board_definition']),('candidates',cand,'stamp_date',['stamp_date','ticker','board_definition']),('entry_latch',latch,'date',['date','ticker']),('forward_log',forward,'date',['date','board_definition'])]:
        report['datasets'][name]={'rows':len(d),'start':str(d[dc].min()),'end':str(d[dc].max()),'dates':d[dc].nunique(),'duplicate_keys':int(d.duplicated(key).sum()),'columns':list(d.columns)}
    report['datasets']['live_forward']={'rows':len(live),'columns':list(live.columns)}
    report['datasets']['candidates']['raw_eligible_nulls']=int(cand.raw_eligible.isna().sum())
    report['datasets']['members']={'rows':len(members),'sectors':members.sector.value_counts(dropna=False).to_dict()}
    report['dataset_definitions']={str(k):{'rows':len(g),'dates':g.date.nunique(),'tickers':g.ticker.nunique(),'start':g.date.min(),'end':g.date.max()} for k,g in board.groupby('board_definition')}
    report['candidate_definitions']={str(k):{'rows':len(g),'dates':g.stamp_date.nunique(),'tickers':g.ticker.nunique(),'lanes':g.lane.value_counts(dropna=False).to_dict()} for k,g in cand.groupby('board_definition')}
    report['board_overlap']={'unique_date_ticker':len(board.drop_duplicates(['date','ticker'])),'rows':len(board),'multi_definition_date_ticker':int((board.groupby(['date','ticker']).board_definition.nunique()>1).sum())}
    v4=board[board.board_definition=='cn_prophet_v4'];sh3=board[board.board_definition=='cn_prophet_v3_shadow']; z=v4.merge(sh3,on=['date','ticker'],suffixes=('_v4','_sh3'))
    report['v4_vs_v3_shadow']={'v4_rows':len(v4),'shadow_rows':len(sh3),'same_date_ticker_rows':len(z),'same_rank_rows':int((z.board_rank_v4==z.board_rank_sh3).sum()),'same_prophet_score_rows':int(np.isclose(z.prophet_score_v4,z.prophet_score_sh3,equal_nan=True).sum())}
    vintage=[];discordant=set()
    for definition,g in board[board.board_definition.isin(cand.board_definition.unique())].groupby('board_definition'):
      for date,q in g.groupby('date'):
        c=cand[(cand.board_definition==definition)&(cand.stamp_date==date)];f=c[c.lane=='featured']
        matched=q[['ticker','prophet_score']].merge(c[['ticker','prophet_score','lane']],on='ticker',how='left',suffixes=('_board','_candidate'))
        different_set=set(q.ticker)!=set(f.ticker);score_disagree=int((abs(matched.prophet_score_board-matched.prophet_score_candidate)>1e-6).sum())
        if different_set or score_disagree:discordant.add((str(definition),str(date)))
        vintage.append({'definition':definition,'date':date,'board_rows':len(q),'candidate_featured_rows':len(f),'board_not_candidate_featured':int((matched.lane!='featured').sum()),'score_disagreements':score_disagree,'same_featured_set':not different_set})
    report['cohort_vintage_coherence']=vintage
    report['board_metadata_nulls']={c:int(board[c].isna().sum()) for c in ['prophet_score','own_market_regime','species_id','archetype','vector_asof','order_mode','requested_order_basis','effective_order_basis','fallback_reason'] if c in board}
    report['board_basis_counts']=board.basis_used.value_counts(dropna=False).to_dict()
    report['latch_basis_counts']=latch.basis_used.value_counts(dropna=False).to_dict()
    report['clock_checks']={}
    stamps=pd.to_datetime(cand.stamp_date)
    for c in ['signal_asof','signal_bar_asof','micro_asof','micro_batch_asof','board_asof','sector_turn_asof','narrative_asof']:
        vals=pd.to_datetime(cand[c],errors='coerce',format='mixed');delta=(stamps-vals).dt.days
        report['clock_checks'][c]={'non_null':int(vals.notna().sum()),'future':int((delta<0).sum()),'same_date':int((delta==0).sum()),'older':int((delta>0).sum()),'over_7_calendar_days':int((delta>7).sum()),'max_lag_days':delta.max()}
    report['clock_checks']['fresh_flag_with_old_micro_batch']={'n':int(((cand.micro_fresh==True)&(pd.to_datetime(cand.micro_batch_asof)<stamps)).sum()),'fresh_n':int((cand.micro_fresh==True).sum())}
    last=cand[cand.stamp_date==cand.stamp_date.max()];missing=last[last.intel_score.isna()]
    report['last_missing_intel']=missing[['ticker','lane','score_rank','prophet_score','raw_eligible','buyable','entry_status','intel_basis','intel_unavailable_reason']].to_dict('records')
    last_cols=['ticker','sector','lane','lane_rank','lane_reasons','score_rank','prophet_score','raw_eligible','buyable','entry_status','stage','extended','adv_yi','execution_clear','micro_fresh','intel_score','intel_basis','intel_unavailable_reason','prophet_signal','prophet_entry','prophet_runway','prophet_bottom_quality','prophet_reversal_member','sector_turn_state','narrative_level']
    last[last_cols].to_json(out/'last_rank_rows.json',orient='records')

    # Exact production build_episodes construction, limited to pure reviewed function.
    ts=blob('engine/track_scoring.py').decode();ep_ast=ast.Module(body=[n for n in ast.parse(ts).body if isinstance(n,ast.FunctionDef) and n.name=='build_episodes'],type_ignores=[])
    ep_ns={'Mapping':dict,'Iterable':list};exec(compile(ep_ast,'pinned_track_scoring.py','exec'),ep_ns)
    eps=[]
    for definition,g in board.groupby('board_definition'):
        days={d:set(q.ticker) for d,q in g.groupby('date')};admission=g.drop_duplicates(['date','ticker']).set_index(['date','ticker'])
        for e in ep_ns['build_episodes'](days):
            a=admission.loc[(e['entry_date'],e['ticker'])].to_dict();eps.append({**a,'date':e['entry_date'],'ticker':e['ticker'],'board_definition':definition,'membership_exit':e['exit_date']})
    episodes=pd.DataFrame(eps);episodes.to_csv(out/'episodes_issuance.csv',index=False)
    report['episode_counts']=episodes.board_definition.value_counts().to_dict()
    lmap={(str(r.date),str(r.ticker)):r for r in latch.itertuples()}
    by_stock={str(t):g for t,g in episodes.groupby('ticker')};cand_by_stock={str(t):g for t,g in cand.groupby('ticker')}
    ticker_set=set(by_stock)|set(cand_by_stock)
    panel_records=[]; board_results=[]; candidate_results=[];latch_deltas=[];prod_rows=[];bar_integrity=collections.Counter();price_source_hashes={}
    price_paths=[p for p in paths if p.startswith('data/china_stocks/') and p.endswith('.parquet')]
    # Streaming git cat-file avoids 1,876 separate processes and never checks files out.
    proc=subprocess.Popen(['git','-C',args.repo,'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def batchblob(p):
        proc.stdin.write((SHA+':'+p+'\n').encode());proc.stdin.flush();header=proc.stdout.readline().decode().strip().split()
        if len(header)!=3:raise RuntimeError('Missing immutable blob '+p)
        data=proc.stdout.read(int(header[2]));proc.stdout.read(1)
        price_source_hashes[p]={'git_blob':header[0],'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        return data
    stocks=[(Path(p).stem,p) for p in price_paths]
    missing_tickers=ticker_set-{t for t,p in stocks}
    stocks.extend((t,'data/china/'+t+'.parquet') for t in missing_tickers if 'data/china/'+t+'.parquet' in pathset)
    report['missing_price_tickers']=sorted(ticker_set-{t for t,p in stocks})
    def cc_row(pdf,t,date,h,meta):
        d0=pd.Timestamp(date);i=cal.searchsorted(d0,side='right');j=i+h
        base={**meta,'ticker':t,'date':str(date),'horizon':h,'status':'immature'}
        if i>=len(cal) or j>=len(cal):return base
        e,x=cal[i],cal[j];base.update(entry_date=str(e.date()),exit_date=str(x.date()))
        if e not in pdf.index or x not in pdf.index:return {**base,'status':'missing_exact_session'}
        er=pdf.loc[e];xr=pdf.loc[x]
        if float(er.get('volume',1))<=0:return {**base,'status':'zero_volume_entry'}
        if all(pd.notna(er.get(c)) for c in ('high','low','close')) and er.high==er.low==er.close:return {**base,'status':'flat_bar_indeterminate'}
        epx=float(er.close);xpx=float(xr.close)
        if not np.isfinite(epx*xpx) or min(epx,xpx)<=0:return {**base,'status':'invalid_price'}
        pnl=(xpx/epx-1)*100;br=(float(bclose.loc[x])/float(bclose.loc[e])-1)*100
        path=pdf.loc[(pdf.index>e)&(pdf.index<=x),'close'].dropna()
        return {**base,'status':'observed','entry_close':epx,'exit_close':xpx,'pnl_cc':pnl,'benchmark_cc':br,'excess_cc':pnl-br,'mae_close':min(0.0,(float(path.min())/epx-1)*100) if len(path) else None,'path_bars':len(path)}
    for ix,(t,p) in enumerate(stocks):
        pdf=pd.read_parquet(io.BytesIO(batchblob(p))).sort_index();pdf.index=pd.to_datetime(pdf.index)
        if 'close' not in pdf:continue
        lastdate=pdf.index.max();age=int((cal>lastdate).sum());close=pdf.close
        panel_records.append({'ticker':t,'rows':len(pdf),'start':str(pdf.index.min().date()),'end':str(lastdate.date()),'terminal_lag_sessions':age,'duplicate_dates':int(pdf.index.duplicated().sum()),'nonpositive_close':int((close<=0).sum()),'zero_volume_since_2026_06_30':int(((pdf.get('volume',pd.Series(1,index=pdf.index))<=0)&(pdf.index>=pd.Timestamp('2026-06-30'))).sum())})
        recent=pdf[pdf.index>='2026-06-30'];bar_integrity['recent_bars']+=len(recent)
        if {'open','high','low','close'}<=set(recent):
            tol=np.maximum(recent[['open','high','low']].abs().max(axis=1),1)*1e-6
            bar_integrity['open_outside_range']+=int(((recent.open<recent.low-tol)|(recent.open>recent.high+tol)).sum())
            bar_integrity['close_outside_range']+=int(((recent.close<recent.low-tol)|(recent.close>recent.high+tol)).sum())
        if t not in ticker_set:continue
        for a in by_stock.get(t,pd.DataFrame()).to_dict('records'):
            for h in HORIZONS:board_results.append(cc_row(pdf,t,a['date'],h,{k:a.get(k) for k in ('board_definition','board_rank','prophet_score','entry_status','tier','extended','washout','species_id')}))
            d0=pd.Timestamp(a['date']);f=fill(pdf,d0,t);lr=lmap.get((str(a['date']),t));fd=f['t1_date'];after=pdf.loc[pdf.index>d0,'close'].dropna()
            row={k:a.get(k) for k in ('date','ticker','board_definition','board_rank','prophet_score','entry_status','tier')};row.update(f);row.update(n_forward=len(after),latch_exists=lr is not None,latched_entry=None if lr is None else float(lr.entry))
            if lr is not None and f['entry'] is not None:
                delt=(float(f['entry'])/float(lr.entry)-1)*100;row['fresh_vs_latch_pct']=delt
                if abs(delt)>0.0001:latch_deltas.append({**row,'latched_basis':lr.basis_used,'latched_asof':lr.latched_asof})
            if f['entry'] is not None and not f['locked'] and len(after)>=10:
                x=after.index[9];e=after.index[0]
                if e in bclose.index and x in bclose.index:
                    br=(float(bclose.loc[x])/float(bclose.loc[e])-1)*100;pnl=(float(after.iloc[9])/float(f['entry'])-1)*100
                    row.update(pnl=pnl,excess=pnl-br,exit_date=str(x.date()),benchmark=br,matured=True)
                    if lr is not None:row['latch_excess']=(float(after.iloc[9])/float(lr.entry)-1)*100-br
                    a0=pdf.loc[d0] if d0 in pdf.index else None
                    if a0 is not None:
                        prev=pdf.loc[pdf.index<d0,'close'].dropna();back=pdf.loc[pdf.index<=d0,'close'].dropna();ret0=float(a0.close)/float(prev.iloc[-1])-1 if len(prev) else None;trail=float(back.iloc[-1])/float(back.iloc[-22])-1 if len(back)>=22 else None;gap=float(f['entry'])/float(a0.close)-1
                        row.update(day0_ret=ret0,trail21=trail,t1_gap=gap)
            prod_rows.append(row)
        for a in cand_by_stock.get(t,pd.DataFrame()).to_dict('records'):
            if not bool(a.get('raw_eligible')):continue
            for h in HORIZONS:
                meta={k:a.get(k) for k in ('board_definition','score_rank','prophet_score','intel_score','lane','lane_rank','lane_reasons','ret_3m','quality_z','rev_percentile','adv_yi','sector','entry_status','buyable')}
                candidate_results.append(cc_row(pdf,t,a['stamp_date'],h,meta))
        if ix and ix%300==0:print('PROGRESS',ix,'/',len(stocks),flush=True)
    for t in report['missing_price_tickers']:
      for a in cand_by_stock.get(t,pd.DataFrame()).to_dict('records'):
        if not bool(a.get('raw_eligible')):continue
        for h in HORIZONS:
            meta={k:a.get(k) for k in ('board_definition','score_rank','prophet_score','intel_score','lane','lane_rank','lane_reasons','ret_3m','quality_z','rev_percentile','adv_yi','sector','entry_status','buyable')}
            candidate_results.append({**meta,'ticker':t,'date':a['stamp_date'],'horizon':h,'status':'no_price_file'})
    proc.stdin.close();proc.wait()
    pr=pd.DataFrame(panel_records);pr.to_csv(out/'price_panel_integrity.csv',index=False)
    report['panel_integrity']={'n_price_files':len(pr),'oldest_start':pr.start.min(),'latest_end':pr.end.max(),'terminal_lag_over_20_sessions':int((pr.terminal_lag_sessions>20).sum()),'at_panel_max':int((pr.end==pr.end.max()).sum()),'lags':pr.terminal_lag_sessions.value_counts().sort_index().to_dict(),'current_members_absent_prices':len(set(members.index)-set(pr.ticker)),**dict(bar_integrity)}
    result=pd.DataFrame(board_results);result.to_csv(out/'episode_horizon_returns.csv',index=False)
    pool=pd.DataFrame(candidate_results);pool.to_csv(out/'eligible_candidate_horizon_returns.csv',index=False)
    pro=pd.DataFrame(prod_rows);pro.to_csv(out/'production_h10_reconciliation.csv',index=False)
    pd.DataFrame(latch_deltas).to_csv(out/'latch_deltas.csv',index=False)
    report['latch_reconciliation']={'episode_rows':len(pro),'latch_available':int(pro.latch_exists.sum()),'changed_entries':len(latch_deltas),'changed_unique_date_ticker':len({(r['date'],r['ticker']) for r in latch_deltas}),'median_abs_change_pct':float(np.median([abs(r['fresh_vs_latch_pct']) for r in latch_deltas])) if latch_deltas else 0,'over_1pct':sum(abs(r['fresh_vs_latch_pct'])>1 for r in latch_deltas),'over_5pct':sum(abs(r['fresh_vs_latch_pct'])>5 for r in latch_deltas),'max_abs_change_pct':max((abs(r['fresh_vs_latch_pct']) for r in latch_deltas),default=0),'examples':sorted(latch_deltas,key=lambda r:abs(r['fresh_vs_latch_pct']),reverse=True)[:6]}
    report['episode_horizons']=[]
    for (definition,h),g in result.groupby(['board_definition','horizon']):
        obs=g[g.status=='observed'];stats=describe(obs);pn=describe(obs,'pnl_cc',False)
        stats.update(board_definition=definition,horizon=int(h),total_episodes=len(g),status_counts=g.status.value_counts().to_dict(),absolute_mean_pct=pn.get('mean_pct'),absolute_positive_rate=pn.get('positive_rate'),median_mae_close_pct=obs.mae_close.median() if 'mae_close' in obs else None)
        ics=[]
        for d,q in obs.groupby('date'):
            if len(q)>=5 and q.board_rank.nunique()>=5:ics.append(q.board_rank.rank().corr(q.excess_cc.rank()))
        stats.update(mean_daily_rank_ic=np.nanmean(ics) if ics else None,ic_dates=len(ics))
        report['episode_horizons'].append(stats)
    report['production_h10']=[]
    for definition,g in pro.groupby('board_definition'):
        obs=g[g.excess.notna()];s=describe(obs,'excess');s.update(board_definition=definition,total_episodes=len(g),n_locked=int(g.locked.sum()),basis_counts=g.basis_used.value_counts().to_dict(),latch=describe(obs,'latch_excess'))
        if len(obs):
            pair=obs.dropna(subset=['latch_excess']);s.update(latch_common_n=len(pair),mean_fresh_minus_latch_pct=(pair.excess-pair.latch_excess).mean(),win_sign_changes=int(((pair.excess>0)!=(pair.latch_excess>0)).sum()))
        report['production_h10'].append(s)
    # Same date, same raw-eligible pool. Baselines are fixed, unswept diagnostics.
    baseline_rows=[]; feature_coverage=[]; matching_gaps=[]; selection_checks=[]
    def top6(o,col,ascending=False):
        ordered=o.dropna(subset=[col]).sort_values([col,'ticker'],ascending=[ascending,True])
        return ordered.groupby('sector',dropna=False,sort=False).head(4).head(6)
    for (definition,h,date),g0 in pool.groupby(['board_definition','horizon','date']):
      for scope in ('raw_eligible_illustrative','rankable_for_featured','rankable_common_features'):
        if scope!='raw_eligible_illustrative' and (str(definition),str(date)) in discordant:continue
        g=g0 if scope=='raw_eligible_illustrative' else g0[(g0.lane=='featured')|((g0.lane=='more_actionable')&g0.lane_reasons.isin(['featured_cap','sector_cap']))]
        if scope=='rankable_common_features':g=g.dropna(subset=['prophet_score','intel_score','ret_3m','quality_z'])
        if len(g)<6:continue
        o=g[g.status=='observed'];coverage=len(o)/len(g)
        if not len(o):continue
        # All membership is frozen on issuance fields BEFORE inspecting outcome status.
        featured=g[g.lane=='featured'].sort_values(['lane_rank','ticker']).head(6)
        score_reference=top6(g,'prophet_score')
        baselines={'eligible_equal':g,'score_top6':score_reference,'momentum_top6':top6(g,'ret_3m'),'reversal_top6':top6(g,'ret_3m',True),'quality_top6':top6(g,'quality_z'),'intel_top6':top6(g,'intel_score')}
        if scope!='rankable_common_features':baselines['featured_top6']=featured
        old_baselines={'eligible_equal':o,'score_top6':top6(o,'prophet_score'),'momentum_top6':top6(o,'ret_3m'),'reversal_top6':top6(o,'ret_3m',True),'quality_top6':top6(o,'quality_z'),'intel_top6':top6(o,'intel_score'),'featured_top6':o[o.lane=='featured'].sort_values(['lane_rank','ticker']).head(6)}
        for feat in ('prophet_score','intel_score','ret_3m','quality_z'):
            feature_coverage.append({'definition':definition,'horizon':h,'date':date,'scope':scope,'feature':feat,'n':len(g),'non_null':int(g[feat].notna().sum())})
        for label,q in baselines.items():
            changed=set(q.ticker)!=set(old_baselines[label].ticker)
            selection_checks.append({'definition':definition,'horizon':h,'date':date,'scope':scope,'baseline':label,'selected_n':len(q),'observed_selected_n':int((q.status=='observed').sum()),'changed_if_selecting_observed_first':changed,'selected_unobserved':q.loc[q.status!='observed',['ticker','status']].to_dict('records'),'old_only_tickers':sorted(set(old_baselines[label].ticker)-set(q.ticker)),'rejected_observed_first_mean_pct':old_baselines[label].excess_cc.mean() if len(old_baselines[label])>=6 else None,'frozen_selection_mean_pct':q.excess_cc.mean() if len(q)>=6 and bool((q.status=='observed').all()) else None})
            if len(q)<6 or not bool((q.status=='observed').all()):continue
            ref_ok=len(featured)==6 and bool((featured.status=='observed').all()) and scope!='rankable_common_features'
            score_ok=len(score_reference)==6 and bool((score_reference.status=='observed').all())
            eligible_mean=g.excess_cc.mean() if bool((g.status=='observed').all()) else None
            baseline_rows.append({'board_definition':definition,'horizon':int(h),'date':date,'scope':scope,'baseline':label,'n':len(q),'pool_n':len(g),'observed_n':len(o),'coverage':coverage,'excess_cc':q.excess_cc.mean(),'pnl_cc':q.pnl_cc.mean(),'hit_rate':(q.excess_cc>0).mean(),'eligible_control_excess':eligible_mean,'versus_eligible_pct':q.excess_cc.mean()-eligible_mean if eligible_mean is not None else None,'featured_same_date_excess':featured.excess_cc.mean() if ref_ok else None,'versus_featured_pct':q.excess_cc.mean()-featured.excess_cc.mean() if ref_ok else None,'versus_score_same_pool_pct':q.excess_cc.mean()-score_reference.excess_cc.mean() if score_ok else None})
        if scope=='rankable_for_featured' and len(featured)==6:
            alternatives=g[~g.ticker.isin(featured.ticker)];matches=[]
            for a in featured.itertuples():
                m=alternatives[(alternatives.sector==a.sector)&(alternatives.adv_yi>=a.adv_yi*.5)&(alternatives.adv_yi<=a.adv_yi*2)]
                matches.append(m)
            matching_gaps.append({'definition':definition,'horizon':h,'date':date,'featured_n':6,'same_sector_liquidity_matched_slots':sum(bool(len(m)) for m in matches),'alternatives_per_slot':[len(m) for m in matches]})
    bl=pd.DataFrame(baseline_rows)
    common=bl[bl.scope=='rankable_common_features'];valid=common[common.baseline.isin(['score_top6','intel_top6','momentum_top6','reversal_top6','quality_top6'])].groupby(['board_definition','horizon','date']).baseline.nunique();common_keys=set(valid[valid==5].index)
    bl=bl[(bl.scope!='rankable_common_features')|pd.Series([(d,h,dt) in common_keys for d,h,dt in zip(bl.board_definition,bl.horizon,bl.date)],index=bl.index)]
    bl.to_csv(out/'baseline_date_returns.csv',index=False);report['baseline_comparison']=[]
    report['feature_coverage']=feature_coverage;report['sector_liquidity_matching_gaps']=matching_gaps;report['selection_before_outcome_checks']=selection_checks
    for (definition,h,scope,label),g in bl.groupby(['board_definition','horizon','scope','baseline']):
        s=describe(g);s.update(board_definition=definition,horizon=int(h),scope=scope,baseline=label,n_candidate_observations=int(g.n.sum()),average_precision=g.hit_rate.mean(),mean_vs_eligible_pct=g.versus_eligible_pct.mean(),vs_eligible=describe(g,'versus_eligible_pct'),vs_featured=describe(g,'versus_featured_pct'),vs_score_same_pool=describe(g,'versus_score_same_pool_pct'))
        if label=='featured_top6':s['cost_sensitivity_excess_pct']={str(bps)+'bps':s['mean_pct']-bps/100 for bps in (10,30,60)}
        report['baseline_comparison'].append(s)
    case=pro[(pro.board_definition=='cn_prophet_v4')&pro.excess.notna()].copy();cases=[]
    if len(case):
        chosen=list(case.sort_values('excess').head(2).index)+list(case.sort_values('excess').tail(2).index)
        for i in chosen:
            r=case.loc[i].to_dict();c=cand[(cand.stamp_date==r['date'])&(cand.ticker==r['ticker'])&(cand.board_definition==r['board_definition'])]
            if len(c):r['candidate_snapshot_features']={k:c.iloc[0].get(k) for k in ['name','sector','lane','lane_reasons','gate_tier','gate_sub','signal_asof','signal_bar_asof','entry_status','entry_spot','stop','prophet_score','intel_score','intel_basis','prophet_signal','prophet_entry','prophet_runway','prophet_bottom_quality','prophet_reversal_member','quality_z','ret_3m']}
            r['matched_horizons']=result[(result.date==r['date'])&(result.ticker==r['ticker'])&(result.board_definition==r['board_definition'])].to_dict('records');cases.append(r)
    report['candidate_cases']=cases
    report['latest_telemetry_summary']=[{k:v for k,v in b.items() if k in ['board_definition','n_board_rows','n_episodes','n_matured','n_winners','n_losers','win_rate','median_excess','n_locked_excluded','n_inflight','n_awaiting_t1','n_no_price']} for b in latest.get('loser_telemetry',{}).get('definitions',[])]
    report['blobs']=blobs
    (out/'price_source_hashes.json').write_text(json.dumps(price_source_hashes,sort_keys=True))
    report['price_hash_manifest_sha256']=hashlib.sha256((out/'price_source_hashes.json').read_bytes()).hexdigest()
    (out/'report.json').write_text(json.dumps(clean(report),indent=2,sort_keys=True,allow_nan=False))
    summary={k:report[k] for k in ['source_sha','episode_counts','panel_integrity','v4_vs_v3_shadow','latch_reconciliation']};summary['episode_h10']=[s for s in report['episode_horizons'] if s['horizon']==10];summary['baseline_h10_v4']=[s for s in report['baseline_comparison'] if s['horizon']==10 and s['board_definition']=='cn_prophet_v4']
    (out/'summary.json').write_text(json.dumps(clean(summary),indent=2,sort_keys=True,allow_nan=False))
    print('DONE',out,'REPORT_BYTES',(out/'report.json').stat().st_size,flush=True)

if __name__=='__main__':main()
