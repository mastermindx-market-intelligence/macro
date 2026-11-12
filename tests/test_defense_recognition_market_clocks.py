"""Bar clock tests against the existing NYSE calendar; synthetic fixtures only."""
from pathlib import Path
from datetime import datetime
import importlib.util,os,sys,unittest
from copy import deepcopy
ROOT=Path(os.environ.get('DFE_TEST_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))
s=importlib.util.spec_from_file_location('clock_subject',ROOT/'engine/government_revenue/defense_economics.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
NOW=datetime.fromisoformat('2026-10-13T03:00:00+00:00');SUBJECT={'issuer_id':'cik:0000936468','security_id':'xnys:LMT'}
BIND={'market':{'sha256':'a'*64,'owner_family':'market','price_adjustment':'raw',**SUBJECT}}
VALUE={'state':'stale','owner_ref':'market','observed_at':'2026-10-13T02:00:00Z','security_id':'xnys:LMT','price_adjustment':'raw','price_vintage':'2026-10-10T09:19:58Z','window_sessions':1,'return_pct':0,'market_as_of':'2026-10-09','previous_session':'2026-10-08','sessions_behind':1}
def project(change=None):return m._recognition_leg({**VALUE,**(change or {})},BIND,NOW,SUBJECT,scenario=False)
class MarketClocks(unittest.TestCase):
 def test_last_archived_session_and_zero_are_preserved(self):
  r=project();self.assertEqual(r['state'],'stale');self.assertEqual(r['return_pct'],0);self.assertEqual(r['market_as_of'],'2026-10-09');self.assertEqual(r['previous_session'],'2026-10-08');self.assertEqual(r['sessions_behind'],1);self.assertNotIn('relative_return_pct',r)
 def test_current_complete_session_can_be_supported(self):
  r=project({'state':'supported','market_as_of':'2026-10-12','previous_session':'2026-10-09','sessions_behind':0,'price_vintage':'2026-10-13T00:00:00Z'});self.assertEqual(r['state'],'supported');self.assertEqual(r['sessions_behind'],0)
 def test_future_or_unfinished_market_session_refuses(self):
  for d in ('2026-10-13','2026-10-14'):
   with self.subTest(d=d):self.assertEqual(project({'market_as_of':d})['state'],'missing_owner')
 def test_previous_session_order_refuses(self):
  for d in ('2026-10-09','2026-10-12'):
   with self.subTest(d=d):self.assertEqual(project({'previous_session':d})['state'],'missing_owner')
 def test_non_session_or_malformed_date_refuses(self):
  for field,value in [('market_as_of','2026-10-11'),('previous_session','2026-10-04'),('market_as_of','20261009'),('market_as_of','2026-02-30')]:
   with self.subTest(field=field,value=value):self.assertEqual(project({field:value})['state'],'missing_owner')
 def test_market_window_requires_actual_calendar_count(self):self.assertEqual(project({'previous_session':'2026-10-07'})['state'],'missing_owner')
 def test_stale_read_cannot_be_promoted_by_generation(self):self.assertEqual(project({'state':'supported'})['state'],'missing_owner')
 def test_lag_requires_exact_calendar_and_integer(self):
  for lag in (0,2,-1,True,'1',1.5):
   with self.subTest(lag=lag):self.assertEqual(project({'sessions_behind':lag})['state'],'missing_owner')
 def test_vintage_cannot_precede_completed_bar(self):self.assertEqual(project({'price_vintage':'2026-10-09T14:00:00Z'})['state'],'missing_owner')
 def test_byte_vintage_cannot_follow_read_clock(self):self.assertEqual(project({'observed_at':'2026-10-10T09:00:00Z'})['state'],'missing_owner')
 def test_missing_bar_provenance_refuses(self):
  for field in ('market_as_of','previous_session','sessions_behind'):
   with self.subTest(field=field):self.assertEqual(project({field:None})['state'],'missing_owner')
if __name__=='__main__':unittest.main(verbosity=2)
