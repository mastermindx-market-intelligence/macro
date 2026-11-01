"""Read retained research inputs and optionally acquire the missing public prices.

No production data writes. Original raw responses are not published. The V11
archive's indicator functions are extracted verbatim, with their source hash.
"""
from __future__ import annotations
import argparse, ast, concurrent.futures, hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

CORE = ['MCD', 'WMT', 'WM', 'COST', 'PG']
PEERS = ['RSG', 'KO', 'PEP', 'CL', 'CHD', 'KMB', 'MDLZ', 'HSY', 'CLX', 'JNJ', 'ADP', 'CTAS', 'KR']
SECTORS = ['XLK', 'XLF', 'XLE', 'XLI', 'XLY', 'XLP', 'XLU', 'XLV', 'XLB', 'XLRE', 'XLC', 'SOXX']
ARCHIVE_SHA = '97966f72ea15cb34e0f5453252eef683411c894b7ca4432de4ce7c540d1ffaf0'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def acquire(symbol, out):
    from curl_cffi import requests
    rawpath = out / 'raw' / f'{symbol}.json'
    receiptpath = out / 'raw' / f'{symbol}.receipt.json'
    if rawpath.exists() or receiptpath.exists():
        if not (rawpath.exists() and receiptpath.exists()):
            raise ValueError(f'Incomplete retained acquisition {symbol}')
        receipt = json.loads(receiptpath.read_text())
        assert sha(rawpath) == receipt['response_sha256']
        raw = rawpath.read_bytes()
    else:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
        params = {'period1': 1262304000, 'period2': 1791504000, 'interval': '1d', 'events': 'div,splits'}
        response = requests.get(url, params=params, impersonate='chrome', timeout=30)
        if response.status_code != 200:
            raise ValueError(f'{symbol} HTTP {response.status_code}: {response.text[:120]}')
        raw = response.content
        receipt = {'url': url, 'params': params, 'acquired_at': datetime.now(timezone.utc).isoformat(),
                   'response_sha256': hashlib.sha256(raw).hexdigest(), 'response_bytes': len(raw),
                   'provider': 'Yahoo Finance public chart', 'credentials_used': False,
                   'evidence_state': 'RETROSPECTIVE_CURRENT_VINTAGE'}
        rawpath.write_bytes(raw)
        receiptpath.write_text(json.dumps(receipt, indent=2))
    x = json.loads(raw)['chart']['result'][0]
    dates = pd.to_datetime(x['timestamp'], unit='s', utc=True).tz_convert('America/New_York').normalize().tz_localize(None)
    d = pd.DataFrame(x['indicators']['quote'][0], index=dates)
    d['adjclose'] = x['indicators']['adjclose'][0]['adjclose']
    d = d.loc['2010-01-04':'2026-10-08'].sort_index()
    assert d.index.is_unique
    assert np.isfinite(d[['open', 'high', 'low', 'close', 'adjclose']]).all().all()
    assert (d[['open', 'high', 'low', 'close', 'adjclose']] > 0).all().all()
    assert (d.high + 1e-5*d.close >= d[['open', 'close', 'low']].max(axis=1)).all()
    assert (d.low - 1e-5*d.close <= d[['open', 'close', 'high']].min(axis=1)).all()
    target = out / 'prices' / f'{symbol}.parquet'
    d.index.name = 'date'
    d.to_parquet(target)
    return {'ticker': symbol, 'path': str(target.resolve()), 'parquet_sha256': sha(target),
            'source_sha256': receipt['response_sha256'], 'n_rows': len(d),
            'first': str(d.index[0].date()), 'last': str(d.index[-1].date()),
            'source_kind': 'new_public_reconstruction', 'source_receipt': str(receiptpath.resolve())}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base-data', type=Path, required=True)
    p.add_argument('--base-events', type=Path, required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--acquire-missing-public', action='store_true')
    a = p.parse_args()
    root = Path(__file__).resolve().parent
    for n in ['raw', 'prices', 'archive']:
        (a.out/n).mkdir(parents=True, exist_ok=True)
    assert sha(a.archive) == ARCHIVE_SHA
    with zipfile.ZipFile(a.archive) as z:
        src = z.read('source/empirical.py').decode()
        tree = ast.parse(src)
        names = ['NativeState', 'snapshots', 'episodes']
        definitions = [ast.get_source_segment(src, n) for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
        assert len(definitions) == len(names)
        header = ('"""Verbatim V11 native mechanics, extracted from the archived empirical.py.\n'
                  f'Archive SHA256: {ARCHIVE_SHA}\nSource SHA256: {hashlib.sha256(src.encode()).hexdigest()}\n"""\n'
                  'from copy import deepcopy\nfrom collections import deque\nimport numpy as np\nimport pandas as pd\nNA = float("nan")\n\n')
        (root/'vendor_v11_native.py').write_text(header + '\n\n'.join(definitions) + '\n')
        for n in ['signal_state_events.csv', 'core_episode_ledger_complete_metadata.csv', 'stress_transition_events.csv']:
            (a.out/'archive'/n).write_bytes(z.read('results/'+n))
    base_manifest = a.base_data/'input_manifest.json'
    base = {r['ticker']: r for r in json.loads(base_manifest.read_text())['assets'] if r['status']=='OK'}
    items, missing = [], []
    for s in CORE + PEERS + ['SPY'] + SECTORS:
        if s in base:
            r = dict(base[s]); f=Path(r['path'])
            assert sha(f)==r['parquet_sha256']
            r['source_kind']='retained_oct21_pivot_snapshot'
            items.append(r)
        else:
            missing.append(s)
    if missing and not a.acquire_missing_public:
        raise ValueError('Missing public inputs; explicit acquisition flag required: '+','.join(missing))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(acquire,s,a.out):s for s in missing}
        for f in concurrent.futures.as_completed(jobs):
            row=f.result(); items.append(row)
            print(json.dumps({k:row[k] for k in ['ticker','n_rows','first','last','source_kind']}),flush=True)
    manifest={'created_at':datetime.now(timezone.utc).isoformat(), 'cutoff':'2026-10-08',
              'base_manifest_sha256':sha(base_manifest), 'archive_sha256':ARCHIVE_SHA,
              'base_events_path':str(a.base_events.resolve()), 'base_events_sha256':sha(a.base_events),
              'assets':sorted(items,key=lambda r:r['ticker']), 'survivorship_bias':True,
              'basis':'raw split-adjusted OHLC plus adjclose; adjusted OHLC used as total-return proxy',
              'original_v11_raw_retained':False, 'point_in_time_qualified':False}
    (a.out/'input_manifest.json').write_text(json.dumps(manifest,indent=2))
    (root/'results').mkdir(exist_ok=True)
    public={k:v for k,v in manifest.items() if k!='base_events_path'}
    public['assets']=[{k:v for k,v in r.items() if k not in ['path','source_receipt']} for r in manifest['assets']]
    (root/'results'/'input_provenance.json').write_text(json.dumps(public,indent=2))
    print('PREPARED',len(items),'ASSETS',flush=True)

if __name__=='__main__':
    main()
