from pathlib import Path
import tempfile,subprocess,hashlib,json,re,posixpath
from urllib.parse import urlsplit
from scripts import build_free_content as B
root=Path.cwd()
with tempfile.TemporaryDirectory(prefix='mmx-render-') as d:
 site=Path(d)/'site';site.mkdir()
 live=Path(d)/'committed-live';live.mkdir()
 refs=set()
 for content in (root/'content/seo').rglob('*.md'):
  refs.update(re.findall(r'/[A-Za-z0-9_./-]+\.html',content.read_text()))
 for ref in sorted(refs):
  data=subprocess.run(['git','show','HEAD:site'+ref],capture_output=True)
  if data.returncode==0:
   target=live/ref.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data.stdout)
 B._LIVE_SITE_DIR=live
 B.render_all(site)
 for p in list(site.rglob('*.html')):
  for src in re.findall(r'(?:href|src)=["\']([^"\']+)',p.read_text()):
   u=urlsplit(src)
   if u.scheme or u.netloc or not u.path.endswith(('.css','.js')):continue
   rel=posixpath.normpath(posixpath.join(p.parent.relative_to(site).as_posix(),u.path))
   if rel.startswith('../'):continue
   target=site/rel
   if target.exists():continue
   data=subprocess.run(['git','show','HEAD:site/'+rel],capture_output=True)
   if data.returncode==0:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data.stdout)
 B._normalize_like_render_lane(site)
 rows=[]
 for p in sorted(site.rglob('*')):
  if not p.is_file() or p.suffix not in ('.html','.xml'):continue
  rel=p.relative_to(site).as_posix()
  if B._is_hand_authored(Path(rel)):continue
  old=subprocess.check_output(['git','show','HEAD:site/'+rel]);new=p.read_bytes()
  if p.suffix=='.html':old=B._comparable(old.decode()).encode();new=B._comparable(new.decode()).encode()
  rows.append({'path':rel,'match':old==new,'render_sha256':hashlib.sha256(new).hexdigest()})
 report={'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'compared':len(rows),'mismatches':[x for x in rows if not x['match']],'rows':rows,'method':'Existing renderer and normalization; exact committed asset bytes; canonical wh-banner normalization; isolated output only'}
 out=root/'research/agentic_media/public_intelligence_20261011/current_event_phase/main_repair_20261014_1012/render_check.json';out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'}));assert not report['mismatches']
