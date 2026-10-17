"""Reference tests for a synthetic algebra diagnostic, not product-model tests."""
import math
import unittest
import numpy as np
import regime_conditioning_r4 as m

class RegimeDiagnosticTests(unittest.TestCase):
    def test_covariance_eigenvalues(self):
        v=m.covariance(12,0.6)
        want=[0.4/12]*10+[7/12]
        np.testing.assert_allclose(np.linalg.eigvalsh(v),want,atol=1e-12)

    def test_dense_posterior_matches_decomposition(self):
        rng=np.random.default_rng(7);y=rng.normal(size=(7,11));a=np.linspace(-.3,.3,11)
        v=m.covariance(12,.6); k=.16*np.linalg.inv(.16*np.eye(11)+v)
        actual=m.estimates(y,a,12,.4,.6)['joint_oracle']
        np.testing.assert_allclose(actual,a+(y-a)@k.T,atol=1e-12)

    def test_hard_cell_equals_data(self):
        y=np.arange(33,dtype=float).reshape(3,11);a=np.zeros(11)
        np.testing.assert_allclose(m.estimates(y,a,4,.1,.6)['hard_cell'],y)

    def test_zero_tau_returns_prior(self):
        y=np.arange(22,dtype=float).reshape(2,11);a=np.linspace(-.3,.3,11)
        est=m.estimates(y,a,4,0,.6)
        for model in ['unconditioned','scalar_oracle','joint_oracle']:
            np.testing.assert_allclose(est[model],np.broadcast_to(a,y.shape))

    def test_stable_pooling_break_even(self):
        a=np.zeros(11);r=m.analytic_risks(a,a,1,4,.4,.6)
        self.assertAlmostEqual(r['unconditioned'],.16)
        self.assertAlmostEqual(r['hard_cell'],.25)
        self.assertLess(r['unconditioned'],r['hard_cell'])

    def test_high_support_hard_cell_improves(self):
        a=np.zeros(11);r=m.analytic_risks(a,a,1,48,.4,.6)
        self.assertLess(r['hard_cell'],r['unconditioned'])

    def test_reversal_risk_is_not_stable_risk(self):
        a=np.zeros(11);r=m.analytic_risks(a,a,-1,12,.4,.6)
        self.assertAlmostEqual(r['hard_cell'],4*.16+1/12)
        self.assertGreater(r['hard_cell'],r['unconditioned'])

    def test_wrong_center_bias(self):
        a=np.linspace(-.3,.3,11);r=m.analytic_risks(a,-a,1,12,.1,0)
        self.assertAlmostEqual(r['unconditioned'],float(np.mean((2*a)**2))+.01)
        self.assertAlmostEqual(r['hard_cell'],1/12)

    def test_analytic_risk_matches_dense_matrix(self):
        a=np.linspace(-.3,.3,11);am=-a;v=m.covariance(12,.6);k=.16*np.linalg.inv(.16*np.eye(11)+v)
        b=am-a;i=np.eye(11)
        want=(np.linalg.norm((i-k)@b)**2+.16*np.trace((k+i)@(k+i).T)+np.trace(k@v@k.T))/11
        self.assertAlmostEqual(m.analytic_risks(a,am,-1,12,.4,.6)['joint_oracle'],want)

    def test_uniform_positive_shrink_does_not_change_selection(self):
        y=np.random.default_rng(18).normal(size=(13,11));a=np.zeros(11)
        es=m.estimates(y,a,12,.4,.6);truth=y*.1
        wanted=m.decision_metrics(es['hard_cell'],truth)['selected']
        for model in ['scalar_oracle','joint_oracle']:
            np.testing.assert_array_equal(m.decision_metrics(es[model],truth)['selected'],wanted)

    def test_stable_tie_order(self):
        z=np.zeros((2,11))
        np.testing.assert_array_equal(m.decision_metrics(z,z)['selected'],[[0,1,2],[0,1,2]])

    def test_regret_nonnegative(self):
        rng=np.random.default_rng(22);pred=rng.normal(size=(8,11));truth=rng.normal(size=(8,11))
        self.assertTrue(np.all(m.decision_metrics(pred,truth)['regret']>=-1e-12))

    def test_oracle_has_zero_regret(self):
        truth=np.random.default_rng(28).normal(size=(5,11));d=m.decision_metrics(truth,truth)
        np.testing.assert_allclose(d['regret'],0,atol=1e-12)
        np.testing.assert_allclose(d['oracle_utility']-d['utility'],0,atol=1e-12)

    def test_hurdle_equality_does_not_act(self):
        d=m.decision_metrics(np.full((1,11),.05),np.ones((1,11)))
        self.assertFalse(bool(d['acted'][0]));self.assertEqual(float(d['utility'][0]),0)

    def test_overconfidence_can_select_negative_utility(self):
        d=m.decision_metrics(np.ones((1,11)),np.full((1,11),-.2))
        self.assertAlmostEqual(float(d['utility'][0]),-.25)
        self.assertEqual(float(d['oracle_utility'][0]),0)

    def test_latent_probability_not_future_outcome_probability(self):
        p=m.uncertainty_example()
        self.assertGreater(p['latent_mean_positive_probability'],.999)
        self.assertLess(p['future_outcome_positive_probability'],.59)
        self.assertGreater(p['future_outcome_positive_probability'],.57)

    def test_invalid_hyperparameters(self):
        for args in [(0,.1,0),(4,-.1,0),(4,.1,1),(4,.1,-.1),(True,.1,0),(4,.1,math.nan),(4,math.inf,0),(4.0,.1,0)]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):m.estimates(np.zeros((2,11)),np.zeros(11),*args)

    def test_bad_numeric_arrays(self):
        for y in [np.zeros((2,10)),np.zeros((0,11)),np.full((2,11),np.nan),np.zeros((2,11),dtype=bool)]:
            with self.subTest(shape=y.shape):
                with self.assertRaises(ValueError):m.estimates(y,np.zeros(11),4,.1,0)

    def test_mismatched_prediction_and_truth(self):
        with self.assertRaises(ValueError):m.decision_metrics(np.ones((2,11)),np.ones((1,11)))

    def test_synthetic_flags_are_not_admission(self):
        self.assertFalse(m.FLAGS['market_data_read'])
        self.assertFalse(m.FLAGS['native_statistical_qualification'])
        self.assertFalse(m.FLAGS['investment_authority'])
        self.assertTrue(m.FLAGS['oracle_hyperparameters'])

if __name__=='__main__':unittest.main()
