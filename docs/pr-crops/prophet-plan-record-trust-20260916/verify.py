"""Exact consumer + shared pager proof. Synthetic screenshots, real-input aggregates.

No external requests, production writes, provider calls or new source population.
Run from this isolated worktree: python3 docs/pr-crops/prophet-plan-record-trust-20260916/verify.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import jinja2
from markupsafe import escape
from playwright.sync_api import sync_playwright
from engine.i18n import tr
import scripts.build_site as bs


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run() -> None:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals.update(tr=tr, us_stance_projection=bs.us_stance_projection)
    template = env.get_template("_us_prophet_plan_cards.html.j2")
    book_bytes = (ROOT / "site/prophet/index.json").read_bytes()
    book = json.loads(book_bytes)
    real_rows = book["plans"]
    real_before = copy.deepcopy(real_rows)
    episodes = bs._us_prophet_episode_map(real_rows)
    real_html = template.render(items=real_rows, cand_map={}, trg_map={}, episode_map=episodes)
    assert real_rows == real_before
    assert book_bytes == (ROOT / "site/prophet/index.json").read_bytes()
    expected_names = []
    for row in real_rows:
        field = ((row.get("board_read") or {}).get("fields") or {}).get("name") or {}
        if field.get("state") == "available" and isinstance(field.get("value"), str):
            expected_names.append(field["value"])
    assert all(str(escape(n)) in real_html for n in expected_names)

    # These quotes and issuers are entirely synthetic. No real premium plan rows
    # are persisted in the screenshot/HTML fixture.
    synthetic = []
    for i, state in enumerate(["resolved", "entered", "invalidated", "ready", "overtime", None]):
        symbol = "DEMO-" + chr(65 + i)
        synthetic.append({
            "id": symbol + "-BULL-20260812", "asset": symbol,
            "lifecycle_state": state, "closed": state == "resolved",
            "entry_status": "buy_now", "_priority_score": 90 - i,
            "plan_asof": "2026-08-12", "recorded_at": "2026-08-12",
            "entry_zone": {"low": 100.25 + i, "high": 103.50 + i} if i != 4 else None,
            "board_read": {"as_of": "2026-09-15", "fields": {
                "status": {"state": "available", "value": "blocked"},
                "name": {"state": "available", "value": ["Example Industrials", "Example Health", "Example Materials", "Example Technology", "Example Consumer", "Example Research"][i]},
                "sector": {"state": "available", "value": "Industrials"},
            }} if i != 5 else None,
        })
    synthetic[-1]["plan_asof"] = synthetic[-1]["recorded_at"] = None
    synthetic_episodes = {synthetic[0]["id"]: {
        "ep": 1, "eps": 2, "dopen_en": "Aug 12", "dopen_zh": "8月12日",
        "newer": synthetic[1]["id"],
    }}
    fixture_cards = template.render(items=synthetic, cand_map={}, trg_map={}, episode_map=synthetic_episodes)
    theme_css = (ROOT / "templates/theme.css").read_text()
    dash = (ROOT / "templates/dashboard.html.j2").read_text()
    grid = re.search(r"  \.nbgrid \{[^}]*\}", dash)
    mobile = re.search(r"    \.nbgrid\[data-showmore-rows\]\{[^}]*\}", dash)
    assert grid and mobile, "actual grid style seam must resolve"
    extra = "\n".join(line.strip() for line in dash.splitlines() if line.strip().startswith((".pv-life{", ".pv-life-w{", ".pv-newer{", ".pv-newer:hover", ".pv-mark{")))
    component_css = str(env.get_template("_prophet_card.html.j2").module.pv_css())
    css = "<style>" + theme_css + grid.group() + "@media(max-width:680px){" + mobile.group() + "}" + extra + "body{margin:0;padding:18px;background:var(--bg);color:var(--text)}main{max-width:1440px;margin:auto}</style>" + component_css
    theme_js = (ROOT / "templates/theme.js").read_text()
    start = theme_js.index("  function smBL(")
    end_marker = "  window.initShowMore = initShowMore;"
    end = theme_js.index(end_marker, start) + len(end_marker)
    pager = theme_js[start:end]
    life_css_start = dash.index('  #us-standouts[data-lifef="watch"]')
    life_css_marker = '  #us-standouts[data-lifef] #us-life-grid + .sm-bar { display: none !important; }'
    life_css_end = dash.index(life_css_marker, life_css_start) + len(life_css_marker)
    life_css = dash[life_css_start:life_css_end]
    life_marker = "P-MP1-SHELL §7 — the lifecycle ladder's filter + URL law"
    life_script_start = dash.index("<script>", dash.index(life_marker)) + len("<script>")
    life_script_end = dash.index("</script>", life_script_start)
    life_script = dash[life_script_start:life_script_end]
    navigation_css = css.replace("</style>", life_css + "</style>", 1)

    def document(
        cards: str,
        theme: str,
        lang: str,
        *,
        lifecycle: bool = False,
        exclude_resolved: bool = False,
    ) -> str:
        selected_css = navigation_css if lifecycle else css
        pager_exclusion = ' data-showmore-exclude-life="resolved"' if exclude_resolved else ''
        html = ('<!doctype html><html data-theme="' + theme + '" data-lang="' + lang + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + selected_css + '</head><body class="page-stocks"><main><h1>Tracked setups</h1><p>Component proof · synthetic screenshots · not production</p><section id="us-standouts"><div class="nbgrid" data-showmore-rows="3"' + pager_exclusion + ' id="us-life-grid">' + cards + '</div></section></main></body></html>')
        # Preserve the rendered fixture while keeping committed evidence whitespace-clean.
        return "\n".join(line.rstrip() for line in html.splitlines()) + "\n"

    (OUT / "synthetic-fixture.html").write_text(document(fixture_cards, "dark", "en"))
    receipt = {
        "scope": "isolated real-input component/pager proof and synthetic visual fixture; not production",
        "source_base": "4f37209719d2ca5caf9fd3a37aca29fa363f351c",
        "source_state": "uncommitted worktree; bind by exact source hashes",
        "real_input_sha256": digest(book_bytes), "declared_rows": len(real_rows),
        "attached_names_verified_without_candidates": len(expected_names),
        "newer_links": sum(bool(x.get("newer")) for x in episodes.values()),
        "inputs_unchanged": True, "external_requests_allowed": False,
        "pager_section_sha256": digest(pager.encode()),
        "lifecycle_script_sha256": digest(life_script.encode()),
        "lifecycle_filter_css_sha256": digest(life_css.encode()),
        "cases": [], "navigation_cases": [], "pager_cases": [],
        "source_sha256": {p: digest((ROOT / p).read_bytes()) for p in [
            "templates/_prophet_card.html.j2", "templates/_us_prophet_plan_cards.html.j2",
            "templates/theme.css", "templates/theme.js", "templates/dashboard.html.j2",
            "scripts/build_site.py", "engine/i18n.py",
        ]},
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            receipt["browser_version"] = browser.version
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            real_errors = []
            page.on("pageerror", lambda err: real_errors.append(str(err)))
            page.route("**/*", lambda route: route.abort())
            page.set_content(document(real_html, "dark", "en", lifecycle=True, exclude_resolved=True))
            page.add_script_tag(content=pager + "\ninitShowMore();")
            real_dom = page.evaluate("""() => {
                const cards = [...document.querySelectorAll('.pvcard')];
                const ids = cards.map(x => x.id);
                const unresolved = cards.filter(x => x.getAttribute('data-life') !== 'resolved');
                const resolved = cards.filter(x => x.getAttribute('data-life') === 'resolved');
                return {
                    cards: cards.length,
                    unique_ids: new Set(ids).size,
                    grid_children: document.querySelector('#us-life-grid').children.length,
                    record_markers: document.querySelectorAll('[data-record-only="1"]').length,
                    action_badges: document.querySelectorAll('.pv-buy,.pv-wait,.pv-near,.pv-hold,.pv-avoid').length,
                    resolved_records: resolved.length,
                    default_population: unresolved.length,
                    visible_unresolved: unresolved.filter(x => !x.classList.contains('sm-hidden')).length,
                    hidden_resolved: resolved.filter(x => x.classList.contains('sm-hidden')).length,
                    pagination: document.querySelector('.sm-count .l-en').textContent,
                };
            }""")
            assert real_dom["cards"] == real_dom["unique_ids"] == real_dom["grid_children"] == len(real_rows), real_dom
            assert real_dom["record_markers"] == len(real_rows) and real_dom["action_badges"] == 0
            assert real_dom["default_population"] + real_dom["resolved_records"] == len(real_rows), real_dom
            assert real_dom["resolved_records"] > 0 and real_dom["hidden_resolved"] == real_dom["resolved_records"], real_dom
            assert real_dom["visible_unresolved"] == min(15, real_dom["default_population"]), real_dom
            assert real_dom["pagination"] == f"Showing {real_dom['visible_unresolved']} of {real_dom['default_population']}", real_dom
            receipt["real_dom"] = real_dom
            page.locator(".sm-ghost").click()
            show_all = page.evaluate("""() => {
                const cards = [...document.querySelectorAll('.pvcard')];
                const unresolved = cards.filter(x => x.getAttribute('data-life') !== 'resolved');
                const resolved = cards.filter(x => x.getAttribute('data-life') === 'resolved');
                return {
                    visible_unresolved: unresolved.filter(x => !x.classList.contains('sm-hidden')).length,
                    hidden_resolved: resolved.filter(x => x.classList.contains('sm-hidden')).length,
                    pagination: document.querySelector('.sm-count .l-en').textContent,
                };
            }""")
            assert show_all["visible_unresolved"] == real_dom["default_population"], show_all
            assert show_all["hidden_resolved"] == real_dom["resolved_records"], show_all
            assert show_all["pagination"] == f"Showing {real_dom['default_population']} of {real_dom['default_population']}", show_all
            page.locator("#us-standouts").evaluate("el => el.setAttribute('data-lifef', 'resolved')")
            resolved_visible = page.locator('#us-life-grid > [data-life="resolved"]').evaluate_all(
                "els => els.filter(el => getComputedStyle(el).display !== 'none').length"
            )
            assert resolved_visible == real_dom["resolved_records"], (resolved_visible, real_dom)
            assert not real_errors, real_errors
            receipt["real_pager_show_all"] = True
            receipt["pager_cases"].append({
                "case": "real_input_default_live_population",
                "dom_records_preserved": real_dom["cards"],
                "default_population": real_dom["default_population"],
                "resolved_history": real_dom["resolved_records"],
                "initial_visible": real_dom["visible_unresolved"],
                "show_all_visible": show_all["visible_unresolved"],
                "resolved_filter_visible": resolved_visible,
                "page_errors": real_errors,
            })
            page.close()

            # Real page lifecycle script + filter CSS: a newer episode must become
            # visible before native fragment navigation, even when show-more hid it.
            nav_rows = []
            for i in range(18):
                row = copy.deepcopy(synthetic[1] if i == 17 else synthetic[3])
                row["id"] = f"NAV-{i:02d}-BULL-20260812"
                row["asset"] = f"NAV-{i:02d}"
                row["lifecycle_state"] = "entered" if i == 17 else "ready"
                row["closed"] = False
                nav_rows.append(row)
            nav_source = copy.deepcopy(synthetic[0])
            nav_source["id"] = "NAV-SOURCE-BULL-20260812"
            nav_source["asset"] = "NAV-SOURCE"
            nav_source["lifecycle_state"] = "resolved"
            nav_source["closed"] = True
            nav_target = nav_rows[-1]
            nav_all = [nav_source] + nav_rows
            nav_episodes = {nav_source["id"]: {
                "ep": 1, "eps": 2, "dopen_en": "Aug 12", "dopen_zh": "8月12日",
                "newer": nav_target["id"],
            }}
            nav_html = template.render(items=nav_all, cand_map={}, trg_map={}, episode_map=nav_episodes)

            def navigation_page(cards: str, url: str):
                page = browser.new_page(viewport={"width": 390, "height": 900})
                errors = []
                page.on("pageerror", lambda err: errors.append(str(err)))
                body = document(cards, "dark", "en", lifecycle=True, exclude_resolved=True)
                page.route("**/*", lambda route: route.fulfill(
                    status=200, body=body, content_type="text/html")
                    if route.request.is_navigation_request() else route.abort())
                page.goto(url)
                page.add_script_tag(content=pager + "\ninitShowMore();\n" + life_script)
                return page, errors

            nav_url = "http://proof.invalid/us_stocks.html?foo=keep&life=resolved"
            page, errors = navigation_page(nav_html, nav_url)
            target_sel = "#pv-" + nav_target["id"]
            assert page.locator(target_sel).count() == 1
            assert page.locator(target_sel).evaluate("el => el.classList.contains('sm-hidden')")
            assert not page.locator(target_sel).is_visible()
            page.locator("#pv-" + nav_source["id"] + " a.pv-newer").click()
            assert page.locator(target_sel).is_visible()
            assert page.locator("#us-standouts").get_attribute("data-lifef") == "entered"
            assert page.url == nav_url.replace("life=resolved", "life=entered") + "#pv-" + nav_target["id"]
            assert not errors, errors
            receipt["navigation_cases"].append({
                "case": "filtered_beyond_first_page", "target_visible": True,
                "query_preserved": "foo=keep" in page.url, "native_fragment": True,
                "target_was_sm_hidden": True, "page_errors": errors,
            })
            page.close()

            # The listener is delegated from #us-standouts, which survives the
            # entitled grid replacement. Replace the grid after initialization,
            # then verify keyboard activation reaches the newly hydrated target.
            source_only = template.render(items=[nav_source], cand_map={}, trg_map={}, episode_map=nav_episodes)
            target_only = template.render(items=[nav_target], cand_map={}, trg_map={}, episode_map={})
            page, errors = navigation_page(source_only, nav_url)
            page.evaluate("""(targetHtml) => {
                const oldGrid = document.getElementById('us-life-grid');
                const oldBar = oldGrid.nextElementSibling;
                const fresh = document.createElement('div');
                fresh.className = oldGrid.className;
                fresh.id = 'us-life-grid';
                fresh.setAttribute('data-showmore-rows', '3');
                fresh.setAttribute('data-showmore-exclude-life', 'resolved');
                fresh.innerHTML = oldGrid.innerHTML + targetHtml;
                oldGrid.replaceWith(fresh);
                if (oldBar && oldBar.classList.contains('sm-bar')) oldBar.remove();
                if (window.initShowMore) window.initShowMore();
            }""", target_only)
            target_sel = "#pv-" + nav_target["id"]
            assert page.locator(target_sel).count() == 1
            assert not page.locator(target_sel).is_visible()
            newer = page.locator("#pv-" + nav_source["id"] + " a.pv-newer")
            newer.focus()
            newer.press("Enter")
            assert page.locator(target_sel).is_visible()
            assert page.locator("#us-standouts").get_attribute("data-lifef") == "entered"
            assert page.url == nav_url.replace("life=resolved", "life=entered") + "#pv-" + nav_target["id"]
            assert not errors, errors
            receipt["navigation_cases"].append({
                "case": "hydrated_keyboard_target", "target_visible": True,
                "query_preserved": "foo=keep" in page.url, "native_fragment": True,
                "delegated_after_grid_replacement": True, "page_errors": errors,
            })
            page.close()

            for width in [1440, 390]:
                for theme in ["dark", "light"]:
                    for lang in ["en", "zh"]:
                        page = browser.new_page(viewport={"width": width, "height": 1100})
                        page.route("**/*", lambda route: route.abort())
                        errors = []
                        page.on("pageerror", lambda err: errors.append(str(err)))
                        page.set_content(document(fixture_cards, theme, lang))
                        # Stabilize visual evidence: the component owns hover/focus
                        # transitions, but screenshots are contract artifacts rather
                        # than animation-frame samples.
                        page.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
                        page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
                        page.add_script_tag(content=pager + "\ninitShowMore();")
                        assert page.locator(f".pv-chip .l-{lang}").first.is_visible()
                        hidden_lang = "en" if lang == "zh" else "zh"
                        assert not page.locator(f".pv-chip .l-{hidden_lang}").first.is_visible()
                        assert page.locator("article.pv-record").count() == len(synthetic)
                        assert page.locator(".pv-buy,.pv-wait,.pv-near,.pv-hold,.pv-avoid,.pv-live,.pv-trg").count() == 0
                        geometry = page.evaluate("""() => ({overflow:document.documentElement.scrollWidth>innerWidth+1,background:getComputedStyle(document.body).backgroundColor,chip:getComputedStyle(document.querySelector('.pv-chip')).color,created:[...document.querySelectorAll('.pv-added')].map(e=>({text:e.innerText,clipped:e.scrollWidth>e.clientWidth+1}))})""")
                        assert not geometry["overflow"], geometry
                        expected_bg = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()")
                        assert expected_bg, "theme background token is missing"
                        assert geometry["background"] != "rgba(0, 0, 0, 0)", geometry
                        assert not any(x["clipped"] for x in geometry["created"]), geometry
                        metadata = page.locator(".pv-mk-i,.pv-newer").evaluate_all("els => els.map(e=>({text:e.innerText,clipped:e.scrollWidth>e.clientWidth+1}))")
                        assert not any(x["clipped"] for x in metadata), metadata
                        geometry["metadata"] = metadata
                        page.evaluate("document.addEventListener('click',e=>{const a=e.target.closest('a');if(a){window.__href=a.getAttribute('href');e.preventDefault();}},true)")
                        page.locator("a.pv-newer").click()
                        assert page.evaluate("window.__href") == "#pv-" + synthetic[1]["id"]
                        page.locator("a.pv-record-link").first.click(position={"x": 12, "y": 12})
                        assert page.evaluate("window.__href") == "stock.html#DEMO-A"
                        page.locator("a.pv-record-link").first.focus()
                        page.locator("a.pv-record-link").first.press("Enter")
                        assert page.evaluate("window.__href") == "stock.html#DEMO-A"
                        assert not errors, errors
                        image = f"record-{theme}-{lang}-{width}.png"
                        page.mouse.move(width - 1, 1099)
                        page.evaluate("document.activeElement && document.activeElement.blur()")
                        page.wait_for_timeout(50)
                        # First capture warms first-use system glyph rasterization
                        # (notably the wide Chinese case); only the second capture
                        # becomes durable evidence.
                        page.screenshot(full_page=True, animations="disabled", caret="hide")
                        page.wait_for_timeout(50)
                        page.screenshot(
                            path=str(OUT / image),
                            full_page=True,
                            animations="disabled",
                            caret="hide",
                        )
                        receipt["cases"].append({"width": width, "theme": theme, "language": lang,
                            "geometry": geometry, "stock_link": True, "newer_link": True,
                            "keyboard_link": True, "page_errors": errors,
                            "image": image, "image_sha256": digest((OUT / image).read_bytes())})
                        print("CASE_PASS", width, theme, lang, flush=True)
                        page.close()
        finally:
            browser.close()
    for p, sha in receipt["source_sha256"].items():
        assert digest((ROOT / p).read_bytes()) == sha, "source changed during capture: " + p
    receipt["status"] = "PASS_COMPONENT_NOT_PRODUCTION"
    receipt["capture_script_sha256"] = digest(Path(__file__).read_bytes())
    receipt["synthetic_fixture_sha256"] = digest((OUT / "synthetic-fixture.html").read_bytes())
    tmp = OUT / "browser-receipt.json.tmp"
    tmp.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(OUT / "browser-receipt.json")
    print("REAL_DOM", json.dumps(receipt["real_dom"]), flush=True)
    print("PAGER_PROOF", len(receipt["pager_cases"]), "DEFAULT-LIVE PASS_COMPONENT_NOT_PRODUCTION", flush=True)
    print("BROWSER_PROOF", len(receipt["cases"]), "VISUAL +", len(receipt["navigation_cases"]), "NAVIGATION PASS_COMPONENT_NOT_PRODUCTION", flush=True)


if __name__ == "__main__":
    run()
