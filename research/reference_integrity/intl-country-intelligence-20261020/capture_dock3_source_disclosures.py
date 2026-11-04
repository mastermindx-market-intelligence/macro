"""Capture actual source disclosures of the frozen full-input candidate."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util, json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]
RIG=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("original_reference_capture",RIG/"capture_complete_reference.py")
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module.ASSETS=(RIG/"proposed_dock3_repair").resolve()
module.SHOTS=ROOT/"mockups/refs/reference_integrity/intl-country-intelligence-20261020/after_dock3_sources"
assert not module.SHOTS.exists()
module.SHOTS.mkdir()
build=json.loads((RIG/"repair_dock3_build_receipt.json").read_text())
assert sha256((module.ASSETS/"intl.html").read_bytes()).hexdigest()==build["html_sha256"]
checks=[]; screenshots=[]
with sync_playwright() as runtime:
    browser=runtime.chromium.launch(channel="chrome",headless=True)
    for viewport,width,height,locale,theme in [
        ("narrow",320,900,"en","dark"),("narrow",320,900,"zh","light")]:
        context=module.context_for(browser,width,height,locale,theme)
        page=context.new_page(); errors=[]
        page.on("pageerror",lambda error: errors.append(str(error)))
        countries=("JP","KR","TW","IN","AU","GB","EZ") if viewport!="narrow" else ("JP","EZ")
        for cc in countries:
            page.goto("http://intl.test/intl.html#imc-country-"+cc,wait_until="domcontentloaded")
            module.settle(page,locale,theme)
            country=page.locator("#imc-country-"+cc)
            if country.get_attribute("open") is None:
                country.locator(":scope > summary").click()
            evidence=country.locator(".imc-evidence")
            evidence.locator(":scope > summary").click()
            evidence.locator(":scope > summary").scroll_into_view_if_needed()
            name=cc+"-"+viewport+"-"+locale+"-"+theme
            state=page.evaluate("() => ({overflow:document.documentElement.scrollWidth>innerWidth,lang:document.documentElement.dataset.lang,theme:document.documentElement.dataset.theme})")
            checks.append({"id":"source-disclosure-"+name,"passed":evidence.get_attribute("open") is not None and not state["overflow"] and state["lang"]==locale and state["theme"]==theme,"actual":state})
            screenshots.append(module.shot(page,"sources-"+name+".png"))
            inputs=country.locator(".imc-macro-inputs[data-metric='gdp']")
            if inputs.count():
                inputs.locator(":scope > summary").click()
                inputs.scroll_into_view_if_needed()
                checks.append({"id":"GDP-inputs-"+name,"passed":inputs.get_attribute("open") is not None and inputs.locator("tbody tr").count()==5})
                screenshots.append(module.shot(page,"gdp-"+name+".png"))
            if cc=="JP":
                raw=country.locator(".imc-equity-rows")
                raw.locator(":scope > summary").click()
                raw.locator(":scope > summary").scroll_into_view_if_needed()
                checks.append({"id":"equity-inputs-"+name,"passed":raw.get_attribute("open") is not None and raw.locator("tbody tr").count()==252})
                screenshots.append(module.shot(page,"equity-rows-"+name+".png"))
        checks.append({"id":"no-page-exceptions-"+viewport+"-"+locale+"-"+theme,"passed":not errors,"actual":errors})
        context.close()
    browser.close()
result={"recorded_at":datetime.now(timezone.utc).isoformat(),"source_commit":build["source_commit"],"html_sha256":build["html_sha256"],
        "checks":checks,"screenshots":screenshots,"passed":sum(c["passed"] for c in checks),"failed":sum(not c["passed"] for c in checks),
        "limits":["Actual isolated anonymous browser; retained production inputs without reacquisition; external requests blocked."]}
target=RIG/"dock3_source_disclosure_browser.json"; assert not target.exists()
target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({k:v for k,v in result.items() if k not in ["checks","screenshots"]}))
print(json.dumps({"failed_checks":[c for c in checks if not c["passed"]]}))
raise SystemExit(bool(result["failed"]))
