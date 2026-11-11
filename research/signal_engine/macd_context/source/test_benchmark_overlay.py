import importlib.util, unittest
from pathlib import Path
import numpy as np
import pandas as pd

class BenchmarkTests(unittest.TestCase):
    def module(self):
        path = Path(__file__).with_name('benchmark_overlay.py')
        self.assertTrue(path.exists(), 'benchmark overlay is not implemented')
        spec = importlib.util.spec_from_file_location('bench_overlay', path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    def test_exact_endpoints_and_missing_is_unknown(self):
        m = self.module()
        s = pd.Series([100.,110.],index=pd.to_datetime(['2020-01-02','2020-01-06']))
        result = m.endpoint_return(s,pd.to_datetime(['2020-01-02','2020-01-03']),pd.to_datetime(['2020-01-06','2020-01-06']))
        self.assertAlmostEqual(result[0],.10)
        self.assertTrue(np.isnan(result[1]))
    def test_benchmark_changes_hit_not_same_date_order(self):
        m = self.module()
        d = pd.to_datetime(['2020-01-02','2020-01-03'])
        spy = m.endpoint_return(pd.Series([100.,105.],index=d),d[:1],d[1:])[0]
        rsp = m.endpoint_return(pd.Series([100.,98.],index=d),d[:1],d[1:])[0]
        stock = np.array([.03,.01])
        a, b = stock-spy, stock-rsp
        self.assertFalse(a[0]>0); self.assertTrue(b[0]>0)
        np.testing.assert_array_equal(np.argsort(a),np.argsort(b))
        np.testing.assert_allclose(b-a,spy-rsp)
if __name__ == '__main__': unittest.main(verbosity=2)
