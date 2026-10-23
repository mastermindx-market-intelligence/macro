"""Synthetic counterexamples for context and terminal label interpretation."""
import unittest, random
from dataclasses import replace
from context_semantics_v1 import *

class ContextTests(unittest.TestCase):
    def test_total_loss_is_rank_eligible_not_missing(self):
        x=economic_outcome(100,0,status='observed_total_loss')
        self.assertEqual(x['simple_return'],-1);self.assertIsNone(x['log_return'])
        self.assertTrue(x['rank_eligible'])
    def test_unresolved_is_not_total_loss(self):
        x=economic_outcome(100,None,status='unresolved')
        self.assertIsNone(x['simple_return']);self.assertFalse(x['rank_eligible'])
    def test_zero_requires_source_evidence(self):
        with self.assertRaises(ValueError):economic_outcome(100,0,status='observed')
    def test_nonzero_is_not_total_loss(self):
        with self.assertRaises(ValueError):economic_outcome(100,1,status='observed_total_loss')
    def test_ordinary_return(self):
        self.assertAlmostEqual(economic_outcome(100,120,status='observed')['simple_return'],.2)
    def test_unresolved_with_value_refused(self):
        with self.assertRaises(ValueError):economic_outcome(100,100,status='unresolved')
    def test_imputed_is_not_observed(self):
        with self.assertRaises(ValueError):economic_outcome(100,0,status='imputed_bankruptcy')
    def test_outcome_negative_and_nonfinite_rejected(self):
        for x in [-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):economic_outcome(100,x,status='observed')
    def test_common_benchmark_rank_invariance_1000_trials(self):
        rng=random.Random(2026092306)
        for _ in range(1000):
            returns=[rng.uniform(-1,3) for j in range(30)]+[-1,-1]
            bench=rng.uniform(-.9,1)
            order=sorted(range(len(returns)),key=lambda j:(returns[j],j))
            relative=[relative_return(x,bench) for x in returns]
            self.assertEqual(order,sorted(range(len(relative)),key=lambda j:(relative[j],j)))
    def test_different_benchmarks_can_change_rank(self):
        self.assertGreater(.10,.05)
        self.assertLess(relative_return(.10,.20),relative_return(.05,0))
    def test_zero_benchmark_wealth_refused(self):
        with self.assertRaises(ValueError):relative_return(0,-1)
    def base(self,by):
        return EstimateSet('SEC:EXAMPLE','EPS','FY2027','GAAP','USD','split-v1',by)
    def test_composition_can_mimic_revision(self):
        r=revision_bridge(self.base({'A':2,'B':4}),self.base({'B':4,'C':6}))
        self.assertEqual(r['all_analyst_mean_change'],2)
        self.assertEqual(r['common_analyst_mean_revision'],0)
        self.assertEqual(r['composition_component'],2)
    def test_incumbent_revision_not_composition(self):
        r=revision_bridge(self.base({'A':2,'B':4}),self.base({'A':3,'B':5}))
        self.assertEqual(r['common_analyst_mean_revision'],1)
        self.assertEqual(r['composition_component'],0)
    def test_fiscal_roll_forward_is_not_revision(self):
        a=self.base({'A':2});b=replace(a,fiscal_period='FY2028',by_analyst={'A':3})
        with self.assertRaises(ValueError):revision_bridge(a,b)
    def test_basis_currency_or_identity_change_refused(self):
        a=self.base({'A':2})
        for field,value in [('currency','EUR'),('accounting_basis','NON_GAAP'),
                            ('security_id','SEC:OTHER'),('share_basis','split-v2')]:
            with self.assertRaises(ValueError):revision_bridge(a,replace(a,**{field:value}))
    def test_no_common_support(self):
        r=revision_bridge(self.base({'A':2}),self.base({'B':3}))
        self.assertEqual(r['reason'],'NO_COMMON_ANALYST_SUPPORT')
    def test_negative_eps_estimates_are_permitted(self):
        r=revision_bridge(self.base({'A':-2}),self.base({'A':-1}))
        self.assertEqual(r['common_analyst_mean_revision'],1)
    def test_nonfinite_estimate_rejected(self):
        with self.assertRaises(ValueError):self.base({'A':float('nan')})

if __name__=='__main__': unittest.main(verbosity=2)
