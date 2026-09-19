"""Correctness checks for the disposable capacity study, not product acceptance."""
import unittest
from collections import deque
import numpy as np
from rolling_capacity import simulate, make_arrivals


def oracle(arrivals, accounts, cap, window, outages=(), cooldown=0):
    queues=[deque() for _ in range(accounts)]
    last=[-cooldown]*accounts
    waiting=deque();i=0;t=0;served=[]
    while i<len(arrivals) or waiting:
        while i<len(arrivals) and arrivals[i]<=t:
            waiting.append(i);i+=1
        for q in queues:
            while q and q[0]<=t-window:q.popleft()
        if not any(s<=t<e for s,e in outages):
            while waiting:
                free=[k for k,q in enumerate(queues) if len(q)<cap and t-last[k]>=cooldown]
                if not free:break
                k=min(free,key=lambda k:(len(queues[k]),k))
                waiting.popleft();queues[k].append(t);last[k]=t;served.append(t)
        t+=1
        if t>10000:raise AssertionError('oracle bound exceeded')
    return served

class CapacityTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(len(simulate([],3).service),0)
    def test_no_delay_below_cap(self):
        self.assertEqual(simulate([0,1,2],1,cap=3,window=10).service.tolist(),[0,1,2])
    def test_exact_rolling_expiry(self):
        self.assertEqual(simulate([0,0,0,1,9,10],1,cap=3,window=10).service.tolist(),[0,0,0,10,10,10])
    def test_not_calendar_midnight_reset(self):
        self.assertEqual(simulate([9,9,9,10],1,cap=3,window=10).service.tolist(),[9,9,9,19])
    def test_multiple_accounts(self):
        self.assertEqual(simulate([0]*7,2,cap=3,window=10).service.tolist(),[0]*6+[10])
    def test_common_outage(self):
        r=simulate([2,4,6,7,9],2,cap=3,window=10,outages=[(4,8)])
        self.assertEqual(r.service.tolist(),[2,8,8,8,9])
    def test_back_to_back_outages(self):
        self.assertEqual(simulate([1],1,outages=[(0,2),(2,4)]).service.tolist(),[4])
    def test_expiry_inside_outage(self):
        self.assertEqual(simulate([0,1],1,cap=1,window=10,outages=[(9,15)]).service.tolist(),[0,15])
    def test_per_account_spacing(self):
        self.assertEqual(simulate([0]*5,2,cap=3,window=10,cooldown=3).service.tolist(),[0,0,3,3,6])
    def test_cap_still_holds_when_delayed(self):
        a=np.random.default_rng(1).integers(0,400,200);a.sort()
        r=simulate(a,3,cap=7,window=60,outages=[(75,120)],cooldown=2)
        for k in range(3):
            ts=r.service[r.accounts==k]
            for t in ts:self.assertLessEqual(np.sum((ts>t-60)&(ts<=t)),7)
        self.assertTrue(np.all(r.service>=a))
        self.assertTrue(np.all(r.service[1:]>=r.service[:-1]))
    def test_independent_tick_oracle(self):
        for seed in range(100):
            rng=np.random.default_rng(seed);a=np.sort(rng.integers(0,80,60))
            n=1+seed%4;cap=1+seed%6;w=7+seed%9;cooldown=seed%3
            out=[(17,23),(41,49)] if seed%2 else []
            self.assertEqual(simulate(a,n,cap,w,out,cooldown).service.tolist(),
                             oracle(a,n,cap,w,out,cooldown),seed)
    def test_reject_invalid(self):
        for kwargs in ({'accounts':0},{'accounts':True},{'accounts':1,'cap':-1},
                       {'accounts':1,'window':0},{'accounts':1,'cooldown':-1},
                       {'accounts':1,'outages':[(8,4)]},{'accounts':1,'outages':[(4,8),(7,9)]}):
            with self.assertRaises(ValueError):simulate([0],**kwargs)
        for values in ([2,1],[-1,0],[0.,1.]):
            with self.assertRaises(ValueError):simulate(values,1)
    def test_thinning_is_nested_for_same_seed(self):
        p={'weekday':[1.]*24,'weekend':[1.]*24,'arrival_days':3}
        full=make_arrivals(p,6,eligible=1.)
        thin=make_arrivals(p,6,eligible=.8)
        # Multiset inclusion, not only timestamp-set inclusion.
        for t in set(thin):self.assertLessEqual(np.sum(thin==t),np.sum(full==t))
    def test_smooth_matches_profile_integral(self):
        p={'weekday':[1.]*24,'weekend':[1.]*24,'arrival_days':7}
        self.assertEqual(len(make_arrivals(p,1,smooth=True)),168)
    def test_throttle_changes_latency_not_quota_rule(self):
        a=[0]*200
        r=simulate(a,3,cooldown=4)
        self.assertGreater(r.service[-1],0)
        self.assertLess(r.service[-1],1440)
    def test_constant_rate_stable_after_warmup(self):
        a=np.arange(0,1000,2)
        r=simulate(a,1,cap=6,window=10)
        self.assertTrue(np.all(r.service==a))

if __name__=='__main__':unittest.main(verbosity=2)
