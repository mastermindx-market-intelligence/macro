"""Research-only native-excerpt probe. No market data or economic backtest.

Runs selected native Python function bodies and a TypeScript-transpiled
JavaScript fixture in isolation. The fixture
excerpts must be reviewed against their pinned upstream sources. Their hashes
identify exactly the tested bytes, not full-product parity or source availability.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd

# Selected native Python function bodies; not a product import.
def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, min_periods=n).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / n, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd_hist(close: pd.Series) -> pd.Series:
    ema12 = close.ewm(span=12, min_periods=12).mean()
    ema26 = close.ewm(span=26, min_periods=26).mean()
    macd = ema12 - ema26
    return macd - macd.ewm(span=9, min_periods=9).mean()

# Same pin, engine/confluence_tiers.py:56 and :255-262.
RSI_LEN, FAST_LEN, BASE_LEN, SIG_LEN = 14, 14, 60, 5


def _ema(s, span):
    return s.ewm(span=span, min_periods=span).mean()


def _rsi_macd(c):
    r = rsi(c, RSI_LEN)
    m = _ema(r, FAST_LEN) - _ema(r, BASE_LEN)
    return m, _ema(m, SIG_LEN)

TERMINAL_EXCERPT = '// Research fixture: native function bodies from terminal@c35b9a1d50ca4960c361645f0300fa9f95158a4e.\n// terminal/lib/suites/shared/oscUtils.ts, Git blob 9374ddefd7df46786964a9cc69da0866ff8295fb.\n// Selected pure functions only; no product imports, mutation, or alternate indicator owner.\nfunction sanLen(len) {\n    const n = Math.floor(Number(len));\n    return Number.isFinite(n) && n >= 1 ? n : 1;\n}\nexport function wilderRma(vals, len) {\n    const n = vals?.length ?? 0;\n    const out = new Float64Array(n);\n    if (n === 0)\n        return out;\n    out.fill(NaN);\n    const L = sanLen(len);\n    let seen = 0; // usable samples so far\n    let seed = 0; // running sum while seeding\n    let prev = NaN;\n    for (let i = 0; i < n; i++) {\n        const v = vals[i];\n        if (!Number.isFinite(v))\n            continue; // hole: out[i] stays NaN, state untouched\n        seen++;\n        if (seen < L) {\n            seed += v;\n            continue; // still warming up - honest NaN\n        }\n        if (seen === L) {\n            seed += v;\n            prev = seed / L;\n        }\n        else {\n            prev = (prev * (L - 1) + v) / L;\n        }\n        out[i] = prev;\n    }\n    return out;\n}\nexport function emaArr(vals, len) {\n    const n = vals?.length ?? 0;\n    const out = new Float64Array(n);\n    if (n === 0)\n        return out;\n    out.fill(NaN);\n    const L = sanLen(len);\n    const k = 2 / (L + 1);\n    let seen = 0;\n    let seed = 0;\n    let prev = NaN;\n    for (let i = 0; i < n; i++) {\n        const v = vals[i];\n        if (!Number.isFinite(v))\n            continue;\n        seen++;\n        if (seen < L) {\n            seed += v;\n            continue;\n        }\n        if (seen === L) {\n            seed += v;\n            prev = seed / L;\n        }\n        else {\n            prev = v * k + prev * (1 - k);\n        }\n        out[i] = prev;\n    }\n    return out;\n}\nexport function rsiArr(closes, len) {\n    const n = closes?.length ?? 0;\n    const out = new Float64Array(n);\n    if (n === 0)\n        return out;\n    out.fill(NaN);\n    const L = sanLen(len);\n    const gain = new Float64Array(n).fill(NaN);\n    const loss = new Float64Array(n).fill(NaN);\n    for (let i = 1; i < n; i++) {\n        const c = closes[i];\n        const p = closes[i - 1];\n        if (!Number.isFinite(c) || !Number.isFinite(p))\n            continue; // hole: both stay NaN, rma skips it\n        const d = c - p;\n        gain[i] = d > 0 ? d : 0;\n        loss[i] = d < 0 ? -d : 0;\n    }\n    const avgG = wilderRma(gain, L);\n    const avgL = wilderRma(loss, L);\n    for (let i = 0; i < n; i++) {\n        const g = avgG[i];\n        const l = avgL[i];\n        if (!Number.isFinite(g) || !Number.isFinite(l))\n            continue;\n        out[i] = l > 0 ? 100 - 100 / (1 + g / l) : g > 0 ? 100 : 50;\n    }\n    return out;\n}\n'

ROOT = Path(__file__).resolve().parent
AUTHORITY = {k: False for k in ('rank', 'entry', 'size', 'trade', 'promotion')}
ATOL = 1e-10


def fixtures() -> dict[str, list[float | None]]:
    t = np.arange(512, dtype=float)
    oscillation = 100 + .025*t + 7*np.sin(.23*t) + 3*np.sin(.079*t)
    broken = oscillation.copy()
    broken[[36, 37, 190, 191, 192, 401]] = np.nan
    cases = {'rising': 100+t, 'falling': 700-t, 'flat': t*0+100,
             'oscillating': oscillation, 'gapped': broken,
             'short': oscillation[:12]}
    return {k: [float(x) if np.isfinite(x) else None for x in a] for k,a in cases.items()}


def terminal_values(cases: dict[str, list[float | None]]) -> dict:
    # Imports only the small reviewed numeric excerpt. No product runtime loads.
    js = TERMINAL_EXCERPT + '''
import fs from 'node:fs';
const cases = JSON.parse(fs.readFileSync(0,'utf8'));
const out = {};
for (const [key,raw] of Object.entries(cases)) {
  const x=raw.map(v=>v===null?NaN:v);
  const clean=a=>Array.from(a, v=>Number.isFinite(v)?v:null);
  const rr=rsiArr(x,14), fast=emaArr(rr,14), slow=emaArr(rr,60);
  const macd=Array.from(rr,(_,i)=>fast[i]-slow[i]), sig=emaArr(macd,5);
  out[key]={rsi:clean(rr),ema:clean(emaArr(x,14)),
    substituted_rsi_macd_hist:clean(macd.map((v,i)=>v-sig[i]))};
}
process.stdout.write(JSON.stringify(out));'''
    run = subprocess.run(['node','--input-type=module','-e',js],
                         cwd=ROOT, input=json.dumps(cases,allow_nan=False), text=True,
                         capture_output=True, timeout=30, check=True)
    return json.loads(run.stdout)


def describe(a, b) -> dict:
    a, b = np.asarray(a,dtype=float), np.asarray(b,dtype=float)
    fa, fb = np.isfinite(a), np.isfinite(b)
    paired = fa & fb
    delta = np.abs(a[paired]-b[paired])
    adjacent = paired[1:] & paired[:-1]
    left_cross = (a[1:] > 50) & (a[:-1] <= 50)
    right_cross = (b[1:] > 50) & (b[:-1] <= 50)
    return {'rows':len(a), 'left_finite':int(fa.sum()), 'right_finite':int(fb.sum()),
            'finite_mask_disagreements':int((fa!=fb).sum()),
            'paired_values':int(paired.sum()),
            'paired_value_disagreements_at_1e_10':int((delta>ATOL).sum()),
            'max_absolute_difference':float(delta.max()) if len(delta) else None,
            'rsi_50_upcross_disagreement_indices':
                (np.flatnonzero(adjacent & (left_cross!=right_cross))+1).tolist()}


def run_probe() -> dict:
    cases = fixtures(); tv = terminal_values(cases)
    observations = {}
    for name, values in cases.items():
        c = pd.Series(values,dtype=float)
        mr = rsi(c).to_numpy(); me = _ema(c,14).to_numpy()
        rd=describe(mr,tv[name]['rsi']); ed=describe(me,tv[name]['ema'])
        # A midline RSI cross is not a meaningful EMA comparison metric.
        ed.pop('rsi_50_upcross_disagreement_indices')
        m,s = _rsi_macd(c)
        hist=(m-s).to_numpy()
        sub=np.asarray(tv[name]['substituted_rsi_macd_hist'],dtype=float)
        pair=np.isfinite(hist)&np.isfinite(sub)
        near=np.abs(hist[pair]-sub[pair])
        adjacent=pair[1:]&pair[:-1]
        changed=adjacent & (((hist[1:]>0)&(hist[:-1]<=0)) != ((sub[1:]>0)&(sub[:-1]<=0)))
        stable={}
        for cut in (80,160,232,400):
            valid=pair & (np.arange(len(hist))>=cut)
            stable[str(cut)]={'paired_values':int(valid.sum()),
                'max_histogram_difference':float(np.abs(hist[valid]-sub[valid]).max()) if valid.any() else None,
                'cross_disagreement_indices':(np.flatnonzero(changed & (np.arange(1,len(hist))>=cut))+1).tolist()}
        observations[name]={'rsi_macro_vs_terminal':rd,'ema_macro_vs_terminal':ed,
                            'macro_rsi_macd_finite':int((m-s).notna().sum()),
                            'macro_price_macd_finite':int(macd_hist(c).notna().sum()),
                            'hypothetical_primitive_substitution_not_terminal_macdx':stable}
    # Usable-history floors and numerical convergence are different questions.
    c=pd.Series(cases['oscillating'],dtype=float)
    m,s=_rsi_macd(c); full=float((m-s).iloc[-1]); trailing=[]
    for count in (80,120,160,232,400):
        mm,ss=_rsi_macd(c.iloc[-count:]); got=(mm-ss).iloc[-1]
        trailing.append({'native_input_bars':count, 'full_history_histogram':full,
            'trailing_history_histogram':float(got) if np.isfinite(got) else None,
            'absolute_delta':abs(float(got)-full) if np.isfinite(got) else None})
    return {'schema':'prophet.native_primitive_probe/v1','authority':dict(AUTHORITY),
            'basis':'synthetic fixtures; isolated native function excerpts, not deployed products',
            'source_pins':{'macro':'b4f95f98ef80b8cbb4636afbd723b5091658e1f1',
                           'terminal':'c35b9a1d50ca4960c361645f0300fa9f95158a4e'},
            'executed_probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'terminal_fixture_sha256':hashlib.sha256(TERMINAL_EXCERPT.encode()).hexdigest(),
            'runtime':{'python':sys.version.split()[0],'numpy':np.__version__,
                       'pandas':pd.__version__,
                       'node':subprocess.check_output(['node','--version'],text=True).strip()},
            'fixtures_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True,allow_nan=False).encode()).hexdigest(),
            'observations':observations,'history_window_sensitivity':trailing,
            'limitations':['No economic outcomes, no optimal timeframe and no predictive claim.',
                'Missing-price policies are primitive-level; callers may pre-filter inputs.',
                'MACD Ultimate normalization and validated Prophet take policy are not executed.',
                'Finite-mask equality, numeric equality, event equality and profitability differ.',
                'Changing a native formula would change strategy identity and requires its own validation.']}


if __name__ == '__main__':
    print(json.dumps(run_probe(),indent=2,allow_nan=False,sort_keys=True))
