"""Bounded visual controls. These outputs are fixtures, never admitted source data or served pages."""
from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import json, sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from engine import i18n
from lib.intl_country_assessment import build_country_assessments
from lib.intl_policy_evidence import reconcile_bis_monthly_policy
from research.paper_international_wave1_wave2.preview_country_cockpit import DOCUMENT
from research.paper_international_wave1_wave2.capture_country_cockpit import IsolatedBrowser
OUT=Path(__file__).resolve().parent/"degraded_states"
OUT.mkdir(exist_ok=True)
base=json.loads((ROOT/"config/intl_country_baseline.json").read_text())
preview=OUT.parent/"preview"
market=json.loads((preview/"market_replay.json").read_text())
currency=json.loads((preview/"currency_replay.json").read_text())
commentary=json.loads((ROOT/"config/intl_country_commentary.json").read_text())["countries"]
def model(cc,today,official=None):
 return build_country_assessments({"records":[{"cc":cc,"equity":market[cc],"currency_observation":currency[cc]}]},today=today,
  official=official if official is not None else base["official"],forecasts=base["forecasts"],
  forecast_archive=base["forecast_archive"],policy_decisions=base["policy_decisions"],
  policy_reviews=base["policy_reviews"],commentary=commentary)
official=deepcopy(base["official"])
original=official["GB"]["policy"]
synthetic=deepcopy(original)
synthetic.update(value=4.0,retrieved_at="2026-10-20T10:00:00+00:00",
 first_observed_at="2026-10-20T10:01:00+00:00",source_sha256="b"*64)
synthetic["daily_reference"].update(value=4.0,source_sha256="b"*64)
official["GB"]["policy"]=reconcile_bis_monthly_policy(original,synthetic,"GB",today=date(2026,10,20))
assert official["GB"]["policy"]["comparison_qualification"]=="retained_conflict"
(OUT/"monthly_collision_fixture.json").write_text(json.dumps({
 "kind":"SYNTHETIC_VERIFICATION_FIXTURE_NOT_SOURCE_EVIDENCE",
 "purpose":"Exercise disagreement display; the 4.0 value and b-digest are deliberately fabricated test inputs.",
 "original_retained":original,"synthetic_incoming":synthetic,"reconciled":official["GB"]["policy"]},indent=2)+"\n")
cases=[
 ("partial_jp",model("JP",date(2026,10,20)),"PARTIAL_COVERAGE_CONTROL",[("en","light",390),("zh","dark",320)],None),
 ("dated_kr",model("KR",date(2026,10,25)),"TIME_SHIFTED_AGEING_CONTROL",[("en","light",320)],".imc-market-read"),
 ("unavailable_kr",model("KR",date(2026,11,3)),"TIME_SHIFTED_AGEING_CONTROL",[("zh","dark",320)],".imc-market-read"),
 ("monthly_review_gb",model("GB",date(2026,10,20),official),"SYNTHETIC_MONTHLY_COLLISION_CONTROL",[("en","light",390),("zh","dark",390)],".imc-policy-decision"),
]
env=Environment(loader=FileSystemLoader(ROOT/"templates"),autoescape=False)
env.globals.update(t=i18n.t,tr=i18n.tr,td=i18n.td)
receipt={"started_at":datetime.now(timezone.utc).isoformat(),"scope":"Actual Chrome renders of explicitly identified controls; no canonical input or receipt changed; no current-market claim.","states":[],"page_errors":[]}
with sync_playwright() as p:
 browser=p.chromium.launch(channel="chrome",headless=True)
 for name,a,kind,variants,region in cases:
  html=env.from_string(DOCUMENT).render(intl_analysis=a)
  (OUT/(name+".html")).write_text(html)
  (OUT/(name+"_assessment.json")).write_text(json.dumps(a,ensure_ascii=False,indent=2)+"\n")
  for lang,theme,width in variants:
   context=IsolatedBrowser(browser,html).new_context(viewport={"width":width,"height":844})
   page=context.new_page()
   page.on("pageerror",lambda e:receipt["page_errors"].append(str(e)))
   page.goto("http://intl.test/intl.html")
   page.evaluate("""s=>{document.documentElement.dataset.lang=s.lang;document.documentElement.lang=s.lang;document.documentElement.dataset.theme=s.theme}""",{"lang":lang,"theme":theme})
   page.evaluate("document.fonts.ready")
   assert page.evaluate("document.documentElement.scrollWidth") <= width
   text=page.locator(".imc-country[open]").inner_text()
   checks={"no_horizontal_overflow":True}
   if name=="partial_jp":
    checks["no_missing_country_links"]=page.locator('.imc-connections a[data-imc-country]:not([data-imc-country="JP"])').count()==0
   elif name=="dated_kr":
    checks["dated_evidence_labeled"]=page.locator(".imc-fx-read").get_attribute("data-fx-quality")=="dated" and "Dated" in text and "+10.91%" in text
   elif name=="unavailable_kr":
    fx=page.locator(".imc-fx-read").inner_text()
    checks["expired_value_withheld"]=page.locator(".imc-fx-read").get_attribute("data-fx-quality")=="missing" and "+10.91%" not in fx and "暂无可用观测" in fx
   else:
    checks["monthly_review_visible"]=("Monthly cross-check needs review" if lang=="en" else "月度交叉核验待复核") in text
    checks["national_decision_preserved"]=a["countries"][0]["policy_decision"]["state"]=="verified" and "3.75%" in text
   filename=f"{name}_{lang}_{theme}_{width}.png"
   if region: page.locator(region).screenshot(path=str(OUT/filename))
   else: page.screenshot(path=str(OUT/filename),full_page=True)
   receipt["states"].append({"name":name,"kind":kind,"locale":lang,"theme":theme,"width":width,"evaluated_at":a["as_of"] if "as_of" in a else None,"file":filename,"sha256":sha256((OUT/filename).read_bytes()).hexdigest(),"html_sha256":sha256(html.encode()).hexdigest(),"checks":checks,"passed":all(checks.values())})
   context.close()
 browser.close()
receipt["finished_at"]=datetime.now(timezone.utc).isoformat()
receipt["passed"]=all(s["passed"] for s in receipt["states"]) and not receipt["page_errors"]
(OUT/"manifest.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"states":len(receipt["states"]),"passed":receipt["passed"],"page_errors":receipt["page_errors"]}))
assert receipt["passed"]
