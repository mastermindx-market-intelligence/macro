"""Focused independent arithmetic and chronology checks for research mechanics."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import analyze as a

def prices(n=100):
    ix=pd.bdate_range('2020-01-01',periods=n)
    return pd.DataFrame({'open':100.,'high':101.,'low':99.,'close':100.,'adjclose':100.},index=ix)

def run():
    checks=[]
    def passed(s): checks.append(s)
    d=prices();d.iloc[81,d.columns.get_loc('low')]=93.
    o=a.outcomes(d,d,3,.001)
    assert o.loc[d.index[80],'stop_hit']
    assert o.loc[d.index[80],'stop_t']==81
    np.testing.assert_allclose(o.loc[d.index[80],'stop_net'],.94*.999/1.001-1)
    passed('entry-session intraday stop included; hand-calculated fill94')
    d=prices();d.iloc[82]=[90.,92.,89.,91.,91.]
    o=a.outcomes(d,d,3,.001)
    np.testing.assert_allclose(o.loc[d.index[80],'stop_net'],.90*.999/1.001-1)
    passed('later gap through stop94 fills at open90')
    d=prices();d.iloc[81,d.columns.get_loc('low')]=98.9
    o=a.outcomes(d,d,3,.001)
    assert o.loc[d.index[80],'reference_break_horizon']
    assert not o.loc[d.index[80],'tolerant_reference_break_horizon']
    passed('strict undercut is distinct from the separately named quarter-ATR tolerance')
    d=prices();ad=d.copy();f=np.ones(len(d))*.5;f[82:]=.505
    ad[['open','high','low','close']]=d[['open','high','low','close']].mul(f,axis=0)
    o=a.outcomes(d,ad,3,.001,'raw')
    np.testing.assert_allclose(o.loc[d.index[80],'net'],1.01*.999/1.001-1)
    np.testing.assert_allclose(o.loc[d.index[80],'price_net'],.999/1.001-1)
    passed('adjustment-factor return separated from price-only return')
    rr,sk=a.accepted_roster([80,81,83,84,90],3,92)
    assert [r['signal_t'] for r in rr]==[80,83,90]
    assert [i for i,_ in sk]==[81,84]
    passed('scheduled interval prevents capital reuse; signal at exit close may nominate next open')
    d=prices();d.iloc[82]=[90.,92.,89.,91.,91.]
    rr,_=a.accepted_roster([80,81,90],3,len(d))
    v,h,u,t=a.sleeve({'A':d},{'A':d},'A',rr,80,.001,stop=True)
    expected=.9*.999/1.001
    np.testing.assert_allclose(v[2:11],expected)
    assert len(t)==2 and t[0]['exit_t']==82 and t[1]['entry_t']==91
    passed('stopped sleeve remains cash; same frozen later entry roster')
    d=prices(92);d.iloc[-1]=[100.,111.,99.,110.,110.]
    rr,_=a.accepted_roster([90],3,len(d))
    v,h,u,t=a.sleeve({'A':d},{'A':d},'A',rr,80,.001)
    np.testing.assert_allclose(v[-1],1.1*.999/1.001)
    assert len(t)==1 and not t[0]['closed'] and h[-1]>0
    passed('immature cutoff position remains marked with terminal liquidation fee')
    d=prices(85);b=d.copy();d.iloc[83]=[100.,121.,99.,120.,120.];b.iloc[83]=[100.,111.,99.,110.,110.]
    rr,_=a.accepted_roster([80],3,len(d))
    v,h,u,t=a.sleeve({'A':d,'B':b},{'A':d,'B':b},'A',rr,80,.001,basket=['A','B'])
    np.testing.assert_allclose(v[3],1.15*.999/1.001)
    assert t[0]['closed']
    passed('equal initial basket allocations produce the hand-calculated mean payoff')
    ix=pd.bdate_range('2010-01-04',periods=2200)
    close=pd.Series(100+np.arange(2100)*.01+8*np.sin(np.arange(2100)/13),index=ix[:2100])
    for frame in ['1D','1W','2W']:
        full=a.snapshots(close,ix,frame)
        for cut in [1997,2000,2051]:
            pre=a.snapshots(close.iloc[:cut],ix,frame)
            np.testing.assert_allclose(pre.select_dtypes(include=[np.number]),full.iloc[:cut].select_dtypes(include=[np.number]),equal_nan=True)
            assert pre.bull.equals(full.bull.iloc[:cut])
    passed('native indicator values and cross events invariant to future-price truncation at nine prefixes')
    flat=a.snapshots(pd.Series(100.,index=ix[:2100]),ix,'1D')
    assert not flat.bull.any() and flat.k.isna().all()
    passed('flat RSI range does not manufacture stochastic crosses')
    dd=prices();rr,_=a.accepted_roster([80],3,len(dd));v,h,u,t=a.sleeve({'A':dd},{'A':dd},'A',rr,80,.001)
    st,an=a.account_stats(v,h,u,dd.index[80:],t,.001)
    assert 0<=st['invested_fraction']<=1 and st['max_drawdown']<0
    np.testing.assert_allclose(v[1],.999/1.001)
    passed('no leverage from liquidation marking; both transaction costs visible at constant price')
    empty=a.sleeve({'A':dd},{'A':dd},'A',[],80,.001,.03)[0]
    np.testing.assert_allclose(empty[-1],1.03**((len(dd)-80-1)/252))
    passed('declared cash scenario compounds only cash across elapsed sessions')
    grid,w=a.block_weights(pd.Timestamp('2018-01-01'),pd.Timestamp('2026-10-08'))
    rare=pd.DataFrame({'halfyear':[4036,4036],'delta':[.01,.02]})
    _,lo,hi,valid,support,eligible=a.boot_mean(rare,'delta',grid,w)
    assert support==1 and not eligible and np.isnan(lo) and np.isnan(hi)
    broad=pd.DataFrame({'halfyear':grid,'delta':np.ones(len(grid))*.02})
    con=a.boot_contrast(broad,broad.assign(delta=.01),'delta',grid,w)
    np.testing.assert_allclose([con['point'],con['lo'],con['hi']],[.01,.01,.01])
    assert con['joint_valid_draw_fraction']==1 and con['interval_available']
    passed('bootstrap suppresses one-block intervals and preserves joint contrast support')
    print(json.dumps({'passed':len(checks),'checks':checks},indent=2))
    return {'passed':len(checks),'checks':checks}

if __name__=='__main__':
    result=run();p=Path(__file__).resolve().parent/'results/mechanical_verification.json'
    p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(result,indent=2))
