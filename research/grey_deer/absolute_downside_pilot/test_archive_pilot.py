"""Tests run on synthetic bars before the registered real-price pilot."""
import unittest
import numpy as np
import pandas as pd
from archive_pilot import make_frame, standardize, fit_logistic, prob

SYMS = ['SPY','QQQ','IWM','XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY']
def bars(n=80):
    idx = pd.bdate_range('2023-01-02', periods=n)
    return {s: pd.DataFrame({'open':100.,'high':102.,'low':98.,'close':100.+np.sin(np.arange(n))}, index=idx) for s in SYMS}

class SpecificationTests(unittest.TestCase):
    def test_two_observation_lag(self):
        data=bars(); base=make_frame(data)
        data['SPY'].iloc[-1, data['SPY'].columns.get_loc('close')]=101.9
        changed=make_frame(data)
        np.testing.assert_allclose(base['X'],changed['X'],equal_nan=True)
    def test_previous_row_not_yet_admitted(self):
        data=bars(); a=make_frame(data)
        data['SPY'].iloc[-2,data['SPY'].columns.get_loc('close')]=101.9
        b=make_frame(data)
        np.testing.assert_allclose(a['X'].iloc[-1],b['X'].iloc[-1])
    def test_two_rows_ago_does_affect_current(self):
        data=bars(); a=make_frame(data)
        data['SPY'].iloc[-3,data['SPY'].columns.get_loc('close')]=101.9
        b=make_frame(data)
        self.assertNotEqual(a['X'].iloc[-1,0],b['X'].iloc[-1,0])
    def test_twenty_row_warmup_plus_lag(self):
        x=make_frame(bars())['X']
        self.assertTrue(x.iloc[:21].isna().any(axis=1).all())
        self.assertTrue(x.iloc[21].notna().all())
    def test_invalid_ohlc_not_a_good_read(self):
        data=bars(); data['XLB'].iloc[30,data['XLB'].columns.get_loc('low')]=103
        result=make_frame(data)
        self.assertTrue(result['X'].iloc[32].isna().any())
        self.assertEqual(result['invalid']['XLB'],1)
    def test_missing_price_not_zero(self):
        data=bars(); data['XLB'].iloc[30,data['XLB'].columns.get_loc('close')]=np.nan
        self.assertTrue(make_frame(data)['X'].iloc[32].isna().any())
    def test_date_alignment_is_required(self):
        data=bars(); data['XLB']=data['XLB'].iloc[1:]
        with self.assertRaises(ValueError): make_frame(data)
    def test_duplicate_dates_refused(self):
        data=bars(); data['SPY'].index=list(data['SPY'].index[:-1])+[data['SPY'].index[-2]]
        with self.assertRaises(ValueError): make_frame(data)
    def test_absolute_endpoint_not_relative(self):
        data=bars(); data['SPY'].iloc[30,data['SPY'].columns.get_loc('close')]=98
        data['SPY'].iloc[30,data['SPY'].columns.get_loc('low')]=97
        self.assertEqual(make_frame(data)['y']['body'].iloc[30],1)
    def test_invalid_target_is_null(self):
        data=bars(); data['SPY'].iloc[30,data['SPY'].columns.get_loc('close')]=np.nan
        self.assertTrue(np.isnan(make_frame(data)['y']['body'].iloc[30]))
    def test_training_only_scaler(self):
        a=np.array([[1.,4.],[3.,4.]])
        train, other, mean, scale=standardize(a,np.array([[100.,4.]]))
        np.testing.assert_allclose(mean,[2.,4.]); np.testing.assert_allclose(scale,[1.,1.])
        self.assertEqual(other[0,0],98.)
    def test_solver_fits_signal_without_weighting(self):
        x=np.linspace(-2,2,100)[:,None]; y=(x[:,0]>0).astype(float)
        coeff=fit_logistic(x,y)
        self.assertGreater(prob(x,coeff)[-1],prob(x,coeff)[0])
        self.assertTrue(np.isfinite(coeff).all())

    def test_decimal_body_threshold_is_inclusive(self):
        data=bars(); row=data['SPY'].index[30]
        data['SPY'].loc[row,['open','high','low','close']]=[100.02,102.,98.,99.0198]
        self.assertEqual(make_frame(data)['y']['body'].loc[row],1.)
    def test_decimal_low_threshold_is_inclusive(self):
        data=bars(); row=data['SPY'].index[30]
        data['SPY'].loc[row,['open','high','low','close']]=[100.02,102.,99.0198,101.]
        self.assertEqual(make_frame(data)['y']['low'].loc[row],1.)

if __name__=='__main__': unittest.main(verbosity=2)
