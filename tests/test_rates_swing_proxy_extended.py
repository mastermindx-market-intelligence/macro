"""The expanded sample must not change the frozen pilot's probability math."""
from __future__ import annotations
import numpy as np
import pandas as pd
from research.rates_direction import swing_proxy_pilot as p
from research.rates_direction.swing_proxy_extended import fast_walk_forward, partition_rows


def fixture(n=150):
    idx=pd.date_range('2020-01-01',periods=n,freq='2h',tz='UTC')
    bars=pd.DataFrame({'session':idx.date.astype(str)},index=idx)
    f=pd.DataFrame({'eligible':True,'vol':1+np.arange(n)%7,'trend':np.sign(np.sin(np.arange(n)/4))},index=idx)
    for k,name in enumerate(p.COMBINATIONS): f[name]=np.sign(np.sin(np.arange(n)/(k+2))).astype(int)
    labels=[]
    for i in range(n):
        end=i+13
        labels.append({'target_end_index':end,'target_end':idx[end].isoformat() if end<n else None,
                       'label':p.LABELS[i%3] if end<n else 'censored'})
    labels[47]['label']='ambiguous'; f.loc[idx[61],'eligible']=False
    return bars,f,labels


def test_vectorized_walk_is_identical_to_frozen_reference():
    b,f,y=fixture()
    a=p.walk_forward(b,f,y); z=fast_walk_forward(b,f,y)
    assert a==z


def test_partition_does_not_move_crossing_targets_into_primary():
    b,f,y=fixture(); rows=fast_walk_forward(b,f,y)
    cut=b.index[100]
    partitions=partition_rows(rows,b,cut)
    assert partitions['earlier'] and partitions['overlap'] and partitions['boundary']
    for r in partitions['earlier']: assert b.index[r['outcome']['target_end_index']]<cut
    for r in partitions['overlap']: assert pd.Timestamp(r['origin'])>=cut
    for r in partitions['boundary']:
        assert pd.Timestamp(r['origin'])<cut<=b.index[r['outcome']['target_end_index']]
    assert sum(map(len,partitions.values()))==len(rows)


def test_extended_fast_path_stays_future_invariant():
    b,f,y=fixture(); a=fast_walk_forward(b,f,y)
    f2=f.copy();f2.iloc[100:,:]=f.iloc[100:,:]
    for name in p.COMBINATIONS: f2.loc[f2.index[100:],name]*=-1
    z=fast_walk_forward(b,f2,y)
    assert [r for r in a if r['origin_index']<100]==[r for r in z if r['origin_index']<100]
