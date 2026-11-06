#!/usr/bin/env python3
"""Add benchmark sensitivity, ledger-vintage checks and compact handoff evidence.
Read-only against pinned git objects; writes only to the explicitly supplied folder.
Run after autopsy.py. This never changes any recorded fill or production artifact.
"""
from __future__ import annotations
import argparse, hashlib, io, json, subprocess
from pathlib import Path
import pandas as pd
import numpy as np
from autopsy import SHA, DEFAULT_REPO, describe, clean

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default=DEFAULT_REPO);ap.add_argument('--out',required=True);a=ap.parse_args();p=Path(a.out)
    def data(path):return subprocess.check_output(['git','-C',a.repo,'show',SHA+':'+path])
    def parquet(path):return pd.read_parquet(io.BytesIO(data(path)))
    j=json.loads((p/'report.json').read_text());board=parquet('data/china_standout_track/board.parquet');latch=parquet('data/china_standout_track/entry_latch.parquet');cand=parquet('data/china_prophet_rank/candidates.parquet');bench=parquet('data/china/510300.SS.parquet');bench500=parquet('data/china/510500.SS.parquet');cal=bench.index
    returns=pd.read_csv(p/'episode_horizon_returns.csv');episodes=pd.read_csv(p/'episodes_issuance.csv');prod=pd.read_csv(p/'production_h10_reconciliation.csv')
    alt=returns[returns.status=='observed'].copy()
    for i,r in alt.iterrows():
        e,x=pd.Timestamp(r.entry_date),pd.Timestamp(r.exit_date)
        if e in bench500.index and x in bench500.index:alt.at[i,'excess_csi500']=r.pnl_cc-(float(bench500.loc[x,'close'])/float(bench500.loc[e,'close'])-1)*100
    extra={'source_sha':SHA,'benchmark_sensitivity':[]}
    for (definition,h),g in alt.groupby(['board_definition','horizon']):
        s=describe(g,'excess_csi500');s.update(board_definition=definition,horizon=int(h));extra['benchmark_sensitivity'].append(s)
    extra['benchmark_clock_only_counterfactual']={'status':'UNIDENTIFIABLE','benchmark_path':'data/china/510300.SS.parquet','benchmark_columns':list(bench.columns),'benchmark_rows':len(bench),'common_cohort_valid_benchmark_open_n':0,'stock_open_h10_matured_n':int(((prod.basis_used=='t1_open')&prod.excess.notna()).sum()),'stock_open_h10_v4_matured_n':int(((prod.basis_used=='t1_open')&(prod.board_definition=='cn_prophet_v4')&prod.excess.notna()).sum()),'required':'Versioned benchmark open/high/low on the same basis for exact fixed stock entry/exit dates; daily bars cannot timestamp HL2 fills. No clock delta is estimated.'}
    v4=returns[(returns.board_definition=='cn_prophet_v4')&(returns.status=='observed')&(returns.horizon.isin([1,3,5,10,20]))];keys=v4.groupby(['date','ticker']).horizon.nunique();common_keys=set(keys[keys==5].index);common_v4=v4[pd.Series([(d,t) in common_keys for d,t in zip(v4.date,v4.ticker)],index=v4.index)];extra['v4_common_matured_horizon_cohort']=[dict(describe(g),horizon=int(h)) for h,g in common_v4.groupby('horizon')]
    extra['turnover']=[]
    for definition,g in board.groupby('board_definition'):
        prev=None;dates=[]
        for d,q in g.groupby('date'):
            cur=set(q.ticker)
            if prev is not None:dates.append({'date':d,'new_share':len(cur-prev)/len(cur),'jaccard':len(cur&prev)/len(cur|prev),'n_current':len(cur),'n_new':len(cur-prev)})
            prev=cur
        e=episodes[episodes.board_definition==definition].sort_values('date');overlap=0
        for t,q in e.groupby('ticker'):
            ix=cal.searchsorted(pd.to_datetime(q.date));overlap+=int(((np.diff(ix)>0)&(np.diff(ix)<=10)).sum())
        extra['turnover'].append({'board_definition':definition,'n_transitions':len(dates),'mean_new_share':np.mean([d['new_share'] for d in dates]) if dates else None,'median_jaccard':np.median([d['jaccard'] for d in dates]) if dates else None,'episodes':len(e),'unique_tickers':e.ticker.nunique(),'repeat_episode_count':len(e)-e.ticker.nunique(),'readmissions_within10_market_sessions':overlap})
    extra['regime_slices']=[]
    r10=returns[(returns.horizon==10)&(returns.status=='observed')].merge(episodes[['date','ticker','board_definition','own_market_regime']],on=['date','ticker','board_definition'],how='left')
    for (definition,regime),g in r10.groupby(['board_definition','own_market_regime'],dropna=False):
        s=describe(g);s.update(board_definition=definition,regime=str(regime));extra['regime_slices'].append(s)
    f=pd.DataFrame(j.pop('feature_coverage'));feature_summary=[]
    for (d,h,scope,feat),g in f.groupby(['definition','horizon','scope','feature']):feature_summary.append({'definition':d,'horizon':int(h),'scope':scope,'feature':feat,'n_rows':int(g.n.sum()),'non_null':int(g.non_null.sum()),'dates':len(g),'zero_coverage_dates':g.loc[g.non_null==0,'date'].tolist(),'fully_covered_dates':int((g.n==g.non_null).sum())})
    j['feature_coverage_summary']=feature_summary
    m=pd.DataFrame(j.pop('sector_liquidity_matching_gaps'));matching=[]
    for (d,h),g in m.groupby(['definition','horizon']):matching.append({'definition':d,'horizon':int(h),'dates':len(g),'dates_all6_slots_match':int((g.same_sector_liquidity_matched_slots==6).sum()),'matched_slots':int(g.same_sector_liquidity_matched_slots.sum()),'total_slots':int(g.featured_n.sum()),'note':'Exclude original featured top6; same recorded sector and 0.5x-2x recorded ADV. Slot coverage only, not a simulated portfolio or independence claim.'})
    j['sector_liquidity_matchability']=matching
    checks=j.pop('selection_before_outcome_checks');c=pd.DataFrame(checks);selection=[]
    for (d,h,scope,label),g in c.groupby(['definition','horizon','scope','baseline']):selection.append({'definition':d,'horizon':int(h),'scope':scope,'baseline':label,'selection_attempts':len(g),'membership_changes_if_observed_first':int(g.changed_if_selecting_observed_first.sum()),'complete_frozen_dates':int(g.frozen_selection_mean_pct.notna().sum()),'rejected_observed_first_dates':int(g.rejected_observed_first_mean_pct.notna().sum()),'complete_frozen_mean_pct':g.frozen_selection_mean_pct.mean(),'rejected_observed_first_mean_pct':g.rejected_observed_first_mean_pct.mean(),'common_complete_max_abs_difference':(g.frozen_selection_mean_pct-g.rejected_observed_first_mean_pct).abs().max()})
    j['selection_before_outcome_summary']=selection;j['selection_changed_examples']=[r for r in checks if r['changed_if_selecting_observed_first'] and r['scope']!='raw_eligible_illustrative' and r['horizon']==10]
    missing=cand[cand.ticker.isin(j['missing_price_tickers'])];extra['missing_price_candidate_coverage']={'rows':len(missing),'tickers':j['missing_price_tickers'],'raw_eligible_rows':int((missing.raw_eligible==True).sum()),'cap_qualified_rows':int(((missing.lane=='featured')|((missing.lane=='more_actionable')&missing.lane_reasons.isin(['featured_cap','sector_cap']))).sum()),'by_ticker':{t:{'rows':len(g),'raw_eligible':int((g.raw_eligible==True).sum()),'lanes':g.lane.value_counts().to_dict()} for t,g in missing.groupby('ticker')},'handling':'No-price placeholders retained in candidate outcome denominators; never substituted with another ticker.'}
    radar=parquet('data/china_radar/ledger.parquet');ic=json.loads(data('data/china_hub/radar_ic.json'))
    extra['radar_separate_instrument']={'rows':len(radar),'sector_rows':int(radar.sector_etf.notna().sum()),'venue_rows':int(radar.sector_etf.isna().sum()),'dates':radar.fired_date.nunique(),'max_events_per_date':int(radar.groupby('fired_date').size().max()),'non_csi300_session_rows':int((~pd.to_datetime(radar.fired_date).isin(cal)).sum()),'ic_payload':ic}
    old=json.loads(data('research/china_alpha/w5/w5a_rederive_stats.json'));battery=json.loads(data('research/cn_prophet_audit/rank_feature_battery_results.json'))
    extra['historical_research_not_reexecuted']={'w5':old,'rank_battery':{'reproduction':battery['reproduction'],'multiplicity':battery['multiplicity'],'top8_feature_ladder':battery['ordering_ladder_by_abs_demeaned_ic_on_excess_h10'][:8],'scoil_h10':{arm:{context:metrics['H10'] for context,metrics in contexts.items() if 'H10' in metrics} for arm,contexts in battery['part_b_scoil_cn_retro']['arms'].items()}}}
    extra['publication_clock_limits']={'board_rows_with_recorded_utc_publication':0,'candidate_rows_with_recorded_utc_publication':0,'latch_first_recorded_timestamp':str(latch.latched_asof.min()),'latch_rows_before_first_recorded_timestamp_date':int((pd.to_datetime(latch.date)<pd.to_datetime(latch.latched_asof.min()).normalize().tz_localize(None)).sum()),'shallow_git':subprocess.check_output(['git','-C',a.repo,'rev-parse','--is-shallow-repository'],text=True).strip(),'note':'Only dates are persisted on issuance rows. Existing field names and shallow reachable history cannot prove first-publication UTC, eligible constituent membership at issuance, or original price vintages.'}
    delta=pd.read_csv(p/'latch_deltas.csv');extra['v4_latch_sign_changes']=prod[(prod.board_definition=='cn_prophet_v4')&prod.excess.notna()&prod.latch_excess.notna()&((prod.excess>0)!=(prod.latch_excess>0))][['date','ticker','entry','latched_entry','excess','latch_excess','fresh_vs_latch_pct']].to_dict('records')
    extra['source_blobs']={path:{'sha256':hashlib.sha256(data(path)).hexdigest()} for path in ['data/china/510500.SS.parquet','data/china_radar/ledger.parquet','data/china_hub/radar_ic.json','research/cn_prophet_audit/rank_feature_battery_results.json','research/china_alpha/w5/w5a_rederive_stats.json']}
    def matrix(d):return {'columns':list(d.columns),'data':d.to_numpy().tolist()}
    review={'episode_rows':matrix(returns[(returns.board_definition=='cn_prophet_v4')&(returns.horizon.isin([1,3,5,10,20]))][['date','ticker','horizon','status','entry_date','exit_date','board_rank','prophet_score','pnl_cc','benchmark_cc','excess_cc','mae_close']]),'production_h10':matrix(prod[prod.board_definition=='cn_prophet_v4'][['date','ticker','board_rank','basis_used','entry','latched_entry','t1_date','exit_date','pnl','excess','latch_excess']])}
    br=pd.read_csv(p/'baseline_date_returns.csv');review['baseline_dates']=matrix(br[(br.board_definition=='cn_prophet_v4')&(br.horizon==10)&(br.scope!='raw_eligible_illustrative')]);(p/'v4_review_rows.json').write_text(json.dumps(clean(review),separators=(',',':'),allow_nan=False))
    compact={'autopsy':j,'extensions':extra};raw=json.dumps(clean(compact),separators=(',',':'),allow_nan=False);(p/'historical_evidence.json').write_text(raw)
    manifest={x.name:{'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in sorted(p.iterdir()) if x.is_file() and x.name!='manifest.json'}
    (p/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True));print('DONE',p/'historical_evidence.json','bytes',len(raw))

if __name__=='__main__':main()
