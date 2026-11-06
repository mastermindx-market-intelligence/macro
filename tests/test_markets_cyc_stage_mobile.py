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
import hashlib
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
    template = TEMPLATE.read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    assert 'href="markets.css"' in template
    digest = hashlib.sha256(MARKETS_CSS.read_bytes()).hexdigest()[:8]
    assert f'href="markets.css?v={digest}"' in page
    for text in (template, page):
        assert text.index('href="cycle.css') < text.index('href="markets.css')



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
        page.click("details.rg-context > summary")
        assert page.locator("details.rg-context").get_attribute("open") is not None
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
        page.click("details.rg-context > summary")
        assert page.locator("details.rg-context").get_attribute("open") is not None
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
        page.click("details.rg-context > summary")
        assert page.locator("details.rg-context").get_attribute("open") is not None
        card = page.evaluate(MEASURE)
        assert card["label"] == en_label and not card["nullChip"] and not card["panelNull"]
    finally:
        context.close()


# The original twelve pulse contracts are folded into this registered page owner.
APP = APP_JS
CSS = MARKETS_CSS
BUILT = PAGE



def _function_slice(src: str, name: str) -> str:
    start = src.index(f"function {name}(")
    brace = src.index("{", start)
    depth = 1
    i = brace + 1
    while i < len(src) and depth:
        depth += (src[i] == "{") - (src[i] == "}")
        i += 1
    assert depth == 0, f"unbalanced function {name}"
    return src[start:i]


def test_template_mounts_one_global_regime_pulse():
    src = TEMPLATE.read_text(encoding="utf-8")
    assert src.count('id="global-regime-pulse"') == 1
    assert 'id="global-regime-pulse-label"' in src
    assert 'id="global-regime-pulse-track"' in src
    assert 'id="global-regime-pulse-buckets"' in src


def test_header_is_compact_and_defers_method_detail_below():
    src = TEMPLATE.read_text(encoding="utf-8")
    assert "Eleven national equity markets on one cycle oscillator." in src
    assert "Nine positions are engine-backed" in src
    assert "Observed history (solid), projection (dashed + uncertainty cone)" not in src


def test_global_pulse_uses_cycle_positions_not_us_market_state():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "nowPosOf(c)" in fn
    assert "engPos(c)" in fn
    assert "market_state" not in fn.lower()
    assert "META.regime" not in fn
    assert "regField(" not in fn


def test_global_pulse_reuses_existing_zone_boundaries():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "var highCut = 82;" in fn
    assert "var lowerCut = 42;" in fn
    css = CSS.read_text(encoding="utf-8")
    assert ".grp-track::before { left: 42%; }" in css
    assert ".grp-track::after { left: 82%; }" in css


def test_global_pulse_exposes_mixed_source_provenance():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "engine-backed" in fn
    assert "analyst estimate" in fn
    assert "data-source" in fn


def test_global_pulse_is_interactive_with_existing_focus_path():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "setFocus(" in fn
    assert "data-id" in fn


def test_global_pulse_rerenders_on_boot_and_language_change():
    src = APP.read_text(encoding="utf-8")
    assert _function_slice(src, "boot").count("renderGlobalPulse()") == 1
    assert _function_slice(src, "onLangChange").count("renderGlobalPulse()") == 1


def test_default_panel_no_longer_duplicates_top_level_global_regime():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "buildDefaultPanel")
    assert "Global-equity regime" not in fn
    assert '<details class="cyc-grp cyc-grp-3 rg-context">' in fn
    assert "<details open" not in fn
    assert fn.index("<details") < fn.index("rg-headline") < fn.index("</details>")
    assert "Where the markets stand" in fn


def test_global_pulse_css_has_mobile_reduction_and_no_literal_hex():
    src = CSS.read_text(encoding="utf-8")
    start = src.index("/* ---- global regime pulse")
    end = src.index("/* ---- two-up:", start)
    block = src[start:end]
    assert ".global-regime-pulse" in block
    assert "@media (max-width: 760px)" in block
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", block)


