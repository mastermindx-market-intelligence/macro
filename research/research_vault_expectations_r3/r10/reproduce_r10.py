"""Reproduce a research review candidate; NEVER patch or run a production service.

Input: the existing component_candidates_r9.md and its two exact retained JS blocks.
Output: a new isolated directory, synthetic tests, and verification records.
No network, credentials, browser, institutional source or native host actions.
"""
from __future__ import annotations
import argparse, datetime, difflib, hashlib, json, pathlib, re, shutil, subprocess, sys

OLD = {
    'search_client_r9.js': '2460075492f450fda043f1ddd69b32a720d0e622b5bbe7880fde2bfb2325cf48',
    'render_feed_r9.js': 'b6d96b80ccab06226075318bbaade85bfe578aaad45fbfbd9b8678cca6caa686',
}
NEW = {
    'search_client_r10.js': '01b29d4261def1168f735b79814a6aaa7e21e13e2453d222347e052ae47511f0',
    'render_feed_r10.js': 'ba1f242c38cbda8307da1583dbd5aca24912da73501c2c5d5ad603e1eb07e031',
}

REPLACEMENT = "  // Reconcile only when the existing view/request scope changes (or the user\n  // explicitly resubmits). renderFeed calls this without recursively rendering.\n  function syncResearchSearch(force) {\n    var context = researchSearchContext();\n    if (!force && SEARCH_CONTEXT === context) return;\n    var serial = ++_searchSerial;\n    var q = FILT.q, inst = FILT.inst;\n    SEARCH_CONTEXT = context;\n    SEARCH_HITS = null;\n    SEARCH_STATUS = q ? 'pending' : 'idle';\n    clearTimeout(_searchTimer);\n    _searchTimer = null;\n    if (!q) return;\n    // A private sentinel cannot be confused with a JSON null server body.\n    var ignored = {};\n    function current() { return serial === _searchSerial && context === researchSearchContext(); }\n    function unavailable() {\n      if (!current()) return;\n      SEARCH_HITS = null;\n      SEARCH_STATUS = 'unavailable';\n      renderFeed();\n    }\n    _searchTimer = setTimeout(function () {\n      _searchTimer = null;\n      if (!current()) return;\n      var url = API + '/api/research/search?q=' + encodeURIComponent(q)\n        + (inst ? '&institution=' + encodeURIComponent(inst) : '');\n      // Captures synchronous helper failures as well as rejected promises.\n      Promise.resolve().then(function () {\n        if (!current()) return ignored;\n        return withAuth();\n      }).then(function (h) {\n        if (!current() || h === ignored) return ignored;\n        return fetch(url, { headers: h, credentials: 'include' });\n      }).then(function (r) {\n        if (!current() || r === ignored) return ignored;\n        if (!r) { unavailable(); return ignored; }\n        if (r.status === 401 || r.status === 402 || r.status === 403) {\n          SEARCH_HITS = Object.create(null);\n          SEARCH_STATUS = 'denied';\n          renderFeed();\n          return ignored;\n        }\n        if (!r.ok) { unavailable(); return ignored; }\n        return r.json();\n      }).then(function (j) {\n        if (!current() || j === ignored) return;\n        if (!j || j.available !== true || !Array.isArray(j.items)) { unavailable(); return; }\n        var valid = j.items.every(function (it) {\n          return it && typeof it.id === 'string' && /^[a-z0-9][a-z0-9-]{0,120}$/.test(it.id);\n        });\n        if (!valid) { unavailable(); return; }\n        var hits = Object.create(null);\n        j.items.forEach(function (it) { hits[it.id] = 1; });\n        SEARCH_HITS = hits;\n        SEARCH_STATUS = 'ready';\n        renderFeed();\n      }).catch(unavailable);\n    }, 280);\n  }\n\n  function onSearchInput() {\n    FILT.q = $('q').value.trim();\n    syncResearchSearch(true);\n    renderFeed();\n  }\n\n"

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def checked_write(path: pathlib.Path, data: str, expected: str) -> None:
    raw=data.encode('utf-8')
    if digest(raw)!=expected:
        raise ValueError(f'Candidate/source identity mismatch: {path.name}')
    path.write_bytes(raw)

