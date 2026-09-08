"""Browser fixture for the existing card with the in-memory composition candidate."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "rru_composition_browser_20260908"
OUT.mkdir(exist_ok=True)
a.apply_bundle(candidate.bundle)
css = a.committed("templates/theme.css") + "\n" + a.committed("templates/_risk_radar_card.css.j2")
profile = a.radar.PROFILES["cn"]
fixtures = {}
for case in ("complete", "partial", "unavailable", "restored"):
    sub = a.fixture(profile)
    members = max(profile.comp_legs, key=lambda item: len(item[1]))[1]
    if case == "partial":
        sub[members[0]].iloc[-1] = a.np.nan
    elif case == "unavailable":
        for series in sub.values():
            series.iloc[-1] = a.np.nan
    elif case == "restored":
        for code in members:
            sub[code].iloc[-20:-10] = a.np.nan
    fixtures[case] = a.project(a.compute(profile, sub))

records = []
with sync_playwright() as browser_api:
    browser = browser_api.chromium.launch(headless=True)
    context = browser.new_context()
    context.route("**/*", lambda route: route.abort())
    page = context.new_page()
    page.set_default_timeout(10000)
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 900})
        for theme in ("dark", "light"):
            for lang in ("en", "zh"):
                for case, rd in fixtures.items():
                    note = "Synthetic fixture — not market data" if lang == "en" else "合成测试样本 — 非市场数据"
                    html = (f'<!doctype html><html data-theme="{theme}" data-lang="{lang}" lang="{lang}">'
                        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                        f'<style>{css}</style><style>main{{max-width:1000px;margin:24px auto;padding:12px}}'
                        '.fixture-note{color:var(--muted);margin-bottom:12px;font:14px system-ui}'
                        '</style></head><body><main>'
                        f'<div class="fixture-note">{note}</div>{a.render(rd)}</main></body></html>')
                    page.set_content(html, wait_until="domcontentloaded")
                    page.wait_for_timeout(50)
                    shot = OUT / f"{case}-{theme}-{lang}-{width}.png"
                    page.screenshot(path=str(shot), full_page=True)
                    closed_overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                    summary = page.locator(".rrx-authority details summary").first
                    summary.focus()
                    page.keyboard.press("Enter")
                    opened = page.locator(".rrx-authority details").first.evaluate("node => node.open")
                    opened_overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                    visible = page.locator(".rrx").inner_text()
                    expected_label = "Input coverage" if lang == "en" else "输入覆盖"
                    records.append(dict(case=case, theme=theme, lang=lang, width=width,
                        closed_overflow=closed_overflow, opened_overflow=opened_overflow,
                        keyboard_details_open=opened, translated_label_present=expected_label in visible,
                        screenshot=shot.name, sha256=hashlib.sha256(shot.read_bytes()).hexdigest()))
    context.close()
    browser.close()
result = dict(kind="synthetic_browser_fixture_not_production", cases=records,
              all_checks_pass=all(not r["closed_overflow"] and not r["opened_overflow"]
                and r["keyboard_details_open"] and r["translated_label_present"] for r in records))
(OUT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(dict(cases=len(records), all_checks_pass=result["all_checks_pass"],
                     failures=[r for r in records if r["closed_overflow"] or r["opened_overflow"]])))
raise SystemExit(0 if result["all_checks_pass"] else 1)
