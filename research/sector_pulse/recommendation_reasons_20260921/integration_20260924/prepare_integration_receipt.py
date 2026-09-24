"""Prepare an immutable #7669 integration in a temporary native Git index.
No branch/ref/index/worktree change; no collection, push, merge retry or deploy.
Reuses the already-computed merge tree and native renderer/finalizer only.
"""
from pathlib import Path, PurePosixPath
from copy import deepcopy
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup
import hashlib, json, os, re, subprocess, sys
ROOT = Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/theme-recommendation-reasons-20260921-sol')
OUT = Path('/tmp/mmx-leadership-resume-20260924/integration').resolve()
HEAD = '76cb5371ec77a711bdb3fe33469e73d0ecdc3d18'
BASE = 'd7711a0a08db8008ffe5975bfb3e6b242e4c70bd'
AUTO = '1cd7565c9e6030ef132f6c05a7eefe9af7e07a9c'
ENV = {**os.environ, 'GIT_NO_LAZY_FETCH': '1'}
def git(*args, data=None, env=None):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], input=data,
                                   env=env or ENV, stderr=subprocess.PIPE)
def text(*args): return git(*args).decode().strip()
assert text('rev-parse', 'HEAD') == HEAD
assert not text('status', '--porcelain=v1')
source_paths = ['engine/basket_score.py', 'engine/theme_scoring.py', 'engine/sector_pulse.py',
                'templates/basket_detail.html.j2', 'lib/pages.py',
                'scripts/optimize_assets.py', 'scripts/externalize_css.py']
for path in source_paths:
    assert text('rev-parse', HEAD+':'+path) == text('rev-parse', AUTO+':'+path), path
raw_result = Path('/tmp/mmx-leadership-finalize-20260924-0433/coverage-merge-tree.txt').read_text()
assert raw_result.splitlines()[0] == AUTO
paths = [line.split('Merge conflict in ', 1)[1] for line in raw_result.splitlines()
         if line.startswith('CONFLICT (content): Merge conflict in ')]
assert len(paths) == len(set(paths)) == 121
assert all(re.fullmatch(r'site/basket(?:_china|_hk|_canada|_intl)?/[a-z0-9_-]+\.html', p) for p in paths)
OUT.mkdir(exist_ok=True); site = OUT/'site'; site.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))
from engine import basket_score
from jinja2 import Environment, FileSystemLoader
from lib.pages import write_page, externalize_css_text, externalize_js_text, dbase_prefix, css_imports
from scripts.externalize_css import MIN_BYTES
from scripts.optimize_assets import make_optimizer
tmpl = Environment(loader=FileSystemLoader(str(ROOT/'templates')), autoescape=True).get_template('basket_detail.html.j2')
assets = {}; generated_assets = {}; prepared = []; rows = []
def asset_path(page_dir, url):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path: return None
    p = (page_dir/unquote(parsed.path)).resolve()
    assert p.is_relative_to(site.resolve()), url
    return p

def materialize(p):
    rel = 'site/'+p.relative_to(site).as_posix()
    if rel in assets: return
    if p.is_file(): body = p.read_bytes()
    else:
        body = git('show', AUTO+':'+rel)
        p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(body)
    assets[rel] = hashlib.sha256(body).hexdigest()
    if p.suffix == '.css':
        for url in css_imports(body.decode()):
            child = asset_path(p.parent, url)
            if child is not None: materialize(child)

