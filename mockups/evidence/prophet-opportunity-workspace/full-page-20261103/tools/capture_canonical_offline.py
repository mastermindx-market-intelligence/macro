"""Invoke the canonical page evidence producer against an offline native public staging directory."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,hashlib,json,sys
cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("--workspace",type=Path,required=True)
cli.add_argument("--site",type=Path,required=True)
cli.add_argument("--output",type=Path,required=True)
a=cli.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
assert not (a.site/"premiumdata").exists()
sys.path.insert(0,str(a.workspace))
from scripts import capture_page_evidence as canonical
class OfflineBrowser:
 def __init__(self,real):self.real=real;self.allowed=None
 def __getattr__(self,name):return getattr(self.real,name)
 def new_context(self,**kwargs):
  kwargs["service_workers"]="block"
  context=self.real.new_context(**kwargs)
  allowed=self.allowed
  context.route("**/*",lambda route:route.continue_() if urlsplit(route.request.url).netloc==allowed and not urlsplit(route.request.url).path.startswith("/premiumdata/") else route.abort())
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
result=canonical.main([
 "--site-dir",str(a.site),"--routes","us_stocks.html,chat.html",
 "--viewports","desktop,mobile","--themes","light,dark","--locales","en,zh",
 "--output-dir",str(a.output/"screenshots"),"--manifest",str(a.output/"manifest.json"),
 "--smells",str(a.output/"smells.json"),"--emit-md",str(a.output/"smells.md"),
 "--settle-ms","1500","--delay-ms","0"
],driver_factory=factory)
(a.output/"offline-driver-provenance.json").write_text(json.dumps({
 "canonical_module_sha256":hashlib.sha256(Path(canonical.__file__).read_bytes()).hexdigest(),
 "wrapper_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 "native_pages":{n:hashlib.sha256((a.site/n).read_bytes()).hexdigest() for n in ("us_stocks.html","chat.html")},
 "scope":"Canonical v2 capture producer; an outer browser-context network policy blocks non-loopback requests, service workers and protected payload paths. Rendering, observed states, screenshots and manifest generation use the canonical producer unchanged. This is not authenticated or production acceptance.",
 "exit":result},indent=2))
raise SystemExit(result)
