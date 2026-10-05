"""Targeted local challenge; no production edits or independent reviewer claim."""
from pathlib import Path
import json,re,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('implicit_scope_escalation',"if scope != 'source_text':","if False:"),
 ('eligibility_after_budget','eligible_ids=frozenset(admitted[\'items\'])','eligible_ids=None'),
 ('body_version_unchecked',"and hashlib.sha256(row['body'].encode('utf-8')).hexdigest() == expected['body_sha256']",'and True'),
 ('source_pdf_hash_unchecked',"or hashlib.sha256(original).hexdigest() != selection['pdf_sha256']",'or False'),
 ('selection_generation_unchecked',"scope['generation'] == ticket['generation'] and expected is not None",'expected is not None'),
 ('accounting_access_change_ignored',"if final_error or not _current(selection, final_scope):",'if False:')]
results=[]
for name,old,new in MUTATIONS:
    with tempfile.TemporaryDirectory(prefix='rv-r12-mutation-') as tmp:
        root=Path(tmp);shutil.copytree(ROOT/'r12',root/'r12');shutil.copytree(ROOT/'upstream',root/'upstream')
        p=root/'r12/bridge.py';s=p.read_text();assert s.count(old)==1,name;p.write_text(s.replace(old,new,1))
        r=subprocess.run([sys.executable,'-m','unittest','test_bridge'],cwd=root/'r12',capture_output=True,text=True,timeout=15)
        match=re.search(r'FAILED \((.*?)\)',r.stderr)
        failures=match.group(1) if match else ''
        results.append({'mutation':name,'exit_code':r.returncode,'summary':failures,'rejected':r.returncode!=0 and bool(match)})
print(json.dumps({'scope':'Direct local mutations, not independent review or additional test cases','results':results},indent=2))
sys.exit(0 if all(x['rejected'] for x in results) else 1)
