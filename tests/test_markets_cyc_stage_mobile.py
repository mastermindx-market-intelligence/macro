"""markets.html cycle stage on mobile + the zh regime card (2026-09-23).

Two pre-existing route defects measured by the UD-B2 W4B-2 lane (#7712) and
fixed here:

1. At <=880px cycle.css turns ``.cyc-detail`` into a fixed bottom sheet peeking
   126px. Measured at 390x844 the peek sat on the chip row (``#cyc-chips``) on the
   first screen and, once a market was focused, the expanded sheet covered the whole
   340px chart it was meant to sit under. site/markets.css (loaded by markets.html
   only, after cycle.css) now keeps the detail IN FLOW under the chart, and
   markets_app.js glides the page on focus instead of expanding a sheet. Desktop
   >=881px is untouched.
2. Under ``data-lang="zh"`` ``regField()`` silently fell back to the English
   ``META.regime`` prose whenever markets_i18n.js carried no zh regime block. It now
   renders a Chinese designed-null state; English prose is never shown under zh and
   nothing is machine-translated.

The static assertions run everywhere (CI installs no browser). The DOM-measured
assertions run under Playwright/Chromium when available and skip cleanly
otherwise, following tests/test_macro_command_copy_law.py.
"""
from __future__ import annotations

import functools
import http.server
import json
import re
import socketserver
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
MARKETS_CSS = SITE / "markets.css"
APP_JS = SITE / "markets_app.js"
I18N_JS = SITE / "markets_i18n.js"
DATA_JS = SITE / "markets_data.js"
TEMPLATE = ROOT / "templates" / "markets.html.j2"
PAGE = SITE / "markets.html"

CJK = re.compile(r"[一-鿿]")
LATIN_WORD = re.compile(r"[A-Za-z]{3,}")
NULL_LABEL = "中文精选叙事待更新"
NULL_STAT_NOTE = "中文注释待更新"
MOBILE = (390, 844)
DESKTOP = (1440, 900)

MEASURE = """() => {
  const box = s => { const b = document.querySelector(s).getBoundingClientRect();
    return {top: b.top, bottom: b.bottom, left: b.left, right: b.right, width: b.width, height: b.height}; };
  const det = document.getElementById('cyc-detail');
  const text = s => { const e = document.querySelector(s); return e ? e.textContent.trim() : null; };
  return {
    lang: document.documentElement.getAttribute('data-lang'),
    theme: document.documentElement.getAttribute('data-theme'),
    vw: innerWidth, vh: innerHeight, scrollY: scrollY,
    scrollWidth: document.documentElement.scrollWidth,
    position: getComputedStyle(det).position,
    handle: getComputedStyle(document.getElementById('cyc-handle')).display,
    detail: box('#cyc-detail'), chips: box('#cyc-chips'), chart: box('#cyc-chart'),
    label: text('#cyc-panel-default .rg-label'),
    headline: text('#cyc-panel-default .rg-headline'),
    tilt: text('#cyc-panel-default .rg-tilt'),
    nullChip: !!document.querySelector('#cyc-panel-default .rg-null-chip'),
    headNull: !!document.querySelector('#cyc-panel-default .rg-head.is-null'),
    panelNull: document.getElementById('cyc-panel-default').classList.contains('rg-null'),
    statNotes: Array.from(document.querySelectorAll('#cyc-panel-default .rg-n')).map(e => e.textContent.trim()),
    focusShown: document.getElementById('cyc-panel-focus').classList.contains('show'),
    panelColumns: getComputedStyle(document.querySelector('.cyc-panel.show')).gridTemplateColumns.split(' ').filter(Boolean).length,
  };
}"""


# --- helpers ---------------------------------------------------------------

