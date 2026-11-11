"""Synthetic tests; no market returns or source stores read."""
import importlib.util, unittest
from pathlib import Path
import pandas as pd

class JoinTests(unittest.TestCase):
    def module(self):
        p = Path(__file__).with_name('recorded_context_join.py')
        self.assertTrue(p.exists(), 'recorded-context implementation absent')
        s = importlib.util.spec_from_file_location('context_join', p)
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        return m
    def frames(self):
        g = pd.DataFrame({'as_of':['2026-06-24','2026-06-30','2026-06-30','2026-07-01'],
                          'lane':['buy']*4,'ticker':['X','A','A','B'],'horizon':[5,5,10,5]})
        c = pd.DataFrame({'as_of':['2026-06-30'],'lane':['buy'],'ticker':['A'],
                          'snapshot_ref':['abc'],'recorded_horizon_d3':[.58]})
        return g,c
    def test_denominator_cutoff_and_unknown(self):
        m = self.module(); g,c = self.frames()
        r = m.attach_context(g,c,'2026-06-25')
        self.assertEqual(len(r),4)
        self.assertEqual(r.context_status.tolist(),['pre_selection_era','attached','attached','missing_snapshot'])
        self.assertTrue(pd.isna(r.iloc[3].recorded_horizon_d3))
        self.assertEqual(r.iloc[1].recorded_horizon_d3,.58)
    def test_duplicate_context_refused(self):
        m = self.module(); g,c = self.frames()
        with self.assertRaises(ValueError): m.attach_context(g,pd.concat([c,c]),'2026-06-25')
    def test_duplicate_grade_keys_refused(self):
        m = self.module(); g,c = self.frames()
        with self.assertRaises(ValueError): m.attach_context(pd.concat([g,g]),c,'2026-06-25')
    def test_market_context_requires_exact_date(self):
        m = self.module(); g,c = self.frames()
        r = m.attach_context(g,c,'2026-06-25')
        states = pd.DataFrame({'market21':['both_up']},index=pd.to_datetime(['2026-06-30']))
        z = m.attach_market_context(r,states)
        self.assertEqual(z.loc[1,'market21'],'both_up')
        self.assertTrue(pd.isna(z.loc[3,'market21']))
        self.assertEqual(len(z),len(g))
    def test_existing_grade_columns_unchanged(self):
        m = self.module(); g,c = self.frames()
        g['frozen_example']=[.1,.2,.2,None]
        r = m.attach_context(g,c,'2026-06-25')
        pd.testing.assert_frame_equal(r[g.columns],g)

if __name__ == '__main__': unittest.main(verbosity=2)
