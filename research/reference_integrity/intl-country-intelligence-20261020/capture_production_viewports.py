"""Legible direct-browser viewport evidence supplementing the full production captures."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SHOTS=ROOT/"mockups/refs/reference_integrity/intl-country-intelligence-20261020/before"
URL="https://www.mastermind-x.com/intl.html"

def main():
    rows=[]
    with sync_playwright() as runtime:
        browser=runtime.chromium.launch(channel="chrome",headless=True)
        for viewport,width,height in (("desktop",1440,900),("mobile",390,844)):
            for locale in ("en","zh"):
                for theme in ("light","dark"):
                    context=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1)
                    context.add_init_script("""(() => {
                        localStorage.setItem('theme',THEME);
                        localStorage.setItem('lang',LANG);
                        localStorage.removeItem('themeAuto');
                    })()""".replace("THEME",json.dumps(theme)).replace("LANG",json.dumps(locale)))
                    page=context.new_page()
                    errors=[]
                    page.on("pageerror",lambda err:errors.append(str(err)))
                    response=page.goto(URL,wait_until="domcontentloaded",timeout=30000)
                    page.evaluate("""({theme,locale}) => {
                        if (typeof window.setTheme === 'function') window.setTheme(theme);
                        if (typeof window.setLang === 'function') window.setLang(locale);
                    }""",{"theme":theme,"locale":locale})
                    page.wait_for_timeout(700)
                    page.evaluate("() => document.fonts.ready.then(() => true)")
                    state=page.evaluate("""() => ({
                        theme:document.documentElement.dataset.theme,
                        locale:document.documentElement.dataset.lang,
                        scrollX,scrollY,documentHeight:document.documentElement.scrollHeight
                    })""")
                    name=f"viewport-{viewport}-{locale}-{theme}.png"
                    path=SHOTS/name
                    page.screenshot(path=str(path),full_page=False,animations="disabled")
                    rows.append({"path":str(path.relative_to(ROOT)),"viewport":viewport,
                        "width":width,"height":height,"theme":theme,"locale":locale,
                        "actual":state,"status":response.status if response else None,
                        "response_sha256":sha256(response.body()).hexdigest() if response else None,
                        "sha256":sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size,
                        "page_errors":errors,"captured_at":datetime.now(timezone.utc).isoformat()})
                    context.close()
        browser.close()
    receipt={"schema":"intl.reference_viewport_capture.v1","live_url":URL,
        "kind":"direct browser screenshots, no image transformation","states":rows}
    (OUT/"production_viewports.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"states":len(rows),"all_response_hashes":sorted({r["response_sha256"] for r in rows}),
        "page_errors":sum(len(r["page_errors"]) for r in rows)}))

if __name__=="__main__":
    main()