def _regime_field(text: str, field: str) -> str:
    """First ``"<field>": "..."`` after the top-level ``"regime": {`` of a page asset."""
    start = text.index('"regime": {')
    match = re.search(r'"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(field), text[start:])
    assert match, field
    return json.loads('"' + match.group(1) + '"')


def _mobile_block(css: str) -> str:
    """The markets-only <=880px block that keeps the detail in flow."""
    marker = "never a fixed sheet"
    assert marker in css, "markets.css lost the mobile in-flow detail block"
    start = css.index("@media (max-width: 880px)", css.index(marker))
    end = css.index("\n}\n", start)
    return css[start:end]


def _overlap(a: dict, b: dict) -> float:
    width = min(a["right"], b["right"]) - max(a["left"], b["left"])
    height = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
    return max(0.0, width) * max(0.0, height)


# --- static contracts (run in CI, no browser) --------------------------------

@pytest.mark.needs_full_checkout("site")
def test_markets_css_keeps_the_detail_in_flow_on_mobile():
    block = _mobile_block(MARKETS_CSS.read_text(encoding="utf-8"))
    assert ".cyc-detail, .cyc-detail.expanded {" in block
    for decl in ("position: static", "transform: none", "height: auto", "max-height: none",
                 "box-shadow: var(--card-shadow)"):
        assert decl in block, decl
    assert ".cyc-handle { display: none; }" in block
    # the stage track and the facts grid shrink to the card instead of inflating it
    assert ".cyc-stage { grid-template-columns: minmax(0, 1fr); }" in block
    assert ".cyc-facts .f { min-width: 0; overflow-wrap: anywhere; }" in block


@pytest.mark.needs_full_checkout("site")
def test_markets_css_is_the_last_cycle_family_stylesheet_on_the_page():
    """markets.css must win the cascade over cycle.css's fixed-sheet rule."""
    for path in (TEMPLATE, PAGE):
        text = path.read_text(encoding="utf-8")
        stamped = re.search(r'href="markets\.css\?v=(\d+)"', text)
        assert stamped, path
        # v6: the first live request for ?v=5 reached the edge before the VPS pull and
        # pinned the OLD body under the new key for a year (TencentEdgeOne, immutable).
        assert int(stamped.group(1)) >= 6, path
        assert text.index('href="cycle.css') < stamped.start(), path


@pytest.mark.needs_full_checkout("site")
def test_app_js_never_shows_the_english_regime_prose_under_zh():
    js = APP_JS.read_text(encoding="utf-8")
    assert "RZ && RZ[f] != null ? RZ[f] : META.regime[f]" not in js, "silent English fallback is back"
    body = js[js.index("function regField(f)"):js.index("function buildDefaultPanel")]
    assert 'if (LANG() !== "zh") return META.regime[f];' in body
    zh_branch = body.split('if (LANG() !== "zh")', 1)[1]
    assert "META.regime[f]" not in zh_branch.split(";", 1)[1]
    assert "REG_NULL_ZH[f]" in zh_branch
    start = js.index("var REG_NULL_ZH = {")
    null_block = js[start:js.index("};", start)]
    for key in ("label", "sub", "headline", "tilt", "statNote"):
        match = re.search(key + r':\s*"([^"]*)"', null_block)
        assert match, key
        assert CJK.search(match.group(1)) and not LATIN_WORD.search(match.group(1)), key
    assert 'label: "%s"' % NULL_LABEL in null_block
    assert 'statNote: "%s"' % NULL_STAT_NOTE in null_block
    # stat notes with no zh entry take the null note under zh, not the English note
    assert "(zh ? REG_NULL_ZH.statNote : s.note)" in js
    assert 'def.classList.toggle("rg-null", regIsNullZh());' in js
    # an in-page language toggle rebuilds the card (langchange -> buildDefaultPanel)
    on_lang = js[js.index("function onLangChange"):js.index("/* ---- boot")]
    assert "buildDefaultPanel();" in on_lang


@pytest.mark.needs_full_checkout("site")
def test_app_js_focus_glides_to_the_in_flow_detail():
    js = APP_JS.read_text(encoding="utf-8")
    assert "function revealDetail()" in js
    assert 'getComputedStyle(sheet).position === "fixed"' in js
    assert "prefers-reduced-motion: reduce" in js
    expand = js[js.index("function expandSheet(on)"):js.index("function initSheet")]
    assert "revealDetail();" in expand


@pytest.mark.needs_full_checkout("site")
def test_zh_regime_block_is_hand_curated_chinese():
    zh = I18N_JS.read_text(encoding="utf-8")
    en = DATA_JS.read_text(encoding="utf-8")
    for field in ("label", "sub", "headline", "tilt"):
        value = _regime_field(zh, field)
        assert CJK.search(value), field
        assert value != _regime_field(en, field), field


# --- DOM-measured (Playwright; skips without a browser) ---------------------

@pytest.fixture(scope="module")
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    try:
        manager = sync_playwright()
        playwright = manager.__enter__()
    except Exception as exc:  # pragma: no cover - runtime-specific
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            launched = playwright.chromium.launch(headless=True, channel="chrome")
        except Exception:
            launched = playwright.chromium.launch(headless=True)
    except Exception as exc:
        manager.__exit__(None, None, None)
        pytest.skip(f"Chromium unavailable: {exc}")
    yield launched
    launched.close()
    manager.__exit__(None, None, None)


@pytest.fixture(scope="module")
def site_url():
    if not PAGE.exists():
        pytest.skip("site/ is sparse-omitted")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # noqa: D401 - silence the request log
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(SITE)))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/markets.html"
    finally:
        httpd.shutdown()
        httpd.server_close()


def _null_regime_route(route):
    """Serve the shipped markets_i18n.js with its regime block removed."""
    response = route.fetch()
    route.fulfill(response=response, body=response.text() + "\nwindow.MARKET_I18N.regime = null;\n")


