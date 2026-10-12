"""Read-only BTC timing diagnostic, preregistered at 47d4eacf6a; no strategy fitting.
Writes only derived research evidence, never engine/config/data or provider state.
"""
from __future__ import annotations
import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import btc_inputs, btc_signals
from lib import config, store
OUT = Path(__file__).resolve().parent
SOURCES = ['config.yml', 'engine/btc_signals.py', 'engine/btc_inputs.py',
           'engine/btc_overrides.py', 'engine/btc_decision.py',
           'engine/btc_impulse_radar.py', 'engine/btc_intraday_cvd.py']
INPUTS = [('vector','signals'),('coinbase','btc_daily'),('yahoo','BTC-USD'),
          ('coinbase','btc_hourly'),('okx','taker_volume_hourly'),('bgeo','sopr'),
          ('bgeo','funding_rate'),('bgeo','open_interest_futures'),
          ('deribit','dvol'),('deribit','options_structure'),('farside','etf_flows')]
def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finite(v):
    return float(v) if pd.notna(v) and np.isfinite(v) else None

def main():
    data = Path(config.data_dir())
    paths = [data/g/(n+'.parquet') for g,n in INPUTS]
    before = {str(p.relative_to(data)):digest(p) for p in paths if p.exists()}
    source = {s:digest(ROOT/s) for s in SOURCES}
    cfg = config.load()['vector']; px = btc_inputs.load_price(); sig = store.read('vector','signals')
    if sig is None or sig.empty or len(px)<366:
        raise RuntimeError('Required baseline history unavailable')
    if not px.index.is_monotonic_increasing or px.index.has_duplicates:
        raise ValueError('Daily index must be monotone and unique')
    dates = px.index[-366:]; full = btc_signals.bottom_pressure(px)
    fn = inspect.getsource(btc_signals.bottom_pressure)
    old = 'c.resample("3D").last()'
    if fn.count(old)!=1:
        raise RuntimeError('Audited source changed; re-pin')
    scope = dict(vars(btc_signals))
    exec(compile(fn.replace(old,'c.resample("72h", origin=idx[0], closed="right", label="right").last()'),
                 '<research-only-completed-3d>','exec'),scope)
    completed = scope['bottom_pressure']; completed_full = completed(px)
    fm = btc_signals.momentum({'price':px},cfg['momentum'])
    fr = btc_signals.risk({'price':px},fm['momentum'],cfg['risk'])
    records=[]
    for i,dt in enumerate(dates):
        p=px.loc[:dt]; b=btc_signals.bottom_pressure(p).iloc[-1]; cb=completed(p).iloc[-1]
        m=btc_signals.momentum({'price':p},cfg['momentum'])
        r=btc_signals.risk({'price':p},m['momentum'],cfg['risk'])
        records.append({'date':dt.strftime('%Y-%m-%d'),'full_bottom_pressure':finite(full.loc[dt]),
          'prefix_bottom_pressure':finite(b),'bottom_delta':finite(full.loc[dt]-b),
          'completed_3d_delta':finite(completed_full.loc[dt]-cb),
          'price_only_momentum_delta':finite(fm.loc[dt,'momentum']-m['momentum'].iloc[-1]),
          'price_only_risk_delta':finite(fr.loc[dt,'risk_index']-r['risk_index'].iloc[-1])})
        if (i+1)%122==0: print(f'Checked {i+1}/366',flush=True)
    rows=pd.DataFrame(records); rows.to_csv(OUT/'r1_prefix_cutoffs.csv',index=False)
    audit={}
    for col in ['bottom_delta','completed_3d_delta','price_only_momentum_delta','price_only_risk_delta']:
        a=pd.to_numeric(rows[col],errors='coerce')
        audit[col]={'tested':len(a),'finite':int(a.notna().sum()),'changed':int((a.abs()>1e-12).sum()),'max_abs_difference':finite(a.abs().max())}
    # Sensitivity only: all other stored inputs and prior bottom history fixed.
    bp0=full.reindex(sig.index); bp1=bp0.copy()
    for row in records:
        dt=pd.Timestamp(row['date'])
        if dt in bp1.index: bp1.loc[dt]=row['prefix_bottom_pressure']
    a0=btc_signals.allocation(sig['momentum'],sig['risk_index'],cfg['allocation'],val=sig,close=sig['close'],bottom_sig=bp0)
    a1=btc_signals.allocation(sig['momentum'],sig['risk_index'],cfg['allocation'],val=sig,close=sig['close'],bottom_sig=bp1)
    sensitivity=[]
    for col in a0:
        d=(a0[col]-a1[col]).reindex(dates)
        sensitivity.append({'variant':col,'changed_dates':int((d.abs()>1e-12).sum()),'max_abs_allocation_pp':finite(d.abs().max()*100)})
    coverage=[]
    for (g,n),p in zip(INPUTS,paths):
        if not p.exists(): coverage.append({'source':f'{g}/{n}','available':False}); continue
        f=store.read(g,n); gaps=pd.DatetimeIndex(f.index).to_series().diff()
        coverage.append({'source':f'{g}/{n}','available':True,'rows':len(f),'columns':len(f.columns),
          'first':str(f.index.min()),'last':str(f.index.max()),
          'max_timestamp_gap_hours':finite(gaps.max()/pd.Timedelta(hours=1)),
          'publication_clock':'NOT_ESTABLISHED_BY_THIS_STORED_FRAME'})
    fields=[]
    for col in ['momentum','risk_index','bottom_pressure','mvrv_z','sopr_z90','funding_rate','oi_total_usd','dvol','skew_25d','gex_per_1pct_usd','etf_flow_usd_mn','macro_score','coinbase_premium','taker_buy_share']:
        if col not in sig: fields.append({'field':col,'present':False}); continue
        s=sig[col]; v=s.dropna()
        fields.append({'field':col,'present':True,'nonnull':len(v),'first':str(v.index.min()) if len(v) else None,
                       'last':str(v.index.max()) if len(v) else None,'trailing_90_nonnull':int(s.tail(90).notna().sum())})
    if before!={str(p.relative_to(data)):digest(p) for p in paths if p.exists()} or source!={s:digest(ROOT/s) for s in SOURCES}:
        raise RuntimeError('Input/source changed during audit; evidence not accepted')
    demo=pd.Series([100.,101.,20.,30.,40.,50.],index=pd.date_range('2026-01-01',periods=6))
    result={'classification':'TEMPORAL_DIAGNOSTIC_NOT_STRATEGY_VALIDATION',
      'preregistration_commit':'47d4eacf6abd98055a085a779e9df75fee567d18',
      'execution_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'script_sha256':digest(__file__),'runtime':{'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__},'source_sha256':source,'input_sha256':before,'input_and_source_unchanged':True,
      'period':[str(dates.min().date()),str(dates.max().date())],'prefix_audit':audit,'allocation_sensitivity':sensitivity,
      'allocation_limit':'Raw-allocation sensitivity only; fixed stored momentum/risk/valuation; no PnL or live-decision assertion.',
      'counterfactual_limit':'One research-only completed-date 3D grouping; no production patch or profitability selection.',
      'synthetic_label_demo':{str(k.date()):float(v) for k,v in demo.resample('3D').last().items()},
      'coverage':coverage,'signal_fields':fields}
    (OUT/'r1_audit.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['period','prefix_audit','allocation_sensitivity','input_and_source_unchanged']},indent=2))
if __name__=='__main__': main()
