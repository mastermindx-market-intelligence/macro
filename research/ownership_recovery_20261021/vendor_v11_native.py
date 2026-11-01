"""Verbatim V11 native mechanics, extracted from the archived empirical.py.
Archive SHA256: 97966f72ea15cb34e0f5453252eef683411c894b7ca4432de4ce7c540d1ffaf0
Source SHA256: 816817ad5bcf71617227631e67b0493bf524fbe4a8f7a4c0d024bc31d8bc7faf
"""
from copy import deepcopy
from collections import deque
import numpy as np
import pandas as pd
NA = float("nan")

class NativeState:
    def __init__(self,fast=14,slow=60,signal=5):
        self.count=0;self.last=NA;self.up=NA;self.down=NA;self.seedup=0.;self.seeddown=0.
        self.fast=NA;self.slow=NA;self.signal=NA;self.nr=0;self.nm=0;self.h=NA
        self.lengths=(fast,slow,signal);self.rs=deque(maxlen=14);self.raw=deque(maxlen=3);self.ks=deque(maxlen=3);self.ms=deque(maxlen=104)
    def preview(self,close):return deepcopy(self).step(close)
    def step(self,close):
        if not np.isfinite(close) or close<=0:raise ValueError('Invalid native close')
        self.count+=1;r=NA
        if np.isfinite(self.last):
            delta=close-self.last;u=max(delta,0);v=max(-delta,0)
            if self.count<=15:
                self.seedup+=u;self.seeddown+=v
                if self.count==15:self.up=self.seedup/14;self.down=self.seeddown/14
            else:self.up=(13*self.up+u)/14;self.down=(13*self.down+v)/14
            if self.count>=15:
                # Exact endpoints prevent roundoff near100 from inventing a
                # nonzero stochastic range during a one-way initial history.
                if self.up==0 and self.down==0:r=50.
                elif self.down==0:r=100.
                elif self.up==0:r=0.
                else:r=100-100/(1+self.up/self.down)
        f,l,n=self.lengths;m=s=NA
        if np.isfinite(r):
            self.nr+=1;af=2/(f+1);al=2/(l+1)
            self.fast=r if self.nr==1 else af*r+(1-af)*self.fast
            self.slow=r if self.nr==1 else al*r+(1-al)*self.slow
            if self.nr>=max(f,l):
                m=self.fast-self.slow;self.nm+=1;a=2/(n+1)
                self.signal=m if self.nm==1 else a*m+(1-a)*self.signal
                if self.nm>=n:s=self.signal
        h=m-s;prior=self.h;bull=bool(np.isfinite(prior) and prior<=0 and h>0);bear=bool(np.isfinite(prior) and prior>=0 and h<0)
        self.rs.append(r);raw=NA
        if len(self.rs)==14 and all(map(np.isfinite,self.rs)) and max(self.rs)>min(self.rs):raw=100*(r-min(self.rs))/(max(self.rs)-min(self.rs))
        self.raw.append(raw);k=float(np.mean(self.raw)) if len(self.raw)==3 and all(map(np.isfinite,self.raw)) else NA
        self.ks.append(k);d=float(np.mean(self.ks)) if len(self.ks)==3 and all(map(np.isfinite,self.ks)) else NA
        past=[v for v in self.ms if np.isfinite(v)];q=np.quantile(past,.2) if len(past)>=52 else NA
        self.ms.append(m);self.h=h;self.last=close
        k3=min(v for v in self.ks if np.isfinite(v)) if np.isfinite(k) else NA
        k2=min(v for v in list(self.ks)[-2:] if np.isfinite(v)) if np.isfinite(k) else NA
        return dict(rsi=r,macd=m,signal=s,hist=h,k=k,d=d,raw=raw,bull=bull,bear=bear,recent3=k3,recent2=k2,deep=bool(np.isfinite(q) and m<0 and m<=q),change=h-prior)

def snapshots(close,calendar,frame='1W',mode='confirmed',phase=0,lengths=(14,60,5)):
    n={'1D':1,'2D':2,'3D':3,'1W':1,'2W':2}[frame]
    if phase not in range(n) or mode not in ['confirmed','developing']:raise ValueError('Invalid phase/mode')
    if calendar[-1]<=close.index[-1]:raise ValueError('Extended session calendar required')
    expected=calendar[(calendar>=close.index[0])&(calendar<=close.index[-1])]
    if not expected.equals(close.index):raise ValueError('Calendar/price mismatch')
    labels=(np.arange(len(calendar))-phase)//n if frame.endswith('D') else (((calendar-pd.Timestamp('2000-01-03')).days//7)-phase)//n
    tab=pd.DataFrame({'date':calendar,'gid':labels});bounds=tab.groupby('gid').date.agg(['first','last','size'])
    valid={}
    for gid,b in bounds.iterrows():
        origin=gid*n+phase
        ok=(origin>=0 and b['size']==n) if frame.endswith('D') else b['first']>=close.index[0]
        if frame.endswith('W') and gid==labels[0]:ok &= calendar[0]<=pd.Timestamp('2000-01-03')+pd.Timedelta(weeks=int(origin))
        valid[gid]=bool(ok and b['first']>=close.index[0])
    lastgid=labels[calendar.get_indexer([close.index[-1]])[0]]
    if frame.endswith('W'):
        nominal_end=pd.Timestamp('2000-01-03')+pd.Timedelta(days=int((lastgid*n+phase+n)*7-1))
        if calendar[-1]<=nominal_end:raise ValueError('Future calendar does not cover native end')
    st=NativeState(*lengths);saved={key:NA for key in ['rsi','macd','signal','hist','k','d','raw','recent3','recent2','change']};saved.update(bull=False,bear=False,deep=False)
    rows=[]
    for date,p,pos in zip(close.index,close.to_numpy(float),calendar.get_indexer(close.index)):
        g=labels[pos];end=bounds.loc[g,'last'];final=bool(valid[g] and date==end)
        if final:q=st.step(p);saved=q.copy()
        elif valid[g] and mode=='developing':q=st.preview(p)
        else:q=saved.copy()
        q=q.copy();q['bull']=bool(final and q.get('bull',False));q['bear']=bool(final and q.get('bear',False));q['fresh']=final;q['count']=st.count
        rows.append(q)
    return pd.DataFrame(rows,index=close.index)

def episodes(context,k,trigger,window=42,clear_n=10,start_i=0):
    out=[];arm=None;clear=clear_n;active=None
    for i in range(start_i,len(context)):
        prev_clear=clear;clear=0 if context[i] else clear+1
        if arm is not None and (i-arm>=window or (np.isfinite(k[i]) and k[i]>=60)):
            active['end_i']=i;arm=None;active=None
        if arm is None and context[i] and np.isfinite(k[i]) and k[i]<60 and (not out or prev_clear>=clear_n):
            arm=i;active={'episode':len(out)+1,'arm_i':i,'end_i':len(context),'signal_i':None};out.append(active)
        if arm is not None and active['signal_i'] is None and trigger[i]:active['signal_i']=i
    return out
