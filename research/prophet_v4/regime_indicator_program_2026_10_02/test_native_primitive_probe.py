import unittest
import numpy as np
import pandas as pd
from native_primitive_probe import rsi, _ema, fixtures, terminal_values, run_probe


class TestPrimitiveIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=fixtures();cls.tv=terminal_values(cls.cases)

    def test_native_rsi_pure_advance_differs(self):
        m=rsi(pd.Series(self.cases['rising']))
        self.assertEqual(int(m.notna().sum()),0)
        self.assertTrue(all(v==100 for v in self.tv['rising']['rsi'][14:]))

    def test_native_rsi_flat_differs(self):
        self.assertEqual(int(rsi(pd.Series(self.cases['flat'])).notna().sum()),0)
        self.assertTrue(all(v==50 for v in self.tv['flat']['rsi'][14:]))

    def test_native_rsi_decline_agrees(self):
        np.testing.assert_allclose(rsi(pd.Series(self.cases['falling'])),
                                   np.array(self.tv['falling']['rsi'],dtype=float),equal_nan=True)

    def test_short_history_not_invented(self):
        self.assertTrue(all(v is None for v in self.tv['short']['rsi']))
        self.assertTrue(rsi(pd.Series(self.cases['short'])).isna().all())

    def test_smoother_seed_is_not_equal(self):
        c=pd.Series(self.cases['rising'])
        self.assertNotAlmostEqual(_ema(c,14).iloc[13],self.tv['rising']['ema'][13])
        self.assertEqual(self.tv['rising']['ema'][13],106.5)

    def test_missing_input_policies_distinct(self):
        c=pd.Series(self.cases['gapped'],dtype=float)
        self.assertTrue(np.isfinite(_ema(c,14).iloc[36]))
        self.assertIsNone(self.tv['gapped']['ema'][36])

    def test_numeric_native_prefix_invariance(self):
        # Test the primitive, NOT the resampler's live/finalized endpoint semantics.
        short={'prefix':self.cases['oscillating'][:200]}
        got=terminal_values(short)['prefix']['rsi']
        np.testing.assert_allclose(np.array(got,dtype=float),
            np.array(self.tv['oscillating']['rsi'][:200],dtype=float),equal_nan=True)
        c=pd.Series(self.cases['oscillating'])
        np.testing.assert_allclose(rsi(c.iloc[:200]),rsi(c).iloc[:200],equal_nan=True)

    def test_usable_history_does_not_imply_convergence(self):
        rows=run_probe()['history_window_sensitivity']
        self.assertIsNotNone(rows[0]['trailing_history_histogram'])
        self.assertGreater(rows[0]['absolute_delta'],0.9)
        self.assertLess(rows[-1]['absolute_delta'],0.00001)

    def test_numeric_differences_do_not_prove_mature_event_changes(self):
        obs=run_probe()['observations']['oscillating']
        cases=obs['hypothetical_primitive_substitution_not_terminal_macdx']
        self.assertGreater(cases['80']['max_histogram_difference'],0)
        self.assertEqual(cases['80']['cross_disagreement_indices'],[])

    def test_report_cannot_claim_authority(self):
        self.assertFalse(any(run_probe()['authority'].values()))


if __name__=='__main__':unittest.main()
