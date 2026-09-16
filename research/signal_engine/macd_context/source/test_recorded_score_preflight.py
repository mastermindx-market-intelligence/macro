"""Metadata-only tests: no recorded prices or outcome columns."""
import importlib.util, unittest
from pathlib import Path
import pandas as pd

class TemporalSupportTests(unittest.TestCase):
    def module(self):
        p = Path(__file__).with_name('recorded_score_preflight.py')
        self.assertTrue(p.exists(), 'preflight is not implemented')
        s = importlib.util.spec_from_file_location('score_preflight_test', p)
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        return m
    def test_overlapping_windows_have_no_temporal_training(self):
        m = self.module(); cal = pd.bdate_range('2026-01-01', periods=60)
        f = pd.DataFrame({'as_of':cal[[1,2,3]], 'entry_date':cal[[2,3,4]], 'horizon':[21]*3})
        r = m.window_support(m.attach_bounds(f,cal))
        self.assertEqual(r['dates_with_optimistic_prior_training'],0)
        self.assertTrue(r['all_windows_share_calendar_interval'])
    def test_separated_windows_can_have_prior_training(self):
        m = self.module(); cal = pd.bdate_range('2026-01-01', periods=60)
        f = pd.DataFrame({'as_of':cal[[0,30]], 'entry_date':cal[[1,31]], 'horizon':[21]*2})
        r = m.window_support(m.attach_bounds(f,cal))
        self.assertEqual(r['dates_with_optimistic_prior_training'],1)
        self.assertEqual(r['max_optimistic_prior_training_dates'],1)
    def test_endpoint_equal_to_observation_is_not_prior(self):
        m = self.module(); cal = pd.bdate_range('2026-01-01', periods=60)
        f = pd.DataFrame({'as_of':cal[[0,22]], 'entry_date':cal[[1,23]], 'horizon':[21]*2})
        self.assertEqual(m.window_support(m.attach_bounds(f,cal))['dates_with_optimistic_prior_training'],0)
