import unittest
import numpy as np
import pandas as pd
from etf_mechanism_pilot import features,event_regime,grade,block_means,contrasts,cell_stats,normalize,event_rows


class TestEtfMechanismPilot(unittest.TestCase):
    def setUp(self):
        self.cal=pd.bdate_range('2020-01-01',periods=50)
        self.spy=pd.Series(100.,index=self.cal)
        self.q=pd.Series(np.arange(50,dtype=float)+100,index=self.cal)
        self.p={'SPY':self.spy,'RSP':self.spy,'QQQ':self.q}

    def test_next_session_close_and_equal_horizon(self):
        x=grade(self.cal[4],'QQQ',self.p)
        self.assertEqual(x['entry_date'],self.cal[5].date().isoformat())
        self.assertEqual(x['exit_date'],self.cal[15].date().isoformat())
        self.assertAlmostEqual(x['asset_return_pct'],100*(115/105-1))

    def test_round_trip_cost_not_per_session(self):
        x=grade(self.cal[4],'QQQ',self.p)
        self.assertAlmostEqual(x['asset_return_pct']-x['net_asset_return_pct'],.2)

    def test_no_end_window_fill(self):
        self.assertEqual(grade(self.cal[-2],'QQQ',self.p)['reason'],'unmatured')

    def test_missing_exact_entry_not_forward_filled(self):
        self.p['QQQ']=self.q.drop(self.cal[5])
        self.assertEqual(grade(self.cal[4],'QQQ',self.p)['reason'],'missing_exact_price')

    def test_signal_session_never_used_for_regime(self):
        f=pd.DataFrame({'real_change_5':1.,'participation_5':-1.},index=self.cal)
        f.loc[self.cal[10]]=[-1.,1.]
        self.assertEqual(event_regime(self.cal[10],f),('hidden_fragility',self.cal[9].date().isoformat()))

    def test_calendar_holiday_uses_strictly_prior_session(self):
        f=pd.DataFrame({'real_change_5':-1.,'participation_5':1.},index=self.cal)
        saturday=self.cal[self.cal.dayofweek==4][0]+pd.Timedelta(days=1)
        self.assertEqual(event_regime(saturday,f)[1],(saturday-pd.Timedelta(days=1)).date().isoformat())

    def test_unknown_never_benign(self):
        f=pd.DataFrame({'real_change_5':np.nan,'participation_5':1.},index=self.cal)
        self.assertEqual(event_regime(self.cal[10],f)[0],'unknown')

    def test_real_yield_carry_is_bounded(self):
        rates=pd.Series([1.],index=[self.cal[0]])
        f=features(self.p,rates)
        self.assertTrue(f.loc[self.cal[8],'real_change_5']!=f.loc[self.cal[8],'real_change_5'])

    def test_future_rate_change_cannot_change_earlier_feature(self):
        rates=pd.Series(np.arange(50,dtype=float),index=self.cal)
        a=features(self.p,rates)
        rates.iloc[25:]+=999
        b=features(self.p,rates)
        pd.testing.assert_frame_equal(a.iloc[:25],b.iloc[:25])

    def test_state_signs_are_not_fitted(self):
        f=pd.DataFrame({'real_change_5':[1.,0.,1.], 'participation_5':[-1.,0.,1.]},index=self.cal[:3])
        self.assertEqual(event_regime(self.cal[1],f)[0],'hidden_fragility')
        self.assertEqual(event_regime(self.cal[2],f)[0],'relief_broadening')
        self.assertEqual(event_regime(self.cal[3],f)[0],'mixed')

    def test_identical_policies_have_zero_paired_block_contrast(self):
        qs=pd.period_range('2010Q1','2014Q4',freq='Q').astype(str).tolist()
        rows=[]
        for i,q in enumerate(qs):
            month=str(pd.Period(q).start_time.to_period('M'))
            for grain in ('1D','3D'):
                for state,extra in [('hidden_fragility',-2),('relief_broadening',2)]:
                    rows.append({'family':'price_macd','grain':grain,'regime':state,'graded':True,
                                 'quarter':q,'month':month,'net_excess_pct':float(i+extra)})
        got=contrasts(rows,'2010-01-01','2014-12-31',draws=200)
        x=next(x for x in got if x['family']=='price_macd' and x['contrast'].startswith('3D_minus'))
        self.assertTrue(x['qualified']);self.assertEqual(x['mean_difference_pp'],0)
        self.assertEqual(x['interval95_pp'],[0.,0.])

    def test_replicated_rows_do_not_manufacture_month_contrast(self):
        row={'family':'price_macd','grain':'1D','regime':'hidden_fragility','graded':True,
             'quarter':'2020Q1','month':'2020-01','net_excess_pct':1.}
        out=contrasts([row]*10000,'2020-01-01','2020-12-31',draws=20)
        self.assertFalse(any(x['qualified'] for x in out))

    def test_no_event_denominator_is_explicit(self):
        x=cell_stats([]);self.assertIsNone(x['mean_net_excess_pct'])
        self.assertEqual(x['events'],0)

    def test_future_first_observation_does_not_backfill(self):
        rates=pd.Series([1.,2.],index=self.cal[[30,35]])
        f=features(self.p,rates)
        self.assertTrue(f['real_change_5'].iloc[:30].isna().all())

    def test_holiday_label_entry_is_next_observed_session(self):
        fri=self.cal[self.cal.dayofweek==4][1]
        label=fri+pd.Timedelta(days=1)
        got=grade(label,'QQQ',self.p)
        self.assertEqual(got['entry_date'],(fri+pd.Timedelta(days=3)).date().isoformat())

    def test_raw_cross_does_not_fire_from_nan(self):
        pp=dict(self.p,IWM=self.q,SOXX=self.q)
        def h(c):
            out=pd.Series(-1.,index=c.index);out.iloc[:3]=np.nan
            out.iloc[3]=1.;out.iloc[20]=1.
            return out
        ns={'macd_hist':h,'_rsi_macd':lambda c:(h(c),pd.Series(0.,index=c.index)),
            '_tf_bars':lambda c,n:(c,None),
            '_completed_resample':lambda c,r:(c,pd.Series(c.index,index=c.index))}
        f=pd.DataFrame({'real_change_5':1.,'participation_5':-1.},index=self.cal)
        rows=event_rows(pp,f,ns)
        self.assertEqual(len(rows),3*4*2)
        self.assertEqual({r['signal_date'] for r in rows},{self.cal[20].date().isoformat()})

    def test_normalize_excludes_recent_context_from_pilot(self):
        source=pd.Series([1.,2.],index=pd.to_datetime(['2026-01-30','2026-09-30']))
        self.assertEqual(len(normalize(source)),1)

    def test_duplicate_dates_rejected(self):
        with self.assertRaises(ValueError):normalize(pd.Series([1.,2.],index=[self.cal[0]]*2))

    def test_block_means_keep_within_quarter_rows_together(self):
        rows=[{'quarter':'2020Q1','net_excess_pct':1.},{'quarter':'2020Q1','net_excess_pct':3.},
              {'quarter':'2020Q2','net_excess_pct':10.}]
        out=block_means(rows,['2020Q1','2020Q2'],np.array([[2,0],[0,2],[1,1]]))
        np.testing.assert_allclose(out,[2,10,14/3])


if __name__=='__main__':unittest.main()
