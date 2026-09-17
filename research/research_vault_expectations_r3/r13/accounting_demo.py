"""Serial request walkthrough using the unchanged existing temporary JSON ledger."""
import json
from test_owner_adapter import Integration,quota

def main():
 c=Integration(methodName='test_20_one_read_exact_one_owner_allow');c.setUp()
 try:
  events=[]
  found=c.discover();selected=found['items'][0]['selection']
  events.append({'action':'discover','status':found['status'],'recorded_user_count':c.count(),'allow_calls':c.charge_calls})
  for i in range(1,5):
   r=c.read(selected)
   events.append({'action':f'read_{i}','status':r['status'],'recorded_user_count':c.count(),
                  'allow_calls':c.charge_calls,'remaining':(r.get('quota') or {}).get('remaining'),
                  'passage_returned':bool(r.get('passages'))})
  assert [x['recorded_user_count'] for x in events]==[0,1,2,3,3]
  assert [x['status'] for x in events]==['ready','matched','matched','matched','view_limit_reached']
  assert c.charge_calls==3
  print(json.dumps({'source':'existing file-backed view limiter, temporary state only','source_permissions':'synthetic',
                   'hourly_limit':3,'events':events,'raw_ledger_files':len(list(quota._rl_dir().glob('*.json'))),
                   'persistence_claim_in_product_result':'not_attested','concurrent_exactly_once_proven':False},indent=2))
 finally:c.tearDown()
if __name__=='__main__':main()
