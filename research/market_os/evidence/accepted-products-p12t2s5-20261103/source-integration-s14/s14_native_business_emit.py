"""Existing one-page renderer + existing canonical asset transforms, no producer."""
import sys,os,json,hashlib,copy,re,datetime
from pathlib import Path
from urllib.parse import urlsplit
from html.parser import HTMLParser
root=Path.cwd();sys.path.insert(0,str(root))
from scripts import build_macro_suite_pages as B, optimize_assets as O, externalize_css as E
from lib import pages as P, macro_suite_view as V
from engine.market_os.macro_workspaces import contract
site=root/'site';page=next(p for p in B.SUITE_PAGES if p.workspace_id=='business_activity');target=site/page.output;data=site/'macrodata'
snap,receipt=B.read_workspace(data,page);contract.validate(snap);snapshot_before=copy.deepcopy(snap)
inputs=[data/'workspaces/manifest.json',data/'workspaces/business_activity/US/latest.json',root/'templates/theme.js']
for name in B.SHARED_ASSETS:
 a=root/'templates'/name;b=site/name;assert a.read_bytes()==b.read_bytes(),name;inputs += [a,b]
hash_inputs=lambda:{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
before=hash_inputs();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ');view=V.build_view(snap,page_built_at=stamp,artifact=receipt)
assert len(view['metrics'])==len(snap['metrics']['items'])==31
assert view['context']['calculation_as_of'] is None and view['context']['last_source_cut'] is None
assert not any('No accepted source cut' in x['body']['en'] for x in view['diagnostics'])
writes=[];blocked=[]
def pathof(x):return Path(os.fsdecode(x)).absolute() if isinstance(x,(str,bytes,os.PathLike)) else None
def allowed(p):return p==target or (p is not None and p.parent==site and p.name.startswith('.'+target.name))
def guard(event,args):
 if event=='open':
  p=pathof(args[0]);mode=args[1];flags=args[2];write=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)))
  if write and p is not None:
   if not allowed(p):blocked.append([event,str(p)]);raise PermissionError('S14 singlepage write fence')
   writes.append([event,str(p)])
 elif event in ['os.rename','os.remove','os.chmod','os.mkdir']:
  p=pathof(args[0]);ok=allowed(p) or (event=='os.mkdir' and p==site and p.is_dir())
  if event=='os.rename':ok=ok and allowed(pathof(args[1]))
  if not ok:blocked.append([event,str(p)]);raise PermissionError('S14 singlepage write fence')
  writes.append([event,str(p)])
sys.addaudithook(guard)
result=B.build_page(root,page,data_root=data,out_dir=site,env=B._environment(root),page_built_at=stamp);assert result[1]
native=target.read_text();styles=[len(s.encode()) for s in re.findall(r'<style\b[^>]*>(.*?)</style>',native,re.S)]
assert all(n<E.MIN_BYTES for n in styles),styles
# Existing externalization interface: sub-threshold inline material stays put;
# there is no opt-in JS block in this page and no new content-addressed asset.
def tiny_only(css,index,media=None):
 assert len(css.encode())<E.MIN_BYTES;return None
externalized=P.externalize_css_text(native,tiny_only);assert externalized==native
assert not re.search(r'<script\b[^>]*data-externalize',native)
optimized=O.make_optimizer(site)(externalized,site)
P.write_page(target,optimized);final=target.read_text();assert final==optimized
assert O.make_optimizer(site)(final,site)==final
assert re.findall(r'<time\b[^>]*>.*?</time>',native,re.S)==re.findall(r'<time\b[^>]*>.*?</time>',final,re.S)
class Body(HTMLParser):
 def __init__(self,s):super().__init__();self.body=False;self.hidden=0;self.text=[];self.feed(s)
 def handle_starttag(self,t,a):
  if t=='body':self.body=True
  if t in ['script','style']:self.hidden+=1
 def handle_endtag(self,t):
  if t in ['script','style']:self.hidden=max(0,self.hidden-1)
  if t=='body':self.body=False
 def handle_data(self,d):
  if self.body and not self.hidden:self.text.append(d)
assert Body(native).text==Body(final).text
class Assets(HTMLParser):
 def __init__(self,s):super().__init__();self.urls=[];self.feed(s)
 def handle_starttag(self,t,a):
  d=dict(a);u=d.get('src') if t=='script' else d.get('href') if t=='link' else None
  if u and not urlsplit(u).scheme and not u.startswith('//') and urlsplit(u).path.endswith(('.css','.js')):self.urls.append(u)
asset_hashes={}
for url in Assets(final).urls:
 parsed=urlsplit(url);f=(site/parsed.path.lstrip('/')).resolve();assert f.is_relative_to(site.resolve()) and f.is_file(),url;digest=hashlib.sha256(f.read_bytes()).hexdigest();asset_hashes[str(f.relative_to(root))]=digest
 assert 'v='+digest[:8] in parsed.query,(url,digest[:8])
assert snap==snapshot_before and hash_inputs()==before and not blocked
assert snap['generation']['content_sha256'] in final
assert 'Source present; freshness unverified' in final and '来源已提供；时效性未核实' in final
assert '生效日期' not in final and 'Business-activity method v1, published' not in final
record={'scope':'existing build_page/read_workspace/write_page + externalize_css_text + optimize_assets.make_optimizer, single paired static Business rendition only','actual_document_rendered_at':stamp,'raw_artifact':receipt,'input_sha256':before,'snapshot_immutable_and_digest_verified':True,'values_periods_source_identity_count':31,'derived_unknown_clocks':True,'no_clock_absence_as_value_failure':True,'inline_style_bytes':styles,'externalization':'all existing styles below1024; no opt-in JS, no new asset','asset_hashes':asset_hashes,'native_prepublication_sha256':hashlib.sha256(native.encode()).hexdigest(),'final_html_sha256':hashlib.sha256(final.encode()).hexdigest(),'publication_transform_preserves_all_body_text_and_time_nodes':True,'asset_stage_fixed_point':True,'writes':writes,'blocked':blocked,'network':'OSdeny network*','not_claimed':['full financial producer','current observation or source authenticity','PIT','fresh visual/browser/touch','host/runtime/served publication']}
print(json.dumps(record,ensure_ascii=False,indent=2))
