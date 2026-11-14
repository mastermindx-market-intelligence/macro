"""Reproduce the isolated review; no repository/runtime writes or external access."""
from __future__ import annotations
from pathlib import Path
import argparse,datetime,hashlib,json,platform,re,shutil,sqlite3,subprocess,sys
HERE=Path(__file__).resolve().parent
BASELINE='0b035b34489a4efd2ae7a3c59d153b3d1977701a'
PENDING='1bc0aacd46d8ec0ad25d3b53341040a3e6aa1af8'
R9PATCH='d9593533dad00251a97d0813f6598ea1fffb8236'
COMPOSITE='58bfdaf91f1cb7f9a4f7e1f700bd90be3269fe9ea7d6cc156661a9a456b89d6f'
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def invoke(args,cwd,stdout,expected=0):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=35)
    stdout.write_text(r.stdout);stdout.with_suffix('.stderr.txt').write_text(r.stderr)
    if r.returncode!=expected:raise RuntimeError(f'Command failed: {args[0]} (see {stdout})')
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--baseline-corpus',type=Path)
    p.add_argument('--pending-corpus',type=Path)
    p.add_argument('--r9-patch',type=Path)
    a=p.parse_args()
    base=a.baseline_corpus or HERE.parent/'upstream/corpus_baseline.py'
    patch=a.r9_patch or HERE.parent/'corpus_search_r9.patch'
    pending=a.pending_corpus or HERE.parent/'upstream/corpus_pending.py'
    b=base.read_bytes();raw=patch.read_bytes();pending_bytes=pending.read_bytes()
    if blob(b)!=BASELINE or blob(raw)!=R9PATCH or blob(pending_bytes)!=PENDING:
        raise ValueError('Dependency identity mismatch')
    if a.output_dir.exists():raise ValueError('Output directory exists; no overwrite')
    if shutil.which('pdftotext') is None or shutil.which('git') is None:raise RuntimeError('git and pdftotext must already be installed')
    import reportlab
    out=a.output_dir.resolve();out.mkdir(parents=True)
    for name in ('r12','upstream','results','work/engine/research_vault'):(out/name).mkdir(parents=True)
    for f in HERE.glob('*.py'):shutil.copy2(f,out/'r12'/f.name)
    (out/'corpus_search_r9.patch').write_bytes(raw)
    target=out/'work/engine/research_vault/corpus.py';target.write_bytes(b)
    (out/'upstream/corpus_baseline.py').write_bytes(b)
    target.write_bytes(pending_bytes)
    (out/'upstream/corpus_pending.py').write_bytes(pending_bytes)
    s=target.read_text();assert s.count('import hashlib\n')==1
    target.write_text(s.replace('import hashlib\n','import hashlib\nimport json\n',1))
    text=raw.decode();body='--- a/engine/research_vault/corpus.py\n+++ b/engine/research_vault/corpus.py\n'+text[text.index('@@ -347'):]
    contextual=out/'results/r9_pending_context.patch';contextual.write_text(body)
    subprocess.run(['git','apply','--check',str(contextual)],cwd=out/'work',check=True,capture_output=True,text=True,timeout=10)
    subprocess.run(['git','apply',str(contextual)],cwd=out/'work',check=True,capture_output=True,text=True,timeout=10)
    if sha(target.read_bytes())!=COMPOSITE:raise ValueError('Composite identity mismatch')
    shutil.copy2(target,out/'upstream/corpus_review.py')
    checks=invoke([sys.executable,'-m','unittest','test_bridge','-v'],out/'r12',out/'results/tests.txt')
    if not re.search(r'Ran 32 tests',checks.stderr) or not checks.stderr.rstrip().endswith('OK'):raise ValueError('Unexpected test result')
    mut=invoke([sys.executable,'mutation_review.py'],out/'r12',out/'results/mutations.json')
    mutations=json.loads(mut.stdout)
    if len(mutations['results'])!=6 or not all(x['rejected'] for x in mutations['results']):raise ValueError('Mutation challenge failed')
    invoke([sys.executable,'demo.py','--output-dir',str(out/'demo')],out/'r12',out/'results/demo.txt')
    demo=json.loads((out/'demo/demo_result.json').read_text())
    receipt={'schema':'research.source_discovery_bridge.r12','verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'ISOLATED_REVIEW_PASS_NOT_PRODUCTION','tests':{'total':32,'failures':0,'errors':0},'mutations':mutations['results'],
        'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'reportlab':reportlab.Version,
        'pdftotext':subprocess.run(['pdftotext','-v'],capture_output=True,text=True).stderr.splitlines()[0],
        'source_identities':{'baseline_corpus_git_blob':BASELINE,'pending_corpus_git_blob':PENDING,'r9_patch_git_blob':R9PATCH,'review_composite_sha256':COMPOSITE},
        'demo':{'source_pdf_sha256':demo['original_pdf_sha256'],'body_sha256':demo['extracted_body_sha256'],
                'page':demo['initial_evidence']['passages'][0]['locator']['page'],'old_selection_after_change':demo['old_selection_after_change']['status'],
                'meter_callback_calls':demo['meter_callback_calls']},
        'source_and_version_integrity_measured':True,'source_material':'entirely synthetic, programmatically created',
        'actual_gateway_run':False,'actual_auth_or_ledger_run':False,'original_institutional_source_admitted':False,
        'actual_browser_run':False,'model_evaluation':False,'runtime_modified':False,
        'limits':'Full corpus and incumbent selector executed; Brain/gateway adapter, permission and accounting remain controlled proposals.',
        'code_sha256':{f.name:sha(f.read_bytes()) for f in sorted((out/'r12').glob('*.py'))}}
    (out/'verification_r12.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'output_dir':str(out),'tests':receipt['tests'],'demo':receipt['demo']},indent=2))
if __name__=='__main__':main()
