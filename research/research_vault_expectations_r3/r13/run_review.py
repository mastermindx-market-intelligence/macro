"""Reproduce the R13 owner mapping in a NEW isolated directory.

The actual quota and tier modules are hash-checked. Identity/source permissions
remain controlled test inputs; no remote services, credentials or model calls.
This executes the R13 suite, not the earlier R12 test/demo acceptance cycle.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, importlib.util, json, os, pathlib, re, shutil, sqlite3, subprocess, sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
EXPECTED={
 'corpus_baseline.py':'0b035b34489a4efd2ae7a3c59d153b3d1977701a',
 'corpus_pending.py':'1bc0aacd46d8ec0ad25d3b53341040a3e6aa1af8',
 'view_ratelimit.py':'5e33b4d213ff3b9497134343712921e3d3ac6b77',
 'tiers.py':'cf59370147d735a84f791ac7469c87136d7b9572',
}
COMPOSITE='58bfdaf91f1cb7f9a4f7e1f700bd90be3269fe9ea7d6cc156661a9a456b89d6f'
def gitblob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def sha(data):return hashlib.sha256(data).hexdigest()
def call(argv,cwd,target):
 r=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,timeout=40)
 target.write_text(r.stdout);target.with_suffix('.stderr.txt').write_text(r.stderr)
 if r.returncode:raise RuntimeError(f'Reproduction failed: {argv[0]}; see {target}')
 return r

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output-dir',type=pathlib.Path,required=True);a=ap.parse_args()
 source={name:(ROOT/'upstream'/name).read_bytes() for name in EXPECTED}
 for name,b in source.items():
  if gitblob(b)!=EXPECTED[name]:raise ValueError('Upstream identity mismatch: '+name)
 raw=(ROOT/'corpus_search_r9.patch').read_bytes()
 if gitblob(raw)!='d9593533dad00251a97d0813f6598ea1fffb8236':raise ValueError('R9 patch identity mismatch')
 if sha((ROOT/'r12/bridge.py').read_bytes())!='4a3376301c711512a5d4d96c07a32e5d7091dafbb6df193f4bb232944e068929':raise ValueError('Prior bridge identity mismatch')
 if a.output_dir.exists():raise ValueError('Output directory exists; refuse overwrite')
 if not shutil.which('git') or not shutil.which('pdftotext'):raise RuntimeError('git and pdftotext must be installed; no installation attempted')
 import reportlab
 out=a.output_dir.resolve();out.mkdir(parents=True)
 for d in ('r13','upstream','prior/r12','prior/upstream','prior/demo','work/engine/research_vault','results'):(out/d).mkdir(parents=True)
 for f in HERE.glob('*.py'):shutil.copy2(f,out/'r13'/f.name)
 for name in ('bridge.py','fixtures.py'):shutil.copy2(ROOT/'r12'/name,out/'prior/r12'/name)
 for name,b in source.items():
  (out/('prior/upstream' if name.startswith('corpus') else 'upstream')/name).write_bytes(b)
 shutil.copy2(ROOT/'upstream/brain_accounting_excerpt.py.txt',out/'upstream/brain_accounting_excerpt.py.txt')
 target=out/'work/engine/research_vault/corpus.py';s=source['corpus_pending.py'].decode()
 if s.count('import hashlib\n')!=1:raise ValueError('Expected pending corpus import anchor')
 target.write_text(s.replace('import hashlib\n','import hashlib\nimport json\n',1))
 text=raw.decode();patch=out/'work/r9_context.patch'
 patch.write_text('--- a/engine/research_vault/corpus.py\n+++ b/engine/research_vault/corpus.py\n'+text[text.index('@@ -347'):])
 for command in (['git','apply','--check',str(patch)],['git','apply',str(patch)]):subprocess.run(command,cwd=out/'work',check=True,capture_output=True,text=True,timeout=10)
 if sha(target.read_bytes())!=COMPOSITE:raise ValueError('Unexpected review composite')
 shutil.copy2(target,out/'prior/upstream/corpus_review.py')
 spec=importlib.util.spec_from_file_location('r13_fixture_input',out/'prior/r12/fixtures.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 record=m.make_source(out/'prior/demo/synthetic_original.pdf')
 (out/'prior/demo/extracted_original.txt').write_text(record['body'])
 tests=call([sys.executable,'-m','unittest','-v','test_owner_adapter'],out/'r13',out/'results/tests.txt')
 if not re.search(r'Ran 46 tests',tests.stderr) or not tests.stderr.rstrip().endswith('OK'):raise ValueError('Unexpected test count or result')
 mutation=call([sys.executable,'mutation_review.py'],out/'r13',out/'results/mutations.json');mu=json.loads(mutation.stdout)
 if len(mu['cases'])!=8 or not all(x['rejected'] for x in mu['cases']):raise ValueError('Targeted regression not caught')
 call([sys.executable,'accounting_demo.py'],out/'r13',out/'results/accounting_demo.json')
 # Re-run after the disposable mutations to ensure the tested source is unchanged.
 final=call([sys.executable,'-m','unittest','-q','test_owner_adapter'],out/'r13',out/'results/final.txt')
 if not re.search(r'Ran 46 tests',final.stderr) or not final.stderr.rstrip().endswith('OK'):raise ValueError('Post-challenge suite failed')
 for f in sorted((out/'r13').glob('*.py')):compile(f.read_bytes(),str(f),'exec')
 demo=json.loads((out/'results/accounting_demo.json').read_text())
 receipt={
  'schema':'research.owner_contract_integration.r13','status':'ISOLATED_OWNER_MAPPING_PASS_NOT_PRODUCTION',
  'executed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,
  'tests':{'total':46,'failures':0,'errors':0},'mutations':mu['cases'],
  'complete_real_modules_executed':['view_ratelimit.py','tiers.py','corpus review composition'],
  'selected_transcribed_wrappers':['_peek_report_view','_charge_report_view'],
  'authentication_and_source_use':'controlled stand-ins, not real grants',
  'gateway_full_source_executed':False,'full_research_report_executed':False,
  'actual_ledger_files_exercised':True,'production_state_touched':False,
  'institutional_pdf_admitted':False,'model_benchmark_run':False,'browser_proof':False,
  'source_blobs':EXPECTED,'corpus_composite_sha256':COMPOSITE,
  'input_pdf_sha256':record['pdf_sha256'],'input_body_sha256':record['body_sha256'],
  'demo':demo,
  'file_sha256':{str(f.relative_to(out)):sha(f.read_bytes()) for f in sorted(out.rglob('*')) if f.is_file() and '__pycache__' not in f.parts},
 }
 (out/'verification_r13.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'output_dir':str(out),'tests':receipt['tests'],'regressions_rejected':len(mu['cases']),'ledger_demo':demo},indent=2))
if __name__=='__main__':main()
