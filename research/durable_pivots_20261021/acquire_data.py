#!/usr/bin/env python3
"""Acquire a fixed, private research snapshot of public daily Yahoo OHLCV.

No production stores are changed. No credentials are used. A failed symbol is
recorded, never silently substituted. Existing successfully saved responses are
reused only when their retained digest verifies.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from curl_cffi import requests

GROUPS = {
    'us_index': 'SPY QQQ IWM DIA',
    'us_sector': 'XLK XLF XLE XLI XLY XLP XLU XLV XLB XLRE XLC SOXX',
    'us_stock': 'AAPL MSFT NVDA AMD INTC MU AMZN GOOGL META TSLA JPM XOM CVX CAT FCX NEM KO PEP WMT WM JNJ PFE',
    'commodity_proxy': 'GLD SLV USO',
    'rates_credit': 'TLT IEF HYG',
    'international_equity': 'EEM EFA EWJ FXI',
    'crypto': 'BTC-USD ETH-USD',
}
CUTOFF = '2026-10-08'

def acquire_one(item, out):
    symbol, group = item
    rawpath = out/'raw'/f'{symbol}.json'
    receiptpath = out/'raw'/f'{symbol}.receipt.json'
    if rawpath.exists() and receiptpath.exists():
        receipt = json.loads(receiptpath.read_text())
        raw = rawpath.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == receipt['response_sha256']
    else:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
        params = {'period1': int(datetime(1980,1,1,tzinfo=timezone.utc).timestamp()),
                  'period2': int(datetime(2026,10,9,tzinfo=timezone.utc).timestamp()),
                  'interval':'1d', 'events':'div,splits'}
        response = requests.get(url, params=params, impersonate='chrome', timeout=30)
        if response.status_code != 200:
            return {'ticker':symbol,'asset_class':group,'status':'FAILED',
                    'http_status':response.status_code,'error':response.text[:200]}
        raw = response.content
        receipt = {'url':url,'params':params,'acquired_at':datetime.now(timezone.utc).isoformat(),
                   'response_sha256':hashlib.sha256(raw).hexdigest(),'response_bytes':len(raw),
                   'http_status':response.status_code,'provider':'Yahoo Finance public chart',
                   'evidence_state':'RETROSPECTIVE_CURRENT_VINTAGE', 'credentials_used':False}
        rawpath.write_bytes(raw)
        receiptpath.write_text(json.dumps(receipt,indent=2))
    result = json.loads(raw)['chart']['result']
    if not result:
        return {'ticker':symbol,'asset_class':group,'status':'FAILED','error':'empty chart result'}
    x = result[0]
    tz = 'UTC' if group=='crypto' else x['meta'].get('exchangeTimezoneName','America/New_York')
    dates = pd.to_datetime(x['timestamp'],unit='s',utc=True).tz_convert(tz).tz_localize(None).normalize()
    d = pd.DataFrame(x['indicators']['quote'][0],index=dates)
    d.index.name='date'
    adj = x['indicators'].get('adjclose')
    d['adjclose'] = adj[0]['adjclose'] if adj else d['close']
    d = d.sort_index().loc[:CUTOFF]
    duplicate = int(d.index.duplicated().sum())
    if duplicate:
        return {'ticker':symbol,'asset_class':group,'status':'FAILED','error':'duplicate dates','count':duplicate}
    bad = (~np.isfinite(d[['open','high','low','close']])).any(axis=1) | (d[['open','high','low','close']]<=0).any(axis=1)
    bad |= (d.high<d.low) | (d.close<d.low-1e-5*d.close) | (d.close>d.high+1e-5*d.close)
    missing_dates = [str(v.date()) for v in d.index[bad]]
    d = d.loc[~bad].copy()
    target = out/'prices'/f'{symbol}.parquet'
    d.to_parquet(target)
    recent=d.loc['1995-01-01':]
    jumps=recent.close.pct_change()
    gaps=np.diff(d.index.values).astype('timedelta64[D]').astype(int)
    return {'ticker':symbol,'asset_class':group,'status':'OK','path':str(target.resolve()),
            'source_sha256':receipt['response_sha256'],'parquet_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'n_rows':len(d),'first':str(d.index.min().date()),'last':str(d.index.max().date()),
            'timezone':tz,'basis':'split_adjusted_dividend_unadjusted_OHLC; separate adjclose supplied',
            'bad_rows_excluded':len(missing_dates),'bad_dates':missing_dates,
            'gaps_over14_days':int((gaps>14).sum()),
            'moves_over30pct':[{'date':str(t.date()),'return':float(v)} for t,v in jumps[jumps.abs()>.3].items()],
            'source_receipt':str(receiptpath.resolve()),'current_vintage_not_point_in_time':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    for name in ['raw','prices']: (a.out/name).mkdir(parents=True,exist_ok=True)
    items=[(s,g) for g,ss in GROUPS.items() for s in ss.split()]
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        pending={ex.submit(acquire_one,item,a.out):item for item in items}
        for future in concurrent.futures.as_completed(pending):
            item=pending[future]
            try: row=future.result()
            except Exception as e: row={'ticker':item[0],'asset_class':item[1],'status':'FAILED','error':str(e)}
            rows.append(row)
            print(json.dumps({k:row.get(k) for k in ['ticker','status','n_rows','first','last','bad_rows_excluded','error']}),flush=True)
    order={s:i for i,(s,g) in enumerate(items)}; rows.sort(key=lambda r:order[r['ticker']])
    manifest={'study':'durable-pivot-confluence-20261021','cutoff':CUTOFF,'assets':rows,
              'selection':'fixed liquid surviving instrument cohort, chosen before outcomes',
              'survivorship_bias':True,'crypto_pooled_with_equities':False,
              'source_policy':'public provider, private research snapshot; no production mutation'}
    (a.out/'input_manifest.json').write_text(json.dumps(manifest,indent=2))
    print('COMPLETE',len(rows),'OK',sum(r['status']=='OK' for r in rows),flush=True)

if __name__=='__main__': main()
