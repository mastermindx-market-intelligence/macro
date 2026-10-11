"""Source-bound browser fixtures; synthetic inputs, never production proof."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "rru_composition_browser_20260909_v4"
OUT.mkdir(exist_ok=False)  # Preserve every previous receipt; never overwrite a run.
a.apply_bundle(candidate.bundle)
css = a.committed("templates/theme.css") + "\n" + a.committed("templates/_risk_radar_card.css.j2")
host = a.committed("templates/dashboard.html.j2")
body_rule = re.search(r"(?m)^  body \{[^}]*\}", host)
help_rules = re.findall(r"(?m)^  \.help(?: \.tip)? \{[^}]*\}", host)
assert body_rule is not None and len(help_rules) == 2
css += "\n" + body_rule.group(0) + "\n" + "\n".join(help_rules)
fixtures = {}
for market, profile in a.radar.PROFILES.items():
    cases = ("complete", "partial", "unavailable", "restored") if market == "cn" else ("partial",)
    for case in cases:
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
        fixtures[(market, case)] = a.project(a.compute(profile, sub))

CHECKS = ("no_closed_overflow", "no_opened_overflow", "keyboard_details_open",
          "translated_label_present", "language_exclusive", "help_hidden", "unreviewed_honest", "no_js_error")
records = []
with sync_playwright() as browser_api:
    browser = browser_api.chromium.launch(headless=True)
    context = browser.new_context()
    context.route("**/*", lambda route: route.abort())
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_default_timeout(10000)
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 900})
        for theme in ("dark", "light"):
            for lang in ("en", "zh"):
                for (market, case), rd in fixtures.items():
                    errors.clear()
                    note = "Synthetic fixture — not market data" if lang == "en" else "合成测试样本 — 非市场数据"
                    html = (f'<!doctype html><html data-theme="{theme}" data-lang="{lang}" lang="{lang}">'
                        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                        f'<style>{css}</style><style>main{{max-width:1000px;margin:24px auto;padding:12px}}'
                        '.fixture-note{color:var(--muted);margin-bottom:12px;font:14px system-ui}'
                        '</style></head><body><main>'
                        f'<div class="fixture-note">{market.upper()} · {note}</div>{a.render(rd)}</main></body></html>')
                    page.set_content(html, wait_until="domcontentloaded")
                    page.wait_for_timeout(50)
                    stem = f"{market}-{case}-{theme}-{lang}-{width}"
                    shot = OUT / f"{stem}.png"
                    page.screenshot(path=str(shot), full_page=True)
                    closed_overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                    summary = page.locator(".rrx-authority details summary").first
                    summary.focus()
                    page.keyboard.press("Enter")
                    opened = page.locator(".rrx-authority details").first.evaluate("node => node.open")
                    opened_overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                    opened_shot = OUT / f"{stem}-expanded.png"
                    page.screenshot(path=str(opened_shot), full_page=True)
                    visible = page.locator(".rrx").inner_text()
                    expected_label = "Input coverage" if lang == "en" else "输入覆盖"
                    opposite = "zh" if lang == "en" else "en"
                    language_exclusive = not page.locator(f".rrx .l-{opposite}").first.is_visible()
                    help_hidden = not page.locator(".help .tip").first.is_visible()
                    background = page.evaluate("getComputedStyle(document.body).backgroundColor")
                    unreviewed_honest = "✅" not in visible and "CALM" not in visible and "平静" not in visible
                    records.append(dict(market=market, case=case, theme=theme, lang=lang, width=width,
                        no_closed_overflow=not closed_overflow, no_opened_overflow=not opened_overflow,
                        language_exclusive=language_exclusive, help_hidden=help_hidden,
                        body_background=background, unreviewed_honest=unreviewed_honest,
                        keyboard_details_open=opened, translated_label_present=expected_label in visible,
                        no_js_error=not errors, js_errors=list(errors),
                        screenshot=shot.name, sha256=hashlib.sha256(shot.read_bytes()).hexdigest(),
                        expanded_screenshot=opened_shot.name,
                        expanded_sha256=hashlib.sha256(opened_shot.read_bytes()).hexdigest(),
                        html_sha256=hashlib.sha256(html.encode()).hexdigest()))
    context.close()
    browser.close()
backgrounds = {theme: {r['body_background'] for r in records if r['theme'] == theme}
               for theme in ('dark', 'light')}
themes_distinct = all(len(values) == 1 for values in backgrounds.values()) and backgrounds['dark'] != backgrounds['light']
result = dict(kind="synthetic_browser_fixture_not_production", schema_version=4,
              fixture_source_pin=a.PIN, cases=records, themes_distinct=themes_distinct,
              candidate_source_sha256={path: hashlib.sha256(text.encode()).hexdigest()
                                       for path, text in candidate.edited.items()},
              all_checks_pass=themes_distinct and all(all(r[k] for k in CHECKS) for r in records))
(OUT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
failures = [dict(market=r['market'], case=r['case'], theme=r['theme'], lang=r['lang'],
                 width=r['width'], failed_checks=[k for k in CHECKS if not r[k]])
            for r in records if not all(r[k] for k in CHECKS)]
print(json.dumps(dict(cases=len(records), screenshots=2 * len(records),
                     all_checks_pass=result['all_checks_pass'], themes_distinct=themes_distinct,
                     failures=failures)))
raise SystemExit(0 if result["all_checks_pass"] else 1)
