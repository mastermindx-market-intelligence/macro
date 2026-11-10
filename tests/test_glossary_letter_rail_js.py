"""Behavioral contract for the glossary A-Z rail's click handling.

The rail emits exactly one build-time `id="gl-letter-X"` anchor per occupied
letter (pinned by tests/test_glossary_contract.py::
test_rendered_letter_rail_anchors_are_unique_ids). That single anchor can
live inside a row that the current domain/search filter has hidden
(`display:none`) — a `display:none` fragment target has no layout box, so a
plain `href="#gl-letter-X"` native jump is a silent no-op even though the
rail still presents the letter as enabled (findings review, round 2,
MAJOR 1). This module runs the actual inline glossary IIFE (extracted from
a real render) in a node-shelled DOM shim and asserts that clicking a live
letter scrolls to the first currently-VISIBLE row carrying that letter,
never to a hidden one — regardless of which row happens to hold the
build-time anchor.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
from html.parser import HTMLParser

import pytest
from jinja2 import Environment, FileSystemLoader

from lib import config
from lib.glossary import glossary_view_model

ROOT = config.ROOT
HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")


def _extract_iife() -> str:
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    vm = glossary_view_model(ROOT)
    html = env.get_template("glossary.html.j2").render(generated_utc="2026-01-01 00:00", **vm)
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert scripts, "no inline <script> blocks rendered"
    iife = scripts[-1]
    assert "gl-search" in iife, "expected the glossary filter IIFE as the last inline script"
    return iife


SHIM = r"""
global.__scrollLog = [];
global.__replaceStateLog = [];

function makeEl(id, attrs) {
  attrs = attrs || {};
  var listeners = {};
  var el = {
    id: id,
    tagName: attrs.tagName || 'DIV',
    hidden: !!attrs.hidden,
    dataset: {},
    _attrs: {},
  };
  Object.keys(attrs).forEach(function (k) {
    if (k === 'tagName' || k === 'hidden') return;
    el._attrs[k] = attrs[k];
  });
  el.getAttribute = function (name) {
    return Object.prototype.hasOwnProperty.call(el._attrs, name) ? el._attrs[name] : null;
  };
  el.setAttribute = function (name, val) { el._attrs[name] = String(val); };
  el.removeAttribute = function (name) { delete el._attrs[name]; };
  el.hasAttribute = function (name) { return Object.prototype.hasOwnProperty.call(el._attrs, name); };
  el.classList = { toggle: function () {}, add: function () {}, remove: function () {} };
  el.addEventListener = function (type, fn) { (listeners[type] = listeners[type] || []).push(fn); };
  el.dispatchEvent = function (ev) {
    (listeners[ev.type] || []).forEach(function (fn) { fn(ev); });
    return true;
  };
  el.scrollIntoView = function (opts) { global.__scrollLog.push({ id: el.id, opts: opts }); };
  el.querySelector = function () { return null; };
  el.querySelectorAll = function () { return []; };
  return el;
}

var ROOT_EL = makeEl('glossary', { 'data-glossary-state': 'complete' });
var QUERY_EL = makeEl('gl-search', { tagName: 'INPUT' });
QUERY_EL.value = '';
var COUNT_EL = makeEl('gl-result-count');
var PANEL_EL = makeEl('panel');

// Two rows sharing letter E: the FIRST (build-time anchor holder, per the
// unique-id fix) sits in a domain the current filter has hidden; the
// SECOND is visible. This mirrors the review's measured us-stocks/
// china-stocks E-letter stranding.
var ROW_HIDDEN_ANCHOR = makeEl('gl-entry-timing-dot-us', {
  'data-glossary-row': '', 'data-domain': 'us-stocks', 'data-letter': 'E',
  'data-search': 'entry timing dot', hidden: true,
});
var ROW_VISIBLE = makeEl('gl-entry-timing-chips-cn', {
  'data-glossary-row': '', 'data-domain': 'china-stocks', 'data-letter': 'E',
  'data-search': 'entry timing chip', hidden: false,
});
var ROWS = [ROW_HIDDEN_ANCHOR, ROW_VISIBLE];

var LETTER_E = makeEl('letter-E', { tagName: 'A', 'data-letter': 'E', href: '#gl-letter-E' });
var LETTERS = [LETTER_E];

ROOT_EL.querySelectorAll = function (sel) {
  if (sel === '[data-glossary-row]') return ROWS;
  if (sel === '.gl-letter') return LETTERS;
  if (sel === '[data-domain-section]') return [];
  if (sel === '[data-domain]') return [];
  return [];
};
ROOT_EL.querySelector = function (sel) {
  if (sel === '[data-empty-state]') return PANEL_EL;
  return null;
};

