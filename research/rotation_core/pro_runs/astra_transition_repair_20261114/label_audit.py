"""Post-result label diagnostic, not a new signal or confirmatory test.
Motivated by pilot R reducing both first-passage outcomes while Bad10 stayed flat.
No threshold selection, new gate, outcome replacement or post-2002 data.
Forward volatility is an OUTCOME diagnostic, never a decision feature.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pilot


def main() -> None:
    r, ri = pilot.download('industries')
    ff, fi = pilot.download('factors')
    assert ri['download_sha256'] == 'b9d36d571e968d71f7b03207e7fed6398554f953719b8c1bf3ee3ad8d00e7520'
    assert fi['download_sha256'] == '96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89'
    dates = r.index.intersection(ff.index)
    r = r.loc[dates]
    market = (ff['Mkt-RF'] + ff['RF']).loc[dates]
    f = pilot.features(r, market)
    events, _ = pilot.build_events(r, market, f, lag=1)
    assert len(events) == 8902
    rows = []
    for _, event in events.iterrows():
        t = int(r.index.get_loc(pd.Timestamp(event.date)))
        j = int(r.columns.get_loc(event.industry))
        e = t + 1
        future = f['lr'].iloc[e+1:e+64, j].to_numpy()
        sigma_future = float(np.std(future, ddof=1))
        log_barrier = 2 * event.sigma63 * math.sqrt(21)
        path = np.cumsum(future)
        up = np.flatnonzero(path >= np.log1p(.10))
        down = np.flatnonzero(path <= np.log1p(-.10))
        a = int(up[0]) if len(up) else 64
        b = int(down[0]) if len(down) else 64
        rows.append({**event.to_dict(),
            'trailing_sigma_annualized': event.sigma63 * math.sqrt(252),
            'forward_sigma_annualized': sigma_future * math.sqrt(252),
            'forward_to_trailing_sigma': sigma_future / event.sigma63,
            'barrier_up_pct': float(np.expm1(log_barrier)),
            'barrier_down_loss_pct': float(-np.expm1(-log_barrier)),
            'fixed10_upper_first': int(a < b), 'fixed10_lower_first': int(b < a),
            'fixed10_unresolved': int(a == b)})
    df = pd.DataFrame(rows)
    metrics = ['trailing_sigma_annualized', 'forward_sigma_annualized', 'forward_to_trailing_sigma',
               'barrier_up_pct', 'barrier_down_loss_pct', 'distance21low',
               'fixed10_upper_first', 'fixed10_lower_first', 'fixed10_unresolved']
    result = {'status': 'POST_RESULT_LABEL_DIAGNOSTIC_NOT_A_NEW_SIGNAL',
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'events': len(df), 'cutoff': '2002-12-31',
        'groups': {str(k): {'n': len(g), 'months': int(g.month.nunique()),
                           'mean': {m: float(g[m].mean()) for m in metrics},
                           'median': {m: float(g[m].median()) for m in metrics}}
                   for k, g in df.groupby('R')},
        'limitations': ['Adaptive descriptive diagnostic; no significance or causal claim.',
            'Fixed +/-10% barriers are a label sensitivity, not the registered primary outcome.',
            'Barriers are applied to closes; not intraday stops or actual executable fills.',
            'Forward volatility is never used to filter candidates.',
            'This does not audit or invalidate the proprietary dot close-ATR hold label.']}
    out = Path(__file__).with_name('LABEL_AUDIT_RESULTS.json')
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result))
    print('RESULT_SHA256', hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
