import unittest
import numpy as np
import pandas as pd
import test_cycle_failure as fixture
import reclaim
import account_replay as a
class ReclaimTests(unittest.TestCase):
 def data(self):
  d,f=fixture.CycleTests().fixture(30);f['lower_bull']=False
  d.loc[d.index[4],['low','close']]=[96,97];f.loc[f.index[4],'lower_hist']=-1
  d.loc[d.index[5],['open','high','low','close']]=[96,98,95,97]
  f.loc[f.index[7],'lower_bull']=True
  d.loc[d.index[12]:,['open','high','low','close']]=[108,112,107,110]
  return d,f
 def test_first_loss_preserved_in_compound_result(self):
  d,f=self.data();r=reclaim.simulate(d,f,2,2,20,'STRUCTURE_MOMENTUM_ATR6',marked=True)
  self.assertEqual(r['attempt_count'],2)
  expected=(96/100*.9995/1.0005)*(110/100*.9995/1.0005)-1
  self.assertAlmostEqual(r['net'],expected);self.assertEqual(r['legs'][0]['exit_i'],5);self.assertEqual(r['legs'][1]['entry_i'],8)
 def test_positive_hist_without_new_cross_does_not_reenter(self):
  d,f=self.data();f['lower_bull']=False
  r=reclaim.simulate(d,f,2,2,20,'STRUCTURE_MOMENTUM_ATR6')
  self.assertEqual(r['attempt_count'],1)
 def test_reentry_requires_reclaimed_original_floor(self):
  d,f=self.data();d.loc[d.index[7],['low','close']]=[96,97]
  r=reclaim.simulate(d,f,2,2,20,'STRUCTURE_MOMENTUM_ATR6')
  self.assertEqual(r['attempt_count'],1)
 def test_weekly_extended_is_not_reentry(self):
  d,f=self.data();f.loc[f.index[7],'weekly_k']=90
  r=reclaim.simulate(d,f,2,2,20,'STRUCTURE_MOMENTUM_ATR6')
  self.assertEqual(r['attempt_count'],1)
 def test_later_qualifier_outside20bar_window_excluded(self):
  d,f=self.data();f['lower_bull']=False;f.loc[f.index[27],'lower_bull']=True
  r=reclaim.simulate(d,f,2,2,29,'STRUCTURE_MOMENTUM_ATR6')
  self.assertEqual(r['attempt_count'],1)
 def test_stale_signal_on_exit_day_excluded(self):
  d,f=self.data();f['lower_bull']=False;f.loc[f.index[5],'lower_bull']=True
  r=reclaim.simulate(d,f,2,2,20,'STRUCTURE_MOMENTUM_ATR6');self.assertEqual(r['attempt_count'],1)
 def test_open_position_blocks_finalday_pending_signal(self):
  d,f=self.data();w=[{'episode':1,'arm_i':1,'signal_i':2},{'episode':2,'arm_i':25,'signal_i':29}]
  r=a.account(d,f,w,'HOLD',horizon=60,start_i=0)
  self.assertEqual(r['summary']['pending_entries'],0);self.assertEqual(r['summary']['busy_signals'],1)
 def test_waiting_cash_marks_not_exposed(self):
  d,f=self.data();r=reclaim.simulate(d,f,2,2,20,'STRUCTURE_MOMENTUM_ATR6',marked=True)
  marks={t[0]:t for t in r['marks']};self.assertFalse(marks[6][3]);self.assertAlmostEqual(marks[6][1],.96*.9995/1.0005)
if __name__=='__main__':unittest.main(verbosity=2)
