"""Capture current Prophet theme and real focus/hover states with the canonical producer."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from bs4 import BeautifulSoup
cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("--workspace",type=Path,required=True)
cli.add_argument("--source-head",required=True)
cli.add_argument("--output",type=Path,required=True)
a=cli.parse_args()
root=a.workspace.resolve()
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==a.source_head
a.output.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(root))
from scripts import capture_page_evidence as canonical
class OfflineBrowser:
 def __init__(self,real):self.real=real;self.allowed=None
 def __getattr__(self,name):return getattr(self.real,name)
 def new_context(self,**kwargs):
  kwargs["service_workers"]="block"
  context=self.real.new_context(**kwargs)
  allowed=self.allowed
  context.route("**/*",lambda route:route.continue_() if urlsplit(route.request.url).netloc==allowed and not urlsplit(route.request.url).path.startswith("/premiumdata/") and not urlsplit(route.request.url).path.endswith(".json") else route.abort())
  return context
class OfflineDriver:
 def __init__(self,real):
  self.real=real;self.browser=OfflineBrowser(real._browser);real._browser=self.browser
 def capture(self,*,url,cell,timeout_s):
  assert urlsplit(url).hostname=="127.0.0.1"
  self.browser.allowed=urlsplit(url).netloc
  return self.real.capture(url=url,cell=cell,timeout_s=timeout_s)
 def close(self):self.real.close()
def factory(**kwargs):return OfflineDriver(canonical.playwright_page_driver(**kwargs))
site=root/"site"
with tempfile.TemporaryDirectory(prefix="public-stage-",dir=a.output.parent) as temp:
 public=Path(temp)
 shutil.copy2(site/"us_stocks.html",public/"us_stocks.html")
 for name in ("assets","fonts"):
  if (site/name).is_dir():
   shutil.copytree(site/name,public/name,ignore=shutil.ignore_patterns("*.json","*.html","*.map"))
 for item in site.iterdir():
  if item.is_file() and item.suffix in {".css",".js",".svg",".woff",".woff2",".ico",".png",".webp"}:
   shutil.copy2(item,public/item.name)
 assert not (public/"premiumdata").exists()
 assert (public/"us_stocks.html").read_bytes()==(site/"us_stocks.html").read_bytes()
 result=canonical.main([
  "--site-dir",str(public),"--routes","us_stocks.html",
  "--viewports","desktop,mobile","--themes","light,dark","--locales","en,zh",
  "--output-dir",str(a.output/"screenshots"),"--manifest",str(a.output/"manifest.json"),
  "--smells",str(a.output/"smells.json"),"--emit-md",str(a.output/"smells.md"),
  "--settle-ms","1500","--delay-ms","0",
  "--force-state","hover:hover(a.terminal-link)","--force-state","focus:focus(a.terminal-link)"
 ],driver_factory=factory)
receipt={
 "source_head":a.source_head,
 "canonical_module_sha256":hashlib.sha256(Path(canonical.__file__).read_bytes()).hexdigest(),
 "wrapper_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 "page_sha256":hashlib.sha256((site/"us_stocks.html").read_bytes()).hexdigest(),
 "source_files":{rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in (
  "site/theme.js","templates/_prophet_opportunity.css.j2","templates/_prophet_opportunity_card.html.j2",
  "templates/dashboard.html.j2","templates/theme.css","site/us_stocks.html")},
 "scope":"Canonical v2 producer unchanged; real browser hover/focus on a.terminal-link, no navigation. Public staging bytes match the verified native-generated HTML; source_head identifies the clean build input. Only loopback public assets allowed. Anonymous offline lab, not authenticated or production acceptance.",
 "exit":result}
receipt["referenced_stylesheets"]={}
for node in BeautifulSoup((site/"us_stocks.html").read_bytes(),"html.parser").select('link[rel="stylesheet"][href]'):
 ref=urlsplit(node["href"])
 if ref.scheme or ref.netloc:continue
 asset=site/ref.path.lstrip("/")
 assert asset.is_file(),str(asset)
 receipt["referenced_stylesheets"][str(asset.relative_to(root))]={"sha256":hashlib.sha256(asset.read_bytes()).hexdigest(),"bytes":asset.stat().st_size}
(a.output/"capture-provenance.json").write_text(json.dumps(receipt,indent=2)+"\n")
print("CAPTURE_EXIT",result,flush=True)
raise SystemExit(result)
