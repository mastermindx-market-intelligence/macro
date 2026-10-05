"""Run R3 research on immutable, explicitly allowed source/data blobs.

Reads no axes.py, regime.py, inputs.py or risk_radar_backtest.py. No live imports,
no network, no source/data-store writes. Out is a new research-only directory.
"""
from __future__ import annotations
import argparse
import ast
from io import BytesIO
import hashlib
import json
import logging
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal
from r3 import archive_asof,endpoint_at,future_path,cross_table

PIN='f6dae649ee6d32ec65a95ccea411b205d0b0bc45'
PREREG='c3f2f5e4ee0419d8b059231a394f347467e7f476'
END='2026-09-25'
SOURCE_HASH='7671e86ae2cce28f83a83054ad76c4920638f68a28a92af074dbf28c054d95eb'
HISTORY_HASH='5003f8c9a75fe3a9ae47a50384d72377ef187c4d6fc69eeb8ff7246de25558d3'
CASES=['2008-09-12','2020-02-19','2020-03-09','2020-03-23','2021-05-10','2022-01-03','2022-10-14','2023-03-08','2023-03-13','2023-05-01','2024-08-02','2025-04-02']
REPLAY_EXTRA=['2020-02-19','2020-02-28','2020-03-09','2020-03-23','2020-04-06','2021-05-10','2021-06-30','2022-10-14','2023-03-08','2023-03-13']


def read_blob(repo,path,expected=None):
    p=subprocess.run(['git','-C',str(repo),'show',PIN+':'+path],capture_output=True)
    if p.returncode:raise FileNotFoundError(path)
    raw=p.stdout;h=hashlib.sha256(raw).hexdigest()
    if expected and h!=expected:raise ValueError('unexpected source hash: '+path)
    return raw,{'path':path,'sha256':h,'bytes':len(raw)}


class GaussianReference:
    """Only the Gaussian emission density dependency; no alternative HMM fit."""
    def __init__(self,**kwargs):pass
    def _compute_log_likelihood(self,X):
        return np.column_stack([multivariate_normal.logpdf(X,mean=m,cov=c)
                                for m,c in zip(self.means_,self.covars_)])


def existing_endpoint(source):
    tree=ast.parse(source)
    keep=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_causal_filtered_pquad','_logsumexp')]
    if len(keep)!=2:raise ValueError('source endpoint functions missing')
    class DensityDependency(ast.NodeTransformer):
        def visit_ImportFrom(self,node):
            if node.module=='hmmlearn.hmm':return ast.copy_location(ast.Pass(),node)
            return node
    isolated=DensityDependency().visit(ast.Module(body=keep,type_ignores=[]));ast.fix_missing_locations(isolated)
    def no_missing_label(*args):raise ValueError('source labels required; no alternate quad formula')
    ns={'np':np,'pd':pd,'GaussianHMM':GaussianReference,'log':logging.getLogger('r3'),
        '_QUADS':('Q1','Q2','Q3','Q4'),'raw_quad':no_missing_label}
    exec(compile(isolated,'pinned_engine_regime_one','exec'),ns)
    return ns['_causal_filtered_pquad']


def recipient_audit(series):
    idx=series['SPY'].index;idx=idx[idx<=END]
    aligned={k:s.reindex(idx) for k,s in series.items()}
    outputs={};cases={};start=idx.searchsorted(pd.Timestamp('2007-01-01'))
    grid=np.zeros(len(idx),bool);grid[start::21]=True
    for threshold in [.05,.10]:
        paths={k:future_path(v,21,threshold) for k,v in aligned.items()}
        table=pd.DataFrame({k:v.event for k,v in paths.items()})
        common=table.notna().all(axis=1)&(idx>='2007-01-01')
        strata={'full':common,'nonoverlap_21':common&grid,
                'pre_KRE_index_change':common&(idx<'2011-10-24'),
                'post_KRE_index_change':common&(idx>='2011-10-24')}
        for y in range(2007,2027):strata[str(y)]=common&(idx.year==y)
        outputs[str(threshold)]={}
        for name,mask in strata.items():
            outputs[str(threshold)][name]={k:cross_table(table.loc[mask,'SPY'],table.loc[mask,k]) for k in aligned if k!='SPY'}
        if threshold==.05:
            for day in CASES:
                t=pd.Timestamp(day)
                if t not in idx:cases[day]={'status':'no_session'};continue
                cases[day]={k:{c:(None if pd.isna(v.loc[t,c]) else float(v.loc[t,c]))
                               for c in ['future_min_return','terminal_return','event','current_drawdown']} for k,v in paths.items()}
            # Independent loop oracle, including full-horizon maturity and missing slots.
            mismatches=0
            for asset,s in aligned.items():
                a=s.to_numpy(dtype=float);actual=paths[asset].event.to_numpy()
                for i in range(len(a)):
                    window=a[i:i+22]
                    exp=np.nan if len(window)!=22 or not (np.isfinite(window)&(window>0)).all() else float(np.min(window[1:])/window[0]-1<=-.05)
                    if not ((np.isnan(exp) and np.isnan(actual[i])) or exp==actual[i]):mismatches+=1
    return {'comparison':'recipient outcomes, not signal accuracy or bank-run diagnosis',
            'tables':outputs,'cases':cases,'independent_label_mismatches':mismatches,
            'common_sample_requires':list(aligned),'calendar':'SPY observed sessions; no fill'}


