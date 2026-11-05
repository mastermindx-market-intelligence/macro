"""Bounded source qualification; never runs a publisher or changes legacy dispositions."""
from pathlib import Path
import copy, datetime, hashlib, json, subprocess, sys
import yaml
W=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main')
D=Path(__file__).resolve().parent
sys.path.insert(0,str(W/'scripts/ci'))
import govrev_publisher_preflight as pre
sha=lambda b:hashlib.sha256(b).hexdigest()
old=json.loads((D/'prior-baseline.json').read_text())
old_source='7c8069a604c77a63ef4c048263cef45f262d0bdc'
protected_main='29e383bc0ded2c3d3dae819fd5b7647ab6fea229'
source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()
prior={p:(D/('prior-'+Path(p).name)).read_bytes() for p in pre.SOURCE_PATHS}
current={p:(W/p).read_bytes() for p in pre.SOURCE_PATHS}
assert {p:sha(b) for p,b in prior.items()}==old['source_closure']

def noncomment_lines(s):
    return '\n'.join(line for line in s.splitlines() if not line.lstrip().startswith('#'))

def qualify(candidate):
    changed={p for p in prior if candidate[p]!=prior[p]}
    assert changed=={'.github/workflows/government-revenue-live.yml','.github/workflows/daily.yml'},changed
    live='.github/workflows/government-revenue-live.yml'
    before=yaml.safe_load(prior[live]);after=yaml.safe_load(candidate[live]);normalized=copy.deepcopy(after)
    assert list(before['jobs'])==list(after['jobs'])
    changed_steps=[]
    for jid,bjob in before['jobs'].items():
        ajob=normalized['jobs'][jid]
        assert len(bjob['steps'])==len(ajob['steps'])
        for i,(bs,ac) in enumerate(zip(bjob['steps'],ajob['steps'])):
            if bs==ac:continue
            assert set(bs)==set(ac)
            assert {k:v for k,v in bs.items() if k!='run'}=={k:v for k,v in ac.items() if k!='run'}
            assert noncomment_lines(bs['run'])==noncomment_lines(ac['run'])
            changed_steps.append(bs.get('name',str(i)))
            ac['run']=bs['run']
    assert normalized==before
    daily='.github/workflows/daily.yml'
    b=yaml.safe_load(prior[daily]);a=yaml.safe_load(candidate[daily])
    assert {k:v for k,v in b.items() if k!='jobs'}=={k:v for k,v in a.items() if k!='jobs'}
    assert set(b['jobs'])==set(a['jobs'])
    assert [k for k in b['jobs'] if b['jobs'][k]!=a['jobs'][k]]==['collect','capital_structure']
    assert pre._caller_job_block(prior[daily],'government_revenue_projection')==pre._caller_job_block(candidate[daily],'government_revenue_projection')
    protected=subprocess.check_output(['git','show',protected_main+':'+daily],cwd=W)
    protected_jobs=yaml.safe_load(protected)['jobs']
    assert all(a['jobs'][j]==protected_jobs[j] for j in ['collect','capital_structure']),'Changed Daily jobs must be exact inherited protected-main source'
    return {'live_changed_steps':changed_steps,'live_noncomment_execution_and_all_other_yaml_equal':True,'daily_publisher_caller_byte_equal':True,'daily_changed_jobs':['collect','capital_structure'],'daily_changed_jobs_exact_protected_main':protected_main}

facts=qualify(current)
negative=[]
for label,change in [
 ('live_execution',lambda d:d.__setitem__('.github/workflows/government-revenue-live.yml',d['.github/workflows/government-revenue-live.yml'].replace(b'set -euo pipefail',b'set +e',1))),
 ('daily_publisher',lambda d:d.__setitem__('.github/workflows/daily.yml',d['.github/workflows/daily.yml'].replace(b'government_revenue_projection:',b'government_revenue_projection_changed:',1))),
 ('proof_helper',lambda d:d.__setitem__('scripts/ci/govrev_candidate_proof.py',d['scripts/ci/govrev_candidate_proof.py']+b'\n# invalidating dependency\n'))]:
    mutated=dict(current);change(mutated)
    try:qualify(mutated)
    except (AssertionError,KeyError,pre.Refused):negative.append({'case':label,'rejected':True})
    else:raise AssertionError('negative control admitted: '+label)
new=copy.deepcopy(old);new['source_closure']={p:sha(b) for p,b in current.items()}
assert {k:v for k,v in new.items() if k!='source_closure'}=={k:v for k,v in old.items() if k!='source_closure'}
stage=D/'stage'
for p,b in current.items():
    target=stage/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
basepath=stage/pre.BASELINE;basepath.parent.mkdir(parents=True,exist_ok=True);basepath.write_text(json.dumps(new,indent=2)+'\n')
assert pre.read_baseline(stage)==new
for p,b in current.items():
    target=stage/p;target.write_bytes(b+b'\n')
    try:pre.read_baseline(stage)
    except pre.Refused as e:assert str(e)=='baseline_source_or_owner_not_qualified'
    else:raise AssertionError(p)
    target.write_bytes(b)
receipt={'schema':'defense.publisher_source_qualification.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_source':old_source,'qualified_source':source,'old_baseline_sha256':sha((W/pre.BASELINE).read_bytes()),'candidate_baseline_sha256':sha(basepath.read_bytes()),'checks':facts,'negative_controls':negative,'actual_read_baseline_positive':True,'actual_read_baseline_source_drift_negatives':len(current),'legacy_operations_preserved':len(old['reconciled_legacy_operations']),'all_non_source_closure_fields_unchanged':True,'current_github_history_preflight':'still required in actual Actions publisher; this script supplies no Actions identity','publication_or_cas_performed':False}
(D/'QUALIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
