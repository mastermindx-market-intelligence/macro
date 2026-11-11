from pathlib import Path
import subprocess,sys,json,hashlib,datetime,importlib.metadata
R=Path.cwd()
E=R/'mockups/evidence/container-edge-removal'
OUT=R/'research/evidence/ew_p4_descriptive_ui_20261031'
previous=json.loads((E/'ew-p4-previous-receipt.json').read_text())
paths=[row['path'] for row in previous['pr_source_equivalence']['render_files']]
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head!='a739405d248e3e985c6215067878028f8403fad9','Save the exact final source snapshot before capture.'
def blob(data):
 return hashlib.sha1(b'blob %d\0'%len(data)+data).hexdigest()
rows=[]
for path in paths:
 actual=blob((R/path).read_bytes())
 expected=subprocess.check_output(['git','rev-parse',head+':'+path],text=True).strip()
 assert actual==expected,(path,'source differs from committed capture snapshot')
 rows.append({'path':path,'blob_at_source_revision':expected,'blob_on_pr_branch':actual})
command=[sys.executable,'tests/probe_ew_p4_descriptive_ui_browser.py','--output',str(OUT)]
subprocess.run(command,check=True)
report=json.loads((OUT/'receipt.json').read_text())
assert report['source_revision']==head and len(report['cases'])==68
for row in rows:
 assert blob((R/row['path']).read_bytes())==row['blob_at_source_revision'],row['path']
for case in report['cases']:
 assert hashlib.sha256((OUT/case['screenshot']).read_bytes()).hexdigest()==case['sha256']
 assert case['no_horizontal_overflow'] and case['page_errors']==[],case['screenshot']
report['pr_source_equivalence']={
 'note':'Actual 68-case EW-P4 probe rerun from the exact committed managed source snapshot at source_revision. Every listed input was verified against that commit before and after capture. blob_on_pr_branch denotes the final PR #10654 candidate bytes, independently checked by CI after publication; this receipt does not assert merge, deployment or real-account acceptance.',
 'pr_branch':'claude/ssd-confident-khayyam-877b44-37f024569f201e61',
 'pr_parent_of_evidence_commit':'c7f08871a7650e1fc7052d792a1592b55cf34c81',
 'render_files':rows,'all_equal':True}
report['recapture']={
 'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_snapshot':head,
 'source_snapshot_tree':subprocess.check_output(['git','rev-parse',head+'^{tree}'],text=True).strip(),
 'command':command,'exit_code':0,
 'python_playwright_version':importlib.metadata.version('playwright'),
 'previous_receipt':'mockups/evidence/container-edge-removal/ew-p4-previous-receipt.json',
 'previous_receipt_sha256':hashlib.sha256((E/'ew-p4-previous-receipt.json').read_bytes()).hexdigest()}
(OUT/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(E/'ew-p4-recapture-receipt.json').write_text(json.dumps({'source_snapshot':head,'render_inputs':len(rows),'cases':68,'contact_sheets':len(report['contact_sheets']),'receipt_sha256':hashlib.sha256((OUT/'receipt.json').read_bytes()).hexdigest(),'exit_code':0},indent=2)+'\n')
print(json.dumps({'source_snapshot':head,'cases':68,'render_inputs':len(rows),'exit_code':0}),flush=True)
