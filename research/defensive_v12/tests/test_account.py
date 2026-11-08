import unittest
import pandas as pd
import numpy as np
import cycle_failure as c
import account_replay as a
import test_cycle_failure as fixtures
class AccountTests(unittest.TestCase):
 def test_open_end_not_forced_liquidation(self):
  d,f=fixtures.CycleTests().fixture();r=c.simulate(d,f,2,2,30,'HOLD',allow_open_end=True,marked=True)
  self.assertEqual(r['status'],'OPEN');self.assertTrue(r['marks'][-1][3]);self.assertAlmostEqual(r['net'],1/1.0005-1)
 def test_final_signal_remains_pending(self):
  d,f=fixtures.CycleTests().fixture();r=c.simulate(d,f,15,15,40,'HOLD',allow_open_end=True)
  self.assertEqual(r['status'],'PENDING_ENTRY')
 def test_account_busy_signal_not_resurrected(self):
  d,f=fixtures.CycleTests().fixture(50);w=[{'episode':1,'arm_i':1,'signal_i':2},{'episode':2,'arm_i':3,'signal_i':4}]
  x=a.account(d,f,w,'HOLD',horizon=20,start_i=0)
  self.assertEqual(x['summary']['entries'],1);self.assertEqual(x['summary']['busy_signals'],1)
 def test_end_mark_includes_cash_waits(self):
  d,f=fixtures.CycleTests().fixture(50);w=[{'episode':1,'arm_i':1,'signal_i':2}]
  x=a.account(d,f,w,'HOLD',horizon=20,start_i=0)
  self.assertAlmostEqual(x['summary']['ending_equity'],.9995/1.0005)
  self.assertTrue((x['equity'].value.iloc[:3]==1.).all())
 def test_second_trade_after_exit_included(self):
  d,f=fixtures.CycleTests().fixture(60);w=[{'episode':1,'arm_i':1,'signal_i':2},{'episode':2,'arm_i':25,'signal_i':26}]
  x=a.account(d,f,w,'HOLD',horizon=20,start_i=0)
  self.assertEqual(x['summary']['entries'],2);self.assertAlmostEqual(x['summary']['ending_equity'],(.9995/1.0005)**2)
 def test_pending_not_an_entry(self):
  d,f=fixtures.CycleTests().fixture();w=[{'episode':1,'arm_i':10,'signal_i':15}]
  x=a.account(d,f,w,'HOLD',horizon=20,start_i=0)
  self.assertEqual(x['summary']['entries'],0);self.assertEqual(x['summary']['pending_entries'],1)
 def test_trade_ids_fixed(self):
  d,f=fixtures.CycleTests().fixture(60);w=[{'episode':12,'arm_i':1,'signal_i':2}]
  x=a.account(d,f,w,'HOLD',horizon=20,start_i=0)
  self.assertEqual(x['trades'][0]['episode'],12)
if __name__=='__main__':unittest.main(verbosity=2)
