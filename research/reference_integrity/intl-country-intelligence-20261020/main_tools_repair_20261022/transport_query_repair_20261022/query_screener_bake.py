#!/usr/bin/env python3
"""Owner integration: canonical Screener HTML bake with no data acquisition."""
import argparse,difflib,hashlib,json,os,pathlib,re,subprocess,sys,datetime
R=pathlib.Path(__file__).resolve().parents[5]
Q=pathlib.Path(__file__).resolve().parent
SOURCE="df1aa0c587bd1fef7a6b20fb69ca2e22afd423fd"
def sha(b): return hashlib.sha256(b).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
p=argparse.ArgumentParser();p.add_argument("--apply",action="store_true");a=p.parse_args()
os.chdir(R);sys.path.insert(0,str(R))
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()==SOURCE
from scripts.build_research_screener import bake_html
from lib.pages import _site_root,write_page
assert _site_root()==(R/"site").resolve()
page=R/"site/research_screener.html";payloadpath=R/"site/research_screener.json"
payloadbytes=payloadpath.read_bytes();oldbytes=page.read_bytes();old=oldbytes.decode("utf-8")
assets=["shared_shell_bridge.js","shared_shell.css","data_base.js","theme.css","research_screener.css"]
assetbytes={name:(R/"site"/name).read_bytes() for name in assets}
for name in ("shared_shell_bridge.js","shared_shell.css","theme.css","research_screener.css"):
 assert assetbytes[name]==(R/"templates"/name).read_bytes(),name+" template/site mismatch"
banner=re.compile(r"[ \t]*<script[^>]*\bdata-whb\b[^>]*></script>\n?")
banners=banner.findall(old);assert len(banners)<=1
baked=bake_html(R,json.loads(payloadbytes));assert not banner.findall(baked)
for name in ("shared_shell_bridge.js","shared_shell.css","theme.css","research_screener.css"):
 token=name+"?v="+sha(assetbytes[name])[:8]
 assert token in baked,(name,token)
rendered=baked
if banners:
 assert "</body>" in baked
 rendered=baked.replace("</body>","".join(banners)+"</body>",1)
assert banner.sub("",rendered)==baked
assert banner.findall(rendered)==banners
assert payloadpath.read_bytes()==payloadbytes
assert all((R/"site"/n).read_bytes()==b for n,b in assetbytes.items())
diff="".join(difflib.unified_diff(old.splitlines(True),rendered.splitlines(True),fromfile="before/site/research_screener.html",tofile="after/site/research_screener.html"))
receipt={"schema":"intl.screener_canonical_bake.v1","observed_at":now(),"source_commit":SOURCE,"working_source_overlay":"paired bridge query API addition, bound by assets below","mode":"apply" if a.apply else "preflight","payload_sha256":sha(payloadbytes),"assets":{n:sha(b) for n,b in assetbytes.items()},"old_html_sha256":sha(oldbytes),"new_html_sha256":sha(rendered.encode()),"banner_count":len(banners),"banner_bytes_preserved":True,"diff_lines":len(diff.splitlines()),"diff_sha256":sha(diff.encode()),"no_acquisition":True,"builder":"scripts.build_research_screener.bake_html","writer":"lib.pages.write_page","product_changed_paths":["site/research_screener.html"] if diff else []}
if a.apply:
 prior=json.loads((Q/"query_screener_preflight.json").read_text())
 for k in ("source_commit","payload_sha256","assets","old_html_sha256","new_html_sha256","banner_count","diff_sha256"):
  assert prior[k]==receipt[k],k+" drift"
 write_page(page,rendered,encoding="utf-8")
 written=page.read_text(encoding="utf-8")
 assert written==rendered
 assert banner.sub("",written)==baked
 assert banner.findall(written)==banners
 assert payloadpath.read_bytes()==payloadbytes
 assert all((R/"site"/n).read_bytes()==b for n,b in assetbytes.items())
 receipt["written_html_sha256"]=sha(page.read_bytes());receipt["completed_at"]=now()
target=Q/("query_screener_apply.json" if a.apply else "query_screener_preflight.json")
target.write_text(json.dumps(receipt,indent=2)+"\n")
(Q/"query_screener_canonical_bake.diff").write_text(diff)
print(json.dumps(receipt,indent=2))
print(diff if len(diff)<9000 else "Diff retained at "+str(Q/"query_screener_canonical_bake.diff"))