"""Record the completed immutable-source reference evidence before its local freeze commit."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
RIG=Path(__file__).resolve().parent
SOURCE='442042e591d255dd24b540ff240edb4c0410c297'
HTML='ad802caa6a04a7049d0adf8721354c88aa7dfec7378d5afc6bf161064f9767d0'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SOURCE
build=json.loads((RIG/'repair_dock4_build_receipt.json').read_text())
assert build['source_commit']==SOURCE and not build['source_overlays'] and build['exit_code']==0
assert build['html_sha256']==HTML
for row in build['files']:
    assert sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'], row['path']
receipts=[]
for name in ['repair_dock4/complete_browser_receipt.json','repair_dock4/review_counterexamples.json','toolbar_dock4_landings.json','country_history_dock4.json','dock4_source_disclosure_browser.json']:
    p=RIG/name;d=json.loads(p.read_text())
    assert d['source_commit']==SOURCE and d['html_sha256']==HTML
    assert d['failed']==0 and d['passed']>0, name
    receipts.append({'path':str(p.relative_to(ROOT)),'sha256':sha256(p.read_bytes()).hexdigest(),'passed':d['passed'],'failed':d['failed']})
manifest=json.loads((RIG/'repair_dock4/complete_capture_manifest.json').read_text())
local_failures=[r for p in manifest['pages'] for r in p.get('failed_responses',[]) if r.get('url','').startswith('http://intl.test/')]
assert not local_failures
country=json.loads((RIG/'toolbar_dock4_landings.json').read_text())['country_evidence_equivalence']
assert len(country)==7 and all(x['identical_country_html'] for x in country)
shots=[]
for dirname in ['after_dock4_repair','after_dock4_anchors','after_dock4_sources']:
    for p in sorted((ROOT/'mockups/refs/reference_integrity/intl-country-intelligence-20261020'/dirname).glob('*.png')):
        shots.append({'path':str(p.relative_to(ROOT)),'sha256':sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
production_paths=['templates/intl_country_cockpit.html.j2','templates/intl_country_cockpit.css','templates/intl_country_cockpit.js','lib/intl_country_inputs.py','lib/intl_country_assessment.py','engine/intl_equity_risk.py','scripts/build_intl.py']
production=[]
for name in production_paths:
    raw=(ROOT/name).read_bytes();committed=subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)
    assert raw==committed,name
    production.append({'path':name,'sha256':sha256(raw).hexdigest()})
result={'schema':'intl.reference_final_evidence.v1','recorded_at':datetime.now(timezone.utc).isoformat(),'source_commit':SOURCE,'html_sha256':HTML,'build_receipt':'repair_dock4_build_receipt.json','receipts':receipts,'screenshots':shots,'country_evidence_equivalence':country,'source_files':production,'local_static_response_failures':local_failures,'limits':['No source reacquisition or production mutation. All 510 retained input files remain the audited source snapshot.','Anonymous isolated browser only; external analytics are intentionally blocked.','Design review and normal hosted CI, merge, genuine Intl prices acquisition, covering render and served acceptance remain separate gates.']}
target=RIG/'FINAL_ARTIFACT_EVIDENCE.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
checkpoint=RIG/'OWNER_CHECKPOINT.md';old=checkpoint.read_text()
text='''# Owner checkpoint — 2026-10-20 final artifact freeze preparation

The country cockpit source is committed at442042e591d255dd24b540ff240edb4c0410c297. The final dock4 no-overlay build uses all510 retained inputs and the pinned production fonts, account, navigation, favicon and shared assistant visual assets. HTML SHA256ad802caa6a04a7049d0adf8721354c88aa7dfec7378d5afc6bf161064f9767d0. FINAL_ARTIFACT_EVIDENCE.json binds actual build, receipts, images and source hashes.

Completed browser verification:46 canonical,109 focused including complete local static assets and12 loaded-launcher post-close geometries,132 fragment/navigation,112 native history and12 narrow source-disclosure checks PASS. The earlier Japan same-document landing failure is repaired with a still-current hash check after disclosure reflow; all original failed receipts remain. All seven country sections remain byte-identical to the source-trace artifact already examined by the independent product and source reviewers. The full assistant stays in its reserved navigation slot, opens via keyboard, closes with Escape and returns focus in all12 width/language/theme contexts.

Current source also passes128 targeted macro/country/build tests, the19-file International contract suite, shared P0B128 real-browser cases and136 receipt tests, and required local guards after the actual radius-token repair. The old hosted macro/axis failure was repaired on main byPR9816; the exact failed tests and new regression pass on this source. All historical failures and audit limits are retained. No waived test or fabricated acquisition is claimed.

The original independent critics are reviewing this exact font-complete dock4 render before final artifact approval. The GDP coverage follow-up is separately documented; no research-only observation has been admitted. PR9596 remains at remote6ad0c3 until the expected-head native push. No main merge, genuine acquisition, covering render or served acceptance is claimed.

Next3: (1) freeze these bytes, receive independent artifact-bound repair verdicts and record the explicit legacy-world hierarchy tradeoff; (2) native publication, applicable hosted CI and normal protected-main acceptance; (3) genuine intl_prices acquisition, source-qualified FX acceptance, covering render and served anonymous proof. No human permission or login blocker identified.

---

'''
checkpoint.write_text(text+old)
print(json.dumps({'source_commit':SOURCE,'html_sha256':HTML,'receipts':receipts,'screenshots':len(shots),'local_static_response_failures':local_failures}))
