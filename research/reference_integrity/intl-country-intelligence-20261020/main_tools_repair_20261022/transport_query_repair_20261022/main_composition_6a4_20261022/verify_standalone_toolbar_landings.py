"""Check actual fragment landings and unchanged country evidence after toolbar repair."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import argparse,importlib.util,json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
ROOT=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018"); RIG=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument("--label",required=True);args=parser.parse_args()
build=json.loads((RIG/("repair_"+args.label+"_build_receipt.json")).read_text())
assert build["exit_code"]==0 and not build["source_overlays"]
assets=(RIG/("proposed_"+args.label+"_repair")).resolve()
html=assets/"intl.html";assert sha256(html.read_bytes()).hexdigest()==build["html_sha256"]
old=BeautifulSoup((Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020")/"proposed_final_repair/intl.html").read_text(),"html.parser")
new=BeautifulSoup(html.read_text(),"html.parser")
equivalence=[]
for cc in ["JP","KR","TW","IN","AU","GB","EZ"]:
    selector="#imc-country-"+cc
    a=str(old.select_one(selector));b=str(new.select_one(selector))
    equivalence.append({"cc":cc,"identical_country_html":a==b,"prior_sha256":sha256(a.encode()).hexdigest(),"new_sha256":sha256(b.encode()).hexdigest()})
spec=importlib.util.spec_from_file_location("original_reference_capture",Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020")/"capture_complete_reference.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.ASSETS=assets;module.SHOTS=RIG/"standalone_toolbar_images"
assert not module.SHOTS.exists();module.SHOTS.mkdir()
checks=[];screens=[]
legacy=["intl-growth-inflation","intl-central-banks","intl-credit-bonds","lb-board"]
targets=legacy+["imc-country-JP","imc-world","imc-countries","imc-connections","intl-analysis-tools"]
with sync_playwright() as runtime:
    browser=runtime.chromium.launch(channel="chrome",headless=True)
    for viewport,width,height,locales,themes in [("desktop",1440,900,["en"],["light"]),("narrow",320,720,["zh"],["dark"])]:
        for locale in locales:
            for theme in themes:
                context=module.context_for(browser,width,height,locale,theme)
                page=context.new_page();errors=[]
                page.on("pageerror",lambda error:errors.append(str(error)))
                for target in targets:
                    page.goto("http://intl.test/intl.html#"+target,wait_until="domcontentloaded")
                    module.settle(page,locale,theme)
                    page.wait_for_timeout(250)
                    state=page.evaluate("""id => {
                      const target=document.getElementById(id),bar=document.querySelector('.imc-toolbar');
                      const r=target?.getBoundingClientRect(),b=bar?.getBoundingClientRect();
                      const launch=document.querySelector('#mmb-launch:not(.mmb-hide),#mmb-boot:not(.mmb-hide)');
                      const l=launch?.getBoundingClientRect(),slot=document.querySelector('.imc-assistant-slot')?.getBoundingClientRect();
                      return {id,exists:!!target,top:r?.top,height:r?.height,toolbarTop:b?.top,toolbarBottom:b?.bottom,
                        toolbarStuck:bar?.classList.contains('is-stuck'),viewportHeight:innerHeight,
                        clear:!!r && r.height>0 && r.top>=Math.max(0,b?.bottom||0)+8 && r.top<innerHeight-30,
                        overflow:document.documentElement.scrollWidth>innerWidth,
                        toolsOpen:document.getElementById('intl-analysis-tools')?.open,
                        assistantInSlot:!!l && !!slot && l.left>=slot.left-1 && l.right<=slot.right+1 && l.top>=slot.top-1 && l.bottom<=slot.bottom+1};
                    }""",target)
                    name=target+"-"+viewport+"-"+locale+"-"+theme
                    checks.append({"id":"landing-"+name,"passed":state["clear"] and not state["overflow"] and state["assistantInSlot"],"actual":state})
                    if (target in legacy and ((viewport=="desktop" and locale=="en" and theme=="light") or (viewport=="mobile" and locale=="zh" and theme=="dark") or (viewport=="narrow" and locale=="en"))) or target=="imc-country-JP":
                        screens.append(module.shot(page,"anchor-"+name+".png"))
                page.goto("http://intl.test/intl.html",wait_until="domcontentloaded");module.settle(page,locale,theme)
                page.locator(".imc-tools-link").click();page.wait_for_timeout(500)
                click=page.locator("#intl-analysis-tools").evaluate("""e => ({top:e.getBoundingClientRect().top,bar:document.querySelector('.imc-toolbar').getBoundingClientRect().bottom,open:e.open})""")
                checks.append({"id":"click-tools-clear-"+viewport+"-"+locale+"-"+theme,"passed":click["open"] and click["top"]>=click["bar"]+8 and click["top"]<height,"actual":click})
                checks.append({"id":"no-page-exceptions-"+viewport+"-"+locale+"-"+theme,"passed":not errors,"actual":errors})
                context.close()
    browser.close()
result={"recorded_at":datetime.now(timezone.utc).isoformat(),"driver_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),"matrix":"representative desktop English light and 320px Chinese dark","source_commit":build["source_commit"],"html_sha256":build["html_sha256"],
        "country_evidence_equivalence":equivalence,"checks":checks,"screenshots":screens,
        "passed":sum(c["passed"] for c in checks),"failed":sum(not c["passed"] for c in checks),
        "limits":["Direct fragment loads and native navigation clicks; no manual scroll correction used in this probe.","Actual isolated anonymous browser; no source reacquisition or authenticated session."]}
out=RIG/("toolbar_"+args.label+"_landings.json");assert not out.exists();out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k not in ["checks","screenshots"]}))
print(json.dumps({"failed_checks":[c for c in checks if not c["passed"]]}))
raise SystemExit(bool(result["failed"]) or not all(e["identical_country_html"] for e in equivalence))