"""D03 T42 focused browser proof over retained actual-producer/actual-builder bytes."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import mimetypes
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

LIVE_CONFIG = "/* Synthetic fixture: live overlays disabled; production key contract. */\nwindow.LIVE_QUOTES_URL='';window.LIVE_SNAPSHOT_URL='';window.LIVE_POLL_SEC=60;window.LIVE_STALE_MIN=20;window.LIVE_DELAYED_MIN=0;window.LIVE_FEED_LABEL='';window.LIVE_FEED_LABEL_ZH='';window.LIVE_WS_TAPE=false;window.LIVE_ENABLED=false;\n"
TIERS = {"primary": "six-month", "r63": "three-month", "atrz": "above-trend"}
STATES = {
    "extended_healthy": ("running", "Still running", "仍在延续"),
    "extended_watch": ("wear", "Showing wear", "势头转弱"),
    "thinning": ("thinning", "Thinning out", "买盘转薄"),
    "breaking": ("changed", "Character changed", "走势已变"),
    "no_read": ("noread", "Not enough to compare", "无可比样本"),
}

def require(value, message):
    if not value:
        raise AssertionError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def group_id(key, state):
    slug = STATES[state][0]
    return ("g-" if key == "primary" else TIERS[key] + "-") + slug

def normalized(text):
    return " ".join(text.split())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--evidence", type=Path, required=True)
    args = ap.parse_args()
    root, out = args.root.resolve(), args.evidence.resolve()
    require(not (out / "browser-proof.json").exists(), "preserve existing browser proof")
    report = json.loads((out / "producer-proof.json").read_text())
    require(report["producer_runs"] == 2 and report["product_source_unchanged"], "producer receipt missing")
    for path, expected in report["source_hashes"].items():
        require(digest(root / path) == expected, "source changed: " + path)
    rendered, cases = {}, {}
    for name, receipt in report["cases"].items():
        artifact = out / name / "consumer-artifact.json"
        require(digest(artifact) == receipt["consumer_artifact_sha256"], "artifact binding drift")
        cases[name] = json.loads(artifact.read_text())
        rendered[name] = gzip.decompress((out / name / "rendered.html.gz").read_bytes())
        require(hashlib.sha256(rendered[name]).hexdigest() == receipt["rendered_html_sha256"],
                "rendered-byte binding drift")
    shots = out / "screenshots"
    shots.mkdir(exist_ok=True)
    from playwright.sync_api import sync_playwright
    assets, stubs, missing, external = {}, set(), set(), set()
    def route_request(route):
        parsed = urlparse(route.request.url)
        if parsed.hostname != "127.0.0.1":
            external.add(parsed.hostname + parsed.path)
            route.abort()
            return
        path = unquote(parsed.path).removeprefix("/case/").lstrip("/")
        if path.endswith(".html") and path[:-5] in rendered:
            route.fulfill(status=200, content_type="text/html; charset=utf-8",
                          body=rendered[path[:-5]])
            return
        if path == "live_config.js":
            route.fulfill(status=200, content_type="text/javascript", body=LIVE_CONFIG)
            return
        for source_root in (root / "templates", root / "site"):
            asset = (source_root / path).resolve()
            if asset.is_relative_to(source_root) and asset.is_file() and asset.suffix in {
                    ".css", ".js", ".woff2", ".woff", ".ttf", ".svg", ".png", ".jpg", ".ico"}:
                assets[str(asset.relative_to(root))] = digest(asset)
                route.fulfill(status=200,
                    content_type=mimetypes.guess_type(asset)[0] or "application/octet-stream",
                    body=asset.read_bytes())
                return
        if parsed.path.endswith(".json"):
            stubs.add(parsed.path)
            route.fulfill(status=200, content_type="application/json", body="{}")
            return
        missing.add(parsed.path)
        route.fulfill(status=404, content_type="text/plain", body="Missing fixture asset")
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        version = browser.version
        for name in cases:
            for width in (320, 1440):
                for theme in ("light", "dark"):
                    for lang in ("en", "zh"):
                        label = f"{name}-{width}-{theme}-{lang}"
                        ctx = cases[name]
                        mobile = width == 320
                        context = browser.new_context(viewport={"width": width, "height": 900},
                            device_scale_factor=1, is_mobile=mobile, has_touch=mobile)
                        context.add_init_script(
                            f"localStorage.setItem('theme',{json.dumps(theme)});"
                            f"localStorage.setItem('lang',{json.dumps(lang)});")
                        context.route("**/*", route_request)
                        page = context.new_page()
                        page.set_default_timeout(6000)
                        errors = []
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        result = {"case": label, "producer_case": name, "width": width,
                                  "theme": theme, "lang": lang, "status": "FAIL"}
                        chosen = (width == 320 and theme == "light" and lang == "en") or (
                                  width == 1440 and theme == "dark" and lang == "zh")
                        try:
                            page.goto(f"http://127.0.0.1/case/{name}.html", wait_until="load")
                            page.evaluate("document.fonts.ready")
                            require(page.locator("html").get_attribute("data-lang") == lang, "language")
                            require(page.locator("html").get_attribute("data-theme") == theme, "theme")
                            page.wait_for_function("""() => [...document.querySelectorAll('.rise')]
                                .every(e => Number(getComputedStyle(e).opacity)>0.99)""")
                            require(page.locator(".hero > .shelf > .sh-row").count() == 3,
                                    "shelf must contain only three independent cohort rows")
                            ids = page.locator("section.tier").evaluate_all("es=>es.map(e=>e.id)")
                            require(ids == ["t-" + slug for slug in TIERS.values()], "tier display order")
                            hero = normalized(page.locator(".hero-lede").inner_text())
                            require(("counts do not add up to a total" if lang == "en" else "这些数字不能相加")
                                    in hero, "visible no-summed-total disclosure")
                            require(("each read against its own history" if lang == "en" else "各自对照自身历史")
                                    in hero, "visible cohort independence")
                            require(("in the last 21 sessions" if lang == "en" else "最近 21 个交易日内")
                                    in hero, "producer's actual membership window not disclosed")
                            require(("only as Character changed" if lang == "en" else "只会列在「走势已变」")
                                    in hero, "off-band retention disclosure")
                            if chosen:
                                page.screenshot(path=str(shots / (label + "-shelf.png")))
                            observations, navigation = {}, []
                            for index, tier in enumerate(ctx["tiers"]):
                                key, slug = tier["key"], TIERS[tier["key"]]
                                shelf = page.locator(".hero > .shelf > .sh-row").nth(index)
                                require(shelf.get_attribute("href") == "#t-" + slug, "shelf anchor mismatch")
                                actual_count = int(shelf.locator(".sh-n b:visible").inner_text())
                                require(actual_count == tier["extended_n"], "cohort shelf denominator")
                                shelf_text = normalized(shelf.inner_text())
                                off_band = ctx["_diagnostics"]["tiers"][key]["n_off_band_on_board"]
                                off_phrase = "no longer clear the bar today" if lang == "en" else "今天已不再达到门槛"
                                require((off_phrase in shelf_text) == (off_band > 0),
                                        "retained off-band count is not cohort-specific")
                                shelf.tap() if mobile else shelf.click()
                                page.wait_for_function("(h)=>location.hash===h", arg="#t-" + slug)
                                section = page.locator("#t-" + slug)
                                section.locator(".tier-hd h2").wait_for(state="visible")
                                navigation.append({"tier": key, "hash": page.evaluate("location.hash"),
                                                   "input": "touchscreen tap" if mobile else "mouse click"})
                                observed_states = {}
                                expected_ids = []
                                for state, values in tier["states"].items():
                                    gid = group_id(key, state)
                                    group = page.locator("#" + gid)
                                    if not values:
                                        require(group.count() == 0, "empty state should not fabricate a section")
                                        continue
                                    expected_ids.append(gid)
                                    require(group.count() == 1, "state group missing")
                                    heading = normalized(group.locator(".grp-hd h2").inner_text())
                                    require(heading == STATES[state][1 if lang == "en" else 2],
                                            "visible state label does not match producer state")
                                    names = group.locator(".row .tk").all_text_contents()
                                    expected_names = [r["ticker"] for r in values]
                                    require(names == expected_names, "cohort/state row order differs from producer")
                                    require(group.locator(".row a.tk").count() == 0,
                                            "fixture must not invent destination pages")
                                    if state == "no_read":
                                        require(group.locator(".wear").count() == 0, "unreadable row wears a clear mark")
                                        require(group.locator(".lens-term.lib").count() == 0,
                                                "unreadable row has analogue opener")
                                    observed_states[state] = {"heading": heading, "tickers": names}
                                actual_groups = section.locator(".grp").evaluate_all("es=>es.map(e=>e.id)")
                                expected_order = [group_id(key, s) for s in STATES if tier["states"][s]]
                                require(actual_groups == expected_order, "state groups lost fixed sequence")
                                observations[key] = {"shelf_count": actual_count, "shelf_text": shelf_text,
                                                     "states": observed_states}
                            primary = observations["primary"]["states"]
                            r63 = observations["r63"]["states"]
                            require("AAA" in r63["extended_watch"]["tickers"],
                                    "AAA widened-cohort state disappeared")
                            if name == "readable":
                                require("AAA" in primary["extended_healthy"]["tickers"],
                                        "worst state leaked across cohorts")
                                require("DBRK" in primary["breaking"]["tickers"], "retained breaking control missing")
                                require(not any("DFLT" in x["tickers"] for x in primary.values()),
                                        "off-band nonbreaking leaked into primary")
                            else:
                                require("AAA" in primary["no_read"]["tickers"],
                                        "unreadable positive control became a clean state")
                                require(not any(ticker in x["tickers"] for x in primary.values()
                                                for ticker in ("DBRK", "DFLT")),
                                        "off-band unreadable leaked into primary")
                            require(not any("DOLD" in x["tickers"] for x in primary.values()),
                                    "outside-window name leaked")
                            smallprint = normalized(page.locator(".smallprint").inner_text())
                            require(("counts never add up to a total" if lang == "en" else "各组数字不能相加")
                                    in smallprint, "no-total smallprint missing")
                            geometry = page.evaluate("""() => {
                                const selectors='.hero-lede,.sh-row,.tier-hd,.grp-hd,.row';
                                const over=[...document.querySelectorAll(selectors)].map(e=>{
                                  const r=e.getBoundingClientRect();
                                  return {selector:e.className,left:r.left,right:r.right};
                                }).filter(r=>r.left<-.5 || r.right>innerWidth+.5);
                                return {viewport:innerWidth,
                                  overflow:Math.max(document.documentElement.scrollWidth,
                                                    document.body.scrollWidth)-innerWidth,
                                  blocks_outside_horizontal_viewport:over};
                            }""")
                            require(geometry["overflow"] <= 1 and
                                    not geometry["blocks_outside_horizontal_viewport"],
                                    "cohort content horizontal overflow")
                            if chosen:
                                state = "extended_healthy" if name == "readable" else "no_read"
                                pg = page.locator("#" + group_id("primary", state))
                                pg.scroll_into_view_if_needed()
                                page.screenshot(path=str(shots / (label + "-primary.png")))
                                rg = page.locator("#" + group_id("r63", "extended_watch"))
                                rg.scroll_into_view_if_needed()
                                page.screenshot(path=str(shots / (label + "-r63.png")))
                            require(not errors, "JavaScript errors")
                            result.update(status="PASS", hero=hero, cohorts=observations,
                                          shelf_navigation=navigation, geometry=geometry,
                                          smallprint=smallprint)
                        except Exception as exc:
                            result["error"] = f"{type(exc).__name__}: {exc}"
                            page.screenshot(path=str(shots / (label + "-FAIL.png")))
                        result["javascript_errors"] = errors
                        results.append(result)
                        print(json.dumps({"case": label, "status": result["status"],
                                          "error": result.get("error")}), flush=True)
                        context.close()
        browser.close()
    unchanged = all(digest(root / p) == h for p, h in report["source_hashes"].items())
    result = {
        "task": "D03 T42", "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline": report["baseline"], "checkout_head": report["checkout_head"],
        "producer_report_sha256": digest(out / "producer-proof.json"),
        "browser": "Chromium " + version, "total": len(results),
        "passed": sum(r["status"] == "PASS" for r in results),
        "failed": sum(r["status"] != "PASS" for r in results),
        "source_unchanged": unchanged, "source_hashes": report["source_hashes"],
        "rendered_hashes": {k: hashlib.sha256(v).hexdigest() for k, v in rendered.items()},
        "served_asset_hashes": assets, "stubbed_unrelated_json": sorted(stubs),
        "live_config": {"live_enabled": False, "sha256": hashlib.sha256(LIVE_CONFIG.encode()).hexdigest()},
        "missing_resources": sorted(missing), "external_requests": sorted(external),
        "cases": results,
        "limits": [
            "Actual producer outputs and actual builder bytes; synthetic fixtures with explicit freshness bypass.",
            "Sixteen focused cohort-consumer cases; does not repeat W07 availability or T44 record-card matrix.",
            "Shelf anchors exercised by native browser touch/mouse; no LENS opening or shared-overlay repair claim.",
            "Plain ticker labels are intentional because synthetic fixture has no published stock destinations.",
            "Initial hot-only classifier observation remains preserved and separate; no global engine acceptance.",
            "Not physical Safari, authentication, production data, deployment, W07 composition or user acceptance."
        ],
    }
    (out / "browser-proof.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"phase": "complete", "total": result["total"], "passed": result["passed"],
                      "failed": result["failed"], "missing": sorted(missing), "external": sorted(external),
                      "source_unchanged": unchanged,
                      "report_sha256": digest(out / "browser-proof.json")}), flush=True)
    return 1 if result["failed"] or not unchanged or missing or external else 0

if __name__ == "__main__":
    raise SystemExit(main())
