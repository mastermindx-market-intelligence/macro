"""Public input acquisition. Never retain/convert out-of-block observations."""
from pathlib import Path
import csv, io, json, zipfile, urllib.request, hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
START, END = '2013-01-02', '2023-12-29'
UA = {'User-Agent': 'Mozilla/5.0 (public historical research)'}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()

def french(n):
    url = f'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{n}_Industry_Portfolios_Daily_CSV.zip'
    z = zipfile.ZipFile(io.BytesIO(get(url)))
    rows, header, entered = [], None, False
    with z.open(z.namelist()[0]) as src:
        for raw in src:
            line = raw.decode('utf-8-sig').strip()
            fields = [s.strip() for s in line.split(',')]
            if not entered and len(fields) == n+1 and fields[0] == '' and all(fields[1:]):
                header = fields[1:]
            if header and fields[0].isdigit() and len(fields[0]) == 8:
                entered = True
                # Inspect only the date before reading any numeric return field.
                d = fields[0]
                if not '20130102' <= d <= '20231229':
                    continue
                vals = [float(x) for x in fields[1:]]
                rows.append([f'{d[:4]}-{d[4:6]}-{d[6:]}'] + [None if x in (-99.99, -999) else x/100 for x in vals])
            elif entered:
                break  # Value-weighted daily section only.
    if header is None or len(rows) < 2500:
        raise RuntimeError(f'French parse failure: {n}, {len(rows)} rows')
    df = pd.DataFrame(rows, columns=['date'] + header).set_index('date')
    return f'ff{n}.csv', df, url

def yahoo(ticker):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1=1357084800&period2=1703980800&interval=1d&events=div%2Csplits'
    obj = json.loads(get(url))['chart']['result'][0]
    times = obj['timestamp']
    adj = obj['indicators']['adjclose'][0]['adjclose']
    close = obj['indicators']['quote'][0]['close']
    rows = []
    for i, stamp in enumerate(times):
        d = datetime.fromtimestamp(stamp, timezone.utc).strftime('%Y-%m-%d')
        if START <= d <= END:
            rows.append((d, adj[i], close[i]))
    df = pd.DataFrame(rows, columns=['date', 'adjclose', 'close']).set_index('date')
    if df.empty or df.index.has_duplicates:
        raise RuntimeError(f'Yahoo invalid {ticker}')
    return f'{ticker}.csv', df, url

def fred(series):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={START}&coed={END}'
    rows = []
    # Date-filter before numeric conversion, even if the server ignores date bounds.
    for row in csv.DictReader(io.StringIO(get(url).decode())):
        d = row.get('observation_date', row.get('DATE'))
        if d and START <= d <= END:
            v = row[series]
            rows.append((d, None if v in ('.', '') else float(v)))
    df = pd.DataFrame(rows, columns=['date', series]).set_index('date')
    if series == 'BAMLH0A0HYM2' and (df.empty or df.index.min() > START):
        # Public preserved FRED CSV, pinned by Git commit. No access control is bypassed.
        archive = 'https://raw.githubusercontent.com/chatterjee-aryan/macro_regime_modeling/4e6529620a0a73d8288f4f70af74c2bd8d275352/data/BAMLH0A0HYM2.csv'
        earlier = 'https://raw.githubusercontent.com/hrithikRag/Optimizing-SP-500-Investment-Timing-A-Multi--Indicator-Approach/6922419cdf65924d472b683236229701813b03b2/BAMLH0A0HYM2.csv'
        def parse_archive(u):
            vals=[]
            for row in csv.DictReader(io.StringIO(get(u).decode())):
                d=row.get('observation_date',row.get('DATE'))
                if d and START <= d <= END:
                    v=row[series];vals.append((d,None if v in ('.','') else float(v)))
            return pd.DataFrame(vals,columns=['date',series]).set_index('date')
        full=parse_archive(archive);old=parse_archive(earlier)
        checks=[]
        for name,check in [('pre2024_public_archive',old),('current_FRED_overlap',df)]:
            both=full.join(check,rsuffix='_check',how='inner').dropna()
            gap=(both[series]-both[series+'_check']).abs()
            if len(both)==0 or gap.max()>1e-9:raise RuntimeError('HY archive verification failed '+name)
            checks.append({'against':name,'matching_nonmissing_rows':len(both),'maximum_absolute_difference':float(gap.max())})
        (ROOT/'results'/'hy_archive_verification.json').write_text(json.dumps({'primary_FRED_url':url,'archive_url':archive,
            'pre2024_crosscheck_url':earlier,'checks':checks,'warning':'Public FRED-origin archived CSV; not an independently proven point-in-time feed.'},indent=2))
        df=full;url=archive
    if df.empty:
        raise RuntimeError(f'FRED empty {series}')
    return f'{series}.csv', df, url

def main():
    DATA.mkdir(exist_ok=True)
    tasks = [(french, 12), (french, 49)]
    tasks += [(yahoo, t) for t in 'SPY XLB XLE XLF XLI XLK XLP XLU XLV XLY XLRE XLC'.split()]
    tasks += [(fred, t) for t in 'DGS2 DGS10 BAMLH0A0HYM2 DTWEXB DTWEXBGS VIXCLS'.split()]
    manifest = {'allowed_start': START, 'allowed_end': END, 'observations_outside_block_retained': 0,
                'vintage': 'public current-vintage histories; no point-in-time vintage proof', 'inputs': []}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(f, arg) for f, arg in tasks]
        for future in futures:
            filename, df, url = future.result()
            assert df.index.min() >= START and df.index.max() <= END
            out = DATA / filename
            df.to_csv(out, float_format='%.12g')
            manifest['inputs'].append({'file': filename, 'url': url, 'rows': len(df),
                'first': df.index.min(), 'last': df.index.max(), 'missing_values': int(df.isna().sum().sum()),
                'sha256': hashlib.sha256(out.read_bytes()).hexdigest()})
            print(filename, len(df), df.index.min(), df.index.max(), 'missing', int(df.isna().sum().sum()), flush=True)
    (ROOT / 'results' / 'input_manifest.json').write_text(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