for relative in paths:
    original = git('show', BASE+':'+relative); s = original.decode()
    assert s.count('const DETAIL = ') == 1
    detail, _ = json.JSONDecoder().raw_decode(s.split('const DETAIL = ', 1)[1])
    result = deepcopy(detail); p = OUT/relative
    assert detail['basket']['id'] == p.stem
    stamp = re.findall(r'<span>([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} UTC)</span>', s)
    assert len(stamp) == 1, relative
    result['act_now'] = basket_score.act_now_stocks(result['members'], result['theme'])
    for key in ('status','buys','uncovered'):
        assert result['act_now'][key] == detail['act_now'][key], (relative,key)
    assert {k:v for k,v in result.items() if k!='act_now'} == {k:v for k,v in detail.items() if k!='act_now'}
    before, after = deepcopy(detail['act_now']), deepcopy(result['act_now'])
    for a in (before,after):
        for k in ('entry_checks','entry_summary','note_en','note_zh'): a.pop(k,None)
        for row in a.get('early_turn_watch',[]):
            row.pop('blocker_en',None); row.pop('blocker_zh',None)
    assert before == after, (relative,'non-explanation mutation')
    region = result.get('region','us')
    en = 'Sector Intelligence' if region=='us' else 'China Sector Intelligence' if region=='china' else 'Theme Rotation Desk'
    zh = '行业智慧' if region=='us' else '中国行业智慧' if region=='china' else '主题轮动台'
    raw = json.dumps(result,separators=(',',':'),ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    html = tmpl.render(detail_json=raw,basket_name=result['basket'].get('name',p.stem),
                       generated_utc=stamp[0],back_href=result['back'],back_label_en=en,back_label_zh=zh)
    def external_asset(body,index,media=None,kind='css'):
        b = body.encode()
        if len(b)<MIN_BYTES: return None
        digest = hashlib.sha256(b).hexdigest()[:8]
        target = site/'assets'/kind/(digest+'.'+kind)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists(): assert target.read_bytes()==b
        else: target.write_bytes(b)
        generated_assets['site/'+target.relative_to(site).as_posix()] = target
        return dbase_prefix(p)+'assets/'+kind+'/'+digest+'.'+kind+'?v='+digest
    html = externalize_css_text(html,external_asset)
    html = externalize_js_text(html,lambda body,index:external_asset(body,index,kind='js'))
    soup = BeautifulSoup(html,'html.parser')
    for tag in soup.find_all(['script','link']):
        url = tag.get('src') if tag.name=='script' else tag.get('href')
        if not url or not urlsplit(url).path.endswith(('.css','.js')): continue
        target = asset_path(p.parent,url)
        if target is not None: materialize(target)
    html = make_optimizer(site)(html,p.parent)
    prepared.append((p,html))
    rows.append({'path':relative,'input_sha256':hashlib.sha256(original).hexdigest(),
                 'as_of':detail['as_of'],'generation_stamp':stamp[0],
                 'members':len(detail['members']),
                 'assessed':sum(isinstance(x.get('conviction'),dict) and x['conviction'].get('score') is not None for x in detail['members']),
                 'status_buys_coverage_unchanged':True,'non_explanation_data_unchanged':True})
    if len(rows)%25==0: print('VALIDATED',len(rows),flush=True)
# Only publish the temporary outputs after every data-invariant check passes.
for (p,html),row in zip(prepared,rows):
    p.parent.mkdir(parents=True,exist_ok=True); write_page(p,html)
    row['output_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
assert not text('status','--porcelain=v1'), 'proof unexpectedly changed source worktree'
index=OUT/'prepared.index'; assert not index.exists(), 'reconcile existing index before repeating'
ienv={**ENV,'GIT_INDEX_FILE':str(index)}
git('read-tree',AUTO,env=ienv)
for relative,p in [(r['path'],OUT/r['path']) for r in rows]+list(generated_assets.items()):
    oid=git('hash-object','-w','--stdin',data=p.read_bytes()).decode().strip()
    git('update-index','--add','--cacheinfo','100644,'+oid+','+relative,env=ienv)
tree=git('write-tree',env=ienv).decode().strip()
changed=text('diff','--name-only',AUTO,tree).splitlines()
assert set(paths)<=set(changed)
assert set(changed)<=set(paths)|set(generated_assets), changed
proof={'head':HEAD,'base':BASE,'native_auto_tree':AUTO,'resolved_tree':tree,
       'pages':len(rows),'member_rows':sum(r['members'] for r in rows),
       'assessed_rows':sum(r['assessed'] for r in rows),'rows':rows,'assets':assets,
       'changes_from_native_auto_tree':changed,'source_worktree_clean':True,
       'branch_updated':False,'pushed':False,'production':False}
(OUT/'proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
(OUT/'prepared-tree.txt').write_text(tree+'\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('rows','assets','changes_from_native_auto_tree')},indent=2),flush=True)