def main(repo,out):
    out.mkdir(parents=True,exist_ok=False)
    study={'schema':'r3_reconstruction_recipients.v1','source_pin':PIN,'protocol_commit':PREREG,
           'authority':'NONE','original_incumbent_comparison':'NOT_RUN_SOURCE_INSPECTION_BLOCKED','inputs':[]}
    source,meta=read_blob(repo,'engine/regime_one.py',SOURCE_HASH);study['inputs'].append(meta)
    raw,meta=read_blob(repo,'data/regime/regime_history.parquet',HISTORY_HASH);study['inputs'].append(meta)
    df=pd.read_parquet(BytesIO(raw));df=df.loc[:END,['growth_score','inflation_score','quad']].copy()
    # Assumed date-label availability for parameter-only diagnostics, NOT a real source clock.
    df['available_at']=pd.to_datetime(df.index,utc=True)+pd.Timedelta(hours=23)
    native=existing_endpoint(source.decode())
    dates=set(str(g.index[-1].date()) for _,g in df.loc['2015-01-01':].groupby(df.loc['2015-01-01':].index.to_period('Q')))
    dates.update(REPLAY_EXTRA);dates=sorted(dates)
    rows=[];prefix_checks=[]
    for j,day in enumerate(dates):
        decision=day+'T23:59:59Z';r=endpoint_at(df,decision,native)
        rows.append(r)
        # Actual-source double execution at prespecified audit dates only.
        if day in ['2020-03-09','2021-05-10','2023-03-13']:
            short=endpoint_at(df.loc[:day],decision,native)
            prefix_checks.append({'day':day,'identical':r==short})
        if j%10==0:print('REPLAY',j+1,'of',len(dates),flush=True)
    pd.DataFrame([{**{k:r[k] for k in ['decision_at','score_asof','fit_cutoff','knowledge_sha256','status']},**(r['probabilities'] or {})} for r in rows]).to_csv(out/'parameter_replay.csv',index=False)
    study['reconstruction']={'assessment_dates':len(rows),'status_counts':pd.Series([r['status'] for r in rows]).value_counts().to_dict(),
                             'prefix_checks':prefix_checks,'time_contract_violations':sum(1 for r in rows if r['fit_cutoff'] and pd.Timestamp(r['fit_cutoff'])>pd.Timestamp(r['decision_at']).tz_localize(None)),
                             'evidence':'PARAMETER_ONLY_DIAGNOSTIC; legacy scores are not vintage-qualified',
                             'dependency':'original fitting/recursion; SciPy Gaussian emission reference, not full production parity',
                             'sample':{day:rows[dates.index(day)] for day in REPLAY_EXTRA if day in dates}}
    study['macro_knowledge_checks']=[]
    for sid,expected in [('PAYEMS','5fe02dde232efad7799d14b5331bd83d4ba2f849dc82e687bd49ade357debaee'),('CPIAUCSL','abc6b65a873a3d6de63d85379c86b61f71f99480354f46915c391d506970718b')]:
        raw,meta=read_blob(repo,f'data/fred_vintage/release_targets/{sid}_all_vintages.parquet',expected);study['inputs'].append(meta)
        d=pd.read_parquet(BytesIO(raw));checks=[]
        for day in CASES:
            a=archive_asof(d,sid,day)
            earlier=d.loc[pd.to_datetime(d.realtime_start)<pd.Timestamp(day)]
            b=archive_asof(earlier,sid,day)
            # Oracle: full output-type-2 vintage snapshot directly, when archive is full.
            direct=earlier.loc[earlier.realtime_start==earlier.realtime_start.max()].sort_values('period')
            direct_levels={pd.Timestamp(p).date().isoformat():float(v) for p,v in zip(direct.period,direct.value)}
            checks.append({'decision':day,'prefix_identical':a==b,'direct_vintage_identical':a['levels']==direct_levels,
                           'period_count':len(a['levels']),'last_publication_date':a['last_publication_date'],'knowledge_sha256':a['knowledge_sha256']})
        study['macro_knowledge_checks'].append({'series':sid,'checks':checks})
    # Read and fingerprint all recipient inputs before any recipient outcome is built.
    recipient={};missing=[]
    for ticker in ['SPY','KRE','XLF']:
        try:raw,meta=read_blob(repo,f'data/yahoo/{ticker}.parquet')
        except FileNotFoundError:missing.append(ticker);continue
        d=pd.read_parquet(BytesIO(raw));meta.update(rows=len(d),columns=list(d.columns),start=str(d.index.min()),end=str(d.index.max()))
        study['inputs'].append(meta);print('RECIPIENT_INPUT',json.dumps(meta),flush=True)
        if 'close' not in d:missing.append(ticker);continue
        s=d['close'].sort_index().loc[:END]
        if s.index.has_duplicates:raise ValueError('duplicate recipient sessions')
        recipient[ticker]=s
    study['missing_recipients']=missing
    study['recipients']=recipient_audit(recipient) if 'SPY' in recipient and len(recipient)>1 else {'status':'unavailable'}
    study['all_input_hashes_rechecked']=all(read_blob(repo,m['path'],m['sha256'])[1]['sha256']==m['sha256'] for m in study['inputs'])
    study['script_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('r3.py')]}
    (out/'results.json').write_text(json.dumps(study,indent=2,allow_nan=False)+'\n')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())}
    (out/'output_manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('R3_DONE',json.dumps(hashes),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.repo_root,a.out)
