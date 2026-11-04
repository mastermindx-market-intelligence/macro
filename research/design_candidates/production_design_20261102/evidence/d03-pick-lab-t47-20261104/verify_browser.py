"""Actual Pick Lab template/write_page and Chromium navigation proof.

Synthetic research inputs, temporary outputs, no production engine/ledger runs.
All network requests are intercepted; source assets come from the candidate tree.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import mimetypes
import re
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright


def contrast(first, second):
    def luminance(color):
        parts = [float(v) / 255 for v in re.findall(r"[\d.]+", color)[:3]]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in parts]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--red-only", action="store_true")
    args = parser.parse_args()
    root, out = args.repo.resolve(), args.out.resolve()
    assert out.is_dir() and not list(out.iterdir()), "Use a new empty evidence directory"
    sys.path.insert(0, str(root))
    from engine.pick_lab import render
    from lib import config
    fixture = load_module("t47_navigation_fixture", root / "tests/test_pick_lab_navigation.py")
    previous = load_module("t47_retained_fixture", root / "tests/test_pick_lab_render.py")
    source_paths = ["templates/us_stocks_lab.html.j2", "engine/pick_lab/render.py",
                    "tests/test_pick_lab_navigation.py", "tests/test_pick_lab_render.py",
                    "tests/js/pick_lab_navigation_harness.cjs", "templates/theme.css",
                    "templates/theme.js", "templates/shared_shell.css",
                    "templates/shared_shell_bridge.js", "templates/data_base.js",
                    "lib/pages.py", "lib/shared_shell.py"]
    hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
    # This committed public asset is omitted from the sparse source workspace.
    # Read its exact Git blob; do not invent a configuration stub.
    live_config = subprocess.check_output(["git", "show", "HEAD:site/live_config.js"], cwd=root)
    hashes["site/live_config.js"] = hashlib.sha256(live_config).hexdigest()
    pl, lh = previous._prod_fixture()
    fires = previous._fires_dict_fixture()
    # The retained fixture has LH edge history, not compounder history. Add
    # explicitly synthetic compounder rows instead of asserting absent content.
    fires["fires_by_book"][fixture.LONG_HOLD] = copy.deepcopy(fires["fires_by_book"][fixture.ENTRY])
    vm_full = render.build_vm(pl, lh, fires_dict=fires)
    vm_full["scoreboard"].append(fixture.navigation_vm()["scoreboard"][-1])
    vm_long = fixture.navigation_vm()
    for book in vm_long["all_books"]:
        book["name_en"] = "A deliberately long research book name with retained provenance and predeclared horizon"
        book["name_zh"] = "保留来源及预先声明时间范围的长名称研究书本，不改变既定历史或选择规则"
    cases = {"populated": vm_full, "empty": fixture.navigation_vm(empty=True),
             "long-name": vm_long, "singleton": fixture.navigation_vm(singleton=True)}
    sites = {}
    for name, model in cases.items():
        case_root = out / "fixtures" / name
        site = case_root / "site"
        site.mkdir(parents=True)
        (case_root / "templates").symlink_to(root / "templates", target_is_directory=True)
        for asset in ("theme.css", "theme.js", "data_base.js"):
            shutil.copy2(root / "templates" / asset, site / asset)
        (site / "live_config.js").write_bytes(live_config)
        with patch.object(config, "ROOT", case_root):
            render.render_page(model, site)
        assert (site / "us_stocks_lab.html").is_file()
        sites[name] = site
    print(json.dumps({"phase":"actual_render_fixtures_ready","out":str(out)}), flush=True)
    blocked = set()
    served = set()

    def route_request(route):
        parsed = urlparse(route.request.url)
        parts = unquote(parsed.path).strip("/").split("/", 2)
        if parsed.hostname == "127.0.0.1" and len(parts) == 3 and parts[0] == "case" and parts[1] in sites:
            site = sites[parts[1]]
            candidate = (site / parts[2]).resolve()
            if candidate.is_relative_to(site) and candidate.is_file():
                served.add(parts[2])
                route.fulfill(status=200, content_type=mimetypes.guess_type(candidate)[0] or "application/octet-stream", body=candidate.read_bytes())
                return
            asset = (root / "templates" / parts[2]).resolve()
            if asset.is_relative_to(root / "templates") and asset.is_file() and asset.suffix in {".css", ".js", ".woff2", ".woff", ".svg", ".png"}:
                served.add(parts[2])
                hashes[str(asset.relative_to(root))] = hashlib.sha256(asset.read_bytes()).hexdigest()
                route.fulfill(status=200, content_type=mimetypes.guess_type(asset)[0] or "application/octet-stream", body=asset.read_bytes())
                return
        # Existing root-relative shell assets are served from this same tree.
        asset = (root / "templates" / unquote(parsed.path).lstrip("/")).resolve()
        if parsed.hostname == "127.0.0.1" and asset.is_relative_to(root / "templates") and asset.is_file() and asset.suffix in {".css", ".js", ".woff2", ".woff", ".svg", ".png"}:
            served.add(str(asset.relative_to(root / "templates")))
            hashes[str(asset.relative_to(root))] = hashlib.sha256(asset.read_bytes()).hexdigest()
            route.fulfill(status=200, content_type=mimetypes.guess_type(asset)[0] or "application/octet-stream", body=asset.read_bytes())
            return
        blocked.add((parsed.hostname or "") + parsed.path)
        route.abort()

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        version = browser.version
        cells = [(390, "light", "en", "populated")] if args.red_only else [
            (width, theme, lang, state)
            for width in (320, 390, 768, 1024, 1440)
            for theme in ("light", "dark") for lang in ("en", "zh")
            for state in ("populated", "empty", "long-name", "singleton")
            if state not in ("long-name", "singleton") or width in (320, 390)
        ]
        for width, theme, lang, state in cells:
            context = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1,
                                          has_touch=width <= 390, reduced_motion="no-preference")
            context.add_init_script(
                f"localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(lang)});"
                "window.__navScrollCalls=[];const real=Element.prototype.scrollIntoView;"
                "Element.prototype.scrollIntoView=function(opts){window.__navScrollCalls.push({id:this.id,...opts});return real.call(this,opts);};")
            context.route("**/*", route_request)
            page = context.new_page()
            page.set_default_timeout(6000)
            errors = []
            failed_resources = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("requestfailed", lambda req: failed_resources.append({"url":req.url,"type":req.resource_type}))
            page.goto(f"http://127.0.0.1/case/{state}/us_stocks_lab.html", wait_until="load")
            page.evaluate("document.fonts.ready")
            font_proof = page.evaluate("async()=>{const loaded=await document.fonts.load('700 14px Inter');return {faces:loaded.map(f=>({family:f.family,status:f.status})),body:getComputedStyle(document.body).fontFamily};}")
            assert font_proof["faces"] and all(f["status"] == "loaded" for f in font_proof["faces"]), font_proof
            assert "Inter" in font_proof["body"], font_proof
            actual_state = page.evaluate("({theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,background:getComputedStyle(document.body).backgroundColor,panel:getComputedStyle(document.documentElement).getPropertyValue('--panel').trim()})")
            assert actual_state["theme"] == theme and actual_state["lang"] == lang, actual_state
            # The incumbent theme has a later body canvas treatment; assert its
            # unambiguous light/dark panel token, not an earlier --bg fallback.
            assert page.locator("html.soft-contrast").count() == 1, "Incumbent theme.js must actually initialize"
            assert actual_state["panel"] == ("#ffffff" if theme == "light" else "#151820"), actual_state
            original_url = page.url
            tab = lambda name: page.locator(f'.pl-tabs [data-tab="{name}"]')
            assert tab("scoreboard").inner_text().strip() == ("Scoreboard" if lang == "en" else "记分板")

            if args.red_only:
                failures = []
                if page.locator('.pl-tabs [aria-selected="true"]').count() != 1:
                    failures.append("selected-tab state absent")
                tab("scoreboard").focus()
                page.keyboard.press("ArrowRight")
                if page.locator('.pl-tabs .on').get_attribute("data-tab") != "velocity":
                    failures.append("ArrowRight does not activate next section")
                page.emulate_media(reduced_motion="reduce")
                origin = page.locator(f'.book-drill[data-ab="{fixture.ENTRY}"]').first
                origin.focus()
                page.keyboard.press("Enter")
                focus = page.evaluate("({tag:document.activeElement.tagName,visible:!!document.activeElement.getClientRects().length,bookFocus:document.activeElement.hasAttribute('data-book-focus')})")
                if not focus["bookFocus"]:
                    failures.append("book drill has no visible destination focus")
                calls = page.evaluate("window.__navScrollCalls")
                if calls and calls[-1]["behavior"] == "smooth":
                    failures.append("reduced-motion drill still requests smooth scrolling")
                evidence = {"fixture_only": True, "source_hashes": hashes, "browser": version,
                            "observed_failures": failures, "focus_after_drill": focus, "scroll_calls": calls,
                            "page_errors": errors}
                (out / "red-browser-proof.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
                page.screenshot(path=str(out / "red-drill.png"), animations="disabled")
                assert len(failures) == 4, evidence
                print(json.dumps({"red_reproduced": failures, "out": str(out)}), flush=True)
                context.close()
                break

            def check_active(name):
                assert page.locator('.pl-tabs [aria-selected="true"]').count() == 1
                assert tab(name).get_attribute("aria-selected") == "true"
                assert tab(name).get_attribute("tabindex") == "0"
                assert page.locator('[data-tab-panel]:visible').count() == 1
                panel = page.locator(f'[data-tab-panel="{name}"]')
                assert panel.is_visible() and panel.get_attribute("hidden") is None
                assert panel.get_attribute("aria-labelledby") == tab(name).get_attribute("id")
                for other in fixture.TABS:
                    assert tab(other).get_attribute("tabindex") == ("0" if other == name else "-1")
                    assert tab(other).get_attribute("aria-selected") == ("true" if other == name else "false")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), (width, state, name, "page overflow")

            check_active("scoreboard")
            tab("scoreboard").focus()
            page.keyboard.press("ArrowLeft")
            check_active("method")
            assert tab("method").evaluate("e=>e===document.activeElement")
            page.keyboard.press("ArrowRight")
            check_active("scoreboard")
            page.keyboard.press("End")
            check_active("method")
            page.keyboard.press("Home")
            check_active("scoreboard")
            owned_ids = page.locator('.pl-tabs [id], [data-tab-panel], #ab-chips [id], .ab-panel').evaluate_all("els=>els.map(e=>e.id)")
            assert len(owned_ids) == len(set(owned_ids)) and all(owned_ids)
            for key, delta in (("ArrowRight", 1), ("ArrowLeft", -1)):
                for step in range(1, len(fixture.TABS) + 1):
                    page.keyboard.press(key)
                    name = fixture.TABS[(step * delta) % len(fixture.TABS)]
                    check_active(name)
                    assert tab(name).evaluate("e=>e===document.activeElement")
            for i, name in enumerate(fixture.TABS):
                tab(name).focus()
                page.keyboard.press("Enter" if i % 2 == 0 else "Space")
                check_active(name)
            tab("scoreboard").focus()
            page.keyboard.press("Enter")
            page.keyboard.press("Tab")
            assert page.locator('[data-tab-panel="scoreboard"]').evaluate("e=>e===document.activeElement")

            # Touch/pointer still shares the same selected-state path.
            (tab("allbooks").tap if width <= 390 else tab("allbooks").click)()
            check_active("allbooks")
            book_count = page.locator('#ab-chips .book-chip').count()
            if book_count:
                chips = page.locator('#ab-chips .book-chip')
                chips.first.focus()
                page.keyboard.press("End")
                assert chips.last.get_attribute("aria-selected") == "true"
                assert chips.last.evaluate("e=>e===document.activeElement")
                page.keyboard.press("ArrowRight")
                assert chips.first.get_attribute("aria-selected") == "true"
                page.keyboard.press("ArrowRight")
                assert chips.nth(1 % book_count).get_attribute("aria-selected") == "true"
                page.keyboard.press("Home")
                assert chips.first.get_attribute("aria-selected") == "true"
                for key, delta in (("ArrowRight", 1), ("ArrowLeft", -1)):
                    for step in range(1, book_count + 1):
                        page.keyboard.press(key)
                        expected = step * delta % book_count
                        assert chips.nth(expected).get_attribute("aria-selected") == "true"
                        assert chips.nth(expected).evaluate("e=>e===document.activeElement")
                        assert chips.evaluate_all("els=>els.filter(e=>e.tabIndex===0&&e.getAttribute('aria-selected')==='true').length") == 1
                        assert page.locator('.ab-panel:visible').count() == 1
                # Two independently owned book destinations and live motion changes.
                for eid, destination in ((fixture.ENTRY, "allbooks"), (fixture.LONG_HOLD, "longhold")):
                    history_selector = ("#ab-" if destination == "allbooks" else "#lh-") + eid + " .all-fires-details"
                    history_before = page.locator(history_selector).text_content()
                    for motion in ("no-preference", "reduce", "no-preference"):
                        page.emulate_media(reduced_motion=motion)
                        tab("scoreboard").click()
                        trigger = page.locator(f'.book-drill[data-ab="{eid}"]').first
                        trigger.focus()
                        calls_before = page.evaluate("window.__navScrollCalls.length")
                        page.keyboard.press("Enter")
                        check_active(destination)
                        target = page.locator(("#ab-" if destination == "allbooks" else "#lh-") + eid)
                        assert target.locator('[data-book-focus]').evaluate("e=>e===document.activeElement")
                        assert target.locator('.all-fires-details').get_attribute("open") is not None
                        assert target.locator('.all-fires-details').text_content() == history_before
                        assert page.evaluate("window.__navScrollCalls.at(-1).behavior") == ("instant" if motion == "reduce" else "smooth")
                        scroll = page.evaluate("window.__navScrollCalls.at(-1)")
                        assert scroll["id"] == target.get_attribute("id")
                        assert page.evaluate("window.__navScrollCalls.length") == calls_before + 1
                        assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches") is (motion == "reduce")
                        heading = target.locator('[data-book-focus]')
                        if motion == "reduce":
                            assert heading.evaluate("e=>{const b=e.getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight;}")
                        # Wait for the actual smooth scroll, not a replacement scroll.
                        assert heading.evaluate("async e=>{let last=null,stable=0;for(let i=0;i<180;i++){await new Promise(requestAnimationFrame);const b=e.getBoundingClientRect();stable=last!==null&&Math.abs(last-b.top)<0.25?stable+1:0;last=b.top;if(stable>=4&&b.top>=0&&b.bottom<=innerHeight)return true;}return false;}")
                # A missing destination cannot hide its own trigger or manufacture success.
                tab("scoreboard").click()
                trigger = page.locator(f'.book-drill[data-ab="{fixture.ENTRY}"]').first
                trigger.evaluate("e=>e.setAttribute('data-ab','absent-book')")
                trigger = page.locator('.book-drill[data-ab="absent-book"]').first
                trigger.focus()
                calls_before = page.evaluate("window.__navScrollCalls.length")
                page.keyboard.press("Enter")
                check_active("scoreboard")
                assert trigger.evaluate("e=>e===document.activeElement")
                assert page.evaluate("window.__navScrollCalls.length") == calls_before
                trigger.evaluate(f"e=>e.setAttribute('data-ab',{json.dumps(fixture.ENTRY)})")

            page.emulate_media(reduced_motion="reduce")
            tab("allbooks").focus()
            page.keyboard.press("Enter")
            motion_style = tab("allbooks").evaluate("e=>({duration:getComputedStyle(e).transitionDuration,property:getComputedStyle(e).transitionProperty,reduced:matchMedia('(prefers-reduced-motion: reduce)').matches})")
            assert all(float(v.strip().removesuffix("s")) == 0 for v in motion_style["duration"].split(",")), motion_style
            page.locator('.pl-tabs').scroll_into_view_if_needed()
            filename = f"navigation-{state}-{width}-{theme}-{lang}.png"
            page.locator('.pl-tabs').screenshot(path=str(out / filename), animations="disabled")
            measurements = page.locator('.pl-tabs .tabbtn').evaluate_all("els=>els.map(e=>{const b=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.innerText,width:b.width,height:b.height,left:b.left,right:b.right,top:b.top,outline:s.outlineStyle,outlineWidth:s.outlineWidth,color:s.color,background:s.backgroundColor};})")
            assert all(m["height"] >= 44 and m["width"] >= 44 and m["left"] >= -1 and m["right"] <= width+1 for m in measurements), measurements
            assert measurements[2]["outline"] != "none" and float(measurements[2]["outlineWidth"].removesuffix("px")) >= 2
            if (width, lang) in ((320, "zh"), (390, "en"), (390, "zh")):
                assert len({round(m["top"]) for m in measurements}) <= 2, measurements
            for m in measurements:
                m["text_contrast"] = contrast(m["color"], m["background"])
                assert m["text_contrast"] >= 4.5, m
            if book_count:
                sizes = page.locator('#ab-chips .book-chip').evaluate_all("els=>els.map(e=>{const b=e.getBoundingClientRect();return [b.height,b.width,b.left,b.right];})")
                assert all(h >= 44 and w >= 44 and l >= -1 and r <= width+1 for h,w,l,r in sizes), (state, sizes)
            if (width, theme, lang, state) in ((320,"dark","zh","populated"),(390,"light","en","long-name"),(1440,"light","en","populated")):
                page.screenshot(path=str(out / f"page-{state}-{width}-{theme}-{lang}.png"), full_page=True, animations="disabled")
            assert page.url == original_url, "Local tab state must not invent navigation"
            assert not errors, errors
            assert not [r for r in failed_resources if r["type"] in ("stylesheet", "script", "font")], failed_resources
            results.append({"width":width,"theme":theme,"lang":lang,"state":state,"book_count":book_count,
                            "keyboard_touch_selection_focus_motion":"PASS","screenshot":filename,"tabs":measurements,
                            "page_errors":errors,"no_page_overflow":True,"no_url_mutation":True,
                            "actual_theme_locale":actual_state,"font_proof":font_proof,"failed_nonessential_requests":failed_resources})
            print(json.dumps({"passed_cell":[width,theme,lang,state]}), flush=True)
            context.close()
        browser.close()
    if not args.red_only:
        assert len(results) == 56
        for relative, digest in hashes.items():
            content = subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=root) if relative == "site/live_config.js" else (root / relative).read_bytes()
            assert hashlib.sha256(content).hexdigest() == digest, (relative, "source changed during capture")
        report = {"fixture_only":True,"browser":version,"source_hashes":hashes,"case_count":len(results),
                  "blocked_requests":sorted(blocked),"served_assets":sorted(served),"results":results,
                  "runner_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (out / "browser-proof.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print(json.dumps({"case_count":len(results),"out":str(out),"page_errors":0}),flush=True)


if __name__ == "__main__":
    main()
