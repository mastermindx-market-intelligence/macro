"""Export immutable, outcome-free inputs from accepted ownership research."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--prior-root', type=Path, required=True)
    args = p.parse_args()
    c = json.loads((ROOT / 'config.json').read_text())
    mp = args.prior_root / 'data/input_manifest.json'
    rp = args.prior_root / 'results/capital_rosters.csv'
    assert sha(mp) == c['source_manifest_sha256']
    assert sha(rp) == c['source_roster_sha256']
    m = json.loads(mp.read_text())
    assets = []
    local_prices = ROOT / 'private/prices'
    local_prices.mkdir(parents=True, exist_ok=True)
    for a in m['assets']:
        assert sha(a['path']) == a['parquet_sha256'], a['ticker']
        link = local_prices / (a['ticker'] + '.parquet')
        if not link.exists():
            link.symlink_to(Path(a['path']).resolve())
        assert sha(link) == a['parquet_sha256']
        assets.append({k: v for k, v in a.items() if k not in ('path', 'source_receipt')})
    sp = next(a for a in m['assets'] if a['ticker'] == 'SPY')
    ix = pd.read_parquet(sp['path']).sort_index().loc['2010-01-04':c['cutoff']].index
    r = pd.read_csv(rp)
    r = r.loc[(r.population == 'SECTORS') & (r.policy == 'RSI')].copy()
    assert len(r) == 108 and set(r.symbol) == set(c['source_symbols'])
    assert not r.duplicated(['symbol', 'signal_t']).any()
    out = []
    for x in r.itertuples():
        t = int(x.signal_t)
        e = t + 1
        assert 0 <= t < len(ix)
        out.append({'symbol': x.symbol, 'signal_t': t,
                    'signal_date': str(ix[t].date()), 'entry_t': e,
                    'entry_date': str(ix[e].date()) if e < len(ix) else '',
                    'executable': e < len(ix),
                    'previous_accepted_ignored': bool(x.accepted)})
    (ROOT / 'inputs').mkdir(exist_ok=True)
    path = ROOT / 'inputs/signal_roster.csv'
    pd.DataFrame(out).sort_values(['signal_t', 'symbol']).to_csv(path, index=False)
    prior_export = ROOT / 'inputs/source_manifest.json'
    created = json.loads(prior_export.read_text())['created_utc'] if prior_export.exists() else datetime.now(timezone.utc).isoformat()
    manifest = {'created_utc': created,
                'previous_merge': c['previous_merge'],
                'source_manifest_sha256': sha(mp), 'source_roster_sha256': sha(rp),
                'signal_roster_sha256': sha(path), 'cutoff': c['cutoff'],
                'price_origin': '2010-01-04', 'signal_rows': len(out),
                'source_archive_sha256': m.get('archive_sha256'),
                'price_convention': 'current-vintage adjusted OHLC proxy; not PIT',
                'assets': assets}
    (ROOT / 'inputs/source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'source_rows': len(out), 'price_files_verified': len(assets),
                      'signal_roster_sha256': sha(path)}))


if __name__ == '__main__':
    main()
