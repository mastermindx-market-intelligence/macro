"""Read-only diagnostic; controller transport is replaced with failing sentinels."""
import datetime,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/eval-os-a1-preflight-20260922-f75c61cdabe6f12c')
sys.path.insert(0,str(ROOT))
import scripts.merge_on_green as M
spec=importlib.util.spec_from_file_location('controller_contract_helpers',ROOT/'tests/test_merge_on_green_semantic.py'); H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
source=(ROOT/'scripts/merge_on_green.py').read_bytes(); bound=json.loads((Path(__file__).parent/'source-binding.json').read_text())
assert hashlib.sha256(source).hexdigest()==bound['sha256'], 'Controller source changed; stop rather than silently using another version'
rows=[]
for case,clear,red in [('semantic-blocked',False,True),('semantic-clear-contract-red',True,True),('clear-stale-control',True,False)]:
 calls=[]; fresh=H._Fresh(stale=(True,'different current base'),paths=['engine/product.py']); runs=[H._check('ci-gate','success',details=True),H._check('fence-pack','success'),H._check('ci-authority/main','success'),H._check('contract-delta','failure' if red else 'success'),H._check('ci-pack-0','failure' if red else 'success')]
 with pytest.MonkeyPatch.context() as patch:
  patch.setattr(M,'_request',lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO NETWORK')))
  patch.setattr(M,'head_check_runs',lambda *a:runs)
  patch.setattr(M,'_semantic_gate',lambda *a:H._gate(clear=clear,classification='introduced'))
  patch.setattr(M,'_semantic_has_nonunit_blocker',lambda *a:False)
  patch.setattr(M.semantic_proof,'format_semantic_unit',lambda u:u.logical_job_id+'/'+u.proof_id)
  patch.setattr(M,'live_authorized_pull',lambda *a,**k:(H._pull(),'ok'))
  patch.setattr(M,'mark_blocked',lambda *a,**k:calls.append('mark_blocked') or True)
  patch.setattr(M,'clear_blocked',lambda *a,**k:None)
  patch.setattr(M,'reprove',lambda *a,**k:calls.append('reprove') or 're-proving')
  patch.setattr(M,'update_branch',lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO BRANCH WRITE')))
  patch.setattr(M,'merge_pull',lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO MERGE')),raising=False)
  verdict=M.sweep_pull('acme/widgets',H._pull(),'NOT_A_TOKEN','NOT_A_TOKEN',fresh,semantic_evidence=H._loaded('synthetic-readonly-probe'))
 expected='re-proving' if case=='clear-stale-control' else 'blocked'
 assert verdict==expected,(case,verdict,calls)
 assert ('reprove' in calls)==(case=='clear-stale-control')
 rows.append({'case':case,'verdict':verdict,'calls':calls,'freshness_calls':fresh.stale_calls})
result={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_binding':bound,'cases':rows,'network_or_branch_effects':False,'scope':'Synthetic control-flow proof only. Actual current CI state comes from separate GitHub observations. Capacity is not reached for blocked semantic proof; only clean-stale control reaches incumbent reprove.','all_passed':True}
(Path(__file__).parent/'reachability-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