var __byId = { glossary: ROOT_EL, 'gl-search': QUERY_EL, 'gl-result-count': COUNT_EL };
global.document = {
  readyState: 'complete',
  documentElement: {
    getAttribute: function () { return null; },
    setAttribute: function () {},
  },
  getElementById: function (id) { return __byId[id] || null; },
  addEventListener: function () {},
  removeEventListener: function () {},
};
global.window = global;
global.history = { replaceState: function (a, b, url) { global.__replaceStateLog.push(url); } };
function OUT(o) { process.stdout.write(JSON.stringify(o)); }
"""


@needs_node
def test_clicking_a_live_letter_scrolls_to_a_visible_row_not_a_hidden_anchor():
    iife = _extract_iife()
    script = SHIM + "\n" + textwrap.dedent(iife) + """
    var ev = { type: 'click', defaultPrevented: false, preventDefault: function () { this.defaultPrevented = true; } };
    LETTER_E.dispatchEvent(ev);
    OUT({
      scrollLog: global.__scrollLog,
      defaultPrevented: ev.defaultPrevented,
    });
    """
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    assert res.stdout.strip(), f"no stdout; stderr:\n{res.stderr}"
    out = json.loads(res.stdout)
    assert out["scrollLog"], (
        "clicking a live letter must scroll to a row — the letter link needs a "
        "click handler that re-targets to the currently-visible row, not just a "
        "static href to the build-time anchor"
    )
    scrolled_ids = [entry["id"] for entry in out["scrollLog"]]
    assert "gl-entry-timing-dot-us" not in scrolled_ids, (
        "must never scroll to a row the current filter has hidden — "
        f"scrolled to {scrolled_ids!r}"
    )
    assert "gl-entry-timing-chips-cn" in scrolled_ids, (
        "must scroll to the first currently-visible row carrying the clicked letter — "
        f"scrolled to {scrolled_ids!r}"
    )
    assert out["defaultPrevented"], (
        "native fragment navigation to the (possibly hidden) static anchor must be "
        "suppressed once JS has taken over the jump"
    )


class _FilterElements(HTMLParser):
    """Read the actual render's filter controls and rows, not a second glossary."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self.buttons = []
        self.letters = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        entry = {"id": attrs.get("id", ""), "attrs": {**attrs, "tagName": tag.upper()}}
        if "data-glossary-row" in attrs:
            self.rows.append(entry)
        if tag == "button" and "gl-filter" in attrs.get("class", "").split():
            self.buttons.append(entry)
        if "gl-letter" in attrs.get("class", "").split():
            self.letters.append(entry)


FILTER_SHIM = r"""
ROWS = FIXTURE.rows.map(function (r) { return makeEl(r.id, r.attrs); });
var FILTER_BUTTONS = FIXTURE.buttons.map(function (b) { return makeEl(b.id, b.attrs); });
LETTERS = FIXTURE.letters.map(function (l) { return makeEl(l.id, l.attrs); });
COUNT_EL.textContent = String(ROWS.length);
PANEL_EL.hidden = true;
QUERY_EL.setAttribute('data-ph-en', 'Search terms');
QUERY_EL.setAttribute('data-ph-zh', '搜索词条');
document.documentElement.getAttribute = function (name) { return name === 'data-lang' ? LANG : null; };
ROOT_EL.querySelectorAll = function (sel) {
  if (sel === '[data-glossary-row]') return ROWS;
  if (sel === '[data-domain-section]') return [];
  if (sel === '.gl-letter') return LETTERS;
  // Honor both selectors against the real HTML element types/classes. The
  // old broad selector also binds rows, which is the regression under test.
  if (sel === '[data-domain]') return FILTER_BUTTONS.concat(ROWS);
  if (sel === 'button.gl-filter[data-domain]') return FILTER_BUTTONS.filter(function (b) {
    return b.tagName === 'BUTTON' && (b.getAttribute('class') || '').split(/\s+/).includes('gl-filter') && b.hasAttribute('data-domain');
  });
  throw new Error('unmodelled root selector: ' + sel);
};
function click(el, part) {
  var ev = { type: 'click', target: part ? { parentNode: el, part: part } : el,
    defaultPrevented: false, preventDefault: function () { this.defaultPrevented = true; } };
  // A descendant click bubbles to its row with the same target. This does
  // not simulate browser navigation or layout, only the owning JS listener.
  el.dispatchEvent(ev);
  return ev.defaultPrevented;
}
function button(domain) { return FILTER_BUTTONS.find(function (b) { return b.getAttribute('data-domain') === domain; }); }
function search(value) { QUERY_EL.value = value; QUERY_EL.dispatchEvent({ type: 'input' }); }
function snapshot() {
  return { count: COUNT_EL.textContent, query: QUERY_EL.value, empty: !PANEL_EL.hidden,
    state: ROOT_EL.getAttribute('data-glossary-state'),
    visible: ROWS.filter(function (r) { return !r.hidden; }).map(function (r) { return r.id; }),
    pressed: FILTER_BUTTONS.filter(function (b) { return b.getAttribute('aria-pressed') === 'true'; }).map(function (b) { return b.getAttribute('data-domain'); }),
    rowPressed: ROWS.filter(function (r) { return r.hasAttribute('aria-pressed'); }).map(function (r) { return r.id; }) };
}
"""


