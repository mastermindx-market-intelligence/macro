"""Bound the earlier assistant failure to the actual dialog focus transition."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util, json
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[3]
RIG = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reference_capture", RIG / "capture_complete_reference.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
capture.ASSETS = (RIG / "proposed_ui_repair").resolve()
output = RIG / "repair_ui" / "assistant_focus_diagnosis.json"
assert not output.exists()
checks = []
with sync_playwright() as runtime:
    browser = runtime.chromium.launch(channel="chrome", headless=True)
    for name, width, height in [("desktop",1440,900),("mobile",390,844),("narrow",320,720)]:
        for locale in ["en","zh"]:
            for theme in ["light","dark"]:
                context = capture.context_for(browser,width,height,locale,theme)
                page = context.new_page()
                errors = []
                page.on("pageerror",lambda error:errors.append(str(error)))
                page.goto("http://intl.test/intl.html",wait_until="domcontentloaded")
                capture.settle(page,locale,theme)
                launcher = page.locator("#mmb-boot, #mmb-launch").filter(visible=True).first
                launcher.focus()
                page.keyboard.press("Enter")
                page.locator("#mmb-panel.open").wait_for(state="visible",timeout=10000)
                at_visible = page.evaluate("document.activeElement.id")
                page.wait_for_function("document.querySelector('#mmb-panel.open')?.contains(document.activeElement)",timeout=4000)
                focused_inside = page.evaluate("({id:document.activeElement.id,tag:document.activeElement.tagName})")
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                actual = page.evaluate("({closed:!document.querySelector('#mmb-panel.open'),focus:document.activeElement.id})")
                checks.append({"id":name+"-"+locale+"-"+theme,"passed":actual["closed"] and actual["focus"]=="mmb-launch" and not errors,
                    "focus_at_panel_visible":at_visible,"settled_focus":focused_inside,"after_escape":actual,"errors":errors})
                context.close()
    browser.close()
receipt = {"recorded_at":datetime.now(timezone.utc).isoformat(),
    "html_sha256":sha256((capture.ASSETS / "intl.html").read_bytes()).hexdigest(),
    "prior_receipt":"research/reference_integrity/intl-country-intelligence-20261020/repair_ui/review_counterexamples.json",
    "sequence":"Keyboard activate launcher; wait for open panel and actual focus inside panel; Escape; inspect close and returned focus.",
    "scope":"Anonymous isolated assets. No prompt, account mutation or external request.",
    "checks":checks,"passed":sum(c["passed"] for c in checks),"failed":sum(not c["passed"] for c in checks)}
output.write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt))
raise SystemExit(bool(receipt["failed"]))
