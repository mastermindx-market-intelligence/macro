import unittest
import pandas as pd
import test_cycle_failure as fixture
import cycle_failure as c
class SlowHarvestTests(unittest.TestCase):
 def f(self):
  d,f=fixture.CycleTests().fixture(20);f['two_week_k']=10.;f['two_week_fresh']=False
  return d,f
 def test_weekly_only_recovery_does_not_complete_two_week_stage(self):
  d,f=self.f();f.loc[f.index[4],['weekly_fresh','weekly_k']]=[True,90.];f.loc[f.index[6],['weekly_fresh','weekly_stoch_bear']]=[True,True]
  r=c.simulate(d,f,2,2,16,'SLOW_STAGE_ATR6');self.assertEqual(r['reason'],'ENDPOINT')
 def test_new_two_week_upper_reading_arms_weekly_exit(self):
  d,f=self.f();f.loc[f.index[4],['two_week_fresh','two_week_k']]=[True,90.];f.loc[f.index[6],['weekly_fresh','weekly_stoch_bear']]=[True,True]
  r=c.simulate(d,f,2,2,16,'SLOW_STAGE_ATR6');self.assertEqual(r['exit_i'],7)
 def test_stale_two_week_upper_reading_never_arms(self):
  d,f=self.f();f['two_week_k']=90.;f.loc[f.index[6],['weekly_fresh','weekly_stoch_bear']]=[True,True]
  self.assertEqual(c.simulate(d,f,2,2,16,'SLOW_STAGE_ATR6')['reason'],'ENDPOINT')
 def test_missing_native_metadata_rejected(self):
  d,f=self.f();f=f.drop(columns=['two_week_fresh'])
  with self.assertRaises(ValueError):c.simulate(d,f,2,2,16,'SLOW_STAGE_ATR6')
 def test_initial_structure_failure_retained(self):
  d,f=self.f();d.loc[d.index[4],['low','close']]=[96,97];f.loc[f.index[4],'lower_hist']=-1
  r=c.simulate(d,f,2,2,16,'SLOW_STAGE_ATR6');self.assertEqual(r['reason'],'STRUCTURE_MOMENTUM_LOSS')
if __name__=='__main__':unittest.main(verbosity=2)
