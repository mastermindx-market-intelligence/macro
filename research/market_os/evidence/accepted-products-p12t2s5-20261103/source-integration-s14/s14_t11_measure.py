from pathlib import Path
import sys,types,subprocess,json,hashlib,difflib,re
from html.parser import HTMLParser
root=Path.cwd();sys.path.insert(0,str(root))
from scripts import build_macro_suite_pages as B
from lib import macro_suite_view as V
from engine.market_os.macro_workspaces import contract
p=Path('/Volumes/Mastermind/evidence/accepted-products-p12t2s5-20261103');out=p/'s14-t11-measured';out.mkdir(exist_ok=True)
t=types.ModuleType('_s14_t11');t.__file__=str(root/'tests/test_macro_rates_curves_route.py');exec(compile(Path(t.__file__).read_bytes(),t.__file__,'exec'),t.__dict__)
data=t.T11_DATA;binding=json.loads((data/'source-binding.json').read_text());assert all(hashlib.sha256((data/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in binding['files'])
page=next(x for x in B.SUITE_PAGES if x.workspace_id=='business_activity');gold=(t.T11_PAGES/page.output).read_text();stamp=t._page_built_stamp(gold);snapshot,receipt=B.read_workspace(data,page);contract.validate(snapshot)
B.build_page(root,page,data_root=data,out_dir=out,env=B._environment(root),page_built_at=stamp)
new=(out/page.output).read_text();normalized=t._t11_collapse_t21_labels(t._t11_collapse_main_prior_label(t._t11_collapse_prior_date(new)))
class Fragments(HTMLParser):
 def __init__(self,s):
  super().__init__(convert_charrefs=False);self.s=s;self.lines=s.splitlines(keepends=True);self.offsets=[0]
  for l in self.lines:self.offsets.append(self.offsets[-1]+len(l))
  self.stack=[];self.parts=[];self.feed(s)
 def position_index(self):
  l,c=self.getpos();return self.offsets[l-1]+c
 def handle_starttag(self,tag,attrs):
  if tag in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:return
  a=dict(attrs);cl=a.get('class','').split();kind=next((k for k in ['mq-context','mq-headline','mq-metric','mq-source'] if k in cl),None)
  self.stack.append((tag,self.position_index(),kind))
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:
    _,start,kind=self.stack[i];self.stack=self.stack[:i]
    if kind:self.parts.append((start,kind,self.s[start:self.position_index()+len(tag)+3]))
    return
 def handle_startendtag(self,tag,attrs):pass
oldparts=sorted(Fragments(gold).parts);newparts=sorted(Fragments(normalized).parts);assert [k for _,k,_ in oldparts]==[k for _,k,_ in newparts]
pairs=[];report=[]
for i,((_,kind,old),(_,_,now)) in enumerate(zip(oldparts,newparts)):
 if old!=now:
  assert old in gold
  pairs.append([now,old]);report.append({'fragment_index':i,'kind':kind,'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':hashlib.sha256(now.encode()).hexdigest(),'old_bytes':len(old.encode()),'new_bytes':len(now.encode())})
collapsed=normalized
for now,old in pairs:collapsed=collapsed.replace(now,old)
a=t._region(gold,page.output);b=t._region(collapsed,page.output)
(p/'s14-t11-unmapped.diff').write_text(''.join(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True),fromfile='frozen',tofile='after_reviewed_fragment_mapping')))
record={'why':'P12.T2.S14: measured reviewed Business-only S13 period/clock/presence semantics at7b7dad38, fresh paired source closure f43b32da. Exact complete context/headline/identified metric/source fragments from unchanged T11 publication generation a58cf3; raw snapshots/manifest/goldens/reader/comparator unchanged. Existing prior/T21/S6 collapses applied first. Full exact fragment includes numeric values/periods/source provenance so an extra character cannot match; no generic date/null/freshness strip or skip. Source input/schema/hash and one-character/provenance controls remain required.','pairs':pairs}
(p/'s14-t11-proposed-collapse.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');(p/'s14-t11-measure-report.json').write_text(json.dumps({'receipt':receipt,'input_binding_sha256':hashlib.sha256((data/'source-binding.json').read_bytes()).hexdigest(),'fragment_count':len(pairs),'fragments':report,'unmapped_equal':a==b,'golden_sha256':hashlib.sha256(gold.encode()).hexdigest(),'current_sha256':hashlib.sha256(new.encode()).hexdigest()},indent=2)+'\n')
print('pairs',len(pairs),'unmapped_equal',a==b,'remainingdiff lines',len((p/'s14-t11-unmapped.diff').read_text().splitlines()))
