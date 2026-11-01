"""Slow-chain immediate-hover capture for the nav pre-hydration barrier fix.

Serves the PR worktree's site/ over loopback and delays nav_market.js to
simulate the slow theme.js -> account.js -> nav_market.js chain.

Pages:
  * chat.html is a COMMITTED page that already carries the barrier script
    (the synced generated-header pair), so it is the real shipped state.
  * macro.html on disk is the pre-estate-render page (no barrier script —
    that lands with the nightly render). It is captured twice:
      - CONTROL: as committed, showing the legacy flash this fix removes.
      - TREATED: with the barrier script from templates/_navlinks.html.j2
        spliced in before the nav stylesheet link — byte-for-byte what the
        estate render emits from the changed partial.

Checks: zero legacy frames during the whole pre-boot window (rAF-sampled) on
1440 dark/light EN, 1440 dark ZH, 390 mobile, immediate keyboard focus; mega
menu opens promptly after boot; fallbacks (nav_market.js blocked -> onerror
lift; account.js blocked -> theme.js onerror lift; JS disabled -> no barrier,
legacy usable).
"""
import functools
import http.server
import json
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

WT = Path("/home/ubuntu2/src/macro/.claude/worktrees/nav-mega-flash-20261030")
SITE = WT / "site"
OUT = Path("/tmp/nav-flash-evidence")
PORT = 8795
BASE = f"http://127.0.0.1:{PORT}"

# The barrier script exactly as the changed partial renders it (no jinja inside).
PARTIAL = (WT / "templates" / "_navlinks.html.j2").read_text(encoding="utf-8")
BARRIER_SCRIPT = PARTIAL.split("<script>", 1)[1].split("</script>", 1)[0]
BARRIER_BLOCK = "<script>" + BARRIER_SCRIPT + "</script>"
NAV_CSS_LINK_MARKER = '<link rel="stylesheet" href="navigation-refresh.css'

NAV_DELAY = 4.0

RESULTS = []


def log(msg):
    print(msg, flush=True)


def record(name, ok, detail, shot=None):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail, "shot": shot})
    log(("ok   " if ok else "FAIL ") + name + " :: " + detail)


