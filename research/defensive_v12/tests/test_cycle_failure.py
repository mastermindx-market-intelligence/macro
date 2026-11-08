import unittest
import numpy as np
import pandas as pd
import cycle_failure as c

class CycleTests(unittest.TestCase):
 def fixture(self,n=16):
  ix=pd.bdate_range('2020-01-06',periods=n)
  d=pd.DataFrame({'open':100.,'high':102.,'low':98.,'close':100.},index=ix)
  f=pd.DataFrame({'atr':1.,'lower_hist':1.,'weekly_fresh':False,'weekly_k':10.,'weekly_stoch_bear':False},index=ix)
  return d,f
 def test_entry_next_open_and_fees(self):
  d,f=self.fixture();d.loc[d.index[3],'open']=101.
  r=c.simulate(d,f,2,2,10,'HOLD')
  self.assertEqual(r['entry_i'],3)
  self.assertAlmostEqual(r['net'],100/101*.9995/1.0005-1)
 def test_gap_stop_at_open(self):
  d,f=self.fixture();d.loc[d.index[4],['open','high','low','close']]=[90,99,89,95]
  r=c.simulate(d,f,2,2,10,'ATR3')
  self.assertEqual(r['exit_price'],90);self.assertEqual(r['reason'],'STOP_GAP')
 def test_entry_day_stop(self):
  d,f=self.fixture();d.loc[d.index[3],'low']=95
  r=c.simulate(d,f,2,2,10,'ATR3')
  self.assertEqual(r['exit_i'],3);self.assertEqual(r['exit_price'],97)
 def test_structure_close_then_next_open(self):
  d,f=self.fixture();d.loc[d.index[4],['low','close']]=[96,97];d.loc[d.index[5],['open','high','low','close']]=[96,97,95,96]
  r=c.simulate(d,f,2,2,10,'STRUCTURE_ATR6')
  self.assertEqual(r['exit_i'],5);self.assertEqual(r['exit_price'],96)
 def test_hist_confirmation_not_same_as_price_only(self):
  d,f=self.fixture();d.loc[d.index[4],['low','close']]=[96,97]
  r=c.simulate(d,f,2,2,10,'STRUCTURE_MOMENTUM_ATR6')
  self.assertEqual(r['reason'],'ENDPOINT')
  f.loc[f.index[4],'lower_hist']=-.1
  r=c.simulate(d,f,2,2,10,'STRUCTURE_MOMENTUM_ATR6')
  self.assertEqual(r['exit_i'],5)
 def test_floor_never_recalculated_after_entry(self):
  d,f=self.fixture();x=c.setup_floor(d,2,2,1.)
  d.loc[d.index[3]:,'low']=1.
  self.assertEqual(c.setup_floor(d,2,2,1.),x)
 def test_stale_weekly_extension_not_harvest_gate(self):
  d,f=self.fixture();f['weekly_k']=90.;f.loc[f.index[4],'weekly_stoch_bear']=True
  r=c.simulate(d,f,2,2,10,'STAGED_ATR6')
  self.assertEqual(r['reason'],'ENDPOINT')
 def test_fresh_weekly_extension_then_bear(self):
  d,f=self.fixture();f.loc[f.index[4],['weekly_fresh','weekly_k']]=[True,90.];f.loc[f.index[6],['weekly_fresh','weekly_stoch_bear']]=[True,True]
  r=c.simulate(d,f,2,2,10,'STAGED_ATR6')
  self.assertEqual(r['exit_i'],7);self.assertEqual(r['reason'],'WEEKLY_CYCLE')
 def test_open_exit_excludes_rest_of_exit_day(self):
  d,f=self.fixture();f.loc[f.index[4],['weekly_fresh','weekly_k']]=[True,90.];f.loc[f.index[6],['weekly_fresh','weekly_stoch_bear']]=[True,True]
  d.loc[d.index[7],['high','low']]=[200,1]
  r=c.simulate(d,f,2,2,10,'STAGED_ATR6')
  self.assertAlmostEqual(r['mae'],-.02);self.assertAlmostEqual(r['mfe'],.02)
 def test_pending_exit_yields_to_gap_stop(self):
  d,f=self.fixture();d.loc[d.index[4],['low','close']]=[96,97];d.loc[d.index[5],['open','high','low','close']]=[90,99,89,95]
  r=c.simulate(d,f,2,2,10,'STRUCTURE_ATR6')
  self.assertEqual(r['reason'],'STOP_GAP');self.assertEqual(r['exit_price'],90)
 def test_undefined_future_horizon_unknown(self):
  d,f=self.fixture();r=c.simulate(d,f,2,2,30,'HOLD')
  self.assertEqual(r['status'],'INCOMPLETE');self.assertNotIn('net',r)
 def test_later_prices_do_not_change_earlier_exit(self):
  d,f=self.fixture();d.loc[d.index[4],['low','close']]=[96,97]
  a=c.simulate(d,f,2,2,10,'STRUCTURE_ATR6');d.loc[d.index[7]:,'close']=1000
  b=c.simulate(d,f,2,2,10,'STRUCTURE_ATR6')
  for k in ['entry_i','exit_i','net','mae','mfe','reason']:self.assertEqual(a[k],b[k])
 def test_unstopped_hold_reconciles_v11(self):
  d,f=self.fixture();r=c.simulate(d,f,2,2,10,'HOLD')
  self.assertAlmostEqual(r['net'],d.close.iloc[10]/d.open.iloc[3]*.9995/1.0005-1)
 def test_wider_stop_control_not_trailing(self):
  d,f=self.fixture();d.loc[d.index[4],['high','close']]=[112,110];d.loc[d.index[5],['low','close']]=[95,96]
  r=c.simulate(d,f,2,2,10,'ATR6');self.assertEqual(r['reason'],'ENDPOINT')
 def test_invalid_policy_refused(self):
  d,f=self.fixture()
  with self.assertRaises(ValueError):c.simulate(d,f,2,2,10,'MAGIC')

if __name__=='__main__':unittest.main(verbosity=2)
