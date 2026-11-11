import importlib.util, unittest
from pathlib import Path
import numpy as np
import pandas as pd

class ComparisonTests(unittest.TestCase):
    def test_known_difference_and_null_exclusion(self):
        path = Path(__file__).with_name('review_comparisons.py')
        self.assertTrue(path.exists(), 'comparison implementation not written')
        spec = importlib.util.spec_from_file_location('review', path)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        d = pd.DataFrame({'event_date':pd.to_datetime(['2010-01-05','2010-01-05','2011-01-05','2011-01-05','2011-01-06']),
                          'arm':['A','B','A','B','A'], 'value':[.1,0,.1,0,np.nan]})
        r = m.compare(d, 'value', reps=200)
        self.assertEqual(r['n_a'],2); self.assertEqual(r['n_b'],2)
        self.assertEqual(r['shared_dates'],2)
        self.assertAlmostEqual(r['pooled_difference'],.1)
        self.assertAlmostEqual(r['shared_date_difference'],.1)
        self.assertAlmostEqual(r['ci95_low'],.1)
        self.assertAlmostEqual(r['ci95_high'],.1)
    def test_disjoint_dates_do_not_become_paired(self):
        path = Path(__file__).with_name('review_comparisons.py')
        self.assertTrue(path.exists(), 'comparison implementation not written')
        spec = importlib.util.spec_from_file_location('review2', path)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        d = pd.DataFrame({'event_date':pd.to_datetime(['2010-01-05','2010-01-06']), 'arm':['A','B'],'value':[.1,0]})
        r = m.compare(d,'value',reps=200)
        self.assertEqual(r['shared_dates'],0)
        self.assertTrue(np.isnan(r['shared_date_difference']))
if __name__ == '__main__': unittest.main(verbosity=2)
