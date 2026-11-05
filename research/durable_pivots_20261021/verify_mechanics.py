#!/usr/bin/env python3
"""Meaningful frozen-pivot policy checks retained with the research package."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import mechanics as m

def run():
    checks=[];idx=pd.bdate_range('2020-01-01',periods=150)
    d=pd.DataFrame({'open':101.,'high':101.5,'low':100.5,'close':101.,'volume':100.},index=idx)
    f={'1D':pd.DataFrame({'valid':True,'bottom_both_rising':False},index=idx)}
    f['1D'].loc[idx[33],'bottom_both_rising']=True
    r=SimpleNamespace(side='bottom',t=30,p=20,candidate_price=100.,atr_p=1.,base='test',ticker='TEST',
       asset_class='test',date=idx[30],halfyear='2020H1',quarter='2020Q1',candidate_date=idx[20],
       primary63=1.,qualified=True,survive63=1.,depth=6.,matched_pivot='TEST:bottom:p')
    a=m.wait_one(r,d,f,'1D','both_rising');assert a['delay']==3 and a['age']==13 and a['primary63']==1
    checks.append('first_completed_confirmation_with_original_age')
    u=d.copy();u.loc[idx[32],'low']=99.7
    assert m.wait_one(r,u,f,'1D','both_rising')['status']=='invalidated'
    checks.append('pre_confirmation_invalidation')
    u=d.copy();u.loc[idx[33],'low']=99.7
    assert m.wait_one(r,u,f,'1D','both_rising')['status']=='invalidated'
    checks.append('same_bar_invalidation_priority')
    u=d.copy();u.loc[idx[32],'low']=99.9
    a=m.wait_one(r,u,f,'1D','both_rising');assert a['candidate_price']==100 and a['primary63']==1
    checks.append('tolerated_undercut_does_not_replace_candidate')
    u=d.copy();u.loc[idx[34],'low']=99.7
    a=m.wait_one(r,u,f,'1D','both_rising');assert a['status']=='confirmed' and a['primary63']==0
    checks.append('post_confirmation_failure')
    r.matched_pivot='';r.qualified=False;r.primary63=0
    a=m.wait_one(r,d,f,'1D','both_rising')
    assert a['primary63']==1 and a['matched_pivot']=='TEST:bottom:'+str(idx[20].date())
    checks.append('original_candidate_retest_detection_credit')
    q=pd.DataFrame({'qualified':True,'a':[True]*5+[False]*5,'b':[False]*5+[True]*5,
       'age':3,'distance':1.,'depth':5.,'survive63':[1.]*5+[0.]*5,'halfyear':'2020H1'})
    z=m.standardized(q,'a','b');assert z['bootstrap_blocks']==1 and np.isnan(z['delta_ci_low'])
    checks.append('single_block_interval_unavailable')
    return checks

if __name__=='__main__':
    checks=run();out=Path(__file__).parent/'local_verification';out.mkdir(exist_ok=True)
    (out/'mechanics_verification.json').write_text(json.dumps({'checks_passed':checks,'count':len(checks)},indent=2))
    print('VERIFIED_MECHANICS',len(checks))
