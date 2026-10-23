import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from selective_analogue_reference_v1 import *

class SelectiveReferenceTests(unittest.TestCase):
    def setUp(self):
        self.t=datetime(2026,1,1,tzinfo=timezone.utc)
    def rows(self,n=60, *, actual=.8,analogue=.8):
        return [PastForecast(str(i),'fixed-v1',self.t-timedelta(days=200+i),
                self.t-timedelta(days=150+i),.5,analogue,actual,.1+i*.001) for i in range(n)]
    def calc(self,history,**kw):
        args=dict(profile_id='fixed-v1',decision_at=self.t,baseline=.5,
                  analogue=.8,nearest_rms_distance=.1,history=history)
        args.update(kw);return past_only_forecast(**args)
    def test_cold_start(self):
        r=self.calc(self.rows(59));self.assertEqual(r['forecast'],.5)
        self.assertEqual(r['reason'],'COLD_START_BASELINE_ONLY')
    def test_fixed_shrinkage_not_full_fitted_gain(self):
        r=self.calc(self.rows());self.assertAlmostEqual(r['fitted_alpha'],.75)
        self.assertAlmostEqual(r['forecast'],.725)
    def test_exact_threshold_inclusive(self):
        r=self.calc(self.rows());t=r['distance_threshold']
        self.assertGreater(self.calc(self.rows(),nearest_rms_distance=t)['used_alpha'],0)
    def test_outside_support_falls_back(self):
        r=self.calc(self.rows(),nearest_rms_distance=100)
        self.assertEqual(r['forecast'],.5);self.assertEqual(r['used_alpha'],0)
    def test_equal_maturation_clock_excluded(self):
        a=self.rows();a[-1]=replace(a[-1],outcome_available_at=self.t)
        self.assertEqual(self.calc(a)['n_matured'],59)
    def test_future_targets_cannot_change_fit(self):
        a=self.rows();future=PastForecast('future','fixed-v1',self.t-timedelta(days=5),
            self.t+timedelta(days=5),.5,1,1,999)
        first=self.calc(a)
        self.assertEqual(first,self.calc(a+[future]))
        self.assertEqual(first,self.calc(a+[replace(future,actual=0)]))
    def test_other_profile_cannot_change_fit(self):
        a=self.rows();extra=replace(a[0],query_id='other',profile_id='other-space',actual=0)
        self.assertEqual(self.calc(a),self.calc(a+[extra]))
    def test_duplicate_queries_rejected(self):
        a=self.rows()
        with self.assertRaises(ValueError):self.calc(a+[a[0]])
    def test_old_issued_future_outcome_excluded(self):
        a=self.rows();future=replace(a[0],query_id='delayed',outcome_available_at=self.t+timedelta(days=2))
        self.assertEqual(self.calc(a),self.calc(a+[future]))
    def test_no_positive_error_covariance_zero_alpha(self):
        r=self.calc(self.rows(actual=.2));self.assertEqual(r['fitted_alpha'],0)
    def test_identical_candidate_baseline_zero_alpha(self):
        r=self.calc(self.rows(analogue=.5));self.assertEqual(r['fitted_alpha'],0)
    def test_coefficient_cannot_exceed_one(self):
        r=self.calc(self.rows(actual=1,analogue=.6));self.assertEqual(r['fitted_alpha'],1)
    def test_no_match_returns_explicit_fallback(self):
        r=self.calc(self.rows(),analogue=None,nearest_rms_distance=None)
        self.assertEqual(r['reason'],'NO_TECHNICAL_MATCH');self.assertEqual(r['forecast'],.5)
    def test_no_distance_with_forecast_rejected(self):
        with self.assertRaises(ValueError):self.calc(self.rows(),nearest_rms_distance=None)
    def test_clock_and_outcome_validation(self):
        r=self.rows()[0]
        for kwargs in [{'actual':1.1},{'baseline':float('nan')},
                       {'outcome_available_at':r.issued_at},
                       {'issued_at':datetime(2025,1,1)},
                       {'nearest_rms_distance':-1}]:
            with self.assertRaises(ValueError):replace(r,**kwargs)
    def test_quantile_is_fixed_linear_interpolation(self):
        self.assertEqual(linear_quantile([0,10],.95),9.5)
    def test_selection_counterexample(self):
        r=evaluation_table([0,0,1,1],[0,0,.5,.5],[.1,.1,None,None])
        self.assertLess(r['candidate_same_covered_mse'],r['baseline_all_mse'])
        self.assertGreater(r['candidate_same_covered_mse'],r['baseline_same_covered_mse'])
        self.assertGreater(r['full_fallback_policy_mse'],r['baseline_all_mse'])
    def test_all_abstained_explicit(self):
        r=evaluation_table([0,1],[.2,.8],[None,None])
        self.assertIsNone(r['candidate_same_covered_mse'])
        self.assertEqual(r['baseline_all_mse'],r['full_fallback_policy_mse'])
    def test_unknown_targets_cannot_be_silently_dropped(self):
        with self.assertRaises((TypeError,ValueError)):evaluation_table([0,None],[.2,.8],[.3,None])
    def test_empty_and_mismatched_samples_rejected(self):
        for inputs in [([],[],[]),([0],[0,1],[0])]:
            with self.assertRaises(ValueError):evaluation_table(*inputs)

if __name__=='__main__':unittest.main(verbosity=2)