def test_mobile_bucket_groups_scroll_horizontally_instead_of_stacking():
    src = CSS.read_text(encoding="utf-8")
    start = src.index("@media (max-width: 760px)")
    mobile = src[start: src.index("/* ---- two-up:", start)]
    assert ".grp-buckets {" in mobile
    assert "display: flex" in mobile
    assert "overflow-x: auto" in mobile
    assert "scroll-snap-type: x proximity" in mobile
    assert ".grp-bucket {" in mobile
    assert "min-width: 210px" in mobile
    assert "scroll-snap-align: start" in mobile


def test_built_markets_page_contains_global_pulse_when_present():
    if not BUILT.exists():
        return
    html = BUILT.read_text(encoding="utf-8")
    assert html.count('id="global-regime-pulse"') == 1


def test_built_markets_page_keeps_asset_stamps_and_defer_contract():
    """The generated page must pass through optimize_assets before commit.

    A raw template render silently drops cache-busting query stamps and the
    defer contract on local scripts, which is a real publication regression.
    """
    if not BUILT.exists():
        return
    html = BUILT.read_text(encoding="utf-8")
    assert re.search(r'href="theme\.css\?v=[0-9a-f]{8}"', html)
    assert re.search(r'href="markets\.css\?v=[0-9a-f]{8}"', html)
    assert re.search(r'href="navigation-refresh\.css\?v=[0-9a-f]{8}"', html)
    assert re.search(r'src="markets_app\.js\?v=[0-9a-f]{8}" defer', html)
    assert re.search(r'src="theme\.js\?v=[0-9a-f]{8}" defer', html)


