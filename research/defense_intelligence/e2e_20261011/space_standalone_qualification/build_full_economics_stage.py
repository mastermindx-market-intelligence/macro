from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
from hashlib import sha256
import sys,json
C=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/pr-9066-e4ea65fadb39fb56');W=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');D=Path(__file__).parent;S=D.parent/'isolated-owner-consumer';sys.path.insert(0,str(C))
from engine.government_revenue.defense_economics_producer import load_defense_owner_snapshot,build_defense_economics_payload
from engine.government_revenue.defense_participation_context import load_participation_inputs
old_raw=(W/'data/government_revenue/defense_economics.json').read_bytes();old=json.loads(old_raw);held=load_defense_owner_snapshot(S)
clock=datetime.now(timezone.utc).isoformat()
# Current complete optional inputs are read through the existing producer; the new financial snapshot is explicit.
result=build_defense_economics_payload(W,generated_at=clock,owner_inputs=held,require_market_owner=True,participation_inputs=load_participation_inputs(W))
raw=(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode();(D/'FULL_ECONOMICS_STAGE.json').write_bytes(raw)
r={'source_financial_generation':held['manifest']['generation_id'],'canonical_old_sha256':sha256(old_raw).hexdigest(),'staged_sha256':sha256(raw).hexdigest(),'profiles':len(result['profiles']),'profile_changes':{}}
for a,b in zip(old['profiles'],result['profiles']):
 assert a['ticker_display']==b['ticker_display'];oldfacts={f['fact_id']:f for f in a['axes']['economics']['facts']};newfacts={f['fact_id']:f for f in b['axes']['economics']['facts']}
 def norm(x):
  if isinstance(x,dict):return {k:norm(v) for k,v in x.items()}
  if isinstance(x,list):return [norm(v) for v in x]
  if isinstance(x,str):return x.replace(held['manifest']['generation_id'],'GEN').replace('8a27d8b450ab547be676fadc','GEN')
  return x
 changed=[k for k in oldfacts if norm(oldfacts[k])!=norm(newfacts.get(k))];added=sorted(set(newfacts)-set(oldfacts));assert not changed,(a['ticker_display'],changed)
 if a['ticker_display']=='NOC':assert len(added)==7 and all(':issuer_space_' in x for x in added)
 else:assert not added
 r['profile_changes'][a['ticker_display']]={'existing_facts_semantically_identical':len(oldfacts),'new_facts':added,'changed_top_fields':[k for k in a if norm(a[k])!=norm(b[k])]}
assert (W/'data/government_revenue/defense_economics.json').read_bytes()==old_raw
r.update(canonical_unchanged=True,stage_only=True,publication=False,clock=clock)
(D/'FULL_ECONOMICS_STAGE_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
