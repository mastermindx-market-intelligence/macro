"""Finite root-owned CI enrollment; no product or test assertion changes."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,re,subprocess,yaml
ROOT=Path(__file__).resolve().parents[5];HERE=Path(__file__).resolve().parent
manifest=ROOT/".github/ci/legacy-jobs.yml";baseline=ROOT/"config/unrun_test_baseline.json"
assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()=="14ed4f12f31b71c63bbabd969aebbf9c4305ccaa"
before=manifest.read_bytes();old=before.decode()
assert sha256(before).hexdigest()=="b9c7feb06f5f76ea9fbab5707a770e8b46adaaa6797ef28051a060ad2f7e40fa"
bb=baseline.read_bytes();assert sha256(bb).hexdigest()=="21306afcfdaff9c31b0c329987c637fbfb0a366bccfaf59b64d3830be6eeefb8"
closure=json.loads((HERE/"ci_build_enrollment/tracked_closure.json").read_text())
added=[p for p in closure["uncovered_required_paths"] if p!=".github/ci/legacy-jobs.yml"]
assert len(added)==len(set(added)) and all((ROOT/p).is_file() for p in added)
start=old.index("  international-workspace-foundation:\n")
end=old.index("\n  international-workspace-browser:",start)
block=old[start:end]
assert "tests/test_intl_build.py" not in block
insert="    paths:\n      # Build-failure suite: measured tracked reads and recursive template includes.\n"+"".join('      - "'+p+'"\n' for p in added)
block=block.replace("    paths:\n",insert,1)
block=block.rstrip()+"\n      - name: International primary build and optional stock isolation\n        run: python -m pytest tests/test_intl_build.py -q\n"
new=old[:start]+block+old[end:]
parsed=yaml.safe_load(new)
job=parsed["jobs"]["international-workspace-foundation"]
assert len(job["paths"])==len(set(job["paths"]))
assert job["steps"][-1]["run"]=="python -m pytest tests/test_intl_build.py -q"
prior=json.loads(bb);line='    "tests/test_intl_build.py",\n'
assert bb.decode().count(line)==1
newbase=bb.decode().replace(line,"",1);afterbase=json.loads(newbase)
assert set(prior["grandfathered"])-set(afterbase["grandfathered"])=={"tests/test_intl_build.py"}
assert set(afterbase["grandfathered"])-set(prior["grandfathered"])==set()
manifest.write_text(new);baseline.write_text(newbase)
record={"schema":"intl.build_ci_enrollment_edit.v1","applied_at":datetime.now(timezone.utc).isoformat(),"base_head":"14ed4f12f31b71c63bbabd969aebbf9c4305ccaa","owner":"international-workspace-foundation","added_paths":added,"added_command":job["steps"][-1]["run"],"removed_grandfathered_suite":"tests/test_intl_build.py","dependency_command_unchanged":job["steps"][2]["run"],"source_scope":"root finite mechanical integration of existing accepted regressions, based on independent exact-head enrollment review and observed tracked/static template closure; no product implementation or test assertion edits","manifest_before_sha256":sha256(before).hexdigest(),"manifest_after_sha256":sha256(manifest.read_bytes()).hexdigest(),"baseline_before_sha256":sha256(bb).hexdigest(),"baseline_after_sha256":sha256(baseline.read_bytes()).hexdigest(),"verification":"existing suite12passed before enrollment; owner/planner/contract gates pending"}
(HERE/"ci_build_enrollment/edit_receipt.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record,indent=2))
