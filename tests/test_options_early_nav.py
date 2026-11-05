"""Exercise the existing navigation owner under Options' early-boot opt-in.

Node executes the actual search, mobile, adaptive, drill and boot functions.
The minimal DOM records mutations/listeners and supplies explicit measurements;
it does not simulate browser paint or claim a CLS result. Settings, network and
unrelated page owners are inert. Browser timing remains a separate acceptance.
"""
from __future__ import annotations

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Callable, Optional
import unittest


ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "templates/theme.js"
OPTIONS = ROOT / "templates/options.html.j2"


class _Tags(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _run_owner(*, early=False, viewport=1440, body=True):
    source = THEME.read_text(encoding="utf-8")
    sections = [
        ("  var STOCK_MARKETS = [", "  /* A theme.js update reaches"),
        ("  function initNavSearch() {", "  /* ---- responsive mobile nav"),
        ("  function initMobileNav() {", "  /* ---- content-aware desktop nav"),
        ("  function initAdaptiveNav(", "  /* ---- settings modal"),
    ]
    functions = "\n".join(source[source.index(start):source.index(end, source.index(start))]
                          for start, end in sections)
    start = source.index("  // Build the settings modal as EARLY as possible.")
    boot = source[start:source.index("  // charts may finish drawing", start)]
    driver = r"""
const settings = SETTINGS;
const events = [], frames = new Map(), fontsReady = [];
let sequence = 0, mainParsed = false, settingsCalls = 0;
const ids = {};
function node(name, width) {
  const attributes = {}, listeners = {};
  const item = {
    name, width:width || 0, className:'', children:[], style:{}, listeners,
    setAttribute(k,v) {
      attributes[k] = String(v);
      if (name === 'nav' && k === 'data-nav-layout') {
        events.push({kind:'layout', value:String(v), mainParsed});
      }
    },
    getAttribute:k => Object.prototype.hasOwnProperty.call(attributes,k) ? attributes[k] : null,
    hasAttribute:k => Object.prototype.hasOwnProperty.call(attributes,k),
    removeAttribute:k => { delete attributes[k]; },
    addEventListener(k,fn) { (listeners[k] || (listeners[k]=[])).push(fn); },
    fire(k) { (listeners[k] || []).slice().forEach(fn => fn({target:item})); },
    appendChild(child) { this.children.push(child); if(child.id) ids[child.id]=child; return child; },
    insertBefore(child) { this.children.unshift(child); return child; },
    getBoundingClientRect() { return {width:this.width}; },
    querySelector() { return null; }, querySelectorAll() { return []; },
    focus() {}, blur() {}, remove() {}, contains() { return false; }
  };
  item.classList = {
    contains:value => item.className.split(/\s+/).includes(value),
    add(value) { if(!this.contains(value)) item.className += ' ' + value; },
    remove(value) { item.className=item.className.split(/\s+/).filter(x=>x!==value).join(' '); },
    toggle(value,force) {
      const on=force===undefined ? !this.contains(value) : force;
      if(on) this.add(value); else this.remove(value); return on;
    }
  };
  return item;
}
const nav=node('nav');nav.className='site-nav';nav.clientWidth=settings.viewport-32;
const links=node('links');links.className='nav-links';
links.children=[node('brand',500),node('menus',500)];
const controls=node('controls',157.36);
const box=node('search');box.className='nav-search';
const searchNodes={};
['.search-trigger','.ticker-input','.search-esc','.ticker-dropdown','.idle-ticker'].forEach(k=>searchNodes[k]=node(k));
searchNodes['.ticker-input'].value='';
box.querySelector=k=>searchNodes[k] || null;
nav.children=[links,box,controls];
nav.querySelector=k=>k==='.nav-links' ? links : k==='.nav-search' ? box :
  k==='.nav-ctrls' ? controls : k==='.nav-toggle' ?
  nav.children.find(x=>x.classList.contains('nav-toggle')) || null : null;
const bodyNode=node('body'), head=node('head'), document=node('document'), window=node('window');
document.head=head;document.body=settings.body ? bodyNode : null;
document.documentElement=node('html');document.documentElement.scrollTop=0;
document.fonts={ready:{then:fn=>fontsReady.push(fn)}};
document.querySelector=k=>k==='.site-nav, .topbar' ? nav : k==='.nav-search' ? box : null;
document.getElementById=k=>ids[k] || null;
document.createElement=k=>node(k);
window.innerWidth=settings.viewport;window.scrollY=0;
window.matchMedia=()=>({matches:true});
window.getComputedStyle=()=>({display:'flex',position:'static'});
function requestAnimationFrame(fn) { const id=++sequence;frames.set(id,fn);return id; }
function cancelAnimationFrame(id) { frames.delete(id); }
window.requestAnimationFrame=requestAnimationFrame;
function flushFrames() { const pending=[...frames.values()];frames.clear();pending.forEach(fn=>fn()); }
const _mmThemeScript={hasAttribute:k=>settings.early && k==='data-nav-early'};
const _mmSharedAssetRoot='/';
const NAV_MOBILE_CSS='';
function curLang() { return 'en'; }
function ensureNavSearchCss() { return true; }
function ensureNavLogoAssets() {}
function initSettings() { settingsCalls++; return true; }
function wrapTables() {}
function _authBoot() {}
function initActiveNav() {}
function initShowMore() {}
function pinBoardTrackToggle() {}
function initListCollapse() {}
function initListOverlay() {}
function initRowPop() {}
function initChatLauncher() {}
function themeCharts() {}
FUNCTIONS
function counts() {
  const toggle=nav.querySelector('.nav-toggle');
  return {trigger:(searchNodes['.search-trigger'].listeners.click||[]).length,
    input:(searchNodes['.ticker-input'].listeners.keydown||[]).length,
    toggle:toggle ? (toggle.listeners.click||[]).length : 0,
    resize:(window.listeners.resize||[]).length,
    click:(document.listeners.click||[]).length,
    keydown:(document.listeners.keydown||[]).length,
    language:(document.listeners.langchange||[]).length,
    market:(document.listeners['mmx-markets-change']||[]).length,
    font:fontsReady.length};
}
function snapshot() {
  return {layout:nav.getAttribute('data-nav-layout'),
    searchReady:box.getAttribute('data-ticker-search-ready'),
    mobile:!!nav.querySelector('.nav-toggle'),pendingFrames:frames.size,
    counts:counts(), settingsCalls, events:events.slice()};
}
BOOT
const before=snapshot();
mainParsed=true;document.body=bodyNode;
document.fire('DOMContentLoaded');
const ready=snapshot();
flushFrames();
const settled=snapshot();
// Every later cause still schedules/coalesces the very same adaptive paint.
nav.clientWidth=1000;
window.fire('resize');
document.fire('mmx-markets-change');
document.fire('langchange');
fontsReady.forEach(fn=>fn());
const updatePending=snapshot();
flushFrames();
const updated=snapshot();
process.stdout.write(JSON.stringify({before,ready,settled,updatePending,updated}));
"""
    driver = driver.replace("SETTINGS", json.dumps(dict(early=early, viewport=viewport, body=body)))
    driver = driver.replace("FUNCTIONS", functions).replace("BOOT", boot)
    result = subprocess.run(["node", "-"], input=driver, text=True,
                            capture_output=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


class OptionsEarlyNavMarkupTests(unittest.TestCase):
    def test_one_synchronous_opted_in_script_after_nav_before_main(self):
        source = OPTIONS.read_text(encoding="utf-8")
        tags = _Tags(source).tags
        scripts = [attrs for tag, attrs in tags
                   if tag == "script" and attrs.get("src") == "theme.js"]
        self.assertEqual(len(scripts), 1)
        self.assertIn("data-nav-early", scripts[0])
        self.assertIn("data-sync", scripts[0])
        self.assertNotIn("defer", scripts[0])
        self.assertNotIn("async", scripts[0])
        self.assertIn(("link", {"rel":"preload", "href":"theme.js", "as":"script"}), tags)
        flag = source.index("{% set nav_defer_enhancements = true %}")
        nav = source.index('{% include "_site_nav.html.j2" %}')
        script = source.index('<script src="theme.js" data-sync data-nav-early>')
        main = source.index('<main class="oew"')
        self.assertLess(flag, nav)
        self.assertLess(nav, script)
        self.assertLess(script, main)
        self.assertLess(source.index('href="theme.js" as="script"'), source.index('</head>'))

    def test_real_asset_optimizer_preserves_sync_and_matches_preload_url(self):
        # Load the pure optimizer and its actual constants without importing
        # unrelated repository configuration or reading production stores.
        path = ROOT / "lib/pages.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = {"DBASE_MARKER", "_OPEN_TAG_RE", "_SRC_ATTR_RE",
                     "_HAS_DEFER_ASYNC_RE", "_MODULE_RE", "_SCHEME_RE",
                     "_OUR_STAMP_RE", "_REL_ATTR_RE"}
        selected = []
        for item in tree.body:
            if isinstance(item, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in constants
                for target in item.targets
            ):
                selected.append(item)
            elif isinstance(item, ast.FunctionDef) and item.name in {
                "_is_local_asset", "optimize_assets_text"
            }:
                selected.append(item)
        namespace = {"re": re, "Callable": Callable, "Optional": Optional}
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
        optimize = namespace["optimize_assets_text"]
        source = OPTIONS.read_text(encoding="utf-8")
        optimized = optimize(source, lambda _: "1234abcd")
        tags = _Tags(optimized).tags
        script = next(attrs for tag, attrs in tags if tag == "script"
                      and attrs.get("src", "").startswith("theme.js"))
        preload = next(attrs for tag, attrs in tags if tag == "link"
                       and attrs.get("rel") == "preload" and attrs.get("as") == "script")
        self.assertEqual(script["src"], "theme.js?v=1234abcd")
        self.assertEqual(preload["href"], script["src"])
        self.assertIn("data-sync", script)
        self.assertIn("data-nav-early", script)
        self.assertNotIn("defer", script)
        self.assertNotIn("async", script)
        self.assertEqual(optimize(optimized, lambda _: "1234abcd"), optimized)


@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class OptionsEarlyNavOwnerTests(unittest.TestCase):
    def test_default_keeps_dom_ready_then_animation_frame(self):
        result = _run_owner()
        self.assertIsNone(result["before"]["searchReady"])
        self.assertFalse(result["before"]["mobile"])
        self.assertIsNone(result["before"]["layout"])
        self.assertEqual(result["before"]["pendingFrames"], 0)
        self.assertEqual(result["ready"]["searchReady"], "1")
        self.assertTrue(result["ready"]["mobile"])
        self.assertIsNone(result["ready"]["layout"])
        self.assertEqual(result["ready"]["pendingFrames"], 1)
        self.assertEqual(result["settled"]["layout"], "single")

    def test_opt_in_measures_before_main_and_fallback_does_not_duplicate_handlers(self):
        result = _run_owner(early=True)
        before, ready = result["before"], result["ready"]
        self.assertEqual(before["searchReady"], "1")
        self.assertTrue(before["mobile"])
        self.assertEqual(before["layout"], "single")
        self.assertEqual(before["pendingFrames"], 0)
        self.assertTrue(before["events"])
        self.assertTrue(all(not event["mainParsed"] for event in before["events"]))
        self.assertEqual(ready["events"], before["events"])
        self.assertEqual(ready["pendingFrames"], 0)
        for event in ("trigger", "input", "toggle", "resize", "language", "market", "font"):
            self.assertEqual(ready["counts"][event], before["counts"][event], event)
        self.assertEqual(ready["counts"]["trigger"], 1)
        self.assertEqual(ready["counts"]["input"], 1)
        self.assertEqual(ready["counts"]["toggle"], 1)
        # Drills bind one document click and one keydown at DOM-ready, never early.
        self.assertEqual(before["counts"]["click"], 2)
        self.assertEqual(before["counts"]["keydown"], 1)
        self.assertEqual(ready["counts"]["click"], 3)
        self.assertEqual(ready["counts"]["keydown"], 2)

    def test_default_and_opt_in_keep_later_measurement_events_coalesced(self):
        for early in (False, True):
            with self.subTest(early=early):
                result = _run_owner(early=early)
                self.assertEqual(result["settled"]["layout"], "single")
                self.assertEqual(result["updatePending"]["pendingFrames"], 1)
                self.assertEqual(result["updatePending"]["layout"], "single")
                self.assertEqual(result["updated"]["layout"], "stacked")
                self.assertEqual(result["updated"]["pendingFrames"], 0)

    def test_existing_900_901_boundary_remains_owned_by_adaptive_measurement(self):
        mobile = _run_owner(early=True, viewport=900)
        desktop = _run_owner(early=True, viewport=901)
        self.assertIsNone(mobile["before"]["layout"])
        self.assertEqual(desktop["before"]["layout"], "stacked")
        self.assertTrue(mobile["before"]["mobile"])
        self.assertTrue(desktop["before"]["mobile"])

    def test_opt_in_without_body_uses_ordinary_dom_ready_fallback(self):
        result = _run_owner(early=True, body=False)
        self.assertIsNone(result["before"]["searchReady"])
        self.assertEqual(result["before"]["settingsCalls"], 0)
        self.assertEqual(result["ready"]["searchReady"], "1")
        self.assertEqual(result["ready"]["pendingFrames"], 1)
        self.assertEqual(result["settled"]["layout"], "single")
