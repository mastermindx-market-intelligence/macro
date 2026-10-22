"""Bounded official daily-data feasibility audit; no market strategy is tested.

Explicit foreground research fetch, no cron, credential, raw-data persistence or
production publisher. The same Cboe history endpoint template is already used by
collectors/cboe_indices.py. Daily OHLC cannot establish intraday trigger ordering.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

URL = 'https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv'
LIMIT = 5_000_000


def inspect_bytes(raw: bytes, *, symbol: str, cutoff: date) -> dict:
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    columns = reader.fieldnames or []
    rows, malformed, later = [], 0, 0
    for row in reader:
        try:
            text = row['DATE'].strip()
            day = datetime.strptime(text, '%m/%d/%Y').date() if '/' in text else date.fromisoformat(text)
            values = {k: float(v) for k, v in row.items() if k != 'DATE' and v is not None and v.strip()}
            if not values or not all(math.isfinite(v) for v in values.values()):
                raise ValueError('missing/nonfinite values')
        except (KeyError, TypeError, ValueError):
            malformed += 1
            continue
        if day > cutoff:
            later += 1
            continue
        rows.append((day, values))
    dates = [day for day, _ in rows]
    result = {'symbol': symbol, 'source_url': URL.format(symbol=symbol),
        'raw_sha256': sha256(raw).hexdigest(), 'raw_bytes': len(raw), 'columns': columns,
        'cutoff': cutoff.isoformat(), 'rows_through_cutoff': len(rows),
        'first_date': min(dates).isoformat() if dates else None,
        'last_date': max(dates).isoformat() if dates else None,
        'malformed_rows': malformed, 'future_rows_excluded': later,
        'duplicate_dates': len(dates) - len(set(dates)),
        'frequency': 'daily', 'operational_pit': False,
        'supports_intraday_trigger_ordering': False,
        'original_availability_timestamps': 'not_present'}
    if symbol == 'VIX1D':
        valid = [v for _, v in rows if all(k in v for k in ('LOW','CLOSE'))]
        result['threshold_6_88_descriptive_only'] = {
            'eligible_daily_rows': len(valid),
            'daily_low_at_or_below': sum(v['LOW'] <= 6.88 for v in valid),
            'daily_close_at_or_below': sum(v['CLOSE'] <= 6.88 for v in valid),
            'low_hit_but_close_above': sum(v['LOW'] <= 6.88 < v['CLOSE'] for v in valid),
            'warning': 'A daily low gives neither first-touch time nor contemporaneous SPY/option conditions.'}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cutoff', type=date.fromisoformat, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fetch-public-daily', action='store_true')
    args = parser.parse_args()
    if not args.fetch_public_daily:
        parser.error('explicit --fetch-public-daily required; no implicit network')
    results = []
    for symbol in ('VIX1D','VIX','VIX3M'):
        try:
            request = Request(URL.format(symbol=symbol), headers={'User-Agent':'Mastermind-Research/1.0'})
            with urlopen(request, timeout=15) as response:
                raw = response.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError('response exceeds byte bound')
            results.append(inspect_bytes(raw, symbol=symbol, cutoff=args.cutoff))
        except Exception as exc:
            results.append({'symbol':symbol,'status':'unavailable','error_class':type(exc).__name__})
    output = {'schema':'market_navigator.daily_feasibility/v1',
        'retrieved_at':datetime.now(timezone.utc).isoformat(),
        'evidence_class':'PUBLIC_RECONSTRUCTION_FEASIBILITY_NOT_PREDICTIVE_VALIDATION',
        'sources':results,'raw_data_committed':False,
        'trading_authority':False,'research_finding':'Daily data can audit measurement coverage; intraday rule validation still needs time-stamped joint observations.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print(json.dumps(output,indent=2))


if __name__ == '__main__':
    main()
