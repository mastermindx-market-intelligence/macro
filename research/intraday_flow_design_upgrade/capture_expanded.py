"""Supplemental actual-click evidence captures; canonical matrix lives in final-r2."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"mockups/refs/intraday-flow-upgrade/expanded"
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width,theme,lang in [(1440,"light","en"),(1440,"dark","zh"),(390,"light","en"),(390,"dark","zh")]:
        context=browser.new_context(viewport={"width":width,"height":900 if width==1440 else 844},reduced_motion="reduce")
        context.add_init_script("localStorage.setItem('theme',"+json.dumps(theme)+");localStorage.setItem('lang',"+json.dumps(lang)+");localStorage.removeItem('themeAuto');")
        page=context.new_page()
        page.goto("http://127.0.0.1:8767/intraday_flow.html",wait_until="networkidle")
        page.locator("#ift-search").fill("CW")
        button=page.locator('button.expander[data-exp="CW"]')
        button.press("Enter")
        detail=page.locator('[data-detail="CW"]')
        detail.wait_for(state="visible")
        page.wait_for_timeout(300)
        name=("desktop" if width==1440 else "phone")+"-"+theme+"-"+lang+"-evidence.png"
        detail.screenshot(path=str(OUT/name))
        print(name,flush=True)
        context.close()
    browser.close()
