"""Public incumbent-provider inspection; no canonical store writes."""
import concurrent.futures
import gzip
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/paper_international_wave1_wave2/fx_coverage_20261020')
URLS = {
    'JP': 'https://query1.finance.yahoo.com/v8/finance/chart/USDJPY%3DX?range=6mo&interval=1d',
    'AU': 'https://query1.finance.yahoo.com/v8/finance/chart/AUDUSD%3DX?range=6mo&interval=1d',
}

def acquire(item):
    cc, url = item
    record = {'cc': cc, 'url': url, 'started_at': datetime.now(timezone.utc).isoformat(), 'attempts': 1}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mastermind country currency research'})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('response_size_limit')
            record.update(status=response.status, final_url=response.url, content_type=response.headers.get('Content-Type'))
        path = OUT / (cc + '_yahoo_chart.json.gz')
        path.write_bytes(gzip.compress(data, mtime=0))
        record.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), archive=path.name)
        body = json.loads(data)
        result = (body.get('chart') or {}).get('result')
        if result:
            row = result[0]
            record['meta'] = {k: row.get('meta', {}).get(k) for k in ['symbol', 'currency', 'instrumentType', 'exchangeName', 'exchangeTimezoneName', 'timezone', 'gmtoffset', 'dataGranularity', 'range', 'regularMarketTime']}
            observed = [(t, c) for t, c in zip(row.get('timestamp', []), row.get('indicators', {}).get('quote', [{}])[0].get('close', [])) if c is not None]
            record.update(observation_count=len(observed), first=observed[0] if observed else None, last=observed[-1] if observed else None)
        else:
            record['provider_error'] = (body.get('chart') or {}).get('error')
    except urllib.error.HTTPError as exc:
        record.update(status=exc.code, error_type=type(exc).__name__)
    except Exception as exc:
        record.update(error_type=type(exc).__name__, error=str(exc)[:400])
    record['finished_at'] = datetime.now(timezone.utc).isoformat()
    return record

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    records = list(pool.map(acquire, URLS.items()))
(OUT / 'incumbent_provider_probe.json').write_text(json.dumps(records, indent=2) + '\n')
for row in records:
    print(json.dumps(row), flush=True)
