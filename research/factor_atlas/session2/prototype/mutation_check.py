"""Targeted mutation witnesses in disposable copies; no source patching."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile
HERE=Path(__file__).parent
SOURCE=HERE/'pressure.py'
MUTANTS=[
 ('first_bar_direction','p, state = .5, \'FIRST_BAR_NEUTRAL\'','p, state = 1., \'FIRST_BAR_NEUTRAL\'','test_first_bar_is_explicit_neutral_not_classified'),
 ('current_return_in_scale','stdev(x[1] for x in h)','stdev([x[1] for x in h] + [current_return])','test_lagged_ddof_one_excludes_current_return'),
 ('current_target_in_reference','values = [float(x.value) for x in selected]','values = [float(x.value) for x in selected] + [target.value]','test_robust_median_mad_and_midrank'),
 ('future_bar_admitted','if bar.end_utc_s > cutoff_utc_s:','if False:','test_corrected_history_still_excludes_future_bars'),
 ('matched_clock_unchecked','if minute != self.key.clock_minute or second != 0:','if False:','test_reference_matched_clock_is_verified_not_just_string_equality'),
 ('overlap_hidden','math.fsum(by_id[s].gross_usd * (len(names)-1) for s,names in membership_of.items() if s in by_id), overlap)','0., overlap)','test_overlap_transparency_and_unique_union'),
]
def main():
 raw=SOURCE.read_text(); source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest(); out=[]
 for name,old,new,test in MUTANTS:
  if raw.count(old)!=1: raise ValueError('mutation_anchor_not_unique:'+name)
  with tempfile.TemporaryDirectory(prefix='factor-atlas-mutant-') as tmp:
   p=Path(tmp); (p/'pressure.py').write_text(raw.replace(old,new)); shutil.copy(HERE/'test_pressure.py',p/'test_pressure.py')
   result=subprocess.run(['python','-m','pytest',str(p/'test_pressure.py')+'::'+test,'-q'],capture_output=True,text=True,timeout=20)
   log=result.stdout+result.stderr
   # A collected, assertion-level failure is the required kill, not an import error.
   killed=result.returncode==1 and '1 failed' in log and 'ERROR collecting' not in log
   out.append(dict(name=name,test=test,exit_code=result.returncode,killed=killed,
                   output_sha256=hashlib.sha256(log.encode()).hexdigest(),tail=log.splitlines()[-3:]))
 assert all(x['killed'] for x in out),out
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
 print(json.dumps(dict(source_sha256=source_hash,mutants=out,killed=len(out),source_unchanged=True),indent=2,sort_keys=True))
if __name__=='__main__': main()