def run(args: list[str], output: pathlib.Path, timeout: int=30) -> dict:
    r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    output.write_text(r.stdout,encoding='utf-8')
    output.with_suffix('.stderr.txt').write_text(r.stderr,encoding='utf-8')
    return {'exit_code':r.returncode,'result':json.loads(r.stdout)}

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-doc',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]/'component_candidates_r9.md')
    ap.add_argument('--output-dir',required=True,type=pathlib.Path,help='A new, nonexistent isolated output directory')
    args=ap.parse_args()
    blocks=re.findall(r'```javascript\n(.*?)\n```',args.source_doc.read_text(encoding='utf-8'),re.S)
    if len(blocks)!=2: raise ValueError('Expected exactly the two R9 client/renderer code blocks')
    old=[x+'\n' for x in blocks]
    for data,expected in zip(old,OLD.values()):
        if digest(data.encode())!=expected:raise ValueError('R9 selected-source hash mismatch; refuse generation')
    if args.output_dir.exists():raise ValueError('Output directory already exists; refusing overwrite')
    if shutil.which('node') is None:raise RuntimeError('Node.js is required; no installation is attempted')
    root=args.output_dir.resolve();root.mkdir(parents=True)
    for d in ('baseline','candidate','tests','results'):(root/d).mkdir()
    for (name,expected),data in zip(OLD.items(),old):checked_write(root/'baseline'/name,data,expected)
    a=old[0].index('  function onSearchInput()');z=old[0].index('  function researchSearchMessage()',a)
    changed=old[0][:a]+REPLACEMENT+old[0][z:]
    rendered=old[1].replace('  function renderFeed() {\n','  function renderFeed() {\n    syncResearchSearch(false);\n',1)
    for (name,expected),data in zip(NEW.items(),[changed,rendered]):checked_write(root/'candidate'/name,data,expected)
    for name in ('test_search_context.js','mutation_review.py'):
        shutil.copy2(pathlib.Path(__file__).resolve().parent/name,root/'tests'/name)
    red=run(['node',str(root/'tests/test_search_context.js'),'baseline'],root/'results/red_r9.json')
    if red['exit_code']!=1 or red['result']['total']!=31 or red['result']['failed']!=15:
        raise ValueError('Baseline no longer matches the declared 31-check/15-failure characterization')
    green=run(['node',str(root/'tests/test_search_context.js'),'candidate'],root/'results/green_r10.json')
    if green['exit_code']!=0 or green['result']['total']!=31 or green['result']['failed']!=0:
        raise ValueError('Candidate checks did not pass')
    mutations=run([sys.executable,str(root/'tests/mutation_review.py')],root/'results/mutations.json')
    if mutations['exit_code']!=0 or not all(x['rejected'] for x in mutations['result']['results']):
        raise ValueError('Targeted mutation challenge did not reject each regression')
    final=run(['node',str(root/'tests/test_search_context.js'),'candidate'],root/'results/final_r10.json')
    if final['exit_code'] or final['result']['failed']:raise ValueError('Post-challenge candidate did not pass')
    for name in NEW:
        subprocess.run(['node','--check',str(root/'candidate'/name)],check=True,capture_output=True,text=True,timeout=10)
    patches=[]
    for name,before,after in [('search_client.js',old[0],changed),('render_feed.js',old[1],rendered)]:
        patches.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/selected/'+name,tofile='b/selected/'+name))
    (root/'review_components_r10.patch').write_text(''.join(patches),encoding='utf-8')
    receipt={
        'schema':'research.client_context_review.r10',
        'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_document':'Existing component_candidates_r9.md; selected JS blocks SHA256-verified',
        'r9_start_head':'e62f39677466b0c342b750357b0e3aa10e13a708',
        'runtime_inspection_pin':'e729d0fd9d48868b49a1911d4098c689b3d373bd',
        'current_client_blob':'1f0b673da6c3d6a44ad3d74b2994f70b9a4311c8',
        'old_selected_sha256':OLD,'new_selected_sha256':NEW,
        'red':{'total':31,'passed':16,'failed':15},
        'final':{k:final['result'][k] for k in ('executed_at_utc','node','total','passed','failed')},
        'mutation_results':mutations['result']['results'],
        'interpretation':'Three failure families; not fifteen independent production defects. Six mutations are not additional passing cases.',
        'scope':'Selected JS client and selected renderer with controlled DOM/auth/network/timers. No whole-client, HTTP, browser, billing, original-source or model proof.',
        'historical_r9_60_checks_rerun':False,'company_association_built':False,
        'owner_acceptance':False,'runtime_modified':False,'deployed':False,
        'file_sha256':{str(p.relative_to(root)):digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()},
    }
    (root/'verification_r10.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output_dir':str(root),'final':receipt['final'],'mutations_rejected':len(receipt['mutation_results'])},indent=2))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f'Reproduction refused/failed: {exc}',file=sys.stderr);raise SystemExit(1)
