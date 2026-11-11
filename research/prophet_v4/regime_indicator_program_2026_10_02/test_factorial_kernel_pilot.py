import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import factorial_kernel_pilot as f
from native_primitive_probe import rsi,_ema,macd_hist,_rsi_macd


def supported_groups():
    rows={k:[] for k in ('A','B')}
    for i,q in enumerate(pd.period_range('2010Q1','2014Q4',freq='Q')):
        for k,family in f.POLICIES:
            for grain in ('1D','3D'):
                for state in ('hidden_fragility','relief_broadening'):
                    rows[k].append({'family':family,'grain':grain,'regime':state,'graded':True,
                        'quarter':str(q),'month':str(q.start_time.to_period('M')),
                        'entry_date':q.start_time.date().isoformat(),'net_excess_pct':float(i),
                        'ticker':'SYNTH','signal_date':q.start_time.date().isoformat()})
    return rows


class TestKernelFactorial(unittest.TestCase):
    def setUp(self):
        t=np.arange(400);self.c=pd.Series(100+.02*t+7*np.sin(.23*t))
        self.ns={'rsi':rsi,'_ema':_ema}

    def test_price_A_matches_existing_native_primitive(self):
        a,b=f.histogram_parts(self.c,transform='price_macd',kernel='A',native=self.ns)
        pd.testing.assert_series_equal(a-b,macd_hist(self.c))

    def test_RSI_B_matches_existing_native_primitive(self):
        a,b=f.histogram_parts(self.c,transform='rsi_macd',kernel='B',native=self.ns)
        x,y=_rsi_macd(self.c)
        pd.testing.assert_series_equal(a-b,x-y)

    def test_price_B_known_native_expression(self):
        a,b=f.histogram_parts(self.c,transform='price_macd',kernel='B',native=self.ns)
        m=_ema(self.c,14)-_ema(self.c,60)
        pd.testing.assert_series_equal(a-b,m-_ema(m,5))

    def test_RSI_A_known_native_expression(self):
        a,b=f.histogram_parts(self.c,transform='rsi_macd',kernel='A',native=self.ns)
        x=rsi(self.c,14);m=_ema(x,12)-_ema(x,26)
        pd.testing.assert_series_equal(a-b,m-_ema(m,9))

    def test_all_four_prefixes_use_no_future_prices(self):
        for k,family in f.POLICIES:
            with self.subTest(kernel=k,family=family):
                a,b=f.histogram_parts(self.c,transform=family,kernel=k,native=self.ns)
                x,y=f.histogram_parts(self.c.iloc[:200],transform=family,kernel=k,native=self.ns)
                pd.testing.assert_series_equal((a-b).iloc[:200],x-y)

    def test_namespace_does_not_mutate_owner(self):
        original=dict(self.ns);ns=f.added_namespace(self.ns)
        self.assertEqual(self.ns,original);self.assertIn('macd_hist',ns)

    def test_no_unregistered_transform_or_parameters(self):
        for transform,kernel in [('normalized','A'),('price_macd','C')]:
            with self.assertRaises(ValueError):f.histogram_parts(self.c,transform=transform,kernel=kernel,native=self.ns)

    def test_joint_identical_policies_cancel_exactly(self):
        out=f.joint_differences(supported_groups(),'2010-01-01','2014-12-31',draws=200)
        for x in out['contrasts']:
            self.assertTrue(x['qualified']);self.assertEqual(x['mean_difference_pp'],0.)
            np.testing.assert_allclose(x['interval95_pp'],[0.,0.],atol=1e-12)

    def test_joint_known_D_effect(self):
        rows=supported_groups()
        for r in rows['B']:
            if r['family']=='rsi_macd' and r['grain']=='3D' and r['regime']=='hidden_fragility':
                r['net_excess_pct']-=2
        out=f.joint_differences(rows,'2010-01-01','2014-12-31',draws=200)
        expected={'kernel_B_minus_A_on_price':0.,'kernel_B_minus_A_on_RSI':-2.,
                  'RSI_minus_price_on_A':0.,'RSI_minus_price_on_B':-2.}
        for x in out['contrasts']:
            self.assertAlmostEqual(x['mean_difference_pp'],expected[x['contrast']])
            np.testing.assert_allclose(x['interval95_pp'],[expected[x['contrast']]]*2,atol=1e-12)

    def test_missing_component_abstains(self):
        rows=supported_groups();rows['A']=[r for r in rows['A'] if r['regime']!='hidden_fragility']
        out=f.joint_differences(rows,'2010-01-01','2014-12-31',draws=20)
        self.assertFalse(next(x for x in out['contrasts'] if x['contrast']=='kernel_B_minus_A_on_price')['qualified'])

    def test_row_duplication_cannot_create_contrast(self):
        rows=supported_groups();rows={k:[r for r in v if r['quarter']=='2010Q1']*100 for k,v in rows.items()}
        out=f.joint_differences(rows,'2010-01-01','2014-12-31',draws=20)
        self.assertFalse(any(x['qualified'] for x in out['contrasts']))

    def test_parent_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{}')
            with self.assertRaises(ValueError):f.read_parent(p)

    def test_source_changes_or_extra_source_refused(self):
        expected={'a':{'sha256':'exact','bytes':2}}
        for actual in ({'a':{'sha256':'different','bytes':2}},{**expected,'new':{'bytes':1}}):
            with self.assertRaises(ValueError):f.require_sources(expected,actual)
        f.require_sources(expected,copy.deepcopy(expected))

    def test_assemble_preserves_parent_and_distinguishes_kernels(self):
        base={'ticker':'SYNTH','grain':'1D','signal_date':'2020-01-01'}
        parent=[{**base,'family':'price_macd'},{**base,'family':'rsi_macd'}]
        added=[{**base,'family':'price_macd'},{**base,'family':'rsi_macd'}]
        before=copy.deepcopy(parent);groups=f.assemble(parent,added)
        self.assertEqual(parent,before)
        self.assertEqual([r['family'] for r in groups['A']],['price_macd','rsi_macd'])
        self.assertEqual([r['family'] for r in groups['B']],['rsi_macd','price_macd'])
        groups['A'][0]['ticker']='changed';self.assertEqual(parent,before)

    def test_duplicate_event_per_policy_refused(self):
        row={'ticker':'SYNTH','grain':'1D','signal_date':'2020-01-01','family':'price_macd'}
        with self.assertRaises(ValueError):f.assemble([row,row],[])

    def test_draw_count_not_silently_zero(self):
        for v in (0,-1,True,2.5):
            with self.assertRaises(ValueError):f.joint_differences(supported_groups(),'2010-01-01','2014-12-31',draws=v)

    def test_reproducible_joint_draws(self):
        rows=supported_groups()
        for r in rows['B']:
            if r['grain']=='3D':r['net_excess_pct']*=1.2
        a=f.joint_differences(rows,'2010-01-01','2014-12-31',draws=100)
        b=f.joint_differences(rows,'2010-01-01','2014-12-31',draws=100)
        self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
