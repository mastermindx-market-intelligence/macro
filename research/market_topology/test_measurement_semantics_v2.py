"""Synthetic specification tests. They do not validate forecast effectiveness."""
import unittest, random, math
from datetime import datetime, timezone, timedelta
from measurement_semantics_v2 import *

class SemanticsTests(unittest.TestCase):
    def test_known_share_is_not_census(self):
        flags={f'id{i}':True if i<20 else False if i<70 else None for i in range(100)}
        r=participation(flags)
        self.assertAlmostEqual(r['known_only'],20/70)
        self.assertEqual((r['lower'],r['upper']),(.2,.5))
    def test_large_finite_weights_cannot_overflow(self):
        r=participation({'a':True,'b':None},{'a':1e308,'b':1e308})
        self.assertEqual((r['lower'],r['upper'],r['known_only']),(.5,1.,1.))
    def test_tiny_known_weight_not_lost_to_subtraction(self):
        r=participation({'a':True,'b':None},{'a':1e-30,'b':1})
        self.assertEqual(r['known_only'],1.)
    def test_all_unknown(self):
        r=participation({'a':None,'b':None});self.assertIsNone(r['known_only'])
        self.assertEqual((r['lower'],r['upper']),(0,1))
    def test_empty(self):
        self.assertIsNone(participation({})['lower'])
    def test_missing_weight(self):
        with self.assertRaises(ValueError):participation({'a':True,'b':None},{'a':1})
    def test_negative_or_nonfinite_weight(self):
        for v in [-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):participation({'a':True},{'a':v})
    def test_zero_total_weight(self):
        with self.assertRaises(ValueError):participation({'a':True},{'a':0})
    def test_weighted_unknown(self):
        r=participation({'a':True,'b':False,'c':None},{'a':.1,'b':.7,'c':.2})
        self.assertAlmostEqual(r['lower'],.1);self.assertAlmostEqual(r['upper'],.3)
    def test_integer_is_not_boolean(self):
        with self.assertRaises(ValueError):participation({'a':1})
    def test_coverage_not_improvement(self):
        r=state_count_bridge({'a':None},{'a':True})
        self.assertEqual(r['common_known_state_change'],0)
        self.assertEqual(r['common_coverage_change'],1)
    def test_membership_not_improvement(self):
        before={f'id{i}':i<20 for i in range(100)}
        after={k:v for k,v in before.items() if int(k[2:])<80}
        r=state_count_bridge(before,after)
        self.assertEqual(r['common_known_state_change'],0)
        self.assertEqual(participation(before)['lower'],.2)
        self.assertEqual(participation(after)['lower'],.25)
    def test_count_bridge_1000_random_populations(self):
        rng=random.Random(2026092304)
        for _ in range(1000):
            a={str(i):rng.choice([True,False,None]) for i in rng.sample(range(100),rng.randrange(101))}
            b={str(i):rng.choice([True,False,None]) for i in rng.sample(range(100),rng.randrange(101))}
            self.assertEqual(state_count_bridge(a,b)['residual'],0)
    def test_bounds_enclose_every_completion(self):
        from itertools import product
        flags={'a':True,'b':False,'c':None,'d':None,'e':None}
        w={'a':.1,'b':.2,'c':.1,'d':.25,'e':.35};r=participation(flags,w)
        for bits in product([False,True],repeat=3):
            filled=flags|dict(zip(['c','d','e'],bits));p=participation(filled,w)['lower']
            self.assertGreaterEqual(p+1e-12,r['lower']);self.assertLessEqual(p-1e-12,r['upper'])
    def test_weight_change_is_separate(self):
        r=common_weighted_bridge({'a':True,'b':False},{'a':True,'b':False},{'a':.2,'b':.8},{'a':.4,'b':.6})
        self.assertEqual(r['state_component'],0);self.assertAlmostEqual(r['weight_component'],.2)
    def test_weight_bridge_1000_random_populations(self):
        rng=random.Random(2026092305)
        for _ in range(1000):
            ids=list(map(str,range(10)))
            a={k:rng.choice([True,False]) for k in ids};b={k:rng.choice([True,False]) for k in ids}
            x=[rng.random() for k in ids];y=[rng.random() for k in ids]
            w0={k:v/sum(x) for k,v in zip(ids,x)};w1={k:v/sum(y) for k,v in zip(ids,y)}
            self.assertAlmostEqual(common_weighted_bridge(a,b,w0,w1)['residual'],0,places=12)
    def test_weighted_bridge_rejects_unknown(self):
        with self.assertRaises(ValueError):common_weighted_bridge({'a':None},{'a':True},{'a':1},{'a':1})
    def test_overlap_reference(self):
        r=cohort_overlap(set(map(str,range(40))),set(map(str,range(16,56))),set(map(str,range(200))))
        self.assertEqual(r['intersection'],24);self.assertEqual(r['independent_set_expected'],8)
        self.assertEqual(r['centered_overlap'],.5)
    def test_all_population_overlap_uninformative(self):
        self.assertIsNone(cohort_overlap({'a'},{'a'},{'a'})['centered_overlap'])
    def test_overlap_rejects_changed_population(self):
        with self.assertRaises(ValueError):cohort_overlap({'x'},{'a'},{'a'})
    def test_clocks_and_revisions(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        a=Observation('old',t,t+timedelta(days=5),t+timedelta(days=7),1.)
        b=Observation('revision',t,t+timedelta(days=12),t+timedelta(days=13),2.)
        self.assertIsNone(latest_available([a,b],t+timedelta(days=4),mode='source_asof'))
        self.assertEqual(latest_available([a,b],t+timedelta(days=6),mode='source_asof').value,1)
        self.assertIsNone(latest_available([a,b],t+timedelta(days=6),mode='served_replay'))
        self.assertEqual(latest_available([a,b],t+timedelta(days=8),mode='served_replay').value,1)
        self.assertEqual(latest_available([a,b],t+timedelta(days=14),mode='served_replay').value,2)
    def test_naive_clock_rejected(self):
        with self.assertRaises(ValueError):latest_available([],datetime(2026,1,1),mode='source_asof')
    def test_readiness_cannot_precede_source(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):Observation('x',t,t+timedelta(days=1),t,1.)
    def test_future_revision_cannot_change_present(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        a=Observation('a',t,t,t,1.);b=Observation('future',t,t+timedelta(days=4),t+timedelta(days=4),999.)
        self.assertEqual(latest_available([a],t,mode='served_replay'),latest_available([a,b],t,mode='served_replay'))
    def test_ambiguous_revisions_rejected(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):latest_available([Observation('a',t,t,t,1.),Observation('b',t,t,t,2.)],t,mode='source_asof')
    def test_later_ingestion_cannot_resolve_source_conflict(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        a=Observation('a',t,t,t,1.);b=Observation('b',t,t,t+timedelta(days=1),2.)
        with self.assertRaises(ValueError):latest_available([a,b],t,mode='source_asof')
        self.assertEqual(latest_available([a,b],t,mode='served_replay').value,1.)
        with self.assertRaises(ValueError):latest_available([a,b],t+timedelta(days=2),mode='served_replay')
    def test_record_id_required(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):Observation('',t,t,t,1.)
    def test_growth_can_coexist_with_loss(self):
        self.assertAlmostEqual(earnings_multiple_bridge(1,1.3,50,30)['price_change'],-.22)
    def test_loss_earnings_not_forced_into_pe(self):
        with self.assertRaises(ValueError):earnings_multiple_bridge(-1,1,10,10)

if __name__=='__main__':unittest.main(verbosity=2)
