"""Re-run the original reference capture and the specific review counterexamples."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import argparse, importlib.util, json, shutil
ROOT = Path(__file__).resolve().parents[3]
RIG = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, choices=("ui", "final"))
    args = parser.parse_args()
    target = RIG / ("repair_" + args.label)
    assert not target.exists()
    target.mkdir()
    spec = importlib.util.spec_from_file_location("original_reference_capture", RIG / "capture_complete_reference.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = target
    module.ASSETS = (RIG / ("proposed_" + args.label + "_repair")).resolve()
    module.SHOTS = ROOT / ("mockups/refs/reference_integrity/intl-country-intelligence-20261020/after_" + args.label + "_repair")
    build_path = RIG / ("repair_" + args.label + "_build_receipt.json")
    build = json.loads(build_path.read_text())
    shutil.copyfile(build_path, target / "complete_build_receipt.json")
    canonical_exit = int(module.main())
    checks = []
    screenshots = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chrome", headless=True)
        for viewport, width, height in [("desktop", 1440, 900), ("mobile", 390, 844), ("narrow", 320, 720)]:
            for locale in ["en", "zh"]:
                for theme in ["light", "dark"]:
                    context = module.context_for(browser, width, height, locale, theme)
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    response = page.goto("http://intl.test/intl.html", wait_until="domcontentloaded")
                    module.settle(page, locale, theme)
                    state = page.evaluate("""() => ({
                      navigation: [...document.querySelectorAll('.imc-nav a')].map(a => {
                        const r = a.getBoundingClientRect();
                        return {text:a.innerText, left:r.left, right:r.right, width:r.width,
                          visible:r.width>0 && r.left>=0 && r.right<=innerWidth};
                      }),
                      equityLabels:[...document.querySelectorAll('.imc-market-state small')].map(e => e.innerText),
                      overflow:document.documentElement.scrollWidth>innerWidth
                    })""")
                    name = viewport + "-" + locale + "-" + theme
                    checks.append({"id":"visible-section-navigation-" + name,
                        "passed":len(state["navigation"])==4 and all(a["visible"] for a in state["navigation"]) and not state["overflow"], "actual":state})
                    label = "Equity trend" if locale == "en" else "股市趋势"
                    checks.append({"id":"equity-scope-" + name,
                        "passed":len(state["equityLabels"])==7 and all(x==label for x in state["equityLabels"]), "actual":state["equityLabels"]})
                    page.locator(".imc-tools-link").click()
                    page.wait_for_timeout(150)
                    opened = page.locator("#intl-analysis-tools").get_attribute("open") is not None
                    checks.append({"id":"visible-tools-entry-opens-" + name,"passed":opened})
                    page.goto("http://intl.test/intl.html", wait_until="domcontentloaded")
                    module.settle(page, locale, theme)
                    page.locator("#imc-country-KR .imc-market-read").scroll_into_view_if_needed()
                    launcher = page.locator("#mmb-boot, #mmb-launch").filter(visible=True).first
                    launcher.wait_for(state="visible", timeout=8000)
                    launch_state = launcher.evaluate("""e => {
                      const r=e.getBoundingClientRect(), s=getComputedStyle(e);
                      return {id:e.id, position:s.position, label:e.getAttribute('aria-label'),
                        inViewport:r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight};
                    }""")
                    screenshots.append(module.shot(page, "reading-" + name + ".png", {"actual":launch_state}))
                    checks.append({"id":"persistent-assistant-" + name,
                        "passed":launch_state["position"]=="fixed" and launch_state["inViewport"] and bool(launch_state["label"]),"actual":launch_state})
                    launcher.focus()
                    page.keyboard.press("Enter")
                    page.locator("#mmb-panel.open").wait_for(state="visible", timeout=10000)
                    page.wait_for_function("document.querySelector('#mmb-panel.open')?.contains(document.activeElement)", timeout=4000)
                    screenshots.append(module.shot(page, "assistant-open-" + name + ".png"))
                    checks.append({"id":"existing-assistant-opens-" + name,
                        "passed":page.locator("#mmb-panel.open").is_visible()})
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                    closed = page.locator("#mmb-panel.open").count()==0
                    focused = page.evaluate("document.activeElement && document.activeElement.id")
                    checks.append({"id":"assistant-close-and-focus-" + name,
                        "passed":closed and focused=="mmb-launch","actual":{"closed":closed,"focus":focused}})
                    checks.append({"id":"no-page-exceptions-" + name,"passed":not errors,"errors":errors})
                    context.close()
        browser.close()
    receipt = {"schema":"intl.rig_review_repair_browser.v1",
        "recorded_at":datetime.now(timezone.utc).isoformat(), "source_commit":build["source_commit"],
        "source_overlays":build["source_overlays"], "html_sha256":build["html_sha256"],
        "build_receipt":str(build_path.relative_to(ROOT)), "canonical_capture_exit":canonical_exit,
        "checks":checks, "screenshots":screenshots,
        "passed":sum(bool(c["passed"]) for c in checks), "failed":sum(not c["passed"] for c in checks),
        "limits":["Actual anonymous isolated browser with copied production inputs; external calls aborted.",
                  "Assistant opening and closing tested; no prompt, account mutation or authenticated answer requested."]}
    (target / "review_counterexamples.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ["checks","screenshots"]}))
    print(json.dumps({"failed_checks":[c for c in checks if not c["passed"]]}))
    return canonical_exit or bool(receipt["failed"])
if __name__=="__main__":
    raise SystemExit(main())
