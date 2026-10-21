"""Invented-input tests of R5 timing and self-financing; no market IO."""
import math
import unittest
import numpy as np
import decision_speed_r5 as m


def panel(n=1, t=454):
    return np.zeros((n, t, 13), dtype=float)


def scalar_cost(h,w,c):
    W=sum(h);lo=0.;hi=W
    for _ in range(90):
        v=(lo+hi)/2
        fee=sum(ci*abs(wi*v-hi0) for hi0,wi,ci in zip(h,w,c))
        if v+fee>W:hi=v
        else:lo=v
    return (lo+hi)/2


class RedCore(unittest.TestCase):
    def test_interval_count_strict_reversal(self):
        self.assertEqual(m.first_strict_source(63),32)
        self.assertEqual(m.first_strict_source(20),11)
    def test_costed_switch(self):
        h=np.array([[0.,1.,0.]])
        w=np.array([[0.,0.,1.]])
        r=m.rebalance_many(h,w,.0025)
        self.assertAlmostEqual(r['wealth'][0],(1-.0025)/(1+.0025),places=12)
    def test_cash_hurdle_tie(self):
        q=m.rolling_target(panel(),252,63,0)
        np.testing.assert_array_equal(q[0],np.r_[np.zeros(11,dtype=int),3])


class TimingAndCosts(unittest.TestCase):
    def test_source_delay_adds_to_review_not_price_origin(self):
        self.assertEqual(m.first_execution(63,5,20,0,1),41)
        self.assertEqual(m.first_execution(63,5,20,0,3),81)
    def test_cost_horizon_strict(self):
        c=.0025; d=.001
        h=m.switch_break_even(c,d)
        self.assertGreater(h,5.)
        self.assertLess(h,5.001)
    def test_63_intervals_not_62(self):
        x=panel(); x[0,189,0]=-.5
        q=m.rolling_target(x,252,63,0)
        self.assertEqual(q[0,0],1)
        self.assertEqual(q[0,-1],2)
    def test_late_prices_cannot_change_target(self):
        x=panel(); x[0,252,:3]=1
        before=m.rolling_target(x,252,63,0)
        x[:,253:,3:6]=2.0
        np.testing.assert_array_equal(before,m.rolling_target(x,252,63,0))
    def test_delay_ignores_recent_price(self):
        x=panel();x[0,252,:3]=1
        self.assertEqual(m.rolling_target(x,252,63,5)[0,-1],3)
    def test_ties_are_deterministic(self):
        x=panel(); x[0,252,:11]=.1
        q=m.rolling_target(x,252,63,0)
        np.testing.assert_array_equal(q[0,:11],np.r_[np.ones(3),np.zeros(8)])
    def test_benchmark_subtraction_does_not_change_order(self):
        x=panel();x[0,252,:3]=1
        q=m.rolling_target(x,252,63,0); x[0,252,12]=900
        np.testing.assert_array_equal(q,m.rolling_target(x,252,63,0))
    def test_incomplete_history_refused(self):
        with self.assertRaises(ValueError):m.rolling_target(panel(t=63),62,63,0)
    def test_nonfinite_refused(self):
        x=panel();x[0,252,2]=np.nan
        with self.assertRaises(ValueError):m.rolling_target(x,252,63,0)
    def test_duplicate_source_does_not_confirm(self):
        a=np.zeros((1,12),int);a[0,-1]=3
        b=np.zeros((1,12),int);b[0,0]=3
        st=m.Confirmation(a,3,10)
        np.testing.assert_array_equal(st.observe(b,11),a)
        np.testing.assert_array_equal(st.observe(b,11),a)
        np.testing.assert_array_equal(st.observe(b,12),a)
        np.testing.assert_array_equal(st.observe(b,13),b)
    def test_confirmation_resets(self):
        a=np.zeros((1,12),int);a[0,-1]=3
        b=np.zeros((1,12),int);b[0,0]=3
        s=m.Confirmation(a,3,1)
        s.observe(b,2);s.observe(a,3);s.observe(b,4)
        np.testing.assert_array_equal(s.observe(b,5),a)
        np.testing.assert_array_equal(s.observe(b,6),b)
    def test_clock_regression_refused(self):
        a=np.zeros((1,12),int);a[0,-1]=3
        s=m.Confirmation(a,3,4)
        with self.assertRaises(ValueError):s.observe(a,3)
    def test_vector_solver_matches_independent_scalar(self):
        rng=np.random.default_rng(7)
        h=rng.random((128,13));w=rng.random((128,13));w/=w.sum(axis=1)[:,None]
        for c in (0.,.0005,.0025):
            r=m.rebalance_many(h,w,c)
            for j in range(128):
                ref=scalar_cost(h[j],w[j],np.r_[0.,np.repeat(c,12)])
                self.assertAlmostEqual(r['wealth'][j]/ref,1.,places=12)
            np.testing.assert_allclose(h.sum(axis=1),r['holdings'].sum(axis=1)+r['fees'],rtol=1e-12)
    def test_cash_purchase_turnover_one_leg(self):
        r=m.rebalance_many(np.array([[1.,0.]]),np.array([[0.,1.]]),.001)
        self.assertAlmostEqual(r['traded'][0],1/1.001,places=12)
    def test_costless_fund_trade_is_turnover(self):
        r=m.rebalance_many(np.array([[0.,1.,0.]]),np.array([[0.,0.,1.]]),0.)
        self.assertEqual(r['traded'][0],2.)
    def test_flat_roundtrip(self):
        x=panel();p=m.Policy('test',63,1,1)
        r=m.simulate(x,p,0,.001)
        self.assertAlmostEqual(r['terminal'][0],.999/1.001,places=12)
        self.assertEqual(r['membership_changes'][0],0)
        self.assertAlmostEqual(r['max_drawdown'][0],1-.999/1.001,places=12)
    def test_same_rank_fast_review_does_not_force_daily_trades(self):
        x=panel();x[:,:,:3]=np.arange(x.shape[1])[None,:,None]*.001
        a=m.simulate(x,m.Policy('a',63,1,1),0,.001)
        b=m.simulate(x,m.Policy('b',63,20,1),0,.001)
        np.testing.assert_allclose(a['terminal'],b['terminal'],rtol=1e-12)
        np.testing.assert_allclose(a['turnover'],b['turnover'],rtol=1e-12)
    def test_execution_interval_earns_old_holdings_return(self):
        x=panel(); # Initial bill exposure. New candidates cross at anchor253.
        x[0,253:,:3]=.1
        x[0,254:,:3]=.4
        r=m.simulate(x,m.Policy('t',20,1,1),0,0.,trace=True)
        # Signal after253 executes close254; that .3 log jump must not be earned.
        self.assertAlmostEqual(r['wealth_path'][0,1],1.,places=12)
        self.assertEqual(r['targets'][0,1,:3].sum(),3)
    def test_target_prefix_independence(self):
        rng=np.random.default_rng(19);x=np.cumsum(rng.normal(0,.01,(2,454,13)),axis=1)
        a=m.simulate(x,m.Policy('t',20,1,3),0,.001,trace=True)
        x[:,300:,:]=x[:,300:,:]+np.arange(154)[None,:,None]
        b=m.simulate(x,m.Policy('t',20,1,3),0,.001,trace=True)
        np.testing.assert_array_equal(a['targets'][:,:48],b['targets'][:,:48])
        np.testing.assert_allclose(a['wealth_path'][:,:47],b['wealth_path'][:,:47])
    def test_no_terminal_rebalance_only_sale(self):
        x=panel();x[0,252:,:3]=.1
        a=m.simulate(x,m.Policy('t',20,1,1),0,.001,trace=True)
        x[0,452,3:6]=2 # Would propose a terminal-date new target, forbidden.
        b=m.simulate(x,m.Policy('t',20,1,1),0,.001,trace=True)
        np.testing.assert_array_equal(a['targets'][:,-1],b['targets'][:,-1])
    def test_no_authority_flags(self):
        r=m.simulate(panel(),m.Policy('t',63,1,1),0,.001)
        self.assertFalse(r['investment_authority']);self.assertTrue(r['synthetic'])
    def test_evaluation_onset_does_not_affect_decisions(self):
        rng=np.random.default_rng(39)
        x=np.cumsum(rng.normal(0,.008,(2,454,13)),axis=1)
        a=m.simulate(x,m.Policy('t',20,1,1),0,.001,trace=True)
        previous=m.CHANGE
        try:
            m.CHANGE=333
            b=m.simulate(x,m.Policy('t',20,1,1),0,.001,trace=True)
        finally:m.CHANGE=previous
        np.testing.assert_array_equal(a['targets'],b['targets'])
        np.testing.assert_array_equal(a['terminal'],b['terminal'])
    def test_cost_increase_cannot_improve_identical_target_paths(self):
        rng=np.random.default_rng(33)
        x=np.cumsum(rng.normal(0,.008,(3,454,13)),axis=1)
        a=m.simulate(x,m.Policy('t',20,1,1),0,.0005,trace=True)
        b=m.simulate(x,m.Policy('t',20,1,1),0,.0025,trace=True)
        np.testing.assert_array_equal(a['targets'],b['targets'])
        self.assertTrue(np.all(a['terminal']>=b['terminal']))
    def test_bad_shape_cost_and_weights(self):
        for h,w,c in [(np.ones((1,2)),np.ones((1,2)),.001),
                      (np.array([[1.,-1.]]),np.array([[0.,1.]]),.001),
                      (np.array([[1.,0.]]),np.array([[0.,1.]]),.1)]:
            with self.assertRaises(ValueError):m.rebalance_many(h,w,c)

if __name__=='__main__':unittest.main()
