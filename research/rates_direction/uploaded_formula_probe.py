"""Synthetic source-contract probes, NOT a Pine runtime or a market backtest.

Research recipe only; does not register a signal or change an existing owner.
Requires numpy/pandas. Native Pine golden vectors and qualified OHLC remain owed.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd


def rsi_reference(close, n=14):
    """Finite-input Wilder reference; native warmup/gap parity is not certified."""
    delta = close.diff().to_numpy(float)
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return pd.Series(out, index=close.index)
    up, down = np.maximum(delta[1:n+1], 0).mean(), np.maximum(-delta[1:n+1], 0).mean()
    for i in range(n, len(close)):
        if i > n:
            up = (up*(n-1)+max(delta[i], 0))/n
            down = (down*(n-1)+max(-delta[i], 0))/n
        out[i] = 100*up/(up+down) if up+down > 0 else np.nan
    return pd.Series(out, index=close.index)


def cross(a, b, side, strict=False):
    b = pd.Series(b, index=a.index) if np.isscalar(b) else b
    if side == 'up':
        prior = a.shift() < b.shift() if strict else a.shift() <= b.shift()
        return (a > b) & prior
    if side == 'down':
        prior = a.shift() > b.shift() if strict else a.shift() >= b.shift()
        return (a < b) & prior
    raise ValueError('invalid direction')


def calculate(f, sma_osc=False, sma_signal=False):
    if not f.index.is_unique or not f.index.is_monotonic_increasing:
        raise ValueError('ordered unique grid required')
    if not {'high','low','close'}.issubset(f):
        raise ValueError('real high/low/close required')
    f = f[['high','low','close']].astype(float)
    if not np.isfinite(f.to_numpy()).all():
        raise ValueError('missing values may not be silently filled')
    if ((f.high < f.close) | (f.low > f.close)).any():
        raise ValueError('invalid high/low/close')
    r = rsi_reference(f.close)
    ma = lambda s,n,simple: s.rolling(n).mean() if simple else s.ewm(span=n,adjust=False).mean()
    m = ma(r,14,sma_osc)-ma(r,60,sma_osc)
    sig = ma(m,5,sma_signal)
    lr,hr = r.rolling(14).min(),r.rolling(14).max()
    kr = (100*(r-lr)/(hr-lr).replace(0,np.nan)).rolling(3).mean()
    lp,hp = f.low.rolling(14).min(),f.high.rolling(14).max()
    kp = (100*(f.close-lp)/(hp-lp).replace(0,np.nan)).rolling(3).mean()
    out = pd.DataFrame({'m':m,'sig':sig,'hist':m-sig,'kr':kr,'dr':kr.rolling(3).mean(),
                        'kp':kp,'dp':kp.rolling(3).mean()})
    for side in ('up','down'):
        out[f'm_{side}']=cross(m,sig,side)
        out[f'h_{side}']=cross(m-sig,0,side)
        out[f'z_{side}']=cross(m,0,side)
        out[f'p_{side}']=cross(kp,out.dp,side,strict=True)
    out['p_strict_up']=out.p_up & (kp.shift()<20)
    out['p_strict_down']=out.p_down & (kp.shift()>80)
    return out


def run():
    t=np.arange(1200)
    c=4+.0007*t+.07*np.sin(t/13)+.015*np.cos(t/3.2)
    f=pd.DataFrame({'close':c,'high':c+.006+.003*np.cos(t/7)**2,
                    'low':c-.004-.003*np.sin(t/5)**2},
                   index=pd.date_range('2020-01-01',periods=1200,freq='2h',tz='UTC'))
    a=calculate(f)
    checks=[]
    for side in ('up','down'):
        assert a[f'm_{side}'].equals(a[f'h_{side}'])
    checks.append('line-signal cross equals histogram-zero cross')
    assert not a.m_up.equals(a.z_up)
    checks.append('MACD zero baseline remains a distinct trigger')
    changed=f.copy(); changed['high'] += .09; b=calculate(changed)
    pd.testing.assert_frame_equal(a[['m','sig','hist','kr','dr']],b[['m','sig','hist','kr','dr']])
    assert (a.kp-b.kp).abs().max()>1
    checks.append('wick-only change affects price stochastic, not RSI-based formulas')
    assert (a.kr-a.kp).abs().max()>1
    checks.append('two lower formulas are not identical')
    k,d=pd.Series([10.,10.,12.]),pd.Series([11.,10.,11.])
    assert cross(k,d,'up').iloc[-1] and not cross(k,d,'up',strict=True).iloc[-1]
    checks.append('strict CM crossing excludes previous equality')
    k,d=pd.Series([19.,25.]),pd.Series([20.,24.])
    assert (cross(k,d,'up',strict=True)&(k.shift()<20)).iloc[-1] and k.iloc[-1]>20
    checks.append('CM extreme test uses previous K')
    changed=f.copy(); changed.iloc[850:,:] += 5
    pd.testing.assert_frame_equal(a.iloc[:850],calculate(changed).iloc[:850])
    checks.append('future mutation does not change prior values or events')
    pd.testing.assert_frame_equal(a.iloc[:801],calculate(f.iloc[:801]))
    checks.append('closed-prefix truncation invariance')
    assert (a.m-calculate(f,sma_osc=True).m).abs().max()>.1
    assert (a.sig-calculate(f,sma_signal=True).sig).abs().max()>.01
    checks.append('SMA toggles materially change the calculation')
    for bad in (f.drop(columns='high'), f.iloc[::-1], pd.concat([f,f.tail(1)])):
        try: calculate(bad)
        except ValueError: pass
        else: raise AssertionError('invalid input accepted')
    for value in (np.nan,np.inf):
        bad=f.copy();bad.iloc[300,0]=value
        try: calculate(bad)
        except ValueError: pass
        else: raise AssertionError('nonfinite value accepted')
    checks.append('missing OHLC, nonfinite, reversed and duplicate grids refused')
    flat=f.copy();flat[:]=4
    assert calculate(flat).kp.isna().all() and calculate(flat).kr.isna().all()
    checks.append('zero-range inputs stay unknown')
    return {'schema':'ric.uploaded_formula_probe.v1','scope':'synthetic contract probes only',
            'checks_passed':len(checks),'checks':checks,'market_outcomes_read':False,
            'empirical_trials':0,'native_pine_parity':False,'production_authority':False,
            'numpy':np.__version__,'pandas':pd.__version__}


if __name__=='__main__':
    print(json.dumps(run(),indent=2,allow_nan=False))
