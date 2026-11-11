"""Mechanical tests on synthetic prices; no market outcomes read."""
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
import run_extension as m

class ExtensionTests(unittest.TestCase):
    def test_endpoint_and_censoring(self):
        c = pd.Series([100.,110.,90.,120.])
        v = m.payoff(c,c,np.array([1,3]),np.array([3,5]),np.ones(2),paths=True)
        self.assertAlmostEqual(v['r'][0],120/110-1)
        self.assertAlmostEqual(v['mae'][0],90/110-1)
        self.assertTrue(np.isnan(v['r'][1]))
    def test_memory_identity(self):
        self.assertAlmostEqual((1-m.alpha_for(26,2/3))**3,(1-m.alpha_for(26))**2)
    def test_complete_event_builder(self):
        dates = pd.bdate_range('2018-01-01',periods=2300)
        x = np.arange(len(dates))
        c = pd.Series(100*np.exp(.0001*x+.09*np.sin(x/19)+.025*np.sin(x/5)),index=dates)
        frame = pd.DataFrame({'date':dates},index=dates)
        keys = {'1D':x,'2D':x//2,'3D':x//3,'1W':dates.to_period('W-FRI'),'1M':dates.to_period('M')}
        bounds = {tf:frame.groupby(k)['date'].max() for tf,k in keys.items()}
        study = SimpleNamespace(spy=c,native=lambda prices,tf:prices.reindex(bounds[tf]))
        result = m.build_name('SYNTHETIC',c,study,m.stress_spells(c))
        self.assertIsInstance(result,pd.DataFrame,'completed event builder must return an outcome table')
        self.assertFalse(result.empty)
        self.assertLessEqual(result.event_date.max(),pd.Timestamp('2025-12-31'))
        self.assertTrue({'cal_21_r','cal_63_r','native_10_r','opposite_252_r','common252'}.issubset(result.columns))
if __name__ == '__main__': unittest.main(verbosity=2)
