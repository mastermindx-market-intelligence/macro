"""Actual Chrome proof for fragment-free Back, chart legend and translated accessible names."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, sys
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from engine import i18n
from research.paper_international_wave1_wave2.preview_country_cockpit import DOCUMENT
from research.paper_international_wave1_wave2.capture_country_cockpit import IsolatedBrowser
OUT=Path(__file__).resolve().parent
phase=sys.argv[1]
assert phase in ("before","after")
env=Environment(loader=FileSystemLoader(ROOT/"templates"),autoescape=False)
env.globals.update(t=i18n.t,tr=i18n.tr,td=i18n.td)
assessment=json.loads((OUT/"preview/assessment.json").read_text())
html=env.from_string(DOCUMENT).render(intl_analysis=assessment)
(OUT/("history_legend_"+phase+".html")).write_text(html)
receipt={"phase":phase,"started_at":datetime.now(timezone.utc).isoformat(),"html_sha256":sha256(html.encode()).hexdigest(),"checks":[],"page_errors":[]}
def check(name,actual,expected):
 receipt["checks"].append({"name":name,"actual":actual,"expected":expected,"passed":actual==expected})
def state(page):
 page.evaluate("() => new Promise(requestAnimationFrame)")
 return page.evaluate("""() => ({hash:location.hash,open:[...document.querySelectorAll('.imc-country[open]')].map(x=>x.id),rail:[...document.querySelectorAll('.imc-country-rail [aria-current="location"]')].map(x=>x.dataset.imcCountry)})""")
with sync_playwright() as p:
 browser=p.chromium.launch(channel="chrome",headless=True)
 context=IsolatedBrowser(browser,html).new_context(viewport={"width":1440,"height":900})
 page=context.new_page()
 page.on("pageerror",lambda e:receipt["page_errors"].append(str(e)))
 page.goto("http://intl.test/intl.html")
 initial=state(page)
 check("initial_fragment_free_selection",initial,{"hash":"","open":["imc-country-KR"],"rail":["KR"]})
 page.locator("#imc-country-JP > summary").click()
 check("select_JP_from_initial",state(page),{"hash":"#imc-country-JP","open":["imc-country-JP"],"rail":["JP"]})
 page.go_back()
 check("back_restores_initial_without_fragment",state(page),initial)
 page.go_forward()
 check("forward_restores_JP",state(page),{"hash":"#imc-country-JP","open":["imc-country-JP"],"rail":["JP"]})
 page.go_back()
 page.reload()
 check("fragment_free_reload_matches_back",state(page),initial)
 for lang in ("en","zh"):
  page.evaluate("""lang => {document.documentElement.dataset.lang=lang;document.documentElement.lang=lang;}""",lang)
  page.evaluate("document.fonts.ready")
  figure=page.locator("#imc-country-KR .imc-growth-chart")
  legend=figure.locator("figcaption").evaluate("""el => [...el.querySelectorAll('span')].map(e=>({text:e.textContent,content:getComputedStyle(e,'::before').content,style:getComputedStyle(e,'::before').borderTopStyle,width:getComputedStyle(e,'::before').width,direct:e.parentElement===el,visible:getComputedStyle(e).display!=='none'}))""")
  painted=[x for x in legend if x["content"] not in ("none","normal") and x["visible"]]
  check("exact_two_legend_swatches_"+lang,len(painted),2)
  check("solid_history_dashed_projection_"+lang,[x["style"] for x in painted],["solid","dashed"])
  snapshot=figure.locator("svg").aria_snapshot()
  receipt.setdefault("accessible_charts",{})[lang]=snapshot
  description=next(c for c in assessment["countries"] if c["cc"]=="KR")["outlook"]["chart"]["description_"+lang]
  check("localized_accessible_chart_"+lang,description in snapshot,True)
  receipt.setdefault("legends",{})[lang]=legend
  figure.screenshot(path=str(OUT/("chart_legend_"+phase+"_"+lang+".png")))
 context.close()
 browser.close()
check("no_page_errors",receipt["page_errors"],[])
receipt["finished_at"]=datetime.now(timezone.utc).isoformat()
receipt["passed"]=sum(x["passed"] for x in receipt["checks"])
receipt["total"]=len(receipt["checks"])
(OUT/("history_legend_"+phase+".json")).write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"phase":phase,"passed":receipt["passed"],"total":receipt["total"],"failed":[x["name"] for x in receipt["checks"] if not x["passed"]],"page_errors":receipt["page_errors"]}))
if phase=="after": assert receipt["passed"]==receipt["total"]
