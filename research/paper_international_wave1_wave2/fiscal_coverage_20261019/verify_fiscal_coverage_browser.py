"""Verify fiscal readings in the canonical anonymous integrated Chrome fixture.

External requests are blocked. The dated market replay and original R12 evidence
remain unchanged; this increment records its own screenshots and manifest.
"""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research/paper_international_wave1_wave2"))
import capture_country_cockpit as fixture

OUT = Path(__file__).resolve().parent
PREVIEW = OUT / "preview"
EVIDENCE = ROOT / "mockups/evidence/intl-fiscal-coverage-20261020"
COUNTRIES = ("JP", "KR", "TW", "IN", "AU", "GB", "EZ")
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844), "narrow": (320, 844)}


def main():
    started = datetime.now(timezone.utc).isoformat()
    fixture.OUTPUT = PREVIEW
    fixture.capture.VIEWPORTS = {**fixture.capture.VIEWPORTS, "narrow": (320, 844)}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    args = ["--repo", str(ROOT), "--base-url", "http://intl.test",
            "--routes", "/intl.html", "--output-dir", str(EVIDENCE),
            "--manifest", str(EVIDENCE / "manifest.json"),
            "--smells", str(EVIDENCE / "smells.json"),
            "--viewports", "desktop,mobile,narrow", "--locales", "en,zh",
            "--themes", "light,dark", "--max-pages", "1",
            "--delay-ms", "0", "--settle-ms", "500", "--timeout-s", "20",
            "--as-of", json.loads((PREVIEW / "manifest.json").read_text())["rendered_at"][:10]]
    with (OUT / "canonical_capture.log").open("w") as log, redirect_stdout(log), redirect_stderr(log):
        capture_exit = fixture.capture.main(args, driver_factory=fixture.real_chrome_driver)
    if capture_exit:
        print(json.dumps({"canonical_capture_exit": capture_exit}))
        return capture_exit

    from playwright.sync_api import sync_playwright
    assessment = json.loads((PREVIEW / "assessment.json").read_text())
    expected = {c["cc"]: c["outlook"] for c in assessment["countries"]}
    rows, shots, history, errors = [], [], [], []
    (OUT / "fiscal_shots").mkdir(exist_ok=True)
    selections = {
        ("desktop", "dark", "en", "KR"), ("desktop", "light", "en", "KR"),
        ("mobile", "dark", "zh", "IN"), ("narrow", "light", "en", "IN"),
        ("mobile", "light", "en", "TW"), ("desktop", "light", "zh", "AU"),
    }
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chrome", headless=True)
        routed = fixture.IsolatedBrowser(browser, (PREVIEW / "intl_integrated_preview.html").read_text())
        for viewport, (width, height) in VIEWPORTS.items():
            for theme in ("light", "dark"):
                for lang in ("en", "zh"):
                    context = routed.new_context(viewport={"width": width, "height": height},
                                                 device_scale_factor=1)
                    page = context.new_page()
                    page.on("pageerror", lambda error, key=(viewport, theme, lang):
                            errors.append({"state": key, "message": str(error)}))
                    page.goto("http://intl.test/intl.html", wait_until="domcontentloaded")
                    page.evaluate("""({theme, lang}) => {
                        if (typeof window.setTheme === 'function') window.setTheme(theme);
                        if (typeof window.setLang === 'function') window.setLang(lang);
                        document.documentElement.dataset.theme = theme;
                        document.documentElement.dataset.lang = lang;
                        document.documentElement.lang = lang;
                    }""", {"theme": theme, "lang": lang})
                    page.evaluate("() => document.fonts.ready.then(() => true)")
                    for cc in COUNTRIES:
                        page.locator('[data-imc-country="' + cc + '"]').first.click()
                        page.wait_for_function("(cc) => document.getElementById('imc-country-' + cc).open", arg=cc)
                        country = page.locator("#imc-country-" + cc)
                        panel = country.locator('[aria-labelledby="imc-balances-' + cc + '"]')
                        panel.scroll_into_view_if_needed()
                        measured = panel.evaluate("""(element) => {
                            const box = element.getBoundingClientRect();
                            const overflowing = [...element.querySelectorAll('*')].filter(node => {
                                const r = node.getBoundingClientRect();
                                return r.width > 0 && r.height > 0 &&
                                    (r.left < box.left - 1 || r.right > box.right + 1);
                            }).map(node => ({tag: node.tagName, class: node.className}));
                            return {
                                viewportWidth: innerWidth, documentWidth: document.documentElement.scrollWidth,
                                panelWidth: Math.round(box.width), panelScrollWidth: element.scrollWidth,
                                overflowing, openCountries: [...document.querySelectorAll('.imc-country[open]')].map(n => n.id),
                                theme: document.documentElement.dataset.theme,
                                lang: document.documentElement.dataset.lang,
                                visibleText: element.innerText,
                                rows: [...element.querySelectorAll('.imc-balance-row')].map(n => n.innerText)
                            };
                        }""")
                        balances = expected[cc]["balances"]
                        row_checks = []
                        for balance, rendered in zip(balances, measured["rows"]):
                            tokens = [balance["label_" + lang], balance["reading_" + lang],
                                      balance["year_label"], balance["next_label"],
                                      f'{balance["current"]:.1f}%', f'{balance["next"]:.1f}%']
                            row_checks.append({"series": balance["series_id"],
                                               "passed": all(t in rendered for t in tokens)})
                        forecast_label = "% GDP · FORECAST" if lang == "en" else "占GDP · 预测"
                        valid = (len(balances) == len(measured["rows"]) == 3
                                 and all(r["passed"] for r in row_checks)
                                 and forecast_label in measured["visibleText"]
                                 and measured["documentWidth"] <= width + 1
                                 and not measured["overflowing"]
                                 and measured["panelScrollWidth"] <= measured["panelWidth"] + 1
                                 and measured["openCountries"] == ["imc-country-" + cc]
                                 and measured["theme"] == theme and measured["lang"] == lang)
                        if (viewport, theme, lang, cc) in selections:
                            path = OUT / "fiscal_shots" / f"{cc.lower()}-{viewport}-{theme}-{lang}.png"
                            panel.screenshot(path=str(path), animations="disabled")
                            shots.append({"path": str(path.relative_to(ROOT)),
                                          "sha256": sha256(path.read_bytes()).hexdigest()})
                        evidence = country.locator(".imc-evidence")
                        evidence.locator("summary").click()
                        ledger = evidence.inner_text()
                        links = evidence.locator("a").evaluate_all("(nodes) => nodes.map(n => n.href)")
                        expected_links = set()
                        for series in expected[cc]["series"].values():
                            url = series.get("dataset_url") or series["source_url"]
                            if series.get("dataset_url") and series.get("source_page"):
                                url += "#page=" + str(series["source_page"])
                            expected_links.add(url)
                        notes = [b.get("coverage_note_" + lang) or b.get("coverage_note")
                                 for b in balances if b.get("coverage_note")]
                        source_ok = (expected_links <= set(links)
                                     and all(note in ledger for note in notes)
                                     and ("Fiscal projections have not been verified" not in ledger)
                                     and ("财政预测尚未核验" not in ledger)
                                     and page.evaluate("document.documentElement.scrollWidth") <= width + 1)
                        evidence.locator("summary").click()
                        rows.append({"viewport": viewport, "theme": theme, "locale": lang, "cc": cc,
                                     "passed": bool(valid and source_ok), "series_checks": row_checks,
                                     "source_links_verified": sorted(expected_links),
                                     "source_notes_verified": source_ok, **measured})
                    if (viewport, theme, lang) == ("desktop", "light", "en"):
                        for cc in ("IN", "KR"):
                            page.locator('[data-imc-country="' + cc + '"]').first.click()
                            page.wait_for_function("(cc) => document.getElementById('imc-country-' + cc).open", arg=cc)
                        page.go_back()
                        page.wait_for_function("() => document.getElementById('imc-country-IN').open")
                        history.append({"action": "back", "cc": "IN", "passed": True})
                        page.go_forward()
                        page.wait_for_function("() => document.getElementById('imc-country-KR').open")
                        history.append({"action": "forward", "cc": "KR", "passed": True})
                    context.close()
        browser.close()
    result = {
        "schema": "mastermind.intl_fiscal_browser_verification.v1",
        "scope": "Anonymous isolated integrated template in real Chrome; external requests are blocked.",
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "html_sha256": sha256((PREVIEW / "intl_integrated_preview.html").read_bytes()).hexdigest(),
        "canonical_manifest": str((EVIDENCE / "manifest.json").relative_to(ROOT)),
        "canonical_manifest_sha256": sha256((EVIDENCE / "manifest.json").read_bytes()).hexdigest(),
        "canonical_capture_exit": capture_exit, "viewport_count": len(VIEWPORTS),
        "country_checks": len(rows), "passed": sum(r["passed"] for r in rows),
        "page_errors": errors, "history": history, "screenshots": shots, "checks": rows
    }
    (OUT / "browser_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("country_checks", "passed", "page_errors", "history", "canonical_manifest")}))
    return 0 if all(r["passed"] for r in rows) and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