def _run_filter_case(source, language, action):
    if source == "template":
        env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
        html = env.get_template("glossary.html.j2").render(
            generated_utc="2026-01-01 00:00", **glossary_view_model(ROOT)
        )
    else:
        html = (ROOT / "site" / "glossary.html").read_text(encoding="utf-8")
    elements = _FilterElements()
    elements.feed(html)
    assert elements.rows and elements.buttons
    iife = re.findall(r"<script>(.*?)</script>", html, re.S)[-1]
    assert "gl-search" in iife
    fixture = {"rows": elements.rows, "buttons": elements.buttons, "letters": elements.letters}
    script = (SHIM + "\nvar FIXTURE = " + json.dumps(fixture) + ";\nvar LANG = "
              + json.dumps(language) + ";\n" + FILTER_SHIM + "\n" + iife + "\n" + action)
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\n{res.stderr}\n{res.stdout}"
    return json.loads(res.stdout)


@needs_node
@pytest.mark.parametrize("source", ["template", "committed"])
@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("part", ["term", "definition", "source-link"])
def test_row_content_clicks_preserve_filter_state(source, language, part):
    out = _run_filter_case(source, language, """
      var before = snapshot();
      var prevented = ROWS.map(function (row) { return click(row, PART); });
      OUT({ before: before, after: snapshot(), prevented: prevented });
    """.replace("PART", json.dumps(part)))
    assert out["after"] == out["before"]
    assert not any(out["prevented"]), "source links must retain their default navigation"
    assert out["after"]["pressed"] == ["all"]
    assert out["after"]["rowPressed"] == []


@needs_node
@pytest.mark.parametrize("source", ["template", "committed"])
@pytest.mark.parametrize("language,needle,expected", [("en", "Net Conviction", 2), ("zh", "净", 3)])
def test_row_click_does_not_hide_cross_domain_search(source, language, needle, expected):
    out = _run_filter_case(source, language, """
      var row = ROWS.find(function (r) { return r.id === 'gl-market-state-score'; });
      if (!row) throw new Error('missing real Market State Score row');
      click(row, 'term'); search(NEEDLE); OUT(snapshot());
    """.replace("NEEDLE", json.dumps(needle)))
    assert int(out["count"]) == expected
    assert out["pressed"] == ["all"]
    assert out["query"] == needle
    assert not out["empty"]


@needs_node
@pytest.mark.parametrize("source", ["template", "committed"])
@pytest.mark.parametrize("language", ["en", "zh"])
def test_explicit_filters_and_search_recovery_remain_working(source, language):
    out = _run_filter_case(source, language, """
      var cases = FILTER_BUTTONS.map(function (b) {
        var domain = b.getAttribute('data-domain'); click(b);
        var before = snapshot();
        ROWS.filter(function (r) { return !r.hidden; }).forEach(function (r) { click(r, 'definition'); });
        var after = snapshot();
        return { domain: domain, expected: domain === 'all' ? ROWS.length : ROWS.filter(function (r) { return r.getAttribute('data-domain') === domain; }).length,
          before: before, after: after };
      });
      click(button('all')); search('zz-no-matching-glossary-term-zz'); var empty = snapshot();
      search(''); OUT({ cases: cases, empty: empty, recovered: snapshot(), total: ROWS.length,
        placeholder: QUERY_EL.getAttribute('placeholder') });
    """)
    for case in out["cases"]:
        assert case["after"] == case["before"]
        assert int(case["after"]["count"]) == case["expected"]
        assert case["after"]["pressed"] == [case["domain"]]
        assert case["after"]["rowPressed"] == []
    assert out["empty"]["count"] == "0"
    assert out["empty"]["empty"] and out["empty"]["state"] == "empty"
    assert int(out["recovered"]["count"]) == out["total"]
    assert not out["recovered"]["empty"]
    assert out["recovered"]["pressed"] == ["all"]
    assert out["placeholder"] == ("搜索词条" if language == "zh" else "Search terms")
