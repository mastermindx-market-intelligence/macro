"""Read-only R14 CI selection proof through the existing planner, not a new gate."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import yaml

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import run_ci_pack as planner
BASE='b74875a6171a4d52cb48decf70d608f106a9fa8e'
FILE='.github/ci/legacy-jobs.yml'
TARGET='engine/btc_intraday_cvd.py'
JOBS={'conviction-profile','unrun-picks-boards'}
RUNTIME=['scripts/build_vector.py','templates/vector.html.j2','engine/btc_intraday_cvd.py',
         'collectors/_crypto_observations.py','collectors/_first_seen_store.py','collectors/okx.py','collectors/bgeo.py',
         'tests/test_ci_pack.py','scripts/check_contract_delta.py','scripts/run_ci_pack.py',
         'config/unrun_test_waivers.yml']


def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    original=subprocess.check_output(['git','show',BASE+':'+FILE],cwd=ROOT)
    current=(ROOT/FILE).read_bytes();old=yaml.safe_load(original);new=yaml.safe_load(current)
    changed=planner._classify_bounded_manifest_job_delta(old,new)
    assert set(changed)==JOBS and len(changed)==2,changed
    restored=yaml.safe_load(current)
    for job in JOBS:
        a=old['jobs'][job]['paths'];b=restored['jobs'][job]['paths']
        assert TARGET not in a and b.count(TARGET)==1
        b.remove(TARGET);assert b==a,'An earlier trigger was changed or reordered'
    assert restored==old,'Non-path manifest semantics changed'
    planes={}
    with tempfile.TemporaryDirectory(prefix='crypto-ci-before-') as tmp:
        p=Path(tmp)/'legacy-jobs.yml';p.write_bytes(original)
        for gate in ['code','data']:
            selected,note=planner.select_jobs(planner.load_legacy_jobs(ROOT/FILE,gate=gate),[TARGET])
            before,_=planner.select_jobs(planner.load_legacy_jobs(p,gate=gate),[TARGET])
            now={j.job_id for j in selected};then={j.job_id for j in before}
            expected={j for j in JOBS if old['jobs'][j].get('gate','code')==gate}
            assert now-then==expected and not then-now,(gate,sorted(now-then),sorted(then-now))
            assert expected<=now
            planes[gate]={'selected_before':sorted(then),'selected_after':sorted(now),
                          'added_selection':sorted(now-then),'removed_selection':sorted(then-now),'selection_note':note}
    # Same source/layout behavior and the exact checks that caught the issue.
    identity={}
    for path in RUNTIME:
        b=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
        assert (ROOT/path).read_bytes()==b,path
        identity[path]=sha(b)
    result={'classification':'LOCAL_CONFIG_SELECTION_PROOF_NOT_DEPLOYMENT_OR_HOSTED_CI',
            'baseline':BASE,'manifest_before_sha256':sha(original),'manifest_after_sha256':sha(current),
            'changed_jobs':sorted(changed),'selection_by_gate':planes,
            'all_other_manifest_semantics_identical':True,'unchanged_source_sha256':identity}
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
