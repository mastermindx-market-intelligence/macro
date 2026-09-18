"""Synthetic archive-association tests; no market prices or historical outcomes."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd


class ScoreAuditTests(unittest.TestCase):
    def module(self):
        path = Path(__file__).with_name('recorded_score_audit.py')
        self.assertTrue(path.exists(), 'audit implementation absent')
        spec = importlib.util.spec_from_file_location('score_audit_test_target', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_ties_and_monotone_rank(self):
        m = self.module()
        r = m.rank_association(pd.Series([1, 2, 2, 3]), pd.Series([2, 4, 4, 6]))
        self.assertAlmostEqual(r['rho'], 1.)
        self.assertEqual(r['pairs'], 4)
        self.assertEqual(r['reason'], 'defined')

    def test_missing_pairs_remain_disclosed(self):
        r = self.module().rank_association(pd.Series([1., np.nan, 2.]), pd.Series([2., 3., 1.]))
        self.assertAlmostEqual(r['rho'], -1.)
        self.assertEqual(r['pairs'], 2)
        self.assertEqual(r['missing_pairs'], 1)

    def test_constant_and_short_dates_stay_undefined(self):
        m = self.module()
        a = m.rank_association(pd.Series([1, 1]), pd.Series([2, 3]))
        self.assertTrue(np.isnan(a['rho']))
        self.assertEqual(a['reason'], 'constant_score')
        b = m.rank_association(pd.Series([1]), pd.Series([2]))
        self.assertEqual(b['reason'], 'fewer_than_two_pairs')

    def test_equal_date_weighting_and_source_preservation(self):
        m = self.module()
        frame = pd.DataFrame({'as_of': ['2026-01-01']*2 + ['2026-01-02']*10,
            'snapshot_rank_by': ['confluence']*12, 'price_basis': ['adjusted']*12,
            'recorded_horizon_d21': [1, 2] + list(range(10)),
            'ret': [1, 2] + list(reversed(range(10)))})
        before = frame.copy(deep=True)
        dates, result = m.summarize_archive(frame)
        chosen = result[result['ranker'].eq('confluence') & result['price_basis'].eq('adjusted')].iloc[0]
        self.assertAlmostEqual(chosen['equal_date_mean_spearman'], 0., places=12)
        self.assertEqual(chosen['defined_dates'], 2)
        self.assertEqual(len(dates), 2)
        pd.testing.assert_frame_equal(frame, before)
        self.assertEqual(len(result), 6)
        self.assertEqual(int(result['signal_dates'].eq(0).sum()), 5)

    def test_constant_outcome_stays_undefined(self):
        r = self.module().rank_association(pd.Series([1, 2]), pd.Series([3, 3]))
        self.assertEqual(r['reason'], 'constant_outcome')

if __name__ == '__main__': unittest.main(verbosity=2)