class RewritingServer(http.server.SimpleHTTPRequestHandler):
    """Serves site/, splicing the partial's barrier script into macro.html
    (the estate-render state), delaying nav_market.js by NAV_DELAY seconds
    (threaded server — other requests proceed while it stalls), and stamping
    nothing else."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path == "/macro.html.treated":
            body = (SITE / "macro.html").read_text(encoding="utf-8")
            idx = body.index(NAV_CSS_LINK_MARKER)
            body = body[:idx] + "    " + BARRIER_BLOCK + "\n" + body[idx:]
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path.endswith("/nav_market.js"):
            time.sleep(NAV_DELAY)
        return super().do_GET()


def serve():
    handler = functools.partial(RewritingServer, directory=str(SITE))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def base_routes(context, nav_market="delay", nav_delay_ms=4000, block_account=False):
    """The nav_market.js stall lives in the threaded server (NAV_DELAY), not in
    this handler — a time.sleep here would block Playwright's sync event loop
    and push every subsequent page call past the boot. Aborts stay here."""

    def route(route):
        url = route.request.url
        if block_account and "account.js" in url:
            return route.abort()
        if nav_market == "abort" and "nav_market.js" in url:
            return route.abort()
        if url.startswith(BASE):
            return route.continue_()
        return route.abort()

    context.route("**/*", route)


US_DD = ".site-nav .nav-links > .nav-dd:first-of-type"
US_TRIG = US_DD + " > a.nav-link"

SAMPLE_JS = """
async (ms) => {
  const dd = document.querySelector('.site-nav .nav-links > .nav-dd:first-of-type');
  const menu = dd.querySelector(':scope > .nav-dd-menu');
  const frames = [];
  const t0 = performance.now();
  await new Promise((done) => {
    (function tick() {
      const cs = getComputedStyle(menu);
      frames.push({
        t: Math.round(performance.now() - t0),
        display: cs.display,
        isMega: menu.classList.contains('nav-market-menu'),
        barrier: document.documentElement.classList.contains('mdx-nav-boot'),
      });
      if (performance.now() - t0 >= ms) done(); else requestAnimationFrame(tick);
    })();
  });
  return frames;
}
"""


def legacy_frames(frames):
    return [f for f in frames if f["display"] != "none" and not f["isMega"]]


def wait_boot(page, timeout=15000):
    page.wait_for_function(
        "() => !document.documentElement.classList.contains('mdx-nav-boot')"
        " && document.querySelector('.nav-market-menu') !== null",
        timeout=timeout,
    )


def chained_scenario(browser, name, path, *, theme, lang, shots, viewport=None):
    kw = {"viewport": viewport or {"width": 1440, "height": 900}}
    ctx = browser.new_context(**kw)
    page = ctx.new_page()
    page.add_init_script(
        "try{localStorage.setItem('theme',%s);localStorage.setItem('lang',%s);}catch(e){}"
        % (json.dumps(theme), json.dumps(lang))
    )
    base_routes(ctx, "delay", 4000)
    page.goto(BASE + path, wait_until="domcontentloaded")
    page.wait_for_selector(".site-nav .nav-links", state="attached")
    page.hover(US_TRIG)
    frames = page.evaluate(SAMPLE_JS, 1500)
    bad = legacy_frames(frames)
    record(
        f"{name}: zero legacy frames while chained (rAF-sampled 1.5s)",
        not bad and frames[0]["barrier"],
        "barrier=%s displays=%s frames=%d bad=%d"
        % (frames[0]["barrier"], sorted(set(f["display"] for f in frames)), len(frames), len(bad)),
    )
    page.screenshot(path=str(OUT / shots[0]))
    wait_boot(page)
    page.hover(US_TRIG)
    page.wait_for_timeout(400)
    disp = page.evaluate(
        "getComputedStyle(document.querySelector('%s > .nav-dd-menu')).display" % US_DD
    )
    is_mega = page.evaluate(
        "document.querySelector('%s > .nav-dd-menu').classList.contains('nav-market-menu')" % US_DD
    )
    record(
        f"{name}: mega menu open after boot",
        disp == "grid" and is_mega,
        "display=%s isMega=%s" % (disp, is_mega),
    )
    page.screenshot(path=str(OUT / shots[1]))
    ctx.close()


def control_scenario(browser):
    """Pre-estate-render macro.html: the legacy flash this fix removes."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    base_routes(ctx, "delay", 4000)
    page.goto(BASE + "/macro.html", wait_until="domcontentloaded")
    page.wait_for_selector(".site-nav .nav-links", state="attached")
    page.hover(US_TRIG)
    frames = page.evaluate(SAMPLE_JS, 1500)
    bad = legacy_frames(frames)
    record(
        "CONTROL (pre-render macro.html): legacy menu paints during the chain",
        bool(bad) and not frames[0]["barrier"],
        "barrier=%s bad_frames=%d/%d displays=%s"
        % (frames[0]["barrier"], len(bad), len(frames), sorted(set(f["display"] for f in frames))),
    )
    page.screenshot(path=str(OUT / "control_pre_fix_legacy_flash.png"))
    ctx.close()


