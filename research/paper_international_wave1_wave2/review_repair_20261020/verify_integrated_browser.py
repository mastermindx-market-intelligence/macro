"""Source-backed currency display proof and explicitly time-shifted ageing controls."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"research/paper_international_wave1_wave2"))
import capture_country_cockpit as fixture
from preview_country_cockpit import DOCUMENT
from lib.intl_country_assessment import build_country_assessments
from engine import i18n
from jinja2 import Environment, FileSystemLoader

OUT = Path(__file__).resolve().parent
PREVIEW = OUT/"preview"
EVIDENCE = ROOT/"mockups/evidence/intl-review-repair-20261020"
COUNTRIES = ("JP", "KR", "TW", "IN", "AU", "GB", "EZ")
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844), "narrow": (320, 844)}

def set_state(page, theme, lang):
    page.goto("http://intl.test/intl.html", wait_until="domcontentloaded")
    page.evaluate("""({theme, lang}) => {
        if (typeof window.setTheme === 'function') window.setTheme(theme);
        if (typeof window.setLang === 'function') window.setLang(lang);
        document.documentElement.dataset.theme = theme;
        document.documentElement.dataset.lang = lang;
        document.documentElement.lang = lang;
    }""", {"theme": theme, "lang": lang})
    page.evaluate("() => document.fonts.ready.then(() => true)")

def main():
    started = datetime.now(timezone.utc).isoformat()
    fixture.OUTPUT = PREVIEW
    fixture.capture.VIEWPORTS = {**fixture.capture.VIEWPORTS, "narrow": (320, 844)}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    args = ["--repo", str(ROOT), "--base-url", "http://intl.test",
            "--routes", "/intl.html", "--output-dir", str(EVIDENCE),
            "--manifest", str(EVIDENCE/"manifest.json"), "--smells", str(EVIDENCE/"smells.json"),
            "--viewports", "desktop,mobile,narrow", "--locales", "en,zh",
            "--themes", "light,dark", "--max-pages", "1", "--delay-ms", "0",
            "--settle-ms", "500", "--timeout-s", "20",
            "--as-of", json.loads((PREVIEW/"manifest.json").read_text())["rendered_at"][:10]]
    with (OUT/"canonical_capture.log").open("w") as log, redirect_stdout(log), redirect_stderr(log):
        capture_exit = fixture.capture.main(args, driver_factory=fixture.real_chrome_driver)
    if capture_exit:
        print(json.dumps({"canonical_capture_exit": capture_exit}))
        return capture_exit

    from playwright.sync_api import sync_playwright
    assessment = json.loads((PREVIEW/"assessment.json").read_text())
    expected = {c["cc"]: c for c in assessment["countries"]}
    rows, shots, errors, history, controls = [], [], [], [], []
    focus_checks = []
    (OUT/"currency_shots").mkdir(exist_ok=True)
    selections = {
        ("desktop", "dark", "en", "KR"), ("desktop", "light", "en", "KR"),
        ("mobile", "dark", "zh", "JP"), ("narrow", "light", "en", "IN"),
        ("mobile", "light", "en", "TW"), ("desktop", "light", "zh", "AU"),
    }
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chrome", headless=True)
        routed = fixture.IsolatedBrowser(browser, (PREVIEW/"intl_integrated_preview.html").read_text())
        for viewport, (width, height) in VIEWPORTS.items():
            for theme in ("light", "dark"):
                for lang in ("en", "zh"):
                    context = routed.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
                    page = context.new_page()
                    page.on("pageerror", lambda e, key=(viewport, theme, lang): errors.append({"state": key, "message": str(e)}))
                    set_state(page, theme, lang)
                    for cc in COUNTRIES:
                        page.locator('[data-imc-country="'+cc+'"]').first.click()
                        page.wait_for_function("(cc) => document.getElementById('imc-country-'+cc).open", arg=cc)
                        country = page.locator("#imc-country-"+cc)
                        panel = country.locator(".imc-market-read")
                        panel.scroll_into_view_if_needed()
                        measured = panel.evaluate("""element => {
                            const box = element.getBoundingClientRect();
                            const cell = element.querySelector('.imc-fx-read');
                            const value = cell.querySelector('strong');
                            const selected = document.querySelector('.imc-country-rail a[aria-current="location"]');
                            const selectedStyle = getComputedStyle(selected);
                            const navStyle = getComputedStyle(document.querySelector('.imc-nav a:first-child'));
                            return {
                                selectedCountryShadow: selectedStyle.boxShadow,
                                selectedCountryWeight: selectedStyle.fontWeight,
                                mainNavEdgeWidth: navStyle.borderBottomWidth,
                                mainNavWeight: navStyle.fontWeight,
                                horizonEdges: [...document.querySelectorAll('.imc-horizon-note')].map(n => getComputedStyle(n).borderLeftWidth),
                                viewportWidth: innerWidth, documentWidth: document.documentElement.scrollWidth,
                                panelWidth: Math.round(box.width), panelScrollWidth: element.scrollWidth,
                                overflow: [...element.querySelectorAll('*')].filter(n => {
                                    const r = n.getBoundingClientRect();
                                    return r.width > 0 && r.height > 0 && (r.left < box.left-1 || r.right > box.right+1);
                                }).map(n => ({tag:n.tagName, class:n.className})),
                                openCountries: [...document.querySelectorAll('.imc-country[open]')].map(n=>n.id),
                                trendFont: getComputedStyle(element.querySelector('.imc-market-grid > div:first-child strong')).fontSize,
                                trendTextFont: getComputedStyle(element.querySelector('.imc-market-grid > div:first-child strong span')).fontSize,
                                quality: cell.dataset.fxQuality, label: cell.querySelector('span').innerText,
                                value: value.innerText, valueClass: value.className,
                                date: cell.querySelector('.imc-fx-date').innerText,
                                theme: document.documentElement.dataset.theme, lang: document.documentElement.dataset.lang
                            };
                        }""")
                        fx = expected[cc]["market"]["currency_observation"]
                        heading = country.locator(".imc-assessment-heading").inner_text()
                        label = expected[cc]["currency"] + (" vs USD · 3 months" if lang == "en" else " 兑美元 · 3个月")
                        valid = (measured["quality"] == "current" and measured["value"] == f'{fx["value"]:+.2f}%'
                                 and measured["label"].strip() == label and fx["end_date"] in measured["date"]
                                 and ("Through " if lang == "en" else "截至 ") in measured["date"]
                                 and ("imc-up" if fx["value"] > 0 else "imc-down") in measured["valueClass"]
                                 and ("Equity observations" if lang == "en" else "股市观测") in heading
                                 and expected[cc]["market"]["as_of"] in heading
                                 and measured["documentWidth"] <= width+1 and not measured["overflow"]
                                 and measured["panelScrollWidth"] <= measured["panelWidth"]+1
                                 and measured["openCountries"] == ["imc-country-"+cc]
                                 and measured["theme"] == theme and measured["lang"] == lang
                                 and measured["selectedCountryShadow"] == "none"
                                 and int(measured["selectedCountryWeight"]) >= 600
                                 and measured["mainNavEdgeWidth"] == "0px"
                                 and int(measured["mainNavWeight"]) >= 700
                                 and all(v == "0px" for v in measured["horizonEdges"]))
                        if (viewport, theme, lang, cc) in selections:
                            path = OUT/"currency_shots"/f"{cc.lower()}-{viewport}-{theme}-{lang}.png"
                            panel.screenshot(path=str(path), animations="disabled")
                            shots.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path.read_bytes()).hexdigest()})
                        evidence = country.locator(".imc-evidence")
                        evidence.locator("summary").click()
                        ledger = evidence.locator(".imc-currency-ledger")
                        text = ledger.inner_text()
                        source_ok = (ledger.locator("a").get_attribute("href") == fx["source_url"]
                                     and f'{fx["value"]:+.2f}%' in text
                                     and fx["start_date"] in text and fx["end_date"] in text
                                     and fx["reference_target"] in evidence.locator(".imc-currency-quotes").inner_text()
                                     and ("per USD" if fx["quote_convention"] == "local_per_USD" and lang == "en"
                                          else "/ 美元" if fx["quote_convention"] == "local_per_USD"
                                          else "USD per" if lang == "en" else "USD /")
                                         in evidence.locator(".imc-currency-quotes").inner_text()
                                     and page.evaluate("document.documentElement.scrollWidth") <= width+1)
                        evidence.locator("summary").click()
                        rows.append({"viewport": viewport, "theme": theme, "locale": lang, "cc": cc,
                                     "passed": bool(valid and source_ok), "source_verified": source_ok, **measured})
                    page.locator(".imc-nav a").first.focus()
                    page.keyboard.press("Tab")
                    focus = page.evaluate("""() => {
                        const n = document.activeElement, s = getComputedStyle(n);
                        return {tag:n.tagName, focusVisible:n.matches(':focus-visible'),
                                outlineWidth:s.outlineWidth, outlineStyle:s.outlineStyle};
                    }""")
                    focus_checks.append({"viewport":viewport,"theme":theme,"locale":lang,
                                         "passed":focus["focusVisible"] and focus["outlineStyle"] == "solid"
                                                  and float(focus["outlineWidth"].removesuffix("px")) >= 2,
                                         **focus})
                    if (viewport, theme, lang) == ("desktop", "light", "en"):
                        for cc in ("IN", "KR"):
                            page.locator('[data-imc-country="'+cc+'"]').first.click()
                        page.go_back()
                        page.wait_for_function("() => document.getElementById('imc-country-IN').open")
                        history.append({"action": "back", "cc": "IN", "passed": True})
                        page.go_forward()
                        page.wait_for_function("() => document.getElementById('imc-country-KR').open")
                        history.append({"action": "forward", "cc": "KR", "passed": True})
                    context.close()
        # Same real retained record evaluated at later dates; these are test controls.
        # No source date, quote or receipt is changed or admitted to canonical data.
        raw = json.loads((PREVIEW/"currency_replay.json").read_text())["KR"]
        equity = json.loads((PREVIEW/"market_replay.json").read_text())["KR"]
        env = Environment(loader=FileSystemLoader(ROOT/"templates"))
        env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr)
        for evaluated, quality in ((date(2026,10,25), "dated"), (date(2026,11,3), "missing")):
            model = build_country_assessments({"records":[{"cc":"KR", "equity":equity,
                                               "currency_observation":raw}]}, today=evaluated)
            html = env.from_string(DOCUMENT).render(intl_analysis=model)
            control = fixture.IsolatedBrowser(browser, html)
            for theme in ("light", "dark"):
                for lang in ("en", "zh"):
                    context = control.new_context(viewport={"width":320,"height":844}, device_scale_factor=1)
                    page = context.new_page()
                    page.on("pageerror", lambda e: errors.append({"state":"ageing_control","message":str(e)}))
                    set_state(page, theme, lang)
                    cell = page.locator(".imc-fx-read")
                    cell.scroll_into_view_if_needed()
                    text = cell.inner_text()
                    valid = (cell.get_attribute("data-fx-quality") == quality
                             and page.evaluate("document.documentElement.scrollWidth") <= 321)
                    if quality == "dated":
                        valid = valid and "+10.91%" in text and "2026-10-19" in text and (
                            "Dated" if lang == "en" else "较早观测") in text
                        valid = valid and cell.evaluate("(n)=>getComputedStyle(n.querySelector('strong')).color===getComputedStyle(n.querySelector('.imc-fx-date')).color")
                    else:
                        valid = valid and "—" in text and "2026-10-19" not in text and "+10.91%" not in text
                    controls.append({"kind":"TIME_SHIFTED_AGEING_CONTROL","evaluated_at":evaluated.isoformat(),
                                     "quality":quality,"theme":theme,"locale":lang,"passed":bool(valid),"text":text})
                    context.close()
        browser.close()
    result = {
        "schema":"mastermind.intl_integrated_browser_verification.v1",
        "focus_checks":focus_checks,
        "source_parent":"1a292672de4bb3f14b00c88e4af1f493b854a364",
        "main_parent":"422e121246f956834085853a49dfc6c2250d3dab",
        "scope":"Anonymous isolated integrated template in real Chrome; external requests blocked.",
        "started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),
        "html_sha256":sha256((PREVIEW/"intl_integrated_preview.html").read_bytes()).hexdigest(),
        "canonical_manifest":str((EVIDENCE/"manifest.json").relative_to(ROOT)),
        "canonical_manifest_sha256":sha256((EVIDENCE/"manifest.json").read_bytes()).hexdigest(),
        "canonical_capture_exit":capture_exit,"country_checks":len(rows),"passed":sum(r["passed"] for r in rows),
        "page_errors":errors,"history":history,"screenshots":shots,"checks":rows,"ageing_controls":controls,
        "ageing_passed":sum(r["passed"] for r in controls),
    }
    (OUT/"browser_verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("country_checks","passed","ageing_passed","page_errors","history","canonical_manifest")}))
    return 0 if all(r["passed"] for r in rows+controls+focus_checks) and not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
