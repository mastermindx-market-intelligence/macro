"""Research-only targeted challenge; mutated copies never replace the candidate."""
from pathlib import Path
import json, shutil, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
changes=[
 ('disconnect_render_reconciliation','render_feed_r10.js','    syncResearchSearch(false);\n',''),
 ('confuse_wire_null_with_ignored_response','search_client_r10.js','if (!current() || j === ignored) return;','if (!current() || j === ignored || j === null) return;'),
 ('query_only_stale_guard','search_client_r10.js','serial === _searchSerial && context === researchSearchContext()','q === FILT.q'),
 ('lose_synchronous_helper_capture','search_client_r10.js',"Promise.resolve().then(function () {\n        if (!current()) return ignored;\n        return withAuth();\n      }).then(function (h) {","withAuth().then(function (h) {"),
 ('lose_same_scope_coalescing','search_client_r10.js','if (!force && SEARCH_CONTEXT === context) return;','if (false) return;'),
 ('widen_denied_response','search_client_r10.js',"SEARCH_HITS = Object.create(null);\n          SEARCH_STATUS = 'denied';","SEARCH_HITS = null;\n          SEARCH_STATUS = 'denied';")
]
results=[]
for name,file,old,new in changes:
    with tempfile.TemporaryDirectory(prefix='rv-r10-mutation-') as tmp:
        p=Path(tmp)
        for d in ('baseline','candidate','tests'):
            shutil.copytree(ROOT/d,p/d)
        f=p/'candidate'/file;s=f.read_text();assert s.count(old)==1,(name,'anchor not unique')
        f.write_text(s.replace(old,new,1))
        r=subprocess.run(['node',str(p/'tests/test_search_context.js'),'candidate'],capture_output=True,text=True,timeout=15)
        d=json.loads(r.stdout)
        results.append({'name':name,'exit_code':r.returncode,'failed_assertions':d['failed'],'rejected':r.returncode==1 and d['failed']>0})
print(json.dumps({'scope':'Direct local mutation challenge; not independent review or additional cases in the final suite','results':results},indent=2))
raise SystemExit(0 if all(r['rejected'] for r in results) else 1)