def keyboard_scenario(browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    base_routes(ctx, "delay", 4000)
    page.goto(BASE + "/chat.html", wait_until="domcontentloaded")
    page.wait_for_selector(".site-nav .nav-links", state="attached")
    page.evaluate("document.querySelector('%s').focus()" % US_TRIG)
    page.wait_for_timeout(150)
    frames = page.evaluate(SAMPLE_JS, 1200)
    bad = legacy_frames(frames)
    record(
        "keyboard: immediate focus shows no legacy menu",
        not bad and frames[0]["barrier"],
        "barrier=%s bad=%d" % (frames[0]["barrier"], len(bad)),
    )
    page.screenshot(path=str(OUT / "kb_preboot.png"))
    wait_boot(page)
    page.evaluate("document.querySelector('%s').focus()" % US_TRIG)
    page.wait_for_timeout(400)
    disp = page.evaluate(
        "getComputedStyle(document.querySelector('%s > .nav-dd-menu')).display" % US_DD
    )
    record("keyboard: mega menu opens on focus after boot", disp == "grid", "display=%s" % disp)
    page.screenshot(path=str(OUT / "kb_postboot.png"))
    ctx.close()


def mobile_scenario(browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    base_routes(ctx, "delay", 4000)
    page.goto(BASE + "/chat.html", wait_until="domcontentloaded")
    page.wait_for_selector(".site-nav .nav-links", state="attached")
    page.tap(".site-nav .nav-toggle")
    page.wait_for_timeout(200)
    page.tap(US_TRIG)
    frames = page.evaluate(SAMPLE_JS, 1500)
    bad = legacy_frames(frames)
    record(
        "mobile 390: immediate accordion tap shows no legacy menu",
        not bad and frames[0]["barrier"],
        "barrier=%s bad=%d" % (frames[0]["barrier"], len(bad)),
    )
    page.screenshot(path=str(OUT / "mobile_preboot.png"))
    wait_boot(page)
    page.tap(US_TRIG)
    page.wait_for_timeout(500)
    disp = page.evaluate(
        "getComputedStyle(document.querySelector('%s > .nav-dd-menu')).display" % US_DD
    )
    record(
        "mobile 390: mega accordion opens after boot",
        disp in ("block", "grid"),
        "display=%s" % disp,
    )
    page.screenshot(path=str(OUT / "mobile_postboot.png"))
    ctx.close()


def fallback_nav_market_blocked(browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    base_routes(ctx, "abort")
    page.goto(BASE + "/chat.html", wait_until="domcontentloaded")
    page.wait_for_selector(".site-nav .nav-links", state="attached")
    page.wait_for_function(
        "() => !document.documentElement.classList.contains('mdx-nav-boot')", timeout=8000
    )
    page.hover(US_TRIG)
    page.wait_for_timeout(300)
    disp = page.evaluate(
        "getComputedStyle(document.querySelector('%s > .nav-dd-menu')).display" % US_DD
    )
    is_legacy = page.evaluate(
        "!document.querySelector('%s > .nav-dd-menu').classList.contains('nav-market-menu')" % US_DD
    )
    record(
        "fallback: nav_market.js blocked -> onerror lift, legacy menu usable",
        disp == "block" and is_legacy,
        "display=%s legacy=%s" % (disp, is_legacy),
    )
    page.screenshot(path=str(OUT / "fallback_nav_market_blocked.png"))
    ctx.close()


def fallback_account_blocked(browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    base_routes(ctx, "delay", 4000, block_account=True)
    page.goto(BASE + "/chat.html", wait_until="domcontentloaded")
    page.wait_for_selector(".site-nav .nav-links", state="attached")
    page.wait_for_function(
        "() => !document.documentElement.classList.contains('mdx-nav-boot')", timeout=8000
    )
    page.hover(US_TRIG)
    page.wait_for_timeout(300)
    disp = page.evaluate(
        "getComputedStyle(document.querySelector('%s > .nav-dd-menu')).display" % US_DD
    )
    record(
        "fallback: account.js blocked -> theme.js onerror lift, legacy menu usable",
        disp == "block",
        "display=%s" % disp,
    )
    page.screenshot(path=str(OUT / "fallback_account_blocked.png"))
    ctx.close()


def no_js(browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, java_script_enabled=False)
    page = ctx.new_page()
    page.goto(BASE + "/chat.html", wait_until="domcontentloaded")
    # get_attribute reads via CDP DOM, not page JS (which is disabled here).
    root_class = page.query_selector("html").get_attribute("class") or ""
    legacy_menu = page.query_selector(".site-nav .nav-links > .nav-dd:first-of-type > .nav-dd-menu")
    record(
        "no-JS: barrier class never armed, legacy nav markup present",
        "mdx-nav-boot" not in root_class and legacy_menu is not None,
        "html_class=%r legacy_menu_present=%s" % (root_class, legacy_menu is not None),
    )
    page.hover(US_TRIG)
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "no_js_legacy_usable.png"))
    ctx.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    httpd = serve()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            control_scenario(browser)
            chained_scenario(browser, "treated macro 1440 dark EN", "/macro.html.treated",
                             theme="dark", lang="en",
                             shots=("desktop_dark_en_preboot.png", "desktop_dark_en_postboot.png"))
            chained_scenario(browser, "treated macro 1440 light EN", "/macro.html.treated",
                             theme="light", lang="en",
                             shots=("desktop_light_en_preboot.png", "desktop_light_en_postboot.png"))
            chained_scenario(browser, "treated macro 1440 dark ZH", "/macro.html.treated",
                             theme="dark", lang="zh",
                             shots=("desktop_dark_zh_preboot.png", "desktop_dark_zh_postboot.png"))
            keyboard_scenario(browser)
            mobile_scenario(browser)
            fallback_nav_market_blocked(browser)
            fallback_account_blocked(browser)
            no_js(browser)
            browser.close()
    finally:
        httpd.shutdown()
    (OUT / "RESULTS.json").write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    failed = [r for r in RESULTS if not r["ok"]]
    log("\n%d checks, %d failed" % (len(RESULTS), len(failed)))
    for r in failed:
        log("FAILED: %s :: %s" % (r["name"], r["detail"]))


if __name__ == "__main__":
    main()