def _run_market_functions(names, body, *, lang="en", meta=None, regime=None, cycles=None):
    """Execute the actual page functions with a minimal deterministic DOM."""
    import subprocess

    source = APP_JS.read_text(encoding="utf-8")
    null_start = source.index("  var REG_NULL_ZH = {")
    null_end = source.index("  };", null_start) + len("  };")
    common = [
        "LANG", "t", "zhM", "dz", "shrt", "ageDaysOf", "curatedDateLabel",
        "zhRegime", "regIsNullZh", "regField",
    ]
    functions = "\n".join(_function_slice(source, n) for n in dict.fromkeys(common + names))
    payload = {
        "lang": lang,
        "meta": meta if meta is not None else {
            "asOf": None,
            "regime": {
                "label": "ENGLISH_LABEL", "sub": "ENGLISH_SUB",
                "headline": "ENGLISH_HEADLINE", "tilt": "ENGLISH_TILT",
                "asOfNote": "ENGLISH_DATE_NOTE",
                "stats": [{"k": "RATE", "v": "3", "note": "ENGLISH_NOTE"}],
            },
        },
        "regime": regime,
        "cycles": cycles or [],
    }
    harness = r"""
const input = INPUT;
Date.now = () => Date.parse("2026-11-06T12:00:00Z");
var META=input.meta, I18N={markets:{},regime:input.regime}, CYCLES=input.cycles;
var lang=input.lang, nodes={}, focusCalls=[], scrollCalls=[];
function getNode(id) {
  if (!nodes[id]) nodes[id]={innerHTML:"",textContent:"",classes:new Set(),
    classList:{toggle(c,on){if(on)nodes[id].classes.add(c);else nodes[id].classes.delete(c);},
      add(c){nodes[id].classes.add(c);},remove(c){nodes[id].classes.delete(c);}},
    querySelectorAll(){return [];},getBoundingClientRect(){return {top:500};}};
  return nodes[id];
}
var document={documentElement:{getAttribute(){return lang;}},getElementById:getNode};
var window={innerWidth:390,innerHeight:844,pageYOffset:0,
  matchMedia(){return {matches:true};},scrollTo(x){scrollCalls.push(x);}};
function getComputedStyle(){return {position:"static"};}
function setFocus(id){focusCalls.push(id);}
""".replace("INPUT", json.dumps(payload, ensure_ascii=False))
    proc = subprocess.run(
        ["node", "-e", harness + "\n" + source[null_start:null_end] + "\n" + functions + "\n" + body],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("regime", [
    None, {}, {"label": "精选标签"},
    {"label": "精选标签", "headline": None},
    {"label": "精选标签", "headline": "精选叙事", "tilt": None, "stats": [{"note": None}]},
    {"label": "精选标签", "headline": "精选叙事", "stats": [{}]},
    {"label": "精选标签", "headline": "精选叙事", "sub": None, "stats": [None]},
])
def test_missing_partial_zh_executes_designed_null_without_english_fallback(regime):
    result = _run_market_functions(
        ["buildDefaultPanel"],
        """buildDefaultPanel();
        console.log(JSON.stringify({
          fields:["label","sub","headline","tilt"].map(regField),
          html:getNode("cyc-panel-default").innerHTML,
          isNull:regIsNullZh()
        }));""",
        lang="zh", regime=regime,
    )
    assert all(CJK.search(value) and "ENGLISH_" not in value for value in result["fields"])
    assert "ENGLISH_" not in result["html"]
    assert NULL_STAT_NOTE in result["html"]
    assert result["isNull"] == not_bool_complete_regime(regime)


def not_bool_complete_regime(regime):
    return not (regime and regime.get("label") is not None and regime.get("headline") is not None)


def test_curated_copy_remains_inside_closed_disclosure_with_language_switch():
    from bs4 import BeautifulSoup

    result = _run_market_functions(
        ["buildDefaultPanel"],
        """buildDefaultPanel();
        var en=getNode("cyc-panel-default").innerHTML;
        lang="zh";buildDefaultPanel();
        console.log(JSON.stringify({en:en,zh:getNode("cyc-panel-default").innerHTML}));""",
    )
    en = BeautifulSoup(result["en"], "html.parser")
    zh = BeautifulSoup(result["zh"], "html.parser")
    for panel in (en, zh):
        disclosure = panel.select_one("details.rg-context")
        assert disclosure is not None and not disclosure.has_attr("open")
        assert panel.select_one(".rg-headline").find_parent("details") is disclosure
        assert panel.select_one(".rg-stats").find_parent("details") is disclosure
        assert panel.select_one(".rg-tilt").find_parent("details") is disclosure
    assert en.select_one(".rg-label").get_text() == "ENGLISH_LABEL"
    assert zh.select_one(".rg-label").get_text() == NULL_LABEL
    assert "Curation date unverified" in en.get_text()
    assert "精选日期待核实" in zh.get_text()


@pytest.mark.parametrize("as_of", [None, "", "bad", "2026-02-30", "2027-01-01"])
def test_valuation_date_never_borrows_price_or_global_date(as_of):
    result = _run_market_functions(
        ["valStaleChip"],
        "console.log(JSON.stringify(valStaleChip(" + json.dumps({
            "now": {"asOf": "2026-11-06"}, "valuation": {"asOf": as_of}
        }) + ")));",
        meta={"asOf": "2026-11-06"},
    )
    assert "Valuation date unverified" in result
    assert "2026-11-06" not in result and "NaN" not in result


@pytest.mark.parametrize("as_of,expected", [
    ("2026-11-06", "valuations as of 2026-11-06"),
    ("2026-10-23", "14d old"),
    ("2026-09-07", "60d old"),
])
def test_valuation_age_executes_exact_utc_day_boundaries(as_of, expected):
    result = _run_market_functions(
        ["valStaleChip"],
        "console.log(JSON.stringify(valStaleChip(" + json.dumps({
            "valuation": {"asOf": as_of}, "now": {"asOf": "2026-11-06"}
        }) + ")));",
    )
    assert expected in result
    if "60d" in expected:
        assert "cc-val-stale-red" in result


@pytest.mark.parametrize("older_date", ["2026-06-26", None, "2026-02-30", "2027-01-01"])
def test_observation_warning_survives_partial_refresh_and_language_change(older_date):
    cycles = [
        {"id": "us", "now": {"asOf": "2026-11-06"}},
        {"id": "china", "now": {"asOf": older_date}},
    ]
    result = _run_market_functions(
        ["renderStalenessBanner"],
        """renderStalenessBanner();
        var en=getNode("mkt-stale-banner").innerHTML;
        lang="zh";renderStalenessBanner();
        console.log(JSON.stringify({en:en,zh:getNode("mkt-stale-banner").innerHTML,
          header:getNode("cyc-asof").textContent}));""",
        cycles=cycles, meta={"asOf": "2026-11-06"},
    )
    assert result["en"] and result["zh"]
    assert "price observation" in result["en"]
    assert "价格观测" in result["zh"]
    assert "2026-11-06" in result["header"]
    if older_date == "2026-06-26":
        assert "1 of 2" in result["en"] and "2026-06-26" in result["header"]
    else:
        assert "unverified" in result["en"] and "待核实" in result["header"]


def test_fresh_observations_clear_only_their_own_warning():
    result = _run_market_functions(
        ["renderStalenessBanner"],
        """getNode("regime-prior-banner").innerHTML="CURATION_WARNING";
        renderStalenessBanner();
        console.log(JSON.stringify({price:getNode("mkt-stale-banner").innerHTML,
          curation:getNode("regime-prior-banner").innerHTML}));""",
        cycles=[{"id": "us", "now": {"asOf": "2026-11-01"}}],
    )
    assert result == {"price": "", "curation": "CURATION_WARNING"}


def test_pulse_uses_actual_position_sources_and_existing_mobile_reveal():
    result = _run_market_functions(
        ["renderGlobalPulse", "clamp", "posFromDrawdown", "engPos", "nowPosOf",
         "revealDetail", "expandSheet"],
        """var ENGINE={uk:{has_engine:true,pos_v2:90},hk:{has_engine:true,pos_v2:30}};
        var MODELS={us:{nowY:50}};
        window.MARKETS_ENGINE={as_of:"2026-11-04"};
        var click;
        getNode("global-regime-pulse").querySelectorAll=function(){
          return [{getAttribute(){return "hk";},addEventListener(name,fn){click=fn;}}];
        };
        renderGlobalPulse();click();
        console.log(JSON.stringify({
          track:getNode("global-regime-pulse-track").innerHTML,
          summary:getNode("global-regime-pulse-summary").textContent,
          asof:getNode("global-regime-pulse-asof").textContent,
          metrics:getNode("global-regime-pulse-metrics").innerHTML,
          focus:focusCalls,scroll:scrollCalls
        }));""",
        cycles=[
            {"id": "uk", "short": "UK", "now": {}},
            {"id": "hk", "short": "HK", "now": {}},
            {"id": "us", "short": "US", "now": {"pos": 50}},
        ],
    )
    assert result["track"].count('data-source="engine"') == 2
    assert result["track"].count('data-source="estimate"') == 1
    assert 'left:90%' in result["track"] and 'left:30%' in result["track"]
    assert "1 of 3 markets are near cycle highs" in result["summary"]
    assert "1 are lower-cycle" in result["summary"]
    assert "Engine through 2026-11-04" in result["asof"]
    assert "Curation date unverified" in result["asof"]
    assert result["focus"] == ["hk"]
    assert len(result["scroll"]) == 1 and result["scroll"][0]["behavior"] == "auto"


def test_pulse_is_covered_by_existing_membership_lock():
    src = TEMPLATE.read_text(encoding="utf-8")
    assert "lock_hide='.global-regime-pulse,.cyc-stage" in src
    assert "lock_renderer='markets_app.js'" in src
