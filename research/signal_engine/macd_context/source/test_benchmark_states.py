import unittest
import numpy as np
import pandas as pd
from benchmark_overlay import market_states

class StateTests(unittest.TestCase):
    def prices(self):
        d = pd.bdate_range('2020-01-01',periods=260)
        return pd.DataFrame({'SPY':100+np.arange(260)*.1,'RSP':100-np.arange(260)*.05},index=d)
    def test_warmup_is_unknown(self):
        p = self.prices()
        s = market_states(p)
        self.assertTrue(s.market200.iloc[:199].eq('unknown').all())
        self.assertTrue(s.market21.iloc[:21].eq('unknown').all())
        self.assertEqual(s.market200.iloc[-1],'cap_above_equal_below')
        self.assertEqual(s.market21.iloc[-1],'cap_up_equal_down')
    def test_future_changes_cannot_revise_past_state(self):
        p = self.prices()
        expected = market_states(p.iloc[:220])
        changed = p.copy()
        changed.iloc[220:] = 9999
        pd.testing.assert_frame_equal(expected,market_states(changed).iloc[:220])
    def test_missing_current_price_is_not_bearish(self):
        p = self.prices()
        p.iloc[-1,1] = np.nan
        s = market_states(p)
        self.assertEqual(s.market200.iloc[-1],'unknown')
        self.assertEqual(s.market21.iloc[-1],'unknown')
if __name__ == '__main__': unittest.main(verbosity=2)