def _open(browser, url: str, lang: str, theme: str, size: tuple[int, int], *, null_regime: bool = False):
    context = browser.new_context(viewport={"width": size[0], "height": size[1]}, reduced_motion="reduce")
    context.add_init_script(
        "try{localStorage.setItem('lang',%s);localStorage.setItem('theme',%s);}catch(e){}"
        % (json.dumps(lang), json.dumps(theme))
    )
    if null_regime:
        context.route("**/markets_i18n.js*", _null_regime_route)
    page = context.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_timeout(800)
    return context, page


@pytest.mark.needs_full_checkout("site")
@pytest.mark.parametrize("theme", ("dark", "light"))
@pytest.mark.parametrize("lang", ("en", "zh"))
def test_mobile_detail_never_covers_the_chip_row_or_the_chart(browser, site_url, lang, theme):
    context, page = _open(browser, site_url, lang, theme, MOBILE)
    try:
        rest = page.evaluate(MEASURE)
        assert (rest["lang"], rest["theme"]) == (lang, theme)
        assert rest["position"] == "static", rest["position"]
        assert rest["handle"] == "none"
        assert _overlap(rest["detail"], rest["chips"]) == 0
        assert _overlap(rest["detail"], rest["chart"]) == 0
        assert rest["detail"]["top"] >= rest["chart"]["bottom"]
        assert rest["scrollWidth"] <= rest["vw"] and rest["detail"]["right"] <= rest["vw"]

        page.click("#cyc-chips button >> nth=0")
        page.wait_for_timeout(600)
        focus = page.evaluate(MEASURE)
        assert focus["focusShown"] and focus["position"] == "static"
        assert _overlap(focus["detail"], focus["chips"]) == 0
        assert _overlap(focus["detail"], focus["chart"]) == 0
        # the glide leaves chart and card sharing the screen: chart fully visible, card head under it
        assert focus["chart"]["top"] >= 0
        assert focus["chart"]["bottom"] <= focus["detail"]["top"] <= focus["vh"]
        assert focus["scrollWidth"] <= focus["vw"] and focus["detail"]["right"] <= focus["vw"]
    finally:
        context.close()


@pytest.mark.needs_full_checkout("site")
def test_desktop_1440_layout_is_untouched(browser, site_url):
    context, page = _open(browser, site_url, "en", "dark", DESKTOP)
    try:
        rest = page.evaluate(MEASURE)
        assert rest["position"] == "static" and rest["handle"] == "none"
        assert rest["detail"]["top"] >= rest["chart"]["bottom"]
        assert rest["panelColumns"] == 12
        assert _overlap(rest["detail"], rest["chart"]) == 0
        page.click("#cyc-chips button >> nth=0")
        page.wait_for_timeout(600)
        focus = page.evaluate(MEASURE)
        assert focus["focusShown"] and focus["position"] == "static"
        assert focus["scrollY"] == 0, "desktop never glides"
        assert focus["panelColumns"] == 12
        assert _overlap(focus["detail"], focus["chart"]) == 0
    finally:
        context.close()


@pytest.mark.needs_full_checkout("site")
@pytest.mark.parametrize("theme", ("dark", "light"))
def test_zh_regime_card_shows_the_curated_chinese_block(browser, site_url, theme):
    zh = I18N_JS.read_text(encoding="utf-8")
    en_label = _regime_field(DATA_JS.read_text(encoding="utf-8"), "label")
    context, page = _open(browser, site_url, "zh", theme, MOBILE)
    try:
        card = page.evaluate(MEASURE)
        assert card["label"] == _regime_field(zh, "label")
        assert card["headline"] == _regime_field(zh, "headline")
        assert CJK.search(card["label"]) and card["label"] != en_label
        assert not card["nullChip"] and not card["headNull"] and not card["panelNull"]
    finally:
        context.close()


@pytest.mark.needs_full_checkout("site")
def test_zh_regime_card_is_a_designed_null_when_the_block_is_missing(browser, site_url):
    en_label = _regime_field(DATA_JS.read_text(encoding="utf-8"), "label")
    context, page = _open(browser, site_url, "zh", "dark", MOBILE, null_regime=True)
    try:
        card = page.evaluate(MEASURE)
        assert card["label"] == NULL_LABEL
        assert card["nullChip"] and card["headNull"] and card["panelNull"]
        for prose in (card["headline"], card["tilt"]):
            assert CJK.search(prose) and not LATIN_WORD.search(prose), prose
        assert card["statNotes"] and all(note == NULL_STAT_NOTE for note in card["statNotes"])
        assert card["label"] != en_label
    finally:
        context.close()
    # the same missing block leaves English untouched
    context, page = _open(browser, site_url, "en", "dark", MOBILE, null_regime=True)
    try:
        card = page.evaluate(MEASURE)
        assert card["label"] == en_label and not card["nullChip"] and not card["panelNull"]
    finally:
        context.close()
